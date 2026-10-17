"""El agente con un Grok falso: compuerta del cierre, errores y caso equivocado."""
import json
from types import SimpleNamespace

import openai
import httpx

from src import agent


class Mensaje:
    def __init__(self, nombre, args, n):
        texto = args if isinstance(args, str) else json.dumps(args)
        self.tool_calls = [SimpleNamespace(id=f"call_{n}", function=SimpleNamespace(name=nombre, arguments=texto))]

    def model_dump(self, **_):
        return {"role": "assistant", "tool_calls": [
            {"id": tc.id, "type": "function",
             "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
            for tc in self.tool_calls]}


class GrokFalso:
    """Devuelve las llamadas a herramientas del guion, en orden; un elemento Exception se lanza."""

    def __init__(self, guion):
        self.guion = list(guion)
        self.mensajes_recibidos = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kw):
        self.mensajes_recibidos.append(kw["messages"][-1])
        paso = self.guion.pop(0)
        if isinstance(paso, Exception):
            raise paso
        nombre, args = paso
        return SimpleNamespace(usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5),
                               choices=[SimpleNamespace(message=Mensaje(nombre, args, len(self.guion)))])


def cierre(case_id="OC-002", estado="EN_RECLAMO", codigos=("QTY_SHORT",), fuga="290.00", monto="5800.00"):
    return ("cerrar_caso", {"case_id": case_id, "estado_final": estado, "codigos": list(codigos),
                            "fuga_detectada_mxn": fuga, "monto_a_pagar_mxn": monto, "resumen": "ok"})


def ultimo_resultado(grok):
    return json.loads(grok.mensajes_recibidos[-1]["content"])


def test_flujo_normal():
    grok = GrokFalso([("cotejar_caso", {"case_id": "OC-002"}), cierre()])
    r = agent.ejecutar_caso("OC-002", client=grok)
    assert r["veredicto"]["estado_final"] == "EN_RECLAMO"
    assert r["uso"]["rechazos"] == 0


def test_grok_pide_otro_caso_se_coteja_el_correcto():
    grok = GrokFalso([("cotejar_caso", {"case_id": "OC-001"}), cierre()])
    r = agent.ejecutar_caso("OC-002", client=grok)
    assert r["veredicto"]["codigos"] == ["QTY_SHORT"]


def test_cerrar_sin_cotejar_se_rechaza():
    grok = GrokFalso([cierre(), ("cotejar_caso", {"case_id": "OC-002"}), cierre()])
    r = agent.ejecutar_caso("OC-002", client=grok)
    assert r["uso"]["rechazos"] == 1
    assert r["veredicto"]["estado_final"] == "EN_RECLAMO"


def test_aprobar_un_faltante_se_rechaza():
    grok = GrokFalso([("cotejar_caso", {"case_id": "OC-002"}), cierre(estado="APROBADO"), cierre()])
    r = agent.ejecutar_caso("OC-002", client=grok)
    assert r["uso"]["rechazos"] == 1
    assert r["veredicto"]["estado_final"] == "EN_RECLAMO"


def test_montos_alterados_se_rechazan():
    grok = GrokFalso([("cotejar_caso", {"case_id": "OC-002"}), cierre(monto="6090.00"), cierre()])
    r = agent.ejecutar_caso("OC-002", client=grok)
    assert r["uso"]["rechazos"] == 1
    assert r["veredicto"]["monto_a_pagar_mxn"] == "5800.00"


def test_codigos_alterados_se_rechazan():
    grok = GrokFalso([("cotejar_caso", {"case_id": "OC-002"}), cierre(codigos=["MATCH_OK"]), cierre()])
    r = agent.ejecutar_caso("OC-002", client=grok)
    assert r["uso"]["rechazos"] == 1


def test_argumentos_json_invalidos_vuelven_a_grok():
    grok = GrokFalso([("cotejar_caso", "{no es json"), ("cotejar_caso", {"case_id": "OC-002"}), cierre()])
    r = agent.ejecutar_caso("OC-002", client=grok)
    assert r["veredicto"]["estado_final"] == "EN_RECLAMO"
    assert ultimo_resultado(grok)["ok"] is True


def test_veredicto_con_esquema_invalido_vuelve_a_grok():
    malo = ("cerrar_caso", {"case_id": "OC-002", "estado_final": "PAGAR"})
    grok = GrokFalso([("cotejar_caso", {"case_id": "OC-002"}), malo, cierre()])
    r = agent.ejecutar_caso("OC-002", client=grok)
    assert r["veredicto"]["estado_final"] == "EN_RECLAMO"


def test_pasos_agotados_escala_con_esquema_completo():
    grok = GrokFalso([("cotejar_caso", {"case_id": "OC-002"})] * agent.MAX_PASOS)
    r = agent.ejecutar_caso("OC-002", client=grok)
    v = r["veredicto"]
    assert v["estado_final"] == "ESCALADO"
    assert v["monto_a_pagar_mxn"] == "5800.00" and v["codigos"] == ["QTY_SHORT"]


def test_caso_que_no_se_puede_cotejar_escala_sin_gastar_pasos():
    grok = GrokFalso([("cotejar_caso", {"case_id": "X"})])
    r = agent.ejecutar_caso("NO-EXISTE", client=grok)
    assert r["veredicto"]["estado_final"] == "ESCALADO"
    assert r["uso"]["llamadas"] == 1


def test_error_transitorio_del_gateway_se_reintenta(monkeypatch):
    monkeypatch.setattr(agent.llamar_grok.retry, "wait", lambda *_: 0)
    req = httpx.Request("POST", "https://api.reto.pltk.mx/v1/chat/completions")
    grok = GrokFalso([openai.APIConnectionError(request=req),
                      ("cotejar_caso", {"case_id": "OC-002"}), cierre()])
    r = agent.ejecutar_caso("OC-002", client=grok)
    assert r["veredicto"]["estado_final"] == "EN_RECLAMO"


def test_listar_casos_ignora_carpetas_incompletas():
    assert agent.listar_casos() == ["OC-001", "OC-002", "OC-003"]
