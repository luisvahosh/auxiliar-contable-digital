# Proceso del Auxiliar Contable — Guía para probar la aplicación

**Fecha:** 11 de julio de 2026 · **Dueño:** Luis Vahos · **Versión:** 1
**Complementa:** PLAN.md (secciones 2, 3 y 9)

---

## 1. Propósito

Este documento describe **cómo trabaja realmente un auxiliar contable en Colombia**, proceso por proceso, para que cada funcionalidad de la app se pruebe contra el trabajo real que reemplaza — no contra lo que el código dice hacer. La regla de oro de cada prueba: *"¿el resultado es el mismo que entregaría un buen auxiliar humano, y el contador lo firmaría?"*

Cada proceso tiene: **disparador → insumos → pasos del auxiliar → resultado → controles**, y una tabla de **casos de prueba** con criterio de aceptación. Los procesos P1–P4 corresponden a la Fase 1 del plan; el resto se prueba cuando llegue su fase.

## 2. El ciclo mensual del auxiliar (vista general)

El trabajo del auxiliar no es una lista de tareas sueltas: es un **ciclo mensual con ritmo semanal y picos en fechas fijas**. La app debe probarse simulando este ciclo completo, no funcionalidades aisladas.

| Momento del mes | Qué hace el auxiliar |
|---|---|
| **Diario** | Descarga/recibe facturas electrónicas, causa compras y ventas, verifica retenciones de cada factura, registra pagos y recibos, archiva soportes |
| **Semanal** | Cruza cartera (quién debe, a quién se debe), envía recordatorios de cobro, programa pagos a proveedores, revisa rechazos DIAN |
| **Quincenal/Mensual** | Conciliación bancaria (al llegar el extracto), legalización de caja menor, depreciaciones, cierre del período |
| **Fechas del calendario tributario** | Prepara soportes para IVA, retefuente, ICA según los vencimientos del NIT; arma la carpeta que revisa el contador |
| **Anual (picos)** | Certificados de retención (feb–mar), información exógena (abr–jun), renovación matrícula mercantil (mar), certificados laborales F.220 |

**Implicación para las pruebas:** el escenario de prueba maestro es *"un mes completo de una empresa real"* — importar los documentos de un mes y verificar que al final del ciclo el contador recibe todo listo. Esa es también la demo que vende (PLAN.md §5).

## 3. Procesos detallados y casos de prueba

### P1. Causación de facturas de compra (el corazón del producto)

**Disparador:** llega una factura electrónica de un proveedor (XML vía DIAN o correo) o un documento físico/PDF.

**Cómo lo hace el auxiliar humano:**
1. Descarga el XML del portal DIAN (o lo recibe por correo del proveedor).
2. Verifica que la factura sea válida: que esté timbrada por la DIAN, que el NIT del emisor coincida con el proveedor, que los cálculos de IVA sean correctos.
3. Consulta el RUT del proveedor para conocer su régimen (responsable de IVA, gran contribuyente, autorretenedor, régimen simple).
4. Determina la cuenta PUC de gasto/costo según el concepto (ej.: papelería → 5195, honorarios → 5110, arriendo → 5120, inventario → 1435).
5. Calcula las retenciones que aplican según el régimen del proveedor y las bases mínimas vigentes (retefuente por concepto, reteIVA si aplica, reteICA según municipio).
6. Registra el asiento en el software contable: débito al gasto/costo + IVA descontable, crédito a cuentas por pagar y a las retenciones.
7. Emite el acuse de recibo del documento electrónico (evento RADIAN) dentro del plazo.
8. Archiva el soporte vinculado al asiento.

**Resultado:** asiento balanceado en el software contable, con tercero, cuentas PUC, impuestos y retenciones correctos; soporte archivado; acuse emitido.

**Controles del auxiliar (la app debe replicarlos):** débitos = créditos; el IVA del XML coincide con el calculado; la retención respeta base mínima y tarifa vigente; no causar dos veces la misma factura (CUFE duplicado).

**Casos de prueba:**

