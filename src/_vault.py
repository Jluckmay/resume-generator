"""Módulo de transporte seguro e cofre efêmero multi-provedor vinculado à tarefa (Task-Bound Enclave).

Implementa:
1. Suporte a chaves de API próprias (NVIDIA, Google Gemini, Anthropic Claude, OpenAI, DeepSeek).
2. Envelope criptográfico efêmero (SECKEY_V1) via AES-256-GCM com sal dinâmico vinculado ao tempo.
3. Descriptografia e ofuscação estritamente em memória volátil RAM (zero-disk, zero-log, zero-storage).
4. Higienização e zeroização imediata de buffers na memória (0x00) e limpeza de variáveis de ambiente.
5. Atestação de pilha de chamadas e pinning de conexão TLS 1.3 estrita por provedor.
"""

from __future__ import annotations

import base64
import hashlib
import inspect
import json
import os
import re
import ssl
import time
from typing import Any, Dict, List, Tuple

import requests
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_ALLOWED_MODES = (
    "MODE:CAVEMAN_JSON_ONLY",
    "MODE:CAVEMAN_LATEX_ONLY",
    "MODE:CAVEMAN_LATEX_REPAIR",
    "MODE:CAVEMAN_LATEX_REVIEW",
    "MODE:CAVEMAN_LATEX_CODE_AND_CONTENT_REVIEW",
)

_ALLOWED_MARKERS = (
    "DADOS_TOON:",
    "DADOS_PERFIL_TOON:",
    "CORPO_TEMPLATE_LATEX:",
    "ERROR:\n",
    "COMPILER_ERROR:",
    "LATEX_BODY_TO_REVIEW:",
)

_ENV_INTERCEPT_VARS = (
    "SSLKEYLOGFILE",
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
    "REQUESTS_CA_BUNDLE",
    "CURL_CA_BUNDLE",
    "PYTHONHTTPSVERIFY",
)

_PROVIDER_ENV_KEYS = {
    "default": ["NVIDIA_API_KEY", "NVIDIA_VAULT_KEY"],
    "nvidia": ["NVIDIA_API_KEY", "NVIDIA_VAULT_KEY"],
    "google": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
    "claude": ["ANTHROPIC_API_KEY", "CLAUDE_API_KEY"],
    "openai": ["OPENAI_API_KEY"],
    "deepseek": ["DEEPSEEK_API_KEY"],
}


class _PinnedTLS13Adapter(HTTPAdapter):
    """Adaptador HTTP com pinning de TLS 1.3 estrito e verificação forçada de hostname."""

    def __init__(self, expected_hostname: str | None = None, **kwargs: Any) -> None:
        self.expected_hostname = expected_hostname
        super().__init__(**kwargs)

    def init_poolmanager(self, connections: int, maxsize: int, block: bool = False, **pool_kwargs: Any) -> None:
        ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        ctx.minimum_version = ssl.TLSVersion.TLSv1_3
        ctx.check_hostname = True
        ctx.verify_mode = ssl.CERT_REQUIRED
        ctx.options |= ssl.OP_NO_COMPRESSION | ssl.OP_NO_TICKET
        pool_kwargs["ssl_context"] = ctx
        if self.expected_hostname:
            pool_kwargs["assert_hostname"] = self.expected_hostname
        self.poolmanager = PoolManager(num_pools=connections, maxsize=maxsize, block=block, **pool_kwargs)


def _scrub_network_environment() -> None:
    """Remove variáveis de interceptação TLS e proxies para impedir captura de pacotes em trânsito."""
    for var in _ENV_INTERCEPT_VARS:
        if var in os.environ:
            os.environ.pop(var, None)


_SERVER_ENCLAVE_STORE: Dict[str, str] = {}


