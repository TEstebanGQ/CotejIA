# S3 · Datos reales y costo por tarea

## Objetivo

Medir con números qué tan bien acierta CotejAI y cuánto cuesta auditar una factura, sobre un set propio de **36 casos etiquetados** (el reto pide 30 o más), con remisiones físicas fotografiadas.

## Lo que pide el reto

| Requisito | Cómo lo cumplimos |
| --- | --- |
| Set de evaluación propio de 30+ casos | 36 casos con la respuesta correcta de cada uno |
| Reporte de costo por tarea | Costo medio por factura auditada, contra pesos de fuga detectada |

Rúbrica que mueve esta semana: **Evidencia con datos reales (15)** e **Impacto del problema (25)**, porque el reporte da el argumento en pesos.

## Entregables

- [ ] Generador `datasets/generate.py` con catálogo de proveedores y 40 SKUs
- [ ] 36 casos con `datasets/<caso>/esperado.json`
- [ ] Remisiones físicas: impresas, selladas, firmadas, tachadas y fotografiadas
- [ ] `eval/evaluar.py`: compara veredictos contra etiquetas y calcula métricas
- [ ] Expediente precargado y extracción por niveles, con medición de costo antes y después
- [ ] Reporte de fugas en HTML generado desde la corrida
- [ ] `eval/reporte_s3.md` con tablas y conclusiones

## Tareas

### T1 · Catálogo y generador (día 1)

- 3 proveedores ficticios con RFC de formato válido (12 caracteres persona moral), razón social y régimen.
- 40 SKUs con unidad (`pza`, `kg`, `caja`, `litro`), precio, tasa de IVA (incluir algunos al 0 % y alguno exento) y descripción realista.
- El generador recibe la proporción de casos y una semilla, y produce por caso: `oc.json`, `cfdi.xml` (CFDI 4.0 con impuestos por concepto), `remision.pdf` y `esperado.json`.
- **Aceptación:** con la misma semilla genera exactamente los mismos archivos.

### T2 · Composición del set (36 casos)

| Tipo | Casos | Qué prueba |
| --- | --- | --- |
| Limpio (`MATCH_OK`) | 10 | Que no reclame de más |
| Faltante parcial (`QTY_SHORT`) | 6 | Monto de nota de crédito exacto |
| Alza de precio (`PRICE_UP`) | 5 | Tolerancia y redondeos |
| Cargo no pactado (`UNAGREED_CHARGE`) | 4 | Grok clasifica fletes y maniobras |
| Duplicado (`DUPLICATE`) | 3 | UUID y folio + total |
| IVA mal calculado (`TAX_MISMATCH`) | 3 | Escalamiento obligatorio |
| 69-B o CFDI cancelado | 2 | Bloqueo sin excepción |
| Remisión ilegible, sin firma o con notas a mano | 3 | Confianza baja y nueva foto |

`esperado.json`:

```json
{
  "case_id": "OC-017",
  "estado_final": "EN_RECLAMO",
  "codigos": ["QTY_SHORT"],
  "monto_a_pagar_mxn": "5800.00",
  "fuga_detectada_mxn": "290.00",
  "remision": {"lineas": [{"sku": "TORN-001", "cantidad_recibida": 80}]}
}
```

### T3 · Remisiones físicas (día 2)

Esto es lo que diferencia el proyecto en "datos reales":
1. Imprimir las remisiones generadas.
2. Sellar y firmar la mayoría; dejar alguna sin sello o sin firma.
3. Tachar cantidades a mano y escribir notas ("faltaron 20", "caja dañada").
4. Fotografiar con celular con luz distinta, ángulo, sombra y algo de desenfoque.
5. Etiquetar en `esperado.json` lo que realmente dice cada foto (lo tachado manda).

Si se consigue un cliente piloto: la descarga masiva del SAT da XML reales de proveedores; anonimizar RFC y razón social antes de subir algo al repositorio.

### T4 · Evaluación (día 3)

`python -m eval.evaluar --set datasets/ --salida runs/eval_<fecha>.json`

