# Design System: CotejAI — Autonomous Three-Way Matching Dashboard

Sistema de diseño semántico para Google Stitch y arquitectura de interfaces frontend, configurado bajo las directivas de **Anti-Slop AI Law**, **Emil Kowalski Polish Engineering**, **Atomic Design** y **WCAG AAA**.

---

## 1. Visual Theme & Atmosphere

* **Atmosphere:** Un centro de control financiero y forense de alta densidad (*Cockpit Dense 8/10*), asimetría funcional (*Offset Asymmetric 6/10*) y física de movimiento táctil (*Fluid Precision 6/10*).
* **Sensación:** Preciso, clínico y sobrio, inspirado en terminales de tesorería y herramientas modernas de ingeniería (Linear, Stripe, Platica.mx). El espacio no se siente vacío ni ruidoso; cada píxel comunica solvencia, auditoría inmutable y protección de capital en pesos mexicanos (MXN).

---

## 2. Color Calibration & Palette Roles

Se prohíbe el uso de negro puro (`#000000`) y cualquier gradiente sintético morado/azul de IA genérica. La paleta es estrictamente monótona neutra profunda con un único acento funcional esmeralda (identidad de Platica.mx) y estados semánticos contenidos:

| Token Semántico | Valor Hex / RGBA | Rol Funcional en CotejAI |
| :--- | :--- | :--- |
| **Canvas Deep** | `#090D16` | Fondo principal de la aplicación, profundidad base. |
| **Surface Elevate** | `#0F172A` | Superficie de contenedores principales, sidebar y barras de navegación. |
| **Card Slate** | `#131C2E` | Fondo de tarjetas de métricas, dropzone y visor documental. |
| **Card Nested** | `#1A263D` | Superficie para inputs, filas alternas de tablas y bloques de código. |
| **Border Whisper** | `rgba(255, 255, 255, 0.08)` | Bordes estructurales micrométricos de 1px en tarjetas y separadores. |
| **Border Active** | `rgba(16, 185, 129, 0.40)` | Borde de foco en inputs, dropzone en arrastre y estado activo. |
| **Text Primary** | `#F8FAFC` | Titulares, importes financieros y datos de máxima jerarquía. |
| **Text Muted** | `#94A3B8` | Metadatos, etiquetas de formulario y descripciones secundarias. |
| **Text Ghost** | `#64748B` | Placeholders, marcas de agua y leyendas de pie. |
| **Accent Platica Emerald** | `#10B981` | Único color de acción: botones primarios, aprobación SAT y métricas positivas. |
| **Alert Warning (Amber)** | `#F59E0B` | Estado `EN_RECLAMO`, discrepancias de cantidad/precio, retención de pago. |
| **Alert Critical (Crimson)**| `#EF4444` | Proveedor en lista 69-B del SAT, CFDI cancelado, `TAX_MISMATCH`. |
| **Vision Focus (Cyan)** | `#06B6D4` | Detección de sellos, firmas y lectura multimodal con Grok Vision. |

---

## 3. Typographic Architecture

Queda estrictamente prohibido el uso de la tipografía `Inter` (por ser el cliché por defecto de IA) y fuentes Serif genéricas. La tipografía combina carácter técnico con legibilidad matemática:

* **Display / Titulares:** `Plus Jakarta Sans` o `Geist`
  * Jerarquía: `font-bold` o `font-extrabold`, `tracking-tight` (`-0.02em`).
  * Sin tamaños gigantescos innecesarios: el titular de sección no supera los `24px` a `28px` para preservar la densidad de cabina de control.
* **Cuerpo / Textos:** `Plus Jakarta Sans` o `Satoshi`
  * Interlineado generoso `leading-relaxed`, ancho máximo de párrafo limitado a `65ch` para evitar fatiga cognitiva.
* **Monospace Técnico (Obligatorio en Cifras):** `JetBrains Mono` o `Geist Mono`
  * **Regla estricta:** Todos los montos en dinero (`$6,090.00 MXN`), UUIDs fiscales, RFCs del SAT, conteo de piezas, tokens y latencias se renderizan exclusivamente en fuente monoespaciada para facilitar la comparación vertical en tablas.

---

## 4. Component Stylings (Microfísica Táctil y UX)

### Botones y Controles
* **Física al presionar:** Todo botón cuenta con compresión elástica activa: `active:scale-[0.98]`.
* **Transiciones específicas:** Prohibido usar `transition: all`. Se declaran propiedades explícitas: `transition-transform duration-100 ease-out, transition-colors duration-150`.
* **Primario:** Fondo `#10B981`, texto `#090D16` font-bold, sin halos de luz ni sombras externas de neón.
* **Secundario / Outline:** Fondo transparente, borde `border-white/[0.12]`, texto `#F8FAFC`, hover `bg-white/[0.04]`.

