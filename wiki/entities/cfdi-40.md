---
title: "CFDI 4.0 & Estructura Fiscal Mexicana"
type: entity
tags: [cfdi, xml, sat, impuestos, iva, ieps]
created: 2026-10-24
updated: 2026-10-24
status: stable
sources:
  - "docs/00-framework.md"
  - "CotejAI_guia_implementacion.md"
---

# CFDI 4.0 & Estructura Fiscal Mexicana

## Descripción
El Comprobante Fiscal Digital por Internet versión 4.0 (CFDI 4.0) es el formato XML estándar oficial en México. CotejAI extrae y valida los nodos críticos para el cotejo tripartito:
- **`cfdi:Comprobante`**: Folio, Serie, Fecha, Moneda, TipoDeComprobante (`I`=Ingreso, `E`=Egreso), SubTotal, Total.
- **`cfdi:Emisor`**: RFC, Nombre, RegimenFiscal.
- **`cfdi:Receptor`**: RFC, UsoCFDI, DomicilioFiscalReceptor.
- **`cfdi:Conceptos / cfdi:Concepto`**: ClaveProdServ, NoIdentificacion (SKU del proveedor), Descripcion, Cantidad, ClaveUnidad, ValorUnitario, Importe, Descuento.
- **`cfdi:Impuestos`**: Traslados (IVA 16%, 8% fronterizo, 0%, Exento, IEPS) y Retenciones.
- **`tfd:TimbreFiscalDigital`**: UUID (Folio Fiscal único de 36 caracteres), SelloCFD, FechaTimbrado.

## Reglas de Negocio en CotejAI
1. **Validación de Timbrado:** Factura sin nodo `TimbreFiscalDigital` es inválida y rechazada.
2. **Impuestos a Nivel Concepto:** El total de impuestos trasladados debe cuadrar exactamente con el cálculo matemático por línea; diferencias originan `TAX_MISMATCH`.
3. **Mapeo de SKUs:** `NoIdentificacion` suele no coincidir con el SKU interno de la Orden de Compra, requiriendo conciliación semántica.

## Páginas Relacionadas
- [[three-way-matching]]
- [[validar-sat-y-lista-69b]]
- [[reconciliar-sku-ambiguo]]
