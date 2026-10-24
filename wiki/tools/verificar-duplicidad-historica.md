---
title: "Herramienta: verificar_duplicidad_historica"
type: tool
tags: [herramienta, antifraude, doble-pago, sqlite, s2]
created: 2026-10-24
updated: 2026-10-24
status: stable
sources:
  - "[[raw/spec-s2-herramientas-resiliencia]]"
---

# Herramienta: `verificar_duplicidad_historica`

## Propósito
Prevenir el doble pago de una misma factura o el reprocesamiento accidental de CFDIs en un histórico móvil de 90 días.

## Firma Técnica
```python
def verificar_duplicidad_historica(
    uuid_factura: str,
    rfc_emisor: str,
    folio: str,
    total: float,
    case_id: str
) -> dict:
    """Verifica en SQLite si el UUID o la tripleta (RFC, Folio, Total) ya fue registrada o pagada."""
```

## Lógica de Detección
1. **Comprobación por UUID:** Búsqueda en `invoices_seen` por `uuid = ?`.
2. **Comprobación por Atributos:** Si el UUID cambia (por refacturación o sustitución indebida), se evalúa la coincidencia exacta de `(rfc_emisor, folio, total)`.
3. **Acción ante Duplicado:**
   - Si se encuentra coincidencia, retorna `es_duplicada: true` y genera el código `DUPLICATE`.
   - Congela el proceso de auditoría y bloquea la generación de cualquier orden de pago.

## Páginas Relacionadas
- [[sqlite-wal]]
- [[three-way-matching]]
- [[resilience-matrix]]
