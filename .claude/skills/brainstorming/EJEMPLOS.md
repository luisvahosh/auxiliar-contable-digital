# Ejemplos de Brainstorming

Estos son ejemplos ficticios de cómo se vería el skill en acción en el proyecto.

---

## Ejemplo 1: Agregar auditoría de cambios en facturas

### Lo que el usuario dice
```
/brainstorming Quiero trackear quién cambió qué en las facturas aprobadas, 
para poder revisar cambios después de aprobación
```

### Lo que el skill preguntaría
1. ¿Auditoría solo de FacturaCompra y FacturaVenta, o también en terceros y asientos?
2. ¿Qué cambios importan? ¿Solo números (valor, retefuente) o también campos textuales?
3. ¿Es solo para datos financieros o también para metadata (estado, asignado a, notas)?
4. ¿Necesitas reportes o solo historial en la vista de detalle?

### Alternativas que presentaría

**Opción A: Historial simple con django-audit-log**
- Usa librería existente de auditoría por modelo
- Pro: Cero código custom, coverage automático
- Contra: Ruido (audita todo, incluso cambios irrelevantes); inflación de BD
- Esfuerzo: Pequeño (2 horas)
- Módulo: `causacion/models.py` + instalación de paquete

**Opción B: Auditoría manual con modelo AuditoriaFactura**
- Modelo explícito que registra usuario, timestamp, campo, valor antes/después
- Pro: Control fino, sin ruido, performante
- Contra: Más trabajo, hay que capturar cambios en signals/vistas
- Esfuerzo: Medio (6-8 horas)
- Módulo: `causacion/models.py` (nuevo), `causacion/signals.py`

**Opción C: Auditoría en la vista con historial descriptivo**
- Solo en facturas APROBADAS, sin modelo, textual ("Cambió retefuente de 100k a 120k")
- Pro: Simple, solo lo que importa
- Contra: No queryable, pierde granularidad
- Esfuerzo: Pequeño (3-4 horas)
- Módulo: `causacion/views.py`

### Recomendación
**Opción B** — el proyecto tiene datos financieros sensibles y el contador probablemente quiera revisar auditorías. Ruido de django-audit-log es un problema; Opción C es demasiado limitada.

**Siguiente paso:**
1. Lee `causacion/models.py` líneas 50-80 (FacturaCompra/FacturaVenta)
2. Diseña modelo `AuditoriaFactura` con campos: factura (FK), usuario, timestamp, campo, valor_antes, valor_despues
3. Escribe test `test_auditar_cambio_retefuente` en `causacion/tests/test_auditoria.py`
4. Implementa signal en `post_save` que capture cambios vs BD

---

## Ejemplo 2: Exportar nómina a formato PILA

### Lo que el usuario dice
```
/brainstorming Necesito que la nómina aprobada se exporte en formato PILA
para entregarle al cliente
```

### Lo que el skill preguntaría
1. ¿Quién entrega el archivo? ¿El auxiliar (tu app) o el operador de nómina (out of scope)?
2. ¿Es validación/prearmado de PILA, o descarga lista para PILA?
3. ¿Qué validaciones de PILA necesita? (ej: IBC mínimo, formato de carrera, etc.)
4. ¿Múltiples formatos PILA según empresa, o uno genérico?

### Alternativas que presentaría

**Opción A: Descarga CSV pre-PILA (borrador)**
- Columnas: cédula, nombre, IBC, aporte salud, aporte pensión
- Pro: Simple, el operador lo sube a PILA manualmente
- Contra: No es PILA nativo; operador hace trabajo extra
- Esfuerzo: Pequeño (3 horas)
- Módulo: `nomina/exportes.py`
- Contexto: Respeta "asistir, no reemplazar" — PILA sigue siendo responsabilidad del operador

**Opción B: XML PILA completo**
- Genera XML con esquema oficial PILA (headers, validaciones, checksum)
- Pro: Listo para subir, operador usa directo
- Contra: XML es frágil, validaciones complejas, quebrar PILA oficial es riesgo legal
- Esfuerzo: Grande (20+ horas)
- Módulo: `nomina/pila.py` (nuevo)
- Contexto: Riesgo de posicionarse como "fuente oficial" en lugar de asistencia

