---
title: "Platica.mx Platform & Integration"
type: entity
tags: [platica, webhooks, mcp, api, whatsapp]
created: 2026-10-24
updated: 2026-10-24
status: stable
sources:
  - "README_PLATICA.md"
---

# Platica.mx Platform & Integration

## Descripción
Platica.mx es la plataforma de agentes conversacionales sobre canales como WhatsApp, Instagram y correo que aloja el Reto Agente 2026. CotejAI no compite con Platica: opera como un agente especialista de backend / capacidad que Platica invoca mediante API personalizada o servidor MCP.

## Puntos de Integración
1. **Punto A (Inbound Consulta):** El comprador pregunta por WhatsApp a Platica "¿qué facturas tienen problemas?" y Platica consulta los endpoints de CotejAI.
2. **Punto B (Outbound Notificación / Reclamo):** CotejAI llama `POST /v1/messages` de Platica con la plantilla formal para solicitar notas de crédito al proveedor.
3. **Punto C (Inbound Respuesta del Proveedor):** Webhook `message.created` de Platica notifica a CotejAI cuando el proveedor responde, reactivando el caso.

## Políticas de Rate Limit y Reintentos
- 30 peticiones por segundo por API key.
- Reintentos con backoff ante errores 502, 503, 504 y 409.
- No reintentar 4xx salvo 409 o 429 con `Retry-After`.

## Páginas Relacionadas
- [[solicitar-nota-credito]]
- [[idempotency-engine]]
