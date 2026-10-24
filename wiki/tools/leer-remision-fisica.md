---
title: "Herramienta: leer_remision_fisica"
type: tool
tags: [herramienta, multimodal, vision, remisiones, s2]
created: 2026-10-24
updated: 2026-10-24
status: stable
sources:
  - "[[raw/spec-s2-herramientas-resiliencia]]"
---

# Herramienta: `leer_remision_fisica`

## Propósito
Extraer información tabular de mercancía recibida, firmas y sellos oficiales de almacén a partir de fotografías (JPG/PNG) o documentos PDF escaneados (renderizados a 200 dpi).

## Firma Técnica
```python
def leer_remision_fisica(case_id: str, ruta_imagen: str) -> dict:
    """Extrae las líneas recibidas, sellos y firmas desde la imagen de remisión usando Grok Vision."""
```

### Parámetros de Entrada
```json
{
  "case_id": "OC-004",
  "ruta_imagen": "datasets/OC-004/remision_foto.png"
}
```

### Esquema de Salida
```json
{
  "folio_remision": "REM-8821",
  "fecha_entrega": "2026-10-15",
  "tiene_sello_almacen": true,
  "tiene_firma_recepcion": true,
  "lineas": [
    {
      "sku": "TORN-001",
      "descripcion": "Tornillo hexagonal 1/2",
      "cantidad_recibida": "80",
      "confianza": 0.95
    }
  ],
  "observaciones_manuales": "Se reciben 80 pzas; faltaron 20 por merma de transporte"
}
```

## Reglas de Ejecución y Resiliencia
1. **Regla Anti-Alucinación:** Si un trazo numérico o texto es ilegible, el prompt ordena estrictamente devolver `null` y reducir `confianza`. Nunca inventar una cantidad.
2. **Umbral de Confianza (< 0.85):** Si alguna línea tiene confianza $< 0.85$, se emite el código `RECEIPT_UNREADABLE`. Se genera una solicitud de re-fotografiado; al segundo fallo consecutivo, el caso se escala a inspección humana.
3. **Certificación de Almacén:** Si `tiene_sello_almacen` o `tiene_firma_recepcion` es `false`, se genera advertencia documental para condicionar la autorización de pago.

## Páginas Relacionadas
- [[grok-vision]]
- [[three-way-matching]]
- [[resilience-matrix]]
