# Plan de Acción Definitivo S2 — CotejAI (Entrega Hoy 24 de Octubre · 23:59 CDMX)

> **Propósito:** Documento definitivo de arquitectura y herramientas reales para implementar hoy en **CotejAI** (Semana 2 del reto **Platica MagIA 2026**). Combina **Grok Vision**, **APIs públicas reales en vivo (Tipo de Cambio + SOAP SAT + Lista 69-B real)** y **Alertas Reales por Webhook con Idempotencia en SQLite**.

---

## 1. Contexto Clave del Comunicado Oficial (Organizadores)

1. **Fecha límite:** **Hoy sábado 24 de octubre a las 23:59 (hora CDMX)**.
2. **Herramientas Reales (S2):**
   - Deben ser funciones que el agente decida invocar por sí mismo para hacer algo real (llamar a una API externa, usar Grok Vision, consultar una base de datos real, enviar un mensaje por red) y tener **manejo de errores**.
3. **Datos Reales valen 15 puntos de la rúbrica:**
   - Al conectarnos a la **API de Tipo de Cambio en vivo**, al **Webservice SOAP real del SAT** y usar **RFCs reales del listado público oficial del Artículo 69-B del SAT**, aseguramos esos puntos de datos reales.
4. **Pruebas de Conectividad Superadas desde el Entorno Local:**
   - `grok-4.6` con imágenes en base64 (`image_url`) en `https://api.reto.pltk.mx/v1` $\rightarrow$ **Activo y verificado**.
   - API de Tipo de Cambio `https://open.er-api.com/v6/latest/USD` $\rightarrow$ **`200 OK` en $<0.5\text{ s}$** (`USD -> MXN`).
   - Servidor SOAP del SAT `https://consultaqr.facturaelectronica.sat.gob.mx/ConsultaCFDIService.svc` $\rightarrow$ **`200 OK` en $<0.5\text{ s}$**.

---

## 2. Catálogo Definitivo de Herramientas Reales que Invocará el Agente (`grok-4.6`)

| # | Herramienta | Qué hace en el mundo real | Manejo de Errores / Resiliencia |
| :--- | :--- | :--- | :--- |
| **1** | **`leer_remision_imagen`** *(Grok Vision en vivo)* | Lee la foto real `remision.png` del almacén usando `grok-4.6` multimodal. Extrae folio, líneas (`sku`, `cantidad_recibida`, `confianza`), firma, sello y notas a mano (*"Se reciben 80 pzas, faltaron 20"*). | Si la foto está borrosa (`confianza < 0.85`) o no tiene sello/firma, **no inventa números**: devuelve `RECEIPT_UNREADABLE` y fuerza el escalamiento. |
| **2** | **`consultar_tipo_cambio_real`** *(API Financiera en vivo)* | Cuando una factura u OC viene en dólares (`USD`) o trae atributo `TipoCambio` en el XML, hace un `GET` real en vivo a `https://open.er-api.com/v6/latest/USD` para validar que el proveedor no esté inflando el tipo de cambio USD/MXN. | Reintento con backoff ante caída de red; si la API externa no responde, usa la última cotización cacheada en SQLite marcando contingencia. |
| **3** | **`consultar_sat_en_vivo`** *(SOAP SAT Real + Lista 69-B Oficial en SQLite)* | 1) Consulta el servidor SOAP oficial del SAT en vivo (`ConsultaCFDIService.svc`) para verificar vigencia del CFDI.<br>2) Cruza el RFC emisor contra la tabla SQLite con **RFCs reales del listado público 69-B (EFOS)**.<br>3) Verifica en `invoices_seen` que el UUID no sea una factura duplicada. | **Circuit Breaker:** Si el servidor SOAP del SAT falla o da timeout 3 veces seguidas, abre el circuito por 10 min (`SAT_NO_VERIFICADO`) para no tumbar el lote de 10 casos. |
| **4** | **`enviar_alerta_reclamo_real`** *(Webhook en vivo + SQLite Idempotente)* | Cuando hay faltante o sobreprecio $\le \$5,000\text{ MXN}$, dispara un `POST` HTTP real por red (Webhook de Platica / Discord / Slack / endpoint en vivo) solicitando la nota de crédito con el desglose exacto. | **Idempotencia estricta:** Registra la llave `OC-XXX:nota_credito:v1` en la tabla `actions` de SQLite (modo WAL). Si se relanza el caso, bloquea el envío duplicado. |
| **5** | **`cotejar_caso` y `cerrar_caso`** *(Motor Determinista + Compuerta `policy_gate`)* | Cruza OC, Remisión y CFDI calculando centavo a centavo el monto a pagar y la fuga en MXN, y valida el veredicto final con Pydantic antes de guardarlo en `cotejai.db`. | La compuerta rechaza cualquier intento del LLM de inventar montos o de reclamar autónomamente fugas $> \$5,000\text{ MXN}$. |

