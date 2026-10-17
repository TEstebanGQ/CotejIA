# CotejAI

Agente autónomo que audita facturas de proveedores antes de pagarlas. Reto Agente 2026 (Platica.mx × Campuslands), Track 1, **entrega S1**.

## El problema

Las empresas pagan facturas que no coinciden con lo que pidieron ni con lo que recibieron: se factura más de lo entregado, el precio sube sin aviso, o se cobran conceptos no pactados. En una cuenta por pagar manual, cotejar **orden de compra (OC) ↔ remisión de almacén ↔ factura CFDI** toma minutos por factura y los errores se pagan en pesos. CotejAI hace ese cotejo, calcula la fuga exacta en MXN y decide qué hacer: aprobar, reclamar al proveedor o escalar a una persona.

## Qué hace hoy (S1)

Flujo de principio a fin sobre 3 casos sintéticos con CFDI 4.0 de formato real:

```
caso (OC + remisión + CFDI XML)
   └─► Grok 4.7 (tool calling) ──► cotejar_caso  (Python determinista, Decimal)
                              └──► cerrar_caso   (veredicto estructurado)
```

- **El código calcula, Grok decide.** `src/matching.py` aplica la regla *se paga lo recibido, al precio pactado, sin exceder lo ordenado* y devuelve códigos de discrepancia y montos. Grok no puede alterarlos; interpreta y elige la acción.
- **La factura se parsea, no se "lee":** `src/cfdi.py` lee el XML CFDI 4.0 sin LLM.
- **Veredicto estricto:** `cerrar_caso` entrega `APROBADO`, `EN_RECLAMO` o `ESCALADO`, validado con Pydantic.
- Telemetría básica por caso: llamadas, tokens y latencia.

| Caso | Situación | Resultado esperado |
| --- | --- | --- |
| OC-001 | Todo cuadra | `MATCH_OK` → APROBADO, $0 de fuga |
| OC-002 | Se facturaron 100 tornillos, se recibieron 80 | `QTY_SHORT` → EN_RECLAMO, fuga $290.00 |
| OC-003 | Cable facturado a $88 en vez de $80 | `PRICE_UP` → EN_RECLAMO, fuga $464.00 |

## Cómo correrlo

```bash
pip install -r requirements.txt
cp .env.example .env        # pega tu RETO_KEY (nunca la subas al repo)
python datasets/generate.py # genera los 3 casos de ejemplo
python main.py audit --case OC-002
python main.py audit --all
python main.py cotejo --case OC-002   # solo el motor, sin Grok
pytest
```

## Qué falta (S2 en adelante)

Lectura de remisiones escaneadas con Grok Vision, validación del CFDI ante el SAT y lista 69-B, compuerta de políticas y solicitud de nota de crédito por correo/webhook (S2); set de 36 casos etiquetados y reporte de costo por factura (S3); corrida de 1,000 casos desatendida (S4). El diseño completo está en [CotejAI_guia_implementacion.md](CotejAI_guia_implementacion.md).

## Licencia

MIT. Ver [LICENSE](LICENSE).
