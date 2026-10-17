"""Pruebas del modo interactivo y conversacional de CotejAI."""
from types import SimpleNamespace
from unittest.mock import patch

from src import agent
from src.agent import conversar, formatear_resumen_caso, tiene_llave_configurada
from main import _responder_localmente


def test_formatear_resumen_caso():
    resumen_001 = formatear_resumen_caso("OC-001")
    assert "OC-001" in resumen_001
    assert "MATCH_OK" in resumen_001
    assert "6,090.00" in resumen_001

    resumen_002 = formatear_resumen_caso("OC-002")
    assert "OC-002" in resumen_002
    assert "290.00" in resumen_002
    assert "TORN-001" in resumen_002


def test_responder_localmente_explicacion():
    resp = _responder_localmente("¿Por qué retuviste el pago?", "OC-002")
    assert "290.00" in resp
    assert "TORN-001" in resp
    assert "nota de crédito" in resp

    resp_iva = _responder_localmente("¿Cómo manejas el IVA?", None)
    assert "16%" in resp_iva
    assert "8%" in resp_iva


def test_tiene_llave_configurada(monkeypatch):
    monkeypatch.setenv("RETO_KEY", "pk_xxxxxxxxxx")
    assert tiene_llave_configurada() is False

    monkeypatch.setenv("RETO_KEY", "")
    assert tiene_llave_configurada() is False

    monkeypatch.setenv("RETO_KEY", "sk_real_secret_token_123")
    assert tiene_llave_configurada() is True


def test_conversar_con_grok_falso():
    class GrokChatFalso:
        def __init__(self):
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

        def _create(self, **kw):
            msg = SimpleNamespace(
                content="Hola, analicé el caso y todo está en orden.",
                tool_calls=None,
                model_dump=lambda **_: {"role": "assistant", "content": "Hola, analicé el caso y todo está en orden."}
            )
            return SimpleNamespace(
                choices=[SimpleNamespace(message=msg)],
                usage=SimpleNamespace(prompt_tokens=15, completion_tokens=10)
            )

    grok = GrokChatFalso()
    resp, historial, uso = conversar("Hola agente", client=grok)
    assert "Hola, analicé el caso" in resp
    assert uso["prompt_tokens"] == 15
    assert len(historial) >= 2