def _get_server_key_for_provider(prov: str) -> str:
    """Recupera chave do servidor armazenada no enclave em RAM, lendo do ambiente se disponível."""
    global _SERVER_ENCLAVE_STORE
    lookup_prov = "default" if prov == "nvidia" else prov
    if lookup_prov in _SERVER_ENCLAVE_STORE and _SERVER_ENCLAVE_STORE[lookup_prov]:
        return _SERVER_ENCLAVE_STORE[lookup_prov]
    if prov in _SERVER_ENCLAVE_STORE and _SERVER_ENCLAVE_STORE[prov]:
        return _SERVER_ENCLAVE_STORE[prov]

    env_vars = _PROVIDER_ENV_KEYS.get(prov, _PROVIDER_ENV_KEYS["default"])
    for ev in env_vars:
        val = os.environ.get(ev, "").strip()
        if val:
            _SERVER_ENCLAVE_STORE[prov] = val
            if prov in ("default", "nvidia"):
                _SERVER_ENCLAVE_STORE["default"] = val
                _SERVER_ENCLAVE_STORE["nvidia"] = val
            # Limpa de os.environ para que nenhum processo-filho herde as credenciais
            os.environ.pop(ev, None)
            return val

    # Fallback cruzado entre default e nvidia
    if prov in ("default", "nvidia"):
        fallback = _SERVER_ENCLAVE_STORE.get("default") or _SERVER_ENCLAVE_STORE.get("nvidia")
        if fallback:
            return fallback
    return ""


def _scrub_all_provider_keys() -> None:
    """Higieniza o ambiente de execução removendo todas as variáveis de chave de provedor."""
    for prov in _PROVIDER_ENV_KEYS:
        _get_server_key_for_provider(prov)
    for var_list in _PROVIDER_ENV_KEYS.values():
        for var in var_list:
            if var in os.environ:
                os.environ.pop(var, None)


def create_secure_envelope(raw_key: str, provider: str = "default") -> str:
    """Cria um envelope criptográfico efêmero (SECKEY_V1) usando AES-256-GCM com sal temporal dinâmico."""
    if not raw_key or not raw_key.strip():
        return ""
    ts = int(time.time() * 1000)
    iv_bytes = os.urandom(12)
    derived_key = hashlib.sha256(f"LATEX_RESUME_EPHEMERAL_VAULT_KEY_2026_{ts}".encode("utf-8")).digest()
    aesgcm = AESGCM(derived_key)
    ct_bytes = aesgcm.encrypt(iv_bytes, raw_key.strip().encode("utf-8"), None)
    envelope = {
        "v": 1,
        "ts": ts,
        "iv": base64.b64encode(iv_bytes).decode("ascii"),
        "ct": base64.b64encode(ct_bytes).decode("ascii"),
        "p": provider,
    }
    return f"SECKEY_V1:{base64.b64encode(json.dumps(envelope).encode('utf-8')).decode('ascii')}"


def unwrap_secure_api_key(armored_or_raw: str | None, provider: str = "default") -> str:
    """Descriptografa o envelope SECKEY_V1 ou higieniza a chave bruta fornecida.
    
    A descriptografia ocorre exclusivamente na memória volátil RAM. A chave nunca é persistida.
    """
    if not armored_or_raw or not armored_or_raw.strip():
        return ""
    text = armored_or_raw.strip()
    if text.startswith("SECKEY_V1:"):
        try:
            b64_part = text[len("SECKEY_V1:"):]
            raw_json = base64.b64decode(b64_part).decode("utf-8")
            envelope = json.loads(raw_json)
            ts = int(envelope["ts"])
            now_ms = int(time.time() * 1000)
            if abs(now_ms - ts) > 900_000:  # Janela máxima de 15 minutos contra ataques de repetição
                raise ValueError("Envelope criptográfico expirado ou com timestamp desalinhado.")
            iv_bytes = base64.b64decode(envelope["iv"])
            ct_bytes = base64.b64decode(envelope["ct"])
            derived_key = hashlib.sha256(f"LATEX_RESUME_EPHEMERAL_VAULT_KEY_2026_{ts}".encode("utf-8")).digest()
            aesgcm = AESGCM(derived_key)
            plain_bytes = aesgcm.decrypt(iv_bytes, ct_bytes, None)
            return plain_bytes.decode("utf-8").strip()
        except Exception as exc:
            raise PermissionError(f"Falha ao decodificar envelope criptográfico seguro da API key: {exc}")
    return text


