# Derrotero de pruebas — Causación (P1) como lo vive un auxiliar contable

Guion paso a paso para probar la plataforma tú mismo, en el orden y con el
criterio con que trabaja un auxiliar contable real. Los archivos están en
`datos-prueba/`. La app corre en **http://127.0.0.1:8000**.

Marca cada paso solo si ves **exactamente** el resultado esperado; si algo no
cuadra, anótalo — cada caso fallido es backlog del producto.

---

## Preparación (una sola vez)

- [ ] Abrir http://127.0.0.1:8000 — se ve la página de inicio con el botón
  **"Subir factura XML"** y el enlace a la **bandeja de causación**.
- [ ] Entrar a **Causación**: la bandeja está vacía ("Aún no hay facturas causadas").

---

## Paso 1 — Llega la factura de honorarios del contador (P1.1)

*Escenario real: tu contador externo (persona natural) pasa su cuenta de
cobro electrónica del mes: $2.000.000 + IVA.*

- [ ] **Subir factura** → seleccionar `P1.1-factura-honorarios.xml` → **Procesar factura**.
- [ ] La propuesta sale como **Automática** y queda **Pendiente de aprobación**
  (la app nunca contabiliza sola).
- [ ] Revisar el asiento como lo haría el auxiliar:
  | Cuenta | | Débito | Crédito |
  |---|---|---:|---:|
  | 5110 Honorarios | | $2.000.000 | |
  | 240802 IVA descontable | | $380.000 | |
  | 236515 Retefuente honorarios | | | $200.000 |
  | 2335 Costos y gastos por pagar | | | $2.180.000 |
- [ ] **Controles:** sumas iguales ($2.380.000 = $2.380.000); la retención es el
  10% porque el emisor es persona natural; la explicación ("Por qué se propone
  así") lo dice con palabras.
- [ ] **Aprobar asiento** → el estado pasa a **Aprobada**.

## Paso 2 — Llega mercancía del proveedor (P1.2)

*Escenario: compraste inventario para revender ($5.600.000 + IVA). El error
clásico del practicante es mandarlo al gasto; va al inventario.*

- [ ] Subir `P1.2-factura-inventario.xml`.
- [ ] La cuenta propuesta es **1435 Mercancías** (activo, no gasto) y la
  contrapartida es **2205 Proveedores**.
- [ ] Retefuente **compras al 2.5% = $140.000** (la base $5.600.000 supera las
  27 UVT). Verificar sumas iguales y aprobar.

## Paso 3 — La factura del aseo: proveedor de Régimen Simple (P1.3)

*Escenario: la empresa de aseo está inscrita en el RST. Un auxiliar que no
mire el régimen le retendría — y eso genera reclamo del proveedor.*

- [ ] Subir `P1.3-factura-regimen-simple.xml`.
- [ ] El asiento **no tiene ninguna cuenta 2365** (sin retención) y la
  explicación dice el porqué: RST no es sujeto de retención (art. 911 E.T.).
- [ ] El crédito a 2335 es por el **total** ($1.785.000). Aprobar.

## Paso 4 — Servicio pequeño, bajo la base mínima (P1.4)

*Escenario: arreglo de la impresora por $150.000. Servicios solo se retiene
desde 4 UVT; retener aquí sería un error.*

- [ ] Subir `P1.4-factura-bajo-base-minima.xml`.
- [ ] Cuenta **5145 Mantenimiento**, **sin retención**, y la explicación
  muestra la cuenta: base $150.000 < base mínima de 4 UVT. Aprobar.

## Paso 5 — El proveedor reenvía la misma factura (P1.5)

*Escenario: el proveedor manda dos veces el correo con su factura. Causarla
doble infla gastos y cuentas por pagar — control clave del auxiliar.*

- [ ] Subir `P1.5-factura-duplicada-mismo-cufe.xml` (es la misma P1.1, mismo CUFE).
- [ ] La app la **rechaza con el aviso "ya fue causada"**, no crea asiento
  doble y te lleva a la factura original. En la bandeja sigue habiendo
  **una sola** FVS-847.

## Paso 6 — Archivos dañados o maliciosos (P1.6)

*Escenario: descargas corruptas o un XML manipulado. La app debe fallar con
elegancia, nunca a medias.*

- [ ] Subir `P1.6a-xml-malformado.xml` → mensaje de error claro ("no es un XML
  bien formado"), sin pantalla de error de Django, y la bandeja **no** tiene
  registros nuevos.
- [ ] Subir `P1.6b-xml-xxe.xml` → rechazado **por seguridad** (intento de leer
  archivos del equipo vía XXE). Nada del contenido del disco aparece en pantalla.

## Paso 7 — El caso que ni el auxiliar resuelve solo (P1.7)

*Escenario: "suministro e instalación de aire acondicionado" — ¿activo fijo
que se deprecia o gasto de mantenimiento? Eso lo decide un humano.*

- [ ] Subir `P1.7-factura-concepto-ambiguo.xml`.
- [ ] La propuesta sale como **Sugerida** (no automática) y la explicación
  lista las cuentas candidatas y por qué es ambigua.
- [ ] Decidir tú: **Aprobar** (aceptas la propuesta) o **Rechazar** (quedará
  para reclasificación manual — llega en la siguiente iteración).

## Cierre — revisión de bandeja

- [ ] La bandeja muestra las 6 facturas con su cuenta, nivel (automática/
  sugerida) y estado, con cifras en números tabulares alineados.
- [ ] Criterio de la guía (P1.8): ¿cuánto te tomó revisar cada factura?
  La meta es **< 30 segundos por documento**.

---

## Qué NO hace todavía (siguiente paso del vertical)

- Envío del asiento aprobado a **Alegra vía API** y **export CSV formato Siigo** (P1.9).
- Matriz de terceros con el RUT real (declarante/autorretenedor — P3).
- Reclasificación manual de las rechazadas.
