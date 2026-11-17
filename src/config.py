"""Configuração de diretórios e seleção dos modelos otimizados para provedores de IA (NVIDIA, Google, Claude, OpenAI, DeepSeek)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = PROJECT_ROOT / ".cache"
OUTPUT_DIR = PROJECT_ROOT / "output"

NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"

PROVIDERS_CONFIG: Dict[str, Dict[str, Any]] = {
    "default": {
        "id": "default",
        "name": "NVIDIA NIM (Padrão do Sistema)",
        "name_en": "NVIDIA NIM (System Default)",
        "requires_key": False,
        "key_hint": "Sem necessidade de chave — fornecida pelo servidor seguro",
        "key_hint_en": "No key needed — supplied securely by the server",
        "key_placeholder": "Chave padrão do servidor ativa",
        "key_placeholder_en": "Default server key active",
        "base_url": NVIDIA_BASE_URL,
        "default_model": "nvidia/nemotron-3.5-super-vl-120b-a12b",
        "models": [
            {
                "id": "nvidia/nemotron-3.5-super-vl-120b-a12b",
                "name": "NVIDIA Nemotron 3.5 Super VL 120B (A12B MoE) — Recomendado",
                "tier": "primary",
                "description": "Equilíbrio entre inteligência (120B), velocidade e 0 tokens de raciocínio ocultos.",
            },
            {
                "id": "stepfun-ai/step-5-preview",
                "name": "StepFun Step-5 Preview (Alta Velocidade)",
                "description": "Excelente velocidade e síntese concisa.",
            },
            {
                "id": "google/gemma-4-31b-it",
                "name": "Google Gemma 4 31B Instruct (Econômico)",
                "description": "Modelo de código aberto altamente eficiente.",
            },
            {
                "id": "z-ai/glm-5.3-flash",
                "name": "Z-AI GLM 5.3 Flash (Raciocínio Avançado)",
                "description": "Raciocínio avançado para estruturação de dados.",
            },
            {
                "id": "mistralai/mistral-large-4-1t-a52b",
                "name": "Mistral Large 4 1T (A52B MoE)",
                "description": "MoE de alta capacidade para currículos extensos.",
            },
        ],
    },
    "nvidia": {
        "id": "nvidia",
        "name": "NVIDIA NIM (Chave Própria)",
        "name_en": "NVIDIA NIM (Own API Key)",
        "requires_key": True,
        "key_prefix": "nvapi-",
        "key_hint": "Chave da NVIDIA NIM (iniciando em nvapi-...)",
        "key_hint_en": "NVIDIA NIM API Key (starts with nvapi-...)",
        "key_placeholder": "nvapi-...",
        "key_placeholder_en": "nvapi-...",
        "base_url": NVIDIA_BASE_URL,
        "default_model": "nvidia/nemotron-3.5-super-vl-120b-a12b",
        "models": [
            {
                "id": "nvidia/nemotron-3.5-super-vl-120b-a12b",
                "name": "NVIDIA Nemotron 3.5 Super VL 120B — Recomendado",
                "description": "MoE 120B otimizado para JSON e código LaTeX.",
            },
            {
                "id": "stepfun-ai/step-5-preview",
                "name": "StepFun Step-5 Preview",
                "description": "Alta velocidade e precisão de formato.",
            },
            {
                "id": "google/gemma-4-31b-it",
                "name": "Google Gemma 4 31B Instruct",
                "description": "Modelo de código aberto altamente eficiente.",
            },
            {
                "id": "z-ai/glm-5.3-flash",
                "name": "Z-AI GLM 5.3 Flash",
                "description": "Raciocínio avançado.",
            },
            {
                "id": "mistralai/mistral-large-4-1t-a52b",
                "name": "Mistral Large 4 1T (A52B MoE)",
                "description": "MoE de alta capacidade para currículos extensos.",
            },
        ],
    },
    "google": {
        "id": "google",
        "name": "Google Gemini (Chave Própria)",
        "name_en": "Google Gemini (Own API Key)",
        "requires_key": True,
        "key_prefix": "AIza",
        "key_hint": "Chave do Google AI Studio (iniciando em AIza...)",
        "key_hint_en": "Google AI Studio API Key (starts with AIza...)",
        "key_placeholder": "AIzaSy...",
        "key_placeholder_en": "AIzaSy...",
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "default_model": "gemini-2.0-flash",
        "models": [
            {
                "id": "gemini-2.0-flash",
                "name": "Gemini 2.0 Flash — Recomendado",
                "description": "Geração instantânea e suporte nativo a JSON e LaTeX.",
            },
            {
                "id": "gemini-1.5-flash",
                "name": "Gemini 1.5 Flash — Econômico",
                "description": "Rápido e leve para síntese de perfis e projetos.",
            },
            {
                "id": "gemini-1.5-pro",
                "name": "Gemini 1.5 Pro — Alta Capacidade",
                "description": "Raciocínio aprofundado para currículos acadêmicos extensos.",
            },
        ],
    },
    "claude": {
        "id": "claude",
        "name": "Anthropic Claude (Chave Própria)",
        "name_en": "Anthropic Claude (Own API Key)",
        "requires_key": True,
        "key_prefix": "sk-ant-",
        "key_hint": "Chave da Anthropic (iniciando em sk-ant-...)",
        "key_hint_en": "Anthropic API Key (starts with sk-ant-...)",
        "key_placeholder": "sk-ant-api03-...",
        "key_placeholder_en": "sk-ant-api03-...",
        "base_url": "https://api.anthropic.com/v1",
        "default_model": "claude-3-5-sonnet-20241022",
        "models": [
            {
                "id": "claude-3-5-sonnet-20241022",
                "name": "Claude 3.5 Sonnet — Recomendado",
                "description": "Líder em precisão textual e formatação sintática.",
            },
            {
                "id": "claude-3-5-haiku-20241022",
                "name": "Claude 3.5 Haiku — Rápido",
                "description": "Baixíssima latência e excelente síntese de tópicos.",
            },
        ],
    },
    "openai": {
        "id": "openai",
        "name": "OpenAI (Chave Própria)",
        "name_en": "OpenAI (Own API Key)",
        "requires_key": True,
        "key_prefix": "sk-",
        "key_hint": "Chave da OpenAI (iniciando em sk-...)",
        "key_hint_en": "OpenAI API Key (starts with sk-...)",
        "key_placeholder": "sk-proj-...",
        "key_placeholder_en": "sk-proj-...",
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o-mini",
        "models": [
            {
                "id": "gpt-4o-mini",
                "name": "GPT-4o Mini — Recomendado",
                "description": "Rápido, econômico e altamente capaz em estruturação de currículos.",
            },
            {
                "id": "gpt-4o",
                "name": "GPT-4o — Avançado",
                "description": "Maior capacidade descritiva e refinamento léxico.",
            },
            {
                "id": "o3-mini",
                "name": "o3-mini — Raciocínio",
                "description": "Focado em raciocínio estruturado para perfis técnicos.",
            },
        ],
    },
    "deepseek": {
        "id": "deepseek",
        "name": "DeepSeek (Chave Própria)",
        "name_en": "DeepSeek (Own API Key)",
        "requires_key": True,
        "key_prefix": "sk-",
        "key_hint": "Chave da DeepSeek (iniciando em sk-...)",
        "key_hint_en": "DeepSeek API Key (starts with sk-...)",
        "key_placeholder": "sk-...",
        "key_placeholder_en": "sk-...",
        "base_url": "https://api.deepseek.com",
        "default_model": "deepseek-chat",
        "models": [
            {
                "id": "deepseek-chat",
                "name": "DeepSeek V3 (deepseek-chat) — Recomendado",
                "description": "Excelente relação custo-benefício e alta qualidade técnica.",
            },
            {
                "id": "deepseek-reasoner",
                "name": "DeepSeek R1 (deepseek-reasoner)",
                "description": "Raciocínio avançado passo a passo.",
            },
        ],
    },
    "none": {
        "id": "none",
        "name": "Sem IA / Offline (0 Tokens — Extração Direta)",
        "name_en": "No AI / Offline (0 Tokens — Direct Extraction)",
        "requires_key": False,
        "key_hint": "Geração 100% determinística sem chamadas a modelos",
        "key_hint_en": "100% deterministic generation without model calls",
        "key_placeholder": "Modo offline ativo (zero tokens)",
        "key_placeholder_en": "Offline mode active (zero tokens)",
        "base_url": "",
        "default_model": "none",
        "models": [
            {
                "id": "none",
                "name": "Motor Determinístico de Extração / Direct Extractor Engine",
                "description": "Gera o currículo LaTeX diretamente dos dados coletados sem gastar nenhum token.",
            }
        ],
    },
}

RECOMMENDED_MODELS: List[Dict[str, str]] = PROVIDERS_CONFIG["default"]["models"]
DEFAULT_PROVIDER = "default"
DEFAULT_MODEL = RECOMMENDED_MODELS[0]["id"]

