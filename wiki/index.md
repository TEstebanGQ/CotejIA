# CotejAI Knowledge Base — Index Maestro

> **Persistencia de Conocimiento Compilado** para el proyecto CotejAI (Reto Agente Platica MagIA 2026).
> Mantenido por agentes de IA bajo las directrices de [[SCHEMA]].

---

## 🧭 Estructura y Navegación Rápida

- [[SCHEMA]]: Reglas de gobernanza, workflows de Ingest/Query/Lint y convenciones de la wiki.
- [[log]]: Bitácora cronológica append-only de modificaciones y aprendizajes.

---

## 🏛️ Entidades (Sistemas, Modelos y Plataformas)

| Página | Resumen de una línea | Tags |
| :--- | :--- | :--- |
| [[grok-vision]] | Motor multimodal Grok 4.6 para lectura de remisiones físicas, sellos y notas manuscritas. | `grok`, `vision`, `ocr` |
| [[mascota-kotek]] | Mascota oficial Kótek (Búho Auditor de 3 Lentes) integrada en web y narrador con voz ElevenLabs para el video de 2 minutos. | `mascota`, `branding`, `voz` |
| [[web-stack]] | Stack oficial unificado: FastAPI, Tailwind CSS (esmeralda/zinc Bento), SPA de 2 vistas, 180 divisas ISO, carga manual y PostgreSQL 16. | `stack`, `fastapi`, `web` |
| [[hyperframes-video]] | Proyecto y video programático (`video-cotejai/cotejai-demo.mp4`, 1920×1080, 30 fps) de la plataforma y sus 5 escenas funcionales. | `hyperframes`, `video`, `demo` |
| [[sat-soap-and-69b]] | Webservice SOAP oficial del SAT para CFDI y lista negra definitiva de EFOS (Art. 69-B). | `sat`, `fiscal`, `69b` |
| [[sqlite-wal]] | Capa de persistencia local en modo WAL para concurrencia, idempotencia y auditoría. | `sqlite`, `wal`, `db` |
| [[cfdi-40]] | Estructura de comprobantes fiscales digitales por internet en México e impuestos desglosados. | `cfdi`, `xml`, `sat` |
| [[platica-platform]] | Arquitectura de integración con Platica.mx vía API personalizada, webhooks y MCP. | `platica`, `whatsapp`, `api` |

---

## 🧠 Conceptos y Arquitectura

| Página | Resumen de una línea | Tags |
| :--- | :--- | :--- |
| [[three-way-matching]] | Lógica de conciliación tripartita entre Orden de Compra, Remisión y Factura CFDI. | `auditoria`, `finanzas` |
| [[circuit-breaker-pattern]] | Mecanismo de corte ante caídas del SAT (3 fallos seguidos abren ventana de 10 min). | `resiliencia`, `circuit-breaker` |
| [[idempotency-engine]] | Control transaccional con llaves únicas en SQLite para prevenir acciones duplicadas al exterior. | `idempotencia`, `transacciones` |
| [[policy-gate]] | Compuerta determinista de políticas ($5,000 MXN de autonomía, bloqueo de EFOS y montos). | `guardrails`, `gobernanza` |
| [[resilience-matrix]] | Matriz integral de escenarios de error, degradación de respuestas y estrategias de recuperación. | `resiliencia`, `matriz` |

---

## 🛠️ Herramientas del Agente (Catálogo S2)

| Página | Tipo | Resumen de una línea |
| :--- | :--- | :--- |
| [[leer-remision-fisica]] | **Terna Obligatoria** | Extrae líneas, sellos y notas manuales de imágenes; umbral de confianza 0.85 anti-alucinaciones. |
| [[validar-sat-y-lista-69b]] | **Terna Obligatoria** | Valida estatus tributario en SAT SOAP y lista 69-B con Circuit Breaker integrado. |
| [[solicitar-nota-credito]] | **Terna Obligatoria** | Emite reclamo formal con límite de autonomía de $5,000 MXN e idempotencia estricta. |
| [[reconciliar-sku-ambiguo]] | *Power-Up* | Conciliación semántica de descripciones y unidades mediante caché en `sku_aliases` y Grok. |
| [[verificar-duplicidad-historica]] | *Power-Up* | Consulta en `invoices_seen` para evitar el pago doble de facturas en una ventana de 90 días. |

---

## 🚀 Sprints y Torneo

| Página | Resumen de una línea | Tags |
| :--- | :--- | :--- |
| [[s2-roadmap]] | Plan de trabajo y tareas técnicas (T1 a T6) para el hito de herramientas y resiliencia. | `s2`, `roadmap` |
| [[s2-demo-script]] | Guion minuto a minuto (120 segundos) para la demostración en video requerida por el torneo. | `demo`, `video` |
| [[tournament-rubric]] | Ponderación de criterios oficiales (Autonomía, Grok, Resiliencia, ROI) y tácticas para ganar. | `torneo`, `rubrica` |

---

## 📂 Fuentes Curadas Inmutables (`wiki/raw/`)

- [[raw/comunicado-s2-organizadores]]: Comunicado oficial con aclaraciones de herramientas, datos reales (15 pts) y cierre S2 (24 oct 23:59).
- [[raw/spec-s2-herramientas-resiliencia]]: Especificación técnica detallada provista por el equipo para S2.
- `docs/00-framework.md`: Arquitectura del framework de agentes CotejAI.
- `docs/S2-herramientas-reales.md`: Guía de implementación del hito S2.
- `README_PLATICA.md`: Integración con Platica y estado consolidado de la Semana 1.
- `CotejAI_guia_implementacion.md`: Especificación fundacional del motor de cotejo y CFDI.
