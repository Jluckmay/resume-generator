"""Módulo para sincronização dinâmica e recuperação de modelos de IA disponíveis em tempo real.

Consulta endpoints oficiais de modelos de cada provedor (NVIDIA NIM, Google, OpenAI, DeepSeek, Anthropic)
com cache em memória volátil RAM (TTL), higienização de modelos utilitários/embeddings e fallback
garantido para os modelos curados do sistema.
"""

from __future__ import annotations

import hashlib
import logging
import time
from typing import Any, Dict, List, Tuple

import requests

from .config import PROVIDERS_CONFIG

logger = logging.getLogger(__name__)

# Cache em memória volátil: { cache_key: (timestamp, [models]) }
_MODELS_CACHE: Dict[str, Tuple[float, List[Dict[str, str]]]] = {}
_CACHE_TTL_SECONDS = 600.0  # 10 minutos de retenção

# Mapeamento de descrições amigáveis para modelos conhecidos da NVIDIA NIM
_NVIDIA_MODEL_NAMES: Dict[str, str] = {
    "nvidia/nemotron-3.5-super-vl-120b-a12b": "NVIDIA Nemotron 3.5 Super 120B (Recomendado • 0 CoT)",
    "stepfun-ai/step-5-preview": "StepFun Step-5 Preview (Alta Velocidade)",
    "google/gemma-4-31b-it": "Google Gemma 4 31B Instruct (Econômico)",
    "z-ai/glm-5.3-flash": "Z-AI GLM 5.3 Flash (Raciocínio Avançado)",
    "mistralai/mistral-large-4-1t-a52b": "Mistral Large 4 1T (A52B MoE)",
    "nvidia/nemotron-3.5-lightning-30b-a3b": "NVIDIA Nemotron 3.5 Lightning 30B (Ultra Rápido)",
    "nvidia/nemotron-3-ultra-550b-a55b": "NVIDIA Nemotron 3 Ultra 550B (Alta Capacidade)",
    "google/gemma-3-12b-it": "Google Gemma 3 12B Instruct",
    "google/gemma-3-4b-it": "Google Gemma 3 4B Instruct",
    "openai/gpt-oss-20b": "OpenAI GPT-OSS 20B",
    "minimaxai/minimax-m3.1-flash": "MiniMax M3.1 Flash",
    "meta/muse-glimmer-30b": "Meta Muse Glimmer 30B",
    "poolside/laguna-xs-2.1": "Poolside Laguna XS 2.1",
    "bigcode/starcoder2-15b": "StarCoder 2 15B",
    "nvidia/cosmos-reason2-8b": "NVIDIA Cosmos Reason 2 8B",
    "nvidia/nemotron-3.5-bolt-e4b": "NVIDIA Nemotron 3.5 Bolt E4B",
    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning": "NVIDIA Nemotron 3 Nano Omni 30B",
}

_NVIDIA_EXCLUDE_KEYWORDS = (
    "embed",
    "clip",
    "detector",
    "guard",
    "calibration",
    "safety",
    "translate",
    "retriever",
    "synthetic-video",
)


def _get_cache_key(provider: str, api_key: str | None = None) -> str:
    key_hash = hashlib.sha256(api_key.encode("utf-8")).hexdigest()[:12] if api_key else "none"
    return f"{provider}:{key_hash}"


def _get_fallback_models(provider: str) -> List[Dict[str, str]]:
    prov_cfg = PROVIDERS_CONFIG.get(provider, PROVIDERS_CONFIG.get("default", {}))
    return list(prov_cfg.get("models", []))


