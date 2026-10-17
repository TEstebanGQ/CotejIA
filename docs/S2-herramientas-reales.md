# S2 · Herramientas reales

## Objetivo

Que el agente actúe sobre el mundo con **tres herramientas reales**, sobreviva a errores sin intervención humana y lo demuestre en **10 ejecuciones seguidas** grabadas en un video de 2 minutos.

## Lo que pide el reto

| Requisito | Cómo lo cumplimos |
| --- | --- |
| 3 herramientas reales | `document_parser` (remisión con Grok Vision), `fiscal` (SAT y lista 69-B), `notifier` (solicitud de nota de crédito y escalamiento) |
| Manejo de errores | Reintentos con backoff, errores devueltos a Grok, circuit breaker del SAT, validación Pydantic con reintento, límite de pasos y de tiempo |
| 10 ejecuciones | `python main.py audit --all` sobre 10 casos distintos, sin tocar nada |
| Video de 2 minutos | Guion en la sección 8 |

Criterios de la rúbrica que mueve esta semana: **Autonomía y funcionalidad (25)** e **Ingeniería sobre Grok (20)**.

## Entregables

- [ ] Paquete `cotejai/` con el registro de herramientas (contrato en [00-framework.md](00-framework.md))
- [ ] 3 familias de herramientas funcionando, cada una con tests
- [ ] Compuerta de políticas con `config/policies.yaml`
- [ ] Persistencia en SQLite: `cases`, `case_events`, `llm_calls`, `invoices_seen`
- [ ] Facturas parciales y duplicados detectados
- [ ] 10 casos en `datasets/` y una corrida guardada en `runs/`
- [ ] Video de 2 minutos y README actualizado

## Tareas

### T1 · Migrar a la estructura del framework (día 1)

- Mover `src/matching.py` → `cotejai/matching/engine.py` y `src/cfdi.py` → `cotejai/fiscal/mx.py`.
- Crear `cotejai/tools/registro.py` con el decorador `@herramienta` y `definiciones_para_grok()`.
- Reescribir `cotejar_caso` y `cerrar_caso` como herramientas registradas.
- **Aceptación:** los 14 tests actuales pasan sin cambiar su lógica y `audit --all` da los mismos veredictos.

### T2 · Persistencia y estados (día 1–2)

Tablas en SQLite (`cotejai.db`, misma estructura que PostgreSQL en S4):

| Tabla | Columnas clave |
| --- | --- |
| `cases` | `case_id`, `estado`, `version`, `codigos`, `monto_a_pagar`, `fuga`, `creado`, `actualizado` |
| `case_events` | `case_id`, `de`, `a`, `actor`, `motivo`, `fecha` |
| `llm_calls` | `case_id`, `paso`, `herramienta`, `model`, `prompt_tokens`, `cached_tokens`, `completion_tokens`, `reasoning_tokens`, `costo_usd`, `latencia_ms`, `reintentos` |
| `actions` | `llave_idempotencia` (única), `case_id`, `herramienta`, `args`, `resultado`, `fecha` |
| `invoices_seen` | `uuid` (único), `rfc_emisor`, `folio`, `total`, `case_id` |

- `cotejai/core/estados.py`: `transicionar(case_id, a, actor, motivo)` rechaza transiciones no válidas y sube `version`.
- **Aceptación:** matar el proceso a mitad de un caso y relanzarlo no duplica ninguna fila de `actions`.

### T3 · Herramienta 1: `leer_remision` con Grok Vision (día 2–3)

- Entrada: imagen JPG/PNG o PDF escaneado (PyMuPDF a PNG a 200 dpi).
- Salida: `RemisionExtraida` (folio, fecha, OC de referencia, líneas con `confianza`, sello, firma, observaciones a mano).
- Llamada con `response_format` y `detail: "high"`; validar con Pydantic; un reintento con el error de validación si falla.
- **Plan B** si el gateway no acepta `response_format`: una herramienta `registrar_remision` cuyos argumentos son el esquema.
- Reglas en el prompt: "si no se lee, `null` y baja la confianza; nunca inventes una cantidad".
- Confianza de una línea < 0.85, o sin sello o sin firma → código `RECEIPT_UNREADABLE` → pedir nueva foto al almacén; al segundo intento fallido, escalar.
- **Prueba primero en el gateway** (antes de escribir la herramienta): una llamada con imagen y otra con `response_format` usando el modelo que usas (`grok-4.6`). Anotar el resultado en el README.
- **Aceptación:** 5 remisiones fotografiadas extraídas; en las ilegibles devuelve `null`, no un número.

### T4 · Herramienta 2: `validar_cfdi_sat` y `verificar_proveedor_69b` (día 3)

- **SAT:** servicio de consulta de estado (Vigente / Cancelado / No encontrado) con `satcfdi`. Para los CFDI sintéticos, un simulador que responde según `datasets/sat_simulado.json`.
- **Circuit breaker:** 5 fallos seguidos → estado `sat_no_verificado` durante 10 minutos; el caso sigue y queda marcado, no bloquea el lote.
- **69-B:** descargar el CSV del SAT una vez al día a `datasets/cache/69b.csv`; buscar el RFC emisor. Definitivo → `SUPPLIER_69B`.
- **Aceptación:** con el servicio apagado el lote termina y los casos quedan como `sat_no_verificado`.

