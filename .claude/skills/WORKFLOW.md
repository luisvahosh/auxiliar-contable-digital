# Workflow de Desarrollo — Skills Brainstorming + Design-Spec + Verify-After-Changes

Este documento muestra cómo usar los tres skills en conjunto para llevar una idea de proyecto a ejecución.

---

## Flujo Completo: De Idea a Código

```
┌─────────────────────────────────────────────────────────────────┐
│                         NUEVA FUNCIONALIDAD                     │
│                  "Quiero agregar X al sistema"                  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                    ¿Idea clara y sin ambigüedades?
                             │
            ┌────────────────┴────────────────┐
            │ NO                             YES
            ▼                                 ▼
    ┌───────────────────┐        ┌──────────────────────┐
    │ /brainstorming    │        │ /design-spec         │
    │ Estructura la idea│        │ Escribe especificación
    │ - Clarifica       │        │ - 6 secciones        │
    │ - Alternativas    │        │ - Contrato técnico   │
    │ - Recomienda      │        │ - Guía para código   │
    └────────┬──────────┘        └──────────┬───────────┘
             │                              │
             │ Usuario elige opción         │ Genera docs/specs/YYYY-MM-DD-*.md
             │                              │
             └──────────────┬───────────────┘
                            │
                  ¿Especificación clara?
                            │
            ┌───────────────┴────────────────┐
            │ NO                            YES
            ▼                                ▼
    [Ajusta en design-spec]    ┌──────────────────────┐
                               │ DESARROLLO           │
                               │ 1. Crear rama        │
                               │ 2. Escribir tests    │
                               │ 3. Implementar       │
                               │ 4. PR con referencia │
                               └──────────┬───────────┘
                                          │
                                   Código listo,
                                   tests pasan
                                          │
                         ┌────────────────┴──────────────┐
                         │ VERIFICACIÓN EN NAVEGADOR      │
                         │ /verify-after-changes          │
                         │ 1. Levanta servidor            │
                         │ 2. Prueba 5 casos críticos     │
                         │ 3. Compara con spec            │
                         │ 4. Genera reporte              │
                         └──────────────┬─────────────────┘
                                        │
                         ¿Todas las pruebas pasan?
                                        │
                    ┌───────────────────┴──────────────────┐
                    │ NO                                  YES
                    ▼                                      ▼
            [Arregla los casos]                  ┌──────────────────┐
                    │                            │ MERGE            │
                    │                            │ - PR aprobado     │
                    └────────────┬────────────────┤ - Tests pasan    │
                                 │                │ - Spec cumple    │
                    /verify-after-changes ← Revalida     │
                         (reintenta)                      ▼
                                                  ✓ Funcionalidad
                                                  viva en producción
```

---

## Escenario 1: Idea Vaga → Brainstorming → Design-Spec

### Paso 1: Invoca `/brainstorming`

```
Usuario: /brainstorming Agregar validación de CUFE duplicado
```

El skill:
- Pregunta: ¿Solo en compras o también ventas?
- Pregunta: ¿Qué hacer con duplicados?
- Pregunta: ¿Comparación por empresa o global?

Usuario responde → El skill **presenta 2-3 alternativas**

### Paso 2: Elige alternativa

Usuario: "Prefiero Opción B: lógica en signals con historial"

Skill dice:
> **Recomendación:** Opción B porque el proyecto tiene datos financieros sensibles y necesitamos trazabilidad.
> **Siguiente paso:** Leer `causacion/models.py` líneas 50-80, diseñar modelo `AuditoriaFactura`, escribir test.

### Paso 3: Invoca `/design-spec`

Con la alternativa clara, ahora es tiempo de especificación:

```
Usuario: /design-spec
```

El skill pregunta:
- ¿Quién es el usuario que ve esto? (Auxiliar, contador, admin?)
- ¿Qué hace si falla? (Rechaza, avisa, permite forzar?)
- ¿Necesita notificación o solo rechaza silenciosamente?

### Paso 4: Se genera el documento

El skill crea:

```
docs/specs/2026-07-15-validar-cufe-duplicado.md
```

Con 6 secciones, ejemplos, casos de error. El documento es **legible y específico** — cualquiera que lo lea entiende qué debe codificarse.

### Paso 5: Ahora sí, desarrollo

```bash
git checkout -b feat/validar-cufe-duplicado

# Escribir test (TDD)
# Implementar según spec
# PR referencia: "Implementa docs/specs/2026-07-15-validar-cufe-duplicado.md"

git push
```

---

## Escenario 2: Idea Clara → Solo Design-Spec

Si el usuario **ya tiene claridad total** (vino de una reunión con el contador, o es una mejora incremental clara):

```
Usuario: /design-spec Agregar campo 'observaciones' a cada factura de compra

Usuario: [No necesito brainstorming, ya sé exactamente qué]
```

El skill va directamente a preguntas de especificación:
- Usuario objetivo: ¿Quién anota observaciones?
- Comportamiento: ¿En qué lugar de la UI?
- Errores: ¿Validaciones?

