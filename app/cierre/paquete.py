"""
Paquete del contador (guía P7.1): un ZIP con el mes listo para revisar y
firmar — resumen del cierre, auxiliares por cuenta y por tercero, el CSV
consolidado formato Siigo y los soportes (XML y fotos) organizados.
"""
import csv
import io
import re
import zipfile
from decimal import Decimal

from .logica import resumen_cierre

_SEPARADOR = ";"  # Excel colombiano


def _csv(filas):
    salida = io.StringIO()
    escritor = csv.writer(salida, delimiter=_SEPARADOR, lineterminator="\r\n")
    escritor.writerows(filas)
    return salida.getvalue().encode("utf-8-sig")  # BOM: tildes bien en Excel


def _nombre_seguro(texto):
    return re.sub(r"[^\w\-.]", "_", texto)


def _renglones_de(documentos):
    """(documento, renglón) de todos los asientos aprobados del período."""
    for documento in documentos:
        for renglon in documento.asiento:
            yield documento, renglon


def _texto_resumen(empresa, resumen):
    lineas = [
        f"CIERRE MENSUAL — {empresa.razon_social} (NIT {empresa.nit})",
        f"Período: {resumen['anio']}-{resumen['mes']:02d}",
        "",
        f"Compras del período: {len(resumen['compras'])} "
        f"({len(resumen['compras_aprobadas'])} aprobadas)",
        f"Ventas del período: {len(resumen['ventas'])} "
        f"({len(resumen['ventas_aprobadas'])} aprobadas)",
        f"Documentos pendientes de aprobación: {len(resumen['pendientes'])}",
        f"Documentos rechazados: {resumen['rechazadas']}",
        f"Movimientos bancarios sin conciliar: {len(resumen['movimientos_pendientes'])}",
        f"Partidas conciliatorias (excepciones documentadas): {len(resumen['excepciones'])}",
        "",
        "RETENCIONES PRACTICADAS (base del formulario 350):",
    ]
    for fila in resumen["retenciones_por_cuenta"]:
        lineas.append(f"  {fila['cuenta']} {fila['nombre']}: ${fila['valor']:,.0f}")
    lineas += [
        f"  TOTAL según asientos: ${resumen['total_retenciones_asientos']:,.0f}",
        f"  TOTAL según facturas: ${resumen['total_retenciones_facturas']:,.0f}",
        f"  Cuadre: {'SÍ' if resumen['retenciones_cuadran'] else 'NO — REVISAR'}",
        "",
        f"ESTADO DEL CIERRE: {'LISTO PARA ENTREGA' if resumen['listo'] else 'CON PENDIENTES'}",
    ]
    for origen, documento in resumen["pendientes"]:
        lineas.append(f"  PENDIENTE ({origen}): {documento.numero} — "
                      f"{documento.explicacion.splitlines()[0]}")
    return "\r\n".join(lineas)


def construir_paquete(empresa, anio, mes):
    """Devuelve (nombre_archivo, bytes del ZIP)."""
    resumen = resumen_cierre(empresa, anio, mes)
    aprobados = resumen["compras_aprobadas"] + resumen["ventas_aprobadas"]
    periodo = f"{anio}-{mes:02d}"

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zip_:
        zip_.writestr(f"resumen-cierre-{periodo}.txt",
                      _texto_resumen(empresa, resumen).encode("utf-8-sig"))

        # Auxiliar por cuenta
        filas = [["CUENTA", "NOMBRE CUENTA", "DOCUMENTO", "FECHA",
                  "NIT TERCERO", "TERCERO", "DEBITO", "CREDITO"]]
        for documento, renglon in sorted(_renglones_de(aprobados),
                                         key=lambda par: par[1]["cuenta"]):
            filas.append([renglon["cuenta"], renglon["nombre"], documento.numero,
                          documento.fecha_emision.isoformat(), documento.nit_tercero,
                          documento.nombre_tercero, renglon["debito"], renglon["credito"]])
        zip_.writestr(f"auxiliar-por-cuenta-{periodo}.csv", _csv(filas))

        # Auxiliar por tercero
        filas = [["NIT TERCERO", "TERCERO", "DOCUMENTO", "FECHA",
                  "CUENTA", "NOMBRE CUENTA", "DEBITO", "CREDITO"]]
        for documento, renglon in sorted(_renglones_de(aprobados),
                                         key=lambda par: par[0].nit_tercero):
            filas.append([documento.nit_tercero, documento.nombre_tercero,
                          documento.numero, documento.fecha_emision.isoformat(),
                          renglon["cuenta"], renglon["nombre"],
                          renglon["debito"], renglon["credito"]])
        zip_.writestr(f"auxiliar-por-tercero-{periodo}.csv", _csv(filas))

        # CSV consolidado formato Siigo (todo el mes en un solo archivo)
        filas = [["TIPO COMPROBANTE", "NUMERO COMPROBANTE", "FECHA", "CODIGO CUENTA",
                  "DESCRIPCION", "NIT TERCERO", "NOMBRE TERCERO", "DEBITO", "CREDITO"]]
        for documento, renglon in _renglones_de(aprobados):
            filas.append(["CC", documento.numero,
                          documento.fecha_emision.strftime("%d/%m/%Y"),
                          renglon["cuenta"],
                          f"Causación {documento.numero} — {documento.nombre_tercero}",
                          documento.nit_tercero, documento.nombre_tercero,
                          renglon["debito"], renglon["credito"]])
        zip_.writestr(f"siigo-consolidado-{periodo}.csv", _csv(filas))

        # Movimientos bancarios con su estado (partidas conciliatorias incluidas)
        filas = [["FECHA", "DESCRIPCION", "VALOR", "ESTADO", "SUGERENCIA", "EXPLICACION"]]
        movimientos = (resumen["movimientos_pendientes"] + resumen["excepciones"])
        for movimiento in movimientos:
            filas.append([movimiento.fecha.isoformat(), movimiento.descripcion,
                          str(movimiento.valor), movimiento.get_estado_display(),
                          movimiento.get_sugerencia_display(), movimiento.explicacion])
        zip_.writestr(f"partidas-conciliatorias-{periodo}.csv", _csv(filas))

        # Soportes: XML original de cada documento y foto si la hay
        for documento in aprobados:
            nombre = _nombre_seguro(documento.numero)
            zip_.writestr(f"soportes/{nombre}.xml", documento.xml_crudo)
            imagen = getattr(documento, "imagen", None)
            if imagen:
                try:
                    with imagen.open("rb") as archivo:
                        extension = imagen.name.rsplit(".", 1)[-1]
                        zip_.writestr(f"soportes/{nombre}.{extension}", archivo.read())
                except (FileNotFoundError, OSError):
                    pass  # la foto no está en disco: el XML/registro sigue en el paquete

    nombre_zip = f"paquete-cierre-{_nombre_seguro(empresa.nit)}-{periodo}.zip"
    return nombre_zip, buffer.getvalue()
