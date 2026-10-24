---
title: "Herramienta: reconciliar_sku_ambiguo"
type: tool
tags: [herramienta, skus, reconciliacion-semantica, cache, grok, s2]
created: 2026-10-24
updated: 2026-10-24
status: stable
sources:
  - "[[raw/spec-s2-herramientas-resiliencia]]"
---

# Herramienta: `reconciliar_sku_ambiguo`

## Propósito
Resolver discrepancias léxicas y factores de empaque entre los códigos internos de la Orden de Compra y las descripciones libres que colocan los proveedores en el CFDI.

## Firma Técnica
```python
def reconciliar_sku_ambiguo(
    rfc_proveedor: str,
    descripcion_cfdi: str,
    unidad_cfdi: str,
    lista_candidatos_oc: list[dict]
) -> dict:
    """Busca en caché local de alias o invoca a Grok para deducir mapeo y factor de conversión."""
```

## Flujo en Dos Niveles
1. **Nivel 1 (Caché $0.00$ ms, $0$ tokens):**
   - Consulta la tabla `sku_aliases` en SQLite:
     ```sql
     SELECT sku_oc, factor_conversion, confianza
     FROM sku_aliases
     WHERE rfc_proveedor = ? AND texto_cfdi = ?;
     ```
   - Si existe un match previamente confirmado o con alta confianza, se aplica de inmediato.
2. **Nivel 2 (Inferencia Semántica Grok):**
   - Si no está en caché, Grok analiza la semántica:
     - Ejemplo: *"Caja Cinta Canela 48mm x 100m Tuck (24 piezas)"* vs *"CT-CAN-TUCK-100"* con unidad *"Pieza"*.
   - Grok infiere: Match válido, similitud $0.96$, factor de conversión $24.0$.
   - El resultado se almacena en `sku_aliases` para reuso permanente.

## Páginas Relacionadas
- [[sqlite-wal]]
- [[three-way-matching]]
