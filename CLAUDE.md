# CLAUDE.md — Auxiliar Contable Digital

Software que hace el trabajo del auxiliar contable colombiano sobre el software
contable existente (Alegra/Siigo). Contexto completo: `PLAN.md`.
Guía de pruebas de dominio: `PROCESO-AUXILIAR-CONTABLE.md`.

## Cómo correr (Windows, desarrollo local — sin Docker por ahora)

```
cd app
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env   # y completar DJANGO_SECRET_KEY
python manage.py migrate
python manage.py runserver
```

Abrir http://127.0.0.1:8000 — debe verse la página de inicio.

## Cómo probar

```
cd app
python manage.py test
```

Toda funcionalidad de dominio se valida contra los casos de
`PROCESO-AUXILIAR-CONTABLE.md` (P1–P7) con datos reales, no solo unit tests.

## Convenciones (no negociables — PLAN.md §4, §10, §12)

1. **12-factor:** toda configuración por `.env`. Nada quemado en código.
   `.env` jamás se versiona; `.env.example` documenta cada variable.
2. **Multi-tenant estricto:** toda query de datos de negocio filtra por tenant
   (manager de Django dedicado). UUID en URLs públicas, nunca ids secuenciales.
   Test de acceso cruzado entre tenants obligatorio en CI.
3. **Humano en el circuito:** toda acción automática tiene nivel
   automática/sugerida/manual y explica su porqué.
4. **Seguridad:** validar toda entrada externa (XML DIAN = vector principal:
   parsear con defusedxml, nunca xml.etree directo). No loguear datos
   financieros de clientes. Minimizar datos enviados a la API de IA.
5. **UI:** español, mobile-first, tokens semánticos de color, números tabulares
   en tablas contables, labels visibles (PLAN.md §11).
6. **Idioma:** código e identificadores en español donde sea natural del
   dominio (causacion, retencion, tercero); comentarios en español.

## Estructura

- `app/config/` — settings, urls raíz.
- `app/core/` — app base (inicio, tenant Empresa; luego: usuarios).
- `app/causacion/` — P1/P2/P3: compras, ventas, terceros, Alegra/Siigo.
- `app/conciliacion/` — P4: extractos bancarios y cruce contra libros.
- `app/calendario/` — P6: calendario tributario por NIT y alertas por correo.
- `app/cierre/` — P7: lista de chequeo del mes y paquete ZIP del contador.
- `app/nomina/` — P8: planta de personal y liquidación mensual con asiento.
- `app/activos/` — P10: activos fijos y depreciación línea recta.
- `app/cajamenor/` — P11: fondo fijo, vales y reembolso que los legaliza.
- Próximas apps por vertical: `asistente/`.

## Estado y siguiente paso

- **Hecho (día 1):** proyecto corriendo con .env, página de inicio.
- **Hecho (día 2):** vertical de causación P1 — subir XML DIAN (defusedxml) →
  validar (totales, CUFE duplicado, XXE) → proponer cuenta PUC + retefuente
  con explicación → asiento balanceado → aprobar/rechazar (humano en el
  circuito). App `causacion/`, tenant `core.Empresa`, 17 tests (P1.1–P1.7 con
  los XML de `datos-prueba/`). Derrotero manual: `DERROTERO-PRUEBAS-P1.md`.
- **Hecho (día 2, P1.9):** asiento aprobado → descarga CSV formato Siigo y
  envío a Alegra vía API (`causacion/siigo.py`, `causacion/alegra.py`;
  credenciales por .env ALEGRA_EMAIL/ALEGRA_TOKEN; mapeo cuenta PUC → id
  Alegra por empresa en admin). 21 tests.
