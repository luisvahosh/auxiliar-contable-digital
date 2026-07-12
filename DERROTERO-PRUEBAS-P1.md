# Derrotero de pruebas — Causación (P1, P2 y P3) como lo vive un auxiliar contable

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

## Paso 8 — Llevar el asiento al software contable (P1.9)

*Escenario: el asiento ya está aprobado; ahora debe quedar en la contabilidad
oficial (Siigo por archivo, Alegra por API).*

- [ ] Entrar a una factura **Aprobada** (por ejemplo la FVS-847 del paso 1):
  aparece la sección **"Llevar al software contable"**.
- [ ] **Descargar CSV Siigo** → baja `siigo-FVS-847.csv`. Abrirlo en Excel:
  un renglón por movimiento del asiento, con cuenta, NIT del tercero,
  débito y crédito. *(La primera importación real a Siigo dirá si hay que
  ajustar columnas a la plantilla oficial.)*
- [ ] **Enviar a Alegra** sin credenciales configuradas → la app avisa con
  claridad que faltan `ALEGRA_EMAIL` y `ALEGRA_TOKEN` en el `.env`, sin romperse.
- [ ] *(Cuando tengas la cuenta de Alegra)*: poner las credenciales en el
  `.env`, reiniciar, registrar el mapeo de cuentas PUC → Alegra en
  http://127.0.0.1:8000/admin (Mapeos de cuenta Alegra) y reenviar: debe
  quedar el aviso "✔ Enviada a Alegra — asiento #…". Reenviar no duplica.

## Paso 9 — Registrar las ventas del mes (P2.1)

*Escenario: tu empresa facturó formación corporativa por $3.000.000 + IVA.
El auxiliar registra el ingreso y la cartera del cliente.*

- [ ] **Subir factura** → `P2.1-venta-estandar.xml`. La app detecta sola que
  es una **venta** (tu empresa es la emisora) y la manda a la bandeja de
  **Ventas** (enlace nuevo del menú).
- [ ] El asiento: débito **1305 Clientes** $3.570.000; crédito **4135
  Ingresos** $3.000.000 y **240801 IVA generado** $570.000. Aprobar.

## Paso 10 — El cliente grande te retuvo (P2.2) y falta una factura (P2.3)

*Escenario: una gran superficie te compró un diplomado y te practicó
retefuente del 4%. Además, entre FE-104 y FE-106 no aparece la FE-105.*

- [ ] Subir `P2.2-venta-cliente-retiene.xml`.
- [ ] En el asiento, la retención que te practicaron queda como anticipo a tu
  favor: débito **135515** $320.000, y la cartera va por el **neto**
  ($9.200.000). El ingreso completo se acredita ($8.000.000 + IVA).
- [ ] Al procesarla aparece la **alerta: "falta FE-105"** — y queda visible
  en la bandeja de Ventas. Así se detecta una factura anulada o no
  descargada antes de que la DIAN pregunte.

## Paso 11 — Nota crédito: un cliente devolvió parte (P2.4)

*Escenario: un participante se retiró del programa de FE-104 y se emitió la
nota crédito NC-12 por $595.000.*

- [ ] Subir `P2.4-nota-credito.xml`.
- [ ] La app la vincula a **FE-104** (visible en el detalle: "Reversa a
  FE-104") y propone la reversa: débito 4135 $500.000 + 240801 $95.000,
  crédito 1305 $595.000. La explicación dice que es **parcial**.
- [ ] Verificación extra: si intentas subir la NC **antes** que su factura
  (en una base limpia), la app la rechaza pidiendo la original primero.

## Paso 12 — El proveedor autorretenedor (P3.2)

*Escenario: una consultora grande tiene calidad de autorretenedor en su RUT
(responsabilidad O-15): retenerle sería un error que ella reclamaría.*

- [ ] Subir `P3.2-factura-autorretenedor.xml` ($6.000.000 + IVA de consultoría).
- [ ] El asiento **no tiene retención** (crédito 2335 por el total $7.140.000)
  y la explicación dice que el proveedor es **autorretenedor**.

## Paso 13 — La matriz de terceros (P3)

*Escenario: el auxiliar mantiene una ficha por proveedor con su calidad
tributaria según el RUT. La app la construye sola y tú la verificas.*

- [ ] Abrir **Terceros** en el menú: están todos los proveedores de las
  facturas que has subido, marcados **"Pendiente"** de verificar contra el RUT.
- [ ] Entrar a **Editar** en Carlos Andrés Pérez (el contador de P1.1):
  su calidad se cotejaría con el RUT real; marca **"Verificado contra el RUT"**
  y guarda.
- [ ] Prueba de que la matriz manda sobre el XML: edita un proveedor y márcalo
  **Régimen Simple** — su próxima factura ya no llevará retención aunque el
  XML no diga nada (la explicación citará "la matriz de terceros").
- [ ] Nota: si un proveedor queda **"No declarante"**, la tarifa de servicios
  sube del 4% al 6% y la de compras del 2.5% al 3.5% automáticamente.

## Cierre — revisión de bandeja

- [ ] La bandeja muestra las 6 facturas con su cuenta, nivel (automática/
  sugerida) y estado, con cifras en números tabulares alineados.
- [ ] Criterio de la guía (P1.8): ¿cuánto te tomó revisar cada factura?
  La meta es **< 30 segundos por documento**.

---

## Qué NO hace todavía (siguientes pasos)

- Validación del CSV contra una importación real en Siigo y del envío con una
  cuenta real de Alegra (falta crear la cuenta y poner credenciales en `.env`).
- Matriz de terceros con el RUT real (declarante/autorretenedor — P3).
- Reclasificación manual de las rechazadas.
