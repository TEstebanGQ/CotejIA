# CotejAI — Catálogo de Herramientas y Resiliencia (Semana 2 · S2)

Documento técnico de especificación de **herramientas reales**, **estrategias de resiliencia ante errores**, **persistencia en base de datos** y **guion de demostración** para el hito S2 del torneo *Platica MagIA Tournament (Reto Agente 2026)*.

---

## 1. Objetivos y Criterios del Hito S2

| Criterio del Torneo | Meta Técnica en CotejAI |
| :--- | :--- |
| **Mínimo 3 herramientas reales** | • `leer_remision_fisica` (Grok Vision / Multimodal)<br>• `validar_sat_y_lista_69b` (Fiscal / SOAP SAT + EFOS)<br>• `solicitar_nota_credito` (Acción externa con idempotencia) |
| **Manejo de errores / Resiliencia** | Circuit breaker para caída del SAT, tolerancia a fotos borrosas, reintentos con backoff exponencial y deduplicación estricta de notificaciones. |
| **10 ejecuciones continuas** | Lote de 10 casos diversos en `datasets/` procesados de forma desatendida. |
| **Video de 2 minutos** | Demostración visual del agente operando sobre los 10 casos, mostrando recuperación ante fallos y la bitácora auditable. |

---

## 2. Catálogo de Herramientas Principales (La Terna Obligatoria)

### Herramienta 1: `leer_remision_fisica` (Visión Documental Multimodal)
* **Propósito:** Extraer datos tabulares, firmas y sellos desde imágenes de remisiones de papel (JPG/PNG o PDF escaneado).
* **Parámetros de entrada:**
  ```json
  {
    "case_id": "OC-004",
    "ruta_imagen": "datasets/OC-004/remision_foto.png"
  }
  ```
* **Salida estructurada:**
  ```json
  {
    "folio_remision": "REM-8821",
    "fecha_entrega": "2026-10-15",
    "tiene_sello_almacen": true,
    "tiene_firma_recepcion": true,
    "lineas": [
      {
        "sku": "TORN-001",
        "descripcion": "Tornillo hexagonal 1/2",
        "cantidad_recibida": "80",
        "confianza": 0.95
      }
    ],
    "observaciones_manuales": "Se reciben 80 pzas; faltaron 20 por merma de transporte"
  }
  ```
* **Manejo de fallos y resiliencia:**
  * **Foto ilegible / borrosa (confianza < 0.85):** No inventa valores. Devuelve código `RECEIPT_UNREADABLE`, solicita reintento y, si falla por segunda vez, escala el expediente a humano.
  * **Falta de sello o firma:** Marca advertencia de recepción no certificada para condicionar el pago.

---

### Herramienta 2: `validar_sat_y_lista_69b` (Validación Fiscal y Antifraude)
* **Propósito:** Verificar el estatus tributario de la factura y del emisor en tiempo real ante las bases oficiales mexicanas.
* **Componentes:**
  1. **Webservice SOAP del SAT:** Consulta si el UUID está `Vigente`, `Cancelado` o `No encontrado`.
  2. **Lista 69-B (EFOS del SAT):** Cruza el RFC del proveedor con el listado oficial de empresas con operaciones presuntamente simuladas.
* **Manejo de fallos (*Circuit Breaker*):**
  * El servicio público del SAT presenta intermitencias frecuentes. Si se registran 3 fallos consecutivos de conexión (timeout o 5xx), la herramienta **no tumba el lote**:
  * Activa el estado `SAT_NO_VERIFICADO` durante una ventana de 10 minutos, permitiendo que la auditoría continúe sobre las reglas comerciales y dejando el caso marcado para verificación posterior.
  * **Si el RFC emisor está en la lista 69-B:** El caso se congela de inmediato bajo `SUPPLIER_69B` y se escala a la dirección jurídica/fiscal sin posibilidad de pago.

---

### Herramienta 3: `solicitar_nota_credito` (Acción y Notificación Externa)
* **Propósito:** Emitir la solicitud formal de compensación al proveedor ante faltantes o sobreprecios, dentro del límite de autonomía ($5,000 MXN).
* **Parámetros de entrada:**
  ```json
  {
    "case_id": "OC-002",
    "rfc_proveedor": "AAA010101AAA",
    "uuid_factura": "4A12B34C-...",
    "monto_nota_credito_mxn": "290.00",
    "motivo": "Faltante de 20 piezas en SKU TORN-001",
    "llave_idempotencia": "OC-002:nota_credito:v1"
  }
  ```
* **Manejo de fallos (*Idempotencia y Reintentos*):**
  * La acción queda registrada en la tabla `actions` antes del envío.
  * Si la llamada a la red (webhook/correo) falla por caída temporal, el agente reintenta con backoff exponencial.
  * Si el proceso se reinicia a mitad de la tarea, **la llave de idempotencia impide enviar un segundo mensaje duplicado** al proveedor.

