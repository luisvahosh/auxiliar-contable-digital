# Plan — Auxiliar Contable Digital (Colombia)

**Fecha:** 11 de julio de 2026 · **Dueño:** Luis Vahos · **Versión:** 4

---

## 1. Qué es (y qué no es)

Un software que **hace o apoya el trabajo del auxiliar contable**, operando *sobre* el software contable que la empresa ya usa (Siigo, Alegra, World Office). **No reemplaza el software contable — reemplaza o potencia las horas del auxiliar** que digita, cruza, verifica, organiza y persigue.

*"El auxiliar contable digital: causa, concilia, alerta y organiza — tu contador solo revisa y firma."*

**Clientes:** micro/pequeñas empresas (sin auxiliar de planta), contadores independientes (multiplican su capacidad), medianas empresas (descargan tareas repetitivas de su equipo).

## 2. Mapa completo de actividades del auxiliar contable

Base de las funciones según manuales de cargo y práctica colombiana. Columnas: qué tan automatizable es hoy con IA + APIs, y en qué fase del producto entra.

### A. Registro y control diario

| Actividad | Automatización | Fase |
|---|---|---|
| Causación de facturas de venta (ingresos) | Alta — ingesta XML factura electrónica → asiento vía API | 1 |
| Causación de compras, servicios públicos, honorarios | Alta — XML/PDF → clasificación PUC por IA → asiento | 1 |
| Comprobantes de egreso y recibos de caja | Alta — generación automática desde pagos registrados | 2 |
| Caja menor: registro, verificación de recibos, paquete de legalización | Media — foto del recibo → OCR + IA arma la legalización | 3 |
| Conciliación bancaria | Alta — extracto (CSV/PDF) vs. registros → cruce automático, excepciones a revisión humana | 2 |

### B. Nómina y seguridad social

| Actividad | Automatización | Fase |
|---|---|---|
| Liquidación de novedades (horas extra, recargos, incapacidades, licencias) | Media — cálculo automático, novedades las reporta un humano | 4 |
| Planilla PILA: generación y revisión de aportes (salud, pensión, ARL, CCF) | Media — pre-liquidación y revisión; presentación por operador PILA | 4 |
| Nómina electrónica DIAN | Media — generación y monitoreo de transmisión | 4 |
| Certificados laborales y de ingresos y retenciones (F. 220) | Alta — generación automática | 4 |

### C. Apoyo tributario

| Actividad | Automatización | Fase |
|---|---|---|
| Verificación de tarifas de retefuente, reteIVA, reteICA según régimen del proveedor | Alta — motor de reglas por RUT del tercero + validación en cada causación | 3 |
| Organizar certificados y base para declaraciones (renta, IVA, retefuente, ICA) | Alta — carpeta digital lista para el contador por período | 3 |
| Expedición de certificados de retención a terceros | Alta — generación masiva anual | 3 |
| Monitoreo de facturación electrónica: timbrado, envío, documento soporte, eventos RADIAN | Alta — verificación diaria contra DIAN, alerta de rechazos | 2 |
| Información exógena / medios magnéticos (nacional y distrital) | Media — pre-armado de formatos (1001, 1007, 2276…), validación de terceros; revisión del contador | 3 |
| Calendario tributario personalizado por NIT + alertas de vencimientos | Alta | 1 |
| Consultas normativas (asistente IA con fuentes: Estatuto Tributario, NIIF, resoluciones DIAN) | Alta — con disclaimer y citas | 1 |

### D. Cartera y proveedores

| Actividad | Automatización | Fase |
|---|---|---|
| Seguimiento a clientes morosos, envío de estados de cuenta | Alta — recordatorios automáticos por correo/WhatsApp | 2 |
| Registro de pagos recibidos y aplicación a facturas | Media — sugerencia automática, confirmación humana | 2 |
| Cuentas por pagar: programación y priorización de pagos | Media | 3 |

### E. Inventarios y activos fijos

| Actividad | Automatización | Fase |
|---|---|---|
| Registro de activos fijos y cálculo de depreciaciones | Alta — tabla de activos + asiento mensual automático | 3 |
| Apoyo al control de inventarios / kardex | Baja — depende del software contable; solo validaciones | Post-v1 |

### F. Informes y entidades de control

| Actividad | Automatización | Fase |
|---|---|---|
| Insumos para estados financieros (auxiliares por cuenta, terceros) | Media — reportes de apoyo, el contador proyecta | 3 |
| Flujo de caja proyectado | Media | 3 |
| Informes a entidades estatales (Supersociedades, etc.) | Baja — apoyo documental | Post-v1 |

