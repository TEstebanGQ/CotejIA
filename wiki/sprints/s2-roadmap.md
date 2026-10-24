---
title: "Roadmap y Plan de Ejecución — Semana 2 (S2)"
type: sprint
tags: [s2, roadmap, tareas, entregables, torneo]
created: 2026-10-24
updated: 2026-10-24
status: stable
sources:
  - "[[raw/spec-s2-herramientas-resiliencia]]"
  - "docs/S2-herramientas-reales.md"
---

# Roadmap y Plan de Ejecución — Semana 2 (S2)

## Metas Clave de S2
1. Implementar la **terna obligatoria** de herramientas reales (`leer_remision_fisica`, `validar_sat_y_lista_69b`, `solicitar_nota_credito`).
2. Implementar los **power-ups** de alto valor (`reconciliar_sku_ambiguo`, `verificar_duplicidad_historica`).
3. Construir la arquitectura de **resiliencia y persistencia**: Circuit Breaker SAT, SQLite WAL, Idempotencia y `policy_gate`.
4. Ejecutar de forma continua y desatendida un **lote de 10 casos diversos** en `datasets/`.
5. Producir el **video de 2 minutos** demostrando recuperación ante fallos y valor financiero.

## Fases de Implementación (Tareas T1 - T6)
- **T1: Registro Unificado de Herramientas:** Estructura modular `@herramienta` con schemas Pydantic tipados y exportación para Grok.
- **T2: Persistencia SQLite WAL:** Creación de tablas `cases`, `actions`, `llm_calls`, `invoices_seen`, `sku_aliases`.
- **T3: Grok Vision en Remisiones:** Integración multimodal con umbral de confianza 0.85 y rechazo sin alucinaciones (`RECEIPT_UNREADABLE`).
- **T4: SAT SOAP + Lista 69-B:** Consulta de estatus, caché de 69-B y circuit breaker ante 3 fallos consecutivos con ventana de 10 minutos.
- **T5: Acción Externa Idempotente:** Envío de nota de crédito a webhook de Platica/correo con deduplicación por clave primaria.
- **T6: Compuerta de Políticas (`policy_gate`):** Validación estricta de límites ($5,000 MXN) y bloqueo de EFOS / cancelados.

## Páginas Relacionadas
- [[tournament-rubric]]
- [[s2-demo-script]]
- [[resilience-matrix]]
- Documento táctico de equipo: `docs/PLAN_ACCION_S2_HOY.md`
