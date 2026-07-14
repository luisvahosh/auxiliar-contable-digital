# Derrotero de validación con el contador — Auxiliar Contable Digital

Guion para sentarte con el contador y que **valide el criterio** de la
herramienta: no que "funcione", sino que lo que propone esté **bien contable y
tributariamente** para Colombia 2026. Al final hay una lista de **decisiones que
solo el contador puede confirmar** — es lo más importante de la sesión.

**Dónde probar:** producción **https://auxcontable.learnway.co** (o local
`http://127.0.0.1:8000`). Datos de ejemplo en `datos-prueba/`.

**Principio a recordarle al contador:** la app **ASISTE al auxiliar, no
reemplaza** a Alegra/Siigo ni al software de nómina. Todo lo que propone es un
**borrador con humano en el circuito** — nada se contabiliza ni se presenta ante
la DIAN/PILA sin que una persona lo apruebe.

**Valores 2026 ya verificados contra fuentes oficiales** (confirmar con el contador):
- UVT $52.374 — Resolución DIAN 000238 del 15-dic-2025.
- SMMLV $1.750.905 y auxilio de transporte $249.095 — Decretos 1469/1470 de 2025.

---

## Bloque A — Causación de compras (P1): el corazón del trabajo

### A1. Honorarios de persona natural (`P1.1-factura-honorarios.xml`)
- [ ] Subir factura → sale propuesta **Automática**, queda **Pendiente**.
- [ ] Asiento propuesto:
  | Cuenta | Débito | Crédito |
  |---|---:|---:|
  | 5110 Honorarios | $2.000.000 | |
  | 240802 IVA descontable | $380.000 | |
  | 236515 Retefuente honorarios | | $200.000 |
  | 2335 Costos y gastos por pagar | | $2.180.000 |
- [ ] **Criterio a validar por el contador:** retención de honorarios **10%**
  por ser **persona natural** (11% si supera 3.300 UVT acumuladas). Sumas iguales.

### A2. Compra de inventario (`P1.2-factura-inventario.xml`)
- [ ] Cuenta **1435 Mercancías** (activo, no gasto); contrapartida **2205 Proveedores**.
- [ ] Retefuente **compras 2.5%** porque la base supera **27 UVT**.
- [ ] **Validar:** ¿la base mínima de compras y la tarifa son las que el contador aplica?

### A3. Proveedor de Régimen Simple — RST (`P1.3-factura-regimen-simple.xml`)
- [ ] **NO se practica retefuente** (al RST no se le retiene).
- [ ] **Validar:** este es el error clásico del practicante; confirmar el criterio.

### A4. Compra bajo la base mínima (`P1.4-factura-bajo-base-minima.xml`)
- [ ] La base no supera la cuantía mínima → **sin retención**.
- [ ] **Validar:** la cuantía mínima en UVT del concepto.

### A5. Duplicados y seguridad (`P1.5` y `P1.6a/6b`)
- [ ] Subir de nuevo la misma factura (`P1.5...`) → **rechazada por CUFE duplicado**
  (no se contabiliza dos veces).
- [ ] `P1.6a` (XML corrupto) y `P1.6b` (XML con XXE) → **rechazados con mensaje claro**
  (defensa de seguridad; el contador no ve datos financieros expuestos).

### A6. Concepto ambiguo (`P1.7-factura-concepto-ambiguo.xml`)
- [ ] Sale como **Sugerida** (no Automática) porque el concepto no es claro.
- [ ] Se puede **Reclasificar** eligiendo la cuenta correcta → recalcula retención y
  vuelve como **Manual** con el motivo. **Validar:** el criterio de reclasificación.

### A7. Nota crédito de proveedor (`P1-nc-proveedor.xml`)
- [ ] Reversa vinculada a su factura original; **advierte el ajuste de retefuente**.

### A8. Factura de papel por foto (`P1.10-factura-fisica.png`) — opcional
- [ ] Subir factura → **Causar desde una foto** → la IA lee los campos → confirmar
  campo por campo → entra **siempre como Sugerida** (nunca automática).

---

## Bloque B — Ventas (P2)
- [ ] `P2.1-venta-estandar.xml` → asiento de venta: **1305** cartera, **4135** ingreso,
  **240801** IVA generado. **Validar** cuentas de ingreso e IVA generado.
- [ ] `P2.2-venta-cliente-retiene.xml` → el cliente practica retención → queda en
  **135515** (retefuente a favor). Sumas iguales.
- [ ] `P2.4-nota-credito.xml` → nota crédito vinculada a la venta original.
- [ ] Al subir la segunda venta, avisa el **hueco en el consecutivo** (falta FE-105).

---

## Bloque C — Matriz de terceros (P3)
- [ ] `/causacion/terceros/` — cada proveedor se creó solo con su primera factura,
  con su calidad tributaria (declarante / autorretenedor / RST / verificado).
- [ ] `P3.2-factura-autorretenedor.xml` → al autorretenedor **no se le practica**
  retención (la matriz manda sobre el XML). **Validar** el criterio.

---

## Bloque D — Conciliación bancaria (P4)
- [ ] **Bancos** → subir `P4-extracto-junio.csv` (o el `.pdf`).
- [ ] Cruza pagos de clientes (por el neto de cartera), pagos a proveedores y
  gastos bancarios (**530505 / 531595**) con asiento propuesto.
- [ ] Las partidas sin match quedan como **excepción con el candidato más probable**.
- [ ] **Validar:** el formato de cuadre y el tratamiento de gastos bancarios.

---

## Bloque E — Cartera y cobro (P5)
- [ ] **Cartera** → saldo por cliente = neto − pagos conciliados − notas crédito;
  edades por vencimiento del XML o 30 días. **Validar** los rangos de edades.

