---
name: design-spec
description: Genera especificación de usuario para una funcionalidad — documento Markdown estructurado que sirve como contrato entre análisis y ejecución
user-invocable: true
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Grep
  - AskUserQuestion
---

# /design-spec — Especificación de Usuario

Use este skill **después de `/brainstorming`**, cuando tiene claridad sobre:

- Qué problema resuelve
- Quién es el usuario objetivo
- Qué enfoque eligió (de las alternativas)
- Cuál es el siguiente paso concreto

El skill genera un documento Markdown (`docs/specs/YYYY-MM-DD-title.md`) con 6 secciones que forman un **contrato entre análisis y ejecución**: el documento responde todas las preguntas que un desarrollador hace antes de empezar a codificar.

## Flujo

### Paso 1: Recolectar información de diseño

Haz preguntas si falta claridad sobre:

- **Título/nombre corto** — cómo se llama esta funcionalidad internamente
- **Usuario objetivo** — perfil específico de quién la usa
- **Contexto** — qué problema la disparó, dato o restricción importante
- **Alcance preciso** — qué incluye (happy path + casos edge)
- **Comportamiento esperado** — flujo paso a paso, pantallas, integraciones
- **Errores** — qué puede salir mal, cómo se maneja

**No repitas lo de `/brainstorming`** — asume que ya hay claridad. Si algo quedó vago, pregunta directo en lugar de re-hacer la ideación.

### Paso 2: Generar la especificación

Escribe un documento con estas 6 secciones (orden exacto):

#### 1. Overview
- **Qué es** en 2-3 frases (nivel ejecutivo)
- **Por qué ahora** — trigger, contexto, urgencia (si aplica)
- **Éxito se mide por** — 1-2 criterios observables

#### 2. Usuario Objetivo
- **Perfil** — rol, experiencia, contexto de uso
- **Necesidad concreta** — qué quiere lograr
- **Frecuencia** — ¿diario, semanal, excepcional?
- **Restricciones del usuario** — movilidad, conectividad, conocimiento

#### 3. Contexto del Problema
- **Situación actual** — cómo lo hace hoy (manual, otro software, etc.)
- **Dolor** — qué es tedioso, arriesgado, propenso a error
- **Dato/restricción importante** — si afecta la solución (ej: DIAN requiere X, tributario vence el día 15)
- **Dependencias externas** — otros sistemas, roles, tiempos

#### 4. Alcance
- **Incluye:**
  - Casos de uso cubiertos (listar con números: U1, U2, U3)
  - Flujos soportados
  - Integraciones (si aplica)
  - Módulos/vistas del sistema que toca

- **Excluye deliberadamente:**
  - Qué NO cubrimos (y por qué, si es no obvio)
  - Validaciones que hace otro sistema
  - Extensiones futuras

#### 5. Comportamiento Esperado
- **Happy path** — flujo normal paso a paso (ej: usuario entra → ve lista → elige → confirma → ve resultado)
- **Datos de entrada** — qué ingresa, rangos, validación básica
- **Datos de salida** — qué produce, formato, consumidor
- **Integraciones** — llamadas a APIs, envío de correos, logs, cambios de estado
- **Nivel de automaticidad** — ¿automática/sugerida/manual? (CLAUDE.md §12)
- **UI/UX mínimo** — botones, mensajes, flujo visual (no diseño gráfico, sí flujo)

#### 6. Posibles Errores y Mitigaciones
- **Por caso** (2-4 errores principales):
  - **Error:** Descripción concreta (ej: "Usuario ingresa retefuente que excede el ingreso")
  - **Síntoma:** Cómo se manifiesta (ej: "Asiento no cuadra")
  - **Mitigación:** Cómo se maneja (validar antes de guardar, avisar, rechazar, etc.)
  - **Nivel:** automática/sugerida/manual
  - **Mensaje usuario:** Qué se le dice exactamente

### Paso 3: Guardar y confirmar

1. **Genera** el archivo en `docs/specs/YYYY-MM-DD-{titulo-corto}.md`
2. **Confirma con el usuario** — muestra el camino del archivo
3. **Ofrece edición** — si algo no cuadra, ajusta antes de guardar

### Paso 3.5: Approval Gate — Revisar, Iterar o Aprobar

**Después de generar el spec**, el skill presenta un **approval gate** — punto de decisión antes de continuar:

