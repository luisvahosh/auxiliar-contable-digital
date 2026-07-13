import re
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.contrib import messages
from django.db import IntegrityError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from . import alegra, vision
from .cartera import RANGOS, edades_de_cartera
from .clasificacion import calcular_retencion, clasificar, construir_asiento
from core.tenancy import rol_en_empresa

from .clasificacion import Propuesta, cuentas_reclasificables
from .forms import (
    TIPOS_IMAGEN,
    FormularioConexionAlegra,
    FormularioFacturaFisica,
    FormularioFotoFactura,
    FormularioReclasificacion,
    FormularioSubirFactura,
    FormularioTercero,
)
from .models import (
    ConexionContable,
    CuentaContable,
    FacturaCompra,
    FacturaVenta,
    MapeoCuentaAlegra,
    Tercero,
)
from .plan_cuentas import plan_de_empresa
from .parser import FacturaParseada, Linea
from .servicios import procesar_xml, tercero_del_emisor
from .siigo import generar_csv_siigo
from .ventas import consecutivos_faltantes

CARPETA_FOTOS = "facturas_fisicas"
# Solo nombres que nosotros mismos generamos (anti path-traversal)
PATRON_NOMBRE_FOTO = re.compile(r"[0-9a-f]{32}\.(jpg|png|webp)")


def _empresa_activa(request):
    """Tenant del request: lo resuelve el middleware desde la sesión (§12)."""
    return request.empresa


# ---------- Subida única: la app decide si es compra, venta o nota crédito ----------

def subir(request):
    empresa = _empresa_activa(request)
    formulario = FormularioSubirFactura(request.POST or None, request.FILES or None)

    if request.method == "POST" and formulario.is_valid():
        resultado = procesar_xml(empresa, formulario.cleaned_data["archivo"].read())
        if resultado.estado == "error":
            messages.error(request, resultado.mensaje)
            return render(request, "causacion/subir.html", {"formulario": formulario})
        if resultado.estado == "duplicado":
            messages.warning(request, resultado.mensaje)
        else:
            messages.success(request, resultado.mensaje)
            if resultado.tipo == "venta":
                _alertar_consecutivo(request, empresa)
        destino = ("causacion:detalle" if resultado.tipo in ("compra", "nc_compra")
                   else "causacion:detalle_venta")
        return redirect(destino, pk=resultado.documento.pk)

    return render(request, "causacion/subir.html", {"formulario": formulario})


def _alertar_consecutivo(request, empresa):
    """Control P2.3: avisar si falta alguna factura en la numeración."""
    numeros = FacturaVenta.objects.de_empresa(empresa).filter(
        tipo="venta").values_list("numero", flat=True)
    faltantes = consecutivos_faltantes(numeros)
    if faltantes:
        messages.warning(
            request,
            "Hueco en el consecutivo de facturación: falta " + ", ".join(faltantes) +
            ". Verifica en la DIAN si fueron anuladas o no se han descargado.",
        )


# ---------- Bandejas y detalles ----------

def bandeja(request):
    empresa = _empresa_activa(request)
    facturas = FacturaCompra.objects.de_empresa(empresa)
    return render(request, "causacion/bandeja.html", {
        "empresa": empresa,
        "facturas": facturas,
        "pendientes": facturas.filter(estado="pendiente").count(),
    })


def bandeja_ventas(request):
    empresa = _empresa_activa(request)
    ventas = FacturaVenta.objects.de_empresa(empresa)
    faltantes = consecutivos_faltantes(
        ventas.filter(tipo="venta").values_list("numero", flat=True))
    return render(request, "causacion/bandeja_ventas.html", {
        "empresa": empresa,
        "ventas": ventas,
        "pendientes": ventas.filter(estado="pendiente").count(),
        "faltantes": faltantes,
    })


def _renglones_decimales(asiento):
    renglones = [
        {**r, "debito": Decimal(r["debito"]), "credito": Decimal(r["credito"])}
        for r in asiento
    ]
    return {
        "renglones": renglones,
        "total_debitos": sum(r["debito"] for r in renglones),
        "total_creditos": sum(r["credito"] for r in renglones),
    }


