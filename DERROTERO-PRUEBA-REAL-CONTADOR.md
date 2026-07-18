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
- [ ] El **enlace de invitación** que te enviaron (vence en 72 horas).
- [ ] Los **XML** de algunas facturas reales de la empresa (compras y ventas del
      mes). Los descargas del **portal de la DIAN** (“Documentos electrónicos”) o
      de tu proveedor de facturación. *Si tienes facturas de papel, sirve una foto.*
- [ ] Los **datos fiscales** de la empresa (responsable de IVA, RST,
      autorretenedor, ICA, etc.) — los sabes de memoria.
- [ ] *(Opcional)* el **extracto bancario** del mes en CSV o PDF.

---

## Paso 1 — Entrar
- [ ] Abre el **enlace de invitación**.
- [ ] Escribe tu **nombre** y crea una **contraseña**. Ya tienes cuenta.
- [ ] Entras a la empresa que te asignaron. Arriba a la derecha ves su nombre.

## Paso 2 — Confirmar los datos de la empresa
- [ ] Entra a **⚙ Configuración**.
- [ ] Revisa y ajusta: municipio, **responsable de IVA**, **Régimen Simple (RST)**,
      **autorretenedor**, **agente de retención**, **tarifa de ICA** y
      **exoneración de parafiscales (art. 114-1)**.
- [ ] **Guarda.** *(La app usa esto para calcular bien las retenciones.)*
- [ ] *(Opcional)* Revisa **Configuración → Plan de cuentas**: trae el PUC por
      defecto; ajusta un código si tu empresa usa otro.

## Paso 3 — Causar una factura de COMPRA (lo más importante)
- [ ] Botón **Subir factura** → elige el **XML** de una compra real → **Procesar**.
- [ ] Revisa la propuesta: la **cuenta**, la **retención** calculada y el **asiento**
      (débitos = créditos), con la explicación de **por qué** lo propone.
- [ ] ¿Está bien según tu criterio? → **Aprobar**. ¿No? → **Reclasificar** y elige
      la cuenta correcta (la app recalcula la retención).
- [ ] Repite con **3–4 compras** distintas (honorarios, servicios, inventario…)
      para ver cómo aplica cada retención.

**Revisa como contador:** ¿la tarifa y la base de retención son las correctas?
¿La cuenta PUC es la que usarías? ¿Respeta el régimen del proveedor (a un RST no
se le retiene)?

## Paso 4 — Causar una factura de VENTA
- [ ] **Subir factura** → elige el **XML** de una venta emitida por la empresa.
- [ ] Verifica el asiento de venta: ingreso, IVA generado y, si el cliente
      retuvo, la retención a favor. **Aprobar** si está bien.
- [ ] Si te falta un número en la numeración, la app te **avisa del hueco**.

## Paso 5 *(opcional)* — Factura de papel por foto
- [ ] **Subir factura → Causar desde una foto** → toma/carga la foto → la app lee
      los campos → confírmalos → entra como **borrador** para tu aprobación.

## Paso 6 *(opcional)* — Conciliación bancaria
- [ ] Menú **Tesorería → Bancos** → sube el **extracto** (CSV o PDF).
- [ ] Mira cómo cruza los pagos con las facturas y propone los gastos bancarios.

## Paso 7 — Cierre del mes y paquete del contador
- [ ] Menú **Cierre mensual**: revisa la lista de chequeo (qué falta, conciliación,
      **cuadre de retenciones**).
- [ ] Descarga el **paquete del contador** (auxiliares por cuenta y por tercero,
      soportes). **Pregúntate:** ¿esto es lo que necesitarías para revisar y declarar?

## Paso 8 — Informes
- [ ] Menú **Informes**: mira el **balance de comprobación** (verifica el cuadre),
      el **estado de resultados** y el **libro mayor**. ¿Las cifras te cuadran con
      lo que causaste?

## Paso 9 *(opcional)* — Exógena y certificados
- [ ] **Tributario → Exógena**: revisa el pre-armado de 1001 / 1007 / 2276.
- [ ] **Facturación → Terceros → Certificados**: certificado de retención por tercero.

---

## Al terminar: cuéntame (esto es lo valioso)
Anota, con tu criterio profesional:
- [ ] ¿Las **retenciones** (tarifas y bases) quedaron bien?
- [ ] ¿Las **cuentas PUC** propuestas son las correctas?
- [ ] ¿El **cuadre de retenciones** y el **paquete del contador** te sirven para declarar?
- [ ] ¿Los **informes** cuadran con lo que registraste?
- [ ] ¿Qué te **gustó**, qué te **estorbó** y qué le **falta** para que la usaras a diario?

> Cualquier cosa rara, un cálculo que no cuadre o un paso confuso: **anótalo con
> el número de factura o la pantalla**. Con eso lo afinamos. ¡Gracias por probarla!