---

## 3. El Lote de 10 Casos para la Ejecución Continua (`datasets/`)

Al correr `python main.py audit --all`, el agente procesará de forma autónoma estos 10 casos reales/diversos:

| Caso | Escenario | Herramientas Reales que Demuestra | Veredicto Esperado |
| :--- | :--- | :--- | :--- |
| **`OC-001`** | Entrega completa y precios exactos en MXN | `consultar_sat_en_vivo` + `cotejar_caso` | `APROBADO` (`MATCH_OK`) |
| **`OC-002`** | Faltante de 20 tornillos en almacén | `cotejar_caso` + `enviar_alerta_reclamo_real` | `EN_RECLAMO` (`QTY_SHORT`) |
| **`OC-003`** | Sobreprecio en rollo de cable ($88 vs $80) | `cotejar_caso` + `enviar_alerta_reclamo_real` | `EN_RECLAMO` (`PRICE_UP`) |
| **`OC-004`** | **Foto de remisión física con nota a mano** | **`leer_remision_imagen` (Grok Vision)** + alerta | `EN_RECLAMO` (`QTY_SHORT`) |
| **`OC-005`** | **Foto de remisión borrosa / ilegible** | **`leer_remision_imagen` (Fallo visual controlado)** | `ESCALADO` (`RECEIPT_UNREADABLE`) |
| **`OC-006`** | **Factura en USD con Tipo de Cambio inflado** | **`consultar_tipo_cambio_real` (API FX en vivo)** | `ESCALADO` / `EN_RECLAMO` (`FX_OVERCHARGE`) |
| **`OC-007`** | **Proveedor con RFC real en Lista 69-B del SAT** | **`consultar_sat_en_vivo` (Datos Reales 15 pts)** | `ESCALADO` (`SUPPLIER_69B`) |
| **`OC-008`** | Impuesto IVA mal calculado en el XML | `cotejar_caso` (Validación fiscal CFDI 4.0) | `ESCALADO` (`TAX_MISMATCH`) |
| **`OC-009`** | Factura CFDI duplicada (UUID ya registrado) | `consultar_sat_en_vivo` (`invoices_seen` en SQLite) | `ESCALADO` (`DUPLICATE`) |
| **`OC-010`** | Caída del servidor SOAP del SAT + Fuga $> \$5,000$ | **Circuit Breaker (`SAT_NO_VERIFICADO`)** + `policy_gate` | `ESCALADO` (Lote termina sin caerse) |

---

## 4. Stack Oficial del Proyecto (Web, Agente y Datos)

| Capa | Tecnología | Rol en CotejAI | Por qué encaja perfecto |
| :--- | :--- | :--- | :--- |
| **Servidor Web & API** | **FastAPI** | Expone los endpoints REST y WebSockets/SSE. | Usa los mismos `Pydantic v2` y `HTTPX` del backend. Unifica todo en un solo comando (`python main.py web`). |
| **Diseño y Estilos** | **Tailwind CSS** | Sistema de diseño, layout Bento, tipografía y paleta. | Cero CSS desordenado. Permite aplicar la identidad exacta de Platica (esmeralda/zinc) con microinteracciones táctiles. |
| **Lógica de Interfaz** | **JavaScript Moderno (ES6+) / Alpine.js** | Reactividad del chat, *Drag & Drop* de fotos y tabs. | Extremadamente ligero, no requiere servidor Node.js corriendo aparte y actualiza el chat en tiempo real sin recargar la página. |
| **Iconografía Técnica** | **Lucide Icons** | Iconos SVG nítidos (visor de imagen, SAT, alertas). | El estándar de las aplicaciones SaaS modernas (mismo set usado por Shadcn/UI y Vercel). |
| **Gráficos (S2 / S3 / S4)** | **Chart.js / ApexCharts** | Gráficas de fugas retenidas, costo por tarea (S3) y monitor de 1,000 casos (S4). | Se cargan de forma modular para mostrar el rendimiento continuo de 12 horas. |
| **Base de Datos** | **PostgreSQL 16 + SQLite WAL** | Persistencia de `cases`, `actions` (idempotencia), `llm_calls`, `invoices_seen` y Lista 69-B real. | Transaccional para producción con fallback instantáneo para tests locales. |
| **Motor de IA** | **Grok 4.6 (Text & Vision)** | Agente autónomo (`tool_calling`) y lectura multimodal de fotos de remisiones. | Conectado directo al gateway oficial `api.reto.pltk.mx/v1` con reintentos `Tenacity`. |

