---
title: "Herramienta: validar_sat_y_lista_69b"
type: tool
tags: [herramienta, sat, fiscal, 69b, soap, circuit-breaker, s2]
created: 2026-10-24
updated: 2026-10-24
status: stable
sources:
  - "[[raw/spec-s2-herramientas-resiliencia]]"
---

# Herramienta: `validar_sat_y_lista_69b`

## Propósito
Verificar en tiempo real la validez fiscal de la factura (estatus de timbrado en el SAT) y asegurar que el proveedor no esté catalogado como Empresa que Factura Operaciones Simuladas (EFOS / Lista 69-B).

## Firma Técnica
```python
def validar_sat_y_lista_69b(case_id: str, uuid_factura: str, rfc_emisor: str, rfc_receptor: str, total_factura: float) -> dict:
    """Verifica estatus del CFDI en el webservice SOAP del SAT y cruza el RFC emisor con la lista 69-B."""
```

### Parámetros de Entrada
```json
{
  "case_id": "OC-003",
  "uuid_factura": "4A12B34C-9999-4A12-B34C-1234567890AB",
  "rfc_emisor": "AAA010101AAA",
  "rfc_receptor": "COT260101XYZ",
  "total_factura": 5800.00
}
```

### Esquema de Salida
```json
{
  "estatus_sat": "Vigente",
  "es_cancelable": "Cancelable con aceptación",
  "en_lista_69b": false,
  "situacion_69b": null,
  "circuit_breaker_activo": false,
  "codigos_generados": []
}
```

## Resiliencia y Reglas de Negocio
1. **Circuit Breaker SAT:**
   - 3 timeouts seguidos (> 3s) o errores 5xx del servidor del SAT abren el circuito.
   - Retorna `estatus_sat: "NO_VERIFICADO"`, `circuit_breaker_activo: true` y añade el código `SAT_NO_VERIFICADO`.
   - El lote continúa sin bloquearse.
2. **Detección Lista 69-B:**
   - Si `rfc_emisor` figura en la lista definitiva de EFOS, devuelve `en_lista_69b: true`, genera `SUPPLIER_69B` y detiene cualquier flujo de pago.
3. **Factura Cancelada:**
   - Si el SAT responde `Cancelado`, genera `CFDI_CANCELLED` y bloquea la operación.

## Páginas Relacionadas
- [[sat-soap-and-69b]]
- [[circuit-breaker-pattern]]
- [[policy-gate]]