```
Especificación generada: docs/specs/2026-07-15-validar-cufe-duplicado.md

¿Qué deseas hacer?

[A] Revisar — Ver el documento completo
[B] Iterar — Editar secciones específicas
[C] Aprobar — Documento OK, continuar con /design-plan
[D] Rechazar — Volver a /brainstorming (cambio de dirección)
```

**Opción A: Revisar**
- Muestra el spec completo en pantalla (o abre el archivo)
- Usuario lee y decide siguiente acción
- Luego vuelve al approval gate

**Opción B: Iterar**
- Usuario elige qué sección editar (Overview / Usuario / Contexto / Alcance / Comportamiento / Errores)
- El skill pregunta: "¿Qué cambiar en [Sección]?"
- Usuario responde
- Skill regenera esa sección y vuelve al approval gate

Iteraciones comunes:
- "La estimación de éxito es muy estricta, relajemos"
- "Falta manejar el caso X"
- "Usuario objetivo debería ser más específico"
- "Error Y no es probable, sáquemoslo"

**Opción C: Aprobar**
- Spec está listo y aprobado
- Skill sugiere siguiente paso:
  > ✅ **Especificación aprobada.**
  > Siguiente paso: `/design-plan` para generar plan de implementación
- Usuario puede invocar `/design-plan` ahora o después

**Opción D: Rechazar**
- Spec no refleja lo que se quiere
- Volver a `/brainstorming` para reconsiderar alternativa
- O reconocer que idea necesita más pensamiento

---

## Flujo Completo con Approval Gate

```
/design-spec (después de /brainstorming)
      ↓
  Genera spec en docs/specs/YYYY-MM-DD-*.md
      ↓
  APPROVAL GATE
      ├─ [A] Revisar → Lee spec → Vuelve a gate
      ├─ [B] Iterar → Edita sección → Vuelve a gate
      ├─ [C] Aprobar → ✅ OK → Sugiere /design-plan
      └─ [D] Rechazar → ❌ No OK → Vuelve a /brainstorming
```

Esta puerta evita que un spec imperfecto llegue a desarrollo.

## Estructura de archivo

```
docs/specs/
├── 2026-07-15-validar-cufe-duplicado.md
├── 2026-07-14-nómina-exportar-pila.md
└── 2026-07-10-alertas-tributarias-sms.md
```

Nombre: `YYYY-MM-DD-{titulo-corto-con-guiones}.md`

## Notas importantes

### Sobre el usuario objetivo
No es "contador" o "auxiliar" — es más específico: **"auxiliar de contabilidad que procesa compras diarias y necesita clasificarlas en <5 min"**. La especificación es un **diálogo con el usuario**, no con la arquitectura.

### Sobre alcance
Ser explícito sobre QUE NO INCLUYE es tan importante como lo que sí. Ej: "No validamos contra DIAN (eso lo hace Alegra)" es crítico para evitar scope creep.

### Sobre comportamiento esperado
Escribe el flujo como si lo narrara el usuario: "entro al módulo, veo la lista de facturas pendientes, hago clic en una, aparece un formulario, cambio la cuenta y guardo". No: "POST /api/facturas/<id> con payload JSON".

### Sobre errores
Prioriza los 3-4 que **pueden ocurrir en uso real**. No inventes edge cases paranoides. Si el proyecto valida XML con defusedxml, no necesitas especificar XXE como error.

## Cuándo usar

✅ Después de `/brainstorming` con una alternativa clara  
✅ Funcionalidad de complejidad media/alta  
✅ Algo que toca múltiples módulos o flujos  
✅ Integración que requiere acuerdos sobre qué falla  

❌ Bugs triviales  
❌ Cambios puramente técnicos (refactor, deps)  
❌ Cosas ya especificadas en otro doc  

## Cuándo NO usar

Si la funcionalidad es **tan simple y obvia** que una especificación es overkill (ej: "agregar un campo booleano al modelo Usuario"), no lo hagas. Pero si hay decisión de diseño (¿automática? ¿validación?), sí.

## Integración con brainstorming

Típicamente:

```
1. /brainstorming "Agregar X"
   → Clarificas requisitos, eliges alternativa A

2. /design-spec
   → Generas especificación con esa alternativa

3. Desarrollo (ya con especificación clara)
   → Escribes tests basados en spec
   → Implementas según spec
   → PR referencia el spec doc
```

---

## Plantilla mínima de referencia

Ver TEMPLATE.md para un ejemplo vacío listo para copiar.