def detalle(request, pk):
    empresa = _empresa_activa(request)
    factura = get_object_or_404(FacturaCompra.objects.de_empresa(empresa), pk=pk)
    return render(request, "causacion/detalle.html", {
        "factura": factura,
        "alegra_configurado": alegra.esta_configurado(empresa),
        **_renglones_decimales(factura.asiento),
    })


def detalle_venta(request, pk):
    empresa = _empresa_activa(request)
    venta = get_object_or_404(FacturaVenta.objects.de_empresa(empresa), pk=pk)
    return render(request, "causacion/detalle_venta.html", {
        "venta": venta,
        "alegra_configurado": alegra.esta_configurado(empresa),
        **_renglones_decimales(venta.asiento),
    })


# ---------- Factura física fotografiada (P1.10) ----------

def foto(request):
    """Paso 1: subir/tomar la foto; si la IA de visión está configurada,
    extrae los campos y prellena el formulario de confirmación."""
    formulario = FormularioFotoFactura(request.POST or None, request.FILES or None)
    if request.method == "POST" and formulario.is_valid():
        archivo = formulario.cleaned_data["foto"]
        contenido = archivo.read()
        nombre = f"{uuid4().hex}{TIPOS_IMAGEN[archivo.content_type]}"
        carpeta = Path(settings.MEDIA_ROOT) / CARPETA_FOTOS
        carpeta.mkdir(parents=True, exist_ok=True)
        (carpeta / nombre).write_bytes(contenido)

        iniciales, confianza = {}, None
        if vision.esta_configurada():
            try:
                campos = vision.extraer_campos(contenido, archivo.content_type)
                confianza = campos.pop("confianza", None)
                iniciales = {clave: valor for clave, valor in campos.items()
                             if valor not in (None, "")}
                if "nit_emisor" in iniciales:
                    iniciales["nit_emisor"] = re.sub(r"\D", "", str(iniciales["nit_emisor"]))
                messages.info(request,
                              "Campos extraídos por la IA de visión: revísalos UNO POR UNO "
                              "contra la factura antes de causar.")
            except vision.ErrorVision as error:
                messages.warning(request,
                                 f"No se pudieron extraer los campos ({error}) — "
                                 "digítalos manualmente; la foto queda como soporte.")
        else:
            messages.info(request,
                          "La IA de visión no está configurada (NVIDIA_API_KEY en .env): "
                          "digita los campos manualmente; la foto queda como soporte.")
        return render(request, "causacion/foto_confirmar.html", {
            "formulario": FormularioFacturaFisica(initial=iniciales),
            "nombre_foto": nombre,
            "confianza": confianza,
        })
    return render(request, "causacion/foto.html", {"formulario": formulario})


