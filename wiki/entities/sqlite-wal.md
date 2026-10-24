---
title: "SQLite WAL & Persistencia Transaccional"
type: entity
tags: [sqlite, wal, persistencia, transacciones, deduplicacion]
created: 2026-10-24
updated: 2026-10-24
status: stable
sources:
  - "[[raw/spec-s2-herramientas-resiliencia]]"
  - "docs/S2-herramientas-reales.md"
---

# SQLite WAL & Persistencia Transaccional

## Descripción
Para soportar la ejecución continua de los 10 casos en S2 y escalar a 1,000 unidades en S4, la capa de persistencia se basa en SQLite con configuración de alta concurrencia mediante WAL (*Write-Ahead Logging*).

## Configuración de Motor
En cada apertura de conexión se ejecutan los pragmas obligatorios:
```sql
PRAGMA journal_mode = WAL;
PRAGMA busy_timeout = 5000;
PRAGMA synchronous = NORMAL;
```
Esto evita el error común `database is locked` cuando múltiples workers o hilos leen y escriben simultáneamente.

## Esquema Canónico de Tablas

### 1. `cases`
Almacena el estado maestro de cada expediente auditado.
- `case_id` (TEXT, PK)
- `estado` (TEXT: `RECIBIDO`, `COTEJADO`, `EN_RECLAMO`, `APROBADO`, `ESCALADO`)
- `version` (INTEGER, control de concurrencia optimista)
- `codigos` (TEXT, JSON array de códigos de discrepancia)
- `monto_a_pagar` (REAL)
- `fuga` (REAL)
- `creado_en` (TIMESTAMP)
- `actualizado_en` (TIMESTAMP)

### 2. `actions`
Garantiza la idempotencia de todas las acciones sobre el mundo exterior.
- `llave_idempotencia` (TEXT, PK): formato `{case_id}:{herramienta}:{version_o_uuid}`
- `case_id` (TEXT, FK)
- `herramienta` (TEXT)
- `payload` (TEXT, JSON)
- `resultado` (TEXT, JSON)
- `fecha_creacion` (TIMESTAMP)

### 3. `llm_calls`
Bitácora auditable de costos y tokens para telemetría.
- `id` (INTEGER PK AUTOINCREMENT)
- `case_id` (TEXT)
- `paso` (INTEGER)
- `herramienta` (TEXT)
- `modelo` (TEXT)
- `prompt_tokens` (INTEGER)
- `cached_tokens` (INTEGER)
- `completion_tokens` (INTEGER)
- `costo_usd` (REAL)
- `latencia_ms` (INTEGER)
- `reintentos` (INTEGER)

### 4. `invoices_seen`
Detección instantánea de facturas duplicadas en los últimos 90 días.
- `uuid` (TEXT, PK)
- `rfc_emisor` (TEXT)
- `folio` (TEXT)
- `total` (REAL)
- `case_id` (TEXT)
- `primer_registro` (TIMESTAMP)

### 5. `sku_aliases`
Caché semántica cruzada de SKUs validados.
- `id` (INTEGER PK AUTOINCREMENT)
- `rfc_proveedor` (TEXT)
- `texto_cfdi` (TEXT)
- `sku_oc` (TEXT)
- `factor_conversion` (REAL)
- `confianza` (REAL)
- `confirmado_por` (TEXT)
- `fecha` (TIMESTAMP)

## Páginas Relacionadas
- [[idempotency-engine]]
- [[verificar-duplicidad-historica]]
- [[reconciliar-sku-ambiguo]]
