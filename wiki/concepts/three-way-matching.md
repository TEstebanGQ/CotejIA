---
title: "Three-Way Matching (Cotejo Tripartito)"
type: concept
tags: [cotejo, finanzas, b2b, auditoria, discrepancias]
created: 2026-10-24
updated: 2026-10-24
status: stable
sources:
  - "CotejAI_guia_implementacion.md"
  - "docs/00-framework.md"
---

# Three-Way Matching (Cotejo Tripartito)

## Definición
El **Three-Way Matching** es el control financiero fundamental en compras B2B que compara tres documentos antes de autorizar el pago de una factura:
1. **Orden de Compra (OC):** Lo que la empresa solicitó y a qué precio acordado.
2. **Remisión de Entrega (Almacén):** Lo que efectivamente ingresó físicamente al almacén (con firma y sello).
3. **Factura CFDI (XML):** Lo que el proveedor pretende cobrar fiscalmente.

```
       ┌────────────────────────┐
       │ Orden de Compra (OC)   │
       │  - Precios pactados    │
       │  - Cantidades pedidas  │
       └───────────┬────────────┘
                   │
                   ▼
  ┌──────────────────────────────────┐
  │ Remisión Física (Almacén)        │◄─── Visión Multimodal (Grok)
  │  - Cantidad real recibida        │     Firmas / Sellos
  │  - Notas y mermas a mano         │
  └────────────────┬─────────────────┘
                   │
                   ▼
       ┌────────────────────────┐
       │ Factura CFDI 4.0 XML   │◄─── Validación SAT / 69-B
       │  - Precios facturados  │
       │  - Unidades y totales  │
       └────────────────────────┘
```

## Códigos Canónicos de Discrepancia
- `MATCH_OK`: Las tres piezas cuadran perfectamente dentro de tolerancias.
- `QTY_OVER_PO`: Cantidad facturada excede la cantidad ordenada.
- `QTY_OVER_RECEIPT`: Se factura mercancía que el almacén nunca recibió (faltante).
- `PRICE_MISMATCH`: Precio unitario facturado excede el precio de la OC.
- `TAX_MISMATCH`: Error en la tasa o cálculo de IVA/IEPS.
- `SUPPLIER_69B`: Proveedor listado como EFOS definitivo en SAT.
- `CFDI_CANCELLED`: Factura cancelada en el SAT.
- `SAT_NO_VERIFICADO`: Servicio SAT no disponible (circuit breaker activado).
- `RECEIPT_UNREADABLE`: Remisión física ilegible o sin certificación de almacén.
- `DUPLICATE`: Factura ya pagada o registrada previamente.

## Páginas Relacionadas
- [[leer-remision-fisica]]
- [[validar-sat-y-lista-69b]]
- [[policy-gate]]
