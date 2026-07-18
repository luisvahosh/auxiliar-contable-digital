---
name: design-plan
description: Genera plan de implementación detallado desde especificación aprobada — lista de tareas ordenadas y estimadas
user-invocable: true
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Grep
  - AskUserQuestion
---

# /design-plan — Plan de Implementación Detallado

Use este skill **después de aprobar el spec** en `/design-spec`. El skill:

1. **Lee el spec aprobado** (`docs/specs/YYYY-MM-DD-*.md`)
2. **Extrae requisitos clave** (qué hacer, quién lo usa, qué puede fallar)
3. **Diseña un plan paso a paso** — lista ordenada de tareas implementables
4. **Genera documento** en `docs/plans/YYYY-MM-DD-{titulo}.md`

El plan es **la guía de desarrollo** — cómo llevar el spec a código.

## Flujo

### Paso 1: Leer especificación aprobada

El skill busca el spec en `docs/specs/` (generado por `/design-spec`).

Extrae:
- **Objetivo** — qué se logra
- **Usuario objetivo** — quién lo usa, restricciones
- **Comportamiento esperado** — qué debe pasar (flujos, integraciones)
- **Posibles errores** — qué validaciones, qué manejo de errores
- **Nivel de automaticidad** — automática/sugerida/manual

### Paso 2: Diseñar tareas

Convierte el spec en **tareas concretas y ordenadas**.

Cada tarea debe:

- **Ser específica** — "Leer `causacion/models.py` líneas 50-80 y entender estructura FacturaCompra" (no "entender modelo")
- **Ser implementable en 1 sesión** — máximo 2-3 horas (si es más, es varias tareas)
- **Tener dependencias claras** — si T2 requiere T1, ordenarlas
- **Nombrar archivos/módulos afectados** — `app/modulo/archivo.py`
- **Incluir criterios de éxito** — cómo sabes que terminó

**Tipo de tareas:**

1. **Setup/Preparación** — crear modelos, migraciones, fixtures
2. **Lógica principal** — signals, servicios, vistas
3. **UI/Formularios** — templates, JavaScript, validaciones frontend
4. **Tests** — unit tests, integration tests, end-to-end
5. **Integración** — conectar con APIs externas, otros módulos
6. **Verificación** — probar en navegador antes de PR (esto guía a `/verify-after-changes`)

### Paso 3: Estimar y ordenar

Para cada tarea:

- **Esfuerzo:** Pequeño (1-2h) / Medio (3-5h) / Grande (6-8h)
- **Dependencias:** "Después de T3, T5"
- **Riesgo:** Bajo / Medio / Alto
- **Asignado a:** Si es equipo, quién la toma

**Ordenamiento:**

1. Tareas sin dependencias primero (setup)
2. Luego tareas que dependen de 1
3. Las de mayor riesgo temprano (detectar problemas pronto)
4. Tests distribuidos (no todo al final)

### Paso 4: Generar documento

Crea `docs/plans/YYYY-MM-DD-{titulo}.md` con:

```markdown
# Plan de Implementación: [Nombre Funcionalidad]
📅 Fecha: YYYY-MM-DD
📋 Spec: docs/specs/YYYY-MM-DD-{titulo}.md

## 1. Objetivo

[Copiado del spec Overview]

## 2. Contexto del Problema

[Copiado del spec Contexto]

## 3. Especificación de Referencia

**Documento:** docs/specs/YYYY-MM-DD-{titulo}.md  
**Usuario objetivo:** [resumen corto]  
**Comportamiento esperado:** [resumen corto]  

Ver spec para detalles completos.

## 4. Lista de Tareas

[Tabla o lista de tareas ordenadas con dependencias, esfuerzo, criterios de éxito]

### T1: Preparación — Leer código existente
- **Esfuerzo:** Pequeño (1-2h)
- **Dependencias:** Ninguna
- **Módulo:** app/causacion/
- **Tarea:**
  1. Lee `app/causacion/models.py` líneas 50-120 (estructura FacturaCompra, FacturaVenta)
  2. Lee `app/causacion/signals.py` (cómo se usan signals para validar)
  3. Ejecuta `python manage.py shell` y verifica FacturaCompra.objects.first()
- **Criterio de éxito:** Entiendes cómo funcionan modelos y signals

### T2: Modelo — Crear AuditoriaFactura
- **Esfuerzo:** Pequeño (2h)
- **Dependencias:** Después de T1
- **Módulo:** app/causacion/models.py
- **Tarea:**
  1. Crea modelo AuditoriaFactura con campos: factura (FK), usuario, timestamp, campo, valor_antes, valor_despues
  2. Agrega Meta.ordering = ['-timestamp']
  3. Crea migración: `python manage.py makemigrations`
- **Criterio de éxito:** Migration crea tabla sin errores

### T3: Lógica — Signal para auditar cambios
- **Esfuerzo:** Medio (3h)
- **Dependencias:** Después de T2
- **Módulo:** app/causacion/signals.py
- **Tarea:**
  1. En post_save signal de FacturaCompra, detecta cambios (comparar con BD anterior)
  2. Para cada campo que cambió, crea AuditoriaFactura
  3. Registra usuario actual, timestamp exacto
- **Criterio de éxito:** Cambios en FacturaCompra se auditan automáticamente

...

## 5. Estimación Total

| Tipo | Count | Esfuerzo Total |
|------|-------|-----------------|
| Pequeño (1-2h) | 3 | 6h |
| Medio (3-5h) | 2 | 10h |
| Grande (6-8h) | 0 | 0h |
| **Total** | **5** | **~16h** |

(Estimación real puede variar ±50%)

## 6. Riesgos y Mitigaciones

| Riesgo | Mitigation |
|--------|------------|
| Cambios concurrentes rompen auditoría | Usar select_for_update en signal |
| Performance: auditoría es lenta | Usar bulk_create si hay muchos cambios |
| Tests lentos | Limitar fixtures a lo necesario |

## 7. Siguiente Paso Después de Completar Tareas

```
1. Todas las tareas completadas → tests pasan
2. /verify-after-changes → prueba en navegador
3. Si todo verde → PR + merge
```
```

