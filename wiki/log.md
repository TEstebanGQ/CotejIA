# CotejAI Knowledge Base — Registro Cronológico (Log)

Bitácora cronológica append-only de modificaciones, ingestas y linteos del grafo de conocimiento.

---

## [2026-10-24] ingest | Especificación S2: Catálogo de Herramientas y Resiliencia
- **Origen:** Especificación técnica del torneo Platica MagIA (Hito S2).
- **Archivos fuente:** `wiki/raw/spec-s2-herramientas-resiliencia.md`, `docs/S2-herramientas-reales.md`.
- **Acciones realizadas:**
  - Creación del esquema y protocolo de gobernanza en [[SCHEMA]].
  - Creación de páginas de entidades: [[grok-vision]], [[sat-soap-and-69b]], [[sqlite-wal]], [[cfdi-40]], [[platica-platform]].
  - Creación de conceptos y arquitectura de resiliencia: [[three-way-matching]], [[circuit-breaker-pattern]], [[idempotency-engine]], [[policy-gate]], [[resilience-matrix]].
  - Documentación de las 5 herramientas: [[leer-remision-fisica]], [[validar-sat-y-lista-69b]], [[solicitar-nota-credito]], [[reconciliar-sku-ambiguo]], [[verificar-duplicidad-historica]].
  - Documentación de sprint y evaluación: [[s2-roadmap]], [[s2-demo-script]], [[tournament-rubric]].
  - Generación del índice maestro [[index]].

## [2026-10-24] ingest | Comunicado Oficial Organizadores — Aclaraciones S2
- **Origen:** Correo/mensaje de seguimiento de los organizadores del reto Platica MagIA.
- **Archivos fuente:** `wiki/raw/comunicado-s2-organizadores.md`.
- **Puntos críticos detectados:**
  - Cierre de entrega S2: **Hoy sábado 24 de octubre a las 23:59 CDMX**.
  - Tres herramientas cuentan si son 3 funciones que ejecutan trabajo real (BD, API, Vision, Notificación) con manejo de errores; no tienen que ser 3 plataformas externas distintas.
  - **15 puntos en la rúbrica para Datos Reales** (incluyendo datos públicos oficiales como Lista 69-B real del SAT e imágenes reales).
- **Páginas actualizadas:** [[tournament-rubric]], [[index]].

## [2026-10-24] update | Definición Final de Herramientas Reales S2
- **Decisión de arquitectura:** Selección de las herramientas 100% funcionales en vivo para el hito S2:
  1. `leer_remision_imagen` (Grok Vision multimodal leyendo PNG real + control de fotos borrosas).
  2. `consultar_tipo_cambio_real` (API financiera pública en vivo `open.er-api.com` USD/MXN) + `consultar_sat_en_vivo` (SOAP oficial del SAT + Lista 69-B real en SQLite con Circuit Breaker).
  3. `enviar_alerta_reclamo_real` (Disparo de Webhook HTTP en vivo con llave de idempotencia en SQLite WAL).
- **Documento actualizado:** `docs/PLAN_ACCION_S2_HOY.md`.

## [2026-10-24] ingest | Definición Oficial del Stack Web, UI y Persistencia
- **Origen:** Tabla de arquitectura acordada por el equipo.
- **Stack confirmado:**
  - **Servidor Web & API:** FastAPI (REST + WebSockets/SSE, comando único `python main.py web`).
  - **Diseño y Estilos:** Tailwind CSS (Layout Bento, identidad Platica esmeralda/zinc).
  - **Lógica de Interfaz:** JavaScript Moderno (ES6+) / Alpine.js (sin servidor Node.js separado, Drag & Drop de fotos, chat reactivo y tabs).
  - **Iconografía Técnica:** Lucide Icons.
  - **Gráficos:** Chart.js / ApexCharts.
  - **Base de Datos:** PostgreSQL 16 (con fallback transparente a SQLite WAL).
  - **Motor de IA:** Grok 4.6 (Text & Vision Multimodal vía Platica Gateway).
- **Páginas creadas/actualizadas:** [[web-stack]], [[index]], `docs/PLAN_ACCION_S2_HOY.md`.

## [2026-10-24] git | Configuración de Flujo Git: develop, dev-tomas y dev-leo
- **Estrategia de ramas:**
  - `main`: Rama de producción / entrega oficial.
  - `develop`: Rama de integración donde se unen el frontend, backend y herramientas.
  - `dev-tomas`: Rama de trabajo individual de Tomás.
  - `dev-leo`: Rama de trabajo individual de Leo.
- **Estado:** Ramas creadas y publicadas en el repositorio remoto GitHub (`origin`). Rama activa local: `dev-tomas`.
