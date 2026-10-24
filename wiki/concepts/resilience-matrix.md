---
title: "Matriz Integral de Resiliencia y Manejo de Errores"
type: concept
tags: [resiliencia, fallos, reintentos, degradacion, circuit-breaker]
created: 2026-10-24
updated: 2026-10-24
status: stable
sources:
  - "[[raw/spec-s2-herramientas-resiliencia]]"
  - "docs/S2-herramientas-reales.md"
---

# Matriz Integral de Resiliencia y Manejo de Errores

## Visión General
La resiliencia en CotejAI garantiza que ninguna falla externa o imprecisión en los datos de entrada detenga la auditoría de un lote desatendido ni induzca alucinaciones costosas.

| Escenario de Error | Causa Raíz | Comportamiento del Agente | Impacto en la Auditoría |
| :--- | :--- | :--- | :--- |
| **Timeout o 429 en Grok** | Límite de tasa del gateway o latencia de red. | Reintento automático con *exponential backoff* y *jitter* (hasta 5 intentos). | El proceso se pausa unos segundos y reanuda sin perder estado ni tokens en vano. |
| **Servicio SOAP del SAT caído** | Indisponibilidad de servidores tributarios oficiales. | El *circuit breaker* conmuta a `SAT_NO_VERIFICADO` tras 3 fallos consecutivos durante 10 min. | El lote continúa procesándose sin bloquearse; caso marcado para reintento diferido. |
| **Foto de remisión rota o borrosa** | Imagen degradada, baja resolución o iluminación pobre. | Si confianza $< 0.85$, devuelve `null` y genera `RECEIPT_UNREADABLE`. Pide reintento; al 2do fallo escala. | Se previene inventar cantidades físicas inexistentes. |
| **Reinicio abrupto del worker** | Crash del contenedor, reinicio de máquina o SIGKILL. | Recuperación transaccional desde SQLite en modo WAL y verificación de `actions`. | Retoma desde el último estado sin duplicar acciones externas (idempotencia). |
| **Monto propuesto fuera de límite** | Discrepancia calculada supera los $5,000 MXN. | La compuerta `policy_gate` rechaza la acción autónoma. | Convierte la acción en `escalar_caso` con expediente prearmado. |
| **Proveedor en lista 69-B** | RFC emisor coincide con la lista negra de EFOS del SAT. | Bloqueo fulminante: asigna código `SUPPLIER_69B`. | Congelamiento de pago y escalamiento legal/fiscal inmediato. |
| **Factura previamente procesada** | Proveedor reenvía CFDI ya pagado o auditado en los últimos 90 días. | Búsqueda en `invoices_seen` por UUID o combinación Emisor+Folio+Total emite `DUPLICATE`. | Bloqueo preventivo de doble pago en $0.00$ ms. |

## Páginas Relacionadas
- [[circuit-breaker-pattern]]
- [[idempotency-engine]]
- [[policy-gate]]
- [[grok-vision]]
- [[sat-soap-and-69b]]
