---
name: verify-after-changes
description: Valida funcionalidad post-implementación — levanta servidor, prueba 5 casos críticos en navegador, compara con spec, recomienda arreglos o luz verde
user-invocable: true
allowed-tools:
  - Read
  - Bash
  - Glob
  - Grep
  - mcp__Claude_Browser__preview_start
  - mcp__Claude_Browser__preview_stop
  - mcp__Claude_Browser__navigate
  - mcp__Claude_Browser__read_page
  - mcp__Claude_Browser__find
  - mcp__Claude_Browser__computer
  - mcp__Claude_Browser__screenshot
  - mcp__Claude_Browser__form_input
  - mcp__Claude_Browser__read_console_messages
  - AskUserQuestion
---

# /verify-after-changes — Validación Post-Implementación

Use este skill **después de terminar la implementación**, cuando:

- El código está listo (tests pasan)
- La rama está completa
- Quiere **probar en navegador** que funciona de verdad (no solo en tests)
- Necesita **comparar contra la especificación** (`docs/specs/YYYY-MM-DD-*.md`)

El skill:
1. **Levanta el servidor** dev
2. **Identifica 5 casos de prueba críticos** basados en el spec
3. **Prueba cada caso en navegador** (captura pantallas, integraciones reales)
4. **Recoge feedback** (qué funciona, qué falla, qué no encaja)
5. **Compara con spec y plan** — valida que todo cumple
6. **Genera reporte** y recomienda: arreglar X, Y → luz verde o necesita más trabajo

## Flujo

### Paso 1: Leer especificación y plan

- Busca el archivo spec en `docs/specs/` (fecha más reciente o lo que el usuario indique)
- Lee CLAUDE.md / PLAN.md para entender el contexto
- Extrae de spec:
  - **Comportamiento esperado** (happy path, flujos alternativos)
  - **Casos de error** y mitigaciones
  - **Integraciones** (qué APIs, bases de datos, etc.)
  - **Nivel de automaticidad** (automática/sugerida/manual)

### Paso 2: Identificar 5 casos de prueba críticos

Basados en el spec, elige 5 que cubran:

1. **Happy path — Flujo normal** (usuario hace lo que debería, todo funciona)
2. **Error principal** (el error más probable o de mayor riesgo)
3. **Validación** (datos inválidos, límites)
4. **Integración** (si toca APIs externas, verifica funcionamiento)
5. **Edge case** (algo raro pero posible, según spec)

**No es random** — cada caso viene de algo específico en el spec.

### Paso 3: Levantar servidor

```bash
# Busca la configuración en .claude/launch.json
# Levanta servidor dev (ej: python manage.py runserver para Django)
# Espera a que esté listo
# Abre navegador en http://localhost:8000
```

### Paso 4: Probar cada caso en navegador

Para cada uno de los 5 casos:

1. **Describe el caso:** qué vamos a probar
2. **Ejecuta en navegador:** clicks, text input, esperas
3. **Captura evidencia:** screenshot, mensajes de error, estado final
4. **Compara con spec:** ¿qué esperaba el spec? ¿qué vimos?
5. **Registra resultado:**
   - ✅ Funciona exacto
   - ⚠️ Funciona pero con diferencia menor
   - ❌ No funciona / diferencia crítica

### Paso 5: Recoger feedback

Para cada caso que **no es ✅**:

- **Síntoma:** qué viste exactamente
- **Esperado (spec):** qué debería pasar según spec
- **Brecha:** cuál es la diferencia
- **Severidad:** bloqueante / importante / cosmético
- **Causa probable:** qué en el código podría causar esto

### Paso 6: Comparar con spec y plan

Genera **reporte de validación**:

```
CASO 1: Happy path — usuario sube factura duplicada
- Esperado (spec): "Modal muestra datos de factura original"
- Visto: ✅ Modal aparece con datos correctos
- Resultado: PASA

CASO 2: Error — NIT inválido
- Esperado (spec): "Valida que NIT tenga 10 dígitos"
- Visto: ❌ No valida, acepta "ABC123"
- Resultado: FALLA
- Severidad: Importante
- Causa probable: Validador no está activo en frontend

...
```

### Paso 7: Recomendar acción

Después de reporte, el skill dice:

- **Si todo pasa (5/5 ✅):**
  > ✅ **Luz verde.** Todos los casos funcionan según spec. Listo para PR/merge.

- **Si hay fallos menores (3-4 pasan, 1-2 falla cosmético):**
  > ⚠️ **Arregla esto antes de mergear:**
  > - CASO X: [descripción]
  > - Propuesta: [qué cambiar en el código]
  > Luego vuelves a `/verify-after-changes`

- **Si hay fallos críticos (≤2 pasan):**
  > ❌ **Bloquea merge.** Necesita más trabajo:
  > - CASO X: [descripción]
  > - Propuesta: [qué cambiar]
  > Arregla y reintenta.

## Sobre la verificación

### Qué prueba

- **Funcionalidad en navegador** — lo que el usuario realmente ve/hace
- **Integraciones reales** — si llama APIs, lo hace de verdad (con datos de test)
- **Mensajes y UX** — textos exactos, flujo visual
- **Estado después** — BD actualizada, estado correcto

