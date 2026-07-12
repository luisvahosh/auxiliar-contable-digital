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
- **Sigue (validación con realidad):** P7.1 con un mes real de la empresa
  (XML reales del portal DIAN); confirmar fechas del calendario contra el
  decreto; CSV contra importación real Siigo. Luego: buzón IMAP (lee
  facturas del correo, sobre procesar_xml), P6.3 monitoreo DIAN (spike
  portal), 2FA admin.

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