@require_POST
def foto_causar(request):
    """Paso 2: el usuario confirmó los campos → causar como SUGERIDA (P1.10)."""
    empresa = _empresa_activa(request)
    nombre_foto = request.POST.get("nombre_foto", "")
    if not PATRON_NOMBRE_FOTO.fullmatch(nombre_foto):
        messages.error(request, "Referencia de foto inválida; vuelve a subirla.")
        return redirect("causacion:foto")

    formulario = FormularioFacturaFisica(request.POST)
    if not formulario.is_valid():
        return render(request, "causacion/foto_confirmar.html", {
            "formulario": formulario, "nombre_foto": nombre_foto, "confianza": None,
        })
    campos = formulario.cleaned_data

    # Sin CUFE (papel): antiduplicado por NIT + número + fecha.
    pseudo_cufe = f"FISICA:{campos['nit_emisor']}:{campos['numero']}:{campos['fecha'].isoformat()}"
    existente = FacturaCompra.objects.de_empresa(empresa).filter(cufe=pseudo_cufe).first()
    if existente:
        messages.warning(request, f"La factura {existente.numero} de ese proveedor y fecha "
                                  "ya fue causada. No se creó un asiento doble.")
        return redirect("causacion:detalle", pk=existente.pk)

    datos = FacturaParseada(
        cufe=pseudo_cufe,
        numero=campos["numero"],
        fecha_emision=campos["fecha"],
        nota=campos["concepto"],
        nit_emisor=campos["nit_emisor"],
        nombre_emisor=campos["nombre_emisor"],
        tipo_persona_emisor=campos["tipo_persona"],
        responsabilidad_emisor="",
        nit_adquiriente=empresa.nit,
        nombre_adquiriente=empresa.razon_social,
        subtotal=campos["subtotal"],
        iva=campos["iva"],
        total=campos["total"],
        lineas=[Linea(descripcion=campos["concepto"], cantidad=Decimal("1"),
                      valor=campos["subtotal"])],
        tipo_documento="factura",
        retefuente_practicada=Decimal("0"),
        referencia_numero="",
        referencia_cufe="",
    )
    plan = plan_de_empresa(empresa)
    tercero = tercero_del_emisor(empresa, datos)
    propuesta = clasificar(datos, plan)
    retencion = calcular_retencion(datos, propuesta.concepto, tercero, plan)
    renglones = construir_asiento(datos, propuesta, retencion, plan)
    try:
        factura = FacturaCompra.objects.create(
            empresa=empresa,
            cufe=pseudo_cufe,
            numero=datos.numero,
            fecha_emision=datos.fecha_emision,
            nit_emisor=datos.nit_emisor,
            nombre_emisor=datos.nombre_emisor,
            tipo_persona_emisor=datos.tipo_persona_emisor,
            responsabilidad_emisor="",
            subtotal=datos.subtotal,
            iva=datos.iva,
            total=datos.total,
            retencion=retencion.valor,
            cuenta_puc=propuesta.cuenta,
            nombre_cuenta_puc=propuesta.nombre_cuenta,
            concepto_retencion=propuesta.concepto,
            nivel="sugerida",  # P1.10: lo que viene de foto NUNCA es automático
            explicacion=("Causada desde foto de factura física: campos confirmados "
                         "por el usuario; entra siempre como sugerida (P1.10).\n"
                         f"{propuesta.explicacion}\n{retencion.porque}"),
            asiento=renglones,
            xml_crudo="(factura física — el soporte es la fotografía adjunta)",
            origen="foto",
            imagen=f"{CARPETA_FOTOS}/{nombre_foto}",
        )
    except IntegrityError:
        messages.warning(request, "Esa factura ya fue causada.")
        return redirect("causacion:bandeja")

    messages.success(request, f"Factura física {factura.numero} causada como sugerida, "
                              "pendiente de tu aprobación.")
    return redirect("causacion:detalle", pk=factura.pk)


# ---------- Plan de cuentas por empresa (consolidación multi-empresa) ----------

def plan_cuentas_vista(request):
    """El admin ajusta el código/nombre de cada rol de cuenta a SU plan."""
    from core.tenancy import rol_en_empresa

    from .plan_cuentas import CUENTAS_ESTANDAR, GRUPOS, plan_de_empresa
    empresa = _empresa_activa(request)
    if rol_en_empresa(request, empresa) != "admin":
        messages.error(request, "Solo el administrador puede editar el plan de cuentas.")
        return redirect("core:inicio")

    if request.method == "POST":
        personalizados = 0
        for rol, (est_cod, est_nom) in CUENTAS_ESTANDAR.items():
            codigo = request.POST.get(f"codigo_{rol}", "").strip()
            nombre = request.POST.get(f"nombre_{rol}", "").strip() or est_nom
            if codigo and (codigo, nombre) != (est_cod, est_nom):
                CuentaContable.objects.update_or_create(
                    empresa=empresa, rol=rol,
                    defaults={"codigo": codigo, "nombre": nombre})
                personalizados += 1
            else:
                # Volver al estándar: borrar el override si existía
                CuentaContable.objects.de_empresa(empresa).filter(rol=rol).delete()
        messages.success(request, f"Plan de cuentas guardado ({personalizados} "
                                  "cuenta(s) personalizada(s); el resto usa el PUC estándar).")
        return redirect("causacion:plan_cuentas")

    plan = plan_de_empresa(empresa)
    grupos = []
    for titulo, roles in GRUPOS:
        filas = []
        for rol in roles:
            codigo, nombre = plan[rol]
            est_cod, est_nom = CUENTAS_ESTANDAR[rol]
            filas.append({"rol": rol, "codigo": codigo, "nombre": nombre,
                          "personalizada": (codigo, nombre) != (est_cod, est_nom)})
        grupos.append({"titulo": titulo, "filas": filas})
    return render(request, "causacion/plan_cuentas.html", {"grupos": grupos})