### Qué NO prueba

- **Performance** (eso es después si aplica)
- **Seguridad avanzada** (eso es code-review)
- **Casos tan extremos que nunca ocurren** (confía en unit tests)

### Datos de prueba

Usa datos que ya existen en tu entorno de dev:

- Si el proyecto tiene `datos-prueba/`, úsalos
- Si necesita crear data nueva, hazlo en la prueba (no deja residuos)
- Números/emails reales dentro de lo posible (ej: auxiliar1@test.local)

## Cuándo usar

✅ Después de terminar implementación (código + tests) y antes de PR  
✅ Funcionalidad que toca UI o flujos de usuario  
✅ Cambios en integraciones externas (APIs, servicios)  
✅ Algo que requiere confirmación de "de verdad funciona"  

❌ Cambios puramente técnicos (refactor, dependencies)  
❌ Unit test falla (arregla el código primero)  
❌ No tienes servidor dev levantable  

## Casos especiales

### Si el proyecto es API puro (sin UI)

Adapta: en lugar de navegador, prueba con curl/requests:

```bash
curl -X POST http://localhost:8000/api/facturas/ -d '{"nit":"..."}' -H "Content-Type: application/json"
```

Igual reporte comparado con spec.

### Si la UI es compleja (muchos pasos)

Elige los 5 casos que cubran la **columna vertebral**, no todos los branches. Ej:

- Case 1: Usuario entra, ve lista
- Case 2: Click en item, ve detalles
- Case 3: Modifica campo, guarda
- Case 4: Error en campo X
- Case 5: Logout y login otra vez

### Si hay integración con sistema externo (Alegra, DIAN)

Usa **mock** en dev (ya debe estar configurado). El skill valida que:

- La app hace la llamada correcta (request está bien)
- Maneja respuesta (mock respuesta)
- No valida que Alegra real responda (eso es staging/producción)

## Output

Genera un **reporte markdown** (opcional: guarda en sesión o muestra en consola):

```markdown
# Verificación Post-Implementación
📅 Fecha: 2026-07-15 14:30
📋 Spec: docs/specs/2026-07-15-validar-cufe-duplicado.md

## Resumen
- Casos totales: 5
- Pasados: 4
- Fallidos: 1
- Tasa: 80% ✅

## Detalle

### CASO 1: Happy path — factura nueva
✅ PASA

### CASO 2: Duplicado exacto (CUFE)
✅ PASA

### CASO 3: Duplicado fuzzy (NIT+número+fecha)
⚠️ PASA CON DIFERENCIA MENOR
- Esperado: Modal con botón "Ver original"
- Visto: Modal sí, botón está pero text es "Ver factura"
- Severidad: Cosmético
- Propuesta: Cambiar texto a "Ver original" en template

### CASO 4: Offline → duplicado no detectado
❌ FALLA
- Esperado: App rechaza guardar si conexión offline
- Visto: App NO rechaza, permite guardar offline
- Severidad: Importante
- Propuesta: Validar conexión antes de mostrar botón "Guardar"

### CASO 5: Admin edita directo, crea duplicado
✅ PASA

## Recomendación

⚠️ **Arregla CASO 4 y 3 antes de mergear:**

1. CASO 4: Agregar validación de conexión en `app/causacion/templates/subir_factura.html`
2. CASO 3: Cambiar label en `app/causacion/templates/modal_duplicado.html`

Luego vuelve a `/verify-after-changes`

---
Generated by /verify-after-changes
```

## Notas importantes

- **Honesto:** si falla, reporta que falla. No hace spin positivo.
- **Específico:** "no funciona" → "botón rechaza click", "valores no se guardan", "integración timeout".
- **Práctico:** si ve problema, propone arreglo (línea de código, archivo, qué cambiar).
- **Iterativo:** si arreglas algo, vuelves a `/verify-after-changes` y revalida ese caso.

---

## Integración con workflow

```
Después de: Implementación (código listo, tests pasan)
            ↓
      /verify-after-changes
            ↓
      5 casos en navegador
            ↓
      Reporte + recomendaciones
            ↓
      Arreglar si falla
            ↓
      /verify-after-changes de nuevo
            ↓
      Todo verde
            ↓
      PR + merge
```

---

## Checklists internos del skill

Antes de empezar:
- [ ] ¿Existe spec en docs/specs/? Si no, pedir al usuario que cree con `/design-spec` primero
- [ ] ¿Servidor dev puede levantarse? (verificar .claude/launch.json)
- [ ] ¿Usuario tiene datos de prueba preparados?

Después de probar cada caso:
- [ ] ¿Capturé screenshot o evidencia?
- [ ] ¿Comparé exacto contra spec?
- [ ] ¿Registré síntoma si falla?
- [ ] ¿Propuse cómo arreglarlo?

Antes de recomendar "luz verde":
- [ ] ¿5/5 casos pasan?
- [ ] ¿No hay fallos bloqueantes?
- [ ] ¿El usuario está de acuerdo?

---

Usa este skill como **validación final antes de PR** — garantiza que "pasa tests" = "funciona de verdad".
