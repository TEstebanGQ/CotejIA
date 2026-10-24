---
title: "Motor de Idempotencia y Deduplicación de Acciones"
type: concept
tags: [idempotencia, transacciones, side-effects, sqlite, deduplicacion]
created: 2026-10-24
updated: 2026-10-24
status: stable
sources:
  - "[[raw/spec-s2-herramientas-resiliencia]]"
  - "docs/S2-herramientas-reales.md"
---

# Motor de Idempotencia y Deduplicación de Acciones

## Justificación
Un agente autónomo en producción sufrirá reinicios imprevistos: fallos de energía, timeouts del runner, crashes de memoria o re-ejecuciones manuales. Si el agente emite llamadas externas (ej. enviar correos, disparar webhooks a Platica o emitir solicitudes de notas de crédito), un reinicio podría provocar el **envío duplicado** de reclamos a proveedores, dañando la relación comercial.

## Mecanismo de Llaves de Idempotencia
Antes de invocar cualquier efecto secundario en el exterior, el agente genera una clave determinista:
$$\text{idempotency\_key} = \text{hash}(\text{case\_id} + \text{tool\_name} + \text{action\_payload\_signature})$$
O en formato semántico:
`{case_id}:{herramienta}:{uuid_o_version}` (ej. `OC-002:nota_credito:v1`).

### Flujo Transaccional
1. **Intento de Inserción:** El agente ejecuta un `INSERT` en la tabla `actions` con `llave_idempotencia` como Primary Key:
   ```sql
   INSERT INTO actions (llave_idempotencia, case_id, herramienta, payload, estado, fecha_creacion)
   VALUES (?, ?, ?, ?, 'PENDIENTE', CURRENT_TIMESTAMP);
   ```
2. **Conflicto de Clave Primaria (`SQLITE_CONSTRAINT_PRIMARYKEY`):**
   - Si la clave ya existe, el agente **no reenvía la notificación**.
   - Recupera el resultado guardado previamente y lo retorna a Grok como si la acción se hubiera completado exitosamente en este instante.
3. **Disparo de Red:** Si la inserción fue exitosa, se invoca la API externa (webhook/SMTP).
4. **Confirmación:** Se actualiza la fila con el `resultado` y estado `'COMPLETADO'`.

## Páginas Relacionadas
- [[solicitar-nota-credito]]
- [[sqlite-wal]]
- [[policy-gate]]
