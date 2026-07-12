# Derrotero de pruebas — P1 a P7, como lo vive un auxiliar contable

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

## Paso 14 — Llega el extracto del banco (P4)

*Escenario: fin de mes. El auxiliar cruza cada movimiento del extracto contra
lo que está en libros: pagos de clientes, pagos a proveedores y los cobros
del banco que nadie registró.*

Requisito: tener **aprobadas** la FVS-847 (paso 1), la FE-104 (paso 9) y la
FE-106 (paso 10) — el extracto se cruza contra lo aprobado.

- [ ] Abrir **Bancos** en el menú → subir `P4-extracto-junio.csv`
  (o su gemelo `P4-extracto-junio.pdf` — el PDF de texto del banco produce
  exactamente los mismos movimientos, caso P4.5).
- [ ] Revisar las sugerencias movimiento por movimiento:
  - **$3.570.000 Comercializadora Andina** → cruce exacto con FE-104 (pago de cliente).
  - **$4.600.000 Grandes Superficies** → **pago parcial** de FE-106 (neto
    $9.200.000): propone aplicar solo lo pagado, el saldo queda en cartera (P4.4).
  - **-$2.180.000 Carlos Pérez** → pago del neto de la FVS-847 (pago a proveedor).
  - **-$14.900 cuota de manejo** y **-$35.000 GMF** → gastos bancarios no
    registrados: proponen su asiento (530505 / 531595 contra bancos) (P4.2).
  - **$1.100.000 consignación en efectivo** → **sin identificar**: va a
    excepciones con el cliente más probable por valor (P4.3). No se puede
    conciliar a la fuerza.
- [ ] Conciliar los 5 identificados y marcar la consignación como excepción.
- [ ] El **formato de conciliación** de arriba muestra el cuadre: abonos,
  cargos, lo explicado y la **diferencia por explicar** (la excepción) (P4.6).

## Paso 15 — La factura de papel: causar desde una foto (P1.10)

*Escenario: el proveedor de la cafetería entrega una factura de papel. El
auxiliar la fotografía, verifica los datos y la causa — el papel se archiva
digitalmente como soporte.*

- [ ] En **Subir factura** → tarjeta "¿La factura es de papel?" → **Causar
  desde una foto** (en el celular el botón abre la cámara directamente).
- [ ] Subir `datos-prueba/P1.10-factura-fisica.png` (una factura de papel
  simulada; sirve cualquier foto real). Con la `NVIDIA_API_KEY` configurada,
  la IA de visión prellena los campos y muestra su confianza; sin key, la app
  lo dice claro y te deja **digitar manualmente** (la foto queda de soporte).
- [ ] Confirmar los campos **uno por uno** contra el papel (prueba dañar el
  total: la app rechaza si subtotal + IVA ≠ total).
- [ ] **Causar como sugerida** → la factura entra al flujo normal (cuenta PUC,
  retención según la matriz de terceros, asiento balanceado), SIEMPRE como
  sugerida — nunca automática por venir de OCR — y en el detalle queda el
  enlace **"ver foto (soporte)"**.
- [ ] Antiduplicado sin CUFE: la misma factura (mismo NIT + número + fecha)
  dos veces → rechazo "ya fue causada".

## Paso 16 — ¿Quién nos debe y hace cuánto? (P5.1)

*Escenario: lunes en la mañana. El auxiliar revisa la cartera para saber a
quién cobrar primero.*

- [ ] Abrir **Cartera** en el menú: cada venta aprobada con saldo aparece
  clasificada por edad (corriente, 1–30, 31–60, 61–90, +90 días) con
  totales por rango arriba.
- [ ] Verificar la conexión con bancos (paso 14): la FE-104 que conciliaste
  **no aparece** (pagada por completo) y la FE-106 muestra el **abono parcial**
  descontado del saldo ($9.200.000 − $4.600.000 = $4.600.000 pendientes).
- [ ] Las notas crédito aprobadas también descuentan cartera (la NC-12 del
  paso 11 rebaja la factura sobre la que se emitió, si ambas están aprobadas).
- [ ] El asterisco (*) marca facturas sin fecha de vencimiento en el XML:
  se les asume el plazo comercial de 30 días.

## Paso 17 — ¿Qué le vence a la empresa este mes? (P6)

*Escenario: el auxiliar lleva el control de vencimientos según el NIT —
llegar tarde a la retefuente cuesta sanción mínima + intereses.*

- [ ] Abrir **Calendario** en el menú: aparecen las fechas del segundo
  semestre 2026 para NIT terminado en **7** (el de LEARNWAY): retención en
  la fuente mensual, IVA bimestral e ICA Bogotá, con su estado (vencido /
  vence HOY / en N días).