---

## 3. Herramientas Complementarias (Power-Ups de Alto Valor)

### Herramienta 4: `reconciliar_sku_ambiguo` (Reconciliación Semántica de Catálogos)
* **Problema real:** Los catálogos entre cliente y proveedor casi nunca coinciden textualmente.
  * OC: `Caja Cinta Canela 48mm x 100m Tuck (24 piezas)`.
  * Factura CFDI: `CT-CAN-TUCK-100` con unidad `Pieza`.
* **Comportamiento:** Grok analiza las descripciones y devuelve:
  * Nivel de similitud semántica.
  * Factor de conversión (ej. $1\text{ caja} = 24\text{ piezas}$).
* **Caché de alias:** Todo emparejamiento validado se almacena en la tabla `sku_aliases` para que futuras facturas del mismo proveedor se resuelvan en $0.00$ ms sin gastar tokens.

### Herramienta 5: `verificar_duplicidad_historica` (Prevención de Doble Pago)
* **Comportamiento:** Consulta en SQLite (`invoices_seen`) si el UUID del CFDI o el par `RFC_Emisor + Folio + Total` ya fue pagado en los últimos 90 días.
* **Impacto:** Si detecta duplicidad, emite código `DUPLICATE` y congela el trámite automáticamente.

---

## 4. Matriz de Resiliencia y Manejo de Errores

| Escenario de Error | Comportamiento del Agente | Impacto en la Auditoría |
| :--- | :--- | :--- |
| **Timeout o 429 en Grok** | Reintento automático con *exponential backoff* y *jitter* (hasta 5 intentos). | El proceso se pausa unos segundos y reanuda sin perder estado. |
| **Servicio SOAP del SAT caído** | El *circuit breaker* conmuta a `SAT_NO_VERIFICADO` tras 3 fallos. | El lote continúa procesándose sin bloquearse. |
| **Foto de remisión rota o borrosa** | Extracción con confianza $< 0.85$ devuelve `null` y código `RECEIPT_UNREADABLE`. | Pide reintento o escala formalmente a almacén. |
| **Reinicio abrupto del worker** | Recuperación transaccional desde SQLite WAL mode. | Retoma desde el último estado sin duplicar acciones externas. |
| **Monto propuesto fuera de límite** | La compuerta `policy_gate` rechaza la acción autónoma. | Convierte la acción en `escalar_caso` con expediente prearmado. |

---

## 5. Arquitectura de Persistencia (SQLite en Modo WAL)

Para soportar las 10 ejecuciones de S2 y las 1,000 unidades de trabajo de S4, la base de datos local `cotejai.db` se configura con:
```sql
PRAGMA journal_mode = WAL;
PRAGMA busy_timeout = 5000;
PRAGMA synchronous = NORMAL;
```

### Esquema de Tablas:
1. **`cases`:** `case_id`, `estado` (`RECIBIDO`, `COTEJADO`, `EN_RECLAMO`, `APROBADO`, `ESCALADO`), `version`, `fuga_mxn`, `monto_pagar_mxn`.
2. **`actions`:** `llave_idempotencia` (PK), `case_id`, `herramienta`, `payload`, `fecha_creacion`.
3. **`llm_calls`:** Registro de telemetría por cada llamada (tokens in/out, modelo, latencia ms, costo USD).
4. **`invoices_seen`:** Registro de facturas procesadas para detección instantánea de duplicados.
5. **`sku_aliases`:** Memoria de catálogo cruzado (RFC proveedor $\leftrightarrow$ SKU interno).

---

## 6. Guion Estratégico para el Video de 2 Minutos (S2)

* **0:00 - 0:25 · Presentación del problema:** Mostrar una remisión física con notas a mano y una factura CFDI con faltante de mercancía.
* **0:25 - 0:55 · Ejecución del Lote (10 casos en vivo):** Correr `python main.py audit --all`. Mostrar la terminal procesando los 10 casos en paralelo/secuencia con indicadores en vivo.
* **0:55 - 1:25 · Demostración de Resiliencia:** 
  * Mostrar cómo el agente detecta un CFDI cancelado y un proveedor en lista 69-B.
  * Simular la caída del webservice del SAT y evidenciar cómo el *circuit breaker* mantiene vivo el lote.
* **1:25 - 1:45 · Acción Externa y Deduplicación:** Mostrar el webhook recibido con la solicitud de nota de crédito y probar que al relanzar el caso no se duplica el mensaje.
* **1:45 - 2:00 · Resumen de Valor:** Tabla final en consola con el dinero total retenido, costo ínfimo en tokens y retorno de inversión (ROI).
