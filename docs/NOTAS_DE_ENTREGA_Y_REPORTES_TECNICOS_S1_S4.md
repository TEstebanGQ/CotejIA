# CotejAI — Compendio Oficial: Notas de Entrega y Reportes Técnicos (S1 a S4)

**Proyecto:** CotejAI — Agente Autónomo de Cuentas por Pagar (Three-Way Matching)  
**Track:** Platica.mx × Campuslands · Reto Agente 2026 · Track 1  
**Repositorio GitHub:** [github.com/TEstebanGQ/CotejIA](https://github.com/TEstebanGQ/CotejIA)  
**Reporte Técnico General (Google Drive):** [https://drive.google.com/file/d/1rQduagkfqgl3EAuQ8Pq6AvGvsouCu5qp/view?usp=drivesdk](https://drive.google.com/file/d/1rQduagkfqgl3EAuQ8Pq6AvGvsouCu5qp/view?usp=drivesdk)

---

## 📌 Índice de Contenidos
1. [Notas de Entrega — Semana 2 (S2): Herramientas Reales y Web UI Forense](#1-notas-de-entrega--semana-2-s2)
2. [Notas de Entrega — Semana 3 (S3): Subsanación, Dataset Balanceado y Extracción Estratificada](#2-notas-de-entrega--semana-3-s3)
3. [Notas de Entrega — Semana 4 (S4): Semana de Carga (1,000 Unidades y 12h Desatendido)](#3-notas-de-entrega--semana-4-s4)
4. [Reportes Técnicos Ejecutivos por Semana (S1, S2, S3, S4)](#4-reportes-técnicos-ejecutivos-por-semana)
5. [Matriz Consolidada de Telemetría e Impacto Financiero](#5-matriz-consolidada-de-telemetría)
6. [Enlaces Oficiales de Videos y Evidencias](#6-enlaces-oficiales-de-videos-y-evidencias)

---

## 1. Notas de Entrega — Semana 2 (S2)
**Hito:** Herramientas Reales de Function Calling con Grok 4.6 y Web UI Forense en Tiempo Real  
**Video Walkthrough Oficial (1080p con Locución y Subtítulos):** [https://drive.google.com/file/d/1MV6u6blB3NIIUkO24vIQslKmx6L2VH7i/view?usp=drivesdk](https://drive.google.com/file/d/1MV6u6blB3NIIUkO24vIQslKmx6L2VH7i/view?usp=drivesdk)

### 1. QUÉ SE LOGRÓ:
• **Implementación de 5 herramientas reales de Function Calling con Grok 4.6 (vía gateway `api.reto.pltk.mx`):**
  1) `cotejar_caso`: Three-Way Matching determinista con cálculo exacto en centavos mediante Python `Decimal` y redondeo `ROUND_HALF_UP` entre Orden de Compra ERP, Remisión física/digital y Factura CFDI 4.0 XML (garantía de cero alucinaciones aritméticas).
  2) `inspeccionar_remision_vision`: Grok 4.6 Vision multimodal con prefiltro de nitidez (varianza Laplaciana) para transcribir notas manuscritas del almacenista (*"Recibidos solo 80 pzas. Merma en transporte (-20)"*) y firmas/sellos de bodega (`OC-004`).
  3) `consultar_tipo_cambio`: Conexión oficial al webservice del Sistema de Información Económica (SIE) de Banco de México (Serie FIX SF43718) para auditar facturas en divisas extranjeras en tiempo real (`OC-006` neutralizó **$19,707.24 MXN** de sobreprecio cambiario no pactado).
  4) `consultar_sat_69b_y_soap`: Validación del estatus fiscal del timbre ante el webservice SOAP del SAT y cruce directo contra la Lista Negra de EFOS del Art. 69-B del CFF (`OC-007` con pago cancelado al 100% por proveedor listado como EFOS Definitivo).
  5) `solicitar_nota_credito`: Generación e invocación de webhooks con clave compuesta de idempotencia en BD y compuerta *Policy Gate* (resolución autónoma si discrepancia $\le \$5,000$ MXN; requerimiento de aprobación humana de contraloría si el monto excede dicho límite en `OC-010`).
• **Ejecución y Auditoría del Lote S2 (10 Casos: OC-001 a OC-010):**
  - **Fuga Total Retenida:** **$42,211.24 MXN** protegidos preventivamente en la tesorería de Platica.mx.
  - **Monto Seguro Autorizado para Pago:** **$154,989.26 MXN**.
  - **Resolución Autónoma:** 90.0% de los casos resueltos sin necesidad de escalamiento técnico.
• **Interfaz Web SPA Forense de Alta Gama:**
  - Sistema dark-mode Shadcn UI (`#121316`) con visor multidocumental en pestañas: Remisión física/digital, CFDI 4.0 XML estructurado con descarga y Orden de Compra ERP.
  - Soporte multidivisa para 180 monedas internacionales, selector rápido `⌘K`, filtros interactivos por estado y badges de auditoría.

### 2. QUÉ FALLÓ Y CÓMO SE SOLUCIONÓ:
• **Fallo 1 (Inestabilidad en WebService SOAP del SAT):** Latencias elevadas y caídas del portal del SAT en horarios hábiles causaban bloqueos en el agente.  
  *Solución:* Se implementó un patrón **Circuit Breaker** con umbral de 3 caídas consecutivas. Al activarse, conmuta a estado `OPEN`, clasifica el caso como `SAT_NO_VERIFICADO` y consulta la base de datos local indexada de la Lista 69-B en $< 2\text{ ms}$ para no paralizar la auditoría.
• **Fallo 2 (Imágenes desenfocadas de remisiones de almacén):** Fotografías con baja luminosidad o movimiento tomadas por los almacenistas provocaban lecturas dudosas en modelos de visión.  
  *Solución:* Se integró un prefiltro de visión con **Varianza Laplaciana (OpenCV/Pillow)**. Si el score de nitidez es inferior a 28.0, la imagen se rechaza automáticamente bajo el código `RECEIPT_UNREADABLE` (`OC-005`), impidiendo aprobaciones indebidas y solicitando una nueva fotografía.
• **Fallo 3 (Riesgo de solicitudes duplicadas de notas de crédito):** Posibles reintentos de red o desconexiones podían generar múltiples emisiones hacia el ERP o proveedor.  
  *Solución:* Se incorporaron **claves de idempotencia compuestas** (`CASE_ID:TIPO:FOLIO`) con índice único en SQLite WAL / PostgreSQL (`invoices_seen` y `actions`), garantizando que cada reclamo se envíe una única vez.
• **Fallo 4 (Expedientes puramente electrónicos sin foto escaneada):** En casos como `OC-001`, `OC-002` y `OC-003`, los evaluadores no tenían imagen visual que auditar.  
  *Solución:* Se diseñó la **Ficha Digital de Recepción**, un documento estructurado que renderiza en pantalla sellos de patio, firmas electrónicas y observaciones de almacén con el mismo rigor que una remisión física.

### 3. TELEMETRÍA Y COSTO POR TAREA:
• **Tokens Totales Consumidos (10 casos reales con Grok 4.6):** 125,816 tokens de entrada y 3,460 tokens de salida a lo largo de 39 llamadas a herramientas.  
• **Latencia Promedio por Caso:** 27.9 segundos (incluyendo razonamiento LLM, visión multimodal e invocación a APIs externas).  
• **Costo Total de Inferencia:** **$0.2862 USD** (**$5.35 MXN**).  
• **Costo Promedio por Expediente:** **$0.0286 USD** (**$0.535 MXN** por factura auditada).  
• **Multiplicador de Retorno de Inversión (ROI):** **7,886x** ($42,211.24 MXN retenidos frente a $5.35 MXN invertidos en inferencia).  
• **Ahorro Operativo vs Revisión Humana:** Reducción del **99.4%** frente al costo estándar de analista de cuentas por pagar (~$5.00 USD por factura).

---

## 2. Notas de Entrega — Semana 3 (S3)
**Hito:** Subsanación Rigurosa de Evaluaciones, Dataset Balanceado con Ground Truth y Extracción Estratificada  
**Reporte Técnico Detallado S3:** [`eval/reporte_s3.md`](eval/reporte_s3.md)  
**Documento de Subsanación Explícita:** [`docs/SUBSANACION_RETROALIMENTACION_S1_S2.md`](docs/SUBSANACION_RETROALIMENTACION_S1_S2.md)

### 1. QUÉ SE LOGRÓ:
• **Construcción y Versionado del Dataset S3 (36 Casos Balanceados):**
  - Generación determinista y reproducible con semilla (`datasets/s3/S3-001` a `S3-036`) a partir de un catálogo de 40 SKUs reales con 4 regímenes fiscales (IVA 16%, 8% región fronteriza norte, exento y retenciones).
  - Cada caso incluye su tríada documental (`oc.json`, `remision.pdf` / `remision.png`, `cfdi.xml`) y su archivo `esperado.json` (Ground Truth independiente calculado con Python `Decimal` y redondeo contable `ROUND_HALF_UP` al centavo).
• **Extracción Documental Estratificada (Tiered Extraction):**
  - **Nivel 1 (Parser Estructurado `pdfplumber` a costo $0):** Procesa el **91.67% de los documentos** (33 de 36 expedientes) directamente de PDFs vectoriales limpios sin llamar a ningún LLM ni gastar tokens de la pasarela.
  - **Nivel 2 (Visión Multimodal Grok 4.6 Vision):** Se activa exclusivamente en el **8.33% de los casos** (3 expedientes) que presentan fotos físicas, sellos superpuestos o tachaduras manuscritas.
• **Evaluador Automatizado y Métricas Oficiales de Precisión (`python -m eval.evaluar`):**
  - **Aprobaciones Indebidas (Falsos Positivos):** **0.00%** (Meta: $\le 0.0\%$). Ningún pago erróneo fue aprobado.
  - **Reclamos Indebidos (Falsos Negativos):** **0.00%** (Meta: $< 5.0\%$). Cero reclamos injustificados a proveedores limpios.
  - **Exactitud de Importes (Aritmética Decimal):** **100.00%** (Meta: $> 95.0\%$).
  - **Exactitud de Códigos SAT y Tipificación:** **100.00%** (Meta: $> 90.0\%$).
  - **Exactitud de Extracción Documental:** **100.00%** (Meta: $> 90.0\%$).
• **Impacto Financiero en S3:**
  - Fuga total detectada y retenida: **$534,195.78 MXN** prevenidos al 100.00%.

### 2. QUÉ FALLÓ Y CÓMO SE SOLUCIONÓ:
• **Fallo 1 (Extracción innecesaria con modelos de visión de alto costo):** En iteraciones tempranas, se enviaban todos los documentos a Grok Vision, encareciendo el costo por factura en casos que eran PDFs nativos perfectamente legibles.  
  *Solución:* Se implementó `src/extraccion.py` con una compuerta estricta: primero se inspecciona la capa de texto y metadatos con `pdfplumber`. Si la extracción extrae las tablas con coherencia y sin marcadores de tachadura manual, se resuelve en Nivel 1 ($0 costo). Si detecta imagen raster o anomalías, delega a Nivel 2.
• **Fallo 2 (Discrepancias sutiles en redondeos fiscales de 3 decimales):** Facturas con partidas donde el IVA unitario daba fracciones de milésimas generaban discrepancias de $0.01 MXN con el total del CFDI.  
  *Solución:* Alineación con la regla del Anexo 20 del SAT: redondeo a nivel partida mediante `ROUND_HALF_UP` a 2 decimales antes de acumular la suma global de impuestos.
• **Fallo 3 (Sobreajuste a casos sintéticos sin semilla):** La retroalimentación de S1/S2 señaló falta de reproducibilidad en los lotes de prueba.  
  *Solución:* Se refactorizó `datasets/generate.py` con argumento `--semilla 42`, garantizando que cualquier evaluador pueda recrear los 36 casos byte a byte con idénticos UUIDs, montos y sellos.

### 3. TELEMETRÍA Y COSTO POR TAREA:
• **Consumo de Inferencia:** 33 de 36 casos operaron a **$0.0000 USD** gracias a Nivel 1.  
• **Costo Promedio del Lote S3:** **$0.0028 USD** (**$0.052 MXN** por expediente), reduciendo en un **90.2%** el costo unitario respecto a la versión inicial.  
• **Latencia Media:** $< 120\text{ ms}$ para expedientes Nivel 1 y $\sim 11.4\text{ s}$ para expedientes Nivel 2 con Grok Vision.  
• **ROI en S3:** **18,670x** ($534,195.78 MXN prevenidos vs ~$28.60 MXN de costo teórico proyectado en inferencia).

---

## 3. Notas de Entrega — Semana 4 (S4)
**Hito:** Semana de Carga (1,000 Unidades de Trabajo y 12 Horas de Operación Continua Desatendida)  
**Video Oficial de Evidencia de Carga S4 (1080p Playwright):** [https://drive.google.com/file/d/13h-CPBloLvk40kZMb9bgiRzJ0jDVzgLK/view?usp=drivesdk](https://drive.google.com/file/d/13h-CPBloLvk40kZMb9bgiRzJ0jDVzgLK/view?usp=drivesdk)  
**Reporte Técnico Formal S4:** [`eval/reporte_s4.md`](eval/reporte_s4.md)  
**Bitácoras Oficiales:** [`runs/bitacora_s4.jsonl`](runs/bitacora_s4.jsonl) | [`runs/bitacora_s4.csv`](runs/bitacora_s4.csv)

### 1. QUÉ SE LOGRÓ:
• **1,000 Unidades de Trabajo de Punta a Punta (`datasets/s4/S4-0001` a `S4-1000`):**
  - Cada unidad de trabajo representa un expediente completo resuelto de inicio a fin: lectura de OC, extracción de remisión, validación de sello y estructura de CFDI 4.0 XML, consulta SOAP de vigencia en el SAT, cruce con lista 69-B (EFOS), auditoría cambiaria Banxico FIX, three-way matching y resolución de compuerta *Policy Gate*.
  - Catálogo diverso con distribución balanceada: 40% casos limpios (`MATCH_OK`), 25% faltantes físicos (`QTY_SHORT`), 15% sobreprecios y cálculos fiscales erróneos (`PRICE_UP` / `TAX_MISMATCH`), 10% sobreprecios cambiarios (`FX_OVERCHARGE`), 5% EFOS Definitivos del SAT 69-B (`SUPPLIER_69B`) y 5% CFDIs cancelados o duplicados (`CFDI_CANCELADO` / `DUPLICATE`).
• **12 Horas de Operación Desatendida (`scripts/run_s4_12h_daemon.py`):**
  - Pacing matemático calibrado: $43,200\text{ s} \div 1,000\text{ tareas} \approx 43.2\text{ s}$ por caso con jitter orgánico ($\pm 4.0\text{ s}$) para simular llegada orgánica de facturas y evitar 429 Rate Limits en la pasarela oficial (`RETO_KEY`).
  - **Fuga de memoria cero:** Ejecución forzada de `gc.collect()` cada 10 ciclos para mantener la huella de memoria RAM estable en $\sim 85\text{ MB}$ RSS sin degradación a lo largo de 12 horas.
• **Capa de Resiliencia Industrial (`src/resilience.py`):**
  - Decorador `@with_resilience` con backoff exponencial, jitter y soporte de la cabecera `Retry-After`.
  - Fallbacks inteligentes de contingencia: validación sintáctica de CFDI ante caídas de SAT SOAP y uso del último FIX del día ante micro-cortes de Banxico.
  - Registro automático de cada incidencia en `runs/bitacora_resiliencia.jsonl`.
• **Bitácora Oficial Dual en Streaming Inmutable:**
  - Registro atómico con `flush()` y `os.fsync()` tanto en JSONL (`runs/bitacora_s4.jsonl`) como en CSV (`runs/bitacora_s4.csv`) con 18 columnas de telemetría forense.
• **Telemetría Web en Tiempo Real:**
  - Endpoints `/api/s4/status` y `/api/s4/bitacora` conectados a una tarjeta KPI en la UI que muestra pulso verde de ejecución, progreso porcentual, conteo de tareas y costo acumulado.
• **Suite de Pruebas Unitarias Ampliada:** 70 pruebas pasando al 100% en 6.54 segundos (`tests/test_s4_resiliencia.py`).

### 2. QUÉ FALLÓ Y CÓMO SE SOLUCIONÓ:
• **Fallo 1 (Riesgo de saturación de la pasarela Grok por concurrencia desmedida):** Ejecutar 1,000 tareas en paralelo o en bucle ciego saturaba la pasarela con respuestas `429 Too Many Requests`.  
  *Solución:* Se programó el motor de *pacing adaptativo*: el daemon calcula el tiempo que tardó la inferencia y descuenta ese lapso del intervalo objetivo de 43.2s, inyectando un jitter estocástico de $\pm 4$ segundos. Además, el decorador de resiliencia intercepta cualquier código 429 y espera el tiempo estipulado en `Retry-After`.
• **Fallo 2 (Acumulación de memoria en procesos de larga duración en Python):** Objetos de Pillow, cadenas XML y sesiones HTTP residuales aumentaban el consumo de RAM tras cientos de ejecuciones.  
  *Solución:* Limpieza explícita del contexto, cierre inmediato de conexiones httpx y disparo programado de `gc.collect()` cada 10 iteraciones, logrando cero fugas de memoria (comportamiento plano durante 12 horas).
• **Fallo 3 (Pérdida de datos ante una eventual caída del sistema):** Escrituras con búfer estándar de disco podían perder registros de bitácora si ocurría un corte eléctrico o reinicio forzado.  
  *Solución:* Persistencia streaming con llamada a `os.fsync(f.fileno())` inmediatamente después de procesar cada expediente.

### 3. TELEMETRÍA Y COSTO POR TAREA:
• **Tasa de Éxito de la Corrida:** **100.0%** de expedientes auditados sin interrupciones catastróficas.  
• **Latencia Media:** 47.03 segundos por ciclo completo de auditoría y pacing.  
• **Costo Unitario por Tarea:** **$0.0329 USD** (**$0.6168 MXN** por expediente completo).  
• **Costo Total Proyectado para 1,000 Tareas:** ~$32.90 USD (~$615.00 MXN), plenamente cubierto dentro de los créditos de la pasarela del torneo.  
• **Ahorro frente a Auditoría Humana (1,000 facturas):** Un equipo humano costaría ~$5,000 USD ($93,500 MXN); CotejAI resuelve el lote completo con un ahorro del **99.3%**.

---

## 4. Reportes Técnicos Ejecutivos por Semana

```mermaid
timeline
    title Evolución Técnica de CotejAI (S1 a S4)
    section Sprint 1 : Motor Determinista : Three-Way Matching Decimal : Modelado de Casos Base
    section Sprint 2 : 5 Herramientas Function Calling : Grok 4.6 Vision : SAT 69-B & Banxico FIX : Web UI Forense
    section Sprint 3 : Subsanación de Evaluaciones : Dataset 36 Casos Ground Truth : Extracción Nivel 1 ($0 Costo)
    section Sprint 4 : Carga Masiva 1,000 Casos : Runner 12h Desatendido : Resiliencia 429 & Bitácora Dual
```

### Resumen Arquitectónico por Semana:
- **Semana 1 (Fundación):** Construcción del cotejador determinista puro. Modelado de datos en Python `Decimal` para evitar errores de punto flotante en cálculos contables e impuestos de facturas CFDI 4.0.
- **Semana 2 (Autonomía e Integración Real):** Incorporación del ciclo ReAct con Grok 4.6 a través del Gateway oficial. Integración de visión multimodal, consulta SOAP en vivo del SAT, catálogo de EFOS 69-B, consulta cambiaria a Banxico y desarrollo de la SPA forense.
- **Semana 3 (Rigor Metodológico y Eficiencia de Costos):** Implementación de la extracción estratificada (`pdfplumber` 91.67% a costo $0 + visión para el 8.33%). Evaluación formal de 36 casos con 0.00% de aprobaciones indebidas y $534,195.78 MXN retenidos.
- **Semana 4 (Escala Industrial y Carga Continua):** Generación de 1,000 casos sintéticos completos (`datasets/s4/`). Orquestación del daemon de 12 horas continuas sin intervención humana, resiliencia ante errores de red, bitácora dual inmutable en disco y telemetría web en vivo.

---

## 5. Matriz Consolidada de Telemetría

| Parámetro | Semana 2 (S2) | Semana 3 (S3) | Semana 4 (S4) |
| :--- | :---: | :---: | :---: |
| **Casos / Tareas Evaluadas** | 10 casos reales | 36 casos balanceados | 1,000 tareas completas |
| **Tiempo de Corrida** | ~4.6 minutos | ~2.5 minutos | 12 horas continuas |
| **Modalidad de Extracción** | 100% Grok Vision / Determinista | 91.67% N1 ($0) / 8.33% N2 | Tiered Extraction + Resiliencia |
| **Fuga de Capital Prevenida** | **$42,211.24 MXN** | **$534,195.78 MXN** | **Escalada a volumen completo** |
| **Aprobaciones Indebidas** | 0.00% | 0.00% | 0.00% |
| **Exactitud de Cálculos** | 100.00% | 100.00% | 100.00% |
| **Costo Promedio por Tarea** | $0.0286 USD ($0.535 MXN) | $0.0028 USD ($0.052 MXN) | $0.0329 USD ($0.616 MXN) |
| **ROI Financiero** | **7,886x** | **18,670x** | **Alta rentabilidad corporativa** |
| **Suite de Tests Automatizados**| 45 pasando | 56 pasando | **70 pasando (100% verde)** |

---

## 6. Enlaces Oficiales de Videos y Evidencias

- 📄 **Reporte Técnico Formal en PDF (Google Drive):**  
  [https://drive.google.com/file/d/1rQduagkfqgl3EAuQ8Pq6AvGvsouCu5qp/view?usp=drivesdk](https://drive.google.com/file/d/1rQduagkfqgl3EAuQ8Pq6AvGvsouCu5qp/view?usp=drivesdk)
- 🎬 **Video Oficial Sprint 4 (Semana de Carga - 12h Desatendido):**  
  [https://drive.google.com/file/d/13h-CPBloLvk40kZMb9bgiRzJ0jDVzgLK/view?usp=drivesdk](https://drive.google.com/file/d/13h-CPBloLvk40kZMb9bgiRzJ0jDVzgLK/view?usp=drivesdk)
- 🎬 **Video Walkthrough Sprint 2/3 (Herramientas Reales, Grok Vision y Web UI):**  
  [https://drive.google.com/file/d/1MV6u6blB3NIIUkO24vIQslKmx6L2VH7i/view?usp=drivesdk](https://drive.google.com/file/d/1MV6u6blB3NIIUkO24vIQslKmx6L2VH7i/view?usp=drivesdk)
- 📊 **Bitácora Inmutable S4 (JSONL):** [`runs/bitacora_s4.jsonl`](../runs/bitacora_s4.jsonl)
- 📊 **Bitácora Inmutable S4 (CSV):** [`runs/bitacora_s4.csv`](../runs/bitacora_s4.csv)
- 📖 **Subsanación de Observaciones Evaluadores:** [`docs/SUBSANACION_RETROALIMENTACION_S1_S2.md`](SUBSANACION_RETROALIMENTACION_S1_S2.md)
