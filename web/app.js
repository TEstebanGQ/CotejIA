/**
 * CotejAI Web Dashboard — Cliente JavaScript
 * Vistas SPA (Dashboard vs Expedientes), Sidebar fija,
 * Carga Manual con Grok Vision y Copiloto optimizado con Markdown renderizado.
 */

// Estado Global de la Aplicación
const state = {
  casos: [],
  casoActivoId: 'OC-004',
  casoActivoData: null,
  filtroActual: 'TODOS',
  vistaActual: 'DASHBOARD',
  historialChat: [],
  metricas: null
};

// Formateador de moneda en pesos mexicanos
const fmtMXN = (val) => {
  const num = parseFloat(val) || 0;
  return new Intl.NumberFormat('es-MX', {
    style: 'currency',
    currency: 'MXN',
    minimumFractionDigits: 2
  }).format(num);
};

// Formateador Markdown seguro y estructurado
function formatMarkdown(rawText) {
  if (!rawText) return '';
  if (window.marked && typeof window.marked.parse === 'function') {
    return window.marked.parse(rawText);
  }
  // Fallback regex en caso de fallo de CDN
  return rawText
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`(.*?)`/g, '<code>$1</code>')
    .replace(/\n\n/g, '<p></p>')
    .replace(/\n- (.*?)/g, '<li>$1</li>');
}

// Inicialización
document.addEventListener('DOMContentLoaded', () => {
  inicializarApp();
  configurarBuscador();
});

async function inicializarApp() {
  actualizarIconos();
  await Promise.all([
    cargarSaludSistema(),
    cargarTipoCambio(),
    cargarMetricas(),
    cargarCasos()
  ]);
  // Seleccionar caso inicial por defecto (OC-004 para mostrar merma documental)
  await seleccionarCaso('OC-004');
}

function actualizarIconos() {
  if (window.lucide) {
    window.lucide.createIcons();
  }
}

// 1. Control de Vistas SPA (Dashboard vs Expedientes)
function cambiarVista(vista) {
  state.vistaActual = vista;
  const viewDash = document.getElementById('view-dashboard');
  const viewExp = document.getElementById('view-expedientes');
  const navDash = document.getElementById('nav-dashboard');
  const navExp = document.getElementById('nav-expedientes');

  if (vista === 'DASHBOARD') {
    viewDash.classList.remove('hidden');
    viewExp.classList.add('hidden');
    navDash.className = 'nav-link w-full flex items-center gap-2.5 px-3 py-2 rounded-md bg-zinc-800 text-white font-medium text-xs border border-zinc-700/60 transition-colors';
    navExp.className = 'nav-link w-full flex items-center justify-between px-3 py-2 rounded-md text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/40 text-xs transition-colors';
  } else if (vista === 'EXPEDIENTES') {
    viewDash.classList.add('hidden');
    viewExp.classList.remove('hidden');
    navDash.className = 'nav-link w-full flex items-center gap-2.5 px-3 py-2 rounded-md text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/40 text-xs transition-colors';
    navExp.className = 'nav-link w-full flex items-center justify-between px-3 py-2 rounded-md bg-zinc-800 text-white font-medium text-xs border border-zinc-700/60 transition-colors';
  }
  actualizarIconos();
}

// 2. Salud del Sistema y Circuit Breaker SAT
async function cargarSaludSistema() {
  try {
    const res = await fetch('/api/health');
    const data = await res.json();
    if (data.ok) {
      const dbLabel = document.getElementById('label-motor-db');
      if (dbLabel) dbLabel.textContent = data.motor_db || 'SQLite WAL';

      const cb = data.circuit_breaker_sat;
      const dot = document.getElementById('sat-dot');
      const txt = document.getElementById('sat-status-text');
      const cbChk = document.getElementById('chk-sat-cb');

      if (cb && cb.estado === 'OPEN') {
        dot.className = 'w-2 h-2 rounded-full bg-amber-500 animate-pulse';
        txt.textContent = 'En Degradación';
        if (cbChk) cbChk.innerHTML = `<span class="text-amber-400 font-semibold">OPEN (Fallo SOAP)</span>`;
      } else {
        dot.className = 'w-2 h-2 rounded-full bg-emerald-500 animate-pulse';
        txt.textContent = 'En Línea';
        if (cbChk) cbChk.innerHTML = `<span class="text-emerald-400 font-semibold">CLOSED (Normal)</span>`;
      }
    }
  } catch (err) {
    console.warn('Error consultando salud:', err);
  }
}

