# Skill Verify-After-Changes — Validación Post-Implementación

Este skill **prueba de verdad en navegador** que una funcionalidad funciona como especifica el documento de requisitos (`design-spec`).

## Por qué existe

**Tests pasan ≠ funciona de verdad**

- Unit tests validan lógica
- Tests de integración validan BD
- Pero nadie prueba lo que el usuario ve/hace

Este skill cierra ese gap: levanta servidor, prueba en navegador, compara exacto contra spec.

## Cuándo usar

✅ Después de implementar, antes de PR  
✅ Cambios en UI o flujos de usuario  
✅ Integraciones que tocan sistemas externos (Alegra, DIAN, etc.)  
✅ "¿De verdad funciona como especificamos?"  

❌ Refactor interno (sin cambio de UI)  
❌ Unit test falla (arregla primero)  
❌ No tienes servidor dev  

## Qué hace

1. **Lee tu spec** (`docs/specs/YYYY-MM-DD-*.md`)
2. **Elige 5 casos de prueba críticos** de ese spec
3. **Levanta servidor dev**
4. **Prueba cada caso en navegador:**
   - Click aquí
   - Ingresa datos
   - Verifica resultado
   - ¿Matchea spec? → ✅ / ❌ / ⚠️
5. **Genera reporte:**
   - Qué pasó
   - Qué esperaba la spec
   - Si falla, qué arreglar
6. **Recomienda:** luz verde o "arregla esto"

## Ejemplo rápido

**Escenario:** Implementaste "validación de CUFE duplicado"

```bash
/verify-after-changes
```

El skill:

1. Lee `docs/specs/2026-07-15-validar-cufe-duplicado.md`
2. Elige 5 casos:
   - Caso 1: Factura nueva (happy path)
   - Caso 2: CUFE duplicado (error principal)
   - Caso 3: NIT+número+fecha duplicado (fuzzy)
   - Caso 4: Intenta offline (edge case)
   - Caso 5: Admin crea duplicado directo (seguridad)
3. Levanta `python manage.py runserver`
4. Abre navegador, prueba cada caso:
   - **Caso 1:** Sube factura nueva → ✅ Continúa flujo normal
   - **Caso 2:** Sube CUFE igual → ✅ Modal muestra original
   - **Caso 3:** NIT+número+fecha igual → ✅ Detecta y rechaza
   - **Caso 4:** Desconecta internet → ⚠️ Permite guardar offline (spec dice que no debería)
   - **Caso 5:** Admin edita, crea duplicado → ✅ BD rechaza con error
5. Genera reporte:
   ```
   4/5 pasan
   CASO 4 falla: necesita validar conexión
   Propuesta: agregar if not internet en línea X de archivo Y
   ```
6. Recomienda: "Arregla CASO 4, luego vuelve a /verify-after-changes"

## Output que ves

Una **tabla clara:**

```
CASO                           RESULTADO    SEVERIDAD   ACCIÓN
────────────────────────────────────────────────────────────────
1. Happy path                  ✅ PASA      —           Ninguna
2. CUFE duplicado              ✅ PASA      —           Ninguna
3. NIT+fecha duplicado         ✅ PASA      —           Ninguna
4. Offline → duplicado no detecta  ❌ FALLA  Importante  Arreglar
5. Admin crea directo          ✅ PASA      —           Ninguna

Resultado: 4/5 (80%)
Recomendación: Arregla CASO 4, reintenta
```

Si hay fallos, detalla:
- **Qué esperaba spec**
- **Qué viste**
- **Dónde probable esté el bug** (archivo, función)
- **Cómo arreglarlo**

## Cómo funciona internamente

### 1. Identifica el spec

```bash
# Busca docs/specs/ y encuentra el más reciente
# O pregunta al usuario si hay varios

docs/specs/
├── 2026-07-15-validar-cufe-duplicado.md  ← Usa este
├── 2026-07-10-alertas-tributarias.md
└── 2026-07-08-nómina-exportar-pila.md
```

### 2. Extrae requisitos del spec

Lee las 6 secciones de `design-spec`:

- **Overview** → qué es, criterios de éxito
- **Usuario objetivo** → quién lo usa
- **Comportamiento esperado** → qué debe pasar
- **Posibles errores** → qué puede fallar, cómo se maneja

### 3. Diseña 5 casos