| # | Escenario | Entrada | Resultado esperado |
|---|---|---|---|
| P1.1 | Factura estándar de servicios | XML real de honorarios de un proveedor persona natural declarante | Asiento con 5110, IVA descontable, retefuente 10/11%, balanceado |
| P1.2 | Compra de inventario | XML de compra de mercancía | Clasifica a 1435 (no a gasto), retefuente compras 2.5% si supera base |
| P1.3 | Proveedor régimen simple | XML de proveedor inscrito en RST | **No** practica retefuente (el RST no es sujeto de retención) |
| P1.4 | Factura bajo la base mínima | XML de servicios por menos de 4 UVT | No calcula retención; asiento sin cuentas 2365 |
| P1.5 | XML duplicado | El mismo XML (mismo CUFE) dos veces | La segunda se rechaza con aviso "ya causada", no crea asiento doble |
| P1.6 | XML malformado o corrupto | Archivo XML inválido / no UBL | Error claro al usuario, sin crash, sin asiento a medias (también prueba de seguridad: XXE) |
| P1.7 | Concepto ambiguo | Factura cuyo concepto admite 2+ cuentas PUC | Va a bandeja de revisión como "sugerida", no se causa automática |
| P1.8 | Volumen | 100 XML de un mes real en lote | Todas procesadas; ≥85% aceptadas sin corrección; <30 seg de revisión c/u (métricas PLAN.md §9) |
| P1.9 | Export/API | Asiento aprobado | Llega correcto a Alegra vía API (cuenta de prueba) y el CSV formato Siigo importa sin errores |
| P1.10 | Factura física fotografiada | Foto de una factura de papel (o PDF escaneado) tomada con el celular | La IA de visión extrae los campos (NIT, fecha, número, totales, concepto), el usuario los confirma en un formulario editable y entra al flujo normal de causación **siempre como "sugerida"** (nunca automática por venir de OCR); antiduplicado por NIT+número+fecha al no haber CUFE |

### P2. Causación de ventas (ingresos)

**Disparador:** la empresa emite facturas de venta (las genera su software de facturación, no la app).

**Cómo lo hace el auxiliar:** descarga las facturas emitidas desde la DIAN, verifica el consecutivo completo (que no falte ninguna), registra el ingreso (crédito 4135/41xx + IVA generado, débito a cartera 1305), y aplica las retenciones que **le practicaron** a la empresa como anticipo de impuestos (1355).

**Casos de prueba:**

| # | Escenario | Entrada | Resultado esperado |
|---|---|---|---|
| P2.1 | Venta estándar | XML de factura emitida | Asiento: 1305 débito, 4135 + 2408 crédito |
| P2.2 | Cliente gran contribuyente retuvo | Factura donde el cliente practica retefuente | La retención queda en 1355 (anticipo), cartera por el neto |
| P2.3 | Hueco en consecutivo | Mes con la factura FE-105 faltante entre FE-104 y FE-106 | Alerta: "falta la factura FE-105" |
| P2.4 | Nota crédito | XML de nota crédito sobre una venta ya causada | Reversa parcial/total vinculada a la factura original |

### P3. Verificación de retenciones por tercero (motor de reglas)

**Disparador:** cada causación (es transversal a P1/P2), y la actualización anual de UVT y tarifas.

**Cómo lo hace el auxiliar:** mantiene una "matriz de terceros" con el régimen de cada proveedor (a partir del RUT); ante cada factura consulta: ¿qué concepto es? ¿supera la base mínima en UVT? ¿qué tarifa aplica? ¿el proveedor es autorretenedor o RST? ¿aplica reteICA en este municipio y a qué tarifa por mil?

**Casos de prueba:**

| # | Escenario | Entrada | Resultado esperado |
|---|---|---|---|
| P3.1 | Cambio de año fiscal | La misma factura con fecha 2025 vs. 2026 | Usa el valor de UVT del año correcto |
| P3.2 | Autorretenedor | Factura de proveedor con calidad de autorretenedor en el RUT | No practica retefuente; lo indica en la explicación |
| P3.3 | ReteICA multi-municipio | Mismo servicio prestado en Medellín vs. Bogotá | Tarifa por mil del municipio correcto |
| P3.4 | Explicabilidad | Cualquier retención calculada | La app muestra el porqué: concepto, base, tarifa, norma — el contador puede verificar sin recalcular |

### P4. Conciliación bancaria

**Disparador:** llega el extracto bancario del mes (PDF o CSV).

**Cómo lo hace el auxiliar:**
1. Descarga el extracto de cada cuenta bancaria.
2. Cruza cada movimiento del extracto contra los registros contables (libro auxiliar de bancos): pagos a proveedores, consignaciones de clientes, cheques girados.
3. Identifica partidas conciliatorias: consignaciones sin identificar, cheques pendientes de cobro, comisiones y gravámenes (4x1000) no registrados, rechazos.
4. Registra los asientos faltantes (comisiones, GMF, rendimientos) y deja documentadas las partidas pendientes.
5. Produce el formato de conciliación: saldo en libros vs. saldo en extracto, con las partidas que explican la diferencia.

**Casos de prueba:**