- **Hecho (día 3):** Alegra real conectado (credenciales en .env; primer
  asiento #1 verificado). Vertical P2 ventas: el mismo "subir XML" detecta
  compra/venta/nota crédito; asiento de venta (1305/4135/240801, retefuente
  practicada a 135515), alerta de huecos en consecutivo, nota crédito
  vinculada a la original. 27 tests.
- **Hecho (día 3, P3):** matriz de terceros — modelo Tercero por empresa
  (declarante/autorretenedor/RST/verificado), se crea solo con la primera
  factura del proveedor, UI en /causacion/terceros/, y manda sobre el XML en
  calcular_retencion (tarifas no declarante incluidas). 34 tests.
- **Hecho (día 3, P4):** conciliación bancaria — app `conciliacion/`: extracto
  CSV (fecha;descripcion;valor) → cruce contra facturas aprobadas (pago
  cliente exacto/parcial por neto de cartera, pago proveedor, gastos
  bancarios 530505/531595 con asiento propuesto), excepciones con candidato
  más probable, formato de cuadre P4.6. 44 tests.
- **Hecho (día 3, P1.10):** causación desde foto de factura física —
  `causacion/vision.py` (NVIDIA NIM OpenAI-compatible, NVIDIA_API_KEY en
  .env; sin key: digitación manual con la foto como soporte) → formulario de
  confirmación campo por campo → flujo normal SIEMPRE como "sugerida";
  antiduplicado NIT+número+fecha (cufe FISICA:...); imagen en MEDIA_ROOT.
  49 tests.
- **Hecho (día 3):** visión verificada end-to-end con NVIDIA_API_KEY real
  (extracción perfecta sobre datos-prueba/P1.10-factura-fisica.png). P5.1
  cartera por edades: `causacion/cartera.py` — saldo = neto − pagos
  conciliados (P4) − notas crédito aprobadas; vencimiento del XML
  (PaymentDueDate, nuevo campo) o 30 días asumidos; página /causacion/cartera/.
  55 tests.
- **Hecho (día 3, P6):** calendario tributario — app `calendario/`:
  VencimientoTributario global (admin-editable), fechas por último dígito
  del NIT (P6.1), alertas con anticipación configurable por empresa y correo
  vía comando `enviar_alertas_tributarias` (P6.2; backend consola en dev).
  Semilla 2026-S2 ESTIMADA (retefuente, IVA bimestral, ICA Bogotá) — confirmar
  contra decreto oficial. 62 tests.
- **Hecho (día 3, P7):** cierre mensual — app `cierre/` (sin modelos: lectura
  transversal): checklist del período (pendientes con motivo, conciliación,
  cuadre de retenciones 2365 = base formulario 350) y paquete ZIP del
  contador (resumen, auxiliares por cuenta/tercero, Siigo consolidado,
  partidas conciliatorias, soportes XML+fotos). 70 tests. Con esto la guía
  P1–P7 tiene su primera pasada completa.
- **Hecho (día 4, PLAN §12):** acceso e identidad — sin registro abierto:
  login (Argon2 + django-axes 5 intentos/1h, error genérico), matrícula por
  token de un solo uso hasheado con 72h (`core.Invitacion`), membresías
  usuario↔empresa con roles (admin/operador/lectura), selector de empresa
  activa por sesión, middleware `AccesoPorEmpresaMiddleware` (todo cerrado
  por defecto, `request.empresa` como tenant). Tests base `CasoConEmpresa`
  en core/pruebas.py — TODA prueba de vistas hereda de ahí. 81 tests.
  Usuario semilla: luisvahosh@gmail.com (admin LEARNWAY + superuser).
- **Hecho (día 4, P5.2/P5.3):** recordatorios de cobro — comando
  `enviar_recordatorios_cobro` (opt-in por Empresa): estado de cuenta por
  cliente agrupando facturas vencidas; el que pagó no recibe nada (la
  cartera descuenta pagos conciliados y NC); correo del cliente extraído
  del XML (Contact) a FacturaVenta.correo_cliente. 87 tests.
- **Hecho (día 4):** recuperación de contraseña (§12, enlace de un solo uso,
  respuesta idéntica exista o no el correo); notas crédito de proveedor
  (reversa vinculada, advierte ajuste de retefuente); refactor
  `causacion/servicios.py` — motor único `procesar_xml` para todos los
  canales de ingesta; comando `causar_lote <carpeta>` (P1.8) con reintento
  de NC al final del lote, reentrante. Ingesta automática (carpeta + buzón
  IMAP) documentada en PLAN.md §4. 94 tests.
- **Hecho (día 4, P4.5):** extracto bancario en PDF — `parsear_extracto_pdf`
  (pypdf, PDF de texto; escaneos rechazados con instrucción), mismo motor de
  cruce; `parsear_extracto_archivo` decide por extensión. Fixture
  P4-extracto-junio.pdf idéntico al CSV. 97 tests.
- **Hecho (día 4):** reclasificación manual — vista `reclasificar` para
  compras pendientes/rechazadas: el usuario elige la cuenta PUC correcta
  (selector con concepto de retención), se recalculan retención (con matriz
  de terceros) y asiento, y vuelve a bandeja como nivel "manual" con el
  motivo en la explicación. Cierra el ciclo de P1.7. 101 tests.
- **Hecho (día 5):** desplegado en el VPS Docker de Hostinger (compose con
  volumen `datos` para sqlite+media, gunicorn+whitenoise, puerto público
  configurable con PUERTO_WEB — quedó en 9500). El repo de GitHub ahora es
  PÚBLICO (historial auditado: sin secretos; ojo permanente: nada sensible
  a git). Primera foto real desde el celular contra el VPS funcionó;
  instrucción de visión afinada con lo aprendido; mapeo Alegra ahora es
  migración semilla (0009) para ambientes nuevos. 101 tests.
- **Hecho (día 5):** HTTPS en producción — Luis montó proxy inverso en el
  VPS y la app vive en https://auxcontable.learnway.co (dominio en
  DJANGO_ALLOWED_HOSTS y DJANGO_CSRF_ORIGINS del .env del servidor, nunca
  editando settings.py en el clon). Panel del día en el inicio.