Genera documento en 10 minutos. Desarrollo listo.

---

## Escenario 3: Brainstorming Completo, Pero Después Cambia

Usuario hace `/brainstorming`, elige opción A.  
Luego hace `/design-spec` y mientras escribe, se da cuenta que la opción A **no cuadra con la realidad** del usuario.

Puede:

```
Usuario: /brainstorming de nuevo
[Vuelve a las alternativas, elige opción B]

Luego: /design-spec con la opción B correcta
```

Los skills son **iterativos** — no son "una sola vez".

---

## Cuándo SKIP los skills

### Skip ambos si:
- Es un bugfix trivial ("arreglar typo en mensaje")
- Cambio técnico puro que no toca UX ("actualizar librería", "refactorizar función")
- Mejora microscópica que no cambia el flujo

### Skip design-spec pero hacer brainstorming si:
- Decisión arquitectónica compleja
- Varias opciones técnicas pero usuario no es decisor
- Ejemplo: "¿Usamos UUID o ID secuencial en URLs?" → Brainstorming con el equipo, no especificación de usuario

### Skip brainstorming pero hacer design-spec si:
- Mejora incremental de algo que ya existe
- Usuario ya pidió explícitamente exactamente qué quiere
- Ejemplo: "Agregar filtro por fecha en la tabla de facturas"

---

## Integración con testing

Los skills **alimentan TDD**:

```
Spec dice: "Si CUFE duplicado, mostrar modal con datos de original"

Test (antes de código):
  def test_rechaza_cufe_duplicado(self):
    # Arrange
    factura_original = crear_factura_compra(cufe="ABC123")
    # Act
    response = subir_factura_compra(cufe="ABC123")  # Mismo CUFE
    # Assert
    self.assertEqual(response.status_code, 409)  # Conflict
    self.assertIn("Factura duplicada", response.content)
```

La **especificación guía los tests**, no al revés.

---

## Integración con PRs

Cada PR debe referenciar la especificación:

```markdown
## Resumen

Implementa validación de CUFE duplicado en compras.

**Especificación:** docs/specs/2026-07-15-validar-cufe-duplicado.md

## Changes

- Modelo AuditoriaFactura con historial de validaciones
- Signal en post_save de FacturaCompra
- Endpoint retorna 409 si duplicado
- Tests para happy path + 4 casos de error

## Validación

- ✓ Tests pasan (40 nuevos, 0 regresos)
- ✓ Spec + código alineados
- ✓ Probado en staging con datos reales
```

Reviewer abre el spec doc, verifica que el código cumple. Claro.

---

## Checklists de Brainstorming → Design-Spec

### Después de Brainstorming, antes de Design-Spec

- [ ] ¿Entiendes el problema original?
- [ ] ¿Qué alternativa ganó y por qué?
- [ ] ¿Hay decisiones de UX ya hechas o falta precisar?
- [ ] ¿Quién es el usuario final exactamente?

Si todas son SÍ → Design-Spec.  
Si faltan → Más brainstorming.

### Después de Design-Spec, antes de Desarrollo

- [ ] ¿Alguien que no conoce el proyecto entiende qué debe codificarse?
- [ ] ¿Casos de error están claros?
- [ ] ¿Integraciones están mapeadas?
- [ ] ¿Nivel de automaticidad (automática/sugerida/manual) está decidido?

Si todas son SÍ → Listo para código.  
Si faltan → Edita el spec.

---

## Integración con Verify-After-Changes

Después de que **el código está listo y los tests pasan**, viene `/verify-after-changes`:

### Flujo típico

```
1. Implementas la funcionalidad (código + tests)
   pytest → 40/40 tests pasan ✅

2. Invocas /verify-after-changes
   → Lee spec
   → Levanta servidor dev
   → Prueba 5 casos en navegador
   → Compara exacto contra spec

3. Reporte:
   a) Si 5/5 pasan → "Luz verde, listo para PR"
   b) Si algunos fallan → "Arregla estos, reintenta"

4. Arreglas bugs si hay
   → git commit
   → /verify-after-changes de nuevo
   → Valida reintenta

5. TODO verde → PR + merge
```

### Por qué después de tests pasan

- **Unit tests** validan lógica (funciones aisladas, BD)
- **Tests de integración** validan flujos entre módulos
- **Verify-after-changes** valida lo que el usuario **realmente ve y hace**

Es el último veto antes de producción: "¿De verdad funciona en navegador como especificamos?"

### Qué hace el skill

1. **Levanta servidor** (`python manage.py runserver`)
2. **Lee spec** de `docs/specs/`
3. **Elige 5 casos críticos** (happy path, errores principales, validaciones, integraciones, edge cases)
4. **Prueba cada caso en navegador:**
   - Click aquí
   - Ingresa "esto"
   - Verifica que aparece "aquello"
   - Captura screenshot
5. **Compara exacto contra spec:**
   - ¿Texto es exacto?
   - ¿Números calculan correctamente?
   - ¿Integración funcionó?
   - ¿Estado de BD cambió?