| # | Escenario | Entrada | Resultado esperado |
|---|---|---|---|
| P4.1 | Mes limpio | Extracto CSV + asientos que cruzan 1:1 | 100% conciliado automático, diferencia $0 |
| P4.2 | Comisiones sin registrar | Extracto con comisiones y 4x1000 no contabilizados | Los detecta, propone los asientos de gasto bancario |
| P4.3 | Consignación sin identificar | Depósito que no coincide con ninguna factura | Va a excepciones con sugerencia del cliente más probable (por valor/fecha) |
| P4.4 | Pago parcial | Cliente paga el 50% de una factura | Sugiere aplicación parcial, no fuerza el cruce total |
| P4.5 | Extracto PDF | El mismo extracto en PDF en vez de CSV | La extracción produce los mismos movimientos |
| P4.6 | Cuadre final | Cierre de la conciliación | El formato saldo libros vs. extracto cuadra exactamente con las partidas listadas |

### P5. Cartera y seguimiento de cobros

**Disparador:** semanal + vencimiento de cada factura de venta.

**Cómo lo hace el auxiliar:** mantiene el aging de cartera (corriente, 30, 60, 90+ días), envía estados de cuenta y recordatorios a clientes morosos, registra los pagos recibidos y los aplica a facturas específicas.

**Casos de prueba:**

| # | Escenario | Entrada | Resultado esperado |
|---|---|---|---|
| P5.1 | Aging correcto | Facturas con fechas de vencimiento variadas | Reporte de edades clasifica cada una en el rango correcto |
| P5.2 | Recordatorio automático | Factura vence hace 5 días | Correo/WhatsApp al cliente con el estado de cuenta, según configuración del tenant |
| P5.3 | No acosar | Cliente que ya pagó ayer | No le llega recordatorio (el pago aplicado detiene la secuencia) |

### P6. Monitoreo de facturación electrónica y calendario tributario

**Disparador:** diario (monitoreo DIAN) + fechas según los últimos dígitos del NIT (calendario).

**Cómo lo hace el auxiliar:** revisa que las facturas emitidas hayan sido aceptadas (no rechazadas) por la DIAN, emite eventos RADIAN de los documentos recibidos, y lleva el control de vencimientos: IVA, retefuente mensual, ICA, renta, exógena, renovación de matrícula — cada uno según el NIT.

**Casos de prueba:**

| # | Escenario | Entrada | Resultado esperado |
|---|---|---|---|
| P6.1 | Calendario por NIT | Dos tenants con NIT terminados en dígitos distintos | Cada uno ve **sus** fechas 2026, no las del otro |
| P6.2 | Alerta anticipada | Vencimiento de retefuente en 5 días | Alerta por correo con días de anticipación configurables |
| P6.3 | Rechazo DIAN | Factura emitida rechazada | Alerta el mismo día con el motivo del rechazo |

### P7. Cierre mensual y paquete para el contador (el entregable que valida todo)

**Disparador:** fin de mes.

**Cómo lo hace el auxiliar:** verifica que todo el mes esté causado, la conciliación cerrada, las retenciones cuadradas (el saldo de 2365/2367 coincide con lo que se declarará), y entrega al contador los auxiliares por cuenta y por tercero con sus soportes organizados.

**Casos de prueba (prueba de aceptación integral — la más importante):**

| # | Escenario | Entrada | Resultado esperado |
|---|---|---|---|
| P7.1 | **Mes completo real** | Todos los documentos de un mes de una empresa real (XML compras+ventas, extracto, RUT de terceros) | Al cerrar: todo causado o en bandeja con motivo, conciliación cuadrada, carpeta del período con soportes descargable, cifras que un contador real firma |
| P7.2 | Cuadre de retenciones | El mes cerrado | Suma de retenciones practicadas = saldo de las cuentas 2365/2367 = base del formulario 350 |
| P7.3 | Aislamiento multi-tenant | Dos empresas cerrando el mismo mes | Ningún dato cruzado; test automatizado de acceso cruzado pasa (PLAN.md §10.3) |

### P8. Nómina (fase 4 — núcleo primero, lo regulatorio después)

**Disparador:** fin de mes (liquidación) + novedades del período.

**Cómo lo hace el auxiliar:** mantiene la planta de personal con salario y
fecha de ingreso; cada mes liquida: devengado (salario + auxilio de transporte
si gana ≤ 2 SMMLV), deducciones del empleado (salud 4%, pensión 4%), neto a
pagar, aportes del empleador (pensión 12%, ARL, caja 4%, y salud/SENA/ICBF
solo si la empresa no está exonerada por art. 114-1 E.T. o el salario es
≥ 10 SMMLV) y provisiones de prestaciones (cesantías, intereses, prima,
vacaciones). Registra el asiento y prepara los totales para PILA. **La app
liquida y propone; el humano aprueba; la PILA y la nómina electrónica DIAN
las presenta el humano (v1 no presenta nada ante entidades).**

**Casos de prueba:**

