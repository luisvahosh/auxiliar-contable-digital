# Ejemplos de Design-Spec

Estos son ejemplos reales de cómo se verían las especificaciones generadas por el skill en el proyecto.

---

## Ejemplo 1: Validación de CUFE Duplicado en Compras

**Contexto:** Después de `/brainstorming`, el usuario eligió "Opción B: Lógica en signals con historial".

**Invoca:** `/design-spec`  
**Responde:** Preguntas sobre usuario, alcance, errores  
**Genera:** Este documento

---

```markdown
# Validación de CUFE Duplicado en Compras
📅 Especificación del 2026-07-15

## 1. Overview

Cuando el auxiliar sube una factura de compra (XML, foto o manual), validamos que el CUFE (o combinación NIT+número+fecha) no exista ya en nuestro sistema. Si existe, rechazamos la factura con un mensaje claro que muestra la factura original.

Esto evita asientos duplicados que rompen el cuadre y generan reparación manual en contabilidad.

**Éxito se mide por:**
- Cero facturas de compra duplicadas aprobadas en 30 días de uso
- Auxiliar entiende por qué fue rechazada (<1 segundo para entender)

---

## 2. Usuario Objetivo

**Perfil:**  
Auxiliar de contabilidad con 1-2 años de experiencia, procesa 10-20 facturas de compra diarias, trabaja principalmente en celular/tablet durante la mañana en la oficina del cliente. Conexión Wi-Fi estable pero ocasionalmente lenta.

**Necesidad concreta:**  
No registrar la misma factura de proveedor dos veces por error de click doble o confusión entre XLS/email/presencial.

**Frecuencia de uso:**  
Diaria — cada factura pasa por esta validación.

**Restricciones del usuario:**  
- Movilidad: necesita que cargue rápido en celular
- Paciencia: si tarda >3s en responder, sospecha que se atascó
- Conocimiento: no es técnico, no entiende "CUFE" sin contexto

---

## 3. Contexto del Problema

**Situación actual:**  
Auxiliar sube factura de compra vía XML o foto → sistema NUNCA rechaza por duplicado → se genera asiento duplicado → contador lo detecta en cuadre de mes → corrige manualmente → pérdida de 1-2 horas.

**Dolor:**  
- Tedioso: corregir duplicados es trabajo manual sin valor
- Arriesgado: si contador no detecta, los reportes financieros están mal
- Humillante: auxiliar se siente culpable pero es un error fácil de cometer

**Dato importante:**  
CUFE (Código Único de Factura Electrónica) es un SHA-1 de DIAN que garantiza unicidad: mismo proveedor + mismo número + misma fecha = mismo CUFE, sin excepciones. Si no hay CUFE (factura física), combinación NIT proveedor + número + fecha es "casi seguro duplicado" (falso positivo raro).

**Dependencia externa:**  
Alegra ya rechaza por CUFE al sincronizar, pero nosotros no sabemos cuándo el auxiliar lo subió a Alegra. Detectarlo aquí previene trabajo manual después.

---

## 4. Alcance

**Incluye:**

- U1: Detectar duplicado al subir XML de compra (canal principal)
- U2: Detectar duplicado al subir foto de factura física + OCR
- U3: Detectar duplicado al importar lote vía comando (`causar_lote`)
- U4: Mostrar datos de factura original (proveedor, número, fecha, quién la registró, cuándo)
- U5: Permitir ver la factura original desde el modal de rechazo
- Registrar en auditoria que se rechazó por duplicado (para investigaciones)
- Validación multi-tenant: duplicado es por empresa (no global)

**Excluye deliberadamente:**

- No comparamos contra Alegra en tiempo real (eso lo hace Alegra)
- No intentamos "fusionar" datos de duplicados (el usuario reintenta o pide ayuda)
- No reactivamos duplicados que fueron rechazados y después marcados como aprobados
- No hacemos fusiones automáticas de asientos
- No alertamos por correo sobre duplicados (el usuario ve el rechazo en pantalla)

---

## 5. Comportamiento Esperado

**Happy path (factura nueva):**

1. Auxiliar abre módulo Causación → "Subir factura de compra"
2. Elige XML o foto
3. Sube archivo
4. Sistema procesa: extrae NIT proveedor, número de factura, CUFE (si XML), fecha
5. Sistema valida: ¿existe factura con este CUFE (exacto) o NIT+número+fecha (en esta empresa)?
6. **Resultado: NO existe** → Continúa flujo normal (clasificación, retencion, etc.)

**Flujo alternativo (factura duplicada):**

1-5. [Igual que happy path]
6. **Resultado: SÍ existe** → 
7. Sistema detiene el proceso
8. Muestra modal: **"⚠️ Factura Duplicada"**
   - Título descriptivo
   - Tabla con datos de la factura ORIGINAL:
     - Proveedor: [nombre]
     - Número: [número]
     - Fecha: [fecha]
     - Monto: [valor]
     - Registrada por: [nombre del auxiliar]
     - Fecha de registro: [cuándo]
     - Estado: [aprobada/pendiente/rechazada]
   - Botones:
     - "Entendido" (cierra modal)
     - "Ver factura original" (abre detalles de la FacturaCompra)
9. Modal se cierra, no se guarda nada, auxiliar puede reintentar con otro archivo

**Datos de entrada:**

- **XML:** Bloque UBL con UUID (CUFE exacto), NIT proveedor, número factura, fecha
- **Foto:** Imagen JPEG, OCR extrae NIT+número+fecha (con confianza ≥ 0.8, si no lanza error de OCR)
- **Manual:** Usuario ingresa NIT+número+fecha explícitamente en formulario

Validación básica:
- NIT: string 1-15 caracteres, numérico + dígito verificación
- Número: 1-20 caracteres, alfanumérico
- Fecha: ISO 8601, no futura, no anterior a 2000

**Datos de salida:**

- **Si no duplicado:** Continúa, retorna factura creada
- **Si duplicado:** Modal con referencia a original, no se guarda nada, retorna error 409 Conflict (HTTP)

**Integraciones:**

- **Base de datos:** Lee tabla `causacion_facturacompra` filtrando por empresa, busca por (cufe) o (nit_proveedor, numero, fecha)
- **Auditoria:** Log `"duplicado_rechazado"` con factura_id del duplicado intentado, factura_id_original, timestamp, usuario
- **Ninguna integración con Alegra** (eso es posterior)

**Nivel de automaticidad:** 🟢 **Automática**  
Se valida y rechaza sin pedir confirmación. Es imposible que un duplicado pase esta validación.

**UI/UX mínimo:**

- **Flujo:** Subir → Esperar 2-3s → Si duplicado: modal → Entendido → Vuelve a lista
- **Modal:** Centrado, fondo oscuro, datos en tabla clara, botones grandes (móvil)
- **Mensajes:**
  - Encabezado: "⚠️ Factura Duplicada"
  - Cuerpo: "Esta factura ya fue registrada. Revisa los datos de la original."
  - Botón primario: "Entendido" (azul, grande)
  - Botón secundario: "Ver original" (gris, pequeño)

---

## 6. Posibles Errores y Mitigaciones

### Error 1: Falso positivo — Factura legítima rechazada por OCR malo

**Síntoma:**  
Auxiliar sube foto de factura nueva (mismo proveedor, número similar), sistema rechaza diciendo que es duplicada.

**Causa probable:**  
OCR extrajo número 1001 cuando la factura real dice 1010; sistema compara (NIT + 1001 + fecha) contra (NIT + 1001 + fecha) en BD y encuentra match.

**Mitigación:**  
- Para XML: CUFE es exacto (no hay falso positivo).
- Para foto: Si OCR retorna confianza < 0.85 en número de factura, NO usamos NIT+número+fecha para comparar. En su lugar:
  - Sistema dice: "No pude leer el número de factura con seguridad. ¿Es (aproximadamente) #[ocr_number]?" 
  - Auxiliar confirma o corrige
  - Luego validamos con el número confirmado
- Para manual (digitación): Usuario ingresa número explícitamente, sin OCR.

**Nivel:** 🟡 **Sugerida**  
Si confianza OCR en número < 0.85, no rechazamos automáticamente; pedimos confirmación.

**Mensaje exacto:**  
"El sistema leyó número #[ocr_number] con poca seguridad. ¿Es ese el número? [Sí] [No, es otro]"

---

### Error 2: Duplicado no detectado — Conexión offline

**Síntoma:**  
Auxiliar sube factura mientras está sin conexión (modo offline), luego se conecta. Duplicado no se detecta porque offline no pudo consultar BD.

**Causa:**  
App offline almacena draft localmente; al conectarse, supuestamente debe validar antes de guardar, pero falla.

**Mitigación:**  
- App **NO permite offline** para subir facturas (valida que hay conexión antes de mostrar botón de subir). Si no hay conexión, muestra: "Necesita conexión para subir facturas. Espere o reintente más tarde."
- Alternativa: Si el usuario insiste (hay campo "guardar borrador offline"), al conectarse el app le advierte: "Detectamos que esta factura podría ser duplicada. ¿Quiere revisarla?" y muestra candidato.

**Nivel:** 🟢 **Automática**  
No permite guardar offline; esto no es un "error" sino una restricción de diseño.

**Mensaje exacto:**  
"Sin conexión no puedo verificar si la factura existe. Conectese a Wi-Fi o datos y reintente."

---

### Error 3: Usuario intenta forzar duplicado vía Django admin

**Síntoma:**  
Admin accede a Django admin, edita FacturaCompra directamente, crea CUFE duplicado (o NIT+número+fecha).

**Causa:**  
Validación es en la lógica de app, no en modelo. Admin puede bypassear.

**Mitigación:**  
- Agregar `validators` en modelo `FacturaCompra.cufe` que valide unicidad por empresa.
- O agregar `unique_together` en Meta: `unique_together = [('empresa', 'cufe')]`
- Django admin rechaza el save con error: "Factura con este CUFE ya existe en la empresa."
- Admin ve el error, revisa qué está mal, cancela o corrige.

**Nivel:** 🟢 **Automática**  
BD rechaza el save; no es opción.

**Mensaje exacto (en admin):**  
"Error: CUFE [cufe_value] ya existe para esta empresa. ID original: [link a factura]."

---

### Error 4: Confusión entre tipo — factura de venta #001 vs compra #001

**Síntoma:**  
Sistema rechaza factura de COMPRA #001 diciendo que VENTA #001 es duplicada.

**Causa:**  
Validación no diferencia tipo de factura.

**Mitigación:**  
- Duplicado se valida por: **tipo** (FacturaCompra vs FacturaVenta) + empresa + NIT (proveedor o cliente) + número + fecha.
- CUFE en XML ya contiene tipo implícitamente (códigos distintos para UBL compra vs UBL venta).
- Query en BD: `FacturaCompra.objects.filter(empresa=empresa, nit_proveedor=nit, numero=numero, fecha=fecha)` — solo busca FacturaCompra, no FacturaVenta.

**Nivel:** 🟢 **Automática**  
Por diseño, buscamos en el modelo correcto.

**Mensaje exacto:**  
N/A — este error no debería ocurrir.

---

**FIN DE ESPECIFICACIÓN — 2026-07-15**
```

