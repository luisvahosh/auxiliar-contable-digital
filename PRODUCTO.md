# Auxiliar Contable Digital — Qué hace y qué cubre

> Documento de producto. Consolida, en lenguaje de negocio, todas las funciones
> que hoy realiza la aplicación para poder plantearla como producto ante
> clientes, aliados y contadores. Detalle técnico y de arquitectura: `PLAN.md`.
> Guía de validación de dominio: `PROCESO-AUXILIAR-CONTABLE.md`.

---

## 1. En una frase

**El auxiliar contable digital hace el trabajo operativo del auxiliar contable
colombiano encima del software contable que la empresa ya usa (Alegra / Siigo):**
recibe los documentos, los clasifica según el PUC, calcula retenciones, arma los
asientos, concilia el banco, vigila el calendario tributario, liquida la nómina
como borrador, cierra el mes y pre-arma la exógena — siempre con un humano que
aprueba.

## 2. El principio que define el alcance (no negociable)

La app **ASISTE al auxiliar; NO reemplaza** los aplicativos especializados. Así
como el auxiliar humano trabaja sobre Alegra/Siigo, la app trabaja sobre ellos.

- Todo cálculo automático es **borrador para revisión humana**.
- Toda acción tiene un nivel explícito — **automática / sugerida / manual** — y
  explica su porqué.
- La **nómina (P8)** es apoyo y causación contable: **no** es un software de
  nómina, **no** compite con Aleluya/Nominapp, **no** presenta PILA ni nómina
  electrónica. Sus exportes son para **entregar al operador**, no para
  reemplazarlo.
- La app **no reporta ante la DIAN**: la exógena y la facturación electrónica
  las presenta el sistema oficial del cliente; aquí se **pre-arman** y se
  **monitorean**.

Este límite es una ventaja comercial: se integra sin fricción y sin pedirle al
cliente que abandone lo que ya paga.

---

## 3. Lo que hace, proceso por proceso

Cada bloque corresponde a un proceso real del auxiliar contable (P1–P13).

### P1 — Causación de compras
- **Subir el XML DIAN** de la factura de compra (parseo seguro con `defusedxml`,
  blindado contra XXE) → **valida** totales, detecta **CUFE duplicado**.
- **Propone la cuenta del PUC** y la **retención en la fuente** con explicación
  en lenguaje claro, y arma el **asiento contable balanceado**.
- El humano **aprueba o rechaza** (humano en el circuito).
- **Causación desde foto** de la factura física (P1.10): el celular saca la
  foto → visión por IA extrae los campos → el auxiliar confirma campo por campo
  → entra al flujo normal, siempre como "sugerida". Antiduplicado por
  NIT+número+fecha.
- **Reclasificación manual** (P1.7): si la cuenta propuesta no es la correcta,
  el usuario elige la cuenta PUC correcta y se recalculan retención y asiento.
- **Causación por lote** de una carpeta completa (P1.8), reentrante.

### P2 — Causación de ventas
- El mismo "subir XML" **detecta solo** si es compra, venta o nota crédito.
- Arma el **asiento de venta** (ingreso, IVA generado, retefuente practicada).
- **Alerta huecos** en el consecutivo de facturación.
- Vincula la **nota crédito** a su factura original.

### P3 — Matriz de terceros
- Modelo de **tercero por empresa** con sus atributos fiscales (declarante,
  autorretenedor, régimen simple, verificado).
- Se **crea solo** con la primera factura del proveedor.
- La matriz **manda sobre el XML** al calcular la retención (tarifas de no
  declarante incluidas).

### P4 — Conciliación bancaria
- Carga del **extracto bancario en CSV o PDF** (PDF de texto; los escaneos se
  rechazan con instrucción).
- **Cruce automático** contra las facturas aprobadas: pago de cliente
  (exacto/parcial por neto de cartera), pago a proveedor, gastos bancarios con
  asiento propuesto.
- **Excepciones** con el candidato más probable señalado.
- **Formato de cuadre** para cerrar la conciliación.

### P5 — Cartera y cobro
- **Cartera por edades** (P5.1): saldo = neto − pagos conciliados − notas
  crédito; vencimiento tomado del XML o 30 días asumidos.
- **Recordatorios de cobro** por correo (P5.2/P5.3), opt-in: estado de cuenta
  por cliente; **el que ya pagó no recibe nada**.

### P6 — Calendario tributario
- **Vencimientos por último dígito del NIT** (P6.1), editables por el contador.
- **Alertas por correo** con la anticipación que cada empresa configure (P6.2).
- **Monitoreo DIAN de facturas emitidas** (P6.3): lee el ApplicationResponse
  que recibe el auxiliar y marca cada factura como **aceptada/rechazada**, con
  motivo y fecha; alerta los rechazos una sola vez.

### P7 — Cierre mensual
- **Lista de chequeo del período**: pendientes con su motivo, estado de la
  conciliación, cuadre de retenciones (2365 = base del formulario 350).
