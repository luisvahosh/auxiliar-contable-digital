# Ejemplos de Verify-After-Changes

Estos son ejemplos reales de cómo se vería el skill en acción en el proyecto.

---

## Ejemplo 1: Validación de CUFE Duplicado (Happy Path)

### Contexto
- **Spec:** `docs/specs/2026-07-15-validar-cufe-duplicado.md`
- **Implementación:** Listo (modelo + signals + tests)
- **Estado:** Todos los unit tests pasan

### Usuario invoca:
```
/verify-after-changes
```

### El skill hace:

#### Paso 1: Lee spec

Encuentra `docs/specs/2026-07-15-validar-cufe-duplicado.md` y extrae:
- Happy path: Factura nueva → se acepta
- Error 1: CUFE duplicado → rechaza con modal
- Error 2: NIT+número+fecha duplicado → rechaza
- Error 3: Offline → no valida
- Error 4: Admin crea duplicado → BD rechaza

#### Paso 2: Diseña 5 casos

```
CASO 1: Happy path — Factura nueva de proveedor
  → Usuario sube XML de factura nueva
  → Sistema valida CUFE no existe
  → Continúa flujo normal (clasificación, etc.)

CASO 2: Error principal — CUFE duplicado exacto
  → Usuario intenta subir misma factura (mismo CUFE)
  → Sistema detecta duplicado
  → Modal muestra datos de original

CASO 3: Validación fuzzy — NIT+número+fecha duplicado
  → Usuario intenta subir factura con mismo NIT, número, fecha (pero CUFE diferente)
  → Sistema detecta por combinación
  → Modal rechaza

CASO 4: Offline — Conexión cae durante validación
  → Usuario está offline, app almacena draft
  → Usuario se conecta
  → Al guardar, valida contra BD
  → Detecta duplicado si existe

CASO 5: Admin — Edición directa crea duplicado
  → Admin en Django admin edita FacturaCompra
  → Intenta crear CUFE duplicado
  → Modelo rechaza por unique_together
```

#### Paso 3: Levanta servidor

```bash
$ python manage.py runserver
Starting development server at http://127.0.0.1:8000/
```

Abre navegador en http://127.0.0.1:8000/

#### Paso 4: Prueba cada caso

---

### **CASO 1: Happy path**

**Descripción:** Usuario sube factura nueva (nunca vista antes)

**Pasos:**
1. Navegador abre http://localhost:8000/causacion/
2. Click en "Subir factura de compra"
3. Selecciona XML de `datos-prueba/P1-factura-compra-nueva.xml`
4. Click en "Procesar"

**Esperado (spec):**
```
"Sistema procesa: extrae NIT proveedor, número de factura, CUFE, fecha
Sistema valida: ¿existe factura con este CUFE?
Resultado: NO existe
→ Continúa flujo normal (clasificación, retencion, etc.)"
```

**Visto en navegador:**
- ✅ XML se procesa sin error
- ✅ Modal de "Clasificar factura" aparece
- ✅ Formulario muestra datos extraídos correctamente
- ✅ Campo "Cuenta" con opciones desplegables
- ✅ Botón "Guardar" disponible

**Resultado:** ✅ **PASA** — Exacto a spec

---

### **CASO 2: CUFE duplicado exacto**

**Descripción:** Usuario sube misma factura (mismo CUFE)

**Pasos:**
1. Abre http://localhost:8000/causacion/
2. Click en "Subir factura de compra"
3. Selecciona `datos-prueba/P1-factura-compra-nueva.xml` DE NUEVO
4. Click en "Procesar"

**Esperado (spec):**
```
"Sistema detecta CUFE duplicado
Sistema detiene el proceso
Muestra modal: '⚠️ Factura Duplicada'
Tabla con datos de factura original:
  - Proveedor: [nombre]
  - Número: [número]
  - Fecha: [fecha]
  - Registrada por: [usuario]
  - Fecha de registro: [cuándo]
Botones: 'Entendido' | 'Ver factura original'"
```

**Visto en navegador:**
- ✅ Modal aparece con encabezado "⚠️ Factura Duplicada"
- ✅ Tabla muestra:
  ```
  Proveedor: ACME S.A.S.
  Número: 1001
  Fecha: 2026-07-10
  Monto: $500.000
  Registrada por: luisvahosh
  Fecha de registro: 2026-07-15 14:30
  Estado: Pendiente
  ```
- ✅ Botones presentes: "Entendido" (azul, grande) | "Ver original" (gris)
- ✅ Click "Entendido" cierra modal
- ✅ Vuelve a lista sin guardar nada

**Resultado:** ✅ **PASA** — Exacto a spec

---

### **CASO 3: NIT+número+fecha duplicado (fuzzy)**

**Descripción:** Usuario sube factura con mismo proveedor, número y fecha (pero foto diferente, OCR levemente distinto)

