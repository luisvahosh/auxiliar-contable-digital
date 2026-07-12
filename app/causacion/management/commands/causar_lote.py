"""
Procesa por lotes todos los XML de una carpeta (guía P1.8 / PLAN.md §4,
ingesta automática). Los tres canales — manual, carpeta y buzón de correo —
pasan por el mismo motor procesar_xml.

Uso:
  python manage.py causar_lote "C:\\ruta\\a\\la\\carpeta" [--nit 901234567]
"""
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from causacion.servicios import procesar_xml
from causacion.ventas import consecutivos_faltantes
from core.models import Empresa


class Command(BaseCommand):
    help = "Causa por lotes todos los XML de una carpeta."

    def add_arguments(self, analizador):
        analizador.add_argument("carpeta", help="Carpeta con los XML descargados")
        analizador.add_argument("--nit", default="",
                                help="NIT de la empresa (si hay más de una)")

    def handle(self, *args, **opciones):
        carpeta = Path(opciones["carpeta"])
        if not carpeta.is_dir():
            raise CommandError(f"La carpeta no existe: {carpeta}")

        if opciones["nit"]:
            empresa = Empresa.objects.filter(nit=opciones["nit"]).first()
            if empresa is None:
                raise CommandError(f"No hay empresa con NIT {opciones['nit']}.")
        elif Empresa.objects.count() == 1:
            empresa = Empresa.objects.first()
        else:
            raise CommandError("Hay varias empresas: indica cuál con --nit.")

        archivos = sorted(carpeta.glob("*.xml"))
        if not archivos:
            raise CommandError(f"No hay archivos .xml en {carpeta}.")

        conteo = {"creado": 0, "duplicado": 0, "error": 0}
        marcas = {"creado": "OK ", "duplicado": "DUP", "error": "ERR"}
        reintentos = []  # notas crédito que llegaron antes que su factura original
        for archivo in archivos:
            resultado = procesar_xml(empresa, archivo.read_bytes())
            if resultado.estado == "error" and resultado.reintentable:
                reintentos.append(archivo)
                continue
            conteo[resultado.estado] += 1
            self.stdout.write(f"{marcas[resultado.estado]}  {archivo.name}: {resultado.mensaje}")

        # Segunda pasada: las originales ya deberían estar causadas
        for archivo in reintentos:
            resultado = procesar_xml(empresa, archivo.read_bytes())
            conteo[resultado.estado] += 1
            self.stdout.write(f"{marcas[resultado.estado]}  {archivo.name}: {resultado.mensaje}")

        self.stdout.write("")
        self.stdout.write(f"Lote de {len(archivos)} archivos para {empresa.razon_social}: "
                          f"{conteo['creado']} procesados, {conteo['duplicado']} duplicados, "
                          f"{conteo['error']} con error.")
        self.stdout.write("Los documentos quedaron PENDIENTES de aprobación en las "
                          "bandejas — humano en el circuito.")

        faltantes = consecutivos_faltantes(
            empresa.facturas_venta.filter(tipo="venta").values_list("numero", flat=True))
        if faltantes:
            self.stdout.write(self.style.WARNING(
                "Hueco en el consecutivo de ventas: falta " + ", ".join(faltantes)))
