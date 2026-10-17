# CotejAI × Platica.mx — Plan de integración (Track 2), estado de S1 y stack

> Documento de trabajo. Todo lo de Platica sale de su documentación pública (docs.platica.mx, revisada el 17 de octubre de 2026). Lo que la documentación **no** dice está marcado como **No documentado**: hay que preguntarlo a los organizadores.

---

## 1. Estado de la Semana 1

Lo que pide el reto para S1 contra lo que hay en el repositorio:

| Requisito de S1 | Estado | Evidencia |
| --- | --- | --- |
| Agente corriendo de principio a fin | ✅ | `python main.py audit --all` procesó 3 casos |
| Conexión real con Grok con la llave del reto | ✅ | Grok 4.6 vía `api.reto.pltk.mx/v1`, 2 llamadas por caso, tool calling funcionando |
| Una entrada → una salida | ✅ | Caso (OC + remisión + CFDI XML) → veredicto JSON validado con Pydantic |
| Repositorio público con licencia | ✅ | Público, MIT |
| README con el problema y qué hace | ✅ | `README.md` con tabla de resultados reales |
| Sin llaves en el repo | ✅ | Solo el placeholder `pk_xxxx` de `.env.example`; `.env` está en `.gitignore` |
| Tests | ✅ | 3 de 3 pasan (`pytest`) |

**Veredicto: S1 está completo.** Lo que pide el mensaje de los organizadores para el sábado 17 está cubierto; lo de S2 en adelante (3 herramientas, 10 ejecuciones, 30 casos, carga) no se exige todavía.

**Mejoras baratas antes de cerrar S1** (no obligatorias):
- [ ] Pegar en el README una captura o el texto de la salida de `audit --all` (ya está la tabla).
- [ ] Agregar un diagrama del flujo (hay uno en la guía; falta en el README).
- [ ] Guardar la bitácora de cada corrida en `runs/*.jsonl` (hoy solo se imprime).

---

## 2. Cómo se conecta CotejAI a Platica

Platica es una plataforma de agentes conversacionales (WhatsApp, Instagram, Messenger, chat, correo). CotejAI **no reemplaza** al agente de Platica: es una **capacidad** que ese agente invoca, y a la vez usa Platica como **canal** para hablar con el proveedor.

```
Comprador ──WhatsApp──► Agente Platica ──(API personalizada o MCP)──► CotejAI (público, HTTPS)
                                                                          │
Proveedor ◄──WhatsApp (plantilla)── POST /v1/messages ◄── notificador ◄───┘
Proveedor ──responde──► Webhook message.created ──► CotejAI reabre el caso
```

Hay **tres puntos de contacto**:

| # | Dirección | Mecanismo de Platica | Para qué |
| --- | --- | --- | --- |
| A | Platica → CotejAI | API personalizada **o** servidor MCP externo | El comprador pregunta por WhatsApp "¿qué facturas tienen problema?" y el agente de Platica consulta CotejAI |
| B | CotejAI → Platica | `POST /v1/messages` | Avisar al proveedor del faltante y pedir la nota de crédito |
| C | Platica → CotejAI | Webhook `message.created` | Recibir la respuesta del proveedor y avanzar el caso |

---

## 3. Referencia de la API de Platica

**Base:** `https://api.platica.mx` · **Auth:** `Authorization: Bearer pl_key_...` (API key en el dashboard: Configuración → API Keys, se muestra una sola vez; da acceso a todo el workspace donde se creó).

| Dato | Valor |
| --- | --- |
| Rate limit | 30 peticiones por segundo por API key; headers `X-RateLimit-*` |
| Error | JSON `{ code, error, details }` |
| Reintentar | 502, 503, 504 con backoff (antes de reintentar un 502/504 síncrono, consultar el recurso: pudo completarse). 409 con backoff. **No** reintentar otros 4xx |
| Códigos a manejar | 402 (se acabó el crédito del workspace), 422 (petición válida pero no procesable), 429 (límite) |
| Soporte API | integraciones@platica.mx |

### 3.1 Enviar mensaje (punto B)

`POST /v1/messages`

| Campo | Notas |
| --- | --- |
| `channelId` | ID del canal o el teléfono del agente en E.164 sin `+` |
| `conversationId` | Teléfono del cliente en E.164 sin `+` (ej. `521234567890`) |
| `content` | Texto, o un objeto para media / interactivo |
| `type` | `text`, `image`, `video`, `file`, `audio`, `interactive`, `email`, `instruction` |
| `delay` / `scheduleTime` | Opcionales; no se pueden usar juntos. Respuesta 202 |