- **Paquete ZIP para el contador**: resumen, auxiliares por cuenta y por
  tercero, consolidado Siigo, partidas conciliatorias y todos los soportes
  (XML + fotos).

### P8 — Nómina (apoyo, no software de nómina)
- **Liquidación mensual**: auxilio de transporte, deducciones de salud y
  pensión (4+4), aportes patronales con exoneración art. 114-1 configurable,
  provisiones — todo en un **asiento consolidado balanceado**.
- **Novedades** (P8.8): incapacidades, horas extra, etc., con su efecto sobre
  base y neto.
- **Carga masiva de empleados por CSV**, reentrante por cédula.
- **Exportes para el operador** (P8.9): pre-PILA (IBC + aportes desglosados) y
  resumen de nómina electrónica. **Borradores para entregar**, la app no
  presenta ante PILA/DIAN.

### P9 — Certificados de retención
- Agrega por tercero y concepto las retenciones del año desde las compras
  aprobadas; las notas crédito descuentan la base.
- **Certificado individual imprimible** y listado.

### P10 — Activos fijos
- Registro por categoría (vida útil + cuentas PUC).
- **Depreciación mensual línea recta**, topada al valor depreciable y sin
  depreciar antes de la fecha de adquisición.
- Al aprobar, actualiza la depreciación acumulada; asiento cuadrado por
  categoría.

### P11 — Caja menor
- **Fondo fijo**, **vales** con categoría del plan de cuentas y **reembolso**
  que legaliza los vales (asiento gastos + IVA contra bancos).
- Controla el efectivo disponible y que no se exceda el fondo.

### P12 — Pre-armado de exógena (apoyo, no reporta ante DIAN)
- **Formato 1001** (pagos y retenciones a proveedores) y **1007** (ingresos por
  cliente).
- **Formato 2276** (rentas de trabajo): agrega por empleado los pagos laborales
  y aportes desde la nómina aprobada.
- **Export CSV** para el prevalidador de la DIAN.

### P13 — Informes contables
- **Lectura transversal** que consolida los asientos aprobados de todos los
  módulos.
- **Balance de comprobación** (con verificación de cuadre), **estado de
  resultados** y **libro mayor** por cuenta con saldo corriente. Export CSV.

### Asistente IA normativo
- **Consulta normativa con citas**: RAG semántico sobre un corpus curado de
  fichas (retenciones, IVA, factura, exógena, nómina, con valores 2026
  verificados). Responde **solo con el contexto**, cita las fuentes y muestra
  disclaimer. Con caché para responder rápido.

---

## 4. Plataforma, seguridad y multi-empresa

Lo que hace que esto sea un producto vendible y no un script:

- **Multi-tenant estricto**: toda la información se aísla por empresa; un
  cliente jamás ve datos de otro (probado en CI). UUID en las URLs públicas.
- **Multi-empresa por usuario**: un auxiliar o contador maneja varias empresas
  con un selector de empresa activa; membresías con **roles**
  (admin/operador/lectura).
- **Acceso cerrado por defecto**: sin registro abierto; ingreso por
  **invitación** con token de un solo uso (72h). Login con Argon2 y bloqueo por
  intentos.
- **2FA (TOTP)** con código QR y **códigos de respaldo** de un solo uso.
- **Recuperación de contraseña** segura (enlace de un solo uso).
- **Configuración por empresa**: datos fiscales, plan de cuentas propio
  (catálogo de ~45 roles con overrides), conexiones contables, buzón.
- **Ingesta automática**: carpeta vigilada y **buzón de correo IMAP** por
  empresa que lee los XML de los adjuntos y ZIP y los causa solo.
- **Secretos cifrados en reposo** (tokens de conexión y buzón).
- **12-factor**: toda la configuración por `.env`, nada quemado en código.
- **Seguridad de datos**: no se loguean datos financieros del cliente; se
  minimiza lo que se envía a la IA; toda entrada externa (XML DIAN) se valida.

### Integraciones — hoy
- **Alegra** (API): envío de asientos y mapeo de cuentas por empresa.
- **Siigo** (CSV): export en formato consolidado.
- **Visión por IA** (NVIDIA NIM): lectura de facturas físicas desde foto.
- **Correo saliente por Microsoft Graph** (Office 365 app-only) para alertas y
  recordatorios.

### Ecosistema de integración — con qué software contable se puede conectar

El diseño (una **conexión contable por empresa**, resuelta por rol de cuenta y
mapeo de PUC configurable) permite sumar más software del mercado colombiano sin
tocar el núcleo. El resto de plataformas líderes **exponen API**, así que son
candidatas naturales de integración:

