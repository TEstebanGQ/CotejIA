# S4 · Semana de carga

## Objetivo

Procesar **1,000 casos en 12 horas, sin nadie mirando**, con una bitácora completa que demuestre que el agente se recuperó solo de fallos y no duplicó ninguna acción.

## Lo que pide el reto

| Requisito | Cómo lo cumplimos |
| --- | --- |
| 1,000 unidades de trabajo | 1,000 casos generados con el generador de S3 |
| 12 horas desatendido | Servidor con reinicio automático, no una laptop |
| Bitácora completa | `case_events`, `llm_calls`, `actions` en PostgreSQL + `runs/s4_<fecha>.jsonl` |

Rúbrica que mueve esta semana: **Autonomía y funcionalidad (25)** y **Viabilidad (10)**.

## Cuentas

1,000 casos en 12 horas son unos 83 por hora, **1.4 por minuto**. El reto es la **estabilidad**, no la velocidad. Con unos 30 s por caso (S1 midió de 9 a 55 s) y 2 a 4 casos en paralelo hay margen de sobra.

**Presupuesto:** con unos 2,700 tokens por caso medidos en S1, 1,000 casos son unos 2.7 millones de tokens más la visión. Antes de arrancar, multiplicar por la tarifa real de `grok-4.6` del panel y comprobar que alcanzan los créditos del tramo.

## Entregables

- [ ] `docker-compose.yml` con PostgreSQL, API y worker
- [ ] Despliegue en un servidor (Railway, Render, Fly.io o un VPS) con reinicio automático
- [ ] Worker concurrente con idempotencia probada
- [ ] Corrida de 1,000 casos en 12 horas con fallos inyectados
- [ ] `eval/reporte_s4.md`

## Tareas

### T1 · Contenedores y base de datos (día 1)

- Migrar de SQLite a PostgreSQL (mismas tablas de S2, con índices en `case_id`, `estado` y `llave_idempotencia`).
- `docker-compose.yml`: `db` (PostgreSQL con volumen), `worker` (`restart: always`), `api` (FastAPI).
- Variables de entorno desde el panel del servidor, nunca dentro de la imagen.
- **Aceptación:** `docker compose up` desde cero procesa un lote de 10 casos.

### T2 · Worker concurrente (día 1–2)

- `cotejai/worker.py`: toma casos `RECIBIDO` con `SELECT ... FOR UPDATE SKIP LOCKED`, para que dos workers nunca agarren el mismo caso.
- **Concurrencia adaptativa con backpressure** ([MEJORAS_COTEJAI.md §3](MEJORAS_COTEJAI.md)): empezar en 2. Ante un 429 o una latencia media mayor al doble de la normal, bajar a 1 y esperar con backoff exponencial; después de 10 casos seguidos sin error, subir de uno en uno hasta un máximo de 4. Cada cambio de concurrencia va a la bitácora.
- **Memoria en procesos largos:** reiniciar el worker cada 200 casos (el estado está en la base, así que retoma sin perder nada) y registrar el uso de memoria en el latido.
- **Ritmo constante:** una cola con tasa máxima de casos por minuto, para no agotar el límite del gateway.
- **Latido:** el worker escribe `heartbeat` cada 30 s; un caso tomado por un worker sin latido por 5 minutos vuelve a `RECIBIDO`.
- **Aceptación:** con 2 workers, 100 casos y ninguno procesado dos veces.

### T3 · Idempotencia de punta a punta (día 2)

- Cada acción externa (correo, webhook, cambio de pago) usa la llave `case_id:herramienta:version` en la tabla `actions` con restricción única.
- Si el worker muere después de enviar el correo y antes de guardar el estado, al reiniciar ve la llave y no reenvía.
- **Aceptación:** test que mata el worker en cada punto del ciclo y comprueba cero duplicados.

### T4 · Monitoreo (día 2)

- `GET /health` y `GET /stats`: casos por estado, casos por minuto, errores de la última hora, costo acumulado.
- Alertas (al webhook del notificador) cuando: no se procesa nada en 10 minutos, la tasa de error pasa del 10 %, o el costo acumulado pasa del presupuesto.
- **Aceptación:** apagar el worker dispara la alerta en menos de 10 minutos.

### T5 · Ensayo de 1 hora (día 3)

- 100 casos a ritmo real, con los mismos fallos que en la corrida final.
- Revisar la bitácora, corregir y repetir hasta que salga limpio.

### T6 · Corrida de 12 horas con inyección de fallos (día 4)

| Hora aproximada | Fallo inyectado | Lo que debe verse en la bitácora |
| --- | --- | --- |
| 1 | Matar el worker | Reinicio automático, casos retomados, cero duplicados |
| 3 | Cortar PostgreSQL 1 minuto | Reintentos de conexión y continuación |
| 5 | Simular 429 del gateway | Backoff y baja de ritmo |
| 7 | SAT caído | Circuit breaker, casos con `sat_no_verificado` |
| 9 | Remisiones corruptas | `RECEIPT_UNREADABLE` y escalamiento, sin caída |
| 11 | Reiniciar el servidor | Retoma sola |

Anotar hora exacta y efecto de cada fallo en `runs/s4_incidentes.md`.

### T7 · Reporte de S4 (día 5)

`eval/reporte_s4.md`:
- Casos procesados, duración y casos por hora.
- Distribución de estados finales y tasa de resolución autónoma.
- Exactitud sobre la muestra con etiqueta.
- Cada incidente: qué pasó, cómo se recuperó, tiempo de recuperación.
- Acciones duplicadas: debe ser **0**.
- Créditos gastados por modelo, costo por caso y fuga total detectada.

## Riesgos

| Riesgo | Mitigación |
| --- | --- |
| Se acaban los créditos a mitad de corrida | Calcular presupuesto antes; alerta de costo; tope en el worker |
| Límite de peticiones del gateway | Ritmo constante y backoff; preguntar el límite a los organizadores |
| El servidor se duerme o reinicia | Plan de pago o VPS; `restart: always` |
| Una falla tumba todo | Cada caso en su propio `try`; el error queda en el caso, no en el worker |

## Después de S4: Track 2

Con el servidor desplegado y la API pública, la integración con Platica de [README_PLATICA.md](../README_PLATICA.md) es conectar: notificador `platica`, webhook de respuesta y herramientas registradas en el agente de Platica.

Herramientas que expondrá el servidor MCP (`cotejai/api/mcp_server.py`, de [MEJORAS_COTEJAI.md §5](MEJORAS_COTEJAI.md)):

| Herramienta | Qué responde | Ojo con Platica |
| --- | --- | --- |
| `consultar_estado_factura(uuid)` | Estado, códigos, fuga y monto a pagar | Rápida: lectura de la base |
| `auditar_lote_compras(fecha_inicio, fecha_fin)` | Un `job_id` al instante | El timeout de Platica es de 60 s como máximo: nunca esperar al lote |
| `obtener_expediente_discrepancia(case_id)` | Resumen del caso con evidencia | Recortar a menos de 32 KB |

El modelo de precios de MEJORAS ($0.04 USD de costo, $0.50 USD de precio, margen de 90 %) es una **hipótesis**: el costo real sale de esta corrida de S4 y el precio se valida con clientes en Track 2 ([mercado.md](mercado.md)).