- Media (`image`, `file`...) recibe una **URL pública https**: sirve para adjuntar la foto de la remisión como evidencia.
- Interactivo (solo WhatsApp): hasta 3 botones o lista de hasta 10 filas. Útil para que el proveedor responda "Aceptar nota de crédito / Disputar".
- **Ventana de 24 horas:** solo se puede enviar texto libre si el cliente escribió en las últimas 24 h. Si no, **hay que usar una plantilla aprobada**. Revisar `canSendDirectMessage` antes de enviar.
- Un proveedor casi nunca tendrá la ventana abierta, así que el primer reclamo **siempre** sale como plantilla.

### 3.2 Plantillas de WhatsApp

- `GET /v1/templates` lista las plantillas **ya aprobadas** por workspace (con `params` y `buttons`).
- **No se pueden crear por API**: se crean en la plataforma de Platica o en WhatsApp Manager (Meta). La aprobación de Meta toma tiempo → **crearla el primer día del Track 2**.
- Endpoint exacto para *enviar* una plantilla: está en la página "Enviar Plantilla" (no la leí; revisarla).
- Plantilla propuesta (categoría utilidad):
  `Hola, soy el asistente de cuentas por pagar de {{empresa}}. La factura {{folio}} tiene una diferencia: {{detalle}}. Solicitamos una nota de crédito por {{monto}} MXN. ¿Nos la pueden enviar?`

### 3.3 Webhooks (punto C)

- Se registran con `POST /v1/webhooks`; eventos en `GET /v1/webhooks/events` (22 eventos, 6 categorías).
- Relevantes: `message.created` (con `source: "inbound.message.received"` cuando escribe el cliente), `message.updated` (cambios de estado: sent → delivered → read → failed), `conversation.*`.
- Payload de mensaje entrante: `data.message.content` (texto), `data.message.files[]` / `images[]` (la forma de los adjuntos **no está documentada**: capturar un payload real), `data.client.id` (teléfono), `data.conversation.id`.
- **Firma:** HMAC-SHA256 del **cuerpo crudo** con el `secret` del webhook; header `X-Webhook-Signature: sha256=<hex>`. Otros headers: `X-Webhook-Event`, `X-Webhook-Event-Id`, `X-Webhook-Timestamp`.
- Responder `2xx`. **No documentado:** política de reintentos y timeout → hacer el handler idempotente (guardar `X-Webhook-Event-Id` y descartar repetidos) y responder rápido (encolar y contestar 200).

### 3.4 Herramientas del agente de Platica (punto A)

Dos formas de que un agente de Platica llame a CotejAI:

**Opción 1 — API personalizada** (la más simple; recomendada para empezar)

1. `POST /v1/tools/apis` con `name`, `description` (10–1024 caracteres; **debe decir cuándo usarla**), `request` (método, URL, headers, auth) y `variables`. Queda en borrador.
2. `POST /v1/tools/apis/{id}/test` con `dryRun: true`, luego una prueba real.
3. `POST /v1/tools/apis/{id}/enable` → devuelve `toolId`.
4. `POST /v1/agents/{agentId}/tools` con el `toolId`.

Reglas que afectan el diseño:
- Timeout de **1 a 60 s** (30 s por defecto) → una auditoría de lote **no cabe** en una llamada. El endpoint devuelve un `job_id` al instante y la consulta de estado es otra herramienta.
- La respuesta se recorta a **32 000 bytes** por defecto (`maxBytes`): devolver resúmenes, no expedientes completos. Se puede filtrar con `path`, `include`, `exclude`.
- Variables `mode: ai` (el modelo las llena), `constant` o `context` (teléfono, conversación, agente...). El esquema que ve el modelo sale de las `description` de las variables: **son parte del producto**.
- Solo URLs HTTPS públicas: se bloquean localhost, redes privadas y redirecciones hacia ellas.

**Opción 2 — Servidor MCP externo**

1. `POST /v1/tools/mcp/preview` con la URL para listar las herramientas sin guardar.
2. `POST /v1/tools/mcp` con `name`, `url`, `auth` (`none`, `bearer`, `apikey-header`, `oauth2`) y `tools` a instalar → `installedToolIds`.
3. `POST /v1/agents/{agentId}/tools` para asignarlas.
4. Estados: `connected`, `pending_auth`, `needs_reauth`, `error`. Error 502 = no se pudo conectar o listar.