# ---------- Buzón de correo: ingesta automática de facturas (PLAN §4) ----------

def buzon(request):
    """Configurar el buzón de correo y revisarlo bajo demanda (solo admin)."""
    from core.tenancy import rol_en_empresa

    from .buzon import BuzonError, revisar_buzon
    from .forms import FormularioBuzon
    from .models import BuzonCorreo

    empresa = _empresa_activa(request)
    if rol_en_empresa(request, empresa) != "admin":
        messages.error(request, "Solo el administrador puede configurar el buzón.")
        return redirect("core:inicio")

    instancia = BuzonCorreo.objects.de_empresa(empresa).first()

    if request.method == "POST" and request.POST.get("accion") == "revisar":
        if instancia is None or not instancia.activo:
            messages.error(request, "Configura y activa el buzón primero.")
            return redirect("causacion:buzon")
        try:
            resumen = revisar_buzon(instancia)
        except BuzonError as error:
            messages.error(request, f"No se pudo revisar el buzón: {error}")
            return redirect("causacion:buzon")
        messages.success(
            request,
            f"Buzón revisado: {resumen.correos} correo(s), {resumen.creados} "
            f"factura(s) nueva(s), {resumen.duplicados} ya causada(s), "
            f"{resumen.errores} con error. Revisa las bandejas: quedan pendientes.")
        return redirect("causacion:bandeja")

    formulario = FormularioBuzon(request.POST or None, instance=instancia)
    if request.method == "POST" and request.POST.get("accion") == "guardar":
        if formulario.is_valid():
            nuevo = formulario.save(commit=False)
            nuevo.empresa = empresa
            if formulario.cleaned_data.get("clave"):
                nuevo.clave = formulario.cleaned_data["clave"]
            elif instancia:
                nuevo.clave = instancia.clave  # conservar la guardada
            nuevo.save()
            messages.success(request, "Buzón guardado. Usa «Revisar ahora» para "
                                      "traer las facturas pendientes.")
            return redirect("causacion:buzon")

    return render(request, "causacion/buzon.html", {
        "formulario": formulario, "buzon": instancia,
    })


# ---------- Conexiones contables por empresa (PLAN §4) ----------

def conexiones(request):
    """El admin de la empresa conecta SU cuenta del software contable."""
    empresa = _empresa_activa(request)
    if rol_en_empresa(request, empresa) != "admin":
        messages.error(request, "Solo el administrador de la empresa puede "
                                "configurar las conexiones contables.")
        return redirect("core:inicio")

    conexion = (ConexionContable.objects.de_empresa(empresa)
                .filter(proveedor="alegra").first())
    formulario = FormularioConexionAlegra(
        request.POST or None,
        initial={"usuario": conexion.usuario} if conexion else {})

    if request.method == "POST" and formulario.is_valid():
        usuario = formulario.cleaned_data["usuario"]
        token = formulario.cleaned_data["token"]
        funciona, detalle = alegra.probar(usuario, token)
        if funciona:
            ConexionContable.objects.update_or_create(
                empresa=empresa, proveedor="alegra",
                defaults={"usuario": usuario, "token": token, "activa": True})
            messages.success(request, f"Conexión con Alegra verificada y guardada "
                                      f"(cuenta: {detalle}).")
            return redirect("causacion:conexiones")
        messages.error(request, f"No se guardó: {detalle}.")

    return render(request, "causacion/conexiones.html", {
        "conexion": conexion,
        "formulario": formulario,
        "hay_respaldo_global": alegra.esta_configurado(),  # .env de la beta
    })


# ---------- Reclasificación manual (cierra P1.7) ----------