| Métrica | Fórmula | Meta |
| --- | --- | --- |
| Aprobaciones indebidas | Casos con discrepancia que el agente aprobó / casos con discrepancia | **0 %** (la más importante) |
| Reclamos indebidos | Casos limpios reclamados / casos limpios | < 5 % |
| Exactitud del monto | Casos con monto a pagar correcto al centavo / total | > 95 % |
| Exactitud de códigos | Casos con los códigos exactos / total | > 90 % |
| Exactitud de extracción | Campos de la remisión correctos / campos etiquetados | > 90 % |
| Resolución autónoma | Casos cerrados sin escalar / total | Reportar, sin meta |
| Costo por caso | Suma de `costo_usd` / casos | Reportar |
| Retorno | Pesos de fuga detectada / costo del agente en pesos | Titular del pitch |

- Cada fallo se lista con el caso, lo esperado y lo obtenido, para corregirlo.
- Correr la evaluación **3 veces** y reportar promedio y variación: Grok no es determinista.

### T5 · Optimización de costo: expediente precargado (día 4)

1. **Medir la línea base** con el diseño actual (Grok pide los datos con herramientas).
2. **Precargar:** el código reúne OC, CFDI, cotejo, SAT y 69-B antes de llamar a Grok y le entrega un expediente compacto.
3. **Atajo sin razonamiento:** si el cotejo da `MATCH_OK` y no hay alertas fiscales, el caso se aprueba sin llamar a Grok para decidir (la visión de la remisión sí se usa).
4. **Caché:** system prompt y políticas idénticos en todas las llamadas, con `x-grok-conv-id`.
5. **Modelo por tarea:** si el gateway tiene un modelo más barato, usarlo para redactar el reclamo y dejar el principal para visión y decisión.
6. **Extracción por niveles** ([MEJORAS_COTEJAI.md §1](MEJORAS_COTEJAI.md)):
   - **Nivel 1, sin red:** si la remisión es un PDF digital (texto seleccionable), extraer la tabla con `pdfplumber`; si es un escaneo nítido, OCR local con `rapidocr`.
   - Si cada línea extraída tiene confianza ≥ 0.90 y cuadra con el formato de la remisión, Grok recibe **texto**, no imagen.
   - **Nivel 2, Grok Visión:** fotos, tachones, notas a mano, sellos y firmas, o cualquier línea con confianza baja.
   - El sello y la firma siempre se verifican con visión: el OCR no sabe si una firma existe.
   - Registrar en `llm_calls` qué nivel resolvió cada remisión.
7. **Medir de nuevo** y reportar la diferencia con las mismas 36 entradas, incluyendo qué porcentaje de remisiones resolvió cada nivel. El ahorro de 40–60 % que sugiere MEJORAS es una hipótesis: aquí se confirma o se descarta.

- **Aceptación:** la exactitud no baja y el costo por caso sí.

### T6 · Reporte de S3 (día 5)

`eval/reporte_s3.md` con:
- Tabla de métricas (promedio de 3 corridas).
- Costo por factura antes y después de la optimización, en USD y en MXN.
- Fuga total detectada en el set, en MXN.
- Retorno: pesos detectados por cada peso gastado en el agente.
- Errores encontrados y qué se cambió por cada uno.
- Limitaciones honestas: datos sintéticos, CFDI no timbrados, simulador del SAT.

**Reporte de fugas en HTML** ([MEJORAS_COTEJAI.md §4](MEJORAS_COTEJAI.md)): `python -m eval.reporte --corrida runs/<archivo>.jsonl` genera `runs/reporte_<fecha>.html` con facturas auditadas, fuga detectada y retenida, notas de crédito solicitadas, alertas SAT y 69-B, costo de inferencia y retorno. **Todos los valores salen de la corrida**, nunca de la tabla de ejemplo de MEJORAS. Es la pieza visual para el reporte de S3 y para el pitch.

## Datos de costo

Las tarifas por modelo van en `config/settings.py`. **Confirmar en el panel del reto la tarifa de `grok-4.6`**: la guía solo tiene la de `grok-4.7`. Con los tokens observados en S1 (unos 2,550 de entrada y 150 de salida por caso, en 2 llamadas) el costo por caso es de centavos de dólar; el reporte debe usar las cifras reales de `llm_calls`, no estimaciones.

## Riesgos

| Riesgo | Mitigación |
| --- | --- |
| Grok inventa cantidades ilegibles | Campo `confianza`, umbral de 0.85, regla "null antes que inventar" |
| Resultados distintos entre corridas | 3 corridas y reporte de variación |
| Sobreajustar el prompt a los 36 casos | Separar 26 de desarrollo y 10 de prueba que no se miran hasta el final |
