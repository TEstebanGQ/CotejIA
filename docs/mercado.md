# Mercado: quién necesita CotejAI y por qué le va a importar

> Investigación del 17 de octubre de 2026. Cada cifra trae su fuente y qué tan confiable es. **No uses en el pitch una cifra marcada como "secundaria" sin verificarla en la fuente original.**

## 1. El problema en una frase

> **Las empresas pagan facturas por mercancía que nunca recibieron, a precios que nunca pactaron, y a veces a proveedores que el fisco ya declaró fantasma.**

Nadie lo nota porque quien recibe la mercancía (almacén, obra, cocina) no es quien paga (cuentas por pagar), y la remisión firmada se queda en papel.

## 2. Por qué es real: datos

| Dato | Cifra | Confiabilidad |
| --- | --- | --- |
| Pagos duplicados o erróneos | 0.8 % a 2 % del gasto total, atribuido a benchmarks de APQC | Secundaria: lo citan blogs de proveedores ([Transparent Global](https://transparentglobal.com/blog/what-percentage-of-ap-spend-is-lost-to-duplicate-payments-industry-benchmarks/), [Dost](https://www.dost.io/blog/duplicate-payments-in-accounts-payable-how-to-detect-and-prevent-them)). Rango más conservador visto: 0.1 % a 0.5 % |
| Facturas que caen en excepción | 10 % a 20 % de las facturas | Secundaria, de proveedor ([Energent](https://www.energent.ai/use-cases/en/compare/three-way-match-with-ai)) |
| RFC en la lista 69-B (México) | ~11,122 definitivos al 12 oct 2026 | Base de un tercero, no oficial ([Herramientas Fiscales](https://herramientasfiscales.mx/consulta-efos)). El SAT sigue publicando: 83 definitivos y 137 presuntos en el DOF del 18 sep 2026 ([MySuite](https://blog.mysuitemex.com/2026/09/22/listado-definitivo-69b-cff-sin-efectos-fiscales/)) |
| Consecuencia de pagarle a un EFOS | El gasto se presume inexistente: no es deducible; el receptor tiene un plazo para probar materialidad o corregir; puede llegar a restricción del certificado de sello digital | Divulgación ([Siempre al Día](https://siemprealdia.co/mexico/fiscal/plazo-de-30-dias-efos-del-sat/), [Siigo](https://www.siigo.com/mx/blog/obligaciones-fiscales/que-son-las-efos/)). Confirmar plazos en el DOF |
| Proveedores ficticios (Colombia) | ~2,270 posibles detectados por la DIAN en el 3.er trimestre de 2025 | Comunicado de la DIAN citado por [INCP](https://incp.org.co/publicaciones/2025/10/dian-pone-la-lupa-sobre-mas-de-2-200-posibles-proveedores-ficticios-en-el-pais/) y [Portafolio](https://www.portafolio.co/economia/impuestos/dian-detecta-mas-de-2-200-posibles-proveedores-ficticios-por-facturas-falsas-en-colombia-642232) |
| Empresas medianas en México | 0.7 % de 5.45 millones de unidades económicas (51 a 250 empleados); aportan 21.8 % de los ingresos | INEGI, Censos Económicos 2024 ([México, ¿cómo vamos?](https://mexicocomovamos.mx/publicaciones/2025/07/censos-economicos-2024-como-vamos-con-la-estructura-productiva-del-pais/)). **Estimación propia:** unas 38,000 empresas medianas |

**Cómo decirlo en el pitch sin exagerar:** "Si una empresa mediana compra $50 millones de pesos al año y pierde aunque sea el 0.5 %, son $250,000 pesos al año. CotejAI cuesta una fracción de eso." El cálculo es ilustrativo; el número real sale de los clientes piloto.

## 3. Quién lo necesita: segmentos ordenados

El cliente ideal tiene tres cosas: **compra mercancía física con frecuencia, la recibe en un lugar distinto de donde se paga, y tiene muchos proveedores**.

| # | Segmento | Por qué le duele | Señal de que es buen cliente | Prioridad |
| --- | --- | --- | --- | --- |
| 1 | **Constructoras medianas** | El material (concreto, acero, block) llega a la obra con remisión en papel firmada por el residente; la factura llega semanas después a oficinas. Es donde más se pierde el rastro | Varias obras activas al mismo tiempo | ⭐ Piloto ideal |
| 2 | **Grupos restauranteros y hoteles** | Entregas diarias de muchos proveedores pequeños; merma; el proveedor ya habla por WhatsApp | 3 o más sucursales | ⭐ Piloto ideal; encaja con Platica |
| 3 | **Distribuidoras y ferreteras** | Facturas con decenas de partidas; entregas parciales; diferencias de precio por lista | Más de 200 facturas de proveedor al mes | Alta |
| 4 | **Manufactura mediana** | Materia prima con entregas parciales contra una OC grande | Usa OC formales | Media |
| 5 | **Hospitales y clínicas privadas** | Insumos médicos con muchos SKUs y precios por contrato | Compras centralizadas | Media |

**Personas que deciden:** el contralor o gerente de administración (paga por el control), el jefe de cuentas por pagar (usa la herramienta), el dueño en empresas medianas (paga por el dinero recuperado).

**Canal que multiplica:** los **despachos contables**. Un despacho atiende decenas de PyMEs y es responsable de sus deducciones: el riesgo 69-B le cae a ellos. Venderle a un despacho es venderle a 30 empresas.

## 4. Competencia, sin maquillar

| Tipo | Ejemplos | Qué hacen | Qué no hacen |
| --- | --- | --- | --- |
| Portales de recepción de CFDI (México) | [EdiFact V3000 PRO](https://www.edifact.com.mx/validador-cfdi-v3000-pro.php), [PortaldeProveedores.mx](https://www.portaldeproveedores.mx/blog/complementos-de-pago-riesgos/) | Reciben XML, validan ante el SAT, revisan lista negra, mandan lo aceptado al ERP | No leen la remisión física, no hacen el cotejo de lo recibido, no persiguen la nota de crédito |
| Agentes de cotejo de tres vías (globales) | [Beam AI](https://beam.ai/agents/three-way-match-agent/), [Spendflo](https://www.spendflo.com/agents/ai-three-way-match-agent), [MAQ Software](https://df.marketplace.microsoft.com/ja-jp/product/maqsoftware.invoice_po_agent_) | Cotejan OC, recepción y factura con IA | Sin CFDI, SAT ni 69-B; pensados para empresas con ERP grande |
| ERP con cuentas por pagar | SAP, Oracle, Microsoft | Cotejo si la recepción se capturó en el sistema | La PyME no captura la recepción; la remisión vive en papel |

> **Corrección:** en [README_PLATICA.md](../README_PLATICA.md) dije que nadie validaba el SAT y la 69-B. No es así: los portales de proveedores mexicanos ya lo hacen. Lo que nadie junta es lo que sigue.

**Lo que hace único a CotejAI:**
1. **Lee la remisión de papel** con visión: tachones, notas a mano, sello y firma. Es el eslabón que nadie digitaliza.
2. **Cierra el ciclo solo:** detecta, retiene, pide la nota de crédito al proveedor **por WhatsApp**, valida el CFDI de egreso cuando llega y libera el pago neto.
3. **Para la empresa que no tiene ERP grande:** funciona con fotos, XML y una hoja de OC.
4. **Multipaís desde el diseño:** el módulo fiscal se cambia por país (sección 5).

## 5. No es solo México

Casi toda América Latina ya obliga la factura electrónica en XML validada por la autoridad, que es justo lo que CotejAI parsea sin LLM. El cotejo (OC, remisión, factura) es igual en todas partes; lo que cambia es el módulo fiscal.

| País | Sistema | Modelo | Lista negra equivalente | Módulo |
| --- | --- | --- | --- | --- |
| 🇲🇽 México | CFDI 4.0 (SAT), timbrado por un PAC | Clearance delegado | Lista 69-B (EFOS) | `fiscal/mx.py` ✅ |
| 🇨🇴 Colombia | Factura electrónica UBL 2.1 (DIAN) + eventos RADIAN | Clearance | Listado de proveedores ficticios de la DIAN | `fiscal/co.py` — segundo país |
| 🇨🇱 Chile | DTE (SII) | Post-clearance | Por investigar | `fiscal/cl.py` |
| 🇵🇪 Perú | CPE (SUNAT) | Post-clearance | Condición "no habido" (por confirmar) | `fiscal/pe.py` |
| 🇪🇨 Ecuador | Comprobantes electrónicos (SRI), XML con firma | Clearance | Por investigar | `fiscal/ec.py` |
| 🇬🇹 Guatemala | FEL, por certificadores | Clearance delegado | Por investigar | `fiscal/gt.py` |
| 🇨🇷 Costa Rica | Comprobante electrónico 4.4 (Hacienda) | Clearance | Por investigar | `fiscal/cr.py` |
| 🇦🇷 Argentina | Factura electrónica (ARCA) | Por confirmar | Base de facturas apócrifas (por confirmar) | `fiscal/ar.py` |
| 🇧🇷 Brasil | NF-e, con reforma tributaria hasta 2033 | Clearance | — | Último: el más complejo |
| 🇪🇺 Unión Europea | Peppol / ViDA: Bélgica desde 2026, Francia desde sep 2026, Alemania escalonado, transfronterizo desde 2030 | Varía | — | Futuro |

Fuentes de la tabla: [Thomson Reuters](https://europe.thomsonreuters.com/blog/e-invoicing-ctc-models), [SAP Community](https://community.sap.com/t5/technology-blog-posts-by-sap/document-reporting-compliance-central-america-amp-latin-america/ba-p/14111016), [e-invoice.app](https://www.e-invoice.app/blog/global-e-invoicing-compliance-2026), [eConnect (ViDA)](https://econnect.eu/en/docs/knowledge/regulations/europe/vida/timeline), [OriginStamp](https://originstamp.com/en/blog/reader/eu-e-invoicing-mandates-timeline-2026-2030). Son mayormente fuentes de proveedores: confirmar fechas con cada autoridad fiscal antes de afirmarlas.

**Orden de expansión sugerido:** México (el reto) → Colombia (equipo Campuslands, DIAN con lista pública de ficticios) → Perú y Chile → resto de Centroamérica → Brasil.

**En el framework:** cada país implementa la misma interfaz:

```python
class ModuloFiscal(Protocol):
    pais: str
    def leer_factura(self, ruta: str) -> Factura: ...            # XML → modelo común
    def estado_ante_autoridad(self, factura: Factura) -> str: ...  # vigente, cancelada, no verificado
    def proveedor_en_lista_negra(self, id_fiscal: str) -> bool: ...
    def tasas_validas(self) -> set[Decimal]: ...
    def nota_credito_valida(self, nota: Factura, original: Factura) -> bool: ...
```

## 6. Cómo hacer que llame la atención

**Frase de entrada:**
> "¿Cuánto pagaste este mes por cosas que nunca llegaron a tu almacén? CotejAI lo sabe antes de que pagues."

**El momento de la demo** (30 segundos que se recuerdan):
1. Una foto de una remisión arrugada, con "faltaron 20" escrito a mano.
2. CotejAI la lee, la cruza con la factura y la OC: **$290 de fuga**.
3. Retiene ese monto y en segundos le llega al proveedor un WhatsApp pidiendo la nota de crédito.
4. El proveedor contesta y el caso se cierra solo.

**Tres números para el pitch** (salen de S3 y S4, no inventarlos):
- Pesos de fuga detectados por cada peso gastado en el agente.
- 0 % de aprobaciones indebidas en el set de evaluación.
- 1,000 facturas en 12 horas sin intervención.

**Hipótesis de precio** (para validar en Track 2): cobro por factura auditada o suscripción mensual por volumen. Como referencia, Platica cobra unos $0.69 MXN por interacción en su plan Basic de $2,499 MXN al mes ([platica.mx](https://platica.mx)). El precio debe quedar muy por debajo de la fuga que evita y muy por encima del costo de tokens medido en S3.

## 7. Cómo validar con clientes reales (Track 2)

**Meta:** 10 entrevistas y 1 o 2 pilotos con datos reales.

**Dónde buscarlos:**
- La red de Campuslands y de Platica (sus clientes ya usan WhatsApp con agentes).
- Despachos contables: un solo contacto abre varias empresas.
- Cámaras de la industria: construcción, restaurantes, comercio.
- LinkedIn: contralores y gerentes de administración de empresas medianas.

**Cinco preguntas para la entrevista:**
1. ¿Cuántas facturas de proveedor reciben al mes y quién las revisa?
2. ¿Cómo comprueban hoy que lo facturado es lo que llegó?
3. ¿Cuándo fue la última vez que pagaron algo que no llegó o que costaba menos? ¿Cuánto fue?
4. ¿Cómo piden hoy una nota de crédito y cuánto tarda en llegar?
5. ¿Revisan la lista 69-B antes de pagar? ¿Les ha tocado un proveedor en la lista?

**Señal de que hay negocio:** que respondan la 3 con un monto concreto y acepten compartir un mes de XML y fotos de remisiones para un piloto.

## 8. Riesgos de mercado

| Riesgo | Mitigación |
| --- | --- |
| "Ya tengo un portal de proveedores" | CotejAI se conecta después del portal: el portal valida el XML, CotejAI coteja contra lo recibido y persigue la nota de crédito |
| No quieren dar sus datos | Piloto con datos anonimizados; despliegue en su propia nube más adelante |
| El proveedor no responde por WhatsApp | Escalar a correo y al comprador; el pago queda retenido igual |
| Reglas fiscales mal interpretadas | Validar el módulo de cada país con un contador local antes de vender ahí |
