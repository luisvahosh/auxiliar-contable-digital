# TEMPLATE — Estructura de Design-Spec

Copia este template para generar nuevas especificaciones. Reemplaza los placeholders `[...]` con contenido real.

---

```markdown
# [Nombre de funcionalidad]
📅 Especificación del [YYYY-MM-DD]

## 1. Overview

[2-3 frases describiendo qué es en nivel ejecutivo]

[Línea de contexto: por qué ahora / trigger / urgencia, si aplica]

**Éxito se mide por:**
- [Criterio 1 — observable, medible]
- [Criterio 2]

---

## 2. Usuario Objetivo

**Perfil:**  
[Rol específico, experiencia, frecuencia de trabajo, contexto]

Ejemplo malo: "Contador"  
Ejemplo bueno: "Auxiliar de contabilidad junior que procesa 10-20 facturas diarias en celular durante la mañana"

**Necesidad concreta:**  
[Qué quiere lograr en concreto — no funcionalidad, sino outcome]

**Frecuencia de uso:**  
[Diario / semanal / mensual / excepcional]

**Restricciones del usuario:**  
[Movilidad, conectividad, conocimiento técnico, tiempo disponible]

---

## 3. Contexto del Problema

**Situación actual:**  
[Cómo lo hace hoy — manual, otro software, request a otro rol]

**Dolor:**  
[Qué es tedioso, lento, propenso a error, arriesgado]

**Dato o restricción importante:**  
[Algo del negocio/regulación que afecta la solución]

Ejemplo: "DIAN requiere que la factura tenga CUFE válido"  
Ejemplo: "Retefuente es 5% para no declarantes, 10% para declarantes"  
Ejemplo: "Impaciencia del usuario: si tarda >3s, abandona"

**Dependencias externas:**  
[Otros sistemas, roles, integraciones que afectan]

Ejemplo: "Alegra es la fuente de verdad de cuentas"  
Ejemplo: "Contador revisa cada asiento antes de reportar"

---

## 4. Alcance

**Incluye:**

- U1: [Caso de uso 1]
- U2: [Caso de uso 2]
- U3: [Caso de uso 3]
- Integración con [sistema/módulo]
- Flujo de [tipo de entrada]
- Vistas/pantallas: [lista]

**Excluye deliberadamente:**

- [Lo que NO hacemos, con razón si no es obvia]
- [Validación que hace otro sistema]
- [Casos extremos que no cubrimos]
- [Extensiones futuras]

---

## 5. Comportamiento Esperado

**Happy path (flujo normal):**

1. [Usuario entra por dónde]
2. [Ve qué]
3. [Hace acción 1]
4. [Sistema responde con]
5. [Usuario ve resultado]

Escribe como narración, no como API.

**Datos de entrada:**

- [Campo/parámetro]: [tipo, rango, validación básica]
- [Campo/parámetro]: [ej: NIT empresa, string 1-10 dígitos]

**Datos de salida:**

- [Qué produce]: [formato, consumidor]
- Ej: "Asiento contable balanceado → se guarda en BD y se manda a Alegra vía API"

**Integraciones:**

- [Sistema externo]: [qué datos intercambia, cuándo, error handling]
- Ej: "Llamamos a Alegra.post_journal si aprobado=true; si falla, guardamos estado `enviando` y reintentamos en 1h"

**Nivel de automaticidad:**

- ☐ Automática (ejecuta sin confirmación)
- ☐ Sugerida (propone, usuario aprueba)
- ☐ Manual (usuario inicia explícitamente)

[Elige uno y justifica brevemente si no es obvio]

**UI/UX mínimo:**

- Flujo de pantallas: [describe qué ve el usuario en cada paso]
- Botones/acciones principales: [lista]
- Mensajes críticos: [ejemplos de lo que se le dice]
- Restricciones de movilidad: [si aplica, ej: "debe funcionar en celular con conexión lenta"]

---

## 6. Posibles Errores y Mitigaciones

### Error 1: [Nombre descriptivo]

**Síntoma:**  
[Cómo se manifiesta al usuario — qué ve, qué pasa]

**Causa probable:**  
[Qué puede causar esto — entrada inválida, timeout, estado inconsistente, etc]

**Mitigación:**  
[Cómo lo detectamos y qué hacemos — validar antes, reintentar, avisar, etc]

**Nivel de manejo:**  
- ☐ Automática
- ☐ Sugerida
- ☐ Manual

**Mensaje exacto al usuario:**  
[Texto específico que aparece — amigable, no técnico]

---

### Error 2: [...]

[Repite estructura]

---

### Error 3: [...]

[Repite estructura — típicamente 2-4 errores principales]

---

**FIN DE ESPECIFICACIÓN**
```

---

## Notas al usar el template

1. **Reemplaza todos los `[...]`** con contenido concreto
2. **Quita ejemplos** que no apliquen
3. **Sé específico:** "auxiliar" es vago; "auxiliar de contabilidad que procesa compras en celular" es concreto
4. **Prueba la narrativa:** si lees el documento y entiendes exactamente qué debe pasar, está bien
5. **Valida contra el problema original:** ¿resuelve el dolor? ¿El usuario puede hacer lo que quiere?

## Checklists antes de guardar

- [ ] Overview tiene 2-3 frases + criterios de éxito
- [ ] Usuario objetivo es perfil específico, no rol genérico
- [ ] Alcance lista casos de uso y excluye deliberadamente
- [ ] Comportamiento esperado se puede narrar paso a paso
- [ ] Errores son 2-4 reales, no paranoia
- [ ] Mitigaciones son concretas, no vagas ("validar" → "validar que NIT tiene 10 dígitos")
- [ ] Alguien que lea esto sin conocer el proyecto entiende qué debe pasar

---

Copia este bloque completo a `docs/specs/YYYY-MM-DD-{titulo-corto}.md` y completa.
