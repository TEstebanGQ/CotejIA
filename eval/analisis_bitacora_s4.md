# Análisis de la bitácora S4 contra ground truth

Generado con `python eval/analizar_bitacora_s4.py` sobre `runs/bitacora_s4.csv` (1000 filas; 998 casos S4; ventana 2026-11-07T05:38 → 2026-11-07T17:52 UTC).

| Resultado | Casos | % |
|---|---:|---:|
| Correcto (estado y códigos = esperado) | 308 | 30.9% |
| Escalado por falla del sistema (sin códigos) | 679 | 68.0% |
| Error de criterio | 11 | 1.1% |

Precisión cuando el cotejo sí corrió: **308/319 (96.6%)**.

Errores de criterio (esperado → obtenido):

- `['CFDI_CANCELADO']->['MATCH_OK']`: 11

Consumo registrado: 7,852,337 tokens de entrada, 178,289 de salida, USD 17.4876. Latencia p50 14.5 s, p95 46.33 s.
## Causa raíz y corrección (10 nov 2026)

La bitácora original marcaba `exito=True` en los 1,000 casos, pero **679 escalamientos no traían ningún código**: el
agente llamó a `cotejar_caso`, el motor lanzó una excepción y el caso se cerró como `ESCALADO` sin dejar el motivo.
Todos los casos en los que el cotejo sí corrió acertaron, salvo una familia.

| Hallazgo | Causa | Corrección |
|---|---|---|
| 679 escalados sin código (68 %) | La excepción no quedó registrada; la causa más probable, reproducida en el análisis: cada conexión a la BD sondeaba un PostgreSQL apagado (~4 s de timeout) y `init_db()` se ejecutaba en cada consulta, recorriendo el catálogo 69-B y compitiendo por el lock de SQLite. Bajo carga el cotejo fallaba y el error se perdía. Los mismos casos corren bien de forma aislada. | Sondeo de Postgres e `init_db()` cacheados por proceso (`src/db.py`); 3 reintentos con backoff en el cotejo; si aun así falla, el veredicto lleva `SYSTEM_ERROR` y el motivo, y el daemon lo registra como `exito=False` con su error (`src/agent.py`, `scripts/run_s4_12h_daemon.py`). |
| 11 CFDI cancelados aprobados | El acuse de estatus SAT (`sat_estatus.json`) nunca se leía. | El cotejo y `consultar_sat_en_vivo` emiten `CFDI_CANCELADO` (pago 0, se escala). |
| S3-035 aprobado sin firma | La remisión sin firma/sello no se trataba como evidencia inválida. | `RECEIPT_UNREADABLE` si falta firma o sello. |

### Validación posterior a la corrección

- Motor determinista sobre los 1,000 casos S4: **1000/1000** estado y códigos iguales a `esperado.json`, en 57 s
  (antes ~16 s por caso solo en el cotejo): `python main.py audit --dir datasets/s4 --modo determinista`.
- Dataset S3 (36 casos): **36/36**.
- Grok 4.6 de punta a punta en casos que antes fallaron (S4-0003, S4-0005, S4-0006, S4-0007, S4-0015, S3-035): todos
  correctos, incluido el CFDI cancelado.
- La corrida de 12 h **no se repitió**; la bitácora histórica se conserva sin editar como evidencia del fallo.
