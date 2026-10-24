---
title: "Policy Gate (Compuerta de Políticas y Límites de Autonomía)"
type: concept
tags: [guardrails, governance, limites-financieros, escalamiento, seguridad]
created: 2026-10-24
updated: 2026-10-24
status: stable
sources:
  - "[[raw/spec-s2-herramientas-resiliencia]]"
  - "docs/S2-herramientas-reales.md"
---

# Policy Gate (Compuerta de Políticas y Límites de Autonomía)

## Propósito
Un agente autónomo no debe tener libertad irrestricta para tomar decisiones financieras de alto impacto. La compuerta `policy_gate` es un middleware determinista en código Python que intercepta toda decisión o acción propuesta por el LLM antes de que se ejecute.

## Configuración Declarativa (`config/policies.yaml`)

```yaml
limite_autonomo_mxn: 5000.00
codigos_que_escalan:
  - SUPPLIER_69B
  - CFDI_CANCELLED
  - TAX_MISMATCH
  - SKU_UNMAPPED
qty_over_po_pct_escala: 0.10
aprobar_pago:
  solo_si_codigos:
    - MATCH_OK
veredicto:
  montos_identicos_al_cotejo: true
```

## Reglas de Intercepción
1. **Límite de Autonomía Financiera:**
   - Si una solicitud de nota de crédito excede `$5,000 MXN`, la compuerta cancela la acción directa y la transmuta automáticamente en `escalar_caso` hacia el líder de cuentas por pagar con el expediente prearmado.
2. **Códigos Bloqueantes Innegociables:**
   - La presencia de `SUPPLIER_69B` o `CFDI_CANCELLED` prohíbe de inmediato cualquier pago o negociación estándar; se congela el caso y se genera alerta de fraude.
3. **Consistencia de Cálculos Aritméticos:**
   - Si Grok intenta invocar `cerrar_caso` con un monto o fuga diferente al calculado matemáticamente por el motor determinista de Python, la compuerta rechaza la llamada, inyecta el error numérico al contexto de Grok y fuerza una corrección.

## Páginas Relacionadas
- [[three-way-matching]]
- [[solicitar-nota-credito]]
- [[resilience-matrix]]
