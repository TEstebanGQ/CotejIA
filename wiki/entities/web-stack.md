---
title: "Stack Oficial Web & Backend — CotejAI"
type: entity
tags: [stack, fastapi, tailwind, alpinejs, lucide, chartjs, postgresql, grok]
created: 2026-10-24
updated: 2026-10-24
status: stable
sources:
  - "[[raw/spec-s2-herramientas-resiliencia]]"
  - "docs/PLAN_ACCION_S2_HOY.md"
---

# Stack Oficial Web & Backend — CotejAI

> **Decisión arquitectónica oficial del equipo (24 de octubre de 2026):** Arquitectura unificada levantada con un solo comando (`python main.py web`) sin requerir un servidor Node.js separado.

## 1. Capa de Interfaz Web y API

| Capa | Tecnología | Rol en CotejAI | Por qué encaja perfecto |
| :--- | :--- | :--- | :--- |
| **Servidor Web & API** | **FastAPI** (+ Uvicorn) | Expone los endpoints REST y WebSockets/SSE, y sirve la interfaz web estática. | Usa los mismos `Pydantic v2` y `HTTPX` del backend. Unifica todo en un solo comando (`python main.py web`). |
| **Diseño y Estilos** | **Tailwind CSS** | Sistema de diseño, layout Bento, tipografía y paleta. | Cero CSS desordenado. Permite aplicar la identidad exacta de Platica (esmeralda/zinc) con microinteracciones táctiles. |
| **Lógica de Interfaz** | **JavaScript Moderno (ES6+) / Alpine.js** | Reactividad del chat, *Drag & Drop* de fotos de remisiones y tabs de casos. | Extremadamente ligero, no requiere servidor Node.js corriendo aparte y actualiza la vista y el chat en tiempo real sin recargar la página. |
| **Iconografía Técnica** | **Lucide Icons** | Iconos SVG nítidos (visor de imagen, SAT, alertas, estados). | El estándar de las aplicaciones SaaS modernas (mismo set usado por Shadcn/UI y Vercel). |
| **Gráficos (S2 / S3 / S4)** | **Chart.js / ApexCharts** | Gráficas de fugas retenidas, costo por tarea (S3) y monitor de 1,000 casos (S4). | Se cargan de forma modular para mostrar métricas financieras y el rendimiento continuo de 12 horas. |

---

## 2. Capa de Agente, Datos e Integraciones Reales

| Capa | Tecnología | Rol en CotejAI |
| :--- | :--- | :--- |
| **Motor de IA & Visión** | **Grok 4.6 (xAI)** vía Platica Gateway (`api.reto.pltk.mx/v1`) | Razonamiento autónomo, llamada a herramientas (`tool_calling`) y lectura multimodal de fotos de remisiones (**Grok Vision**). |
| **Base de Datos** | **PostgreSQL 16** (con fallback automático a **SQLite WAL**) | Persistencia de casos (`cases`), motor de idempotencia (`actions`), bitácora de tokens (`llm_calls`), antiduplicados (`invoices_seen`) y Lista 69-B real (`sat_69b_efos`). |
| **Validación y Resiliencia** | **Pydantic v2** + **Tenacity** + **HTTPX** | Compuerta `policy_gate`, reintentos con *exponential backoff + jitter* y *Circuit Breaker* para servicios externos. |
| **Herramientas Reales Externas** | **SOAP SAT WebService**, **Lista 69-B Oficial**, **ExchangeRate-API (USD/MXN)**, **Webhooks HTTP** | Consultas en vivo en tiempo real sin mocks estáticos. |

## Páginas Relacionadas
- [[grok-vision]]
- [[sqlite-wal]]
- [[s2-roadmap]]
