"""
Informes contables (guía P13): consolida los asientos aprobados de TODOS los
módulos (compras, ventas, nómina, depreciación, caja menor, conciliación) en
un balance de comprobación, estado de resultados y libro mayor.

Es una lectura transversal (sin modelos propios): cada módulo ya guarda su
asiento como JSON; aquí se recolectan, se filtran por período y se agregan
por cuenta.
"""
from dataclasses import dataclass
from decimal import Decimal

CLASES_PUC = {
    "1": "Activo", "2": "Pasivo", "3": "Patrimonio",
    "4": "Ingresos", "5": "Gastos", "6": "Costos de ventas",
    "7": "Costos de producción", "8": "Cuentas de orden deudoras",
    "9": "Cuentas de orden acreedoras",
}


@dataclass
class Movimiento:
    cuenta: str
    nombre: str
    debito: Decimal
    credito: Decimal
    fecha: object
    origen: str      # "Compra FVS-847", "Nómina 2026-07", …


def _renglones(asiento, fecha, origen):
    for r in asiento:
        debito, credito = Decimal(r["debito"]), Decimal(r["credito"])
        if debito or credito:
            yield Movimiento(r["cuenta"], r["nombre"], debito, credito, fecha, origen)


def movimientos_del_periodo(empresa, anio, mes=None):
    """Todos los movimientos de asientos aprobados del período, de todos los
    módulos. `mes` opcional (None = todo el año)."""
    from activos.models import DepreciacionMensual
    from cajamenor.models import ReembolsoCajaMenor
    from causacion.models import FacturaCompra, FacturaVenta
    from conciliacion.models import MovimientoBancario

    movs = []

    def por_fecha(qs, campo="fecha_emision"):
        qs = qs.filter(**{f"{campo}__year": anio})
        if mes:
            qs = qs.filter(**{f"{campo}__month": mes})
        return qs

    for f in por_fecha(FacturaCompra.objects.de_empresa(empresa).filter(estado="aprobada")):
        etiqueta = "Nota crédito" if f.tipo == "nota_credito" else "Compra"
        movs += _renglones(f.asiento, f.fecha_emision, f"{etiqueta} {f.numero}")
    for v in por_fecha(FacturaVenta.objects.de_empresa(empresa).filter(estado="aprobada")):
        etiqueta = "Nota crédito" if v.tipo == "nota_credito" else "Venta"
        movs += _renglones(v.asiento, v.fecha_emision, f"{etiqueta} {v.numero}")

    # Nómina y depreciación se filtran por anio/mes propios
    from nomina.models import LiquidacionNomina
    nomina = LiquidacionNomina.objects.de_empresa(empresa).filter(
        estado="aprobada", anio=anio)
    deprec = DepreciacionMensual.objects.de_empresa(empresa).filter(
        estado="aprobada", anio=anio)
    if mes:
        nomina = nomina.filter(mes=mes)
        deprec = deprec.filter(mes=mes)
    for n in nomina:
        from datetime import date
        movs += _renglones(n.asiento, date(n.anio, n.mes, 1), f"Nómina {n.anio}-{n.mes:02d}")
    for d in deprec:
        from datetime import date
        movs += _renglones(d.asiento, date(d.anio, d.mes, 1),
                           f"Depreciación {d.anio}-{d.mes:02d}")

    for reem in por_fecha(ReembolsoCajaMenor.objects.de_empresa(empresa).filter(
            estado="aprobado"), campo="fecha"):
        movs += _renglones(reem.asiento, reem.fecha, f"Caja menor {reem.caja.nombre}")

    for m in por_fecha(MovimientoBancario.objects.de_empresa(empresa).filter(
            estado="conciliado"), campo="fecha"):
        if m.asiento:
            movs += _renglones(m.asiento, m.fecha, f"Banco: {m.descripcion[:30]}")

    return movs


def balance_comprobacion(empresa, anio, mes=None):
    """Por cuenta: débitos, créditos, saldo. Cuadra si total déb = total créd."""
    movs = movimientos_del_periodo(empresa, anio, mes)
    cuentas = {}
    for m in movs:
        c = cuentas.setdefault((m.cuenta, m.nombre),
                               {"debito": Decimal("0"), "credito": Decimal("0")})
        c["debito"] += m.debito
        c["credito"] += m.credito
    filas = []
    total_d = total_c = Decimal("0")
    for (cuenta, nombre), v in sorted(cuentas.items()):
        saldo = v["debito"] - v["credito"]
        filas.append({"cuenta": cuenta, "nombre": nombre,
                      "debito": v["debito"], "credito": v["credito"], "saldo": saldo})
        total_d += v["debito"]
        total_c += v["credito"]
    return {"filas": filas, "total_debito": total_d, "total_credito": total_c,
            "cuadra": total_d == total_c}


def estado_resultados(empresa, anio, mes=None):
    """Ingresos (clase 4) − gastos (5) − costos (6,7) = utilidad."""
    bal = balance_comprobacion(empresa, anio, mes)
    ingresos = costos = gastos = Decimal("0")
    detalle = {"ingresos": [], "gastos": [], "costos": []}
    for f in bal["filas"]:
        clase = f["cuenta"][:1]
        if clase == "4":
            monto = f["credito"] - f["debito"]  # ingreso: saldo crédito
            ingresos += monto
            detalle["ingresos"].append({**f, "monto": monto})
        elif clase == "5":
            monto = f["debito"] - f["credito"]
            gastos += monto
            detalle["gastos"].append({**f, "monto": monto})
        elif clase in ("6", "7"):
            monto = f["debito"] - f["credito"]
            costos += monto
            detalle["costos"].append({**f, "monto": monto})
    return {"ingresos": ingresos, "costos": costos, "gastos": gastos,
            "utilidad": ingresos - costos - gastos, "detalle": detalle}


def libro_mayor(empresa, cuenta, anio, mes=None):
    """Movimientos de una cuenta con su documento de origen y saldo corriente."""
    movs = [m for m in movimientos_del_periodo(empresa, anio, mes) if m.cuenta == cuenta]
    movs.sort(key=lambda m: m.fecha)
    filas, saldo = [], Decimal("0")
    for m in movs:
        saldo += m.debito - m.credito
        filas.append({"fecha": m.fecha, "origen": m.origen, "nombre": m.nombre,
                      "debito": m.debito, "credito": m.credito, "saldo": saldo})
    return filas
