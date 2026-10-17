# 00 · El framework de CotejAI

## 1. Idea central

> **El código calcula, Grok decide, la compuerta autoriza.**

Todo lo que se puede calcular de forma exacta (leer el CFDI, cotejar cantidades y precios, revisar impuestos, consultar el SAT) lo hace código determinista. Grok recibe un **expediente** con los números ya calculados y decide qué hacer usando **herramientas**. Ninguna acción que mueva dinero o hable con un proveedor se ejecuta sin pasar por la **compuerta de políticas**, escrita en código.

## 2. Decisión de framework: SDK propio

| Opción | Veredicto | Motivo |
| --- | --- | --- |
| **SDK propio** (cliente `openai` hacia el gateway) | ✅ Elegido | Control total de tool calling, `x-grok-conv-id`, caché, reintentos y telemetría por llamada; puntúa en "Ingeniería sobre Grok"; el flujo es lineal |
| LangGraph | Descartado por ahora | Aporta puntos de control y pausas humanas, que aquí resuelven la tabla `cases` y la máquina de estados |
| CrewAI | Descartado | No hay roles que repartir entre varios agentes |
| OpenClaw / Hermes | Descartado | Agregan una capa que esconde justo lo que el jurado evalúa |

Se revisa esta decisión solo si el flujo se vuelve un grafo con muchas ramas y pausas humanas.

## 3. Conceptos del framework

| Concepto | Qué es | Dónde vive |
| --- | --- | --- |
| **Caso** | Una unidad de trabajo: una OC con su remisión y su CFDI. El lote es solo una lista de casos | `cotejai/core/caso.py` |
| **Expediente** | Lo que el código reúne antes de llamar a Grok: OC, CFDI parseado, remisión extraída, cotejo, SAT, 69-B, historial del proveedor | `cotejai/core/expediente.py` |
| **Herramienta** | Función que Grok puede llamar. Declara nombre, descripción, esquema de entrada (Pydantic), tipo y manejador | `cotejai/tools/` |
| **Tipo de herramienta** | `lectura` (sin efectos), `accion` (pasa por la compuerta), `terminal` (cierra el caso) | `cotejai/tools/registro.py` |
| **Compuerta** | `policy_gate(caso, herramienta, args)` → permitir, rechazar con motivo o convertir en escalamiento | `cotejai/policy/` |
| **Estado** | Máquina de estados persistente e idempotente del caso | `cotejai/core/estados.py` |
| **Notificador** | Interfaz para hablar con el proveedor o el responsable: `correo`, `webhook`, `platica` | `cotejai/notifiers/` |
| **Módulo fiscal** | Reglas de un país: parseo, validación ante la autoridad, listas negras | `cotejai/fiscal/mx.py` (después `co.py`) |
| **Telemetría** | Una fila por llamada a Grok y por decisión de la compuerta | `cotejai/telemetry.py` |

## 4. Contratos

### 4.1 Herramienta

```python
from typing import Literal, Callable
from pydantic import BaseModel

class Herramienta(BaseModel):
    nombre: str                                   # lo que ve Grok, snake_case en español
    descripcion: str                              # CUÁNDO usarla, no solo qué hace
    entrada: type[BaseModel]                      # el JSON Schema se deriva de aquí
    tipo: Literal["lectura", "accion", "terminal"]
    manejador: Callable[..., dict]

REGISTRO: dict[str, Herramienta] = {}

def herramienta(nombre, descripcion, entrada, tipo="lectura"):
    """Decorador: registra la función y genera la definición para Grok."""
    def envolver(fn):
        REGISTRO[nombre] = Herramienta(nombre=nombre, descripcion=descripcion,
                                       entrada=entrada, tipo=tipo, manejador=fn)
        return fn
    return envolver

def definiciones_para_grok() -> list[dict]:
    return [{"type": "function", "function": {
        "name": h.nombre, "description": h.descripcion,
        "parameters": h.entrada.model_json_schema()}} for h in REGISTRO.values()]
```

Reglas:
- Una herramienta **nunca lanza** hacia el agente: devuelve `{"ok": True, "resultado": ...}` o `{"ok": False, "error": ..., "detalle": ...}`.
- Una herramienta `accion` recibe una **llave de idempotencia** `case_id:herramienta:version` y no repite el efecto si la llave ya existe.
- Montos siempre como `Decimal` en el código y como texto (`"290.00"`) en JSON.