Herramientas MCP que expondría CotejAI: `auditar_lote`, `estado_caso`, `listar_casos_con_problema`, `aprobar_ajuste`.

**Recomendación:** empezar con API personalizada (3 endpoints REST: crear auditoría, consultar estado, listar problemas) y pasar a MCP cuando funcione. El MCP propio de Platica (`https://api.platica.mx/mcp`, JSON-RPC sobre Streamable HTTP, auth OAuth 2.1 o Bearer `pl_key_`) sirve para que **nosotros** usemos la API de Platica desde un cliente MCP, no para el sentido inverso.

---

## 4. Qué NO está documentado (preguntar a los organizadores)

1. **Cómo se accede al sandbox** del Track 2 y si requiere una API key distinta o un workspace aparte. La documentación pública no menciona sandbox.
2. Si el sandbox permite **enviar WhatsApp reales** o solo canales internos. En canales internos, `interactive`, `email` y plantillas devuelven 422: no sirven para probar el flujo de plantillas.
3. Tiempo de aprobación de plantillas de WhatsApp.
4. **Reintentos y timeout** de los webhooks.
5. Forma de los adjuntos (`files[]`, `images[]`) en el payload entrante.
6. Si el límite de 30 req/s aplica igual en el sandbox y si hay tope de créditos de mensajes.

---

## 5. Plan de integración (paso a paso)

**Antes de que empiece el Track 2 (se puede hacer ya, sin Platica):**
- [ ] Interfaz `Notificador` con implementaciones `correo` y `webhook`; `NOTIFIER=correo|webhook|platica` en `.env`.
- [ ] API REST de CotejAI con FastAPI: `POST /audits` (devuelve `job_id`), `GET /audits/{job_id}`, `GET /cases?estado=...`.
- [ ] Endpoint `POST /webhooks/platica` con verificación HMAC sobre el cuerpo crudo e idempotencia por `X-Webhook-Event-Id`.
- [ ] Despliegue público con HTTPS (Railway, Render o Fly.io): sin esto Platica no puede llamar a CotejAI.

**Al recibir el sandbox:**
1. Generar la API key y guardarla como secreto (nunca en el repo).
2. Pedir/crear la plantilla de reclamo en la plataforma (empieza la aprobación de Meta).
3. Implementar `NotificadorPlatica`: consultar `canSendDirectMessage`; si es `false`, plantilla; si es `true`, texto libre o botones.
4. Registrar el webhook con `POST /v1/webhooks`, suscrito a `message.created`, con `secret`.
5. Registrar las herramientas de CotejAI en el agente de Platica (API personalizada → `test` con `dryRun` → `enable` → asignar).
6. Prueba de punta a punta: el comprador pregunta por WhatsApp → agente de Platica llama a CotejAI → CotejAI escribe al proveedor → el proveedor responde → webhook → caso se actualiza.
7. Medir el costo real por caso y por mensaje para los *unit economics*.

---

## 6. ¿Hay proyectos parecidos?

Buscado el 17 de octubre de 2026. Resumen honesto:

- **No encontré un proyecto de código abierto** que haga cotejo de tres vías con CFDI 4.0, validación ante el SAT y lista 69-B. Para México, el nicho está vacío en lo que pude encontrar.
- **Productos comerciales de cotejo con IA** (conceptualmente iguales, sin foco en México): [Beam AI](https://beam.ai/agents/three-way-match-agent/), [Spendflo](https://www.spendflo.com/agents/ai-three-way-match-agent), [Airparser](https://airparser.com/blog/automate-three-way-invoice-matching/), el [Invoice PO Matching Agent de MAQ Software](https://df.marketplace.microsoft.com/ja-jp/product/maqsoftware.invoice_po_agent_) y el [agente de excepciones de facturas de Microsoft](https://adoption.microsoft.com/es-es/scenario-library/finance/invoice-exception-agent/).
- **Referencia de código abierto más cercana:** el [ejemplo de procurement en TypeScript](https://glama.ai/mcp/servers/@PSPDFKit/nutrient-document-engine-mcp-server/blob/5a304d0ac1109dcc9379389afef3c1ad69bb3f70/examples/procurement-agent-ts/README.md) (LangGraph.js, clasifica, extrae y cruza OC, factura y pago). Verificar el repositorio original antes de usarlo.
- **Patrón de gobierno** útil: [Gravitee — controles y gobierno del agente](https://gravitee.io/corpus/gen-2446/purchase-to-pay/three-way-matching-automation.html). Insiste en que extraer no basta: hay que encontrar la OC correcta y resolver alias de proveedor.

**Lo que ya hacen los comerciales y CotejAI debe igualar:** tolerancias configurables, rutas de excepción a un aprobador, cola de revisión.
**Lo que los diferencia (y es el argumento del pitch):**
1. Cotejo contra la **remisión física** leída con visión, sumado a CFDI 4.0, SAT y lista 69-B. Ojo: los portales de proveedores mexicanos (EdiFact V3000, PortaldeProveedores.mx) ya validan el SAT y la 69-B; lo que no hacen es cotejar contra lo recibido ni perseguir la nota de crédito. Detalle en [docs/mercado.md](docs/mercado.md).
2. Flujo cerrado de **nota de crédito** con validación del CFDI de egreso.
3. El cierre ocurre **por WhatsApp** con el proveedor, que es como se trabaja en México.
4. Código abierto, auditable, con compuerta de políticas en código.

> Las cifras de precisión y ahorro de los productos comerciales son de sus propias páginas y no están verificadas de forma independiente. No las uses en el pitch como si fueran datos.

---

## 7. Stack recomendado

| Capa | Tecnología | Por qué |
| --- | --- | --- |
| Lenguaje | Python 3.12+ | Ecosistema de IA, `Decimal`, `satcfdi` |
| Modelo | Grok 4.6 (hoy), 4.7 si el gateway lo expone; visión del mismo modelo | Exigido por el reto; ya probado |
| Cliente LLM | SDK `openai` apuntando al gateway | Compatible con la API de xAI |
| Validación de salidas | Pydantic v2 | Esquemas estrictos, reintento si falla |
| Motor de cotejo | Python puro, `Decimal` | Determinista y testeable |
| Fiscal México | `satcfdi` (CFDI, estado SAT, 69-B), `httpx` | Evita armar el SOAP a mano |
| Visión / PDF | PyMuPDF (PDF → PNG) | Grok solo acepta JPG/PNG |
| API | FastAPI + Uvicorn | Endpoints para Platica, jobs asíncronos |
| MCP | SDK oficial de MCP para Python | Opción 2 de integración |
| Base de datos | PostgreSQL (SQLite en desarrollo) | Casos, estados, bitácora, `llm_calls` |
| Cola / workers | `asyncio` + semáforo; Redis + RQ si hace falta | Prueba de carga de S4 |
| Reintentos | `tenacity` | Backoff con jitter |
| Config y secretos | `python-dotenv`, variables de entorno del host | Llave fuera del repo |
| Pruebas | `pytest` + generador sintético | Métricas del reporte de S3 |
| Despliegue | Docker + `docker-compose`, Railway/Render/Fly.io | HTTPS público para Platica |
| Observabilidad | Logs JSON por línea + tabla `llm_calls` | Costo y latencia por caso |
| Notificación | Interfaz con `correo`, `webhook`, `platica` | Cambio por configuración al llegar el sandbox |

**Orden sugerido:** S2 = visión + SAT/69-B + compuerta + notificador por correo/webhook; S3 = generador de 36 casos + métricas de costo; S4 = Docker + worker + prueba de 1.000 casos; Track 2 = Platica según la sección 5.

---

## Fuentes

- [Platica — API](https://docs.platica.mx/api) · [Autenticación](https://docs.platica.mx/api/autenticacion) · [Errores](https://docs.platica.mx/api/errores)
- [Enviar mensaje](https://docs.platica.mx/api/mensajes/enviar-mensaje) · [Plantillas](https://docs.platica.mx/api/mensajes/plantillas/listar-plantillas)
- [Webhooks](https://docs.platica.mx/api/webhooks/introduccion) · [Entrega y firmas](https://docs.platica.mx/api/webhooks/entrega-y-firmas) · [Payloads](https://docs.platica.mx/api/webhooks/payloads)
- [Servidores MCP](https://docs.platica.mx/api/herramientas/servidores-mcp) · [APIs personalizadas](https://docs.platica.mx/api/herramientas/apis-personalizadas) · [MCP de Platica](https://docs.platica.mx/mcp)