### G. Archivo, auditoría y administrativo

| Actividad | Automatización | Fase |
|---|---|---|
| Archivo digital de comprobantes según normas de retención documental | Alta — repositorio organizado por período/tipo, búsqueda | 2 |
| Soporte en auditorías: entrega de documentación | Alta — exportación de paquetes por auditor | 3 |
| Apoyo en respuestas a requerimientos DIAN/UGPP | Media — recopila soportes, borrador con IA, revisa el contador | Post-v1 |
| Actualización RUT, renovación matrícula mercantil (recordatorios) | Alta — alertas con checklist | 1 |

**Resumen:** ~26 actividades mapeadas; ~15 de automatización alta. El corazón del negocio es automatizar las de digitación y cruce (causación, conciliación, monitoreo DIAN, cartera), que consumen el 70–80% del tiempo de un auxiliar.

## 3. MVP y fases (verticales completos, no piezas sueltas)

**Ancla económica:** un auxiliar contable cuesta ~$1.4–2.5M COP/mes (salario + prestaciones). Si la app hace el 60% de su trabajo por <$300K/mes, la venta se explica sola.

| Fase | Vertical completo | Semanas |
|---|---|---|
| **1 — Causación + cumplimiento** | Ingesta de facturas electrónicas (**descarga directa del portal DIAN** — estándar del mercado — + buzón de correo como complemento) → clasificación PUC por IA → asiento en Alegra/Siigo vía API (o export). + Calendario tributario por NIT con alertas. + Asistente IA normativo con citas. | 1–10 |
| **2 — Conciliación + cartera + archivo** | Conciliación bancaria por extracto, monitoreo facturación electrónica/RADIAN, recordatorios de cobro, archivo digital de comprobantes. | 11–18 |
| **3 — Tributario profundo** | Motor de retenciones por tercero, carpetas de declaración por período, certificados de retención, pre-armado de exógena, caja menor, activos fijos. | 19–30 |
| **4 — Nómina** | Novedades, pre-PILA, nómina electrónica, certificados. (Última por complejidad regulatoria y riesgo.) | Según tracción |

### Lo que NO hace la v1
- No es software contable: no lleva libros ni emite facturas — se integra con el que exista.
- No presenta declaraciones ni PILA ante entidades: prepara, el humano presenta.
- No firma nada: todo pasa por revisión del contador (Ley 43 de 1990).
- No maneja inventarios ni multi-país.

### Principio de diseño: humano en el circuito
Cada acción automática tiene tres niveles configurables: **automática** (asientos rutinarios de alta confianza), **sugerida** (la app propone, el usuario aprueba con un clic), **manual** (casos ambiguos van a bandeja de revisión). La confianza del cliente se gana mostrando el porqué de cada clasificación.

## 4. Stack

- **Backend:** Django + PostgreSQL (pgvector para RAG normativo). Celery para tareas programadas (monitoreo DIAN, alertas, conciliaciones).
- **Integraciones (núcleo del producto):** **API de Alegra primero** (registro gratuito, API pública bien documentada — cuenta de prueba sin costo). El plan de facturación Siigo de Luis **no incluye credenciales API** (solo los planes Nube Profesional/Independiente/Emprendedor/Premium las tienen), así que la integración Siigo se hace vía **export CSV** desde el día 1 y vía API cuando haya un beta con plan Siigo que la incluya. Export genérico (CSV/Excel) para el resto.
- **Beta cero (dogfooding):** la empresa propia de Luis. Sus XML de ventas (emitidas por Siigo) y compras están en el portal DIAN con su NIT — el kit de datos reales no depende de la API de Siigo.
- **Ingesta:** **descarga masiva desde el portal DIAN** (automatización del portal — no hay API pública; todos los competidores lo hacen así, es el estándar esperado) + buzón de correo dedicado por cliente como complemento; carga manual de PDF/extractos; OCR para recibos. Riesgo técnico a validar en semana 1–2: estabilidad del acceso al portal DIAN (captchas, cambios de HTML) — plan B: el buzón de correo y carga manual siempre funcionan.
- **IA — RAG vía API gratuita de NVIDIA (build.nvidia.com / NIM):**
  - Endpoints **compatibles con OpenAI** (`integrate.api.nvidia.com/v1`): un solo cliente en el código, cambiar de modelo es cambiar un string. Key gratuita (`nvapi-…`), sin costo por token en el tier de desarrollo.
  - Modelos: uno de embeddings (p. ej. NV-Embed / `bge-m3` del catálogo) + un LLM fuerte en español (Llama 3.x / Qwen del catálogo) — evaluar con 20 preguntas normativas reales antes de fijar.
  - **Límites del tier gratuito:** ~40 req/min (ampliable a 200 solicitándolo). Suficiente para desarrollo y betas; el diseño debe encolar (Celery) y cachear respuestas frecuentes para no chocar con el límite.
  - **Proveedor detrás de una interfaz única:** al ser OpenAI-compatible, migrar a otro proveedor (Claude, OpenAI, u Ollama autohospedado si algún día hay GPU propia) es cambiar base URL + key. Decisión 100% reversible.
  - **Ojo para producción:** el tier gratuito es de prueba/desarrollo — los términos no garantizan SLA ni uso comercial ilimitado. Antes del lanzamiento pago, validar términos o presupuestar el paso a un tier pago/otro proveedor. Además, los datos viajan a un tercero: no enviar datos identificables innecesarios en los prompts (minimización, Ley 1581).
  - Validar en semana 1–2: calidad en texto legal colombiano, latencia, y comportamiento del rate limit con carga real.