### Paso 5: Confirmation y Following Steps

El skill pregunta:

- ¿Te parece bien el plan?
- ¿Hay dependencias que faltan?
- ¿Estimaciones razonables?
- ¿Hay tareas que hay que agregar o quitar?

Luego recomienda:

> **Plan listo.** Comienza por T1 (Preparación). 
> Cuando termines cada tarea:
> - Commit descriptivo
> - Tests pasan
> - Siguiente tarea
> Cuando todas estén hechas: `/verify-after-changes` y PR.

---

## Estructura de Tareas

Cada tarea sigue este template:

```markdown
### T[N]: [Categoría] — [Nombre específico]

- **Esfuerzo:** Pequeño / Medio / Grande
- **Dependencias:** Después de T1, T3 (o "Ninguna")
- **Archivos afectados:** 
  - app/causacion/models.py
  - app/causacion/signals.py
  - app/causacion/tests/test_auditoria.py
- **Criterio de éxito:**
  1. [Condición 1]
  2. [Condición 2]

**Descripción:**
[2-3 párrafos explicando qué hace la tarea]

**Pasos:**
1. [Paso específico, con línea de código si aplica]
2. [Paso 2]
3. [Paso 3]
```

---

## Categorías de Tareas (Típicas)

1. **Preparación / Setup**
   - Leer código existente
   - Crear modelos, migraciones
   - Crear fixtures de prueba

2. **Lógica / Servicios**
   - Implementar signals
   - Servicios o managers
   - Validaciones
   - Cálculos

3. **API / Vistas**
   - Crear vistas (GET, POST)
   - Endpoints, serializers
   - Permisos

4. **UI / Templates**
   - Crear templates HTML
   - Formularios (Django Forms)
   - JavaScript si hay interactividad

5. **Tests**
   - Unit tests para modelos/servicios
   - Tests de API (requests/responses)
   - Tests de UI (Selenium si aplica)

6. **Integración**
   - Conectar con APIs externas
   - Actualizar otros módulos que lo usan
   - Migraciones de datos (si aplica)

7. **Verificación**
   - Pruebas manuales en navegador
   - Coverage de tests ≥ 80%
   - Lint/formato de código

---

## Criterios para Orden de Tareas

1. **Sin dependencias primero** — setup que otros necesitan
2. **Mayor riesgo temprano** — detectar problemas antes de gastar tiempo
3. **Tests cercanos al código** — no todo al final
4. **Integración al final** — cuando el código ya funciona

**Ejemplo de orden:**

```
T1 (Setup: crear modelo)
  ↓
T2 (Lógica: signals)
  ↓
T3 (Tests: unit tests de signals)
  ↓
T4 (Integración: conectar con otro módulo)
  ↓
T5 (UI: template)
  ↓
T6 (Tests: tests de UI)
  ↓
T7 (Verificación: /verify-after-changes)
```

---

## Cuándo Usar

✅ Después de aprobar spec en `/design-spec`  
✅ Antes de empezar a codificar  
✅ Funcionalidad de complejidad media/alta  

❌ Cambios triviales  
❌ Specs que no fueron aprobadas  
❌ Ya estás codificando (demasiado tarde)  

---

## Ejemplo de Uso

```bash
# 1. Terminaste /design-spec y aprobaste el spec

# 2. Invocas /design-plan
/design-plan

# 3. El skill:
# - Lee docs/specs/2026-07-15-validar-cufe-duplicado.md
# - Diseña 7 tareas ordenadas (setup → lógica → tests → UI → verificación)
# - Genera docs/plans/2026-07-15-validar-cufe-duplicado.md

# 4. Pregunta: ¿Te parece bien el plan?
# Usuario: "Sí, empiezo por T1"

# 5. Comienza desarrollo:
# T1: Leer código → T2: Modelo → T3: Signals → T4: Tests → ...

# 6. Después de todas las tareas:
/verify-after-changes
# → Pruebas en navegador
# → PR + merge
```

---

## Integración con Workflow

```
/brainstorming ← Ideación
      ↓
/design-spec ← Especificación + APPROVAL GATE
      ↓
     [Aprueba spec]
      ↓
/design-plan ← Plan de implementación
      ↓
Desarrollo (siguiendo tareas)
      ↓
/verify-after-changes ← Validación en navegador
      ↓
PR + merge
```

---

## Notas Importantes

- **El plan es una guía, no dogma** — si durante T2 ves que necesitas hacer algo de T3, adelante
- **Reestima si cambias scope** — si el spec cambió, reajusta tareas
- **Commits por tarea** — cada T terminada = commit ("Feat: T3 implementar signals")
- **Tests no se omiten** — si no caben en la T lógica, son T separada

---

Usa el plan como **hoja de ruta clara** — cualquiera que lo lea sabe exactamente qué hacer, en qué orden y cuánto tiempo lleva.