| Software contable / ERP | API para integrar | Estado en el producto |
|---|---|---|
| **Alegra** | API REST pública documentada | **Integrado** (envío de asientos) |
| **Siigo** | API para desarrolladores / socios | Export CSV hoy; API en hoja de ruta |
| **World Office (Cloud)** | API REST pública (`developer.worldoffice.cloud`), auth JWT | Candidato de integración |
| **Loggro** | API REST pública con OpenAPI (`developer.loggro.com`), incluye contabilidad y nómina | Candidato de integración |
| **ContaPyme** | Módulo "agente de servicios web" (API documentada, cualquier lenguaje) | Candidato de integración |
| **Helisa** | Contabilidad/POS/nómina; integración vía servicios | Por evaluar |

> Mensaje comercial: **"lleva la contabilidad en el software que ya usa"** — el
> producto se acopla encima del ERP del cliente, no lo obliga a migrar.

### Facturación electrónica DIAN — proveedores tecnológicos con API

Para recibir y monitorear documentos electrónicos (P1/P2/P6.3) existe una capa de
**proveedores autorizados por la DIAN** con API REST, complementaria al ERP. La
app hoy trabaja con el **XML DIAN** que el auxiliar ya recibe (subida, buzón
IMAP, lote), pero puede conectarse a estos proveedores para automatizar la
recepción/consulta:

- **Alegra API**, **Plemsi**, **Aliaddo**, **Factus**, **Alanube**, **Matias
  API**, **Factura Latam**, **Nextpyme Plus**, **LaFactura**.

> Estas son la vía técnica para la emisión/recepción ante la DIAN; **la app no
> reemplaza al proveedor DIAN del cliente** — lo lee y lo monitorea (principio
> asistir-no-reemplazar).

### Despliegue
- Corriendo en **producción** sobre VPS con Docker (PostgreSQL, gunicorn,
  whitenoise) en **https://auxcontable.learnway.co**, con HTTPS por proxy
  inverso.

---

## 5. Cómo se posiciona como producto

**La promesa:** hace el trabajo operativo repetitivo — recibir, clasificar,
calcular, conciliar, alertar, cerrar y pre-armar — dejando al profesional solo
la **revisión y la decisión**. No pide cambiar de software: se monta encima del
que ya usan.

### A quién sirve — tres segmentos

**1. Firmas contables (llevan la contabilidad de muchas empresas)**
- Manejan **decenas de empresas** desde un solo lugar, con **selector de empresa
  activa** y **aislamiento estricto** entre clientes.
- Reparten el trabajo por **roles** (admin/operador/lectura) y por invitación
  controlada; el socio revisa, el auxiliar opera.
- **Estandarizan la calidad**: la misma clasificación, retenciones y cierre para
  todos los clientes, con explicación de cada decisión.
- Escalan la cartera de clientes **sin sumar auxiliares al mismo ritmo**: la
  digitación y la clasificación las hace la app.

**2. Contadores independientes (unas pocas empresas, todo el ciclo en sus manos)**
- Hacen ellos mismos lo operativo; la app les **quita la digitación y el
  cálculo** para dedicarse al análisis y a la asesoría.
- **Foto → asiento** y **buzón → asiento**: la entrada de datos casi desaparece.
- Cierre mensual y **paquete listo** con soportes, auxiliares y consolidado —
  menos noches de cierre.

**3. Empresas (llevan su propia contabilidad o quieren visibilidad)**
- La empresa con auxiliar interno **reduce la carga operativa** y **estandariza**
  el proceso sin depender de la memoria de una sola persona.
- **Visibilidad para gerencia**: cartera por edades, calendario de vencimientos
  con alertas, informes (balance, resultados, mayor) y monitoreo DIAN de sus
  facturas — sin esperar al contador.
- **Trabaja con su contador externo, no contra él**: la empresa alimenta y ve;
  el asiento sigue con **revisión profesional** antes de aprobarse. Se integra
  con el Alegra/Siigo que la empresa ya paga.

**Diferenciales (para los tres):**
1. **Cubre el ciclo completo** del auxiliar (P1–P13), no una sola tarea.
2. **Humano en el circuito** con niveles y explicaciones — apto para quien
   responde profesionalmente por la contabilidad.
3. **Multi-empresa real** con aislamiento estricto — igual sirve a una firma con
   50 clientes que a una empresa con una sola contabilidad.
4. **Se integra, no reemplaza** — cero fricción de adopción sobre Alegra/Siigo.
5. **Foto → asiento** y **buzón → asiento**: la entrada de datos casi
   desaparece.

---

## 6. Estado actual (a la fecha de este documento)

- Ciclo P1–P13 con **primera pasada completa**, más asistente IA, acceso e
  identidad (§12) y consolidación multi-empresa con PostgreSQL.
- **229 pruebas** automatizadas; validación de dominio contra datos reales.
- En producción y verificado end-to-end en varias integraciones (Alegra real,
  visión real, asistente real).

**Frentes abiertos:** ampliar el corpus del asistente con un contador; validar
un mes real de XML DIAN; confirmar el calendario tributario 2026 y los conceptos
de exógena contra las resoluciones oficiales; validar el CSV contra Siigo real;
confirmar los códigos ResponseCode de la DIAN.
