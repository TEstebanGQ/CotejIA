---
title: "Producción de Video Programático con HyperFrames — CotejAI"
type: entity
tags: [hyperframes, video, demo, gsap, render, s2]
created: 2026-10-24
updated: 2026-10-24
status: stable
sources:
  - "video-cotejai/SPEC.md"
  - "video-cotejai/REVIEW.md"
  - "DESIGN.md"
---

# Producción de Video Programático con HyperFrames — CotejAI

> **Propósito:** Composición de video HTML/GSAP determinista cuadro por cuadro (`1920×1080`, `30 fps`, `24.0 s`) que demuestra la interfaz real de CotejAI (`web/index.html`) y sus capacidades autónomas de auditoría fiscal y documental.

---

## 1. Artefactos Principales

| Ruta | Descripción |
| :--- | :--- |
| `video-cotejai/cotejai-demo.mp4` | Video final renderizado (`2.7 MB`, `1920×1080`, `30 fps`, `720 cuadros`, `24.0 s`). |
| `video-cotejai/index.html` | Composición raíz que declara variables editables (`brandName`, `brandTagline`, `fugaTotal`, `accentColor`) y monta las 5 escenas. |
| `video-cotejai/SPEC.md` | Especificación numérica de dirección visual, paleta (`#090D16` / `#0F172A` / `#10B981`), tipografía (`Outfit` + `JetBrains Mono`) y curvas de animación. |
| `video-cotejai/REVIEW.md` | Reporte de auditoría visual y técnica (`0 errores` de lint/layout/runtime y `104/104` en contraste WCAG). |
| `.agents/skills/hyperframes/` | Skill oficial de `heygen-com/hyperframes` instalado en el repositorio. |

---

## 2. Arquitectura de las 5 Escenas (`video-cotejai/compositions/`)

| Escena | Ventana | Archivo | Qué demuestra |
| :--- | :---: | :--- | :--- |
| **1. Hook & Motor Determinista** | `0.0s – 4.5s` | `s1-hook.html` | Cabecera con telemetría (`SAT SOAP: En Línea`, `USD/MXN: $18.69`) y contraste del **Expediente OC-004** (`100 pzas` en OC y CFDI 4.0 vs `80 pzas` en almacén). |
| **2. Visor Multimodal & Grok Vision** | `4.5s – 9.5s` | `s2-vision.html` | Imagen física real (`assets/remision-oc004.png`) analizada por [[grok-vision]] (`99.4%` confianza, `Nitidez: 112.4`), recuadro cian sobre nota manuscrita de merma (`-20 pzas`) y **Three-Way Matching Triad** con retención de `$5,800.00 MXN`. |
| **3. Blindaje SAT & Copiloto Grok 4.6** | `9.5s – 15.0s` | `s3-sat-copilot.html` | Validación en vivo de [[sat-soap-and-69b]] (`Lista 69-B <2ms`, `Timbre CFDI`, [[circuit-breaker-pattern]] `CLOSED`, `180 divisas ISO`), chat del Copiloto Grok 4.6 y acciones de 1 clic con [[idempotency-engine]] y [[policy-gate]] (`$5,000 MXN`). |
| **4. Dashboard KPIs & Registro Central** | `15.0s – 19.8s` | `s4-dashboard-kpis.html` | Las 4 tarjetas Bento (`$418,920.00 MXN` en fuga retenida, `10/10` casos, `94.8%` resolución IA, `$0.038 MXN`/factura) y tabla central (`OC-001`, `OC-002`, `OC-004`, `OC-006 ESCALADO 69-B`). |
| **5. End Card Arquitectónico** | `19.8s – 24.0s` | `s5-endcard.html` | Lockup de marca **CotejAI** (*"El código calcula en centavos. Grok 4.6 decide y protege tu tesorería"*) y los 3 pilares técnicos. |

---

## 3. Comandos de Operación y Edición

```powershell
# Entrar al directorio del proyecto de video
cd video-cotejai

# 1. Abrir la vista previa interactiva en navegador (puerto 3002)
npx hyperframes preview

# 2. Ejecutar validación de contrato, layout, contraste y craft
npx hyperframes check --json

# 3. Generar hojas de contacto de revisión (beats, seams y 360px móvil)
npx hyperframes snapshot --review

# 4. Renderizar nuevamente el archivo MP4 (requiere FFmpeg en PATH)
npx hyperframes render --output cotejai-demo.mp4
```

## Páginas Relacionadas
- [[web-stack]]
- [[s2-demo-script]]
- [[grok-vision]]
- [[three-way-matching]]