| # | Escenario | Entrada | Resultado esperado |
|---|---|---|---|
| P8.1 | Salario mínimo | Empleado con 1 SMMLV | Con auxilio de transporte; deducciones 8%; neto correcto al peso |
| P8.2 | Salario alto | Empleado con 3 SMMLV | Sin auxilio de transporte |
| P8.3 | Exoneración 114-1 | Empresa exonerada vs no exonerada | La exonerada no aporta salud 8.5% ni SENA/ICBF (para salarios < 10 SMMLV); la no exonerada sí |
| P8.4 | Asiento balanceado | Liquidación del mes | Débitos (gasto de personal) = créditos (neto + aportes por pagar + provisiones) |
| P8.5 | Un mes, una liquidación | Liquidar dos veces el mismo mes | La segunda se rechaza: ya existe |
| P8.6 | Humano en el circuito | Liquidación creada | Queda pendiente; nada se contabiliza sin aprobación |
| P8.7 | Parámetros por año | SMMLV/auxilio del año correcto | Cambiar de año usa los valores de ese año (VERIFICAR contra decretos) |
| P8.8 | Novedades | Horas extra, incapacidades, días no laborados, bonos | La liquidación del mes aplica cada novedad: recargos que suman al devengado, descuentos por días no laborados/incapacidad, bonos (constitutivos o no de salario); el asiento sigue cuadrando |
| P8.9 | Nómina electrónica DIAN y pre-PILA | Liquidación aprobada | *Pendiente: exportes para el operador de PILA y el proveedor de nómina electrónica* |

### P9. Certificados de retención en la fuente (fase 3 — el trámite de febrero)

**Disparador:** cada febrero, el proveedor pide su certificado del año
anterior; también lo exige la conciliación del formulario 350.

**Cómo lo hace el auxiliar:** por cada tercero al que se le practicó
retención, suma en el año (por concepto: honorarios, servicios, compras,
arrendamiento) las bases y las retenciones de todas las facturas causadas, y
emite el certificado con el total. Es la misma cifra que declara la empresa
como agente retenedor. La app agrega desde las facturas aprobadas — cero
digitación.

**Casos de prueba:**

| # | Escenario | Entrada | Resultado esperado |
|---|---|---|---|
| P9.1 | Certificado por tercero | Un proveedor con varias facturas retenidas en el año | Suma bases y retenciones por concepto; total correcto al peso |
| P9.2 | Solo lo aprobado y del año | Facturas pendientes o de otro año | No entran en el certificado |
| P9.3 | Descuenta notas crédito | Compra retenida con nota crédito posterior | La base neta refleja la reversa |
| P9.4 | Cuadre con el 350 | Suma de todos los certificados del año | = total de créditos a las cuentas 2365 del período |
| P9.5 | Sin retención | Proveedor RST o bajo base mínima | No aparece en el listado de certificados |

### P8. Procesos de fases posteriores (probar cuando lleguen)

**Caja menor (F3):** foto de recibos → OCR → paquete de legalización que cuadra con el monto del fondo. **Activos fijos (F3):** depreciación mensual automática, línea recta, meses correctos. **Certificados de retención (F3):** generación masiva anual por tercero; los valores cuadran con los auxiliares. **Exógena (F3):** pre-armado de formatos 1001/1007/2276; los totales cruzan contra la contabilidad. **Nómina (F4):** novedades → liquidación con provisiones; pre-PILA cuadra con la planilla del operador.

## 4. Datos de prueba necesarios (conseguir antes de la semana 1)

**Beta cero: la propia empresa de Luis, que factura con Siigo.** El kit sale de ahí, sin depender de terceros:

1. **XML de ventas:** las facturas emitidas por Siigo (descargables de Siigo o del portal DIAN con el NIT propio).
2. **XML de compras:** descarga de documentos recibidos en el portal DIAN del mismo NIT (sirve además como spike de la descarga DIAN).
3. **Extracto bancario** del mismo período (PDF y CSV).
4. **RUT propio y de 10+ proveedores/clientes** frecuentes.
5. **Destino contable de prueba:** cuenta gratuita de Alegra (su API pública es la primera integración). El plan de facturación Siigo de Luis no incluye API, así que Siigo se valida vía export CSV; la prueba API-Siigo se hará con el primer beta que tenga plan Nube con credenciales.

Para variedad que la empresa propia no cubra (proveedores RST, autorretenedores, notas crédito), completar después con el mes de un contador aliado — ese mes será también la demo de venta.

## 5. Reglas de evaluación

- Cada caso de prueba se ejecuta con datos reales anonimizados, nunca solo con datos inventados.
- Un caso pasa cuando **un contador humano valida el resultado**, no cuando el código no arroja error.
- Las métricas del PLAN.md §9 se miden aquí: ≥85% de clasificaciones aceptadas sin corrección (P1.8), <30 seg de revisión por documento (P1.8), mes completo firmable (P7.1).
- Todo caso fallido produce una entrada en el backlog con el XML/documento que lo hizo fallar — esa colección de casos difíciles es un activo del producto.
