# SPEC — CotejAI: Autonomous Three-Way Matching Dashboard Film

GOAL:    Show financial controllers and evaluators how CotejAI's web dashboard and autonomous agent (Grok 4.6 + deterministic Python fiscal engine) stop capital leakage in Mexican Accounts Payable by matching Purchase Orders, physical warehouse receipts (Grok Vision), and SAT CFDI 4.0 XML invoices in real time.
OUTPUT:  HyperFrames, 1920 x 1080, 30 fps
TIME:    24.0 seconds x 30 fps = 720 frames
LOOK:    Ground: #090D16 (Canvas Deep) and #0F172A (Surface Elevate) with 1px structural borders rgba(255,255,255,0.08);
         Card surfaces: #131C2E (Card Slate) and #1A263D (Card Nested);
         Ink: #F8FAFC (Text Primary) and #94A3B8 (Text Muted);
         Accents: #10B981 (Platica Emerald for verified/approved & primary actions), #F59E0B (Amber Warning for EN_RECLAMO & retention), #06B6D4 (Cyan Vision Focus for Grok Vision & Copilot), #EF4444 (Crimson Critical for 69-B EFOS);
         Display & UI face: 'Outfit', weight 700-800, 32px-64px, tracking -0.02em;
         Monospace technical face: 'JetBrains Mono', weight 500-700, 28px-56px for all MXN amounts, RFCs, UUIDs, SKU quantities, and telemetry;
         Medium: High-density financial forensic cockpit UI at 1.7x scale with crisp 1px borders and real scanned delivery note imagery (assets/remision-oc004.png).
OBJECTS: 1. Top Telemetry Header with SAT SOAP Circuit Breaker pill, 180-currency ISO 4217 FX ticker (USD/MXN $18.69), and "+ Nuevo Cotejo" / "Auditar Lote" buttons.
         2. Physical Delivery Note Viewer (Grok Vision 99.4%) displaying real scanned image `assets/remision-oc004.png` with cyan bounding box over handwritten warehouse merma note.
         3. Three-Way Matching Triad (1. Orden de Compra ERP -> 2. Remisión Física Almacén -> 3. Factura CFDI 4.0 SAT XML) + Preventive Retention Banner ($5,800.00 MXN).
         4. Grok 4.6 Forensic Copilot Chat + Live SAT Regulatory Checklist (Lista 69-B EFOS, Timbre CFDI, Circuit Breaker, PostgreSQL 16 Idempotency).
         5. Top 4 Bento KPI Cards ($418,920.00 MXN retained leakage, 10/10 cases audited, 94.8% autonomous resolution, $0.038 MXN cost/invoice) & Audit Registry Table.
MOTION:  Arrivals: power4.out and expo.out (0.35s - 0.55s);
         Camera/panel shifts: power3.inOut (0.45s);
         Exits: power3.in (0.22s - 0.30s);
         Number count-ups: 1.3s power2.out, then hold dead still.
SHOTS:
  - Shot 1 (0.0s - 4.5s, frames 0-135, s1-hook): Opens immediately on the CotejAI header and Case OC-004 (Metales & Manufacturas de Toluca, RFC AAA010101AAA). Contrasts the CFDI 4.0 invoice billing 100 units vs 80 received in warehouse, locking onto the exact centavo leakage.
  - Shot 2 (4.5s - 9.5s, frames 135-285, s2-vision): Zooms into the Multimodal Physical Receipt Viewer (`assets/remision-oc004.png`) as Grok Vision (99.4%, Nitidez 112.4) frames the handwritten note ("Recibidos solo 80 pzas. Merma en transporte -20") in cyan and populates the Three-Way Matching Triad and $5,800.00 MXN retention banner.
  - Shot 3 (9.5s - 15.0s, frames 285-450, s3-sat-copilot): Shifts to the right cockpit pane: Live SAT Regulatory Validation (Lista 69-B EFOS clean in <2ms, CFDI Timbre valid, Circuit Breaker CLOSED) and Grok 4.6 Copilot conversation, ending as the cursor clicks "Solicitar Nota de Crédito" and "Aprobar Pago Parcial ($23,200.00 MXN)" with PostgreSQL 16 idempotency.
  - Shot 4 (15.0s - 19.8s, frames 450-594, s4-dashboard-kpis): Reveals the 4 Bento KPI Cards ($418,920.00 MXN Fuga Retenida, 10/10 Casos, 94.8% Resolución Autónoma, $0.038 MXN/Factura) and the multi-case Audit Registry Table (OC-001, OC-002, OC-003, OC-004, OC-006).
  - Shot 5 (19.8s - 24.0s, frames 594-720, s5-endcard): CotejAI Brand Lockup ("El Código Calcula, Grok 4.6 Decide"), showing the Platica.mx emerald emblem, key architecture pillars, and command CTA.
BANNED:  Pure #000000 void with tiny floating text; purple/pink AI gradients; neon glow shadows; generic filler slogans; titles that drift after landing; CSS transforms on GSAP targets; text smaller than 28px without data-layout-ignore.
QA:      Check frames at t=0.2s, 2.5s, 5.5s, 8.0s, 11.0s, 14.0s, 16.5s, 18.5s, 21.5s, 23.0s for legibility, zero overlap, and exact numerical accuracy.