def reclasificar(request, pk):
    """El usuario corrige la cuenta PUC de una compra pendiente o rechazada:
    se recalculan retención y asiento y vuelve a la bandeja como manual."""
    empresa = _empresa_activa(request)
    factura = get_object_or_404(
        FacturaCompra.objects.de_empresa(empresa), pk=pk,
        tipo="compra", estado__in=["pendiente", "rechazada"])

    plan = plan_de_empresa(empresa)
    formulario = FormularioReclasificacion(
        request.POST or None, plan=plan, initial={"cuenta": factura.cuenta_puc})
    if request.method == "POST" and formulario.is_valid():
        elegida = formulario.cleaned_data["cuenta"]
        cuenta, nombre, concepto, rol = next(
            fila for fila in cuentas_reclasificables(plan) if fila[0] == elegida)

        # Reconstruir los datos mínimos para recalcular retención y asiento
        datos = FacturaParseada(
            cufe=factura.cufe, numero=factura.numero,
            fecha_emision=factura.fecha_emision, nota="",
            nit_emisor=factura.nit_emisor, nombre_emisor=factura.nombre_emisor,
            tipo_persona_emisor=factura.tipo_persona_emisor,
            responsabilidad_emisor=factura.responsabilidad_emisor,
            nit_adquiriente=empresa.nit, nombre_adquiriente=empresa.razon_social,
            subtotal=factura.subtotal, iva=factura.iva, total=factura.total,
            lineas=[], tipo_documento="factura",
            retefuente_practicada=Decimal("0"),
            referencia_numero="", referencia_cufe="",
        )
        tercero = Tercero.objects.de_empresa(empresa).filter(
            nit=factura.nit_emisor).first()
        motivo = formulario.cleaned_data["motivo"] or "sin motivo registrado"
        propuesta = Propuesta(
            cuenta, nombre, concepto, "manual",
            f"Reclasificada manualmente a {cuenta} ({nombre}) por el usuario: "
            f"{motivo}.", rol=rol)
        retencion = calcular_retencion(datos, concepto, tercero, plan)
        factura.cuenta_puc = cuenta
        factura.nombre_cuenta_puc = nombre
        factura.concepto_retencion = concepto
        factura.retencion = retencion.valor
        factura.nivel = "manual"
        factura.estado = "pendiente"
        factura.explicacion = f"{propuesta.explicacion}\n{retencion.porque}"
        factura.asiento = construir_asiento(datos, propuesta, retencion, plan)
        factura.save()
        messages.success(request, f"Factura {factura.numero} reclasificada a "
                                  f"{cuenta} y devuelta a la bandeja para tu aprobación.")
        return redirect("causacion:detalle", pk=factura.pk)

    return render(request, "causacion/reclasificar.html", {
        "factura": factura,
        "formulario": formulario,
    })


# ---------- Cartera (P5.1) ----------

def cartera(request):
    empresa = _empresa_activa(request)
    partidas, totales = edades_de_cartera(empresa)
    return render(request, "causacion/cartera.html", {
        "empresa": empresa,
        "partidas": partidas,
        "rangos": [(clave, etiqueta, totales[clave]) for clave, etiqueta in RANGOS],
        "total_cartera": sum(totales.values()),
        "hay_asumidos": any(partida["vencimiento_asumido"] for partida in partidas),
    })


# ---------- Certificados de retención (P9) ----------

def certificados(request):
    from datetime import date

    from .certificados import certificados_del_anio
    empresa = _empresa_activa(request)
    try:
        anio = int(request.GET.get("anio", date.today().year))
    except ValueError:
        anio = date.today().year
    datos = certificados_del_anio(empresa, anio)
    return render(request, "causacion/certificados.html", {
        "datos": datos,
        "anio": anio,
        "anios": range(date.today().year, date.today().year - 5, -1),
    })


def certificado_tercero(request, anio, nit):
    from .certificados import certificado_de
    empresa = _empresa_activa(request)
    datos = certificado_de(empresa, anio, nit)
    if datos is None:
        messages.error(request, "No hay retenciones para ese proveedor en el año.")
        return redirect("causacion:certificados")
    return render(request, "causacion/certificado_tercero.html", datos)


# ---------- Matriz de terceros (P3) ----------

def terceros(request):
    empresa = _empresa_activa(request)
    lista = Tercero.objects.de_empresa(empresa)
    return render(request, "causacion/terceros.html", {
        "terceros": lista,
        "sin_verificar": lista.filter(verificado=False).count(),
    })


