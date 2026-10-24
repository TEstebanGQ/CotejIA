---
title: "Rúbrica Oficial y Criterios del Torneo (Platica MagIA 2026)"
type: sprint
tags: [torneo, rubrica, evaluacion, criterios, platica]
created: 2026-10-24
updated: 2026-10-24
status: stable
sources:
  - "README_PLATICA.md"
  - "docs/S2-herramientas-reales.md"
  - "[[raw/comunicado-s2-organizadores]]"
---

# Rúbrica Oficial y Criterios del Torneo (Platica MagIA 2026)

## Aclaraciones Oficiales de los Organizadores (24 de octubre de 2026)
- **Fecha límite S2:** Sábado **24 de octubre a las 23:59 (hora CDMX)**.
- **Definición de 3 Herramientas Reales:** No requieren ser tres plataformas externas distintas; tres funciones distintas que el agente decida invocar por sí mismo cuentan siempre que hagan algo real (consultar BD SQLite, llamar a Grok Vision, consultar CSV/API pública del SAT, registrar un reclamo, etc.) y tengan manejo de errores. Lo único que no cuenta son funciones que regresen datos estáticos fijos (`mock`).
- **Datos Reales (15 puntos):** La rúbrica otorga **15 puntos** al uso de datos reales (muestras reales o datos públicos oficiales, como el listado oficial de EFOS 69-B del SAT y fotografías reales de remisiones).
- **Video de 2 minutos:** Debe mostrar al agente resolviendo de principio a fin, invocando herramientas y recuperándose ante un fallo. No requiere explicar código línea por línea.

## Criterios Clave y Ponderación

| Criterio | Puntos | Qué se Evalúa | Impacto de S2 en CotejAI |
| :--- | :--- | :--- | :--- |
| **Autonomía y Funcionalidad** | **25 pts** | El agente opera sin intervención humana, usa herramientas reales y toma decisiones fundamentadas. | Uso de las 3 herramientas reales, compuerta `policy_gate` y cierre de casos. |
| **Ingeniería sobre Grok** | **20 pts** | Uso óptimo de tool calling, visión multimodal, estructuración Pydantic y control de fallos. | Integración multimodal con Grok 4.6, prompt engineering anti-alucinaciones y manejo de rate limits. |
| **Resiliencia y Confiabilidad** | **20 pts** | Capacidad de recuperarse de errores de red, servicios caídos y datos corruptos. | Circuit breaker del SAT, idempotencia en SQLite WAL, reintentos con backoff. |
| **Impacto de Negocio / ROI** | **20 pts** | Retorno financiero claro, retención de fugas de capital y relación costo/beneficio en tokens. | Métrica de fuga detectada vs costo en USD por caso auditado. |
| **Claridad de Demostración** | **15 pts** | Calidad del video de 2 minutos, documentación auditable y facilidad de reproducción. | Script cronometrado de 120s y ejecución de 10 casos en vivo. |

## Estrategia de CotejAI para Maximizar Puntuación
1. **Diferenciador Multimodal:** No conformarse con remisiones en texto sintético; procesar imágenes reales con sellos y notas a mano.
2. **Defensa Fiscal en Vivo:** Validar SAT SOAP y 69-B demuestra comprensión profunda de las operaciones mercantiles mexicanas.
3. **Idempotencia Garantizada:** Demostrar en video que relanzar un proceso fallido no dispara duplicados es la marca de un sistema de grado producción.

## Páginas Relacionadas
- [[s2-roadmap]]
- [[s2-demo-script]]
