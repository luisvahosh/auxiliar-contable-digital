# Corpus normativo inicial: fichas orientativas de los temas que la app maneja,
# citando el artículo del Estatuto Tributario. Contenido de apoyo (no texto
# legal oficial); el usuario/contador amplía o reemplaza con la fuente oficial
# vía el comando agregar_articulo. Valores 2026 verificados (dic-2025).
from django.db import migrations

FICHAS = [
    ("retencion-honorarios", "Retención en la fuente por honorarios",
     "art. 392 E.T.",
     "Los honorarios y comisiones están sujetos a retención en la fuente. La "
     "tarifa general es 11% para personas jurídicas y personas naturales "
     "declarantes, y 10% para personas naturales no declarantes. No hay base "
     "mínima en UVT: se retiene desde el primer peso. Si el proveedor está en "
     "el Régimen Simple (RST) o es autorretenedor, no se le practica retención.",
     "https://estatuto.co/392"),
    ("retencion-servicios", "Retención en la fuente por servicios",
     "art. 392 E.T. / Decreto 1625 de 2016",
     "Los servicios generales tienen retención del 4% (declarantes) o 6% (no "
     "declarantes). La base mínima para practicarla es 4 UVT; en 2026, con UVT "
     "de $52.374, equivale a $209.496. Por debajo de esa base no se retiene.",
     "https://estatuto.co/392"),
    ("retencion-compras", "Retención en la fuente por compras",
     "art. 401 E.T.",
     "Las compras generales tienen retención del 2.5%. La base mínima es 27 "
     "UVT; en 2026 (UVT $52.374) equivale a $1.414.098. La compra de bienes "
     "para revender se registra como inventario (activo), no como gasto.",
     "https://estatuto.co/401"),
    ("retencion-rentas-trabajo", "Retención en la fuente por rentas de trabajo",
     "art. 383 E.T.",
     "Los pagos laborales gravables se someten a la tabla de retención del "
     "artículo 383, con tarifas marginales por rangos en UVT (desde 0% hasta "
     "el tramo superior). Aplica a salarios y, en ciertos casos, a honorarios "
     "de personas naturales sin empleados. Es distinta de la retención por "
     "servicios/honorarios del artículo 392.",
     "https://estatuto.co/383"),
    ("regimen-simple", "Régimen Simple de Tributación y retención",
     "art. 903 y 911 E.T.",
     "Los contribuyentes del Régimen Simple de Tributación (RST) no son "
     "sujetos de retención en la fuente a título de renta: quien les paga NO "
     "les practica retefuente. El RST declara y paga de forma unificada. Se "
     "verifica el régimen del tercero en su RUT (responsabilidad O-47).",
     "https://estatuto.co/911"),
    ("autorretenedor", "Autorretenedores de renta",
     "art. 368 E.T. / Decreto 2201 de 2016",
     "Un autorretenedor se practica a sí mismo la retención en la fuente a "
     "título de renta; por eso quien le paga NO le retiene. La calidad de "
     "autorretenedor consta en el RUT del tercero (responsabilidad O-15).",
     "https://estatuto.co/368"),
    ("iva-responsables", "Responsables del IVA y tarifa general",
     "art. 420, 437 y 468 E.T.",
     "El IVA grava la venta de bienes y la prestación de servicios gravados. "
     "La tarifa general es 19%. Son responsables quienes vendan bienes o "
     "presten servicios gravados y superen los topes del régimen. El IVA "
     "pagado en compras gravadas relacionadas con la actividad es descontable.",
     "https://estatuto.co/420"),
    ("factura-electronica", "Factura electrónica y soporte de costos",
     "art. 616-1 y 771-2 E.T.",
     "La factura electrónica de venta es el soporte de las operaciones. Para "
     "que un costo, gasto o IVA descontable sea aceptado fiscalmente, debe "
     "estar soportado en factura con el lleno de los requisitos (art. 771-2). "
     "El CUFE identifica de forma única cada factura ante la DIAN.",
     "https://estatuto.co/616-1"),
    ("exoneracion-parafiscales", "Exoneración de aportes parafiscales",
     "art. 114-1 E.T.",
     "Las sociedades y personas jurídicas contribuyentes de renta están "
     "exoneradas de aportes a salud (8.5% patronal), SENA (2%) e ICBF (3%) por "
     "los trabajadores que ganen menos de 10 SMMLV. Sí aportan pensión, ARL y "
     "caja de compensación. Por encima de 10 SMMLV se aporta todo.",
     "https://estatuto.co/114-1"),
    ("informacion-exogena", "Información exógena (medios magnéticos)",
     "art. 631 E.T.",
     "La DIAN puede exigir anualmente información de terceros (exógena): pagos "
     "y retenciones practicadas (formato 1001), ingresos recibidos (1007), "
     "entre otros. Los conceptos, cuantías mínimas y plazos los fija una "
     "resolución anual de la DIAN, que debe consultarse cada año.",
     "https://estatuto.co/631"),
    ("salario-minimo-2026", "Salario mínimo y auxilio de transporte 2026",
     "Decretos 1469 y 1470 de 2025",
     "Para 2026 el salario mínimo mensual (SMMLV) es $1.750.905 y el auxilio "
     "de transporte $249.095. El auxilio se paga a quienes devenguen hasta 2 "
     "SMMLV. Estos valores se actualizan por decreto cada diciembre.",
     ""),
    ("uvt-2026", "Unidad de Valor Tributario (UVT) 2026",
     "Resolución DIAN 000238 de 2025",
     "La UVT para 2026 es $52.374 (Resolución DIAN 000238 del 15-dic-2025). La "
     "UVT se usa para expresar bases, topes y sanciones tributarias, y se "
     "reajusta cada año según el IPC. Muchas bases mínimas de retención se "
     "expresan en UVT.",
     ""),
]


def sembrar(apps, schema_editor):
    Articulo = apps.get_model("asistente", "ArticuloNormativo")
    for tema, titulo, ref, texto, url in FICHAS:
        Articulo.objects.update_or_create(
            tema=tema,
            defaults={"titulo": titulo, "referencia": ref,
                      "texto": texto, "fuente_url": url})


def borrar(apps, schema_editor):
    apps.get_model("asistente", "ArticuloNormativo").objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [("asistente", "0001_initial")]
    operations = [migrations.RunPython(sembrar, borrar)]