---

## Bloque F — Calendario tributario (P6) y Monitoreo DIAN (P6.3)
- [ ] **Calendario** → las fechas 2026 salen según el **último dígito del NIT**.
  ⚠ **Validar contra el calendario oficial 2026** (hoy es una semilla ESTIMADA).
- [ ] **Monitoreo DIAN** → subir `respuestas-dian/P6.3-rechazo-dian.xml` (la
  respuesta de la DIAN sobre la factura FE-104): la factura queda **RECHAZADA**
  con el motivo, destacada en rojo. Subir `P6.3-aceptacion-dian.xml` → **Aceptada**.
  ⚠ **Validar los códigos ResponseCode** de aceptación/rechazo contra la resolución.

---

## Bloque G — Cierre mensual y cuadre de retenciones (P7) · el entregable clave
- [ ] **Cierre mensual** → checklist del período: pendientes con motivo,
  conciliación, y **cuadre de retenciones**.
- [ ] **Validar lo más importante:** la suma de retenciones practicadas = saldo de
  **2365/2367** = base del **formulario 350**. Este cuadre es lo que el contador firma.
- [ ] **Descargar el paquete ZIP del contador**: resumen, auxiliares por cuenta y
  por tercero, Siigo consolidado, partidas conciliatorias y soportes (XML + fotos).
- [ ] **Pregunta al contador:** ¿este paquete es lo que necesitas para revisar y
  declarar? ¿Falta algún auxiliar o formato?

---

## Bloque H — Nómina (P8) y exportes para el operador (P8.9)
- [ ] **Nómina** → cargar `P8-empleados.csv` (carga masiva) → **Liquidar** el mes.
- [ ] Revisar la liquidación: devengado (salario + auxilio si ≤ 2 SMMLV),
  deducciones 4% salud + 4% pensión, aportes patronales (con/ sin **exoneración
  art. 114-1**), provisiones. Asiento cuadrado. Queda **Pendiente** → **Aprobar**.
- [ ] Con la liquidación aprobada, **descargar los exportes para el operador**:
  **pre-PILA** (IBC + aportes por empleado) y **resumen de nómina electrónica**.
- [ ] **Recordarle al contador:** la app **no presenta** PILA ni nómina electrónica
  — son borradores para el operador. La **retención en la fuente de nómina no la
  calcula** la app (la completa el operador). **Validar** los porcentajes de aportes.

---

## Bloque I — Certificados de retención (P9)
- [ ] **Terceros → Certificados** → por tercero y concepto, agregados del año desde
  las compras aprobadas. **Validar:** el total cuadra con los créditos a **2365**.

---

## Bloque J — Activos fijos (P10) y caja menor (P11)
- [ ] **Activos fijos** → alta de un activo → **depreciación línea recta** mensual,
  topada al valor depreciable, sin depreciar antes de adquirir. **Validar** vidas útiles.
- [ ] **Caja menor** → fondo fijo, vales por categoría, **reembolso** que legaliza los
  vales (gastos + IVA vs bancos). El efectivo disponible nunca excede el fondo.

---

## Bloque K — Exógena pre-armada (P12)
- [ ] **Exógena** → **Formato 1001** (pagos y retenciones a terceros, con concepto
  DIAN; las notas crédito descuentan), **Formato 1007** (ingresos por cliente) y
  **Formato 2276** (rentas de trabajo por empleado, desde las nóminas aprobadas).
- [ ] Descargar los CSV para el prevalidador.
- [ ] ⚠ **Validar:** los **conceptos y casillas** de 1001/1007/2276 contra la
  **resolución de exógena del año** (los códigos cambian). Los totales deben cruzar
  contra la contabilidad.

---

## Bloque L — Informes (P13)
- [ ] **Balance y estados** → balance de comprobación (con verificación de cuadre),
  estado de resultados y libro mayor, consolidando los asientos de **todos** los
  módulos. **Validar** la clasificación por clases PUC (4/5/6) y el cuadre.

---

## Bloque M — Asistente normativo (IA)
- [ ] **Asistente IA** → preguntar p. ej. *"¿qué retención aplica a un pago a un
  abogado?"* → responde citando el **artículo** y con **disclaimer**.
- [ ] **Pedirle al contador** que revise 3–4 respuestas: son un corpus curado de 12
  fichas; él puede ampliarlo/corregirlo con el texto oficial.

---

## ⭐ Decisiones que necesito que el contador confirme (lo esencial)

1. **Criterios de retención en la fuente** (Bloques A–C): tarifas, bases mínimas en
   UVT, tratamiento de RST y autorretenedores. ¿El motor aplica lo correcto?
2. **Calendario tributario 2026** (P6): hoy es una **semilla estimada** —
   reemplazarla por las fechas oficiales por último dígito del NIT.
3. **Códigos ResponseCode de la DIAN** (P6.3): confirmar cuáles significan
   aceptación vs rechazo en el ApplicationResponse.
4. **Cuadre de retenciones y paquete del contador** (P7): ¿el ZIP y el cuadre
   2365/2367 vs formulario 350 son suficientes para declarar?
5. **Aportes y parámetros de nómina** (P8): porcentajes de salud/pensión/parafiscales,
   exoneración 114-1, y confirmar SMMLV/auxilio 2026.
6. **Conceptos y casillas de exógena** 1001/1007/2276 (P12) contra la resolución anual.
7. **Plan de cuentas PUC**: revisar que las cuentas por defecto coincidan con el plan
   que usan los clientes (es personalizable por empresa).

> Anota junto a cada punto la respuesta del contador. Cada corrección entra como
> ajuste del producto — con eso la herramienta queda lista para clientes reales.