- **Hecho (día 5, §12):** 2FA TOTP con django-otp — activación con QR
  (SVG, sin pillow) en /seguridad/2fa/, verificación por sesión en el
  middleware, anti-repetición y throttling del propio django-otp, aviso
  persistente a admins sin 2FA en el panel. 108 tests.
- **Hecho (día 5):** afinado de visión P1.10 — preprocesamiento de foto
  (rotación EXIF + reducción a 1600px/JPEG con pillow), reintento
  auto-correctivo cuando subtotal+iva≠total (con confianza degradada si
  persiste), y cambio de modelo predeterminado por torneo (formal/tirilla/
  torcida): nvidia/nemotron-nano-12b-v2-vl 17/18 campos vs llama-90b 7/18.
  112 tests.
- **Hecho (día 5):** conexiones contables por empresa — modelo
  `ConexionContable` (credenciales Alegra por tenant, verificadas contra
  la API al guardar; token pendiente de cifrado en reposo antes de
  clientes reales), panel en Mis empresas → Conexiones (solo admin),
  `alegra._credenciales(empresa)` con respaldo al .env de la beta.
  2FA con emisor visible en la app autenticadora (OTP_TOTP_ISSUER).
  Soporte de proxy https por env (DJANGO_TRAS_PROXY=1: X-Forwarded-Proto,
  cookies seguras) — arregla el CSRF 403 del VPS junto con
  DJANGO_CSRF_ORIGINS. 117 tests.
- **Hecho (día 5, seguridad):** tokens de conexiones cifrados en reposo
  (core/cifrado.py, Fernet derivado de SECRET_KEY — si cambia, reconectar;
  valores heredados en claro se leen y se cifran al re-guardar) y códigos
  de respaldo del 2FA (otp_static: 8 códigos de un solo uso al activar,
  regenerables desde 2FA activo; /verificar/ acepta app o respaldo).
  122 tests.
- **Hecho (día 6, P8 núcleo):** nómina — app `nomina/`: Empleado y
  LiquidacionNomina por tenant, motor de liquidación mensual (auxilio si
  ≤2 SMMLV, deducciones 4+4, aportes patronales con exoneración art.
  114-1 configurable en Empresa, provisiones), asiento consolidado
  balanceado, un mes = una liquidación, aprobación humana. Casos P8 en la
  guía. SMMLV/auxilio 2026 ESTIMADOS (nomina/parametros.py — confirmar
  decretos). 132 tests.