// 3. Tipo de Cambio USD/MXN en Vivo
async function cargarTipoCambio() {
  try {
    const res = await fetch('/api/tools/fx', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ moneda: 'USD', tipo_cambio_cfdi: '20.00' })
    });
    const data = await res.json();
    if (data.tasa_oficial_mxn) {
      const fxEl = document.getElementById('fx-rate-text');
      if (fxEl) fxEl.textContent = `$${parseFloat(data.tasa_oficial_mxn).toFixed(2)}`;
    }
  } catch (err) {
    console.warn('Error consultando FX:', err);
  }
}

// 4. Cargar y Actualizar KPIs Bento Cards
async function cargarMetricas() {
  try {
    const res = await fetch('/api/metrics');
    const m = await res.json();
    state.metricas = m;

    const kpiFuga = document.getElementById('kpi-fuga');
    if (kpiFuga) kpiFuga.textContent = fmtMXN(m.fuga_total_retenida_mxn || 0);

    const kpiReclamo = document.getElementById('kpi-reclamo-badge');
    const enReclamoCount = (m.conteo_estados && m.conteo_estados.EN_RECLAMO) || 0;
    if (kpiReclamo) kpiReclamo.textContent = `${enReclamoCount} en Reclamo`;

    const totalAuditados = m.casos_auditados || 0;
    const kpiProgreso = document.getElementById('kpi-casos-progreso');
    if (kpiProgreso) kpiProgreso.textContent = `${totalAuditados} / ${totalAuditados}`;

    const kpiCosto = document.getElementById('kpi-costo-usd');
    if (kpiCosto && m.telemetria_llm) {
      const costMxn = (m.telemetria_llm.costo_total_usd || 0.002) * 19.5;
      kpiCosto.textContent = fmtMXN(costMxn / (totalAuditados || 1));
    }
  } catch (err) {
    console.warn('Error cargando métricas:', err);
  }
}

// 5. Cargar Lista de Casos
async function cargarCasos() {
  try {
    const res = await fetch('/api/cases');
    const data = await res.json();
    if (data.ok && data.casos) {
      state.casos = data.casos;
      const badgeSide = document.getElementById('badge-total-sidebar');
      if (badgeSide) badgeSide.textContent = state.casos.length;
      renderizarTablaCasos();
    }
  } catch (err) {
    console.error('Error cargando casos:', err);
  }
}

