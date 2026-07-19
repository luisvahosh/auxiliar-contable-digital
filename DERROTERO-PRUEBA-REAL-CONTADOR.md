# Guía de prueba — hazlo tú mismo con tu empresa real

Bienvenido, contador. Esta guía te lleva **paso a paso** para probar la
plataforma **solo, con una empresa real tuya**, directo en producción. No
necesitas ayuda técnica: sigue los pasos en orden y marca cada casilla `[ ]`
cuando lo logres. Si algo no te cuadra, **anótalo** — es justo lo que queremos
mejorar contigo.

**Dónde:** https://auxcontable.learnway.co (todo se hace ahí).

> **Tranquilo, es una prueba:** la app **no envía nada a la DIAN ni a la PILA**,
> y **no toca tu Alegra/Siigo** (esa conexión es opcional y no la vamos a usar).
> Todo lo que registres es un **borrador tuyo**, aislado, que puedes rechazar.

---

## Antes de empezar: ten a la mano
- [ ] El **enlace de invitación** que te enviaron (vence en 72 horas) — es solo
      para darte acceso a la plataforma.
- [ ] La **razón social** y el **NIT** de la empresa que vas a registrar
      (tú mismo la creas, en el paso 2).
- [ ] Las **facturas** reales de esa empresa (compras y ventas del mes). Sirve el
      **XML**, el **ZIP** de la DIAN, o el **PDF/HTML** de la factura (la app saca
      el XML que traen adentro). Los descargas del **portal de la DIAN**
      (“Documentos electrónicos”) o de tu proveedor de facturación. *Si tienes
      facturas de papel, sirve una foto.*
- [ ] *(Muy recomendado)* Un **balance de prueba** de la empresa, **al mayor nivel
      de cuentas que puedas y sin terceros** (Excel o CSV, como lo exporta tu
      software). De ahí la app toma tus **cuentas auxiliares** reales. *(El PUC
      estándar del sector real ya viene cargado de fábrica.)*
- [ ] Los **datos fiscales** de la empresa (responsable de IVA, RST,
      autorretenedor, ICA, etc.) — los sabes de memoria.
- [ ] *(Opcional)* el **extracto bancario** del mes en CSV o PDF.

---

## Paso 1 — Entrar a la plataforma
- [ ] Abre el **enlace de invitación**.
- [ ] Escribe tu **nombre** y crea una **contraseña**. Ya tienes tu cuenta.
- [ ] Quedas dentro de la plataforma. Arriba a la derecha ves el menú.

## Paso 2 — Crea TU empresa
- [ ] Arriba a la derecha, entra a **Mis empresas**.
- [ ] Toca **“+ Crear empresa”**.
- [ ] Escribe la **razón social** y el **NIT real** de tu empresa → **Crear empresa**.
- [ ] Quedas como **administrador** de ella y se activa sola. Te lleva a la
      configuración para el siguiente paso.

## Paso 3 — Completa los datos de la empresa
- [ ] En **⚙ Configuración**, revisa y ajusta: municipio, **responsable de IVA**,
      **Régimen Simple (RST)**, **autorretenedor**, **agente de retención**,
      **tarifa de ICA** y **exoneración de parafiscales (art. 114-1)**.
- [ ] **Guarda.** *(La app usa esto para calcular bien las retenciones.)*

## Paso 3b — Tu plan de cuentas (PUC) 🆕
- [ ] Entra a **Configuración → Plan de cuentas → “Cargar mi PUC”**. Tu empresa
      **ya viene con el PUC estándar del sector real** cargado hasta la subcuenta
      (como Siigo): revísalo.
- [ ] Sube tu **balance de prueba** (al mayor nivel de cuentas, **sin terceros**,
      Excel o CSV): la app toma el código y el nombre de tus **auxiliares** e
      ignora los saldos y los títulos. Puedes subirlo las veces que quieras; solo
      actualiza lo que cambió.
- [ ] Prueba **agregar una cuenta a mano** (ej. una auxiliar tuya como 111006
      «Bancos cooperativos»): campo código + nombre → **Agregar cuenta**. También
      puedes **eliminar** una del listado.
- [ ] Verás el catálogo con cada cuenta marcada como **mayor** o **auxiliar**.
      *(Al causar o reclasificar podrás elegir la auxiliar exacta —ej. 51103505—
      y no una cuenta mayor de 4 dígitos.)*
- [ ] *(Opcional)* En **Plan de cuentas** puedes fijar qué cuenta usa la app para
      cada uso (honorarios, IVA, retenciones…): al escribir el código te sugiere
      tus cuentas cargadas.

## Paso 4 — Causar una factura de COMPRA (lo más importante)
- [ ] Botón **Subir factura** → elige el **XML, ZIP, PDF o HTML** de una compra
      real → **Procesar**. *(La app saca el XML aunque venga dentro del PDF/ZIP.)*