**Pasos:**
1. Abre http://localhost:8000/causacion/
2. Click en "Subir factura de compra"
3. Selecciona foto: `datos-prueba/P1.10-factura-fisica-duplicada.png`
4. Sistema hace OCR, extrae NIT=800123456-9, número=1001, fecha=2026-07-10
5. Click en "Procesar"

**Esperado (spec):**
```
"Si CUFE no existe pero NIT+número+fecha es duplicado
Sistema valida con confianza < 0.85 en algún campo
Muestra: '¿Esta factura ya fue registrada? [Sí, es duplicada] [No, es nueva]'
Si usuario dice Sí → rechaza como duplicada
Si usuario dice No → continúa flujo normal"
```

**Visto en navegador:**
- ✅ OCR procesa foto
- ⚠️ Confianza en número: 0.92 (alta, pero menos de OCR perfecto)
- ⚠️ Modal pregunta: "¿Esta factura ya fue registrada? (Número OCR: #1001)"
- ⚠️ Usuario click "Sí, es duplicada"
- ✅ Modal de duplicado aparece (igual a CASO 2)

**Resultado:** ⚠️ **PASA CON NOTA MENOR**

**Nota:** Esperaba que preguntara solo si confianza < 0.85, pero pregunta siempre. No es error, es "más seguro". Spec dice "NO usamos NIT+número+fecha para comparar si OCR retorna confianza < 0.85", pero código pregunta siempre. Es mitigación defensiva.

**Propuesta:** OK así, es válido (más seguro no daña).

---

### **CASO 4: Offline → duplicado no detectado**

**Descripción:** Usuario intenta subir mientras está offline

**Pasos:**
1. Abre DevTools → Network → Offline
2. Click en "Subir factura de compra"
3. Selecciona XML
4. Click en "Procesar"

**Esperado (spec):**
```
"Si no hay conexión, app debe rechazar:
'Necesita conexión para subir facturas. Espere o reintente más tarde.'
NO permite guardar offline borrador de factura"
```

**Visto en navegador:**
- ❌ Botón "Subir factura" sigue habilitado (no gris)
- ❌ Usuario hace click
- ❌ Archivo se procesa localmente (OCR funciona offline)
- ❌ Modal de clasificación aparece (esperado, es offline)
- ❌ Usuario guarda
- ⚠️ App dice "Guardando..." pero con conexión offline, el save no se puede hacer en BD
- ❌ No hay error explícito, solo queda en estado "raro"

**Resultado:** ❌ **FALLA**

**Diferencia crítica:**
- Spec: Rechaza before processing si offline
- Visto: Permite procesamiento local, falla silenciosa al guardar

**Severidad:** Importante (usuario confundido si conexión falla)

**Propuesta de arreglo:**
- En `causacion/templates/subir_factura.html`, agregar:
  ```javascript
  <script>
    if (!navigator.onLine) {
      document.querySelector('button[name="upload"]').disabled = true;
      document.querySelector('span.offline-warning').textContent = 
        'Necesita conexión para subir facturas';
    }
  </script>
  ```
- O más robusto: En `causacion/views.py`, hacer primero un ping a BD antes de procesar

---

### **CASO 5: Admin en Django admin crea duplicado**

**Descripción:** Admin accede a Django admin, edita FacturaCompra, intenta crear CUFE duplicado

**Pasos:**
1. Abre http://localhost:8000/admin/
2. Login como admin
3. Navega a Facturas de compra
4. Click en factura existente (la del CASO 1)
5. Cambia CUFE a uno que ya existe (CASO 2)
6. Click "Guardar"

**Esperado (spec):**
```
"Modelo tiene unique_together en (empresa, cufe)
BD rechaza el save con error: 
'CUFE [...] ya existe para esta empresa. ID: [link]'"
```

**Visto en navegador:**
- ✅ Django admin muestra error:
  ```
  Error: Factura con este CUFE ya existe en la empresa.
  Original: ID 123 (link a factura)
  ```
- ✅ Save es rechazado
- ✅ Se mantiene en formulario sin cambios

**Resultado:** ✅ **PASA** — Exacto a spec

---

## Resumen de Reporte