**Opción C: Tabla visual + botón descarga CSV**
- Panel en Nómina que muestra tabla con empleado/IBC/aportes, botón descarga CSV
- Pro: Intermedio, usuario revisa antes de entregar
- Contra: Dos pasos (revisar + entregar)
- Esfuerzo: Medio (6-8 horas)
- Módulo: `nomina/views.py`, `nomina/exportes.py`

### Recomendación
**Opción A** — la CLAUDE.md dice "asistir, no reemplazar". El cliente tiene Aleluya/Nominapp; aquí solo ayudamos. XML PILA (Opción B) nos posiciona como fuente oficial y es riesgoso si PILA cambia. Opción C es más work sin gran valor sobre A.

**Siguiente paso:**
1. Lee `nomina/exportes.py` (ya existe `exportar_nómina_electronica`)
2. Agrega función `exportar_pre_pila` similar
3. Test: `test_exportar_pre_pila_incluye_todos_empleados`
4. Añade botón en template `nomina/liquidacion_detail.html`

---

## Ejemplo 3: Alertas SMS cuando vence un impuesto

### Lo que el usuario dice
```
/brainstorming Agregar alertas por SMS cuando faltan 3 días para vencer 
un impuesto en el calendario
```

### Lo que el skill preguntaría
1. ¿Solo SMS o también email/push? (Hoy ya hay email, ¿SMS es adicional o reemplazo?)
2. ¿Quién recibe? ¿Admin de la empresa? ¿Contador externo? ¿Configurable?
3. ¿Número de teléfono dónde se guarda? ¿Manual en Empresa o automático de contacto?
4. ¿Proveedor de SMS? (ej: Twilio, AWS SNS — costo, .env)
5. ¿Opt-in o automático? (Convención: nivel automática/sugerida/manual)

### Alternativas que presentaría

**Opción A: SMS via Twilio + email simultáneo**
- Mismo comando `enviar_alertas_tributarias` envía SMS + email
- Pro: Redundancia, usuario elige favorito
- Contra: Costo de Twilio, requiere .env + API key, número guardado en BD
- Esfuerzo: Medio (8-10 horas)
- Módulo: `calendario/services.py`, `calendario/models.py` (agregar phone)

**Opción B: Email + link a dashboard**
- En lugar de SMS, email + un enlace corto que lleva a la factura en la app
- Pro: Cero costo, ya existe infraestructura de email
- Contra: Menos urgente que SMS, requiere acceso a la app
- Esfuerzo: Pequeño (2 horas)
- Módulo: `calendario/services.py` (template)

**Opción C: SMS solo para admins sin email verificado**
- SMS como "fallback" si el admin no tiene correo
- Pro: Costo mínimo, cubre gap de contacto
- Contra: Más lógica condicional
- Esfuerzo: Medio (8 horas)
- Módulo: `core/models.py`, `calendario/services.py`

### Recomendación
**Opción A** — el contador puede estar en movilidad; SMS es más confiable. Costo de Twilio es insignificante vs. riesgo de no pagar a tiempo un impuesto. Configurable por empresa.

**Siguiente paso:**
1. Escribe test `test_enviar_alerta_tributaria_sms_a_admin` (mock Twilio)
2. Crea variable .env `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_PHONE`
3. Lee `calendario/models.py` y agrega campo `VencimientoTributario.admin_phone`
4. Refactoriza `enviar_alertas_tributarias` para incluir SMS

---

## Patrón común: Decisión sobre "nivel automática/sugerida/manual"

Muchas funcionalidades en el proyecto tendrán que decidir si son:

- **Automática:** ejecuta sin confirmación (ej: conciliación exacta)
- **Sugerida:** propone, usuario revisa y aprueba (ej: clasificación de gasto)
- **Manual:** usuario inicia explícitamente (ej: reclasificación)

El skill siempre preguntará esto, porque la CLAUDE.md lo pide: "toda acción automática tiene nivel automática/sugerida/manual y explica su porqué."

---

## Notas finales

- **Puedes invocar `/brainstorming` en cualquier momento** — si durante el trabajo descubres un giro importante, haz un brainstorming de esa decisión.
- **El skill no es gospel** — si después de escuchar las alternativas tienes otra idea, adelante. El skill es una estructura, no una regla.
- **Documenta la decisión en tu rama** — commit message o PR describe por qué elegiste esa opción.
