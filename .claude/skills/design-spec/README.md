# Skill Design-Spec — Especificación de Usuario

Este skill genera un **documento de especificación desde la perspectiva del usuario** — no es arquitectura, es "qué quiero que pase cuando uso esto".

El documento serve como **contrato entre análisis (tú) y ejecución (el código)**.

## Cuándo usarlo

✅ Después de `/brainstorming` con una alternativa clara  
✅ Funcionalidad nueva de complejidad media/alta  
✅ Algo que toca múltiples módulos  
✅ Integración con decisiones sobre qué falla y cómo  

❌ Bugs triviales ("corregir typo")  
❌ Cambios puramente técnicos (refactor, actualizar librería)  
❌ Cosas que ya están especificadas en otro doc  

## Qué sale

Un archivo Markdown en `docs/specs/YYYY-MM-DD-{titulo-corto}.md` con:

1. **Overview** — qué es, por qué ahora, cómo se mide éxito
2. **Usuario objetivo** — quién es, qué necesita, con qué restricciones
3. **Contexto del problema** — qué duele hoy, qué datos importan
4. **Alcance** — qué cubre, qué NO cubre deliberadamente
5. **Comportamiento esperado** — flujo paso a paso, datos, integraciones
6. **Posibles errores** — qué puede fallar, cómo se maneja, qué se le dice al usuario

## Ejemplo de uso

```bash
/design-spec
```

Luego responde a las preguntas:

- **Título:** "Validación de CUFE duplicado en compras"
- **Usuario:** Auxiliar que procesa 10-20 facturas diarias
- **Problema:** Hoy acepta facturas duplicadas; genera asientos duplicados
- **Alcance:** Validar al subir XML; rechazar con explicación
- **Error que puede ocurrir:** Misma factura subida dos veces en 10 minutos → primera aprobada, segunda rechazada → usuario confundido

El skill genera:

```markdown
# Validación de CUFE Duplicado en Compras
📅 Especificación del 2026-07-15

## 1. Overview

Cuando el auxiliar sube un XML de compra, validamos que el CUFE no exista ya en el sistema. Si existe, rechazamos con un mensaje claro: "Factura duplicada — ya fue registrada el [fecha] por [usuario]".

Esto evita asientos duplicados y confusión.

**Éxito se mide por:**
- Cero facturas duplicadas aprobadas en 3 meses de uso
- Auxiliar entiende por qué fue rechazada

## 2. Usuario Objetivo

**Perfil:** Auxiliar de contabilidad junior, 1-2 años de experiencia, procesa 10-20 facturas diarias, trabaja en movilidad (celular/tablet).

**Necesidad:** No registrar la misma factura dos veces por error de click doble o confusión.

**Frecuencia:** Diario (cada factura pasa por esta validación).

**Restricción:** Conexión intermitente; si valida offline y después se conecta, el duplicado puede no detectarse al momento.

## 3. Contexto del Problema

**Situación actual:** Auxiliar sube XML → el sistema NUNCA rechaza por duplicado → se generan asientos duplicados → contador repara manualmente.

**Dolor:** Reparación manual es tediosa, auditoría incómoda, riesgo de error.

**Dato importante:** CUFE es la "firma" de la factura (está en el XML). Mismo NIT proveedor + mismo número de factura + misma fecha = casi seguro duplicado (DIAN lo garantiza).

**Dependencia:** Alegra ya rechaza por CUFE, pero no sabemos si nuestro auxiliar lo sabe.

## 4. Alcance

**Incluye:**
- U1: Detectar duplicado al subir XML (canal normal)
- U2: Detectar duplicado al subir foto de factura + OCR
- U3: Detectar duplicado al importar lote (comando)
- Mostrar factura original (fecha, usuario, estado)
- Registrar en logs que se rechazó por duplicado

**Excluye:**
- No comparamos contra Alegra (eso lo hace Alegra)
- No reactivamos duplicados rechazados
- No fusionamos datos de duplicados
- Validación es por empresa (multitenancy)

## 5. Comportamiento Esperado

**Happy path:**
1. Auxiliar abre "Subir factura de compra"
2. Sube XML o foto
3. Sistema procesa
4. Sistema valida: CUFE o (NIT+número+fecha) ya existe
5. **Si es nuevo:** sigue flujo normal → clasificación, etc.
6. **Si es duplicado:** 
   - Muestra modal: "Factura duplicada"
   - Datos: Proveedor, número, fecha, quién la registró, fecha de registro
   - Botones: "Entendido" (cierra), "Ver factura original" (lleva a la FacturaCompra)

**Datos:**
- Entrada: XML con UBL:UUID (CUFE) o foto con OCR que extrae NIT+número+fecha
- Salida: Rechazo con datos de original (si no hay CUFE, usa NIT+número+fecha)

**Integración:**
- Lee de BD: FacturaCompra.cufe, FacturaCompra.nit_proveedor, FacturaCompra.numero, FacturaCompra.fecha
- Log: `audit_log("duplicado_rechazado", factura_id=original.id, razon="cufe_exacto")`

**Nivel de automaticidad:** Automática (valida y rechaza, no pide confirmación).

**UI mínimo:**
- Modal "Factura duplicada" con tabla de datos
- Link "Ver original" abre detalles de la factura existente

## 6. Posibles Errores y Mitigaciones

### Error 1: Factura legitima rechazada por falso positivo
**Síntoma:** Auxiliar sube factura nueva, sistema dice que existe.  
**Causa posible:** OCR extrajo número mal, o NIT con dígitos de verificación inconsistentes.  
**Mitigación:** 
- Comparamos CUFE (exacto) vs NIT+número+fecha (fuzzy si OCR).
- Si CUFE existe = seguro duplicado, rechaza.
- Si CUFE no existe pero NIT+número+fecha parece duplicado = **sugerida** (no automática): "¿Esta factura ya fue registrada el [fecha]?" con opción de forzar.
- **Mensaje:** "Factura similar detectada. ¿Es duplicado o una factura nueva del mismo proveedor?" [Sí, es duplicado] [No, es nueva]
- **Nivel:** Sugerida.

### Error 2: Duplicado no detectado (conexión offline)
**Síntoma:** Auxiliar sube factura en offline, luego se conecta, duplicado no se detecta.  
**Causa:** App offline no puede consultar BD.  
**Mitigación:**
- App offline almacena draft con CUFE local.
- Al conectarse, valida antes de guardar.
- Si es duplicado, avisa: "Esta factura ya fue registrada en sesión anterior" y no guarda.
- **Nivel:** Automática (no permite guardar duplicado).

### Error 3: Usuario intenta forzar un duplicado via admin
**Síntoma:** Admin en Django admin edita FacturaCompra directamente, crea CUFE duplicado.  
**Causa:** Validación es en la app, no en el modelo.  
**Mitigación:**
- Agregar `unique_together` en modelo o un validator en `full_clean()` de FacturaCompra.
- Mensaje: "CUFE ya existe en la BD (ID #xxx)".
- **Nivel:** Automática (BD la rechaza).

### Error 4: Confusión entre facturas de compra vs. venta con mismo número
**Síntoma:** Factura de venta #001 rechaza factura de compra #001.  
**Causa:** Validación es global, no por tipo.  
**Mitigación:**
- Duplicado se valida por: tipo (FacturaCompra vs FacturaVenta) + NIT + número + fecha.
- CUFE ya tiene tipo implícito en el XML.
- **Nivel:** Automática.

---

**Documento especificación finalizado.**
```

El skill confirma dónde guardó el archivo y ofrece editar si falta algo.

## Después de design-spec

Ya con la especificación:

1. **Escribir tests** basados en el comportamiento esperado (TDD)
2. **Crear rama** de feature con el nombre del spec
3. **Implementar** según el doc
4. **PR referencia el spec** — "Implementa docs/specs/2026-07-15-validar-cufe-duplicado.md"

## No necesitas memorizar

El skill tiene toda la estructura. Invócalo, responde preguntas, revisa el doc que genera, ajusta si falta algo. Listo.