6. **Genera reporte:**
   - Caso 1: ✅ pasa
   - Caso 2: ❌ falla (diferencia: [describe], propuesta: [arreglo])
   - ...
7. **Recomienda:** "Luz verde" o "Arregla estos X casos, reintenta"

### Ejemplo: Verificación CUFE Duplicado

```
/verify-after-changes

Spec: docs/specs/2026-07-15-validar-cufe-duplicado.md
Servidor: python manage.py runserver

CASO 1: Happy path — factura nueva
  ✅ PASA — Usuario sube XML, sistema acepta

CASO 2: CUFE duplicado
  ✅ PASA — Modal muestra datos de original

CASO 3: NIT+fecha duplicado
  ✅ PASA — Sistema detecta y rechaza

CASO 4: Offline
  ❌ FALLA — Permite guardar offline (debería rechazar)
    Propuesta: Validar conexión en template, línea 142

CASO 5: Admin crea directo
  ✅ PASA — BD rechaza con error

Resultado: 4/5 (80%)
Recomendación: Arregla CASO 4, luego /verify-after-changes de nuevo
```

Usuario arregla, reintenta, TODO verde → merge.

### Cuándo usarlo

✅ Después de implementar (tests pasan)  
✅ Antes de hacer PR  
✅ Cambios en UI, flujos, integraciones  

❌ Refactor interno (solo lógica, sin cambio de comportamiento)  
❌ Unit test falla (arregla primero)  
❌ No tienes servidor dev  

### Datos de prueba

Usa datos que ya existen en dev:

- Si hay `datos-prueba/`, úsalos
- Si necesita crear data, la crea en la prueba y la limpia después
- Números/emails reales dentro de lo posible (ej: `test@example.local`)

### Si la prueba falla

El skill es **honesto** — si no funciona, lo reporta exacto:

```
❌ FALLA
Esperado (spec): "Modal muestra 'Factura duplicada'"
Visto: No hay modal, solo mensaje en consola

Severidad: Importante (usuario confundido)
Causa probable: Validador no retorna 409, devuelve 200 silenciosamente
Propuesta: En views.py línea 142, retornar JsonResponse(..., status=409)
```

Así sabes exactamente qué arreglar.

### Después de arreglar

```bash
# 1. Arreglas el bug
git commit -m "Fix: validación de conexión en offline"

# 2. Revalidas con verify-after-changes
/verify-after-changes

# 3. Solo casos que fallaban se revisan rápido
# Los que pasaban se asumon que siguen pasando

# 4. Si TODO verde → PR → merge
```

---

## Notas finales

- **Los skills son herramientas, no dogma** — si una funcionalidad es trivial, no los uses.
- **Son iterativos** — puedes volver a `/brainstorming` si la realidad cambia.
- **El documento (spec) es vivo** — si durante el código descubres algo, actualiza el spec y el PR lo referencia.
- **Cualquiera lee el spec y entiende** — es la métrica de si está bien.

---

## Ejemplo mínimo (5 minutos)

Usuario: "Quiero campo de notas en facturas de compra"

### Brainstorming (2 min)
- ¿Visible para quién? Auxiliar y contador.
- ¿Editable después de aprobada? Sí (contador agrega notas).
- ¿Validación? Solo longitud máxima (1000 caracteres).

Skill: "Opción única: agregar campo en modelo, formulario, vistas. Hazlo."

### Design-Spec (3 min)
Especificación corta:

```markdown
# Notas en Facturas de Compra
Auxiliar y contador pueden agregar notas (1000 caracteres max) a una factura, visible en detalle. Siempre editable.

## Usuario
Contador que revisa facturas y quiere dejar anotaciones para auditoría.

## Contexto
Hoy usan comentarios en email; queremos trazabilidad en la app.

## Alcance
- Campo texto en FacturaCompra
- Editable siempre (aprobada o no)
- Visible en vista de detalle
- Sin validaciones complejas

## Comportamiento
1. Usuario abre factura
2. Ve campo "Notas" (área de texto, 1000 caracteres max, contador a la derecha)
3. Escribe nota
4. Guarda factura
5. Nota persiste

## Errores
- Usuario escribe > 1000 caracteres → Backend rechaza con "Máximo 1000 caracteres"
- Conexión falla al guardar → Modal "Error al guardar" con reintento
```

### Desarrollo (≤1 hora)

```python
# models.py
class FacturaCompra(models.Model):
    # ... campos existentes ...
    notas = models.TextField(blank=True, max_length=1000)

# tests
def test_nota_se_guarda_en_factura(self):
    factura = crear_factura_compra()
    factura.notas = "Revisar con contador"
    factura.save()
    self.assertEqual(FacturaCompra.objects.get(id=factura.id).notas, "Revisar con contador")

def test_rechaza_nota_> 1000_caracteres(self):
    factura = crear_factura_compra()
    factura.notas = "x" * 1001
    with self.assertRaises(ValidationError):
        factura.full_clean()
```

**Listo.**

---

Usa los skills para evitar ambigüedades. La claridad al inicio ahorra horas de desarrollo.