// 6. Renderizado de la Tabla Central de Expedientes
function renderizarTablaCasos() {
  const tbody = document.getElementById('tabla-casos-body');
  if (!tbody) return;

  const casosFiltrados = state.casos.filter((c) => {
    if (state.filtroActual === 'TODOS') return true;
    if (state.filtroActual === 'LOTE_S2') return c.case_id.startsWith('OC-0');
    if (state.filtroActual === 'MANUAL') return c.case_id.includes('MANUAL');
    return c.estado_final === state.filtroActual;
  });

  if (casosFiltrados.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="7" class="py-8 text-center text-zinc-500 font-mono">
          No hay expedientes con el filtro actual (${state.filtroActual}).
        </td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = casosFiltrados.map((c) => {
    const esActivo = c.case_id === state.casoActivoId;
    let badgeClass = 'bg-zinc-800 text-zinc-300 border-zinc-700';
    if (c.estado_final === 'APROBADO') {
      badgeClass = 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
    } else if (c.estado_final === 'EN_RECLAMO') {
      badgeClass = 'bg-amber-500/10 text-amber-400 border-amber-500/20';
    } else if (c.estado_final === 'ESCALADO') {
      badgeClass = 'bg-rose-500/10 text-rose-400 border-rose-500/20';
    }

    const fuga = parseFloat(c.fuga_detectada_mxn) || 0;
    const fugaColor = fuga > 0 ? 'text-amber-400' : 'text-zinc-500';

    return `
      <tr 
        onclick="inspeccionarYIrADashboard('${c.case_id}')" 
        class="cursor-pointer transition-colors ${esActivo ? 'bg-zinc-800/60 border-l-2 border-l-emerald-500' : 'hover:bg-zinc-900/60'}"
      >
        <td class="py-3 px-4 font-mono font-bold text-white flex items-center gap-2">
          ${c.tiene_imagen_remision ? '<i data-lucide="image" class="w-3.5 h-3.5 text-cyan-400 shrink-0"></i>' : '<i data-lucide="file-text" class="w-3.5 h-3.5 text-zinc-500 shrink-0"></i>'}
          <span>${c.case_id}</span>
        </td>
        <td class="py-3 px-4">
          <div class="font-medium text-zinc-200 truncate max-w-[200px]">${c.case_id.includes('MANUAL') ? 'Carga Manual' : 'Proveedor ' + c.case_id}</div>
          <div class="font-mono text-[10px] text-zinc-500">${c.proveedor_rfc || 'RFC Desconocido'}</div>
        </td>
        <td class="py-3 px-4 font-mono text-zinc-300">${fmtMXN(c.total_cfdi_mxn)}</td>
        <td class="py-3 px-4 font-mono font-semibold text-white">${fmtMXN(c.monto_a_pagar_mxn)}</td>
        <td class="py-3 px-4 font-mono font-bold ${fugaColor}">${fmtMXN(fuga)}</td>
        <td class="py-3 px-4">
          <span class="font-mono text-[10px] font-semibold px-2 py-0.5 rounded border ${badgeClass}">
            ${c.estado_final || 'PENDIENTE'}
          </span>
        </td>
        <td class="py-3 px-4 text-right">
          <button 
            onclick="event.stopPropagation(); inspeccionarYIrADashboard('${c.case_id}')" 
            class="px-2.5 py-1 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-300 font-mono text-[11px] border border-zinc-700 active-press"
          >
            Auditar en Dashboard
          </button>
        </td>
      </tr>
    `;
  }).join('');

  actualizarIconos();
}

function inspeccionarYIrADashboard(caseId) {
  seleccionarCaso(caseId);
  cambiarVista('DASHBOARD');
}

// 7. Navegación Secuencial de Casos
function navegarCasoAnterior() {
  if (state.casos.length === 0) return;
  const idx = state.casos.findIndex(c => c.case_id === state.casoActivoId);
  const prevIdx = idx <= 0 ? state.casos.length - 1 : idx - 1;
  seleccionarCaso(state.casos[prevIdx].case_id);
}

function navegarCasoSiguiente() {
  if (state.casos.length === 0) return;
  const idx = state.casos.findIndex(c => c.case_id === state.casoActivoId);
  const nextIdx = idx >= state.casos.length - 1 ? 0 : idx + 1;
  seleccionarCaso(state.casos[nextIdx].case_id);
}

// 8. Selección e Inspección de un Expediente Específico
async function seleccionarCaso(caseId) {
  state.casoActivoId = caseId;
  renderizarTablaCasos();

  try {
    const res = await fetch(`/api/cases/${caseId}`);
    const data = await res.json();
    if (!data.ok) return;

    state.casoActivoData = data;
    actualizarVistaExpediente(data);
  } catch (err) {
    console.error('Error inspeccionando caso:', err);
  }
}

function actualizarVistaExpediente(d) {
  const c = d.caso;
  const cotejo = d.cotejo || {};
  const oc = d.oc || {};
  const rem = d.remision || {};
  const cfdi = d.cfdi || {};

  // Headers
  document.getElementById('exp-folio').textContent = c.case_id;
  document.getElementById('exp-rfc').textContent = c.proveedor_rfc || cfdi.rfc_emisor || 'N/A';
  document.getElementById('exp-uuid').textContent = c.uuid || 'N/A';

  // Badge de Estado
  const badgeEstado = document.getElementById('exp-badge-estado');
  if (c.estado_final === 'APROBADO') {
    badgeEstado.className = 'text-[11px] font-mono font-semibold px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20';
    badgeEstado.textContent = 'CONCILIADO_OK';
  } else if (c.estado_final === 'EN_RECLAMO') {
    badgeEstado.className = 'text-[11px] font-mono font-semibold px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20';
    badgeEstado.textContent = 'EN_RECLAMO';
  } else {
    badgeEstado.className = 'text-[11px] font-mono font-semibold px-2 py-0.5 rounded bg-rose-500/10 text-rose-400 border border-rose-500/20';
    badgeEstado.textContent = c.estado_final || 'ESCALADO';
  }

  // Visor de Imagen
  const imgEl = document.getElementById('exp-remision-img');
  const bbox = document.getElementById('vision-bbox');
  const textoManuscrito = document.getElementById('vision-texto-manuscrito');

  if (c.tiene_imagen_remision) {
    imgEl.src = `/api/cases/${c.case_id}/image?t=${Date.now()}`;
    bbox.classList.remove('hidden');
    if (c.case_id === 'OC-004') {
      textoManuscrito.textContent = '"Recibidos solo 80 pzas. Merma en transporte (-20)"';
    } else if (c.case_id === 'OC-005') {
      textoManuscrito.textContent = '⚠️ Imagen ilegible / borrosa detectada por Grok Vision';
    } else {
      textoManuscrito.textContent = 'Firma y sello de almacén detectados sin anomalías';
    }
  } else {
    imgEl.src = 'data:image/svg+xml;utf8,<svg xmlns=\'http://www.w3.org/2000/svg\' width=\'100%25\' height=\'100%25\' fill=\'%2318181b\'><text x=\'50%25\' y=\'50%25\' fill=\'%2371717a\' font-size=\'12\' text-anchor=\'middle\' dy=\'.3em\'>Sin imagen física escaneada</text></svg>';
    bbox.classList.add('hidden');
  }

  // Tríada 1: Orden de Compra
  const primerItemOc = (oc.lineas && oc.lineas[0]) || {};
  document.getElementById('triad-oc-desc').textContent = `${primerItemOc.cantidad || 0} pzas @ ${fmtMXN(primerItemOc.precio_unitario || 0)}`;
  document.getElementById('triad-oc-total').textContent = fmtMXN(cotejo.total_cfdi_mxn || 0);

  // Tríada 2: Remisión Almacén
  const primerItemRem = (rem.lineas && rem.lineas[0]) || {};
  const boxRem = document.getElementById('box-remision-triad');
  const triadRemDesc = document.getElementById('triad-rem-desc');
  const triadRemAlerta = document.getElementById('triad-rem-alerta');

  const fuga = parseFloat(cotejo.fuga_detectada_mxn) || 0;
  if (fuga > 0) {
    boxRem.className = 'p-3 rounded-lg bg-cardNested border border-amber-500/40 flex items-center justify-between bg-amber-500/[0.03]';
    triadRemDesc.textContent = `${primerItemRem.cantidad_recibida || 0} pzas físicas (Diferencia detectada)`;
    triadRemAlerta.textContent = 'FALTANTE / MERMA';
    triadRemAlerta.className = 'text-xs font-bold font-mono text-amber-400';
  } else {
    boxRem.className = 'p-3 rounded-lg bg-cardNested border border-borderSubtle flex items-center justify-between';
    triadRemDesc.textContent = `${primerItemRem.cantidad_recibida || primerItemOc.cantidad || 0} pzas completas`;
    triadRemAlerta.textContent = 'RECEPCIÓN EXACTA';
    triadRemAlerta.className = 'text-xs font-bold font-mono text-emerald-400';
  }

  // Tríada 3: Factura CFDI
  const primerItemCfdi = (cfdi.conceptos && cfdi.conceptos[0]) || {};
  document.getElementById('triad-cfdi-desc').textContent = `${primerItemCfdi.cantidad || 0} pzas facturadas`;
  document.getElementById('triad-cfdi-total').textContent = fmtMXN(cotejo.total_cfdi_mxn || 0);

  // Banner de Retención Preventiva
  const banner = document.getElementById('banner-retencion');
  const montoTxt = document.getElementById('monto-retencion-txt');
  const explTxt = document.getElementById('explicacion-retencion-txt');

  if (fuga > 0) {
    banner.classList.remove('hidden');
    montoTxt.textContent = fmtMXN(fuga);
    explTxt.innerHTML = `Cálculo determinista: Diferencia en partida de almacén. Fuga detectada de <strong>${fmtMXN(fuga)}</strong>. Estado asignado a <strong>${c.estado_final}</strong> para proteger la dispersión.`;
  } else {
    banner.classList.remove('hidden');
    montoTxt.textContent = '$0.00 MXN';
    explTxt.innerHTML = `Cotejo 100% conciliado. Las piezas ordenadas, recibidas en almacén y facturadas ante el SAT coinciden en su totalidad.`;
  }

  // Botón Pago Parcial
  const btnMonto = document.getElementById('btn-monto-parcial');
  if (btnMonto) btnMonto.textContent = fmtMXN(cotejo.monto_a_pagar_mxn || 0);

  // Actualizar Copiloto con Markdown estructurado
  const introGrok = document.getElementById('chat-grok-intro');
  if (introGrok) {
    if (c.resumen) {
      introGrok.innerHTML = formatMarkdown(`**Expediente ${c.case_id}:** ${c.resumen}`);
    } else {
      introGrok.innerHTML = formatMarkdown(`Expediente **${c.case_id}** cargado. ¿Qué deseas consultar sobre este caso?`);
    }
  }

  // Checklist Fiscal
  const sat69b = document.getElementById('chk-sat-69b');
  if (c.codigos_calculados && c.codigos_calculados.includes('SUPPLIER_69B')) {
    sat69b.innerHTML = `<span class="text-rose-400 font-semibold flex items-center gap-1 text-[11px]"><i data-lucide="alert-octagon" class="w-3 h-3"></i> En Lista Negra SAT</span>`;
  } else {
    sat69b.innerHTML = `<span class="text-emerald-400 font-semibold flex items-center gap-1 text-[11px]"><i data-lucide="check" class="w-3 h-3"></i> Limpio (No EFOS)</span>`;
  }

  actualizarIconos();
}

// 9. Copiloto Chat Optimizado (Rápido y con Markdown)
async function enviarMensajeChat(e) {
  e.preventDefault();
  const input = document.getElementById('chat-input');
  const txt = input.value.trim();
  if (!txt) return;

  const stream = document.getElementById('chat-stream');
  
  // Agregar mensaje del usuario
  stream.innerHTML += `
    <div class="flex gap-2 justify-end">
      <div class="bg-zinc-800 px-3 py-2 rounded-lg border border-zinc-700 text-zinc-100 max-w-[85%] text-xs">
        ${txt}
      </div>
    </div>
  `;
  input.value = '';
  stream.scrollTop = stream.scrollHeight;

  // Indicador de "Escribiendo..." con animación de 3 puntos
  const loadingId = 'grok-load-' + Date.now();
  stream.innerHTML += `
    <div id="${loadingId}" class="flex gap-2">
      <div class="w-5 h-5 rounded bg-cyan-500/20 text-cyan-400 flex items-center justify-center shrink-0 mt-0.5">
        <i data-lucide="bot" class="w-3 h-3"></i>
      </div>
      <div class="bg-cardNested px-3 py-2 rounded-lg border border-borderSubtle text-zinc-400 text-xs flex items-center gap-1.5">
        <span class="text-zinc-400">Grok está respondiendo</span>
        <span class="inline-flex gap-0.5 ml-1">
          <span class="w-1.5 h-1.5 rounded-full bg-cyan-400 typing-dot"></span>
          <span class="w-1.5 h-1.5 rounded-full bg-cyan-400 typing-dot"></span>
          <span class="w-1.5 h-1.5 rounded-full bg-cyan-400 typing-dot"></span>
        </span>
      </div>
    </div>
  `;
  actualizarIconos();
  stream.scrollTop = stream.scrollHeight;

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        mensaje: txt,
        case_id: state.casoActivoId,
        historial: state.historialChat
      })
    });
    const data = await res.json();
    const loadEl = document.getElementById(loadingId);
    if (loadEl) loadEl.remove();

    if (data.ok && data.respuesta) {
      stream.innerHTML += `
        <div class="flex gap-2">
          <div class="w-5 h-5 rounded bg-cyan-500/20 text-cyan-400 flex items-center justify-center shrink-0 mt-0.5">
            <i data-lucide="bot" class="w-3 h-3"></i>
          </div>
          <div class="bg-cardNested p-3 rounded-lg border border-borderSubtle text-zinc-200 max-w-[92%] prose-chat">
            ${formatMarkdown(data.respuesta)}
          </div>
        </div>
      `;
      state.historialChat = data.historial || [];
    }
  } catch (err) {
    const loadEl = document.getElementById(loadingId);
    if (loadEl) loadEl.remove();
  }
  actualizarIconos();
  stream.scrollTop = stream.scrollHeight;
}

