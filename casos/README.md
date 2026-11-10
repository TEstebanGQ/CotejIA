# Casos propios para el harness

Cada subcarpeta es un expediente. Ponga aquí sus casos y corra:

```bash
python main.py audit --dir casos                 # local
docker compose run --rm app python main.py audit --dir /casos   # en Docker
```

| Archivo | Requerido | Contenido |
|---|---|---|
| `oc.json` | sí | Orden de compra: `proveedor_rfc`, `moneda`, `lineas[]` con `sku`, `cantidad`, `precio_unitario`, `tasa_iva` |
| `cfdi.xml` | sí | Factura CFDI 4.0 timbrada (los conceptos se cruzan por `NoIdentificacion` = `sku`) |
| `remision.json` / `remision.pdf` / `remision.png` | al menos uno | Lo recibido en almacén: JSON estructurado, PDF digital (se extrae sin red) o foto (Grok Vision) |
| `sat_estatus.json` | no | Acuse de estatus SAT, p. ej. `{"uuid": "...", "estado": "Cancelado"}` |
| `esperado.json` | no | Si existe, la salida agrega `comparacion_esperado` |

Ejemplos incluidos: `EJEMPLO-001` limpio (APROBADO), `EJEMPLO-002` sobreprecio (EN_RECLAMO), `EJEMPLO-003` proveedor en lista 69-B (ESCALADO).
