"""
Testes automatizados para sincronização dinâmica e atualização automática da lista de modelos de IA.
"""

import json
from unittest.mock import patch, MagicMock
import pytest

from src.model_fetcher import (
    fetch_available_models_for_provider,
    _MODELS_CACHE,
)
from src._vault import encrypt_payload_envelope, decrypt_payload_envelope
from server import app


def test_fetch_available_models_default_nvidia():
    """Verifica se a busca de modelos da NVIDIA NIM retorna modelos válidos e prioriza o recomendado."""
    models = fetch_available_models_for_provider("default")
    assert isinstance(models, list)
    assert len(models) >= 1

    # O modelo recomendado deve ser o primeiro
    assert models[0]["id"] == "nvidia/nemotron-3.5-super-vl-120b-a12b"
    assert "Recomendado" in models[0]["name"]

    # Modelos de embedding, clip e detectores devem ser filtrados
    model_ids = [m["id"] for m in models]
    assert not any("embed" in mid for mid in model_ids)
    assert not any("clip" in mid for mid in model_ids)
    assert not any("detector" in mid for mid in model_ids)


def test_fetch_available_models_none_provider():
    """Verifica se o provedor 'none' retorna exclusivamente o motor determinístico."""
    models = fetch_available_models_for_provider("none")
    assert len(models) == 1
    assert models[0]["id"] == "none"
    assert "Determinístico" in models[0]["name"]


def test_fetch_available_models_google_fallback_and_live():
    """Verifica fallback para Google Gemini sem chave e parsing com resposta simulada."""
    # Sem chave: deve retornar os modelos curados
    fb_models = fetch_available_models_for_provider("google")
    assert len(fb_models) >= 2
    assert any("gemini-2.0-flash" in m["id"] for m in fb_models)

    # Com chave e resposta simulada
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "models": [
            {
                "name": "models/gemini-2.5-flash",
                "displayName": "Gemini 2.5 Flash",
                "supportedGenerationMethods": ["generateContent"],
            },
            {
                "name": "models/text-embedding-004",
                "displayName": "Text Embedding",
                "supportedGenerationMethods": ["embedContent"],
            },
        ]
    }
    with patch("requests.get", return_value=mock_resp):
        live = fetch_available_models_for_provider("google", api_key="fake_key_12345")
        assert len(live) == 1
        assert live[0]["id"] == "gemini-2.5-flash"


def test_fetch_available_models_openai_fallback():
    """Verifica retorno de modelos curados da OpenAI."""
    models = fetch_available_models_for_provider("openai")
    assert len(models) >= 2
    assert any("gpt-4o" in m["id"] for m in models)


def test_api_models_endpoint_get():
    """Verifica endpoint GET /api/models."""
    client = app.test_client()
    resp = client.get("/api/models?provider=default")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
    assert data["provider"] == "default"
    assert isinstance(data["models"], list)
    assert len(data["models"]) >= 1


def test_api_models_endpoint_post_encrypted():
    """Verifica endpoint POST /api/models com payload criptografado."""
    client = app.test_client()
    enc_req = encrypt_payload_envelope({"provider": "nvidia"}, direction="req")
    resp = client.post(
        "/api/models",
        json=enc_req,
        headers={"X-Encrypted-Payload": "1"},
    )
    assert resp.status_code == 200
    enc_resp = resp.get_json()
    assert enc_resp.get("enc_version") == "ENC_PAYLOAD_V1"
    dec_data = decrypt_payload_envelope(enc_resp, direction="resp")
    assert dec_data["status"] == "ok"
    assert dec_data["provider"] == "nvidia"
    assert len(dec_data["models"]) >= 1


def test_api_status_contains_updated_models():
    """Verifica se /api/status inclui os modelos do provedor default."""
    client = app.test_client()
    resp = client.get("/api/status")
    assert resp.status_code == 200
    data = resp.get_json()
    providers = data.get("providers", {})
    assert "default" in providers
    assert len(providers["default"].get("models", [])) >= 1