### Tarjetas de Métricas (Top 4 KPIs estilo Shadcn)
* Borde sutil de 1px `border-white/[0.08]`.
* Sombra multicapa difusa hacia el fondo negro (`shadow-sm shadow-black/40`).
* Número central masivo en `JetBrains Mono` con indicador de tendencia (porcentaje o comparativo) en píldora compacta.

### Zona de Carga / Dropzone Multimodal
* Borde discontinuo `border-2 border-dashed border-white/[0.12]`.
* Al arrastrar un archivo sobre la zona: transición inmediata a `border-emerald-500/60 bg-emerald-500/[0.03]`.
* Miniatura instantánea de la imagen de la remisión con opción de zoom modal y recuadro delimitador en cian sobre el sello y la firma detectados por Grok Vision.

### Consola de Chat Copiloto (Grok 4.6)
* Contenedor acotado con scroll interno independiente.
* Burbujas asimétricas: mensajes del agente alineados a la izquierda con avatar técnico esmeralda; mensajes del usuario a la derecha en tono esmeralda oscuro/medio.
* Estados de pensamiento con *shimmer skeleton*, jamás spinners giratorios en el centro de la pantalla.

### Tabla de Auditoría Densa (Three-Way Matching)
* Cabeceras pegajosas (*sticky headers*) con fondo `#0F172A`.
* Filas con hover táctil micrométrico (`hover:bg-white/[0.02]`).
* Badges de estado semántico en pastillas de bajo contraste: fondo al 15% de opacidad y texto al 100% (ej. `bg-amber-500/15 text-amber-300 border border-amber-500/30`).
* Clic en cualquier fila carga el expediente instantáneamente en el visor superior y en el copiloto.

---

## 5. Layout Architecture (Mapeo Shadcn Dashboard)

Estructura de cuadrícula asimétrica optimizada para pantallas de escritorio (1280px a 1920px), colapsable de forma limpia en tablets:

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ HEADER SUPERIOR: Identidad Platica · CotejAI | Barra de Búsqueda | Tickers en Vivo (SAT / Grok / FX)   │
├──────────────┬──────────────────────────────────────────────────────────────────────────────────────────┤
│ SIDEBAR      │ 4 TARJETAS DE KPIS SUPERIORES (Fuga Retenida, Lote S2, Tasa Resolución, Costo/Factura)  │
│ (240px fija) ├──────────────────────────────────────────────────────────────────────────────────────────┤
│ • Dashboard  │ WORKSPACE DUAL (Bento Grid):                                                             │
│ • Casos S2   │ ┌─────────────────────────────────────────────┐ ┌──────────────────────────────────────┐ │
│ • Visor Foto │ │ Visor Multimodal & Dropzone (60% ancho)     │ │ Copiloto Grok 4.6 Reasoning (40%)    │ │
│ • Costos S3  │ │ • Imagen de remisión con notas a mano       │ │ • Chat de aclaraciones y políticas   │ │
│ • Carga S4   │ │ • Desglose de impuestos CFDI 4.0 (IVA 16%)  │ │ • Telemetría de tokens y latencia    │ │
│              │ └─────────────────────────────────────────────┘ └──────────────────────────────────────┘ │
│              ├──────────────────────────────────────────────────────────────────────────────────────────┤
│              │ TABLA DE FACTURAS AUDITADAS (10 Casos del Lote con Badges de Estado y Acciones Rápidas) │
└──────────────┴──────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Motion & Physics Principles

* **Curva de aceleración:** Orgánica y física, inspirada en Apple y Emil Kowalski:  
  `cubic-bezier(0.16, 1, 0.3, 1)`.
* **Duraciones:**
  * Microinteracción de clic: `100ms`.
  * Transición de estados de tarjetas: `200ms`.
  * Despliegue de paneles modulares: `250ms`.
* **Prohibido:** Animaciones lineales (`linear`), rebotes elásticos infantiles (*bouncy springs*) o `transition: all`.

---

## 7. Anti-Patterns (Banned AI Clichés)

Queda estrictamente prohibido:
1. **Emojis en etiquetas o titulares:** Ningún emoji decorativo en la UI (se usan exclusivamente iconos SVG técnicos de Lucide).
2. **Gradientes de texto multicolor:** Prohibidos los textos en degradado morado/rosa.
3. **Botones con sombras de neón:** Prohibido el resplandor difuso exterior (*glow effect*).
4. **Textos genéricos o vacíos:** Prohibido *"Revoluciona tus finanzas con IA de última generación"*. Todo texto debe reflejar datos reales de negocio: *"Retención de $290.00 MXN aplicada por faltante de 20 piezas en SKU TORN-001"*.
5. **Spinners genéricos en pantalla completa:** Todo estado de carga usa *shimmer skeleton* en el componente afectado.
6. **Números inventados:** Todo cálculo de impuestos, retenciones y montos proviene del motor determinista en centavos (`Decimal`).