def _fetch_nvidia_models(api_key: str | None = None) -> List[Dict[str, str]]:
    url = "https://integrate.api.nvidia.com/v1/models"
    headers = {"Accept": "application/json"}
    if api_key and api_key.strip():
        headers["Authorization"] = f"Bearer {api_key.strip()}"

    resp = requests.get(url, headers=headers, timeout=4.0)
    if resp.status_code != 200:
        raise ValueError(f"NVIDIA API retornou HTTP {resp.status_code}")

    data = resp.json().get("data", [])
    models: List[Dict[str, str]] = []

    for item in data:
        m_id = str(item.get("id", "")).strip()
        if not m_id:
            continue
        m_id_lower = m_id.lower()
        if any(kw in m_id_lower for kw in _NVIDIA_EXCLUDE_KEYWORDS):
            continue

        friendly_name = _NVIDIA_MODEL_NAMES.get(m_id)
        if not friendly_name:
            # Constrói nome legível a partir do ID
            parts = m_id.split("/")
            base = parts[-1].replace("-", " ").replace("_", " ").title()
            prefix = parts[0].title() if len(parts) > 1 else ""
            friendly_name = f"{prefix} {base}".strip()

        models.append({"id": m_id, "name": friendly_name})

    # Prioridades preferenciais para ordenar os modelos mais relevantes no topo
    priority_order = [
        "nvidia/nemotron-3.5-super-vl-120b-a12b",
        "stepfun-ai/step-5-preview",
        "google/gemma-4-31b-it",
        "z-ai/glm-5.3-flash",
        "mistralai/mistral-large-4-1t-a52b",
        "nvidia/nemotron-3.5-lightning-30b-a3b",
        "nvidia/nemotron-3-ultra-550b-a55b",
        "google/gemma-3-12b-it",
        "google/gemma-3-4b-it",
        "openai/gpt-oss-20b",
        "minimaxai/minimax-m3.1-flash",
    ]

    def nvidia_sort_key(m: Dict[str, str]) -> Tuple[int, str]:
        mid = m["id"]
        if mid in priority_order:
            return (priority_order.index(mid), m["name"])
        if mid in _NVIDIA_MODEL_NAMES:
            return (100, m["name"])
        return (200, m["name"])

    models.sort(key=nvidia_sort_key)
    return models if models else _get_fallback_models("default")


def _fetch_google_models(api_key: str) -> List[Dict[str, str]]:
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key.strip()}"
    resp = requests.get(url, timeout=3.5)
    if resp.status_code != 200:
        raise ValueError(f"Google API retornou HTTP {resp.status_code}")

    data = resp.json().get("models", [])
    models: List[Dict[str, str]] = []

    for item in data:
        raw_name = str(item.get("name", "")).strip()
        m_id = raw_name.replace("models/", "")
        methods = item.get("supportedGenerationMethods", [])
        if "generateContent" not in methods:
            continue
        if not m_id.startswith("gemini"):
            continue

        disp_name = str(item.get("displayName") or m_id)
        models.append({"id": m_id, "name": f"{disp_name} ({m_id})"})

    # Prioriza gemini-2.0-flash e versões mais recentes
    def google_sort_key(m: Dict[str, str]) -> int:
        mid = m["id"]
        if "2.0-flash" in mid:
            return 0
        if "2.5" in mid:
            return 1
        if "1.5-flash" in mid:
            return 2
        if "1.5-pro" in mid:
            return 3
        return 10

    models.sort(key=google_sort_key)
    return models if models else _get_fallback_models("google")


def _fetch_openai_models(api_key: str) -> List[Dict[str, str]]:
    url = "https://api.openai.com/v1/models"
    headers = {"Authorization": f"Bearer {api_key.strip()}"}
    resp = requests.get(url, headers=headers, timeout=3.5)
    if resp.status_code != 200:
        raise ValueError(f"OpenAI API retornou HTTP {resp.status_code}")

    data = resp.json().get("data", [])
    models: List[Dict[str, str]] = []
    allowed_prefixes = ("gpt-4o", "gpt-4", "o1", "o3", "chatgpt")
    exclude_keywords = ("audio", "realtime", "instruct", "vision-preview", "tts", "whisper", "embedding", "dall-e")

    for item in data:
        m_id = str(item.get("id", "")).strip()
        m_lower = m_id.lower()
        if not any(m_lower.startswith(p) for p in allowed_prefixes):
            continue
        if any(kw in m_lower for kw in exclude_keywords):
            continue
        models.append({"id": m_id, "name": m_id})

    def openai_sort_key(m: Dict[str, str]) -> int:
        mid = m["id"]
        if mid == "gpt-4o-mini":
            return 0
        if mid == "gpt-4o":
            return 1
        if "o3-mini" in mid:
            return 2
        if "o1" in mid:
            return 3
        return 10

    models.sort(key=openai_sort_key)
    return models if models else _get_fallback_models("openai")