- **Frontend:** Django + HTMX; web responsive.
- **Pagos:** **sin botón de pago en la plataforma.** Cobro fuera de la app (factura + transferencia/consignación). El panel interno de admin registra el estado de cada tenant (activo, en prueba, moroso, suspendido) y la app solo lee ese estado para permitir o restringir acceso. Ventaja: cero superficie de ataque de pagos, cero comisiones de pasarela; se puede añadir pasarela después sin tocar el resto.
- **Infra — desarrollo local primero, contenedor después:**
  - **Fase de desarrollo (ahora):** todo corre local sin Docker — Python/venv + PostgreSQL y Redis instalados en la máquina. Cero fricción de infraestructura mientras se construye el MVP.
  - **Regla que hace indoloro el salto a Docker después:** configuración 100% por variables de entorno (archivo `.env`, 12-factor) desde el día 1 — nada de rutas ni credenciales quemadas en el código. Si esto se respeta, contenerizar luego es escribir un `Dockerfile`, no reescribir la app.
  - **Fase de despliegue (proyecto avanzado):** contenerizar (app + PostgreSQL+pgvector + Redis + worker Celery + beat) y subir a **nuestra propia infraestructura** (VPS/cloud).
  - **Modelo SaaS:** el cliente nunca instala nada — consume el servicio por web con su cuenta. Una sola instalación multi-tenant que nosotros operamos, actualizamos y respaldamos.

## 5. Modelo de negocio

Comparación de venta: no contra software contable ($45–139K/mes) sino contra **horas de auxiliar** ($1.4–2.5M/mes).

**Sin precios públicos.** Venta consultiva: la web no publica tarifas — el precio se acuerda en la llamada/demo según NITs, volumen de documentos y módulos. (Mismo enfoque de Cifrato, el líder del segmento.) Ventajas: evita la guerra de precios con Back Contable ($89K/mes publicado) y N1 ($600/causación publicado), permite cobrar por valor y ajustar por cliente sin tocar la web. Los niveles internos de referencia (Básico / Pyme / Contador / Empresarial, escalados por NITs y volumen) se mantienen como guía comercial interna, no publicada.

**Segmentos (los tres son cuña, con mensajes distintos):**

| Segmento | Mensaje de venta |
|---|---|
| Contador independiente | Multiplica tu capacidad: más NITs con el mismo tiempo |
| Pyme sin auxiliar | El 60% del trabajo del auxiliar por una fracción del costo |
| Firma de outsourcing / BPO | Escala tu operación sin crecer nómina |

Prueba de 14 días con datos reales del cliente (importar su último mes y mostrarle el trabajo hecho — esa es la demo que vende).

**Cobro:** sin botón de pago en la plataforma. Facturación mensual manual (factura electrónica + transferencia); el admin actualiza el estado del tenant en el panel interno. Coherente con la venta consultiva (matrícula por invitación, sección 12): quien entra ya cerró trato con nosotros.

## 6. Competencia y defensa

**La causación automática con IA ya es un mercado activo en Colombia (verificado jul-2026).** El posicionamiento es **"auxiliar contable completo"**: la causación es la puerta de entrada, pero se vende el paquete que nadie más junta — calendario tributario + alertas, asistente normativo con citas, cartera, archivo, exógena, certificados.

