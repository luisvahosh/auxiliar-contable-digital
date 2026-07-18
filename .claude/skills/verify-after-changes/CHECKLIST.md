# Checklist de Verificación

Use esta lista mientras prueba cada caso. Cópiela para cada ejecución.

---

## Antes de Empezar

- [ ] ¿Spec existe en `docs/specs/`?
- [ ] ¿Todos los unit tests pasan? (`pytest` o `python manage.py test`)
- [ ] ¿Servidor dev se levanta sin errores?
- [ ] ¿Tienes datos de prueba listos?
- [ ] ¿Navegador está en http://localhost:8000?

## Para Cada Caso de Prueba

### CASO #: [NOMBRE]

**Descripción de lo que vamos a probar:**
```
[Frase concisa: qué usuario hace, qué debería pasar]
```

### Ejecución

- [ ] Paso 1: [acción]
  - [ ] Capturé screenshot? (si aplica)
  - [ ] ¿Qué veo? [describe]
  
- [ ] Paso 2: [acción]
  - [ ] Capturé screenshot? (si aplica)
  - [ ] ¿Qué veo? [describe]

- [ ] Paso 3: [acción]
  - [ ] Capturé screenshot? (si aplica)
  - [ ] ¿Qué veo? [describe]

### Comparación con Spec

**Spec dice:**
```
[Copia literal de la sección "Comportamiento Esperado" o "Posibles Errores"]
```

**Yo vi:**
```
[Describe exacto qué pasó en navegador]
```

**¿Matchean?**
- [ ] ✅ SÍ — Exacto a spec
- [ ] ⚠️ CASI — Funciona pero hay diferencia menor
- [ ] ❌ NO — Diferencia importante o no funciona

### Si ⚠️ o ❌:

**Diferencia:**
```
Esperado: [qué debería ser]
Visto: [qué es]
```

**Severidad:**
- [ ] 🔴 Bloqueante (rompe funcionalidad)
- [ ] 🟠 Importante (confunde al usuario)
- [ ] 🟡 Cosmético (texto, orden, UI menor)

**Probable causa:**
```
[Dónde en el código crees que está el problema]
```

**Propuesta de arreglo:**
```
[Qué cambiar, dónde, cómo]
```

**Archivo/línea a revisar:**
```
app/modulo/archivo.py línea XXX
```

---

## Después de Todos los Casos

### Conteo Final

- [ ] Casos totales: ___ / 5
- [ ] Pasados (✅): ___
- [ ] Con nota (⚠️): ___
- [ ] Fallidos (❌): ___

### Lista de Arreglos Necesarios

```
[ ] CASO X: [nombre] — [qué arreglar]
[ ] CASO Y: [nombre] — [qué arreglar]
```

### Recomendación

- [ ] ✅ **Luz verde** — Todo pasa, listo para PR
- [ ] 🟡 **Arreglar antes** — Hay fallos, necesita fixes
- [ ] 🔴 **Mucho trabajo** — Demasiados fallos, no listo

### Si hay arreglos:

```bash
# 1. Anota en los casos qué arreglar
# 2. Arregla el código
# 3. Vuelve a /verify-after-changes
# 4. Revalida solo los casos que fallaron
```

---

## Template para Copiar

Usa este template para cada ejecución de `/verify-after-changes`:

```markdown
# Verificación: [NOMBRE DE FUNCIONALIDAD]
📅 Fecha: YYYY-MM-DD HH:MM
📋 Spec: docs/specs/YYYY-MM-DD-*.md

## CASO 1: [NOMBRE]
**Descripción:** [Qué pruebo]

**Pasos:**
1. [Acción]
   - Veo: [resultado]
2. [Acción]
   - Veo: [resultado]

**Spec dice:** 
[Cita literal]

**Yo vi:**
[Describe]

**Resultado:** ✅ / ⚠️ / ❌
**Severidad:** — / 🟡 / 🟠 / 🔴
**Propuesta:** [Si falla]

---

## CASO 2: ...

---

## Resumen
- Totales: 5
- Pasados: __
- Notas: __
- Fallidos: __

## Recomendación
✅ / 🟡 / 🔴 [Elige]

[Si hay arreglos:]
```
Arreglar:
- CASO X: ...
- CASO Y: ...
```
Luego `/verify-after-changes` de nuevo
```
```

---

## Tips Mientras Pruebas

### Captura de Pantallas

Toma screenshot cuando:
- [ ] Estado inicial (lista, formulario, etc.)
- [ ] Después de llenar datos
- [ ] Resultado final (éxito o error)
- [ ] Si hay modal o popup importante
- [ ] Si hay integración (correo, API, etc.)

### Datos de Prueba

Úsalos consistentemente:
- NIT empresa: `800000000-1` (TEST)
- Email: `test@example.local`
- Teléfono: `123-456-7890`
- Direcciones: "Cra 1 # 1-01, Bogotá"

Así si ves los datos en la salida, sabes que es de tu test, no residuo.

### Errores en Consola

Abre DevTools (F12) → Console:

```javascript
// Si ves errores, documenta:
// - Mensaje exacto
// - Línea de archivo
// - Stack trace
```

Proporciona eso en "Probable causa".

### Integraciones Externas

Si toca Alegra, DIAN, IMAP, etc.:

- [ ] Verifica que está **mocked** en dev (no llama API real)
- [ ] Captura el request que se hace (DevTools → Network)
- [ ] Verifica que el formato es correcto
- [ ] Verifica que maneja respuesta mock correctamente

### Performance

No evalúes speed en detail, pero nota si:
- [ ] Página carga en < 3s
- [ ] Click responde al instante
- [ ] Form valida en tiempo real

Si es lento, anota pero no lo bloquea a menos que spec lo pida.

---

## Red Flags — Si Ves Esto, Investiga

🚩 **Datos no se guardan en BD**
- Verifica: ¿Hay error silencioso?
- DevTools → Network → POST requests
- Verifica response status (200 ok, 400 error, 500 server)

🚩 **Modal/error no aparece**
- Verifica: ¿Está en el HTML pero hidden (display: none)?
- DevTools → Elements → busca el elemento
- Verifica CSS: display, visibility, z-index

🚩 **Integración no funciona**
- Verifica: ¿Mock está configurado?
- ¿Request se hace al URL correcto?
- ¿Response es válido JSON/XML?

🚩 **Usuario confusion**
- Si un mensaje es poco claro, anota en severidad cosmético
- Propuesta: "Cambiar texto a: '...' más explícito"

---

## Después de Cada Caso

Antes de pasar al siguiente:

- [ ] ¿Limpié datos que creé? (si se supone que no debe dejar residuos)
- [ ] ¿Logout y login de nuevo si es necesario?
- [ ] ¿Refreshear la página?
- [ ] ¿Volver a estado inicial?

Esto evita que un caso afecte al siguiente.

---

## Cuando Terminas Todo

```bash
# 1. Recompila resumen
# 2. Cuenta: ✅ / ⚠️ / ❌
# 3. Genera propuestas de arreglo
# 4. Dice: Luz verde o "Arregla estos casos"
# 5. Si hay arreglos, comando siguiente es arreglando código
# 6. Vuelve a /verify-after-changes
```

---

Usa este checklist para ser **sistemático y no olvidar nada** durante las pruebas.
