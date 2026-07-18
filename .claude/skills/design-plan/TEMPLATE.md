# TEMPLATE — Plan de Implementación

Copia este template para generar nuevos planes. Reemplaza los placeholders `[...]` con contenido real.

```markdown
# Plan de Implementación: [Nombre Funcionalidad]
📅 Fecha: YYYY-MM-DD
📋 Especificación de Referencia: docs/specs/YYYY-MM-DD-{titulo}.md

## 1. Objetivo

[Copiado del spec "Overview" — 2-3 frases sobre qué se logra]

**Éxito se mide por:**
- [Métrica 1]
- [Métrica 2]

---

## 2. Contexto del Problema

[Copiado del spec "Contexto del Problema"]

**Situación actual:**  
[Qué hace hoy, manualmente]

**Dolor:**  
[Qué es tedioso/arriesgado]

**Dato importante:**  
[Restricción técnica/negocio que afecta la solución]

---

## 3. Especificación de Referencia

**Documento:** docs/specs/YYYY-MM-DD-{titulo}.md

**Usuario objetivo:** [Resumen: rol, frecuencia, restricciones]

**Comportamiento esperado:** [Resumen: qué pasa cuando todo funciona]

**Posibles errores:** [Resumen: qué validaciones, qué errores]

Ver especificación para detalles completos.

---

## 4. Lista de Tareas

### T1: [Categoría] — [Nombre específico]

**Esfuerzo:** Pequeño (1-2h) / Medio (3-5h) / Grande (6-8h)  
**Dependencias:** Ninguna / Después de T[X], T[Y]  
**Riesgo:** Bajo / Medio / Alto  

**Archivos afectados:**
- `app/modulo/archivo.py`
- `app/modulo/tests/test_xxx.py`

**Descripción:**
[2-3 párrafos explicando qué hace la tarea, por qué es necesaria]

**Pasos:**
1. [Paso específico, con línea de código si aplica]
2. [Paso 2]
3. [Paso 3, incluye comando exacto si aplica]

**Criterio de éxito:**
- [Condición 1 — observable, medible]
- [Condición 2]

---

### T2: [Categoría] — [Nombre específico]

[Repite estructura]

---

### T3: [...]

[Repite estructura — típicamente 5-8 tareas]

---

## 5. Estimación Total

| Tarea | Esfuerzo |
|-------|----------|
| T1: ... | 2h |
| T2: ... | 3h |
| T3: ... | 1.5h |
| ... | ... |
| **TOTAL** | **~XXh** |

(Estimación ±50%)

---

## 6. Riesgos y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigation |
|--------|------------|--------|-----------|
| [Riesgo 1] | Bajo/Medio/Alto | Bajo/Medio/Alto | [Cómo se previene o detecta] |
| [Riesgo 2] | ... | ... | ... |

---

## 7. Siguiente Paso

Después de completar todas las tareas:

1. **Todos los tests pasan** (`pytest ...`)
2. **Verificación en navegador** (`/verify-after-changes`)
3. **Commit + PR**

---

**Plan listo. Comienza por T1. 🎯**
```

---

## Checklist Antes de Usar

- [ ] Copié el template
- [ ] Reemplacé todos los `[...]` con contenido real
- [ ] Tareas tienen dependencias claras
- [ ] Estimaciones son realistas
- [ ] Criterios de éxito son observables
- [ ] Archivos afectados están listos

---

## Tips

1. **Dependencias:** Si T2 necesita que T1 esté lista, escribe "Después de T1"
2. **Criterios:** No escribas "está listo" — escribe "tests pasan", "modal aparece", "API retorna 409"
3. **Estimaciones:** Pequeño = puedo terminar en 1-2h solo sin interrupciones
4. **Riesgos:** Documenta lo que podría salir mal (no paranoia, cosas reales)

---

Llena este template y tendrás una hoja de ruta clara. 🗺️