- [ ] Revisa la propuesta: la **cuenta**, la **retención** calculada y el **asiento**
      (débitos = créditos), con la explicación de **por qué** lo propone.
- [ ] ¿Está bien según tu criterio? → **Aprobar**.

**Si NO está bien, tienes tres formas de corregir (de menor a mayor control):**
- [ ] **Reclasificar cuenta** → ahora puedes elegir **cualquier cuenta auxiliar de
      tu PUC** (ej. 51103505) y su **concepto de retención**; la app recalcula. 🆕
- [ ] Marca **“Recordar esta cuenta y concepto para este proveedor”** 🆕 y, de ahí
      en adelante, **todas** las facturas de ese tercero se causan solas así (sin
      volver a corregir). *Así “instruyes” al sistema con las primeras facturas.*
- [ ] **Editar asiento a mano** 🆕 → para casos donde ni la propuesta ni la
      reclasificación bastan: cambias cuentas y montos, agregas o quitas renglones.
      Solo te deja guardar **si cuadra** (débitos = créditos); la retención se
      recalcula sola de los créditos a cuentas 2365.
- [ ] Repite con **3–4 compras** distintas (honorarios, servicios, inventario…)
      para ver cómo aplica cada retención y cómo se “pega” la regla al tercero.

> **Atajo del amarre por tercero:** también puedes fijar la regla desde
> **Facturación → Terceros → Editar** un proveedor: su **cuenta de gasto fija** y su
> **concepto de retención**. La columna **“Regla de causación”** te muestra a qué
> proveedores ya se la fijaste.

**Revisa como contador:** ¿la tarifa y la base de retención son las correctas?
¿La cuenta PUC (auxiliar) es la que usarías? ¿Respeta el régimen del proveedor (a
un RST no se le retiene)? ¿La regla que amarraste al tercero se aplicó en su
siguiente factura?

## Paso 5 — Causar una factura de VENTA
- [ ] **Subir factura** → elige el **XML** de una venta emitida por la empresa.
- [ ] Verifica el asiento de venta: ingreso, IVA generado y, si el cliente
      retuvo, la retención a favor. **Aprobar** si está bien.
- [ ] Si te falta un número en la numeración, la app te **avisa del hueco**.

## Paso 6 *(opcional)* — Factura de papel por foto
- [ ] **Subir factura → Causar desde una foto** → toma/carga la foto → la app lee
      los campos → confírmalos → entra como **borrador** para tu aprobación.

## Paso 7 *(opcional)* — Conciliación bancaria
- [ ] Menú **Tesorería → Bancos** → sube el **extracto** (CSV o PDF).
- [ ] Mira cómo cruza los pagos con las facturas y propone los gastos bancarios.

## Paso 8 — Cierre del mes y paquete del contador
- [ ] Menú **Cierre mensual**: revisa la lista de chequeo (qué falta, conciliación,
      **cuadre de retenciones**).
- [ ] Descarga el **paquete del contador** (auxiliares por cuenta y por tercero,
      soportes). **Pregúntate:** ¿esto es lo que necesitarías para revisar y declarar?

## Paso 9 — Informes
- [ ] Menú **Informes**: mira el **balance de comprobación** (verifica el cuadre),
      el **estado de resultados** y el **libro mayor**. ¿Las cifras te cuadran con
      lo que causaste?

## Paso 10 *(opcional)* — Exógena y certificados
- [ ] **Tributario → Exógena**: revisa el pre-armado de 1001 / 1007 / 2276.
- [ ] **Facturación → Terceros → Certificados**: certificado de retención por tercero.

---

## Al terminar: cuéntame (esto es lo valioso)
Anota, con tu criterio profesional:
- [ ] ¿El **PUC estándar de fábrica** te pareció completo? ¿El **balance de prueba**
      cargó bien tus auxiliares? ¿Pudiste causar en la **auxiliar** correcta (no en
      la mayor)?
- [ ] ¿La **regla por tercero** funcionó? (le fijas cuenta+concepto a un proveedor y
      su siguiente factura sale sola así)
- [ ] ¿La **edición del asiento a mano** te dio el control que necesitabas?
- [ ] ¿Las **retenciones** (tarifas y bases) quedaron bien?
- [ ] ¿El **cuadre de retenciones** y el **paquete del contador** te sirven para declarar?
- [ ] ¿Los **informes** cuadran con lo que registraste?
- [ ] ¿Qué te **gustó**, qué te **estorbó** y qué le **falta** para que la usaras a diario?

> Cualquier cosa rara, un cálculo que no cuadre o un paso confuso: **anótalo con
> el número de factura o la pantalla**. Con eso lo afinamos. ¡Gracias por probarla!
