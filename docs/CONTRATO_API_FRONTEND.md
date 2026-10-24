# Contrato de Integración Frontend ↔ Backend (FastAPI) — CotejAI S2

> **Para:** Leo (Rama `dev-leo` · Frontend Web)  
> **De:** Tomás (Rama `dev-tomas` · Backend, Agente Grok 4.6, Herramientas Reales y Base de Datos)  
> **Comando para levantar el servidor:** `python main.py web` (corre en `http://localhost:8000`)  
> **Documentación interactiva (Swagger UI):** `http://localhost:8000/docs`

---

## 1. Cómo Levantar y Servir el Frontend

El servidor **FastAPI (`src/api.py`)** ya tiene configurado:
1. **CORS abierto (`allow_origins=["*"]`)**: Puedes consumir `http://localhost:8000/api/...` desde cualquier puerto o directamente desde la raíz `/`.
2. **Servidor Estático Integrado**:
   - `GET /` sirve automáticamente el archivo `web/index.html`.
   - `GET /static/...` sirve cualquier archivo dentro de `web/` (por ejemplo, `<script src="/static/app.js"></script>`).

---

## 2. Catálogo de Endpoints REST (`http://localhost:8000`)

### 2.1. Salud del Sistema y Circuit Breaker SAT
* **Método y Ruta:** `GET /api/health`
* **Uso en UI:** Mostrar en el header si **Grok 4.6** está conectado, qué motor de BD está activo (`PostgreSQL 16` o `SQLite WAL`) y el semáforo del **Circuit Breaker del SAT** (`CLOSED` = Verde / `OPEN` = Ámbar).
* **Respuesta JSON:**
  ```json
  {
    "ok": true,
    "servicio": "CotejAI Backend S2",
    "motor_db": "PostgreSQL 16",
    "grok_conectado": true,
    "modelo": "grok-4.6",
    "circuit_breaker_sat": {
      "estado": "CLOSED",
      "fallos_consecutivos": 0,
      "max_fallos": 3,
      "segundos_restantes_apertura": 0
    }
  }
  ```

---

### 2.2. KPIs Financieros y Telemetría de Tokens (Cards Superiores y Gráficas)
* **Método y Ruta:** `GET /api/metrics`
* **Uso en UI:** Alimentar las tarjetas Bento superiores (Dinero Retenido, Monto a Pagar, Conteo de Estados, Acciones Idempotentes, Costo en USD y ROI).
* **Respuesta JSON:**
  ```json
  {
    "motor_db": "SQLite WAL",
    "casos_auditados": 10,
    "conteo_estados": {
      "APROBADO": 1,
      "EN_RECLAMO": 3,
      "ESCALADO": 6
    },
    "total_facturado_mxn": "195462.75",
    "total_a_pagar_mxn": "148155.10",
    "fuga_total_retenida_mxn": "47307.65",
    "acciones_idempotentes_registradas": 3,
    "rfcs_69b_cargados": 10,
    "telemetria_llm": {
      "llamadas_totales": 24,
      "prompt_tokens": 18420,
      "completion_tokens": 2150,
      "costo_total_usd": 0.0583,
      "roi_estimado_x": 43401.5
    },
    "circuit_breaker_sat": {
      "estado": "CLOSED",
      "fallos_consecutivos": 0,
      "max_fallos": 3,
      "segundos_restantes_apertura": 0
    },
    "grok_conectado": true
  }
  ```

---

### 2.3. Listar los 10 Casos del Lote (`OC-001` a `OC-010`)
* **Método y Ruta:** `GET /api/cases`
* **Uso en UI:** Llenar la tabla principal de casos con sus badges de estado, códigos (`MATCH_OK`, `QTY_SHORT`, `PRICE_UP`, `RECEIPT_UNREADABLE`, `FX_OVERCHARGE`, `SUPPLIER_69B`, `TAX_MISMATCH`, `DUPLICATE`, `SAT_NO_VERIFICADO`) y montos.
* **Respuesta JSON:**
  ```json
  {
    "ok": true,
    "total": 10,
    "casos": [
      {
        "case_id": "OC-004",
        "proveedor_rfc": "AAA010101AAA",
        "uuid": "00000004-0000-4000-8000-000000000000",
        "moneda": "MXN",
        "tipo_cambio": "1",
        "tiene_imagen_remision": true,
        "imagen_url": "/api/cases/OC-004/image",
        "total_cfdi_mxn": "6090.00",
        "monto_a_pagar_mxn": "5800.00",
        "fuga_detectada_mxn": "290.00",
        "codigos_calculados": ["QTY_SHORT"],
        "auditado_en_db": true,
        "estado_final": "EN_RECLAMO",
        "version_db": 1,
        "herramientas_usadas": ["leer_remision_imagen", "cotejar_caso", "enviar_alerta_reclamo_real", "cerrar_caso"],
        "resumen": "Se detectó faltante de 20 piezas en TORN-001 mediante visión documental...",
        "actualizado_en": "2026-10-24T18:20:00Z"
      }
    ]
  }
  ```