- [ ] Las que caen dentro de la anticipación configurada (5 días por defecto)
  salen como **alerta destacada** arriba.
- [ ] En el admin (Empresas → LEARNWAY) puedes cambiar el **correo de
  alertas** y los **días de anticipación**; el comando
  `python manage.py enviar_alertas_tributarias` (programado a diario) envía
  el correo con el detalle.
- [ ] **Importante:** las fechas sembradas son *estimadas* con el patrón DIAN
  por último dígito; se confirman contra el decreto oficial de plazos y se
  ajustan en el admin (Vencimientos tributarios).
- [ ] P6.1 (dos tenants ven fechas distintas) queda cubierto por test
  automático; el monitoreo de rechazos DIAN (P6.3) requiere la
  automatización del portal y está pendiente.

## Paso 18 — Entregar el mes al contador (P7)

*Escenario: fin de mes. El auxiliar repasa que no quede nada suelto y arma la
carpeta que el contador revisa y firma.*

- [ ] Abrir **Cierre** en el menú (elegir el período, p. ej. 2026-06).
- [ ] La lista de chequeo muestra los 3 controles del cierre:
  1. **Todo causado:** cuántas compras/ventas tiene el mes y cuáles siguen en
     bandeja, cada una con su motivo (P7.1).
  2. **Conciliación:** sin movimientos pendientes; las excepciones quedan
     documentadas como partidas conciliatorias.
  3. **Retenciones cuadradas (P7.2):** por cuenta 2365, total según asientos =
     total según facturas — la base del formulario 350.
- [ ] Si hay pendientes, el estado dice **"Con pendientes"**; aprueba/rechaza
  lo que falte y verás el badge **"Listo para entrega"** en verde.
- [ ] **Descargar paquete** → un ZIP con: resumen del cierre, auxiliar por
  cuenta, auxiliar por tercero, CSV consolidado formato Siigo, partidas
  conciliatorias y la carpeta `soportes/` con el XML (y foto) de cada
  documento. Ábrelo y revisa que los auxiliares abran bien en Excel.
- [ ] P7.3 (dos empresas cerrando el mismo mes sin cruzarse) queda cubierto
  por test automático.

## Paso 19 — Acceso e identidad (PLAN §12)

*Escenario: la plataforma es multi-tenant de verdad — nadie entra sin
invitación y ninguna empresa sabe que las otras existen.*

- [ ] Abrir http://127.0.0.1:8000 en una ventana de incógnito: **todo redirige
  al login** — no hay nada visible sin sesión.
- [ ] Ingresar con tu usuario (`luisvahosh@gmail.com` + la contraseña temporal
  entregada; cámbiala en el admin → Users). Probar una contraseña mala: el
  error dice solo "Correo o contraseña incorrectos" — nunca revela si el
  correo existe. Al 5.º intento fallido la cuenta se bloquea 1 hora
  (django-axes).
- [ ] En el menú aparece la **empresa activa** (LEARNWAY SAS) y el botón
  **Salir**. El nombre de la empresa lleva a **Mis empresas** — solo lista
  las tuyas.
- [ ] **Invitar un usuario:** Mis empresas → Invitar → correo + rol → se
  genera un enlace de un solo uso que vence en 72 horas (con backend de
  correo de consola, el correo sale en la terminal del servidor). Abrir el
  enlace en incógnito: formulario de registro con contraseña validada
  (Argon2). El enlace **muere al usarse** — probarlo dos veces.
- [ ] Roles: un usuario "operador" no puede invitar; solo el administrador
  de la empresa.

## Paso 20 — Recordatorios de cobro automáticos (P5.2 y P5.3)

*Escenario: cada mañana, la app le escribe a los clientes morosos con su
estado de cuenta — sin molestar jamás al que ya pagó.*

- [ ] Activar el opt-in: admin → Empresas → LEARNWAY → marcar **"enviar
  recordatorios de cobro"**. (Es por tenant: cada empresa decide.)
- [ ] Correr `python manage.py enviar_recordatorios_cobro` — con el backend
  de consola, los correos salen en la terminal del servidor: un **estado de
  cuenta por cliente** agrupando todas sus facturas vencidas con días de
  mora y saldo.
- [ ] Reglas verificadas por test: la factura **corriente no molesta** al
  cliente; el cliente **que ya pagó** (pago conciliado en Bancos) no recibe
  nada (P5.3); las facturas sin correo del cliente se reportan aparte.
- [ ] El correo del cliente se toma automáticamente del XML de la factura
  (Contact/ElectronicMail); se puede completar a mano en el admin.
- [ ] En producción, este comando y el de alertas tributarias se programan
  a diario (Programador de tareas / Celery beat).

## Paso 21 — Recuperar la contraseña