---

## 5. Plan de Implementación en Código (Sin romper los 35 tests actuales)

1. **`src/db.py` (Nuevo):**
   - Inicializa `cotejai.db` con `PRAGMA journal_mode=WAL; PRAGMA busy_timeout=5000;`.
   - Tablas: `cases`, `actions` (llave de idempotencia), `llm_calls` (telemetría de tokens/latencia), `invoices_seen` (antiduplicados) y `sat_69b_efos` (precargada con RFCs reales del listado oficial 69-B del SAT).
2. **`src/vision.py` (Nuevo):**
   - Función `leer_remision_imagen(case_id)` que envía `datasets/{case_id}/remision.png` en base64 a `grok-4.6`, valida el JSON con Pydantic y evalúa `confianza >= 0.85`.
3. **`src/external_tools.py` (Nuevo):**
   - `consultar_tipo_cambio_real(moneda_origen, tipo_cambio_cfdi)`: consulta `https://open.er-api.com/v6/latest/USD` con `httpx` + caché de respaldo en SQLite.
   - `consultar_sat_en_vivo(case_id, uuid, rfc_emisor, rfc_receptor, total)`: consulta la tabla 69-B real en SQLite, revisa duplicados en `invoices_seen` y llama al SOAP del SAT con **Circuit Breaker** (3 fallos $\rightarrow$ ventana abierta de 10 minutos con `SAT_NO_VERIFICADO`).
   - `enviar_alerta_reclamo_real(case_id, rfc_proveedor, uuid_factura, monto_mxn, motivo)`: verifica idempotencia en tabla `actions` de SQLite y dispara el webhook HTTP real con `httpx`.
4. **`src/agent.py` y `main.py` (Actualización):**
   - Registra las nuevas herramientas en `TOOLS` para que `grok-4.6` las invoque autónomamente.
   - Imprime al final de `python main.py audit --all` la tabla ejecutiva con los 10 casos, herramientas usadas, dinero retenido, bloqueos de idempotencia y costo en tokens.
5. **`datasets/generate.py` (Actualización):**
   - Genera los 10 casos (`OC-001` a `OC-010`) incluyendo las imágenes reales `OC-004/remision.png` (nítida con sello y nota manuscrita) y `OC-005/remision.png` (desenfocada/ilegible).

---

## 5. Guion para el Video de 2 Minutos (S2)

* **0:00 - 0:20 · Problema y Arquitectura:** Mostrar el flujo de CotejAI y abrir en pantalla la foto `datasets/OC-004/remision.png` (donde se ve la nota a mano de que faltaron 20 piezas) junto al `cfdi.xml`.
* **0:20 - 1:05 · Ejecución Autónoma de los 10 Casos:** Correr `python main.py audit --all`. Se ve en vivo cómo Grok decide llamar a `leer_remision_imagen`, `consultar_tipo_cambio_real`, `consultar_sat_en_vivo` y `enviar_alerta_reclamo_real`.
* **1:05 - 1:35 · Demostración de Resiliencia y Datos Reales:**
  - En `OC-005` detecta la foto borrosa (`RECEIPT_UNREADABLE`) y escala sin inventar números.
  - En `OC-006` consulta la API de divisas en vivo y detecta el dólar inflado (`FX_OVERCHARGE`).
  - En `OC-007` frena a un proveedor real de la Lista 69-B del SAT (`SUPPLIER_69B`).
  - En `OC-010` el *circuit breaker* absorbe la falla del SAT (`SAT_NO_VERIFICADO`) sin detener el lote.
* **1:35 - 2:00 · Idempotencia y ROI:** Volver a correr `python main.py audit --case OC-004` para mostrar que la tabla `actions` de SQLite impide enviar un segundo webhook duplicado, y mostrar la tabla final de miles de pesos retenidos.