---

### 2.4. Detalle Completo de un Expediente + Visor de Imagen
* **Método y Ruta:** `GET /api/cases/{case_id}` (ej. `/api/cases/OC-004`)
* **Imagen PNG directa:** `GET /api/cases/{case_id}/image` (devuelve `image/png` listo para `<img src="/api/cases/OC-004/image">`)
* **Uso en UI:** Abrir el modal o panel *Split-Screen* mostrando la Orden de Compra (`oc`), la Remisión (`remision` + foto `imagen_url`), la Factura (`cfdi`), los hallazgos (`cotejo.detalle`) y el historial de `acciones_idempotentes`.

---

### 2.5. Ejecutar Auditoría con el Agente Grok 4.6
* **Auditar un solo caso:** `POST /api/audit/{case_id}` (ej. `POST /api/audit/OC-004`)
* **Auditar los 10 casos seguidos:** `POST /api/audit-all`
* **Respuesta JSON de `POST /api/audit/{case_id}`:**
  ```json
  {
    "ok": true,
    "modo": "grok-4.6",
    "veredicto": {
      "case_id": "OC-004",
      "estado_final": "EN_RECLAMO",
      "codigos": ["QTY_SHORT"],
      "fuga_detectada_mxn": "290.00",
      "monto_a_pagar_mxn": "5800.00",
      "resumen": "Faltante de 20 unidades en TORN-001 según nota manuscrita en remisión física."
    },
    "uso": {
      "prompt_tokens": 1420,
      "completion_tokens": 185,
      "llamadas": 4,
      "segundos": 3.8,
      "rechazos": 0,
      "herramientas": ["leer_remision_imagen", "cotejar_caso", "enviar_alerta_reclamo_real", "cerrar_caso"]
    }
  }
  ```

---

### 2.6. Endpoints Directos de las 3 Familias de Herramientas Reales (Para Botones de Demo)

1. **Probar Grok Vision sobre la Foto (`OC-004` nítida o `OC-005` borrosa):**
   * `POST /api/tools/vision/{case_id}`
   * Devuelve `nitidez_optica`, `legible`, `confianza_minima`, `codigo_alerta` (`null` o `"RECEIPT_UNREADABLE"`) y `remision_extraida`.
2. **Probar Tipo de Cambio en Vivo (Catálogo de 180 Divisas ISO 4217 / Anexo 20 SAT):**
   * **Listar las 180 divisas:** `GET /api/currencies` $\rightarrow$ devuelve `{"ok": true, "total_divisas": 180, "divisas": [{"codigo": "AED", "nombre": "Dírham de Emiratos Árabes Unidos"}, ...]}`.
   * **Consultar cotización hacia MXN:** `POST /api/tools/fx` con body `{"moneda": "EUR", "tipo_cambio_cfdi": "24.50"}`
   * Devuelve `tasa_oficial_mxn` en tiempo real desde `open.er-api.com`, `nombre_moneda`, `variacion_pct` y `codigo_alerta: "FX_OVERCHARGE"`.
3. **Probar Consulta SAT SOAP + Lista 69-B Real + Circuit Breaker:**
   * `POST /api/tools/sat/{case_id}` (ej. `OC-007` para ver `SUPPLIER_69B` o `OC-010` para disparar el Circuit Breaker `SAT_NO_VERIFICADO`).
4. **Probar Envío de Reclamo e Idempotencia en Base de Datos:**
   * `POST /api/tools/reclamo/{case_id}` (ej. `POST /api/tools/reclamo/OC-002`)
   * **Primera llamada:** devuelve `"idempotencia_bloqueada": false` y envía el webhook HTTP real.
   * **Segunda llamada (Demo de Idempotencia):** devuelve `"idempotencia_bloqueada": true` y el mensaje `"Acción ya ejecutada... se evitó envío duplicado"`.

---

### 2.7. Chat Conversacional con CotejAI (`grok-4.6`)
* **Método y Ruta:** `POST /api/chat`
* **Body JSON:**
  ```json
  {
    "mensaje": "¿Por qué se escaló el caso OC-007 y qué pasa con el caso OC-004?",
    "historial": []
  }
  ```
* **Respuesta JSON:**
  ```json
  {
    "ok": true,
    "respuesta": "El caso OC-007 fue escalado porque el proveedor AAA080808AAA aparece como Definitivo en la Lista 69-B del SAT...",
    "historial": [...],
    "uso": {"prompt_tokens": 950, "completion_tokens": 140}
  }
  ```