- [ ] En el login → **"¿Olvidaste tu contraseña?"** → escribir tu correo.
  La respuesta es idéntica exista o no la cuenta (no se puede adivinar
  quién tiene usuario).
- [ ] El correo con el enlace sale por la consola del servidor (en
  desarrollo). Abrirlo, definir la contraseña nueva y entrar con ella.
- [ ] Volver a abrir el mismo enlace: ya no sirve (un solo uso).

## Paso 22 — La nota crédito del proveedor

*Escenario: el contador acordó un descuento de $300.000 sobre su factura
FVS-847 y emitió la nota crédito NCP-15.*

- [ ] Subir `P1-nc-proveedor.xml` **antes** que la FVS-847 (en una base
  limpia): la app pide causar primero la original.
- [ ] Con la FVS-847 causada, subirla de nuevo: queda vinculada ("Reversa a
  FVS-847") con el asiento de reversa — débito 2335 $357.000, crédito 5110
  $300.000 y 240802 $57.000 — y la explicación **advierte revisar el ajuste
  de la retefuente** porque la compra original tuvo retención.

## Paso 23 — Causar el mes por lotes (P1.8, ingesta automática)

*Escenario: descargaste la carpeta del mes desde el portal DIAN — nadie va a
subir 100 facturas una por una.*

- [ ] Correr:
  `python manage.py causar_lote "..\datos-prueba"`
  El comando procesa todos los XML de la carpeta y reporta por archivo:
  **OK** (causada/registrada), **DUP** (ya estaba, no duplica) o **ERR**
  (con el motivo — el malformado y el XXE caen aquí).
- [ ] Las notas crédito que llegan antes que su factura original se
  **reintentan al final del lote** — el orden de los archivos no importa.
- [ ] Todo queda **pendiente de aprobación** en las bandejas: el lote acelera
  la digitación, no reemplaza tu revisión (humano en el circuito).
- [ ] Correrlo dos veces: la segunda pasada no duplica nada.

## Paso 24 — El humano decide: reclasificar (cierra P1.7)

*Escenario: la app propuso "activo fijo" para el aire acondicionado (paso 7),
pero el contador decide que es gasto de instalación. La decisión es humana;
la app recalcula todo.*

- [ ] Abrir la factura ambigua del paso 7 (TS-3391, pendiente o rechazada) →
  botón **"Reclasificar cuenta"**.
- [ ] La pantalla muestra el porqué de la propuesta original y un selector de
  cuentas con su concepto de retención. Elegir **5145 — Mantenimiento y
  reparaciones** y escribir el motivo.
- [ ] Al guardar: la retención se recalcula (de compras 2.5% a servicios 4%,
  respetando la matriz de terceros), el asiento completo se rearma
  balanceado, y la factura vuelve a la bandeja como propuesta **Manual**
  pendiente de tu aprobación — con tu motivo en la explicación.
- [ ] Una factura **rechazada** también se puede reclasificar (vuelve a la
  bandeja); una **aprobada** no (el asiento ya está en firme).

## Paso 25 — Segundo factor (2FA)

*Escenario: la contraseña de un administrador se filtra. Con 2FA, el atacante
igual no entra: falta el código del teléfono.*

- [ ] En el panel de inicio, como administrador verás el aviso 🔐 →
  **actívalo aquí** (o directo en `/seguridad/2fa/`).
- [ ] Escanear el QR con Google/Microsoft Authenticator (o similar) y
  confirmar con el código de 6 dígitos.
- [ ] Salir y volver a entrar: tras la contraseña, la app **exige el código**.
  Probar uno malo (rechaza; tras varios fallidos aplica freno anti fuerza
  bruta) y el bueno (entra).
- [ ] Detalles de seguridad ya incluidos: un código usado no sirve dos veces
  (anti-repetición) y si cambias de teléfono, el dispositivo se restablece
  desde el panel admin (dispositivos TOTP).

## Paso 26 — Conexiones contables por empresa

*Escenario: cada empresa cliente conecta SU cuenta de Alegra (o su software
contable) — las credenciales viven por tenant, no en el servidor.*

- [ ] Como administrador: **Mis empresas → Conexiones contables**.
- [ ] Registrar el correo y el token de la cuenta Alegra de la empresa →
  **Verificar y guardar**: la app prueba las credenciales contra Alegra
  antes de aceptarlas (credenciales malas no se guardan; probarlo).
- [ ] Un usuario operador no puede entrar a esta pantalla.
- [ ] Desde ahora los envíos a Alegra usan la cuenta de la empresa; el
  `.env` del servidor queda solo como respaldo global de la beta.
- [ ] Siigo sigue por archivo (CSV del cierre o por factura); su API
  llegará cuando la cuenta tenga plan con credenciales.

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
