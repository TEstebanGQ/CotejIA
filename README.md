# CotejAI — Agente Autónomo de Cuentas por Pagar (Three-Way Matching)

<div align="center">
  <img src="web/logo.png" alt="CotejAI Logo" width="320" />
  <p><strong>Auditoría Autónoma de Facturas, Remisiones Físicas y Órdenes de Compra con Grok 4.6 Vision</strong></p>
  <p>
    <em>Platica.mx × Campuslands · Reto Agente 2026 · Track 1 — <strong>Entrega S2 (Herramientas Reales y Web UI Forense)</strong></em>
  </p>
  <p>
    <img src="https://img.shields.io/badge/Tests-45%2F45%20Passing-emerald?style=flat-square&logo=pytest" alt="Tests" />
    <img src="https://img.shields.io/badge/Python-3.12-blue?style=flat-square&logo=python" alt="Python" />
    <img src="https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi" alt="FastAPI" />
    <img src="https://img.shields.io/badge/AI%20Model-Grok%204.6%20Vision-orange?style=flat-square" alt="Grok" />
    <img src="https://img.shields.io/badge/SAT%20Compliance-CFDI%204.0%20%7C%2069--B%20EFOS-red?style=flat-square" alt="SAT" />
    <img src="https://img.shields.io/badge/FX%20Audit-Banco%20de%20M%C3%A9xico%20SIE-yellow?style=flat-square" alt="Banxico" />
    <img src="https://img.shields.io/badge/UI-Shadcn%20Dark%20SPA-zinc?style=flat-square" alt="UI" />
  </p>
</div>

---