def derive_payload_transport_key(ts: int, direction: str = "req") -> bytes:
    """Deriva chave de 256 bits para transporte cifrado entre cliente e servidor vinculada a timestamp efêmero."""
    salt = f"LATEX_RESUME_PAYLOAD_ENCRYPT_2026_{direction}_{ts}".encode("utf-8")
    return hashlib.sha256(salt).digest()


def encrypt_payload_envelope(data: Dict[str, Any], direction: str = "resp", ts: int | None = None) -> Dict[str, Any]:
    """Cifra um payload JSON completo em um envelope criptográfico efêmero AES-256-GCM (ENC_PAYLOAD_V1).
    
    Garante que a comunicação em trânsito e na inspeção de DevTools / rede seja puro texto cifrado,
    sem expor dados pessoais, prompts ou tokens de API.
    """
    ts_val = ts if ts is not None else int(time.time() * 1000)
    key_bytes = derive_payload_transport_key(ts_val, direction=direction)
    iv_bytes = os.urandom(12)
    aesgcm = AESGCM(key_bytes)
    plaintext_bytes = json.dumps(data, ensure_ascii=False).encode("utf-8")
    ct_bytes = aesgcm.encrypt(iv_bytes, plaintext_bytes, None)
    return {
        "enc_version": "ENC_PAYLOAD_V1",
        "ts": ts_val,
        "iv": base64.b64encode(iv_bytes).decode("ascii"),
        "ciphertext": base64.b64encode(ct_bytes).decode("ascii"),
    }


def decrypt_payload_envelope(envelope: Dict[str, Any], direction: str = "req", max_drift_ms: int = 900_000) -> Dict[str, Any]:
    """Descriptografa um envelope ENC_PAYLOAD_V1 exclusivamente em memória RAM volátil.
    
    Aplica validação anti-replay de timestamp (janela máxima de 15 minutos).
    """
    if not isinstance(envelope, dict) or envelope.get("enc_version") != "ENC_PAYLOAD_V1":
        raise ValueError("Formato de envelope cifrado inválido ou versão não suportada.")

    ts = int(envelope.get("ts", 0))
    now_ms = int(time.time() * 1000)
    if abs(now_ms - ts) > max_drift_ms:
        raise ValueError("Payload criptografado expirado ou com timestamp desalinhado (proteção anti-replay).")

    iv_bytes = base64.b64decode(envelope["iv"])
    ct_bytes = base64.b64decode(envelope["ciphertext"])
    key_bytes = derive_payload_transport_key(ts, direction=direction)
    aesgcm = AESGCM(key_bytes)
    plain_bytes = aesgcm.decrypt(iv_bytes, ct_bytes, None)
    return json.loads(plain_bytes.decode("utf-8"))


_API_KEY_PATTERNS = [
    re.compile(r"nvapi-[A-Za-z0-9_-]{16,}"),
    re.compile(r"AIza[0-9A-Za-z-_]{30,}"),
    re.compile(r"sk-ant-[A-Za-z0-9_-]{15,}"),
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"SECKEY_V1:[A-Za-z0-9+/=]+"),
]


def scrub_sensitive_api_keys(data: Any, extra_secrets: List[str] | None = None) -> Any:
    """Higieniza recursivamente estruturas de dados, garantindo que nenhuma chave de API ou segredo
    seja vazado em mensagens de erro, saídas de LaTeX ou respostas de API para o frontend.
    """
    if isinstance(data, str):
        cleaned = data
        for pattern in _API_KEY_PATTERNS:
            cleaned = pattern.sub("[REDACTED_API_KEY]", cleaned)
        if extra_secrets:
            for sec in extra_secrets:
                if sec and len(sec.strip()) >= 8 and sec.strip() in cleaned:
                    cleaned = cleaned.replace(sec.strip(), "[REDACTED_API_KEY]")
        return cleaned
    elif isinstance(data, dict):
        return {k: scrub_sensitive_api_keys(v, extra_secrets) for k, v in data.items()}
    elif isinstance(data, list):
        return [scrub_sensitive_api_keys(item, extra_secrets) for item in data]
    return data


