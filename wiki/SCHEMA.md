# LLM Wiki Schema & Governance — CotejAI

Este documento establece el contrato de operación, estructura y convenciones para el mantenimiento de la **Wiki de Conocimiento Persistente** de CotejAI gestionada por agentes de IA en colaboración con humanos.

Basado en el patrón *LLM Wiki* (Memex compounding artifact), Obsidian-friendly.

---

## 1. Las Tres Capas

```
┌────────────────────────────────────────────────────────┐
│ 1. Raw Sources (wiki/raw/)                             │
│    Documentos inmutables, especificaciones del torneo, │
│    transcripciones, prompts y guías oficiales.         │
└──────────────────────────┬─────────────────────────────┘
                           │ Ingest / Síntesis
┌──────────────────────────▼─────────────────────────────┐
│ 2. The Wiki (wiki/)                                    │
│    Artículos estructurados, interconectados y          │
│    mantenidos por el LLM:                              │
│    - index.md (Catálogo maestro de contenidos)         │
│    - log.md (Historial cronológico append-only)        │
│    - entities/ (Sistemas externos, APIs, modelos)      │
│    - concepts/ (Patrones de arquitectura, diseño)      │
│    - tools/ (Especificaciones de herramientas del LLM) │
│    - sprints/ (Hitos S1-S4, rúbricas, guiones demo)    │
└──────────────────────────┬─────────────────────────────┘
                           │ Gobernanza
┌──────────────────────────▼─────────────────────────────┐
│ 3. The Schema (wiki/SCHEMA.md)                         │
│    Reglas de formato, ciclo de vida, linteo y flujos.  │
└────────────────────────────────────────────────────────┘
```

---

## 2. Convenciones de Formato

### Frontmatter YAML obligatorio
Cada página en la wiki (excepto `index.md`, `log.md` y `SCHEMA.md`) debe comenzar con frontmatter YAML compatible con Dataview de Obsidian:

```yaml
---
title: "Nombre Canónico de la Página"
type: entity | concept | tool | sprint | synthesis
tags: [cotejai, s2, herramientas, resiliencia]
created: YYYY-MM-DD
updated: YYYY-MM-DD
status: stable | draft | deprecated
sources:
  - "[[raw/spec-s2-herramientas-resiliencia]]"
---
```

### Enlaces y Navegación
- Usar enlaces dobles tipo wiki `[[nombre-archivo]]` para links internos (compatibles con el Graph View de Obsidian).
- Mantener nombres de archivo en minúsculas con guiones (`kebab-case.md`).
- Proveer siempre texto descriptivo en enlaces contextuales.

---

## 3. Operaciones del Agente

### Operación 1: `Ingest`
Cuando entra un nuevo archivo fuente a `wiki/raw/`:
1. El agente lee la fuente sin modificarla.
2. Extrae entidades clave, decisiones técnicas y restricciones de negocio.
3. Actualiza o crea páginas en `entities/`, `concepts/`, `tools/` o `sprints/`.
4. Si detecta discrepancias con información previa, documenta la contradicción explícitamente en una sección `## Conflictos / Evolución`.
5. Actualiza `wiki/index.md` con la nueva entrada y su resumen de una línea.
6. Registra en `wiki/log.md`:
   ```markdown
   ## [YYYY-MM-DD] ingest | Título de la fuente
   - Resumen de lo integrado
   - Páginas modificadas o creadas: [[pagina-1]], [[pagina-2]]
   ```

### Operación 2: `Query`
1. El agente consulta primero `wiki/index.md` para ubicar el conjunto de páginas relevantes.
2. Lee las páginas necesarias y sintetiza la respuesta citando las páginas fuente `[[pagina]]`.
3. Si el usuario formula un análisis complejo, comparación técnica o deducción inédita, el resultado **se guarda como nueva página en la wiki** para que el conocimiento sea acumulativo.

### Operación 3: `Lint`
Auditoría periódica de salud del grafo de conocimiento:
- Detección de páginas huérfanas (sin enlaces entrantes).
- Detección de enlaces rotos (`[[enlace-inexistente]]`).
- Detección de afirmaciones obsoletas o contradicciones sin resolver entre fases (ej. S1 vs S2).
- Verificación de consistencia entre la especificación de herramientas y el código real en `cotejai/` o `src/`.

---

## 4. Filosofía de Mantenimiento
- **El humano:** Dirige la estrategia, provee fuentes oficiales, formula preguntas y supervisa la arquitectura.
- **El LLM:** Mantiene la wiki actualizada, enlaza conceptos, preserva el contexto del torneo y asegura que ningún aprendizaje se pierda entre sesiones de chat.
