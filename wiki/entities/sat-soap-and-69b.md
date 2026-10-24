---
title: "SAT SOAP WebService & Lista 69-B (EFOS)"
type: entity
tags: [sat, fiscal, soap, 69b, antifraude, efos]
created: 2026-10-24
updated: 2026-10-24
status: stable
sources:
  - "[[raw/spec-s2-herramientas-resiliencia]]"
  - "docs/S2-herramientas-reales.md"
---

# SAT SOAP WebService & Lista 69-B (EFOS)

## Descripción
La validación fiscal en México se compone de dos pilares esenciales para garantizar la deducibilidad tributaria y evitar la materialización de operaciones con empresas fantasma:
1. **Webservice SOAP del SAT:** Consulta de estatus de factura en vivo (`Vigente`, `Cancelado`, `No encontrado`).
2. **Lista Negra del Artículo 69-B del CFF:** Listado oficial de Contribuyentes que realizan operaciones inexistentes o simuladas (EFOS).

## Desafíos Reales de Operación
- **Alta Latencia e Inestabilidad:** El webservice SOAP del SAT (`ConsultaCFDIService`) sufre constantes micro-cortes, timeouts (3-10s) y errores 500.
- **Tamaño del CSV 69-B:** El archivo oficial del SAT contiene miles de RFCs. Debe cachearse localmente (`datasets/cache/69b.csv`) y cargarse en un `Set` en memoria o tabla SQLite indexada para búsquedas en $O(1)$.

## Circuit Breaker para el SOAP SAT
- Si se registran **3 fallos consecutivos** de red o timeout al SAT:
  - Se conmuta el estado a `SAT_NO_VERIFICADO`.
  - Se abre el circuito durante **10 minutos**, durante los cuales las peticiones retornan inmediatamente `SAT_NO_VERIFICADO` sin degradar el lote continuo.
  - El expediente se audita comercialmente y se agenda para revalidación fiscal asíncrona.

## Impacto de Proveedor 69-B
- Si el RFC emisor está en la lista definitiva de 69-B, se activa el código `SUPPLIER_69B`.
- Por política estricta de cumplimiento, el caso se congela de inmediato y se escala a la dirección jurídica y fiscal. El pago queda terminantemente bloqueado.

## Páginas Relacionadas
- [[validar-sat-y-lista-69b]]
- [[circuit-breaker-pattern]]
- [[policy-gate]]