def _fetch_deepseek_models(api_key: str) -> List[Dict[str, str]]:
    url = "https://api.deepseek.com/models"
    headers = {"Authorization": f"Bearer {api_key.strip()}"}
    resp = requests.get(url, headers=headers, timeout=3.5)
    if resp.status_code != 200:
        raise ValueError(f"DeepSeek API retornou HTTP {resp.status_code}")

    data = resp.json().get("data", [])
    models: List[Dict[str, str]] = []
    for item in data:
        m_id = str(item.get("id", "")).strip()
        if m_id:
            name = "DeepSeek V3 (deepseek-chat)" if m_id == "deepseek-chat" else (
                "DeepSeek R1 (deepseek-reasoner)" if m_id == "deepseek-reasoner" else m_id
            )
            models.append({"id": m_id, "name": name})

    return models if models else _get_fallback_models("deepseek")


def _fetch_claude_models(api_key: str) -> List[Dict[str, str]]:
    url = "https://api.anthropic.com/v1/models"
    headers = {
        "x-api-key": api_key.strip(),
        "anthropic-version": "2023-06-01",
    }
    resp = requests.get(url, headers=headers, timeout=3.5)
    if resp.status_code != 200:
        raise ValueError(f"Anthropic API retornou HTTP {resp.status_code}")

    data = resp.json().get("data", [])
    models: List[Dict[str, str]] = []
    for item in data:
        m_id = str(item.get("id", "")).strip()
        disp = str(item.get("display_name") or m_id)
        if m_id:
            models.append({"id": m_id, "name": f"{disp} ({m_id})"})

    return models if models else _get_fallback_models("claude")


def fetch_available_models_for_provider(provider: str, api_key: str | None = None) -> List[Dict[str, str]]:
    """Obtém a lista atualizada de modelos disponíveis para o provedor informado.

    Utiliza cache em RAM com TTL para baixa latência e resiliência contra falhas upstream.
    """
    prov = (provider or "default").strip().lower()
    if prov == "none":
        return [{"id": "none", "name": "Motor Determinístico de Extração (0 Tokens)"}]

    cache_key = _get_cache_key(prov, api_key)
    now = time.time()

    if cache_key in _MODELS_CACHE:
        ts, cached_models = _MODELS_CACHE[cache_key]
        if now - ts < _CACHE_TTL_SECONDS and cached_models:
            return cached_models

    try:
        if prov in ("default", "nvidia"):
            models = _fetch_nvidia_models(api_key)
        elif prov == "google":
            models = _fetch_google_models(api_key) if (api_key and api_key.strip()) else _get_fallback_models("google")
        elif prov == "openai":
            models = _fetch_openai_models(api_key) if (api_key and api_key.strip()) else _get_fallback_models("openai")
        elif prov == "deepseek":
            models = _fetch_deepseek_models(api_key) if (api_key and api_key.strip()) else _get_fallback_models("deepseek")
        elif prov == "claude":
            models = _fetch_claude_models(api_key) if (api_key and api_key.strip()) else _get_fallback_models("claude")
        else:
            models = _get_fallback_models(prov)

        if models:
            _MODELS_CACHE[cache_key] = (now, models)
            return models
    except Exception as exc:
        logger.warning("Falha ao buscar modelos ao vivo para '%s': %s. Usando fallback curado.", prov, exc)

    fallback = _get_fallback_models(prov)
    _MODELS_CACHE[cache_key] = (now, fallback)
    return fallback
