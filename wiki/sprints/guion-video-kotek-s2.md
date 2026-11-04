# Guion Oficial del Video S2 (2 Minutos) — Narrado por Kótek (Mascota Oficial de CotejAI)

- **Duración total**: ~120 segundos (6 escenas sincronizadas automáticamente en `http://localhost:8000`)
- **Voz generada (ElevenLabs Multilingual v2)**: Voz masculina `Eric` (`cjVigY5qzO86Huf0OWal`) en `web/assets/audio/escena_1_intro.mp3` a `escena_6_circuit_breaker_cierre.mp3`
- **Cómo ejecutarlo en vivo**: Abrir `http://localhost:8000` y hacer clic en el botón superior **`Demo Kótek (2m)`** o en el botón flotante inferior derecho **`Kótek Auditor — ▶ Explicar Proyecto (2m)`**.

---

## Escena 1 (0:00 – 0:20) | ¿Qué es CotejAI y por qué nace?
- **Visual en pantalla**: Modal Hero con **Kótek (el Búho Auditor de 3 Lentes)** en alta resolución, anillos de voz cian/esmeralda y tarjetas de arquitectura (`1. Three-Way Match`, `2. Grok 4.6 Vision`, `3. PostgreSQL 16 + SAT`).
- **Locución de Kótek (`escena_1_intro.mp3`)**:
  > *"¡Hola! Soy Kótek, el búho auditor de tres lentes de CotejAI. Nacimos para resolver uno de los mayores dolores en las empresas mexicanas: la fuga de capital en cuentas por pagar por mermas de almacén, sobrecargos cambiarios y facturas fantasma. A diferencia de un chat común, combino el razonamiento multimodal de Grok cuatro punto seis con un motor matemático determinista y persistencia transaccional en PostgreSQL dieciséis."*

---

## Escena 2 (0:20 – 0:42) | 180 Divisas en Vivo + `consultar_tipo_cambio_real` (`OC-006`)
- **Visual en pantalla**: Kótek pasa a modo *Picture-in-Picture* en la esquina inferior, cambia en vivo el selector de las **180 divisas ISO 4217 / SAT Anexo 20** (`USD` → `EUR` → `USD`), selecciona **`OC-006`** y muestra el toast de invocación de `consultar_tipo_cambio_real("USD", "21.85")` reteniendo `$19,230.39 MXN` por `FX_OVERCHARGE`.
- **Locución de Kótek (`escena_2_arquitectura_divisas.mp3`)**:
  > *"En nuestra barra superior conectamos en tiempo real las ciento ochenta divisas oficiales del anexo veinte del SAT contra el peso mexicano. Por ejemplo, al inspeccionar el expediente OC cero cero seis facturado en dólares, invoco la herramienta consultar tipo de cambio real, detecto un tipo de cambio inflado de veintiuno ochenta y cinco frente al oficial y retengo diecinueve mil doscientos treinta pesos por sobrecargo cambiario."*

---

## Escena 3 (0:42 – 1:06) | Caso Real de Principio a Fin (`OC-004`): `leer_remision_imagen` (Grok Vision)
- **Visual en pantalla**: Kótek selecciona **`OC-004`**, muestra la foto física `remision.png` con la nota escrita a mano, invoca `leer_remision_imagen("OC-004")` y calcula la retención exacta de `$290.00 MXN` (`QTY_SHORT`).
- **Locución de Kótek (`escena_3_vision_merma.mp3`)**:
  > *"Veamos un caso de principio a fin con el expediente OC cero cero cuatro. El proveedor facturó cien piezas, pero al invocar mi herramienta leer remisión imagen con Grok Vision sobre la foto física del almacén, detecto el sello azul, la firma y una nota escrita a mano que reporta solo ochenta piezas por merma en transporte. Mi motor determinista retiene exactamente doscientos noventa pesos con IVA incluido."*

---

## Escena 4 (1:06 – 1:26) | Webhook en Vivo + Bloqueo de Idempotencia en PostgreSQL 16 (`enviar_alerta_reclamo_real`)
- **Visual en pantalla**: En **`OC-004`**, Kótek dispara `enviar_alerta_reclamo_real` por primera vez (enviando el webhook y guardando la llave primaria en `actions`) y 5 segundos después lo dispara por segunda vez mostrando el bloqueo transaccional `idempotencia_bloqueada: true` en PostgreSQL 16.
- **Locución de Kótek (`escena_4_idempotencia.mp3`)**:
  > *"Como la diferencia es menor a cinco mil pesos, mi compuerta policy gate me autoriza invocar enviar alerta reclamo real, disparando el webhook de solicitud de nota de crédito al proveedor. Y si alguien intenta enviarlo por segunda vez, nuestra llave de idempotencia en PostgreSQL dieciséis bloquea automáticamente el duplicado para nunca reclamar dos veces la misma factura."*

---

## Escena 5 (1:26 – 1:48) | ¿Qué hace cuando algo falla? Foto Borrosa (`OC-005`) y Lista Negra 69-B (`OC-007`)
- **Visual en pantalla**: Kótek abre **`OC-005`** mostrando la imagen desenfocada rechazada con `RECEIPT_UNREADABLE` (barrera anti-alucinación) y luego abre **`OC-007`** mostrando al proveedor EFOS Definitivo bloqueado al 100% por `SUPPLIER_69B`.
- **Locución de Kótek (`escena_5_fallos_vision_69b.mp3`)**:
  > *"¿Y qué hago cuando algo falla? En el expediente OC cero cero cinco, la fotografía de la remisión está borrosa. En lugar de inventar números o alucinar cantidades, activo el código recibo ilegible y escalo el caso a revisión humana. Y en el caso OC cero cero siete, al cruzar el RFC contra el padrón oficial del artículo sesenta y nueve B del SAT, bloqueo el cien por ciento del pago por tratarse de una empresa facturadora de operaciones simuladas."*

---

## Escena 6 (1:48 – 2:10) | Caída del SAT SOAP (`Circuit Breaker`) + `Policy Gate` de `$5,000 MXN` (`OC-010`)
- **Visual en pantalla**: Kótek abre **`OC-010`**, ejecuta `consultar_sat_en_vivo("OC-010")` activando el **Circuit Breaker (`OPEN — En Degradación / SAT_NO_VERIFICADO`)** en la barra superior, y muestra cómo la compuerta `Policy Gate` bloquea el reclamo autónomo porque la fuga (`$9,280.00 MXN`) supera el límite de `$5,000 MXN`.
- **Locución de Kótek (`escena_6_circuit_breaker_cierre.mp3`)**:
  > *"Finalmente, en el expediente OC cero diez probamos resiliencia extrema: ante una caída del servicio SOAP del SAT, nuestro Circuit Breaker abre el circuito tras tres fallos, marca el expediente como SAT no verificado sin colgar el sistema, y como el faltante supera el umbral autónomo de cinco mil pesos, el policy gate bloquea el reclamo automático y lo escala a gerencia. Soy Kótek de CotejAI: auditoría autónoma donde la inteligencia artificial razona y la matemática determinista gobierna."*
