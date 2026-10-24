---
title: "Guion Estratégico para Video de 2 Minutos (Hito S2)"
type: sprint
tags: [demo, video, guion, evaluacion, s2]
created: 2026-10-24
updated: 2026-10-24
status: stable
sources:
  - "[[raw/spec-s2-herramientas-resiliencia]]"
---

# Guion Estratégico para Video de 2 Minutos (Hito S2)

## Estructura Cronometrada (120 Segundos)

| Tiempo | Bloque | Qué se Muestra en Pantalla | Narración / Mensaje Clave |
| :--- | :--- | :--- | :--- |
| **0:00 - 0:25** | **El Problema Real** | Split screen: Remisión física arrugada con nota a mano ("faltaron 20") y factura CFDI cobrando el 100%. | "El 8% del gasto B2B se fuga en facturas con faltantes o sobreprecios que nadie coteja a tiempo. CotejAI audita el ciclo completo con agentes autónomos." |
| **0:25 - 0:55** | **Ejecución Continua del Lote** | Terminal ejecutando `python main.py audit --all` sobre 10 casos en tiempo real con spinners e indicadores de progreso. | "Corremos 10 casos reales de forma 100% desatendida. CotejAI lee la remisión con visión multimodal, valida fiscalmente y detecta discrepancias al instante." |
| **0:55 - 1:25** | **Demostración de Resiliencia** | Log mostrando detección de CFDI cancelado, proveedor 69-B, y simulación de corte del SAT con activación del Circuit Breaker. | "Si el SAT se cae, el circuit breaker conmuta a `SAT_NO_VERIFICADO` y no tumba el lote. Si una foto es borrosa, no inventa números: solicita refotografiado o escala." |
| **1:25 - 1:45** | **Acción Externa e Idempotencia** | Webhook recibido con la solicitud de nota de crédito ($290 MXN). Relanzamiento del caso mostrando que la base de datos bloquea el duplicado. | "El agente actúa en el mundo real reclamando la nota de crédito, pero con estricta idempotencia: relanzar el proceso jamás duplicará una notificación." |
| **1:45 - 2:00** | **Resumen Financiero y ROI** | Tabla final en consola con el dinero retenido ($45,200 MXN), costo ínfimo de Grok ($0.03 USD) y ROI masivo. | "En 10 casos CotejAI recuperó miles de pesos con centavos en tokens. Auditoría implacable y autónoma para el Reto Platica MagIA 2026." |

## Elementos Visuales Indispensables
- Terminal de alta resolución con texto grande legible y colores contrastantes.
- Ventana adyacente (o navegador) mostrando el webhook recibido.
- Base de datos SQLite mostrando los registros en `actions` e `invoices_seen`.

## Video Programático Renderizado con HyperFrames

Además del guion en vivo de 2 minutos, el repositorio cuenta con el video programático de alta definición renderizado con **HyperFrames** (`1920×1080`, `30 fps`, `24.0 s`):
- **Archivo MP4:** `video-cotejai/cotejai-demo.mp4`
- **Documentación técnica del video:** [[hyperframes-video]]

## Páginas Relacionadas
- [[s2-roadmap]]
- [[resilience-matrix]]
- [[idempotency-engine]]
- [[hyperframes-video]]
