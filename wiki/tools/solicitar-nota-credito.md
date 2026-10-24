---
title: "Herramienta: solicitar_nota_credito"
type: tool
tags: [herramienta, notificaciones, accion-externa, idempotencia, s2]
created: 2026-10-24
updated: 2026-10-24
status: stable
sources:
  - "[[raw/spec-s2-herramientas-resiliencia]]"
---

# Herramienta: `solicitar_nota_credito`

## Propósito
Generar y transmitir la reclamación comercial formal al proveedor cuando se detecta un faltante físico o un sobreprecio en la factura, dentro de los límites de autonomía aprobados por la política corporativa.

## Firma Técnica
```python
def solicitar_nota_credito(
    case_id: str,
    rfc_proveedor: str,
    uuid_factura: str,
    monto_nota_credito_mxn: float,
    motivo: str,
    llave_idempotencia: str
) -> dict:
    """Envía la solicitud de compensación formal al proveedor asegurando idempotencia transaccional."""
```

### Parámetros de Entrada
```json
{
  "case_id": "OC-002",
  "rfc_proveedor": "AAA010101AAA",
  "uuid_factura": "4A12B34C-...",
  "monto_nota_credito_mxn": 290.00,
  "motivo": "Faltante de 20 piezas en SKU TORN-001",
  "llave_idempotencia": "OC-002:nota_credito:v1"
}
```

### Esquema de Salida
```json
{
  "estatus": "ENVIADO",
  "canal": "webhook_platica",
  "id_mensaje_externo": "msg_98234710",
  "monto_solicitado": 290.00,
  "ya_existia": false,
  "timestamp": "2026-10-24T09:40:12Z"
}
```

## Resiliencia y Control Idempotente
1. **Verificación Previa en SQLite:** La inserción previa en la tabla `actions` usando `llave_idempotencia` como clave primaria previene envíos duplicados ante reintentos del worker.
2. **Filtrado por `policy_gate`:** Si `monto_nota_credito_mxn > 5000.00`, la compuerta rechaza el despacho y transmuta la llamada en un `escalar_caso` con reporte Markdown para autorización ejecutiva.
3. **Respaldo ante Caídas:** Si la red exterior falla (502/503 de Platica o error SMTP), se reintenta con backoff exponencial sin duplicar el registro local.

## Páginas Relacionadas
- [[idempotency-engine]]
- [[policy-gate]]
- [[platica-platform]]
