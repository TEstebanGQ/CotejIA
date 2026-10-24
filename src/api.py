"""Servidor FastAPI de CotejAI (S2): Endpoints REST para el Frontend, Herramientas Reales y Métricas."""
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .agent import (
    DATASETS,
    cargar_caso,
    conversar,
    ejecutar_caso,
    formatear_resumen_caso,
    listar_casos,
    tiene_llave_configurada,
    tool_cotejar_caso,
    veredicto_escalado,
)
from .db import (
    guardar_resultado_caso,
    init_db,
    listar_acciones_db,
    obtener_casos_db,
    obtener_metricas_db,
)
from .external_tools import (
    CIRCUIT_BREAKER_SAT,
    consultar_sat_en_vivo,
    consultar_tipo_cambio_real,
    enviar_alerta_reclamo_real,
    listar_divisas_real,
)
from .vision import leer_remision_imagen

ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = ROOT / "web"

app = FastAPI(
    title="CotejAI API — Auditor Autónomo de Cuentas por Pagar (S2)",
    description="Backend FastAPI conectado a Grok 4.6 (Text & Vision), SAT SOAP + Lista 69-B, ExchangeRate-API y PostgreSQL/SQLite WAL.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    mensaje: str
    historial: list[dict[str, Any]] | None = None


class FXRequest(BaseModel):
    moneda: str = "USD"
    tipo_cambio_cfdi: float | str | None = None


class ReclamoRequest(BaseModel):
    monto_nota_credito_mxn: str | float | None = None
    motivo: str | None = None
    llave_idempotencia: str | None = None


@app.get("/api/health")
def api_health():
    motor = init_db()
    return {
        "ok": True,
        "servicio": "CotejAI Backend S2",
        "motor_db": motor,
        "grok_conectado": tiene_llave_configurada(),
        "modelo": "grok-4.6",
        "circuit_breaker_sat": CIRCUIT_BREAKER_SAT.estado_dict(),
    }


@app.get("/api/metrics")
def api_metrics():
    m = obtener_metricas_db()
    m["circuit_breaker_sat"] = CIRCUIT_BREAKER_SAT.estado_dict()
    m["grok_conectado"] = tiene_llave_configurada()
    return m


@app.get("/api/cases")
def api_list_cases():
    guardados = obtener_casos_db()
    resultado = []
    for cid in listar_casos():
        oc, rem, cfdi = cargar_caso(cid)
        cotejo = tool_cotejar_caso(cid)
        db_row = guardados.get(cid)
        tiene_img = (DATASETS / cid / "remision.png").exists()
        resultado.append({
            "case_id": cid,
            "proveedor_rfc": cfdi.get("rfc_emisor"),
            "uuid": cfdi.get("uuid"),
            "moneda": cfdi.get("moneda", "MXN"),
            "tipo_cambio": str(cfdi.get("tipo_cambio", "1")),
            "tiene_imagen_remision": tiene_img,
            "imagen_url": f"/api/cases/{cid}/image" if tiene_img else None,
            "total_cfdi_mxn": cotejo["total_cfdi_mxn"],
            "monto_a_pagar_mxn": cotejo["monto_a_pagar_mxn"],
            "fuga_detectada_mxn": cotejo["fuga_detectada_mxn"],
            "codigos_calculados": cotejo["codigos"],
            "auditado_en_db": db_row is not None,
            "estado_final": db_row["estado_final"] if db_row else None,
            "version_db": db_row["version"] if db_row else 0,
            "herramientas_usadas": db_row["herramientas"] if db_row else [],
            "resumen": db_row["resumen"] if db_row else None,
            "actualizado_en": db_row["actualizado_en"] if db_row else None,
        })
    return {"ok": True, "total": len(resultado), "casos": resultado}


@app.get("/api/cases/{case_id}")
def api_case_detail(case_id: str):
    cid = case_id.upper()
    if cid not in listar_casos():
        raise HTTPException(status_code=404, detail=f"El caso {cid} no existe en datasets/")
    oc, rem, cfdi = cargar_caso(cid)
    cotejo = tool_cotejar_caso(cid)
    guardados = obtener_casos_db()
    tiene_img = (DATASETS / cid / "remision.png").exists()
    cfdi_serializable = {
        **cfdi,
        "tipo_cambio": str(cfdi.get("tipo_cambio", "1")),
        "subtotal": str(cfdi["subtotal"]),
        "descuento": str(cfdi["descuento"]),
        "total": str(cfdi["total"]),
        "conceptos": [
            {
                **c,
                "cantidad": str(c["cantidad"]),
                "valor_unitario": str(c["valor_unitario"]),
                "importe": str(c["importe"]),
                "descuento": str(c["descuento"]),
                "traslados": [
                    {**t, "tasa": str(t["tasa"]), "base": str(t["base"]), "importe": str(t["importe"])}
                    for t in c["traslados"]
                ],
                "retenciones": [
                    {**r, "tasa": str(r["tasa"]), "base": str(r["base"]), "importe": str(r["importe"])}
                    for r in c["retenciones"]
                ],
            }
            for c in cfdi["conceptos"]
        ],
    }
    return {
        "ok": True,
        "case_id": cid,
        "tiene_imagen_remision": tiene_img,
        "imagen_url": f"/api/cases/{cid}/image" if tiene_img else None,
        "oc": oc,
        "remision": rem,
        "cfdi": cfdi_serializable,
        "cotejo": cotejo,
        "registro_db": guardados.get(cid),
        "acciones_idempotentes": listar_acciones_db(cid),
        "reporte_texto": formatear_resumen_caso(cid, veredicto=guardados.get(cid), cotejo=cotejo),
    }


@app.get("/api/cases/{case_id}/image")
def api_case_image(case_id: str):
    cid = case_id.upper()
    ruta = DATASETS / cid / "remision.png"
    if not ruta.exists():
        raise HTTPException(status_code=404, detail=f"El caso {cid} no tiene imagen remision.png")
    return FileResponse(str(ruta), media_type="image/png")


@app.post("/api/audit/{case_id}")
def api_audit_case(case_id: str):
    cid = case_id.upper()
    if cid not in listar_casos():
        raise HTTPException(status_code=404, detail=f"El caso {cid} no existe en datasets/")

    cotejo = tool_cotejar_caso(cid)
    if tiene_llave_configurada():
        try:
            r = ejecutar_caso(cid)
            return {"ok": True, "modo": "grok-4.6", **r}
        except Exception as exc:
            veredicto_fb = veredicto_escalado(cid, f"Contingencia en gateway: {type(exc).__name__}", cotejo)
            guardar_resultado_caso(cid, veredicto_fb, total_cfdi_mxn=cotejo["total_cfdi_mxn"], herramientas=["cotejar_caso"])
            return {"ok": True, "modo": "fallback_determinista", "veredicto": veredicto_fb, "cotejo": cotejo}

    # Modo local determinista si no hay RETO_KEY
    cods = set(cotejo["codigos"])
    fuga = float(cotejo["fuga_detectada_mxn"])
    if cods == {"MATCH_OK"}:
        est = "APROBADO"
        res_txt = "Cotejo exacto entre OC, remisión y CFDI."
    elif cods <= {"QTY_SHORT", "PRICE_UP"} and fuga <= 5000.0:
        est = "EN_RECLAMO"
        res_txt = f"Se retienen ${fuga:,.2f} MXN y se solicita nota de crédito con llave de idempotencia."
        enviar_alerta_reclamo_real(cid, cotejo.get("rfc_emisor") or "AAA010101AAA", cotejo.get("uuid") or "", cotejo["fuga_detectada_mxn"], res_txt)
    else:
        est = "ESCALADO"
        res_txt = f"Escalado a revisión humana por códigos: {', '.join(cotejo['codigos'])}."
    veredicto_local = {
        "case_id": cid,
        "estado_final": est,
        "codigos": cotejo["codigos"],
        "fuga_detectada_mxn": cotejo["fuga_detectada_mxn"],
        "monto_a_pagar_mxn": cotejo["monto_a_pagar_mxn"],
        "resumen": res_txt,
    }
    guardar_resultado_caso(cid, veredicto_local, total_cfdi_mxn=cotejo["total_cfdi_mxn"], herramientas=["cotejar_caso"])
    return {"ok": True, "modo": "determinista_local", "veredicto": veredicto_local, "cotejo": cotejo}


@app.post("/api/audit-all")
def api_audit_all():
    resultados = []
    for cid in listar_casos():
        resultados.append(api_audit_case(cid))
    return {
        "ok": True,
        "total_procesados": len(resultados),
        "resultados": resultados,
        "metricas": api_metrics(),
    }


@app.post("/api/tools/vision/{case_id}")
def api_tool_vision(case_id: str):
    return leer_remision_imagen(case_id.upper())


@app.post("/api/tools/fx")
def api_tool_fx(req: FXRequest):
    return consultar_tipo_cambio_real(moneda=req.moneda, tipo_cambio_cfdi=req.tipo_cambio_cfdi)


@app.get("/api/currencies")
def api_currencies():
    return listar_divisas_real()


@app.post("/api/tools/sat/{case_id}")
def api_tool_sat(case_id: str):
    cid = case_id.upper()
    if cid not in listar_casos():
        raise HTTPException(status_code=404, detail=f"El caso {cid} no existe")
    oc, _, cfdi = cargar_caso(cid)
    return consultar_sat_en_vivo(
        case_id=cid,
        uuid=cfdi.get("uuid") or "",
        rfc_emisor=cfdi.get("rfc_emisor") or "",
        rfc_receptor=cfdi.get("rfc_receptor") or "",
        total=str(cfdi.get("total") or "0.00"),
        simular_caida_sat=bool(oc.get("simular_caida_sat", False)),
    )


@app.post("/api/tools/reclamo/{case_id}")
def api_tool_reclamo(case_id: str, req: ReclamoRequest | None = None):
    cid = case_id.upper()
    if cid not in listar_casos():
        raise HTTPException(status_code=404, detail=f"El caso {cid} no existe")
    cotejo = tool_cotejar_caso(cid)
    monto = (req.monto_nota_credito_mxn if req and req.monto_nota_credito_mxn else None) or cotejo["fuga_detectada_mxn"]
    motivo = (req.motivo if req and req.motivo else None) or f"Faltante/sobreprecio en expediente {cid}"
    llave = req.llave_idempotencia if req else None
    return enviar_alerta_reclamo_real(
        case_id=cid,
        rfc_proveedor=cotejo.get("rfc_emisor") or "AAA010101AAA",
        uuid_factura=cotejo.get("uuid") or "",
        monto_nota_credito_mxn=monto,
        motivo=motivo,
        llave_idempotencia=llave,
    )


@app.post("/api/chat")
def api_chat(req: ChatRequest):
    if tiene_llave_configurada():
        resp, hist, uso = conversar(req.mensaje, historial=req.historial)
        return {"ok": True, "respuesta": resp, "historial": hist, "uso": uso}
    return {
        "ok": True,
        "respuesta": "Modo local activo: configura RETO_KEY en .env para conversar con Grok 4.6 en vivo.",
        "historial": req.historial or [],
        "uso": {"prompt_tokens": 0, "completion_tokens": 0},
    }


if WEB_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
def serve_index():
    index_file = WEB_DIR / "index.html"
    if index_file.exists():
        return index_file.read_text(encoding="utf-8")
    return "<h1>CotejAI API Activa</h1><p>Visita <a href='/docs'>/docs</a> para ver Swagger UI.</p>"