```markdown
# Verificación Post-Implementación
📅 Fecha: 2026-07-15 15:45
📋 Spec: docs/specs/2026-07-15-validar-cufe-duplicado.md
🔧 Rama: feat/validar-cufe-duplicado

## Resumen Ejecutivo
- **Casos totales:** 5
- **Pasados:** 4
- **Con notas:** 1 (cosmético)
- **Fallidos:** 1 (importante)
- **Tasa de paso:** 80% ✅

---

## Detalle de Casos

| # | Nombre | Resultado | Severidad | Acción |
|---|--------|-----------|-----------|--------|
| 1 | Happy path — factura nueva | ✅ PASA | — | Ninguna |
| 2 | CUFE duplicado exacto | ✅ PASA | — | Ninguna |
| 3 | NIT+fecha duplicado (fuzzy) | ⚠️ NOTA | Cosmético | Revisar |
| 4 | Offline → no detecta | ❌ FALLA | Importante | Arreglar |
| 5 | Admin crea duplicado | ✅ PASA | — | Ninguna |

---

## Detalles

### CASO 3: NIT+fecha duplicado (fuzzy)
**Nota cosmética**

- Esperado: Solo pregunta si confianza OCR < 0.85
- Visto: Pregunta siempre (incluso con confianza alta)
- Análisis: Es una mitigación defensiva (más seguro), válido
- Acción: Aceptar como está (no daña UX)

### CASO 4: Offline
**Falla importante**

- Esperado (spec): "Rechaza antes de procesar si offline"
- Visto: Permite procesar, falla silenciosa al guardar
- Impacto: Usuario confundido, no entiende qué pasó
- Archivo: `causacion/views.py` línea 142 (procesar_xml)
- Propuesta:
  ```python
  # En views.py
  def subir_factura(request):
      # Primero: validar conexión
      if not request.user.empresa.conexion_contable.is_connected():
          return JsonResponse({'error': 'Sin conexión a BD. Reintente.'}, 
                            status=503)
      # Luego: procesar
      ...
  ```
- Alternativa más simple: Validar conexión en template (JavaScript)

---

## Recomendación

⚠️ **Necesita arreglo antes de mergear:**

1. **CASO 4 (Offline):** Implementar validación de conexión
   - Opción A: Backend (robusto)
   - Opción B: Frontend (rápido)
   - Recomiendo: Opción A + error visual

2. **CASO 3 (Fuzzy):** Aceptar como está (defensiva)

**Próximos pasos:**
```
1. Arregla CASO 4 en causacion/views.py
2. Vuelve a /verify-after-changes
3. Si todo verde → PR → merge
```

---

**Generado por /verify-after-changes**
**Servidor: http://localhost:8000/**
```

---

## Ejemplo 2: Notificación de Rechazo DIAN (Con Falla)

**Contexto:**
- **Spec:** `docs/specs/2026-07-14-notificacion-rechazo-dian.md`
- **Implementación:** Listo, pero código tiene bug
- **Resultado:** 3/5 pasan

### El skill hace:

**CASO 1: Happy path — DIAN rechaza, usuario se entera**
✅ PASA

**CASO 2: Email opt-in — Notificación por correo**
❌ FALLA
- Esperado: Correo llega a admin en < 1 min
- Visto: Ningún correo recibido después de 5 minutos
- Causa probable: Comando `alertar_rechazos_dian` no está en cron
- Propuesta: Verificar `.env` CRON_SCHEDULE_DIAN_ALERTS o agregar a crontab

**CASO 3: Modal con código — Usuario ve código de rechazo**
✅ PASA

**CASO 4: Reintento — Usuario re-emite desde la app**
❌ FALLA
- Esperado: Botón "Re-emitir en Alegra" abre Alegra
- Visto: Botón existe pero no es clickeable (display: none)
- Causa: CSS visibility issue
- Propuesta: `causacion/templates/rechazo_dian.html` línea 45: cambiar `display: none` a visible

**CASO 5: State — BD actualiza dian_estado correctamente**
✅ PASA

### Reporte
```
3/5 pasan
CASO 2: Email no se envía (cron no corre)
CASO 4: Botón oculto (CSS)
Propuesta: 
- Revisar cron en servidor / agregar comando a tasks
- Revisar CSS en template
```

---

## Patrón: Después de arreglar

Usuario arregla los dos bugs (CASO 2 y 4).

Invoca de nuevo:
```
/verify-after-changes
```

El skill:
- Revuelve con especial atención a CASOS 2 y 4 (los que fallaron)
- Asume que CASOS 1, 3, 5 siguen pasando (si nada tocó)
- Reporte rápido: "Los 2 casos que fallaban, ahora pasan. Todo verde."

---

## Tips para buenos test cases

Elige los 5 casos que cubran:

1. **Feliz** — Usuario hace todo bien, resultado esperado
2. **Error crítico** — Error que rompe todo o confunde mucho
3. **Validación** — Datos inválidos, límites
4. **Integración** — Algo que toca otro sistema
5. **Edge raro pero posible** — Algo de la spec que es caso extremo

No hagas:
- ❌ 5 happy paths (redundante)
- ❌ Casos paranoia (XXE, SQL injection, etc. — eso es code-review)
- ❌ Casos tan específicos que ocurren 1x al año

Haz:
- ✅ Casos que el usuario realmente ejecuta
- ✅ Casos de error que están en el spec
- ✅ Integraciones que toquen APIs
- ✅ Validaciones que rechacen entrada mala