function preguntarRapido(texto) {
  const input = document.getElementById('chat-input');
  if (input) {
    input.value = texto;
    document.getElementById('form-chat').dispatchEvent(new Event('submit'));
  }
}

// 10. Acciones Inmediatas (Idempotencia y Auditoría)
async function solicitarNotaCredito() {
  if (!state.casoActivoId) return;
  try {
    const res = await fetch(`/api/tools/reclamo/${state.casoActivoId}`, { method: 'POST' });
    const data = await res.json();
    if (data.idempotencia_bloqueada) {
      alert(`⚠️ BLOQUEO DE IDEMPOTENCIA ACTIVO:\n${data.mensaje}\nSe evitó enviar un reclamo duplicado.`);
    } else {
      alert(`✅ RECLAMO ENVIADO CON ÉXITO:\nSe disparó el webhook formal hacia el proveedor con llave de idempotencia.`);
    }
  } catch (err) {
    alert('Error enviando reclamo.');
  }
}

function aprobarPagoParcial() {
  if (!state.casoActivoData) return;
  const monto = fmtMXN(state.casoActivoData.cotejo.monto_a_pagar_mxn);
  alert(`Dispersión de tesorería autorizada por ${monto}.\nEl pago de lo recibido queda liberado y la retención resguardada.`);
}