| Competidor | Qué hace | Precio | Debilidad explotable |
|---|---|---|---|
| **[Cifrato](https://cifrato.ai/)** (YC) | Causación + conciliación, descarga DIAN/SII/SAT, +50 integraciones, +1M facturas | No público (caro según competencia) | Solo causación/conciliación — no calendario, ni asistente normativo, ni cartera |
| **[Back Contable](https://backcontable.com/)** (Medellín) | IA + equipo contable humano valida cada asiento; descarga DIAN, retenciones, conciliación | Desde $89K/mes | El humano en su nómina no escala; sin verticales de cumplimiento |
| **[N1](https://n1.app/)** | DIAN → Alegra/Siigo, pago por uso | $600/causación | Solo causación, sin plataforma |
| **[SyncManager](https://www.sync-manager.com/contabilidad/)** | Agente IA CO+CL, Siigo/SAP | No público | Generalista multi-industria, piloto temprano |
| **[Alegra IA](https://www.alegra.com/colombia/ia/)** | Factura por foto/WhatsApp, conciliación IA — el riesgo "lo construyen ellos" ya empezó | Incluido en Alegra | Solo sirve a su propia base; no cubre Siigo/World Office |

- **Defensa central:** amplitud (26 actividades vs. 1–2 de los competidores), foco Colombia-profundo (retenciones, exógena, RADIAN, calendario por NIT), multi-marca de software contable, y niveles de confianza self-serve (la validación humana es del cliente, no de nuestra nómina — escala mejor que Back Contable).
- **Auxiliares tercerizados / BPO contable:** competencia en precio — la app es 5–10x más barata; y los BPO son también segmento cliente.
- **IA genérica:** no se integra con Siigo/Alegra ni monitorea DIAN.

## 7. Riesgos

| Riesgo | Mitigación |
|---|---|
| Asiento mal clasificado → declaración errónea | Niveles de confianza, bandeja de revisión, trazabilidad de cada asiento, el contador aprueba |
| Ejercicio ilegal de la contaduría (Ley 43/1990) | La app prepara y el humano firma; asesoría legal antes de lanzar |
| Dependencia de APIs de terceros (Alegra/Siigo cambian condiciones) | Export genérico siempre disponible como plan B; multi-integración |
| Portal DIAN sin API pública (captchas, cambios de HTML rompen la descarga) | Buzón de correo + carga manual como respaldo permanente; monitoreo del scraper con alertas |
| Competidores establecidos en causación (Cifrato con capital YC, Back Contable en precio) | No competir en causación sola: vender el paquete completo; velocidad en los verticales que ellos no tienen |
| Cambio normativo (tarifas, formatos exógena, calendario) | Pipeline de actualización normativa como proceso central |
| Habeas data — datos financieros sensibles (Ley 1581) | Cifrado, mínimo dato, política de datos día 1 |
| Errores en nómina/PILA (sanciones UGPP) | Por eso nómina es la fase 4, no la 1 |

## 8. Arranque (reglas Fable)

**Semana 1 — vertical feo pero completo y desplegado:**
- Día 1: `git init`, CLAUDE.md (cómo correr, probar, convenciones), estructura de carpetas, proyecto Django corriendo local con `.env` y un "hola" visible en el navegador.
- Días 2–5: subir un XML de factura electrónica **de nuestra propia empresa** (descargado del portal DIAN) → la app extrae datos → propone cuenta PUC → genera el asiento en Alegra (cuenta de prueba gratuita vía API) + export CSV formato Siigo. Un flujo, de punta a punta, con datos reales desde el día 2.

**Semanas 1–2 (en paralelo):** validar el RAG con la API de NVIDIA — indexar 2–3 normas clave, probar 2–3 modelos del catálogo con 20 preguntas reales de contador, medir calidad, latencia y rate limit. Si un modelo no pasa, cambiar el string del modelo y repetir. **Y spike técnico de la descarga DIAN:** probar la automatización del portal (login, descarga masiva de XML) con un NIT real — si resulta frágil, el buzón de correo sube a plan A del MVP y el portal pasa a fase 2.

**Semanas 2–4:** buzón de correo para ingesta automática, bandeja de revisión con niveles de confianza (siguiendo el sistema de diseño de la sección 11), calendario tributario 2026 por NIT, login + matrícula por token de invitación (sección 12) con aislamiento multi-tenant probado por tests.

**Semanas 5–10:** asistente IA normativo, alertas correo/WhatsApp, **contenerización + primer despliegue en nuestra infraestructura** (los betas necesitan URL en línea), **auditoría de seguridad #1** (antes del primer beta con datos reales), gestión de estado de suscripción en el panel admin (cobro fuera de la app), landing, 5–10 betas (ideal 2–3 contadores con sus clientes).

**Cada sesión termina con el proyecto corriendo y committeado.**

## 9. Métricas de éxito

- MVP: 10 empresas beta procesando facturas reales en la semana 10.
- ≥85% de clasificaciones PUC aceptadas sin corrección (medido en la bandeja de revisión).
- Tiempo de causación por documento: de ~5 min manuales a <30 seg de revisión.
- ≥5 clientes pagando al mes 4; churn <10% desde el mes 3.

## 10. Seguridad (marco Fable — auditor, no porrista)

Datos financieros + credenciales de APIs contables + servidor de IA propio = superficie de ataque seria. La seguridad se integra por fase, no al final.

### Superficie de ataque a mapear (antes de codificar)
- **Entradas externas:** buzón de correo de ingesta (XML/PDF adjuntos de remitentes desconocidos — vector principal), formularios web. (Sin pasarela de pagos: no hay webhooks ni datos de tarjetas — superficie eliminada.)
- **Salidas a terceros:** API de NVIDIA (prompts con contenido de documentos — minimizar datos identificables), APIs Alegra/Siigo.
- **Secretos:** key de NVIDIA (`nvapi-…`), tokens de API Alegra/Siigo por cliente, llaves de correo. Variables de entorno / gestor de secretos desde el día 1; nunca en código, en git ni horneados en la imagen Docker (revisar historial y capas de imagen en cada auditoría).
- **Datos sensibles:** información tributaria y financiera de terceros (Ley 1581 — habeas data).

### Orden de revisión en cada auditoría (no se cambia)
1. Secretos en código o historial de git.
2. Validación de entrada por endpoint — crítico en el parser de XML (XXE, archivos malformados, adjuntos maliciosos) y OCR de recibos.
3. **Autorización, no solo autenticación:** multi-tenant estricto — ¿puede el cliente A ver asientos, facturas o NIT del cliente B cambiando un id? Aislamiento por tenant en cada query (test automatizado obligatorio).
4. Inyección: SQL, comandos, XSS — y **prompt injection**: texto de una factura maliciosa no puede convertirse en instrucciones para el LLM (sanitizar/delimitar todo contenido de documentos antes de pasarlo al modelo).
5. Fugas: datos financieros en logs, mensajes de error o respuestas de API con campos de más.
6. Dependencias: `pip audit` en CI.

### Reglas
- Cada hallazgo: archivo+línea, severidad, cómo se explota. Sin genéricos.
- **Puntos de control:** auditoría con `fable-chequeo-seguridad` (a) antes del primer beta con datos reales, (b) antes del lanzamiento comercial, (c) antes de la fase de nómina, y (d) tras cada integración nueva.
- Secretos en `.env` local (fuera de git vía `.gitignore` desde el primer commit); al contenerizar: imagen sin secretos, usuario no-root, dependencias fijadas, escaneo de imagen (`trivy`), Redis y PostgreSQL nunca expuestos públicamente.
- IA externa: no registrar prompts con datos de clientes; minimizar datos identificables enviados a NVIDIA.
- Cifrado en reposo (PostgreSQL) y tránsito (TLS), backups cifrados probados.

## 11. Diseño UI/UX (marco ui-ux-pro-max)

Producto = SaaS financiero data-denso. La percepción de **confiabilidad y precisión** es el diseño: un error visual en una cifra mata la confianza en toda la app.

### Sistema de diseño
- **Estilo:** minimalismo profesional (flat, sin efectos decorativos). Un solo estilo en todas las páginas.
- **Color:** tokens semánticos, no hex sueltos: `primary` (azul confianza), `success` / `warning` / `danger` (estados de asientos y vencimientos — siempre con ícono + texto, nunca solo color), `surface` / `on-surface`. Contraste mínimo 4.5:1.
- **Tipografía:** sans-serif legible (Inter o similar), base 16px, line-height 1.5, escala consistente (12/14/16/18/24/32). **Cifras en números tabulares** (`font-variant-numeric: tabular-nums`) — obligatorio en tablas contables para que las columnas no bailen.
- **Íconos:** un solo set SVG (Lucide/Heroicons), nunca emojis; tamaño tokenizado.
- **Espaciado:** sistema de 4/8px; máx-width consistente en desktop; mobile-first (los contadores revisan desde el celular).

### Patrones clave del producto
- **Bandeja de revisión** (el corazón de la app): tabla con filas de asientos propuestos, nivel de confianza visible (badge con % + color + ícono), aprobación con un clic, virtualización si hay 50+ filas, orden por teclado (`aria-sort`), estados vacíos con guía ("no hay documentos pendientes — así conectas tu buzón").
- **Formularios:** labels visibles (nunca solo placeholder), validación on-blur, error junto al campo con causa + cómo corregir, tipos semánticos (NIT → teclado numérico).
- **Feedback:** toda acción asíncrona (causación, conciliación) muestra estado en <100 ms, skeleton si tarda >1 s, confirmación antes de acciones destructivas, undo donde sea posible.
- **Navegación:** sidebar en desktop (≥1024px), navegación inferior ≤5 ítems en móvil, ubicación actual siempre resaltada, deep links a cada documento/período.
- **Accesibilidad:** foco visible, navegación completa por teclado, `prefers-reduced-motion`, jerarquía h1→h6 correcta.
- **Anti-patrones prohibidos:** gráficos que dependen solo del color, animaciones decorativas, hover como única interacción, texto <12px en cifras.

### Checklist pre-entrega de cada pantalla
Contraste AA, targets táctiles ≥44px, sin scroll horizontal en 375px, números tabulares en toda tabla, estados cargando/vacío/error definidos, probado en móvil.

## 12. Acceso e identidad (login y matrícula de empresas)

**Principio: no hay registro abierto.** Solo entran empresas matriculadas, y ninguna empresa puede saber qué otras empresas existen en la plataforma.

### Flujo de matrícula por token de invitación
1. **Matrícula (nosotros):** al cerrar la venta, el admin registra la empresa (razón social, NIT, plan) en el panel interno. La empresa queda creada como tenant, sin usuarios aún.
2. **Invitación:** el sistema genera un **token de un solo uso** (aleatorio ≥32 bytes, con expiración de 72 h, guardado hasheado) y envía el enlace al correo del contacto: `https://app.../registro/<token>`.
3. **Registro del usuario:** el enlace abre un formulario donde la persona define correo y contraseña. El token muere al usarse; queda vinculada a su empresa y solo a ella.
4. **Usuarios adicionales:** un usuario administrador de la empresa puede invitar colegas (mismo mecanismo de token), siempre dentro de su propio tenant. Roles: admin de empresa / operador / solo-lectura. El caso del plan Contador: un mismo usuario puede estar vinculado a varios tenants y cambia de empresa activa con un selector — nunca ve datos de dos a la vez.

### Página de login
- Correo + contraseña. Diseño según sección 11: formulario centrado, labels visibles, error junto al campo, toggle mostrar/ocultar contraseña, mínimo 16px, targets ≥44px.
- **El mensaje de error nunca revela qué falló:** "correo o contraseña incorrectos" — jamás "ese correo no existe" (evita enumerar usuarios/empresas).
- Protecciones desde el día 1: rate limiting por IP y por cuenta (p. ej. django-axes), bloqueo temporal tras N intentos, contraseñas con validadores de Django (longitud mínima, no comunes), hash Argon2. Recuperación de contraseña por enlace de un solo uso con la misma disciplina de tokens.
- 2FA (TOTP) como mejora en fase 2 — obligatoria para usuarios admin.

### Invisibilidad entre empresas (refuerza sección 10)
- Ningún endpoint lista, cuenta ni sugiere empresas. Sin autocompletar de razones sociales, sin "empresas que usan la plataforma" en la app.
- Identificadores públicos en URLs son **UUID**, nunca ids secuenciales (un id `47` invita a probar el `48`).
- Todas las queries pasan por un manager de Django que filtra por el tenant de la sesión — imposible olvidarlo por convención; test automatizado que intenta acceso cruzado entre dos tenants en cada CI.
- El subdominio/URL no revela clientes (una sola app en `app.dominio.com`, no `cliente.dominio.com`).

---

*Fuentes: [funciones del auxiliar contable — Gerencie](https://www.gerencie.com/funciones-del-auxiliar-contable.html), [5 funciones clave — Magneto](https://www.magneto365.com/co/blog/funciones-auxiliar-contable-colombia), [información exógena — Alegra](https://blog.alegra.com/colombia/que-son-los-medios-magneticos/), [perfil OCUPACOL MinTrabajo](https://ocupacol.mintrabajo.gov.co/Profile/OccupationalProfile/43110), [precios software contable 2026](https://programascontabilidad.com/comparativas-de-software/precios-de-software-contable-colombia-2026/).*
