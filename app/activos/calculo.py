"""
Motor de depreciación mensual en línea recta (guía P10).

Cada activo aporta su cuota, topada al saldo por depreciar (P10.2) y solo si
ya estaba adquirido (P10.5). El asiento consolidado agrupa por categoría el
gasto y la depreciación acumulada.
"""
from datetime import date
from decimal import Decimal

from . import parametros as p


def depreciar_mes(empresa, activos, anio, mes):
    """Depreciación consolidada del mes. → dict con detalle, total, asiento y
    explicación. `activos` ya viene filtrado por empresa."""
    fin_mes = date(anio, mes, 28)  # cualquier día del mes sirve para comparar
    detalle = []
    # gasto y depreciación acumulada agregados por categoría (para el asiento)
    por_categoria = {}

    for activo in activos:
        if activo.fecha_adquisicion > fin_mes:
            continue  # P10.5: aún no se había comprado
        cuota = min(activo.cuota_mensual, activo.saldo_por_depreciar)
        if cuota <= 0:
            continue  # ya totalmente depreciado (P10.2)
        detalle.append({
            "activo_id": str(activo.pk),
            "nombre": activo.nombre,
            "categoria": activo.categoria,
            "cuota": str(cuota),
            "acumulada_despues": str(activo.depreciacion_acumulada + cuota),
            "valor_en_libros": str(activo.costo - activo.depreciacion_acumulada - cuota),
        })
        por_categoria[activo.categoria] = por_categoria.get(
            activo.categoria, Decimal("0")) + cuota

    renglones = []
    for categoria, monto in por_categoria.items():
        datos = p.CATEGORIAS[categoria]
        renglones.append({"cuenta": datos["cuenta_gasto"][0],
                          "nombre": datos["cuenta_gasto"][1],
                          "debito": str(monto), "credito": "0"})
        renglones.append({"cuenta": datos["cuenta_dep_acum"][0],
                          "nombre": datos["cuenta_dep_acum"][1],
                          "debito": "0", "credito": str(monto)})

    total = sum(por_categoria.values(), Decimal("0"))
    debitos = sum(Decimal(r["debito"]) for r in renglones)
    creditos = sum(Decimal(r["credito"]) for r in renglones)
    if debitos != creditos:
        raise ValueError(f"Asiento de depreciación desbalanceado: {debitos} ≠ {creditos}.")

    explicacion = (
        f"Depreciación {anio}-{mes:02d} en línea recta de {len(detalle)} activo(s). "
        "Cuota mensual = (costo − valor residual) / vida útil en meses, sin pasar "
        "del valor depreciable. Débito al gasto de depreciación, crédito a la "
        "depreciación acumulada, agrupados por categoría."
    )
    return {"detalle": detalle, "total": total, "asiento": renglones,
            "explicacion": explicacion}
