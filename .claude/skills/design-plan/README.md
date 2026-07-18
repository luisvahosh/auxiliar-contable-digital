# Skill Design-Plan — Plan de Implementación Detallado

Este skill convierte una **especificación aprobada** en un **plan paso a paso** — la hoja de ruta exacta del desarrollo.

## Cuándo Usar

✅ Después de aprobar el spec en `/design-spec`  
✅ Antes de empezar a codificar  
✅ Tienes claridad total sobre QUÉ hacer, ahora necesitas CÓMO hacerlo  

❌ Funcionalidades triviales  
❌ Specs que aún están siendo refinadas  

## Qué Sale

Un documento en `docs/plans/YYYY-MM-DD-{titulo}.md` con:

1. **Objetivo** — qué se logra (copiado del spec)
2. **Contexto del problema** — por qué (copiado del spec)
3. **Ref al spec** — link exacto a la especificación
4. **Lista de tareas ordenadas:**
   - T1: Preparación → Leer código
   - T2: Modelo → Crear estructura
   - T3: Lógica → Implementar servicios
   - T4: Tests → Unit tests
   - T5: UI → Templates
   - ... (según lo que necesite)

Cada tarea tiene:
- Esfuerzo (Pequeño/Medio/Grande)
- Dependencias (después de qué tarea)
- Archivos afectados
- Pasos concretos
- Criterios de éxito

---

## Ejemplo Rápido

### Spec aprobado: "Validación de CUFE Duplicado"

```
/design-plan
```

El skill genera:

```markdown
# Plan de Implementación: Validación de CUFE Duplicado
📅 Fecha: 2026-07-15
📋 Spec: docs/specs/2026-07-15-validar-cufe-duplicado.md

## Objetivo
Cuando auxiliar sube factura de compra, validamos que CUFE no exista ya.

## Contexto del Problema
Hoy se generan asientos duplicados que rompen cuadre.

## 4. Lista de Tareas

### T1: Preparación — Leer código existente
- Esfuerzo: Pequeño (1-2h)
- Dependencias: Ninguna
- Pasos:
  1. Lee app/causacion/models.py líneas 50-120
  2. Entiende FacturaCompra, FacturaVenta
  3. Lee app/causacion/signals.py
- Criterio: Entiendes modelos y signals

### T2: Modelo — Agregar campo cufe
- Esfuerzo: Pequeño (30 min)
- Dependencias: Después de T1
- Pasos:
  1. Agrega field cufe a FacturaCompra
  2. makemigrations
  3. migrate
- Criterio: Campo existe, puede guardar CUFE

### T3: Lógica — Signal para validar duplicado
- Esfuerzo: Medio (3h)
- Dependencias: Después de T2
- Pasos:
  1. Pre-save signal: valida CUFE no exista
  2. Si existe: levanta ValidationError con ref a original
  3. Maneja por tipo (compra vs venta)
- Criterio: ValidationError se dispara si duplicado

### T4: Vistas — Retornar 409 en API
- Esfuerzo: Pequeño (1h)
- Dependencias: Después de T3
- Pasos:
  1. Catch ValidationError en view
  2. Retorna JsonResponse status=409
  3. Incluye datos de factura original
- Criterio: API retorna 409 con datos cuando duplicado

### T5: Pruebas — Unit tests de validación
- Esfuerzo: Medio (2h)
- Dependencias: Después de T4
- Pasos:
  1. Test: crear factura, intentar duplicado → ValidationError
  2. Test: duplicado por CUFE exacto
  3. Test: duplicado por NIT+número+fecha
- Criterio: 3 tests pasan

### T6: UI — Modal de rechazo
- Esfuerzo: Pequeño (1.5h)
- Dependencias: Después de T4
- Pasos:
  1. Template modal de "Factura duplicada"
  2. JavaScript para mostrar/ocultar
  3. Botones "Entendido" y "Ver original"
- Criterio: Modal aparece y es usable

### T7: Verificación — Pruebas manuales
- Esfuerzo: Pequeño (1h)
- Dependencias: Después de T6
- Pasos:
  1. /verify-after-changes
  2. Prueba los 5 casos
  3. Todos pasan
- Criterio: 5/5 casos verde

## Estimación Total
~13 horas

## Siguiente paso
Comienza por T1. Cuando termines cada tarea:
1. Commit git
2. Tests pasan
3. Siguiente tarea
```

---

## Qué hace Internamente

1. **Lee el spec** (`docs/specs/`)
2. **Extrae requisitos:**
   - Qué es lo que debe pasar (Comportamiento esperado)
   - Qué errores manejar (Posibles errores)
   - Quién lo usa (Usuario objetivo)
   - Integraciones (si toca APIs, etc.)
3. **Diseña tareas** basadas en:
   - Dependencias lógicas (primero setup, luego lógica)
   - Complejidad (tareas pequeñas, implementables)
   - Riesgo (lo crítico temprano)
4. **Ordena tareas** en secuencia óptima
5. **Genera documento** con detalles concretos

---

## Estructura de Tareas Típicas

**Preparación** (30 min - 2h)
- Leer código existente
- Crear modelos, migraciones
- Crear fixtures

**Lógica** (1-6h)
- Servicios, signals, validaciones
- Cálculos
- Integraciones internas

**API/Vistas** (1-3h)
- Endpoints
- Serializers
- Permisos

**UI** (1-4h)
- Templates
- Formularios
- JavaScript

**Tests** (2-6h)
- Unit tests
- Integration tests
- UI tests

**Verificación** (1-2h)
- Pruebas manuales en navegador
- Coverage ≥ 80%

---

## Cómo se Integra

```
Flujo Completo:

/brainstorming
      ↓ (Clarifica + elige alternativa)
/design-spec
      ↓ (Escribe especificación)
   [APRUEBA SPEC]
      ↓ (Approval gate)
/design-plan
      ↓ (Plan detallado)
Desarrollo (siguiendo tareas)
      ↓
/verify-after-changes
      ↓
PR + merge
```

---

## Cuándo Regresar a /design-plan

Si durante el desarrollo descubres que:
- Una tarea es más grande de lo estimado
- Hay una dependencia que falta
- Hay una tarea que no estaba en el plan

Puedes:
1. Reajustar el plan
2. Dividir la tarea en dos
3. Agregar nuevas dependencias

Actualiza `docs/plans/` y continúa.

---

## No Necesitas Memorizar

El skill te guía. Simplemente:

1. Después de aprobar spec: `/design-plan`
2. El skill pregunta si te parece bien
3. Comienzas por T1
4. Sigues las tareas en orden
5. Cuando todas estén hechas: `/verify-after-changes`

---

## Checklists Antes de Invocar

- [ ] ¿Terminé `/design-spec`?
- [ ] ¿Aprobé el spec? (con approval gate)
- [ ] ¿Tengo claridad sobre qué codificar?

Si sí a todas → adelante con `/design-plan`.

---

Úsalo como **brújula durante el desarrollo** — cada tarea tiene un propósito, un criterio de éxito y es implementable.