### T5 · Herramienta 3: `solicitar_nota_credito` y `escalar_caso` (día 4)

- Interfaz `Notificador` con `NotificadorCorreo` (SMTP) y `NotificadorWebhook` (Discord, Slack o un endpoint de prueba).
- El mensaje lleva: folio y UUID de la factura, monto exacto, motivo por línea y evidencia (foto de la remisión y línea de la OC).
- `escalar_caso` arma el expediente en Markdown y avisa al responsable.
- Ambas son `accion`: pasan por la compuerta y usan llave de idempotencia.
- **Aceptación:** reenviar el mismo caso no manda un segundo correo.

### T6 · Compuerta de políticas (día 4)

`config/policies.yaml`:

```yaml
limite_autonomo_mxn: 5000
codigos_que_escalan: [SUPPLIER_69B, CFDI_CANCELLED, TAX_MISMATCH, SKU_UNMAPPED]
qty_over_po_pct_escala: 0.10
aprobar_pago:
  solo_si_codigos: [MATCH_OK]
veredicto:
  montos_identicos_al_cotejo: true
```

Reglas mínimas, cada una con su test:
1. Un código bloqueante → cualquier `accion` se convierte en `escalar_caso`.
2. `solicitar_nota_credito` con monto > límite autónomo → escalar.
3. `aprobar_pago` con códigos distintos de `MATCH_OK` → rechazar.
4. `cerrar_caso` con montos distintos a los del cotejo → rechazar y devolverle a Grok los montos correctos.
5. `cerrar_caso` con un estado incoherente con los códigos (por ejemplo `APROBADO` con `QTY_SHORT`) → rechazar.

- **Aceptación:** un test fuerza a un modelo falso a proponer `APROBADO` en un caso con faltante y la compuerta lo impide.

### T7 · Facturas parciales y duplicados (día 5)

- **Duplicado:** mismo UUID en `invoices_seen`, o mismo `rfc_emisor + folio + total` → `DUPLICATE` → bloquear el pago.
- **Parcial:** el motor recibe lo ya facturado y lo ya recibido de la OC en casos anteriores. La cantidad a pagar por línea es `min(facturada, recibida_acumulada − pagada_acumulada, ordenada − pagada_acumulada)`.
- **Aceptación:** dos facturas de 50 piezas para una OC de 100 se aprueban; una tercera de 50 sale como `QTY_OVER_PO`.

### T8 · Manejo de errores (transversal)

| Falla | Respuesta |
| --- | --- |
| Timeout, conexión, 429, 5xx del gateway | `tenacity`: 5 intentos, backoff exponencial con jitter, máximo 30 s |
| 400 del gateway | No se reintenta; a la bitácora y escalar |
| Argumentos de herramienta inválidos (`json.loads` o Pydantic) | Se devuelve el error a Grok para que corrija; al segundo fallo, escalar |
| Error dentro de una herramienta | Se devuelve como resultado `{"ok": false}`, no rompe el lote |
| Más de 10 pasos o más de 3 minutos por caso | Escalamiento automático con el motivo |
| SAT caído | Circuit breaker (T4) |

- **Aceptación:** un test por fila con un cliente falso que inyecta la falla.

## Telemetría y costo

- Registrar `usage` completo de cada respuesta. Verificar si el gateway trae `cached_tokens` y `reasoning_tokens`; si no, guardar solo entrada y salida.
- Tarifas en `config/settings.py` por modelo. **Pendiente:** confirmar la tarifa de `grok-4.6` en el panel del reto (el panel muestra el consumo por modelo).
- Header `x-grok-conv-id: <case_id>` en todas las llamadas del caso para aprovechar la caché.

## Casos de la semana (10)

| Caso | Situación | Esperado |
| --- | --- | --- |
| OC-001 | Limpio | APROBADO |
| OC-002 | Faltante de 20 piezas | EN_RECLAMO |
| OC-003 | Alza de precio | EN_RECLAMO |
| OC-004 | Precio dentro de tolerancia | APROBADO |
| OC-005 | IVA mal calculado | ESCALADO |
| OC-006 | Factura duplicada (mismo UUID que OC-001) | ESCALADO o bloqueado |
| OC-007 | Flete no pactado | EN_RECLAMO o ESCALADO |
| OC-008 | Remisión fotografiada legible | según cotejo |
| OC-009 | Remisión sin firma | pedir nueva foto |
| OC-010 | Fuga mayor a $5,000 | ESCALADO |

## Video de 2 minutos (guion)

1. **0:00–0:15** El problema en pesos: "las empresas pagan lo que no recibieron".
2. **0:15–0:30** El diagrama: código calcula, Grok decide, compuerta autoriza.
3. **0:30–1:20** `python main.py audit --all` corriendo los 10 casos sin tocar nada; enseñar un reclamo que llega al correo.
4. **1:20–1:45** La bitácora: `case_events` y `llm_calls` con costo por caso.
5. **1:45–2:00** Un fallo inyectado (SAT caído) y el lote que termina igual.

## Riesgos

| Riesgo | Mitigación |
| --- | --- |
| El gateway no acepta imágenes con `grok-4.6` | Probarlo el día 1; plan B con otro modelo del gateway que tenga visión |
| El servicio del SAT no responde | Circuit breaker y simulador para los CFDI sintéticos |
| La migración rompe lo que funciona | T1 primero, con los tests actuales como red |