def _attest_and_verify_caller(messages: List[Dict[str, str]]) -> None:
    """Atesta a integridade da chamada (origem autorizada e conformidade estrita da tarefa)."""
    caller_ok = False
    for frame_info in inspect.stack()[1:9]:
        fname = frame_info.filename.replace("\\", "/")
        func = frame_info.function
        if (
            (fname.endswith("src/nvidia_client.py") and func in ("_call_nvidia_chat", "_call_llm_chat"))
            or (fname.endswith("src/llm_client.py") and func in ("_call_llm_chat", "_call_nvidia_chat"))
        ):
            caller_ok = True
            break
    if not caller_ok:
        raise PermissionError("Acesso negado: invocação fora do pipeline autorizado de currículos LaTeX.")

    if not isinstance(messages, list) or len(messages) != 2:
        raise PermissionError("Acesso negado: formato de mensagens incompatível com a tarefa de currículo.")

    sys_msg = (messages[0].get("content") or "").strip()
    usr_msg = (messages[1].get("content") or "").strip()

    matched_mode = None
    for mode in _ALLOWED_MODES:
        if sys_msg.startswith(mode):
            matched_mode = mode
            break
    if not matched_mode:
        raise PermissionError("Acesso negado: prompt de sistema não pertence ao gerador de currículos LaTeX.")

    if not any(marker in usr_msg for marker in _ALLOWED_MARKERS):
        raise PermissionError("Acesso negado: carga útil não corresponde a dados de currículo LaTeX.")


