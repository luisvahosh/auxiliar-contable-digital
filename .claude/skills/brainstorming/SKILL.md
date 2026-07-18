---
name: brainstorming
description: Estructura de ideación para nuevas funcionalidades — clarifica requisitos y presenta 2-3 alternativas de implementación
user-invocable: true
allowed-tools:
  - Read
  - Edit
  - Write
  - Bash
  - Glob
  - Grep
  - AskUserQuestion
  - mcp__visualize__read_me
  - mcp__visualize__show_widget
---

# /brainstorming — Ideación Estructurada de Funcionalidades

Use este skill cuando comience a trabajar en una **nueva funcionalidad, mejora o corrección** que no sea trivial. El skill:

1. **Clarifica requisitos** — hace preguntas para evitar ambigüedades
2. **Mapea restricciones** — entiende alcance, dependencias, stakeholders
3. **Presenta alternativas** — 2-3 enfoques concretos con trade-offs
4. **Propone siguiente paso** — recomendación accionable para empezar

## Flujo

### Paso 1: Recolectar contexto

Haz preguntas sobre:

- **Objetivo**: ¿Qué problema resuelve? ¿Para quién?
- **Alcance**: ¿Qué casos cubre? ¿Qué excluye deliberadamente?
- **Contexto técnico**: ¿Qué módulos/modelos afecta? ¿Hay dependencias?
- **Restricciones**: ¿Plazo? ¿Presupuesto de cambios? ¿Compatibilidad?
- **Éxito**: ¿Cómo se valida que funciona?

**No hagas preguntas obvias** — si el usuario ya dijo "agregar un campo X a la nómina", no preguntes de nuevo qué es. Pregunta por detalles que requieran decisión.

### Paso 2: Listar alternativas

Presenta **2-3 enfoques** cada uno con:

- **Nombre** — corto, memorable
- **Descripción** — qué es y cómo funciona
- **Ventajas** — cuándo brilla
- **Desventajas** — costos/riesgos
- **Esfuerzo estimado** — pequeño/medio/grande en el contexto del proyecto
- **Archivo clave / módulo** — dónde viviría

**Criterios para elegir alternativas:**
- Una **simple y directa** (MVP, menos cambios)
- Una **robusta pero más trabajo** (cubre más casos)
- Una **experimental o futura** (si aplica; no siempre hay tercera)

Si el usuario menciona una arquitectura clara ya, **no inventes alternativas**. Confirma que entiende y propón el siguiente paso.

### Paso 3: Recomendación y siguiente paso

Después de que el usuario elige (o tú recomiendas), di:

1. **Por qué esa opción** — resume el razonamiento
2. **Siguiente acción concreta** — "leer tal archivo", "crear tests para X", "revisar el módulo Y", etc.
3. **Bloqueos potenciales** — si ves que va a necesitar cambios a componentes compartidos, avisa

## Notas sobre el contexto del proyecto

- **Auxiliar Contable Digital:** Django + tests extensos (229+), multi-tenant, módulos por función (causación/nómina/activos/etc).
- **Principio "Asistir, no reemplazar":** la app apoya al auxiliar; no sustituye softwares especializados (Alegra/Siigo para contabilidad, Aleluya/Nominapp para nómina).
- **Convenciones no negociables** (CLAUDE.md §12):
  - Todo config por `.env`, nada quemado en código
  - Multi-tenant: toda query filtra por empresa, no IDs secuenciales en URLs
  - Humano en circuito: acciones automáticas son nivel automática/sugerida/manual
  - Seguridad: validar XML (defusedxml), no loguear datos financieros, minimizar datos a IA
  - UI: español, mobile-first, números tabulares en tablas contables
- **Integraciones activas:** Alegra (API), NVIDIA NIM (visión), IMAP (buzón)
- **Estado actual:** P1-P13 funcionales + multi-empresa + Postgres; próximas: ampliar corpus del asistente, validar datos reales con contador.

## Patrón: Leer el estado antes de ideate

Si el usuario no contextualizó bien:

1. **Lee CLAUDE.md** (convenciones del proyecto)
2. **Revisa el archivo/módulo** relevante brevemente (no hagas análisis profundo)
3. **Pregunta 2-3 cosas clave** que te falta entender

Así evitas proponer algo que choque con las convenciones o que requiera cambios que el usuario no vio.

## Cuándo NO usar este skill

- Si es una corrección obvia de un bug (usa `/code-review` o directamente fix)
- Si el usuario ya tiene claridad total y dice "empecemos" (dirígete al trabajo)
- Si es una pregunta sobre "¿qué debería hacer?" SIN un problema real (ofrece conversa aquí y sugiere `/brainstorming` si quiere estructurar)

## Cómo invocar

Usuario escribe:
```
/brainstorming agregar notificaciones por correo cuando se aprueba una factura
```

Tú:
1. Lees un poco del módulo de facturas (causación/nómina/etc)
2. Haces 2-3 preguntas (¿solo compras o también ventas? ¿opt-in o automático? ¿usar comando Django o cola async?)
3. Presentas 2-3 alternativas con trade-offs
4. Recomiendas y dices siguiente paso

---

## Plantilla mínima de respuesta

```markdown
## Aclaración de requisitos

1. **Objetivo:** [resumen claro]
2. **Alcance:** [qué cubre / qué no]
3. **Restricciones:** [plazo / cambios mínimos / etc]

## Alternativas

### Opción A: [nombre]
- **Cómo:** [párrafo corto]
- **Ventajas:** [2-3 bullets]
- **Desventajas:** [2-3 bullets]
- **Esfuerzo:** [pequeño/medio/grande]
- **Módulo:** `app/modulo/archivo.py`

### Opción B: [nombre]
...

## Recomendación

**Sugiero Opción A porque:** [1-2 frases]

**Siguiente paso:** [acción concreta]
```
