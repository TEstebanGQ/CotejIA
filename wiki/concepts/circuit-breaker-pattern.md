---
title: "Patrón Circuit Breaker en Agentes Autónomos"
type: concept
tags: [resiliencia, circuit-breaker, sat, arquitectura, estabilidad]
created: 2026-10-24
updated: 2026-10-24
status: stable
sources:
  - "[[raw/spec-s2-herramientas-resiliencia]]"
  - "docs/S2-herramientas-reales.md"
---

# Patrón Circuit Breaker en Agentes Autónomos

## Problema
En procesos batch donde un agente procesa lotes de expedientes (10 casos en S2, 1,000 en S4), la dependencia de servicios externos lentos o inestables (como el webservice SOAP del SAT) introduce riesgo de **bloqueo en cascada**. Si el SAT tarda 10 segundos por llamada y empieza a fallar con HTTP 500 o timeouts:
1. El lote completo se ralentiza o colapsa por timeout general.
2. Se desperdician tokens y llamadas al LLM esperando un servicio caído.
3. El agente aborta sin auditar los aspectos comerciales que sí son viables.

## Arquitectura del Circuit Breaker en CotejAI

```
      [ Petición a SAT ]
               │
       ┌───────┴───────┐
       ▼               ▼
[ Circuito CERRADO ]  [ Circuito ABIERTO ]
(Operación normal)     (3 fallos seguidos)
       │                       │
       │ Consulta SOAP         │ Fast-Fail instantáneo
       │                       ▼
       │              Retorna: SAT_NO_VERIFICADO
       │              Ventana de 10 minutos
       ▼                       │
3 fallos seguidos ─────────────┘
```

## Estados del Circuito
1. **CLOSED (Cerrado):** Las llamadas al SOAP del SAT se realizan normalmente con timeout estricto de 3 segundos.
2. **OPEN (Abierto):** Tras **3 fallos consecutivos** (timeout, HTTP 5xx, socket error), el circuito se abre.
   - Durante una ventana de **10 minutos**, ninguna llamada viaja a la red del SAT.
   - La herramienta devuelve inmediatamente el código `SAT_NO_VERIFICADO`.
   - El lote sigue procesando sin retrasos.
3. **HALF-OPEN (Semi-abierto):** Al expirar los 10 minutos, una petición de prueba intenta consultar el SAT. Si responde con éxito, el circuito vuelve a CLOSED; si falla, el timer de 10 minutos se reinicia.

## Páginas Relacionadas
- [[validar-sat-y-lista-69b]]
- [[resilience-matrix]]
- [[sat-soap-and-69b]]