def editar_tercero(request, pk):
    empresa = _empresa_activa(request)
    tercero = get_object_or_404(Tercero.objects.de_empresa(empresa), pk=pk)
    formulario = FormularioTercero(request.POST or None, instance=tercero)
    if request.method == "POST" and formulario.is_valid():
        formulario.save()
        messages.success(
            request,
            f"Tercero {tercero.razon_social} actualizado. Las próximas facturas "
            "de este proveedor usarán esta calidad tributaria.",
        )
        return redirect("causacion:terceros")
    return render(request, "causacion/tercero_form.html", {
        "formulario": formulario,
        "tercero": tercero,
    })


# ---------- Decisión humana y salida al software contable (compras y ventas) ----------

def _decidir(request, modelo, pk, estado, nombre_detalle, mensaje):
    empresa = _empresa_activa(request)
    documento = get_object_or_404(
        modelo.objects.de_empresa(empresa), pk=pk, estado="pendiente")
    documento.estado = estado
    documento.save(update_fields=["estado", "actualizada"])
    (messages.success if estado == "aprobada" else messages.info)(
        request, mensaje.format(numero=documento.numero))
    return redirect(nombre_detalle, pk=documento.pk)


@require_POST
def aprobar(request, pk):
    return _decidir(request, FacturaCompra, pk, "aprobada", "causacion:detalle",
                    "Asiento de la factura {numero} aprobado.")


@require_POST
def rechazar(request, pk):
    return _decidir(request, FacturaCompra, pk, "rechazada", "causacion:detalle",
                    "Propuesta de la factura {numero} rechazada: no se contabilizará.")


@require_POST
def aprobar_venta(request, pk):
    return _decidir(request, FacturaVenta, pk, "aprobada", "causacion:detalle_venta",
                    "Asiento de {numero} aprobado.")


@require_POST
def rechazar_venta(request, pk):
    return _decidir(request, FacturaVenta, pk, "rechazada", "causacion:detalle_venta",
                    "Registro de {numero} rechazado: no se contabilizará.")


def _exportar_siigo(request, modelo, pk):
    """Descarga el asiento aprobado como CSV importable en Siigo (P1.9)."""
    empresa = _empresa_activa(request)
    documento = get_object_or_404(
        modelo.objects.de_empresa(empresa), pk=pk, estado="aprobada")
    respuesta = HttpResponse(
        generar_csv_siigo(documento).encode("utf-8-sig"),  # BOM: Excel abre bien las tildes
        content_type="text/csv; charset=utf-8",
    )
    respuesta["Content-Disposition"] = f'attachment; filename="siigo-{documento.numero}.csv"'
    return respuesta


def exportar_siigo(request, pk):
    return _exportar_siigo(request, FacturaCompra, pk)


def exportar_siigo_venta(request, pk):
    return _exportar_siigo(request, FacturaVenta, pk)


def _enviar_alegra(request, modelo, pk, nombre_detalle):
    """Crea el asiento aprobado en Alegra vía API (P1.9)."""
    empresa = _empresa_activa(request)
    documento = get_object_or_404(
        modelo.objects.de_empresa(empresa), pk=pk, estado="aprobada")
    if documento.id_alegra:
        messages.info(request, f"{documento.numero} ya está en Alegra "
                               f"(asiento #{documento.id_alegra}).")
        return redirect(nombre_detalle, pk=documento.pk)

    mapeo = dict(
        MapeoCuentaAlegra.objects.de_empresa(empresa)
        .values_list("cuenta_puc", "id_alegra")
    )
    try:
        id_alegra = alegra.enviar_asiento(documento, mapeo)
    except alegra.AlegraNoConfigurado as aviso:
        messages.warning(request, str(aviso))
        return redirect(nombre_detalle, pk=documento.pk)
    except alegra.ErrorAlegra as error:
        messages.error(request, str(error))
        return redirect(nombre_detalle, pk=documento.pk)

    documento.id_alegra = id_alegra
    documento.enviada_alegra = timezone.now()
    documento.save(update_fields=["id_alegra", "enviada_alegra", "actualizada"])
    messages.success(request, f"Asiento creado en Alegra con id #{id_alegra}.")
    return redirect(nombre_detalle, pk=documento.pk)


@require_POST
def enviar_alegra(request, pk):
    return _enviar_alegra(request, FacturaCompra, pk, "causacion:detalle")


@require_POST
def enviar_alegra_venta(request, pk):
    return _enviar_alegra(request, FacturaVenta, pk, "causacion:detalle_venta")
