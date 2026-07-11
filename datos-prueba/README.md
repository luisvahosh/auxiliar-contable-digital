# Datos de prueba — facturas electrónicas simuladas (casos P1)

XML simulados en formato UBL 2.1 con extensiones DIAN, uno por caso de prueba
de `PROCESO-AUXILIAR-CONTABLE.md` (P1). **Todos los NITs, CUFEs, resoluciones
y firmas son ficticios** — no son documentos reales y no tienen firma XAdES.
El adquiriente en todos es LEARNWAY SAS (NIT ficticio 901.234.567).

| Archivo | Caso | Escenario | Resultado esperado |
|---|---|---|---|
| `P1.1-factura-honorarios.xml` | P1.1 | Honorarios $2.000.000 + IVA, persona natural declarante | Débito 5110 + 2408; crédito 2365 retefuente honorarios 10% ($200.000) y proveedor por el neto; balanceado |
| `P1.2-factura-inventario.xml` | P1.2 | Mercancía $5.600.000 + IVA, 2 líneas, persona jurídica | Débito **1435** (no gasto) + 2408; retefuente compras 2.5% ($140.000, supera 27 UVT); crédito 2205 neto |
| `P1.3-factura-regimen-simple.xml` | P1.3 | Aseo/cafetería $1.500.000 + IVA, proveedor RST (`TaxLevelCode O-47`) | **Sin retefuente** (RST no es sujeto de retención, art. 911 E.T.); crédito proveedor por el total |
| `P1.4-factura-bajo-base-minima.xml` | P1.4 | Mantenimiento $150.000 + IVA (< 4 UVT servicios) | Sin cuentas 2365: no se calcula retención |
| `P1.5-factura-duplicada-mismo-cufe.xml` | P1.5 | Copia exacta de P1.1 (mismo CUFE) | Subida después de P1.1: rechazo con aviso "ya causada", sin asiento doble |
| `P1.6a-xml-malformado.xml` | P1.6 | XML truncado, tags sin cerrar | Error claro al usuario, sin crash, sin asiento a medias |
| `P1.6b-xml-xxe.xml` | P1.6 | `DOCTYPE` con entidad externa (ataque XXE) | defusedxml lo rechaza (`EntitiesForbidden`); nunca parsear con `xml.etree` directo |
| `P1.7-factura-concepto-ambiguo.xml` | P1.7 | Suministro + instalación de aire acondicionado $4.800.000 | No se causa automática: ¿activo fijo (1528/1540) o gasto (5145)? Va a bandeja como "sugerida" con explicación |

Cada XML lleva en su comentario de cabecera el asiento esperado detallado.

## Notas de formato

- CUFE en `cbc:UUID` (schemeName `CUFE-SHA384`, 96 hex); el de P1.5 es
  idéntico al de P1.1 a propósito.
- Régimen del emisor en `cac:PartyTaxScheme/cbc:TaxLevelCode`
  (`O-47` = Régimen Simple, `R-99-PN` = otros; `O-13` gran contribuyente,
  `O-15` autorretenedor — aún sin caso, ver P3.2).
- Tipo de documento del emisor en `cbc:CompanyID@schemeName`
  (`31` = NIT, `13` = cédula) y dígito de verificación en `@schemeID`.
- La retención en la fuente **no viene en el XML**: la calcula el comprador
  al causar. Ese cálculo es lo que se prueba.
- Faltan por generar cuando lleguen sus fases: P1.8 (lote de 100), P2.x
  (ventas y nota crédito), P3.2 (autorretenedor).

Regenerar/ajustar: el generador vive en el scratchpad de la sesión que los
creó; si se necesita de nuevo, pedirle a Claude que lo recree (los archivos
son autocontenidos y editables a mano).