- **Hecho (día 6, P9):** certificados de retención — `causacion/certificados.py`
  agrega por tercero y concepto desde facturas de compra aprobadas del año;
  las NC de proveedor descuentan la base; retención total cuadra con créditos
  a 2365 (P9.4). Listado en Terceros → Certificados y certificado individual
  imprimible. 138 tests.
- **Hecho (día 6, P8.8):** novedades de nómina — modelo NovedadNomina con
  efecto por tipo (constitutivo/no constitutivo/reduce_base/descuento);
  el motor ajusta base de aportes/provisiones y neto; asiento cuadra con
  descuentos en 237010. Pantalla Nómina → Novedades. 144 tests.
- **Hecho (día 6, P10):** activos fijos — app `activos/`: ActivoFijo por
  categoría (vida útil + cuentas PUC en parametros.py), DepreciacionMensual
  línea recta topada al valor depreciable (P10.2) y sin depreciar antes de
  adquirir (P10.5); aprobar actualiza depreciacion_acumulada; asiento por
  categoría cuadrado. 155 tests.
- **Consolidación multi-empresa (día 6, en curso):** panel de configuración
  por empresa (datos fiscales: ciudad, responsable IVA, RST, autorretenedor,
  agente retención, tarifa ICA, exoneración) y panel de usuarios (listar
  membresías, cambiar rol, quitar acceso, revocar invitaciones), ambos solo
  admin. 163 tests.
  - **Plan de cuentas por empresa HECHO:** `causacion/plan_cuentas.py`
    (CUENTAS_ESTANDAR = catálogo de ~45 roles con PUC por defecto;
    plan_de_empresa(empresa) mezcla overrides), modelo `CuentaContable`
    (rol→código/nombre por empresa). TODOS los motores refactorizados para
    resolver por rol: causación (clasificacion/ventas/servicios), nómina
    (calculo), activos (calculo), conciliación (motor). UI en Configuración
    → Plan de cuentas (solo admin). 168 tests.
  - **PostgreSQL HECHO (infra):** docker-compose con servicio `db`
    (postgres:16-alpine, volumen pgdata, healthcheck); el `web` recibe
    DATABASE_URL=postgres://… — el código NO cambió (dj_database_url).
    Local sigue en sqlite por defecto (arrancar.bat). requirements con
    psycopg[binary]. En el VPS: poner POSTGRES_PASSWORD en el .env, rebuild;
    migrate al arrancar crea esquema+semillas; falta solo createsuperuser
    (postgres arranca vacío). 168 tests.
  - **CONSOLIDACIÓN MULTI-EMPRESA COMPLETA.**
- **Hecho (día 6, P11):** caja menor — app `cajamenor/`: CajaMenor (fondo
  fijo), GastoCajaMenor (vales con categoría del plan), ReembolsoCajaMenor
  (legaliza vales, asiento gastos+IVA vs bancos, aprobación humana);
  efectivo disponible = monto − vales pendientes; no excede el fondo (P11.5);
  usa el plan de cuentas por empresa. 177 tests.
- **Sigue:** P8.9 pre-PILA/nómina electrónica; exógena 1001/1007;
  validación mes real XML DIAN (P7.1); confirmar calendario y SMMLV contra
  decretos; CSV contra Siigo real; buzón IMAP; P6.3; asistente IA normativo.

## Git

El repo se versiona en Windows (git dentro del sandbox no opera sobre OneDrive).
Primera vez:

```
git init -b main
git add .
git commit -m "Día 1: proyecto Django corriendo con configuración por .env"
```

Cada sesión termina con el proyecto corriendo, committeado y **pusheado**
(PLAN.md §8). Remoto: https://github.com/luisvahosh/auxiliar-contable-digital
(privado, `origin/main`).
Nota: OneDrive puede pelear con `.git/` — si molesta, mover el repo a una
carpeta fuera de OneDrive y dejar aquí solo los documentos.
