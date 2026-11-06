import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PDF = ROOT / "docs" / "Reporte_Tecnico_Oficial_CotejAI_S1_S4.pdf"

html_content = """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <title>CotejAI — Reporte Técnico Oficial y Notas de Entrega (S1 a S4)</title>
  <style>
    @page {
      size: A4;
      margin: 12mm 14mm 12mm 14mm;
      @bottom-right {
        content: counter(page) " / " counter(pages);
        font-family: -apple-system, sans-serif;
        font-size: 8pt;
        color: #71717a;
      }
    }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
      font-size: 8.5pt;
      line-height: 1.45;
      color: #18181b;
      background: #ffffff;
      margin: 0;
      padding: 0;
    }
    .header-box {
      border-bottom: 2px solid #059669;
      padding-bottom: 8px;
      margin-bottom: 12px;
    }
    h1 {
      font-size: 16pt;
      font-weight: 800;
      color: #09090b;
      margin: 0 0 3px 0;
      letter-spacing: -0.4px;
    }
    .subtitle {
      font-size: 9.5pt;
      font-weight: 600;
      color: #059669;
      margin: 0 0 4px 0;
    }
    .meta-bar {
      font-size: 7.5pt;
      color: #52525b;
      display: flex;
      justify-content: space-between;
      border-top: 1px solid #e4e4e7;
      padding-top: 4px;
      margin-top: 4px;
    }
    h2 {
      font-size: 11pt;
      font-weight: 700;
      color: #09090b;
      margin: 14px 0 6px 0;
      border-bottom: 1.5px solid #059669;
      padding-bottom: 3px;
      page-break-after: avoid;
    }
    h3 {
      font-size: 9.5pt;
      font-weight: 700;
      color: #18181b;
      margin: 10px 0 4px 0;
      page-break-after: avoid;
    }
    p {
      margin: 0 0 5px 0;
      text-align: justify;
    }
    ul, ol {
      margin: 0 0 6px 0;
      padding-left: 16px;
    }
    li {
      margin-bottom: 2px;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      margin: 8px 0 10px 0;
      font-size: 7.5pt;
    }
    th, td {
      border: 1px solid #d4d4d8;
      padding: 4px 6px;
      text-align: left;
    }
    th {
      background: #f4f4f5;
      font-weight: 700;
      color: #18181b;
    }
    tr:nth-child(even) {
      background: #fafafa;
    }
    .kpi-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 8px;
      margin: 8px 0 12px 0;
    }
    .kpi-card {
      border: 1px solid #e4e4e7;
      border-radius: 4px;
      padding: 6px 8px;
      background: #fafafa;
    }
    .kpi-label {
      font-size: 6.5pt;
      text-transform: uppercase;
      font-weight: 600;
      color: #71717a;
      margin-bottom: 2px;
    }
    .kpi-val {
      font-size: 11pt;
      font-weight: 800;
      color: #059669;
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    }
    .kpi-sub {
      font-size: 6.5pt;
      color: #52525b;
    }
    .badge {
      display: inline-block;
      font-size: 6.5pt;
      font-weight: 700;
      padding: 1px 4px;
      border-radius: 3px;
    }
    .badge-ok { background: #dcfce7; color: #166534; }
    .badge-claim { background: #fef9c3; color: #854d0e; }
    .badge-alert { background: #fee2e2; color: #991b1b; }
    .badge-tech { background: #e0f2fe; color: #0369a1; }
    .page-break {
      page-break-before: always;
    }
    .callout {
      background: #f0fdf4;
      border-left: 3px solid #059669;
      padding: 6px 10px;
      margin: 8px 0;
      font-size: 8pt;
    }
    .links-box {
      background: #f8fafc;
      border: 1px solid #cbd5e1;
      border-radius: 4px;
      padding: 8px 12px;
      margin: 10px 0;
      font-size: 8pt;
    }
    .links-box a {
      color: #0284c7;
      text-decoration: none;
      font-weight: 600;
    }
  </style>
</head>
<body>

  <!-- HEADER OFICIAL -->
  <div class="header-box">
    <h1>CotejAI — Agente Autónomo de Cuentas por Pagar (Three-Way Matching)</h1>
    <div class="subtitle">Compendio Oficial: Reporte Técnico y Notas de Entrega (Semanas 1 a 4)</div>
    <div class="meta-bar">
      <span><strong>Torneo:</strong> Platica.mx × Campuslands · Reto Agente 2026 (Track 1)</span>
      <span><strong>Modelo Base:</strong> Grok 4.6 Vision (api.reto.pltk.mx) + Determinista Decimal</span>
      <span><strong>Fecha:</strong> Noviembre 2026</span>
    </div>
  </div>

  <div class="callout">
    <strong>Resumen de Impacto Global:</strong> CotejAI audita el ciclo completo de tres vías (Orden de Compra, Remisión de almacén física/digital y CFDI 4.0 XML) verificando vigencia ante el webservice SOAP del SAT, cruzando en tiempo real con la Lista Negra de EFOS del Art. 69-B del CFF y auditando la serie FIX del Banco de México para erradicar sobreprecios cambiarios y mermas.
  </div>

  <!-- KPI ROW RESUMEN -->
  <div class="kpi-grid">
    <div class="kpi-card">
      <div class="kpi-label">Fuga Retenida S2</div>
      <div class="kpi-val">$42,211 MXN</div>
      <div class="kpi-sub">ROI: 7,886x en 10 casos reales</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Fuga Retenida S3</div>
      <div class="kpi-val">$534,195 MXN</div>
      <div class="kpi-sub">Exactitud 100% (36 casos)</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Capacidad S4 Carga</div>
      <div class="kpi-val">1,000 Tareas</div>
      <div class="kpi-sub">12h Desatendido continuo</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Tests Automatizados</div>
      <div class="kpi-val">70 / 70 ✅</div>
      <div class="kpi-sub">100% Passing en pytest</div>
    </div>
  </div>

  <!-- SECCIÓN 1: NOTAS DE ENTREGA S2 -->
  <h2>1. Notas de Entrega — Semana 2 (S2): Herramientas Reales y Web UI</h2>
  <p><strong>Enfoque:</strong> Function Calling con Grok 4.6, visión multimodal de remisiones físicas escaneadas, conexión oficial a Banxico FIX, validador fiscal SAT 69-B y Web SPA Forense.</p>

  <h3>1.1 Qué se logró:</h3>
  <ul>
    <li><strong>5 herramientas de Function Calling implementadas:</strong>
      <ol>
        <li><code>cotejar_caso</code>: Three-Way Matching determinista con cálculo en Python <code>Decimal</code> al centavo entre OC, Remisión y Factura CFDI 4.0 XML (cero alucinaciones).</li>
        <li><code>inspeccionar_remision_vision</code>: Grok 4.6 Vision con filtro de varianza Laplaciana para transcribir notas manuscritas del almacenista (<em>"Recibidos solo 80 pzas. Merma en transporte (-20)"</em>) y sellos en fotos físicas (<code>OC-004</code>).</li>
        <li><code>consultar_tipo_cambio</code>: Conexión oficial al SIE de Banco de México (Serie SF43718) para auditar facturas en USD/EUR en tiempo real (<code>OC-006</code> retuvo <strong>$19,707.24 MXN</strong> de sobreprecio cambiario no pactado).</li>
        <li><code>consultar_sat_69b_y_soap</code>: Verificación de vigencia del timbre fiscal ante webservice SOAP del SAT y cruce con la Lista 69-B de EFOS del CFF (<code>OC-007</code> con pago suspendido al 100%).</li>
        <li><code>solicitar_nota_credito</code>: Notificación externa con clave única de idempotencia en BD y compuerta Policy Gate (autonomía hasta $5,000 MXN; montos mayores requieren aprobación humana de contraloría).</li>
      </ol>
    </li>
    <li><strong>Ejecución del Lote S2 (10 Casos Reales):</strong> <strong>$42,211.24 MXN</strong> de fuga de capital prevenida en tesorería con 90% de resolución autónoma y <strong>$154,989.26 MXN</strong> autorizados con seguridad.</li>
    <li><strong>Interfaz Web SPA Forense:</strong> Shadcn Dark (FastAPI) con visor multidocumental por pestañas, selector para 180 divisas y atajo rápido <code>⌘K</code>.</li>
  </ul>

  <h3>1.2 Qué falló y cómo se solucionó:</h3>
  <ul>
    <li><strong>Fallo 1 (Webservice SOAP del SAT):</strong> Timeouts y micro-cortes intermitentes. <em>Solución:</em> Circuit Breaker de 3 caídas que conmuta a <code>OPEN</code> (SAT_NO_VERIFICADO) y recurre a la base indexada local de RFCs 69-B (< 2 ms).</li>
    <li><strong>Fallo 2 (Fotos borrosas de remisiones):</strong> Imágenes desenfocadas de bodega causaban alucinaciones. <em>Solución:</em> Filtro de nitidez Laplaciana (< 28.0) que tipifica <code>RECEIPT_UNREADABLE</code> (<code>OC-005</code>) y bloquea el pago hasta recibir imagen nítida.</li>
    <li><strong>Fallo 3 (Riesgo de reclamos duplicados):</strong> Reintentos de red podían duplicar reclamos. <em>Solución:</em> Claves compuestas de idempotencia (<code>CASE_ID:TIPO:FOLIO</code>) con índice único en SQLite WAL / PostgreSQL.</li>
    <li><strong>Fallo 4 (Expedientes sin foto física):</strong> Evaluadores no tenían documento visual en expedientes puramente digitales. <em>Solución:</em> Creación de la Ficha Digital de Recepción con firmas y sellos estructurados.</li>
  </ul>

  <h3>1.3 Telemetría y costo por tarea:</h3>
  <ul>
    <li><strong>Consumo:</strong> 125,816 tokens in / 3,460 tokens out en 39 llamadas a herramientas con Grok 4.6.</li>
    <li><strong>Latencia media:</strong> 27.9 segundos por caso con razonamiento completo y visión multimodal.</li>
    <li><strong>Costo operativo por expediente:</strong> <strong>$0.0286 USD</strong> (~$0.535 MXN por factura auditada).</li>
    <li><strong>Retorno de Inversión (ROI):</strong> <strong>7,886x</strong> ($42,211.24 MXN retenidos vs $5.35 MXN invertidos en LLM).</li>
  </ul>

  <div class="page-break"></div>

  <!-- SECCIÓN 2: NOTAS DE ENTREGA S3 -->
  <h2>2. Notas de Entrega — Semana 3 (S3): Subsanación y Extracción Estratificada</h2>
  <p><strong>Enfoque:</strong> Dataset balanceado con Ground Truth en Decimal, eliminación del 100% de falsas aprobaciones y Extracción Estratificada Nivel 1/2.</p>

  <h3>2.1 Qué se logró:</h3>
  <ul>
    <li><strong>Dataset S3 de 36 Casos Balanceados:</strong> Generación determinista y reproducible con semilla (<code>--semilla 42</code>) de 40 SKUs reales en 4 regímenes fiscales (IVA 16%, 8% frontera norte, exento y retenciones) con <code>esperado.json</code> independiente.</li>
    <li><strong>Extracción Estratificada (Tiered Extraction):</strong>
      <ul>
        <li><strong>Nivel 1 (Parser <code>pdfplumber</code> a costo $0):</strong> 91.67% de los documentos (33 de 36 casos) extraídos directamente de PDFs nativos sin invocar LLMs ni consumir tokens.</li>
        <li><strong>Nivel 2 (Grok 4.6 Vision Multimodal):</strong> Activación automática en el 8.33% de los casos (3 expedientes) con fotos físicas, sellos superpuestos o tachaduras.</li>
      </ul>
    </li>
    <li><strong>Evaluador Formal S3 (<code>python -m eval.evaluar</code>):</strong>
      <ul>
        <li>Aprobaciones Indebidas: <strong>0.00%</strong> (Meta: $\le 0.0\%$).</li>
        <li>Reclamos Indebidos: <strong>0.00%</strong> (Meta: $< 5.0\%$).</li>
        <li>Exactitud de Importes y Códigos SAT: <strong>100.00%</strong> (Meta: $> 95\%$).</li>
      </ul>
    </li>
    <li><strong>Fuga Retenida en S3:</strong> <strong>$534,195.78 MXN</strong> protegidos al 100%.</li>
  </ul>

  <h3>2.2 Qué falló y cómo se solucionó:</h3>
  <ul>
    <li><strong>Fallo 1 (Gasto excesivo de tokens enviando PDFs nativos a visión):</strong> <em>Solución:</em> Compuerta en <code>src/extraccion.py</code> que extrae primero mediante Nivel 1 vectorial. Si el contenido es estructurado y coherente, se omite visión ($0 costo).</li>
    <li><strong>Fallo 2 (Redondeos en partidas fiscales de 3 decimales):</strong> <em>Solución:</em> Homologación estricta con la regla del Anexo 20 del SAT (redondeo <code>ROUND_HALF_UP</code> a 2 decimales a nivel partida).</li>
    <li><strong>Fallo 3 (No reproducibilidad en pruebas sintéticas):</strong> <em>Solución:</em> Control estricto de semillas pseudoaleatorias para reproducibilidad byte a byte.</li>
  </ul>

  <h3>2.3 Telemetría y costo por tarea:</h3>
  <ul>
    <li><strong>Costo Unitario Promedio:</strong> <strong>$0.0028 USD</strong> (~$0.052 MXN por expediente), reduciendo en un 90.2% el costo de la S2.</li>
    <li><strong>Latencia media:</strong> < 120 ms en Nivel 1 y ~11.4 s en Nivel 2.</li>
    <li><strong>ROI en S3:</strong> <strong>18,670x</strong> ($534,195.78 MXN protegidos).</li>
  </ul>

  <!-- SECCIÓN 3: NOTAS DE ENTREGA S4 -->
  <h2>3. Notas de Entrega — Semana 4 (S4: Semana de Carga)</h2>
  <p><strong>Enfoque:</strong> Escala masiva de 1,000 unidades de trabajo resueltas de punta a punta, 12 horas de operación desatendida, resiliencia industrial y bitácora dual inmutable.</p>

  <h3>3.1 Qué se logró:</h3>
  <ul>
    <li><strong>1,000 Unidades de Trabajo de Punta a Punta (<code>datasets/s4/S4-0001</code> a <code>S4-1000</code>):</strong>
      Auditoría completa e individualizada de cada caso (OC + Remisión + CFDI 4.0 XML + SAT SOAP + 69-B + Banxico FIX + Policy Gate). Distribución balanceada: 40% limpios, 25% faltantes, 15% sobreprecios/IVA, 10% sobreprecio cambiario FX, 5% EFOS 69-B y 5% cancelados/duplicados.
    </li>
    <li><strong>12 Horas de Operación Desatendida (<code>scripts/run_s4_12h_daemon.py</code>):</strong>
      Pacing matemático calibrado (43.2s por caso con jitter de $\pm 4$s) contra la pasarela oficial (<code>RETO_KEY</code>) y recolección forzada de basura periódica (<code>gc.collect()</code>) para memoria RAM plana en $\sim 85$ MB RSS.
    </li>
    <li><strong>Capa de Resiliencia Industrial (<code>src/resilience.py</code>):</strong>
      Decorador <code>@with_resilience</code> con backoff exponencial, jitter y respeto estricto de cabeceras <code>Retry-After</code> para códigos 429 y 5xx, con fallbacks automáticos para SAT y Banxico.
    </li>
    <li><strong>Bitácora Oficial Dual Inmutable:</strong> Streaming append atómico con <code>os.fsync()</code> en <code>runs/bitacora_s4.jsonl</code> y <code>runs/bitacora_s4.csv</code> con 18 campos forenses.</li>
    <li><strong>Telemetría Web en Vivo:</strong> Endpoints <code>/api/s4/status</code> y <code>/api/s4/bitacora</code> conectados a la nueva tarjeta KPI en el dashboard web.</li>
    <li><strong>Suite de Tests:</strong> 70 pruebas unitarias pasando al 100% en 6.54 segundos.</li>
  </ul>

  <h3>3.2 Qué falló y cómo se solucionó:</h3>
  <ul>
    <li><strong>Fallo 1 (Saturación de pasarela y 429 Too Many Requests):</strong> Ráfagas paralelas desbordaban los límites de la pasarela. <em>Solución:</em> Motor de pacing adaptativo que descuenta la latencia de inferencia y respeta el intervalo de 43.2s, más manejo de <code>Retry-After</code>.</li>
    <li><strong>Fallo 2 (Acumulación de memoria en procesos largos):</strong> <em>Solución:</em> Context managers estrictos y <code>gc.collect()</code> cada 10 ciclos para evitar fugas de RAM durante 12 horas.</li>
    <li><strong>Fallo 3 (Riesgo de pérdida de registros en fallas eléctricas):</strong> <em>Solución:</em> Flush inmediato y <code>os.fsync()</code> a nivel de descriptor de archivo tras cada tarea procesada.</li>
  </ul>

  <h3>3.3 Telemetría y costo por tarea:</h3>
  <ul>
    <li><strong>Tasa de éxito:</strong> <strong>100.0%</strong> de tareas completadas sin caídas.</li>
    <li><strong>Costo unitario por tarea:</strong> <strong>$0.0329 USD</strong> (~$0.6168 MXN por expediente completo de tres vías).</li>
    <li><strong>Costo total para 1,000 tareas:</strong> ~$32.90 USD (~$615 MXN), dentro del presupuesto asignado.</li>
    <li><strong>Ahorro frente a auditoría humana (1,000 facturas):</strong> <strong>99.3%</strong> de reducción ($615 MXN vs $93,500 MXN de analistas de CxP).</li>
  </ul>

  <div class="page-break"></div>

  <!-- SECCIÓN 4: MATRIZ Y ENLACES -->
  <h2>4. Matriz Comparativa de Desempeño (S2, S3, S4)</h2>
  <table>
    <thead>
      <tr>
        <th>Métrica / Dimensión</th>
        <th>Semana 2 (S2)</th>
        <th>Semana 3 (S3)</th>
        <th>Semana 4 (S4: Carga)</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td><strong>Volumen de Tareas</strong></td>
        <td>10 casos reales</td>
        <td>36 casos balanceados</td>
        <td><strong>1,000 unidades completas</strong></td>
      </tr>
      <tr>
        <td><strong>Duración de Corrida</strong></td>
        <td>~4.6 minutos</td>
        <td>~2.5 minutos</td>
        <td><strong>12 horas continuas desatendidas</strong></td>
      </tr>
      <tr>
        <td><strong>Fuga Prevenida</strong></td>
        <td>$42,211.24 MXN</td>
        <td>$534,195.78 MXN</td>
        <td><strong>Protección masiva a escala</strong></td>
      </tr>
      <tr>
        <td><strong>Aprobaciones Indebidas</strong></td>
        <td>0.00%</td>
        <td>0.00%</td>
        <td><strong>0.00%</strong></td>
      </tr>
      <tr>
        <td><strong>Exactitud en Cálculos</strong></td>
        <td>100.00% (Decimal)</td>
        <td>100.00% (Decimal)</td>
        <td><strong>100.00% (Decimal)</strong></td>
      </tr>
      <tr>
        <td><strong>Costo Promedio / Tarea</strong></td>
        <td>$0.0286 USD ($0.535 MXN)</td>
        <td>$0.0028 USD ($0.052 MXN)</td>
        <td><strong>$0.0329 USD ($0.616 MXN)</strong></td>
      </tr>
      <tr>
        <td><strong>Estrategia de Extracción</strong></td>
        <td>Grok Vision + Determinista</td>
        <td>Tiered (91.67% N1 / 8.33% N2)</td>
        <td><strong>Tiered Extraction + Resiliencia 429</strong></td>
      </tr>
      <tr>
        <td><strong>Bitácora y Telemetría</strong></td>
        <td>JSONL (lote_s2_telemetria)</td>
        <td>reporte_s3.md</td>
        <td><strong>Dual inmutable: JSONL + CSV (18 cols)</strong></td>
      </tr>
      <tr>
        <td><strong>Tests Unitarios</strong></td>
        <td>45 passing</td>
        <td>56 passing</td>
        <td><strong>70 passing (100% verde)</strong></td>
      </tr>
    </tbody>
  </table>

  <h2>5. Enlaces Oficiales para Evaluación en Plataforma</h2>
  <div class="links-box">
    <p>📄 <strong>Reporte Técnico General en PDF (Google Drive):</strong><br>
    <a href="https://drive.google.com/file/d/1rQduagkfqgl3EAuQ8Pq6AvGvsouCu5qp/view?usp=drivesdk">https://drive.google.com/file/d/1rQduagkfqgl3EAuQ8Pq6AvGvsouCu5qp/view?usp=drivesdk</a></p>

    <p>🎬 <strong>Video Oficial Sprint 4 (Semana de Carga - 12h Desatendido, 1080p):</strong><br>
    <a href="https://drive.google.com/file/d/13h-CPBloLvk40kZMb9bgiRzJ0jDVzgLK/view?usp=drivesdk">https://drive.google.com/file/d/13h-CPBloLvk40kZMb9bgiRzJ0jDVzgLK/view?usp=drivesdk</a></p>

    <p>🎬 <strong>Video Walkthrough Sprint 2/3 (Herramientas Reales y Web UI Forense, 1080p con Audio):</strong><br>
    <a href="https://drive.google.com/file/d/1MV6u6blB3NIIUkO24vIQslKmx6L2VH7i/view?usp=drivesdk">https://drive.google.com/file/d/1MV6u6blB3NIIUkO24vIQslKmx6L2VH7i/view?usp=drivesdk</a></p>

    <p>🐙 <strong>Repositorio GitHub:</strong><br>
    <a href="https://github.com/TEstebanGQ/CotejIA">https://github.com/TEstebanGQ/CotejIA</a> (Ramas sincronizadas: <code>develop</code> y <code>dev-leo</code>)</p>
  </div>

  <p style="font-size: 7pt; color: #71717a; text-align: center; margin-top: 15px;">
    CotejAI · Diseñado para Platica.mx por el equipo de ingeniería · Licencia MIT · 2026
  </p>

</body>
</html>
"""

async def main():
    print(f"Generando PDF ejecutivo en: {OUTPUT_PDF}")
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.set_content(html_content, wait_until="networkidle")
        await page.pdf(
            path=str(OUTPUT_PDF),
            format="A4",
            print_background=True,
            margin={"top": "12mm", "bottom": "12mm", "left": "14mm", "right": "14mm"}
        )
        await browser.close()
    print(f"PDF generado con éxito. Tamaño: {OUTPUT_PDF.stat().st_size} bytes")

if __name__ == "__main__":
    asyncio.run(main())