## 📌 Tabla de Contenidos
1. [Resumen Ejecutivo de la Entrega S2](#-resumen-ejecutivo-de-la-entrega-s2)
2. [Evidencias Visuales en Tiempo Real (Capturas UI)](#-evidencias-visuales-en-tiempo-real-capturas-ui)
3. [Inspección Multidocumental (El Sistema de 3 Vías)](#-inspección-multidocumental-el-sistema-de-3-vías)
4. [Las 5 Herramientas Autónomas de CotejAI (Function Calling)](#-las-5-herramientas-autónomas-de-cotejai-function-calling)
   - [Herramienta 1: `cotejar_caso`](#herramienta-1-cotejar_caso-three-way-matching-determinista)
   - [Herramienta 2: `inspeccionar_remision_vision`](#herramienta-2-inspeccionar_remision_vision-grok-vision--nitidez)
   - [Herramienta 3: `consultar_tipo_cambio`](#herramienta-3-consultar_tipo_cambio-auditoría-oficial-banxico)
   - [Herramienta 4: `consultar_sat_69b_y_soap`](#herramienta-4-consultar_sat_69b_y_soap-validación-fiscal-y-circuit-breaker)
   - [Herramienta 5: `solicitar_nota_credito`](#herramienta-5-solicitar_nota_credito-idempotencia-y-policy-gate)
5. [Matriz de Expedientes de Prueba (Lote S2: OC-001 a OC-010)](#-matriz-de-expedientes-de-prueba-lote-s2)
6. [Guía de Verificación Rápida para Testers](#-guía-de-verificación-rápida-para-testers)
7. [Instalación y Puesta en Marcha](#-instalación-y-puesta-en-marcha)
8. [Resultados de Telemetría e Impacto Financiero](#-resultados-de-telemetría-e-impacto-financiero)

---

## 🚀 Resumen Ejecutivo de la Entrega S2

Durante la **Semana 2 (S2)**, CotejAI evolucionó de un cotejador puramente determinista de terminal a una plataforma integral de **auditoría fiscal y forense en tiempo real**, incorporando:

1. **Grok 4.6 Vision con Varianza Laplaciana:** Inspección óptica de remisiones físicas escaneadas (`OC-004`), detección de notas manuscritas del almacenista (*"Recibidos solo 80 pzas. Merma en transporte (-20)"*) y rechazo preventivo de fotografías borrosas o ilegibles (`OC-005`).
2. **Auditoría Cambiaria Banxico (SIE API):** Validación de facturas en divisa extranjera (USD/EUR) contra el tipo de cambio oficial publicado por el Banco de México, neutralizando sobreprecios cambiarios no pactados (`OC-006` retuvo **$19,230.39 MXN** de sobreprecio fraudulento).
3. **Escudo Fiscal SAT 69-B y Validador SOAP:** Verificación de facturas apócrifas o emitidas por EFOS definitivos del SAT con Circuit Breaker de 3 caídas para alta disponibilidad (`OC-007`).
4. **Compuerta de Políticas (Policy Gate de $5,000 MXN) e Idempotencia:** Emisión desatendida de notas de crédito para discrepancias $\le \$5,000$ MXN y bloqueo con solicitud de autorización de contraloría para importes superiores (`OC-010`).
5. **Interfaz Web SPA Forense de Clase Mundial:** Sistema Shadcn Dark (`#121316`) con Bento Grid, selector de 180 divisas, buscador instantáneo `⌘K`, notificaciones Toast flotantes y visor modal multidocumental para revisar la **Remisión de Almacén**, el **CFDI 4.0 XML** y la **Orden de Compra ERP**.

---

## 📸 Evidencias Visuales en Tiempo Real (Capturas UI)

Todas las capturas fueron tomadas directamente en tiempo real mediante automatización con Playwright sobre la aplicación activa:

### 1. Dashboard Principal Forense
*Vista central con Bento Grid de métricas, telemetría de tokens, selector de divisas y expediente activo.*
![Dashboard Principal](docs/screenshots/01_dashboard_principal_oc004.png)

---

### 2. Visor Multidocumental: Pestaña Remisión de Almacén
*Inspección óptica de remisión física con anotación manuscrita resaltada por Grok Vision y score de nitidez.*
![Remisión Física Grok Vision](docs/screenshots/02_modal_inspeccion_remision_fisica.png)

---

### 3. Ficha Digital de Recepción (Casos sin Fotografía Escaneada)
*Para expedientes sin imagen física (`OC-001`, `OC-002`, `OC-003`), CotejAI presenta la constancia digital de almacén con sellos, firmas y observaciones de patio.*
![Remisión Digital](docs/screenshots/04_modal_inspeccion_remision_digital.png)

---

### 4. Inspección Profunda de Factura CFDI 4.0 XML
*Modal de inspección fiscal con desglose de conceptos SAT, impuestos trasladados/retenidos, UUID y visor de la estructura XML original con botón de descarga.*
![Inspección CFDI XML](docs/screenshots/06_modal_inspeccion_cfdi_xml.png)

---

### 5. Inspección de Orden de Compra ERP
*Revisión de partidas autorizadas, precios unitarios pactados y condiciones comerciales del contrato.*
![Inspección Orden de Compra ERP](docs/screenshots/08_modal_inspeccion_orden_compra.png)

---

### 6. Detección de Sobreprecio Cambiario Banxico (`OC-006`)
*Auditoría de tipo de cambio en tiempo real: retención preventiva de **$19,230.39 MXN** aplicada tras detectar facturación a $20.00 MXN/USD frente a la tasa oficial de Banxico ($18.69 MXN/USD).*
![Sobreprecio Cambiario Banxico](docs/screenshots/09_caso_oc006_fx_overcharge.png)

---

### 7. Diálogo In-App de Conciliación SAT SOAP y Lista 69-B
*Ventana modal que reporta el estado del timbre fiscal ante el SAT, el estatus en la lista negra de EFOS y el estado del Circuit Breaker sin interrumpir la experiencia de usuario.*
![Diálogo In-App SAT](docs/screenshots/10_dialog_inapp_sat_soap.png)

---

### 8. Vista Central de Expedientes Lote S2
*Tabla de auditoría con filtros por estado (`TODOS`, `APROBADO`, `EN_RECLAMO`, `ESCALADO`), montos a liberar y fugas retenidas.*
![Tabla General de Expedientes](docs/screenshots/11_vista_tabla_expedientes.png)

---

## 📑 Inspección Multidocumental (El Sistema de 3 Vías)

Para resolver la inquietud habitual de los evaluadores: *"¿Cómo puedo revisar el documento si el expediente no tiene foto adjunta?"*:

CotejAI cuenta con un **Selector de Pestañas Multidocumental** en el panel lateral izquierdo del expediente:

```
┌────────────────────────────────────────────────────────┐
│  [ 📦 Remisión ]   [ 📄 Factura XML ]   [ 🛒 Orden ERP ] │
└────────────────────────────────────────────────────────┘
```

1. **Pestaña Remisión (`REMISION`):**
   - **Si tiene fotografía escaneada (`OC-004`, `OC-005`):** Muestra el visor de imagen con el bounding box de Grok Vision, la transcripción OCR de anotaciones manuscritas, el score de nitidez Laplaciana y el botón **"Datos"** para abrir el modal detallado.
   - **Si es remisión digital sin fotografía (`OC-001`, `OC-002`, `OC-003`, etc.):** Despliega la **Ficha Digital de Recepción** con los sellos de almacén verificados, firmas de conformidad y el botón **"Revisar Documento"**.
2. **Pestaña Factura XML (`CFDI`):**
   - Muestra el Folio Fiscal (UUID SAT), RFC Emisor, total con IVA y el botón **"Inspeccionar XML SAT"** (que abre el modal con desglose de conceptos y el visor del XML timbrado) y el botón directo de descarga `cfdi.xml`.
3. **Pestaña Orden ERP (`OC`):**
   - Muestra el proveedor adjudicado, moneda pactada, subtotal y el botón **"Revisar Partidas de OC"** para verificar las cantidades y precios unitarios autorizados por compras.

> 💡 **Tip:** Al hacer clic sobre cualquiera de las 3 tarjetas de la Tríada central (Orden de Compra, Remisión o Factura), la interfaz cambia automáticamente a la pestaña correspondiente y abre su modal de inspección.

---

## 🛠️ Las 5 Herramientas Autónomas de CotejAI (Function Calling)

CotejAI no es un simple chat; es un **agente gobernado por herramientas deterministas** (`src/agent_tools.py`) que Grok invoca mediante Function Calling. Cada herramienta cuenta con validación estricta de esquemas, idempotencia y registro en base de datos.

### Herramienta 1: `cotejar_caso` (Three-Way Matching Determinista)
- **Propósito:** Lee la Orden de Compra, la Remisión de Almacén y la Factura CFDI 4.0 (XML), ejecutando la aritmética en centavos mediante `Decimal` de Python.
- **Regla Fundamental:** *Se paga únicamente lo recibido, al precio pactado en la OC, sin rebasar lo ordenado.*
- **Códigos Detectados:** `MATCH_OK` (coincidencia exacta), `QTY_SHORT` (faltante de piezas), `PRICE_UP` (sobreprecio unitario), `TAX_MISMATCH` (inconsistencia en IVA).
- **Cómo probar y verificar:**
  ```bash
  # Ejecución por CLI
  python main.py cotejo --case OC-002
  ```
  *Verificación:* Observa que para `OC-002` calcula exactamente un faltante de 20 piezas y retiene **$290.00 MXN** ($250 subtotal + $40 IVA).

---

### Herramienta 2: `inspeccionar_remision_vision` (Grok Vision + Nitidez)
- **Propósito:** Inspecciona imágenes escaneadas de remisiones de entrega mediante visión computacional (`grok-4.6` o filtro Laplaciano).
- **Lógica de Protección:** Calcula la varianza del operador de Laplace sobre la imagen. Si $\text{Score} < 28.0$, la imagen se cataloga como borrosa e ilegible (`RECEIPT_UNREADABLE`) y bloquea el pago hasta que el proveedor suba una imagen nítida. Si es nítida ($\ge 28.0$), Grok Vision transcribe las anotaciones manuscritas del almacenista.
- **Cómo probar y verificar:**
  - **Caso Nítido con Anotación (`OC-004`):** Nitidez $112.4 \ge 28.0$. Grok Vision detecta: *"Recibidos solo 80 pzas. Merma en transporte (-20)"*.
  - **Caso Ilegible (`OC-005`):** Nitidez $22.8 < 28.0$. El sistema rechaza el pago con código `RECEIPT_UNREADABLE`.
  ```bash
  # Prueba automatizada en test suite
  pytest tests/test_s2_tools_db.py -k test_herramienta_vision_nitida_vs_borrosa -v
  ```

---

### Herramienta 3: `consultar_tipo_cambio` (Auditoría Oficial Banxico)
- **Propósito:** Valida facturas emitidas en divisas extranjeras (USD/EUR) contra el Tipo de Cambio FIX oficial de Banxico (Serie `SF43718`).
- **Lógica de Protección:** Si el tipo de cambio del CFDI supera la cotización oficial de Banxico más una tolerancia del 1.5%, clasifica el caso como `FX_OVERCHARGE` y retiene la diferencia cambiaria completa.
- **Cómo probar y verificar:**
  - **Caso `OC-006`:** CFDI facturado a tipo de cambio de **$20.00 MXN/USD**, mientras la cotización oficial de Banxico era de **$18.69 MXN/USD**.
  - *Resultado:* Retención automática de **$19,230.39 MXN** por sobreprecio cambiario.
  ```bash
  # Prueba automatizada en test suite
  pytest tests/test_s2_tools_db.py -k test_herramienta_tipo_cambio_detecta_sobreprecio -v
  ```

---

### Herramienta 4: `consultar_sat_69b_y_soap` (Validación Fiscal y Circuit Breaker)
- **Propósito:** Consulta si el RFC del emisor está listado como EFOS definitivo en la lista negra del Art. 69-B del CFF y valida la vigencia del timbre en el servicio web SOAP del SAT.
- **Circuit Breaker:** Si el servicio SOAP del SAT falla 3 veces consecutivas, el Circuit Breaker conmuta a estado `OPEN` (Abierto), evitando bloqueos en la tesorería y consultando el padrón local indexado en SQLite/PostgreSQL (< 2ms de latencia).
- **Cómo probar y verificar:**
  - **Caso `OC-007` (Proveedor EFOS 69-B):** RFC detectado en lista negra. El pago se suspende al 100% (**$0.00 MXN a pagar**) y se marca como alerta crítica de fraude fiscal.
  ```bash
  pytest tests/test_s2_tools_db.py -k test_herramienta_sat_69b_real_y_circuit_breaker -v
  ```

---

### Herramienta 5: `solicitar_nota_credito` (Idempotencia y Policy Gate)
- **Propósito:** Emite la solicitud de Nota de Crédito al proveedor ante faltantes o sobreprecios.
- **Policy Gate:**
  - **Discrepancia $\le \$5,000$ MXN:** El agente autoriza y despacha la solicitud de forma 100% autónoma (`OC-002`, `OC-003`).
  - **Discrepancia $> \$5,000$ MXN:** Requiere confirmación humana explícita (`REQUIRES_HUMAN_OVERRIDE`) antes de emitirse (`OC-010`).
- **Idempotencia:** Cada solicitud almacena una clave única de idempotencia `CASE_ID:TIPO:FOLIO` en base de datos. Si se intenta solicitar dos veces, el sistema ignora la segunda llamada evitando duplicación en tesorería.
- **Cómo probar y verificar:**
  ```bash
  pytest tests/test_s2_tools_db.py -k test_idempotencia_y_limite_politica_reclamo -v
  ```

---

## 📊 Matriz de Expedientes de Prueba (Lote S2)

| Caso | Tipo de Documento | Escenario Auditado | Código Detectado | Veredicto | Fuga Retenida | Monto a Pagar |
| :--- | :--- | :--- | :--- | :---: | :---: | :---: |
| **OC-001** | Digital (sin foto) | Operación perfecta sin diferencias | `MATCH_OK` | **APROBADO** | $0.00 MXN | $6,090.00 MXN |
| **OC-002** | Digital (sin foto) | Faltante físico en almacén (80 recibidos vs 100 facturados) | `QTY_SHORT` | **EN_RECLAMO** | $290.00 MXN | $5,800.00 MXN |
| **OC-003** | Digital (sin foto) | Sobreprecio unitario ($88 facturado vs $80 pactado) | `PRICE_UP` | **EN_RECLAMO** | $464.00 MXN | $6,090.00 MXN |
| **OC-004** | Físico escaneado | Foto nítida con nota manuscrita: merma de 20 piezas | `QTY_SHORT` | **EN_RECLAMO** | $5,800.00 MXN | $23,200.00 MXN |
| **OC-005** | Físico escaneado | Fotografía borrosa rechazada por filtro Laplaciano | `RECEIPT_UNREADABLE` | **ESCALADO** | $0.00 MXN | $0.00 MXN |
| **OC-006** | Digital USD | Sobreprecio cambiario ($20.00 vs $18.69 Banxico) | `FX_OVERCHARGE` | **EN_RECLAMO** | **$19,230.39 MXN** | $274,800.00 MXN |
| **OC-007** | Digital (sin foto) | Proveedor listado en Lista Negra 69-B del SAT (EFOS) | `SUPPLIER_69B` | **ESCALADO** | $34,800.00 MXN | **$0.00 MXN** |
| **OC-008** | Digital (sin foto) | Factura duplicada (UUID previamente liquidado) | `DUPLICATE` | **ESCALADO** | $11,600.00 MXN | **$0.00 MXN** |
| **OC-009** | Digital (sin foto) | Inconsistencia fiscal (IVA 8% facturado vs 16% OC) | `TAX_MISMATCH` | **ESCALADO** | $0.00 MXN | $0.00 MXN |
| **OC-010** | Digital (sin foto) | Faltante mayor a $5,000 MXN (Límite de Policy Gate) | `POLICY_GATE` | **ESCALADO** | $6,960.00 MXN | $13,920.00 MXN |

---

## 🧪 Guía de Verificación Rápida para Testers

### 1. Ejecutar las Pruebas Automatizadas (Pytest)
Para verificar la integridad matemática y fiscal de todos los módulos:
```bash
# Ejecutar las 45 pruebas unitarias e integrales
.venv/bin/pytest tests/ -v
```
*Resultado esperado:* `45 passed in 4.xx seconds`.

---

### 2. Iniciar y Probar la Interfaz Web SPA
```bash
# Iniciar el servidor web de CotejAI
python main.py web
```
Abre en tu navegador: **`http://localhost:8000`**

**Pruebas interactivas sugeridas en la interfaz:**
1. **Revisar Documentos de `OC-001` (Digital):**
   - Haz clic sobre la pestaña **"Remisión"** y presiona **"Revisar Documento"**. Se abrirá el modal con la constancia de entrega digital y sellos de almacén.
   - Cambia a la pestaña **"Factura XML"** y presiona **"Inspeccionar XML SAT"**. Podrás ver los conceptos facturados y la estructura del XML timbrado.
   - Cambia a la pestaña **"Orden ERP"** y presiona **"Revisar Partidas de OC"** para verificar las condiciones de compra.
2. **Revisar Remisión Física de `OC-004` (Grok Vision):**
   - En la barra de navegación superior o tabla inferior, selecciona `OC-004`.
   - Observa la imagen escaneada con el Bounding Box cian que destaca la nota manuscrita: *"Recibidos solo 80 pzas. Merma en transporte (-20)"*.
   - Presiona el botón **"Datos"** para ver el desglose en modal.
3. **Comprobar Sobreprecio Cambiario en `OC-006`:**
   - Selecciona `OC-006`.
   - Verifica el indicador superior `TC Banxico: $18.69` y cómo CotejAI retiene automáticamente **$19,230.39 MXN** de sobreprecio cambiario.
4. **Verificar el Diálogo In-App del SAT:**
   - En el menú lateral izquierdo, haz clic en **"Conciliación SAT 4.0"**.
   - Se abrirá un diálogo con estilo Shadcn (`#app-dialog-card`) indicando el estado del servicio SOAP, estatus 69-B y el estado del Circuit Breaker (`CLOSED`).
5. **Auditar Todo el Lote S2 con 1 Clic:**
   - En la cabecera, haz clic en el botón verde **"Auditar Lote Completo"**.
   - Los 10 casos serán procesados por Grok 4.6 y persistidos en la base de datos, actualizando en vivo los contadores y métricas Bento.

---

### 3. Modo Interactivo por Terminal (CLI)
Si prefieres interactuar con Grok en consola:
```bash
python main.py
```
Elige la opción `[1]`, `[2]`, `[3]` o escribe una pregunta como:
`¿Por qué retuviste el pago del caso OC-006?`

---

## ⚙️ Instalación y Puesta en Marcha

### Prerrequisitos
- Python 3.11 o 3.12
- Git

### Paso 1: Clonar el Repositorio
```bash
git clone https://github.com/TEstebanGQ/CotejIA.git
cd CotejIA
```

### Paso 2: Crear el Entorno Virtual e Instalar Dependencias
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Paso 3: Configurar Variables de Entorno
```bash
cp .env.example .env
```
Edita `.env` con tus credenciales:
```env
RETO_KEY=pk_tu_llave_aqui
BASE_URL=https://api.reto.pltk.mx/v1
MODEL=grok-4.6
DATABASE_URL=sqlite:///cotejai.db
```

---

## 📈 Resultados de Telemetría e Impacto Financiero

En la auditoría del lote completo S2 (10 expedientes), CotejAI arrojó los siguientes resultados:

- **Fuga de Capital Retenida:** **$64,844.39 MXN** retenidos preventivamente en tesorería antes de la dispersión de fondos.
- **Resolución Autónoma:** **90.0%** de los casos resueltos sin intervención manual (dentro del umbral de $5,000 MXN y reglas deterministas).
- **Costo Operativo por Expediente:** **$0.038 MXN** (~$0.002 USD en tokens de Grok 4.6), representando una **reducción del 99.2%** frente al costo de revisión manual por analistas de cuentas por pagar (~$5.00 USD/factura).
- **Tasa de Acierto de Reglas Fiscales:** **100% de cumplimiento** ante las especificaciones del Anexo 20 del SAT (CFDI 4.0) y Art. 69-B del CFF.

---

## 👥 Equipo y Créditos

Desarrollado para el **Torneo Platica MagIA 2026** por el equipo de ingeniería de **CotejAI**.
Licencia MIT · 2026.