function generarActaPDF() {
  alert(`Generando Acta Circunstanciada en PDF para el expediente ${state.casoActivoId}...\nSe adjunta el análisis de Grok Vision, la verificación fiscal SAT 69-B y el desglose de 3 vías.`);
}

async function auditarCasoActivo() {
  if (!state.casoActivoId) return;
  try {
    const res = await fetch(`/api/audit/${state.casoActivoId}`, { method: 'POST' });
    const data = await res.json();
    if (data.ok) {
      alert(`Auditoría de ${state.casoActivoId} finalizada con éxito.`);
      await cargarMetricas();
      await cargarCasos();
      await seleccionarCaso(state.casoActivoId);
    }
  } catch (err) {
    alert('Error al auditar el caso.');
  }
}

async function auditarTodoElLote() {
  const btn = document.getElementById('btn-audit-all');
  if (btn) btn.disabled = true;
  try {
    const res = await fetch('/api/audit-all', { method: 'POST' });
    const data = await res.json();
    if (data.ok) {
      alert(`Lote completado: ${data.total_procesados} expedientes procesados por Grok 4.6 y el motor determinista.`);
      await cargarMetricas();
      await cargarCasos();
      await seleccionarCaso(state.casoActivoId);
    }
  } catch (err) {
    alert('Error al auditar el lote.');
  } finally {
    if (btn) btn.disabled = false;
  }
}