No random — cada uno viene de algo en el spec:

```
CASO 1 (Happy path):
  Viene de → Comportamiento esperado: "Usuario sube factura nueva"
  Test → Usuario ingresa datos válidos, sistema acepta

CASO 2 (Error principal):
  Viene de → Posibles errores: "Factura duplicada por CUFE"
  Test → Usuario intenta subir CUFE que existe

CASO 3 (Validación):
  Viene de → Posibles errores: "NIT inválido"
  Test → Usuario ingresa NIT con caracteres inválidos

CASO 4 (Integración):
  Viene de → Comportamiento: "Sistema valida conexión"
  Test → Usuario intenta offline

CASO 5 (Edge case):
  Viene de → Posibles errores: "Admin crea duplicado directo"
  Test → Admin en Django admin edita FacturaCompra
```

### 4. Levanta servidor

Lee `.claude/launch.json`:

```json
{
  "version": "0.0.1",
  "configurations": [
    {
      "name": "Django",
      "runtimeExecutable": "python",
      "runtimeArgs": ["manage.py", "runserver"],
      "port": 8000
    }
  ]
}
```

Levanta `python manage.py runserver`, espera a que esté listo, abre http://localhost:8000.

### 5. Prueba en navegador

Para cada caso:
- Navega a la página correcta
- Rellena formularios
- Hace clicks
- Captura pantallas
- Verifica resultado

Compare exacto contra spec:
- ¿El texto es exacto?
- ¿Los números se calculan correctamente?
- ¿La integración funcionó?
- ¿El estado de BD cambió como esperaba?

### 6. Genera reporte

```markdown
CASO X: [nombre]
- Esperado (spec): [literal del spec]
- Visto: [lo que pasó en navegador]
- ✅ / ❌ / ⚠️
- [Si falla] Propuesta de arreglo: [qué cambiar]
```

### 7. Recomienda

- Si 5/5 ✅ → "Luz verde, listo para PR"
- Si 3-4 pasan → "Arregla estos, reintenta"
- Si ≤2 pasan → "Mucho trabajo aún, necesita más"

## Flujo después

```
/verify-after-changes
    ↓
Reporte con fallos
    ↓
Arreglas el código
    ↓
/verify-after-changes de nuevo
    ↓
Todo verde
    ↓
git push → PR → merge
```

## Datos de prueba

El skill usa datos que ya existen en tu dev:

- Si tienes `datos-prueba/`, los usa
- Si necesita crear data (ej: usuario de test), la crea en la prueba
- No deja residuos (borra lo que creó después)

Ejemplo: Para probar "factura duplicada", crea una factura en la BD, luego intenta crear otra igual.

## Si falla

El skill NO dice "no funciona" — dice exacto qué está mal:

```
❌ FALLA
- Esperado: Modal muestra "Factura duplicada"
- Visto: No hay modal, solo redirecciona a lista
- Archivo probable: causacion/views.py línea 142
- Propuesta: Validar duplicado antes de render, no después de save
```

Así sabes exactamente qué arreglar.

## No prueba

- Performance (si carga lento, eso es otro tema)
- Seguridad avanzada (eso es code-review)
- Casos imposibles de que ocurran en la realidad

Confía en unit tests para eso.

## Integración con otros skills

```
1. /brainstorming → Ideación
2. /design-spec → Especificación
3. Implementar → Código
4. /verify-after-changes ← Aquí
5. PR + merge
```

El skill asume que existen spec y plan. Si no, te pide que crees primero.

---

## Cuándo regresar a /verify-after-changes

Después de arreglar un caso que falló:

```bash
# Arreglas el bug
git commit -m "Fix: validar conexión antes de guardar offline"

# Revalidas
/verify-after-changes

# Solo el caso que fallaba se revalida rápido
# Los que ya pasaron se asumen que siguen pasando
```

## Checklists antes de invocar

- [ ] ¿Termino la implementación? (código + tests)
- [ ] ¿Todos los unit tests pasan?
- [ ] ¿Existe spec en docs/specs/? (si no, usa `/design-spec` primero)
- [ ] ¿Servidor dev se puede levantar? (verifica `.claude/launch.json`)

Si sí a todas → adelante con `/verify-after-changes`.

---

Úsalo como **puerta de salida** antes de PR: garantiza que de verdad funciona, no solo que pasa tests.
