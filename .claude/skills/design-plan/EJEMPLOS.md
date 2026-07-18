# Ejemplos de Design-Plan

Ejemplo real de cómo se vería un plan generado por el skill.

---

## Ejemplo: Plan de Validación de CUFE Duplicado

**Contexto:**
- Spec aprobado: `docs/specs/2026-07-15-validar-cufe-duplicado.md`
- Usuario invoca: `/design-plan`
- El skill genera este plan

---

```markdown
# Plan de Implementación: Validación de CUFE Duplicado en Compras
📅 Fecha: 2026-07-15
📋 Especificación de Referencia: docs/specs/2026-07-15-validar-cufe-duplicado.md

## 1. Objetivo

Cuando el auxiliar sube una factura de compra (XML, foto o manual), el sistema valida que el CUFE (Código Único de Factura Electrónica) no exista ya en la base de datos. Si existe, rechaza la factura mostrando datos de la factura original.

Esto evita asientos duplicados que rompen cuadre y generan reparación manual.

**Éxito se mide por:**
- Cero facturas de compra duplicadas aprobadas en 30 días
- Auxiliar entiende por qué fue rechazada en < 1 segundo

---

## 2. Contexto del Problema

**Situación actual:**  
Auxiliar sube factura de compra vía XML o foto → sistema NUNCA rechaza por duplicado → genera asiento duplicado → contador lo detecta en cuadre de mes → corrige manualmente → pérdida de 1-2 horas.

**Dolor:**
- Tedioso: corregir duplicados es trabajo sin valor
- Arriesgado: si contador no detecta, reportes financieros están mal
- Humillante: auxiliar se siente culpable

**Dato importante:**
CUFE es un SHA-1 que garantiza unicidad. Mismo proveedor + número + fecha = mismo CUFE. Si no hay CUFE (factura física), NIT+número+fecha es "casi seguro duplicado".

---

## 3. Especificación de Referencia

**Documento:** docs/specs/2026-07-15-validar-cufe-duplicado.md

**Usuario objetivo:** Auxiliar de contabilidad que procesa 10-20 facturas diarias en celular.

**Comportamiento esperado:**
- Usuario sube XML/foto
- Si CUFE/NIT+número+fecha es nuevo → continúa flujo normal
- Si es duplicado → muestra modal con datos de original, rechaza

**Posibles errores:**
- Error 1: OCR malo (fuzzy matching)
- Error 2: Offline (no valida)
- Error 3: Admin en Django admin crea duplicado

Ver spec para detalles completos.

---

## 4. Lista de Tareas

### T1: Preparación — Estudio de Código Existente
**Esfuerzo:** Pequeño (1-2h)  
**Dependencias:** Ninguna  
**Riesgo:** Bajo  

**Archivos a leer:**
- `app/causacion/models.py` (líneas 50-120: FacturaCompra, FacturaVenta)
- `app/causacion/signals.py` (cómo se usan signals para validar)
- `app/causacion/tests/test_causacion.py` (estructura de tests)

**Pasos:**
1. Lee modelo FacturaCompra: qué campos tiene, relaciones
2. Entiende cómo se crean facturas (subir XML vs foto)
3. Abre `python manage.py shell` y verifica:
   ```python
   from app.causacion.models import FacturaCompra
   f = FacturaCompra.objects.first()
   print(f.cufe, f.nit_proveedor, f.numero, f.fecha)
   ```
4. Lee al menos 2 signals existentes en signals.py (ej: validar_retefuente)

**Criterio de éxito:**
- Entiendes estructura de FacturaCompra
- Sabes cómo se crean (XML → OCR → validar)
- Entiende concepto de signals

---

### T2: Modelo — Agregar Campo CUFE y Constraint Único
**Esfuerzo:** Pequeño (1.5h)  
**Dependencias:** Después de T1  
**Riesgo:** Bajo  

**Archivos afectados:**
- `app/causacion/models.py`
- `app/causacion/migrations/` (nueva migración)

**Pasos:**
1. En `FacturaCompra` model, agrega campo:
   ```python
   cufe = models.CharField(max_length=256, blank=True, null=True, help_text="Código único DIAN")
   ```

2. Agrega constraint único por empresa:
   ```python
   class Meta:
       constraints = [
           UniqueConstraint(
               fields=['empresa', 'cufe'],
               condition=Q(cufe__isnull=False),
               name='unique_cufe_per_empresa'
           ),
       ]
   ```

3. Crea migración:
   ```bash
   python manage.py makemigrations causacion
   ```

4. Verifica que migración se ve bien:
   ```bash
   cat app/causacion/migrations/000X_xxx.py
   ```

**Criterio de éxito:**
- Campo `cufe` se agregó
- Constraint único existe en Meta
- Migración se genera sin errores
- `python manage.py migrate` funciona

---

### T3: Extracción — Extraer CUFE desde XML y OCR
**Esfuerzo:** Pequeño (1.5h)  
**Dependencias:** Después de T1 (leyó código)  
**Riesgo:** Bajo  

**Archivos afectados:**
- `app/causacion/parsers.py` (nuevo o existente)

**Pasos:**
1. Crea función `extraer_cufe_from_xml(xml_string)`:
   ```python
   # Busca UUID en namespace UBL
   # Retorna CUFE o None
   ```

2. Crea función `extraer_cufe_from_ocr(ocr_data)`:
   ```python
   # OCR retorna dict con numero, nit, fecha
   # Retorna (nit, numero, fecha) para matching fuzzy
   ```

3. Crea función `extraer_cufe_from_manual(form_data)`:
   ```python
   # User ingresa NIT, numero, fecha manualmente
   # Retorna tuple (nit, numero, fecha)
   ```

**Criterio de éxito:**
- 3 funciones creadas
- Tests unitarios pasan (2-3 tests por función)
- Manejan XML válido + inválido

---

### T4: Validación — Signal para Detectar Duplicado
**Esfuerzo:** Medio (3-4h)  
**Dependencias:** Después de T2, T3  
**Riesgo:** Medio  

**Archivos afectados:**
- `app/causacion/signals.py`
- `app/causacion/models.py` (agregar método helper)

**Pasos:**
1. En FacturaCompra, agrega método:
   ```python
   def validar_no_duplicado(self):
       """Levanta ValidationError si CUFE duplicado"""
       if self.cufe:
           existente = FacturaCompra.objects.filter(
               empresa=self.empresa, 
               cufe=self.cufe
           ).exclude(id=self.id).first()
           if existente:
               raise ValidationError(
                   f"CUFE duplicado: factura original ID {existente.id}"
               )
   ```

2. Crea pre_save signal:
   ```python
   @receiver(models.signals.pre_save, sender=FacturaCompra)
   def validar_cufe_pre_save(sender, instance, **kwargs):
       instance.validar_no_duplicado()
   ```

3. Registra signal en `app.ready()`

**Criterio de éxito:**
- Signal se dispara en pre_save
- ValidationError se levanta si duplicado
- Tests de signal pasan

---

### T5: Vistas — Catch ValidationError y Retornar 409
**Esfuerzo:** Medio (2-3h)  
**Dependencias:** Después de T4  
**Riesgo:** Medio  

**Archivos afectados:**
- `app/causacion/views.py` (función que procesa upload)
- `app/causacion/templates/` (si necesita cambio en template)

**Pasos:**
1. En vista `subir_factura_compra`, wrap save en try-except:
   ```python
   try:
       factura.save()
   except ValidationError as e:
       # Retorna 409 con datos de original
       original_id = extract_id_from_error(str(e))
       original = FacturaCompra.objects.get(id=original_id)
       return JsonResponse({
           'error': 'Factura duplicada',
           'original': {
               'id': original.id,
               'proveedor': original.nit_proveedor,
               'numero': original.numero,
               'fecha': original.fecha.isoformat(),
           }
       }, status=409)
   ```

2. Test que POST con duplicado retorna 409
3. Test que response incluye datos de original

**Criterio de éxito:**
- ValidationError es caught
- Retorna 409 con datos de factura original
- Tests de API pasan

---

### T6: Pruebas — Unit Tests Exhaustivos
**Esfuerzo:** Medio (3h)  
**Dependencias:** Después de T5  
**Riesgo:** Bajo  

**Archivos afectados:**
- `app/causacion/tests/test_validar_cufe_duplicado.py` (nuevo)

**Pasos:**
1. Test: Happy path (factura nueva):
   ```python
   def test_factura_nueva_se_acepta(self):
       factura = FacturaCompra.objects.create(...)
       self.assertTrue(factura.id)  # Se guardó
   ```

2. Test: CUFE duplicado exacto:
   ```python
   def test_cufe_duplicado_levanta_error(self):
       factura1 = ...
       factura2 = FacturaCompra(...cufe=factura1.cufe...)
       with self.assertRaises(ValidationError):
           factura2.save()
   ```

3. Test: API retorna 409:
   ```python
   def test_post_duplicado_retorna_409(self):
       factura1 = ...
       response = self.client.post('/api/facturas/', {...cufe...})
       self.assertEqual(response.status_code, 409)
   ```

4. Test: Duplicado por NIT+número+fecha (fuzzy):
   ```python
   def test_nit_numero_fecha_duplicado(self):
       # Similar a CUFE pero sin CUFE exacto
   ```

5. Test: Offline (modelo rechaza, no entra a signal):
   ```python
   def test_validacion_offline_local(self):
       # Local validation antes de conectar
   ```

**Criterio de éxito:**
- 5+ tests pasan
- Coverage ≥ 85%
- Todos los casos del spec cubiertos

---

### T7: UI — Modal de Rechazo Duplicado
**Esfuerzo:** Pequeño (2h)  
**Dependencias:** Después de T5  
**Riesgo:** Bajo  

**Archivos afectados:**
- `app/causacion/templates/modal_duplicado.html` (nuevo)
- `app/causacion/templates/subir_factura.html` (actualizar JS)
- `app/causacion/static/css/modales.css` (si necesario)

**Pasos:**
1. Crea HTML modal:
   ```html
   <div id="modalDuplicado" class="modal" style="display:none;">
     <div class="modal-content">
       <h2>⚠️ Factura Duplicada</h2>
       <table>
         <tr><td>Proveedor:</td><td id="proveedorOriginal"></td></tr>
         <tr><td>Número:</td><td id="numeroOriginal"></td></tr>
         <tr><td>Fecha:</td><td id="fechaOriginal"></td></tr>
         <tr><td>Registrada por:</td><td id="usuarioOriginal"></td></tr>
       </table>
       <button onclick="cerrarModal()">Entendido</button>
       <button onclick="irAFactura()">Ver Original</button>
     </div>
   </div>
   ```

2. En JavaScript, cuando API retorna 409:
   ```javascript
   if (response.status === 409) {
       mostrarModalDuplicado(response.data.original);
   }
   ```

3. CSS para modal (centrado, responsive, overlay)

**Criterio de éxito:**
- Modal aparece cuando API retorna 409
- Datos se rellenan correctamente
- Modal es cerrable
- Botones funcionan (Entendido, Ver Original)
- Es usable en celular

---

### T8: Verificación End-to-End
**Esfuerzo:** Pequeño (1-2h)  
**Dependencias:** Después de T7  
**Riesgo:** Bajo  

**Pasos:**
1. Levanta servidor: `python manage.py runserver`
2. Invoca `/verify-after-changes`:
   ```bash
   /verify-after-changes
   ```
3. El skill prueba 5 casos:
   - Caso 1: Factura nueva → ✅ Se acepta
   - Caso 2: CUFE duplicado exacto → ✅ Modal muestra original
   - Caso 3: NIT+fecha duplicado → ✅ Rechaza
   - Caso 4: Offline → ⚠️ Verifica comportamiento
   - Caso 5: Admin crea directo → ✅ BD rechaza
4. Si alguno falla, arregla y reintenta

**Criterio de éxito:**
- `/verify-after-changes` retorna: "Luz verde, 5/5 pasan"

---

## 5. Estimación Total

| Tarea | Esfuerzo | Dependencias |
|-------|----------|-------------|
| T1: Preparación | 2h | — |
| T2: Modelo | 1.5h | T1 |
| T3: Extracción | 1.5h | T1 |
| T4: Signal | 3.5h | T2, T3 |
| T5: Vistas | 2.5h | T4 |
| T6: Tests | 3h | T5 |
| T7: UI | 2h | T5 |
| T8: Verificación | 1.5h | T7 |
| **TOTAL** | **~18h** | |

Esto es ~2-3 días de desarrollo full-time, o 1 semana part-time.

(±50% en realidad; puede ser más rápido si todo sale bien)

---

## 6. Riesgos y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigation |
|--------|------------|--------|-----------|
| CUFE no siempre en XML real | Media | Bajo | Fallback a NIT+número+fecha |
| OCR extrae mal número | Media | Medio | Preguntar si es ≥ 0.85 confianza |
| Performance: validar en cada save | Baja | Bajo | Solo valida si tiene cufe |
| Tests lentos si muchas facturas | Baja | Bajo | Limitar fixtures a 10-20 |
| Admin crea duplicado directo | Baja | Bajo | Constraint en modelo lo rechaza |

---

## 7. Siguiente Paso

Después de completar todas las tareas:

1. **Todos los tests pasan:**
   ```bash
   pytest app/causacion/tests/test_validar_cufe_duplicado.py -v
   ```

2. **Verificación en navegador:**
   ```bash
   /verify-after-changes
   ```
   - 5/5 casos pasan
   - Reporte OK
   - Luz verde

3. **Commit final:**
   ```bash
   git commit -m "Feat: validación de CUFE duplicado (P1 - Compras)

   Implementa todas las tareas del plan docs/plans/2026-07-15-validar-cufe-duplicado.md
   
   - Modelo: campo cufe + constraint único
   - Signal: validar duplicado pre_save
   - Vistas: retorna 409 con datos de original
   - UI: modal muestra factura duplicada
   - Tests: 8+ tests con coverage ≥ 85%
   
   /verify-after-changes confirma funcionamiento en navegador.
   "
   ```

4. **PR + Merge:**
   - Referencia: `docs/plans/2026-07-15-validar-cufe-duplicado.md`
   - Descripción: Lista de tareas completadas
   - Aprobado: Code review + tests green

---

**Plan finalizado. Comienza por T1. 🎯**
```

---

## Notas

- Cada tarea es **implementable en 1-2 sesiones**
- **T1 (Preparación) es crítica** — no la saltes
- **Tests se hacen junto con código**, no al final
- **Si un tarea toma más de lo estimado**, la divides en dos
- **Commits por tarea** — así el historio queda limpio

Este plan es la **hoja de ruta exacta** desde "tenemos spec" hasta "código listo para PR".