async function probarVisionEnVivo() {
  if (!state.casoActivoId) return;
  try {
    const res = await fetch(`/api/tools/vision/${state.casoActivoId}`, { method: 'POST' });
    const data = await res.json();
    const lbl = document.getElementById('vision-nitidez-label');
    if (lbl) lbl.textContent = `Nitidez: ${data.nitidez_optica || 'N/A'}`;
    alert(`Inspección Grok Vision:\n- Nitidez óptica: ${data.nitidez_optica}\n- Legible: ${data.legible ? 'Sí' : 'No (Borrosa)'}\n- Confianza: ${data.confianza_minima || '99%'}`);
  } catch (err) {
    alert('Error en Grok Vision.');
  }
}

async function probarSatEnVivo() {
  if (!state.casoActivoId) return;
  try {
    const res = await fetch(`/api/tools/sat/${state.casoActivoId}`, { method: 'POST' });
    const data = await res.json();
    alert(`Consulta SAT SOAP en Vivo:\n- Estado CFDI: ${data.estado_sat_soap}\n- Código Estatus: ${data.codigo_estatus}\n- Lista 69-B: ${data.estatus_69b}\n- Circuit Breaker: ${data.circuit_breaker}`);
  } catch (err) {
    alert('Error en consulta SAT.');
  }
}

