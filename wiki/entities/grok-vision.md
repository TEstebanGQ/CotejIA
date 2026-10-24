---
title: "Grok Vision & Multimodal Extraction"
type: entity
tags: [grok, multimodal, ocr, vision, ai-gateway]
created: 2026-10-24
updated: 2026-10-24
status: stable
sources:
  - "[[raw/spec-s2-herramientas-resiliencia]]"
  - "docs/S2-herramientas-reales.md"
---

# Grok Vision & Multimodal Extraction

## Descripción
En CotejAI, **Grok Vision** (`grok-4.6` multimodal vía el gateway oficial de Platica `api.reto.pltk.mx/v1`) es el motor responsable de procesar evidencias visuales físicas del mundo real: remisiones en papel, sellos de almacén de tinta, firmas manuscritas y notas marginales ("se recibieron 80 piezas, faltaron 20").

## Capacidades Requeridas en S2
1. **Extracción Estructurada:** Extraer JSON tipado (`RemisionExtraida`) con folio, fecha, líneas de artículos recibidos, presencia booleana de sello y firma.
2. **Scoring de Confianza por Línea:** Cada línea extraída debe incluir un índice `confianza: float (0.0 a 1.0)`.
3. **Lectura de Anotaciones Informales:** Detectar observaciones escritas a mano que alteran el conteo oficial de almacén.

## Degeneraciones y Resiliencia
- **Imágenes Borrosas / Dañadas:** Si la confianza es menor a `0.85`, el agente tiene la instrucción estricta de no alucinar números. Retorna `null` y genera el código `RECEIPT_UNREADABLE`.
- **Fallos de Gateway (429 / 5xx):** Circuit breaker y reintentos con *exponential backoff* y *jitter* (hasta 5 intentos) para evitar saturación de cuota en el gateway.

## Páginas Relacionadas
- [[leer-remision-fisica]]
- [[resilience-matrix]]
- [[policy-gate]]