---

## Ejemplo 2: Reportar Rechazo de Factura Venta por DIAN

**Contexto:** Se implementó P6.3 (monitoreo DIAN), pero falta flujo de notificación al usuario.

**Invoca:** `/design-spec`  
**Responde:** Información simplificada porque viene de `/brainstorming` anterior  
**Genera:**

```markdown
# Notificación de Rechazo de Factura Venta por DIAN
📅 Especificación del 2026-07-14

## 1. Overview

Cuando la DIAN rechaza una factura de venta (ApplicationResponse con código de rechazo), el sistema notifica al auxiliar mostrando el motivo. El auxiliar puede ver el reporte técnico de la DIAN o reclasificar/corregir la factura.

Esto cierra el ciclo: factura emitida → validación DIAN → reporte al usuario.

**Éxito se mide por:**
- Auxiliar se entera del rechazo dentro de 1 hora de que la DIAN rechaza
- Entiende por qué fue rechazada (código + descripción amigable)

---

## 2. Usuario Objetivo

**Perfil:**  
Auxiliar de contabilidad senior o contador, que emite 5-10 facturas de venta diarias y necesita estar al tanto de rechazos antes de reportar.

**Necesidad:**  
Detectar facturas rechazadas por DIAN para corregirlas y re-emitir.

**Frecuencia:**  
Varias veces al mes (no diaria, pero crítica cuando ocurre).

**Restricción:**  
Debe notificar en < 1 hora; mail es aceptable pero notificación en-app es preferida.

---

## 3. Contexto del Problema

**Situación actual:**  
Factura se emite → Alegra la manda a DIAN → DIAN acepta o rechaza → Alegra guarda el resultado → auxiliar No tiene forma de saber que fue rechazada (debe revisar Alegra manualmente).

**Dolor:**  
- Lentitud: contador descubre rechazos cuando cierra la facturación (fin de mes)
- Riesgo: reporta factura rechazada como válida
- Manual: contador debe revisar Alegra cada vez

**Dato importante:**  
DIAN da 7 días desde emisión para aceptar/rechazar. Después de eso, factura es COMO SI fuera aceptada (presunción de aceptación tácita, art. 622 ET).

---

## 4. Alcance

**Incluye:**
- U1: Mostrar lista de facturas rechazadas por DIAN en dashboard
- U2: Notificar por correo (opt-in por empresa)
- U3: Mostrar código de rechazo + descripción amigable
- U4: Link para ver ApplicationResponse original
- U5: Link para re-emitir o reclasificar la factura

**Excluye:**
- No re-emitimos automáticamente
- No modificamos números de factura (eso lo hace Alegra)
- No contactamos a DIAN (eso lo hace Alegra)

---

## 5. Comportamiento Esperado

**Happy path:**
1. DIAN rechaza factura venta #42 con código "REC-001"
2. Sistema recibe ApplicationResponse (via Alegra API o buzón)
3. Sistema marca FacturaVenta.dian_estado = "rechazada", guarda código y motivo
4. En-app: Panel Facturación → Monitoreo DIAN destaca rechazo (rojo)
5. Por correo (si opt-in): "Factura #42 fue rechazada por DIAN — [motivo breve]"
6. Auxiliar hace clic en factura → ve detalles + código técnico
7. Corrige (ej: IVA mal) y re-emite vía Alegra

**Datos:**
- Entrada: ApplicationResponse XML de DIAN
- Salida: Notificación en-app + correo + registro en BD

**Integraciones:**
- Lee `FacturaVenta`, guarda `dian_estado`, `dian_codigo`, `dian_motivo`
- Envía mail via `send_email()`

**Nivel:** 🟢 **Automática** (detecta y notifica sin intervención)

**UI mínimo:**
- Tabla con facturas rechazadas, badge rojo "Rechazada"
- Click → modal con "Código: [REC-001]", "Motivo: [descripción]", "Visto en DIAN: [fecha]"
- Botón "Ver ApplicationResponse" (descarga XML)
- Botón "Re-emitir en Alegra" (abre Alegra en nueva tab)

---

## 6. Posibles Errores y Mitigaciones

### Error 1: Notificación tardía

**Síntoma:** Factura fue rechazada el lunes, auxiliar se entera el viernes.  
**Causa:** Comando `alertar_rechazos_dian` no se ejecutó.  
**Mitigación:** Ejecuta comando cada 4 horas (cron). Si falla, retardo < 4h.

**Nivel:** 🟡 Sugerida (avisa si hay rechazos sin alertar)

**Mensaje:** "Hay rechazos de DIAN sin revisar. Haga clic para verlos."

---

### Error 2: Falso positivo de rechazo

**Síntoma:** Sistema marca como rechazada una factura que DIAN aceptó.  
**Causa:** Parser de ApplicationResponse leyó código incorrectamente.  
**Mitigación:** Validar que dian_estado viene de ApplicationResponse confiable (XML válido).

**Nivel:** 🟢 Automática (parser es estricto)

---

**FIN DE ESPECIFICACIÓN — 2026-07-14**
```

---

## Patrón: Después de design-spec

Típicamente:

```
1. /design-spec
   → Genera docs/specs/YYYY-MM-DD-{titulo}.md

2. Usuario revisa y edita si falta algo

3. Desarrollo:
   a. Crear rama: git checkout -b feat/2026-07-15-validar-cufe-duplicado
   b. Escribir tests basados en "Comportamiento Esperado"
   c. Implementar según spec
   d. PR con referencia: "Implementa docs/specs/2026-07-15-validar-cufe-duplicado.md"
```

El documento es el **contrato** — el código debe cumplirlo exactamente.