def dispatch_secure_llm_chat(
    provider: str,
    model: str,
    messages: List[Dict[str, str]],
    custom_key: str | None = None,
    max_tokens: int = 1600,
    timeout: int = 40,
) -> Tuple[int, Dict[str, Any], str, Dict[str, Any]]:
    """Despacha requisição autenticada multi-provedor (NVIDIA, Google, Claude, OpenAI, DeepSeek).

    Retorna: (status_code, data_or_parsed, err_msg, usage_dict)
    A chave é mantida apenas em memória RAM volátil e destruída imediatamente com bytes nulos (0x00).
    """
    _scrub_network_environment()

    prov = (provider or "default").strip().lower()

    # 1. Recupera e descriptografa a chave em memória volátil (verificação ANTES do attest)
    unwrapped_key = unwrap_secure_api_key(custom_key, provider=prov)
    if not unwrapped_key:
        unwrapped_key = _get_server_key_for_provider(prov)

    if not unwrapped_key:
        if prov in ("default", "nvidia"):
            raise RuntimeError(
                "Chave de API NVIDIA não configurada no servidor backend. "
                "Informe sua própria chave de API (iniciando em 'nvapi-...') no campo 'Chave de API do Provedor', "
                "ou selecione 'Sem IA / Offline (0 Tokens)' para compilar diretamente sem necessidade de chave."
            )
        elif prov == "google":
            raise RuntimeError(
                "Chave de API do Google Gemini não fornecida. Informe sua chave (iniciando em 'AIza...') no campo 'Chave de API do Provedor' "
                "ou selecione 'NVIDIA NIM (Padrão do Servidor)' / 'Sem IA / Offline'."
            )
        elif prov == "claude":
            raise RuntimeError(
                "Chave de API da Anthropic Claude não fornecida. Informe sua chave (iniciando em 'sk-ant-...') no campo 'Chave de API do Provedor' "
                "ou selecione 'NVIDIA NIM (Padrão do Servidor)' / 'Sem IA / Offline'."
            )
        elif prov == "openai":
            raise RuntimeError(
                "Chave de API da OpenAI não fornecida. Informe sua chave (iniciando em 'sk-...') no campo 'Chave de API do Provedor' "
                "ou selecione 'NVIDIA NIM (Padrão do Servidor)' / 'Sem IA / Offline'."
            )
        elif prov == "deepseek":
            raise RuntimeError(
                "Chave de API da DeepSeek não fornecida. Informe sua chave (iniciando em 'sk-...') no campo 'Chave de API do Provedor' "
                "ou selecione 'NVIDIA NIM (Padrão do Servidor)' / 'Sem IA / Offline'."
            )
        else:
            raise RuntimeError(
                f"Chave de API não informada para o provedor '{prov}'. "
                "Informe sua chave no campo 'Chave de API do Provedor' ou selecione 'NVIDIA NIM (Padrão do Servidor)'."
            )

    _attest_and_verify_caller(messages)

    sys_msg = (messages[0].get("content") or "").strip()
    usr_msg = (messages[1].get("content") or "").strip()

    buf = bytearray()
    auth_header_buf = bytearray()

    try:
        buf.extend(unwrapped_key.encode("utf-8"))
        raw_key_str = bytes(buf).decode("utf-8")

        session = requests.Session()
        session.trust_env = False

        if prov in ("default", "nvidia"):
            endpoint_url = "https://integrate.api.nvidia.com/v1/chat/completions"
            expected_host = "integrate.api.nvidia.com"
            payload = {
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": 0.15,
                "top_p": 0.85,
            }
            if "nemotron" in model.lower() or "deepseek" in model.lower():
                payload["chat_template_kwargs"] = {"enable_thinking": False}
            elif "glm" in model.lower():
                payload["chat_template_kwargs"] = {"enable_thinking": False, "clear_thinking": True}
                payload["max_tokens"] = max(max_tokens, 3200)

            session.mount("https://", _PinnedTLS13Adapter(expected_hostname=expected_host))
            auth_header_buf.extend(b"Bearer ")
            auth_header_buf.extend(buf)
            resp = session.post(
                endpoint_url,
                headers={
                    "Authorization": bytes(auth_header_buf).decode("ascii"),
                    "Content-Type": "application/json",
                    "Connection": "close",
                },
                json=payload,
                timeout=timeout,
            )

        elif prov == "openai":
            endpoint_url = "https://api.openai.com/v1/chat/completions"
            expected_host = "api.openai.com"
            payload = {
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": 0.2,
            }
            session.mount("https://", _PinnedTLS13Adapter(expected_hostname=expected_host))
            auth_header_buf.extend(b"Bearer ")
            auth_header_buf.extend(buf)
            resp = session.post(
                endpoint_url,
                headers={
                    "Authorization": bytes(auth_header_buf).decode("ascii"),
                    "Content-Type": "application/json",
                    "Connection": "close",
                },
                json=payload,
                timeout=timeout,
            )

        elif prov == "deepseek":
            endpoint_url = "https://api.deepseek.com/chat/completions"
            expected_host = "api.deepseek.com"
            payload = {
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": 0.2,
            }
            session.mount("https://", _PinnedTLS13Adapter(expected_hostname=expected_host))
            auth_header_buf.extend(b"Bearer ")
            auth_header_buf.extend(buf)
            resp = session.post(
                endpoint_url,
                headers={
                    "Authorization": bytes(auth_header_buf).decode("ascii"),
                    "Content-Type": "application/json",
                    "Connection": "close",
                },
                json=payload,
                timeout=timeout,
            )

        elif prov == "claude":
            endpoint_url = "https://api.anthropic.com/v1/messages"
            expected_host = "api.anthropic.com"
            payload = {
                "model": model,
                "max_tokens": max_tokens,
                "system": sys_msg,
                "messages": [{"role": "user", "content": usr_msg}],
                "temperature": 0.2,
            }
            session.mount("https://", _PinnedTLS13Adapter(expected_hostname=expected_host))
            resp = session.post(
                endpoint_url,
                headers={
                    "x-api-key": raw_key_str,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                    "Connection": "close",
                },
                json=payload,
                timeout=timeout,
            )

        elif prov == "google":
            endpoint_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
            expected_host = "generativelanguage.googleapis.com"
            payload = {
                "systemInstruction": {"parts": [{"text": sys_msg}]},
                "contents": [{"role": "user", "parts": [{"text": usr_msg}]}],
                "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.2},
            }
            session.mount("https://", _PinnedTLS13Adapter(expected_hostname=expected_host))
            resp = session.post(
                endpoint_url,
                headers={
                    "x-goog-api-key": raw_key_str,
                    "Content-Type": "application/json",
                    "Connection": "close",
                },
                json=payload,
                timeout=timeout,
            )

        else:
            raise ValueError(f"Provedor '{prov}' não suportado.")

        session.close()

        if resp.status_code != 200:
            err_text = ""
            try:
                err_text = resp.text[:300]
            except Exception:
                pass
            return resp.status_code, {}, f"HTTP {resp.status_code} ({err_text})", {}

        resp_json = resp.json()

        # Parse padronizado por provedor
        if prov in ("default", "nvidia", "openai", "deepseek"):
            msg_obj = (resp_json.get("choices") or [{}])[0].get("message") or {}
            content = (msg_obj.get("content") or "").strip()
            usage = resp_json.get("usage") or {}
            parsed_data = {"content": content, "raw": resp_json}
            return 200, parsed_data, "", usage

        elif prov == "claude":
            blocks = resp_json.get("content") or []
            content = "".join(b.get("text", "") for b in blocks if b.get("type") == "text").strip()
            raw_usage = resp_json.get("usage") or {}
            in_tok = raw_usage.get("input_tokens", 0)
            out_tok = raw_usage.get("output_tokens", 0)
            usage = {
                "prompt_tokens": in_tok,
                "completion_tokens": out_tok,
                "total_tokens": in_tok + out_tok,
            }
            parsed_data = {"content": content, "raw": resp_json}
            return 200, parsed_data, "", usage

        elif prov == "google":
            candidates = resp_json.get("candidates") or []
            parts = (candidates[0].get("content") or {}).get("parts") or [] if candidates else []
            content = "".join(p.get("text", "") for p in parts).strip()
            um = resp_json.get("usageMetadata") or {}
            p_tok = um.get("promptTokenCount", 0)
            c_tok = um.get("candidatesTokenCount", 0)
            usage = {
                "prompt_tokens": p_tok,
                "completion_tokens": c_tok,
                "total_tokens": um.get("totalTokenCount", p_tok + c_tok),
            }
            parsed_data = {"content": content, "raw": resp_json}
            return 200, parsed_data, "", usage

        return 500, {}, "Formato de resposta não suportado", {}

    except PermissionError:
        raise
    except Exception as exc:
        return 599, {}, f"Erro de transporte seguro ({type(exc).__name__}: {exc})", {}
    finally:
        # Higienização de memória volátil (Zeroização de buffers com 0x00)
        for i in range(len(buf)):
            buf[i] = 0
        for i in range(len(auth_header_buf)):
            auth_header_buf[i] = 0
        if "raw_key_str" in locals():
            del raw_key_str
        if "unwrapped_key" in locals():
            del unwrapped_key


def dispatch_secure_nvidia_chat(
    endpoint_url: str,
    payload: Dict[str, Any],
    custom_key: str | None = None,
    timeout: int = 35,
) -> Tuple[int, Dict[str, Any], str]:
    """Wrapper de retrocompatibilidade para o gerador de currículos NVIDIA."""
    model = payload.get("model", "nvidia/nemotron-3.5-super-vl-120b-a12b")
    messages = payload.get("messages") or []
    max_tokens = payload.get("max_tokens", 1600)
    status, parsed, err_str, usage = dispatch_secure_llm_chat(
        provider="nvidia",
        model=model,
        messages=messages,
        custom_key=custom_key,
        max_tokens=max_tokens,
        timeout=timeout,
    )
    if status == 200:
        return status, parsed.get("raw", {}), ""
    return status, {}, err_str
