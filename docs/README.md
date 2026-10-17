# Documentación de CotejAI

CotejAI se construye como un **framework**: un núcleo con contratos fijos (caso, expediente, herramienta, compuerta, estado, notificador, telemetría) sobre el que cada semana del reto agrega piezas sin reescribir lo anterior.

## Índice

| Documento | Qué contiene |
| --- | --- |
| [00-framework.md](00-framework.md) | Arquitectura, contratos, estructura de carpetas, convenciones y la decisión de usar SDK propio |
| [S2-herramientas-reales.md](S2-herramientas-reales.md) | Semana 2: visión, SAT y 69-B, notificador, compuerta, persistencia, errores, 10 ejecuciones y video |
| [S3-datos-y-costos.md](S3-datos-y-costos.md) | Semana 3: set de 36 casos etiquetados, remisiones físicas, evaluación, optimización y reporte de costo |
| [S4-semana-de-carga.md](S4-semana-de-carga.md) | Semana 4: despliegue, workers, 1,000 casos en 12 horas, inyección de fallos y bitácora |
| [mercado.md](mercado.md) | Quién necesita CotejAI, datos del problema, competencia, países, pitch y validación con clientes |
| [../README_PLATICA.md](../README_PLATICA.md) | Track 2: integración con Platica, estado de S1 y stack |
| [../CotejAI_guia_implementacion.md](../CotejAI_guia_implementacion.md) | Guía original de diseño |

## Calendario

| Semana | Fechas | Hito del reto | Pregunta que responde |
| --- | --- | --- | --- |
| S1 ✅ | 12–17 oct 2026 | Agente corriendo | ¿El flujo corre de punta a punta con Grok? |
| S2 | 19–24 oct 2026 | Herramientas reales | ¿El agente actúa con herramientas reales y sobrevive a errores? |
| S3 | 26–31 oct 2026 | Datos reales | ¿Qué tan bien acierta y cuánto cuesta por factura? |
| S4 | 2–7 nov 2026 | Semana de carga | ¿Aguanta 1,000 casos en 12 horas sin nadie mirando? |

> Las fechas de S2 a S4 son las semanas que siguen a S1; confírmalas con los organizadores.

## Cómo usar estos documentos

Cada plan semanal tiene la misma estructura: **objetivo → criterios del reto → entregables → tareas (con archivo y contrato) → criterios de aceptación → riesgos**. Una tarea está terminada cuando cumple su criterio de aceptación y tiene test, no cuando "ya corre".