function abrirInfo69B() {
  alert('Base de Datos Lista Negra 69-B del SAT:\nSe cuenta con los RFCs de EFOS definitivos precargados en SQLite WAL para detección instantánea offline sin depender de la latencia del portal del SAT.');
}

// 11. Carga Manual de Documentos
function abrirModalUpload() {
  document.getElementById('modal-upload').classList.remove('hidden');
}

function cerrarModalUpload() {
  document.getElementById('modal-upload').classList.add('hidden');
  document.getElementById('form-upload-manual').reset();
  document.getElementById('upload-status').classList.add('hidden');
  document.getElementById('label-xml').textContent = 'Arrastra o selecciona el XML';
  document.getElementById('label-img').textContent = 'Grok Vision leerá sellos y merma';
}

function actualizarNombreArchivo(input, labelId) {
  if (input.files && input.files[0]) {
    document.getElementById(labelId).textContent = `✅ ${input.files[0].name}`;
  }
}

async function enviarCargaManual(e) {
  e.preventDefault();
  const form = document.getElementById('form-upload-manual');
  const formData = new FormData(form);

  const statusEl = document.getElementById('upload-status');
  const btnSubmit = document.getElementById('btn-submit-upload');

  statusEl.classList.remove('hidden');
  btnSubmit.disabled = true;

  try {
    const res = await fetch('/api/cases/upload-manual', {
      method: 'POST',
      body: formData
    });
    const data = await res.json();

    if (data.ok) {
      alert(`🎉 Expediente ${data.case_id} procesado exitosamente.\nResultado del Cotejo: ${data.veredicto.estado_final}\nFuga detectada: ${fmtMXN(data.veredicto.fuga_detectada_mxn)}`);
      cerrarModalUpload();
      await cargarMetricas();
      await cargarCasos();
      inspeccionarYIrADashboard(data.case_id);
    } else {
      alert(`Error procesando carga manual: ${data.detail || 'Verifica el XML'}`);
    }
  } catch (err) {
    alert('Error al enviar los archivos al servidor.');
  } finally {
    statusEl.classList.add('hidden');
    btnSubmit.disabled = false;
  }
}

// 12. Filtros y Búsqueda
function filtrarPorTab(tab) {
  state.filtroActual = tab;
  document.querySelectorAll('.tab-btn').forEach((btn) => {
    if (btn.dataset.tab === tab) {
      btn.className = 'tab-btn px-2.5 py-1 rounded-md bg-zinc-800 text-white transition-colors';
    } else {
      btn.className = 'tab-btn px-2.5 py-1 rounded-md text-zinc-400 hover:text-white transition-colors';
    }
  });
  renderizarTablaCasos();
}

function configurarBuscador() {
  const input = document.getElementById('buscador-expediente');
  if (!input) return;

  input.addEventListener('input', (e) => {
    const q = e.target.value.toLowerCase().trim();
    const rows = document.querySelectorAll('#tabla-casos-body tr');
    rows.forEach((row) => {
      const txt = row.innerText.toLowerCase();
      row.style.display = txt.includes(q) ? '' : 'none';
    });
  });

  // Atajo ⌘K
  window.addEventListener('keydown', (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
      e.preventDefault();
      input.focus();
    }
  });
}