### 4.2 Compuerta

```python
class Decision(BaseModel):
    permitido: bool
    motivo: str | None = None
    convertir_en: str | None = None    # p. ej. "escalar_caso"

def policy_gate(caso: Caso, herramienta: str, args: dict) -> Decision: ...
```

Las reglas viven en `config/policies.yaml` para poder cambiarlas por cliente o por proveedor sin tocar código.

### 4.3 Estados del caso

```
RECIBIDO → DOCUMENTOS_LISTOS → COTEJADO ─┬─► APROBADO
                                          ├─► EN_RECLAMO ─┬─► CERRADO   (llega y se valida el CFDI de egreso)
                                          │               └─► ESCALADO  (vence el plazo)
                                          └─► ESCALADO
```

Cada transición se guarda en `case_events` con fecha, actor (`agente`, `humano`, `sistema`), estado anterior, estado nuevo y motivo. Esa tabla es la bitácora auditable que pide S4.

### 4.4 Notificador

```python
class Notificador(Protocol):
    def enviar(self, destinatario: Destinatario, mensaje: Mensaje, llave: str) -> ResultadoEnvio: ...
```

Se elige con `NOTIFIER=correo|webhook|platica`. Cambiar a Platica en Track 2 es configuración, no arquitectura.

### 4.5 Veredicto

`cerrar_caso` es la única forma de terminar un caso. La compuerta verifica que `monto_a_pagar_mxn` y `fuga_detectada_mxn` sean **idénticos** a los que devolvió el motor de cotejo: Grok no puede cambiar un número.

## 5. Estructura de carpetas objetivo

```text
CotejIA/
├── main.py                        # CLI
├── config/
│   ├── settings.py                # tolerancias, límites, modelo, tarifas, URLs
│   └── policies.yaml              # reglas de la compuerta
├── cotejai/
│   ├── core/        caso.py, expediente.py, estados.py, veredicto.py
│   ├── matching/    engine.py     # hoy src/matching.py
│   ├── fiscal/      mx.py         # hoy src/cfdi.py + SAT + 69-B
│   ├── tools/       registro.py, documentos.py, fiscal.py, pagos.py, notificar.py, control.py
│   ├── policy/      gate.py
│   ├── notifiers/   base.py, correo.py, webhook.py, platica.py
│   ├── agent/       loop.py, prompts.py, llm.py
│   ├── storage/     db.py, modelos.py
│   ├── telemetry.py
│   ├── worker.py
│   └── api/         rest.py, mcp_server.py
├── datasets/                      # casos, etiquetas, generador
├── eval/                          # evaluación y reportes (S3)
├── runs/                          # bitácoras de corridas (no se sube)
├── tests/
└── docs/
```

La migración de `src/` a `cotejai/` es la primera tarea de S2.

## 6. Convenciones

- **Idioma:** dominio en español (`caso`, `remision`, `fuga`); librerías en su idioma.
- **Dinero:** `Decimal`, redondeo `ROUND_HALF_UP` a centavos, nunca `float`.
- **Configuración:** todo número de negocio (tolerancias, límites, tarifas) en `config/settings.py`, nunca en el código.
- **Secretos:** solo en `.env` o en variables del servidor. `.env.example` lleva placeholders.
- **Tests:** cada regla del motor y de la compuerta tiene un test. Una regla sin test no existe.
- **Bitácora:** una línea JSON por evento en `runs/<fecha>.jsonl` además de la base de datos.
- **Commits:** un cambio lógico por commit, mensaje en español.

## 7. Cómo se extiende

| Quiero agregar... | Toco solo |
| --- | --- |
| Una herramienta nueva | Un archivo en `cotejai/tools/` con `@herramienta` y su test |
| Una regla de negocio | `config/policies.yaml` o `matching/engine.py`, y su test |
| Un país (Colombia) | `cotejai/fiscal/co.py` con la misma interfaz que `mx.py` |
| Un canal de aviso | Una clase en `cotejai/notifiers/` |
| Otro modelo de Grok | `MODEL` en `.env` y su tarifa en `settings.py` |
