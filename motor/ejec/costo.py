"""Generadores de obra, presupuesto (APU de VERTICE-CALCULO con precios Tijuana) y programa de obra.

Las cantidades salen de la misma geometría y del mismo cálculo que los planos (coordinación). Los conceptos
cuya base no trae material quedan con su mano de obra y el material se lista en "Por cotizar" con cantidades.
"""
import math
from .. import instalaciones as I
from . import inst as IE
from .est import paneles


def generadores(blq, lays, r, cancel, acab):
    niveles = blq["niveles"]
    q = {}
    notas = {}

    def add(k, v, nota=""):
        q[k] = q.get(k, 0.0) + v
        if nota:
            notas.setdefault(k, []).append(nota)
    # cimentación
    for cl in r["cargas_lineas"]:
        z = r["zap_linea"][(cl["eje"], round(cl["c"], 3), cl["a"])]
        L, B, h = cl["b"] - cl["a"], z["B"] / 100, z["h"] / 100
        add("exc-mano", L * (B + 0.10) * (r["Df"] + 0.05))
        add("plantilla", L * (B + 0.10))
        add("cimbra-cim", 2 * L * h)
        add("relleno", max(0.0, L * (B + 0.10) * (r["Df"] + 0.05) - L * B * h - L * 0.15 * (r["Df"] - h)))
    # acero (castillos incluidos en su APU con armex)
    ligero = medio = 0.0
    for f in r["cuantificacion"]["filas"]:
        if f["elemento"].startswith("Castillos"):
            continue
        ligero += f["kg3"] + f["kg2"]
        if f["elemento"].startswith("Trabe"):
            medio += f["kg4"]
        else:
            ligero += f["kg4"]
    add("acero-ligero", ligero, "#2.5, #3 y #4 en zapatas, dalas, losas, trabes y escalera")
    add("acero-medio", medio, "#5 y #6 en trabes")
    # concreto
    for f in r["cuantificacion"]["filas"]:
        e = f["elemento"]
        if e.startswith("Castillos"):
            continue
        if e.startswith("Dala"):
            add("colado-trompo", f["concreto"], "Dalas f'c 150")
        else:
            add("colado-bomba", f["concreto"], e)
    # cimbras
    A_losas = sum(t["w"] * t["d"] for ts in r["tableros"] for t in ts)
    add("cimbra-losa", A_losas)
    for t in r["trabes"]:
        add("cimbra-trabe", (t["L"] + 0.3) * (2 * t["h"] + t["b"]) / 100)
    # muros
    for k, n in enumerate(niveles):
        hn = n["h"] - r["losas"][k]["h"] / 100 - 0.20
        for ln in r["estructurales"][k]:
            maciza = sum(b - a for a, b in paneles(ln, lays[k][1]))
            t = r["t_x"] if ln["eje"] == "h" else r["t_y"]
            add("block-20" if t == 20 else "block-15", maciza * hn)
        add("castillo", len(r["castillos"][k]) * n["h"])
    per = 2 * (blq["w"] + blq["d"])
    # pretil sólo con azotea plana: con cubierta inclinada sobre la losa (A-04/A-05/A-06) no existe y antes
    # se cobraba block, dala D-2 y aplanado de un pretil que no aparece en los planos
    h_pre = 0.0 if blq.get("cubierta_ligera") else (blq.get("pretil") or 0.6)   # misma altura que A-05 y A-06
    if h_pre:
        add("block-15", per * h_pre, f"Pretil h = {h_pre:.2f} m")
    for f in r["cuantificacion"]["filas"]:
        if f["elemento"].startswith("Dala"):
            add("dala", f["cantidad"])
    # firme, acabados
    hojas0 = [c for c in lays[0][0] if not c["contenedor"]]
    add("firme", blq["w"] * blq["d"])
    ventanas = sum(t["ancho"] * t["alto"] * t["cant"] for t in cancel if t["clave"].startswith(("V", "PT", "P")))
    H = sum(n["h"] for n in niveles)
    add("aplanado", max(0.0, (per * (H + h_pre) - ventanas * 0.6)), "Fachadas y pretil (mortero)" if h_pre else "Fachadas (mortero)")
    piso = azul = yeso = plaf = 0.0
    for k, n in enumerate(niveles):
        for c in [c for c in lays[k][0] if not c["contenedor"]]:
            A = c["w"] * c["d"]
            P = 2 * (c["w"] + c["d"])
            hm = n["h"] - r["losas"][k]["h"] / 100
            plaf += A
            if c["t"] not in ("ext", "almacen"):
                piso += A
            if c["t"] == "humedo" and "MEDIO" in c["n"].upper():
                # medio baño: sin regadera, azulejo sólo en el muro del lavabo a 1.20 m (igual que la cédula de acabados)
                azul += P * 1.2 * 0.3
                yeso += P * hm * 0.7
            elif c["t"] == "humedo":
                azul += P * 2.1 * 0.6
                yeso += P * hm * 0.4
            elif c["t"] == "cocina":
                azul += max(c["w"], c["d"]) * 0.6
                yeso += P * hm * 0.8
            elif c["t"] == "servicio":
                azul += P * 1.2 * 0.5
                yeso += P * hm * 0.6
            else:
                yeso += P * hm * 0.85
    add("piso-cer", piso)
    add("azulejo", azul)
    add("yeso", yeso + plaf, "Muros interiores y plafones")
    add("pintura", yeso + plaf + q["aplanado"])
    add("imper", blq["w"] * blq["d"] * 1.05)
    # instalaciones
    sal_e = 0
    muebles = 0
    for k in range(len(niveles)):
        for c in [c for c in lays[k][0] if not c["contenedor"]]:
            sal_e += I._luminarias(c, blq)[0] + IE.contactos(c, blq) + 1
            if I.es_humedo(c):
                muebles += I._muebles(c)[2]
    add("salida-elec", sal_e, "Luminarias, contactos y apagadores")
    add("salida-hid", muebles, "Por mueble (agua fría, caliente y desagüe)")
    return {k: round(v, 2) for k, v in q.items()}, notas


def por_cotizar(blq, lays, r, cancel, q, cc, rasgos=(), piso=None):
    filas = []
    for t in cancel:
        if t["clave"].startswith("V"):
            filas.append((f"{t['clave']} {t['desc']} {t['ancho']:.2f}x{t['alto']:.2f} m — {t['mat']}", "m²", round(t["ancho"] * t["alto"] * t["cant"], 2)))
        else:
            filas.append((f"{t['clave']} {t['desc']} {t['ancho']:.2f}x{t['alto']:.2f} m — {t['mat']}", "pza", t["cant"]))
    hojas = [c for k in range(len(lays)) for c in lays[k][0] if not c["contenedor"]]
    wc = sum(1 for c in hojas if c["t"] == "humedo")
    reg = sum(1 for c in hojas if c["t"] == "humedo" and "Medio" not in c["n"])
    # material de piso según la cédula de acabados (antes decía porcelanato aunque el spec pidiera terrazo, barro o madera)
    piso_txt = ("Porcelanato y adhesivo (material)" if not piso or "porcelanato" in piso.lower() else
                f"{piso} en locales habitables; porcelanato antiderrapante y cerámico en baños y servicio (material)")
    filas += [(piso_txt, "m²", round(q.get("piso-cer", 0) * 1.08, 2)),
              ("Azulejo y adhesivo (material)", "m²", round(q.get("azulejo", 0) * 1.08, 2)),
              ("Pintura vinílica y sellador (material, 2 manos)", "L", round(q.get("pintura", 0) / 4.5, 1)),
              ("Impermeabilizante prefabricado APP 4 mm (material)", "m²", round(q.get("imper", 0) * 1.1, 2)),
              ("Tubería, cajas y cableado THW-LS (material)", "lote", 1),
              ("Tubería CPVC/PPR, PVC sanitario y conexiones (material)", "lote", 1),
              ("Inodoro ahorrador 4.8 L con asiento", "pza", wc),
              ("Lavabo con llave mezcladora", "pza", wc),
              ("Regadera con mezcladora", "pza", reg),
              ("Tarja de cocina con mezcladora", "pza", 1),
              ("Cocina integral (gabinetes y cubierta)", "ml", round(max((c["w"] for c in hojas if c["t"] == "cocina"), default=3.0) + 1.2, 1)),
              ("Clósets de MDF con puertas", "ml", round(sum(max(0, min(c["w"], c["d"]) - 0.9) for c in hojas if c["n"].startswith("Recámara")), 1)),
              ("Barandal de herrería en escalera h = 0.90 m", "ml", 6.0),
              ("Calentador de paso 16 L/min a gas", "pza", 1),
              ("Cisterna prefabricada 2,500 L con accesorios", "pza", 1),
              ("Equipo hidroneumático 1/2 HP", "pza", 1),
              (f"Tanque estacionario de gas LP {blq.get('gas_L', '300 L')}, regulador y tubería de cobre", "lote", 1),
              (f"{cc['tablero']} con interruptores", "lote", 1),
              ("Luminarias LED 18 W", "pza", sum(c["lum"] for c in cc["circuitos"])),
              ("Contactos y apagadores (placas y accesorios)", "pza", sum(c["cont"] for c in cc["circuitos"]) + len(hojas)),
              ("Acometida y contrato CFE / toma y descarga CESPT", "lote", 1),
              ("Limpieza final de obra", "m²", round(sum(n["h"] * 0 + blq["w"] * blq["d"] for n in blq["niveles"]), 2))]
    cl = blq.get("cubierta_ligera")
    if cl:
        al = cl["alero"]
        a_inc = (blq["w"] + 2 * al) * (blq["d"] + 2 * al) * math.sqrt(1 + cl["pend"] ** 2)
        filas.append((f"Cubierta {cl['tipo'].replace('_', ' ')} de {cl['material']} sobre armadura ligera de PTR galvanizado, "
                      "triplay 16 mm y fieltro asfáltico (incluye alero, cumbrera y limatesas)", "m²", round(a_inc, 2)))
        filas.append(("Canalón perimetral de lámina galvanizada cal. 24 con bajadas", "ml",
                      round(2 * (blq["w"] + blq["d"] + 4 * al), 2)))
        if "porche" in cl["rasgos"]:
            filas.append(("Porche de acceso: postes 20x20 y vigas de madera termotratada con cubierta (1.80 m de fondo)", "lote", 1))
        if "pergola" in cl["rasgos"]:
            filas.append((f"Pérgola posterior de madera termotratada ({blq['w']:.2f} x 2.50 m)", "lote", 1))
    # rasgos de fachada que no forman parte de los generadores de obra negra (antes no se cuantificaban)
    from .. import layout
    if "pilotis" in rasgos and len(blq["niveles"]) > 1:
        P = layout.pilotis(blq, lays[0][1])
        filas.append((f"Marquesina de concreto armado f'c = 250 kg/cm² e = {P['losa'] * 100:.0f} cm, vuelo {P['fondo']:.2f} m, "
                      "con trabe de borde, impermeabilizada", "m²", round((P["x1"] - P["x0"]) * P["fondo"], 2)))
        filas.append((f"Pilotis: columnas circulares de concreto aparente Ø{P['diam'] * 100:.0f} cm con zapata aislada "
                      f"(h = {blq['niveles'][0]['h']:.2f} m)", "pza", len(P["cols"])))
    if "volado" in rasgos and blq.get("volado"):
        VO = blq["volado"]
        filas.append((f"Losa en volado de concreto armado f'c = 250 kg/cm² en fachada principal, peralte {VO['peralte'] * 100:.0f} cm, "
                      f"vuelo {VO['fondo']:.2f} m, anclada a la losa de azotea, con gotero e impermeabilizada", "m²",
                      round((VO["x1"] - VO["x0"]) * VO["fondo"], 2)))
    if len(blq["niveles"]) > 1:
        zb1 = blq["niveles"][0]["h"]
        ztop = sum(n["h"] for n in blq["niveles"])
        if "celosia" in rasgos or "parteluces" in rasgos:
            # misma geometría que render, AP-03, A-05 y Blender (layout.parteluces); antes no se cuantificaban
            PL = layout.parteluces(blq, "celosia" in rasgos)
            desc = ("Celosía de madera termotratada (listones de 8 cm)" if "celosia" in rasgos else
                    f"Parteluces verticales de concreto armado {PL['ancho'] * 100:.0f}x{(PL['y0'] - PL['y1']) * 100:.0f} cm "
                    "anclados a losas, aplanado y pintura")
            filas.append((f"{desc} en fachada principal, h = {ztop - zb1:.2f} m", "pza", len(PL["xs"])))
        if "marco" in rasgos:
            fx0 = layout.inicio_marco(lays[1][1], blq["x"], blq["w"])
            largo = 2 * (blq["w"] + 0.05 - fx0) + 2 * (ztop - zb1 + 0.3)
            filas.append(("Marco volumétrico de concreto armado 30 x 90 cm en planta alta de la fachada principal, "
                          "aplanado y pintura en color de acento", "ml", round(largo, 2)))
    if "ventana_corrida" in rasgos and len(blq["niveles"]) > 1:
        # sólo los paños entre ventanas (las ventanas ya están en la cancelería), con la altura de la ventana (1.45 m)
        area = 0.0
        for k_ in range(1, len(blq["niveles"])):
            vs = sorted((v["a"], v["b"]) for v in lays[k_][1] if v["tipo"] == "ventana" and v.get("lado") == "S")
            area += sum(max(0.0, a2 - b1) for (_, b1), (a2, _) in zip(vs, vs[1:])) * 1.45
        if area > 0:
            filas.append(("Banda corrida: paneles de aluminio compuesto entre ventanas de fachada principal", "m²", round(area, 2)))
    if q.get("block-20"):
        filas.append(("Block hueco de concreto 20x20x40 (material, 12.5 pza/m²)", "pza", math.ceil(q["block-20"] * 12.5 * 1.05)))
    if q.get("dala"):
        filas.append(("Armex 15x20 o acero y concreto de dalas (material de la partida 'dala')", "ml", q["dala"]))
    return filas


def presupuesto(V, nombre, blq, q, area):
    from vertice import costos
    db = costos.BaseDatos()
    pres = costos.Presupuesto(nombre, cliente="Proyecto del día Vértice", area_construida=area)
    orden = ["exc-mano", "plantilla", "cimbra-cim", "relleno", "acero-ligero", "acero-medio", "colado-bomba", "colado-trompo",
             "cimbra-losa", "cimbra-trabe", "block-15", "block-20", "castillo", "dala", "firme", "aplanado", "yeso",
             "azulejo", "piso-cer", "pintura", "imper", "salida-elec", "salida-hid"]
    solo_mo = []
    i = 0
    for rid in orden:
        if not q.get(rid):
            continue
        i += 1
        a = costos.apu_desde_base(db, rid, clave=f"{i:03d}")
        if not any(x.tipo == "Material" for x in a.insumos):
            a.concepto += " (mano de obra; material en 'Por cotizar')"
            solo_mo.append(rid)
        pres.agregar(a, round(q[rid], 2))
    return pres, db, solo_mo


def programa(V, nombre, pres, db, q):
    from vertice import programa as P
    pr = P.Programa(nombre)
    clave = {c.apu.clave: c for c in pres.conceptos}
    rid_de = {}
    for c in pres.conceptos:
        for rid in q:
            if c.apu.concepto.startswith(db.rendimiento(rid)["concepto"]):
                rid_de[rid] = c

    def act(i, nombre_, rids, pred, cuadrillas=1, extra=0):
        dur, costo = 0, 0.0
        for rid in rids:
            if rid not in rid_de:
                continue
            r = db.rendimiento(rid)
            dur += P.duracion_por_rendimiento(q[rid], (r["rend_min"] + r["rend_max"]) / 2, cuadrillas)
            costo += pres.pu(rid_de[rid]) * rid_de[rid].cantidad
        if dur == 0:
            return None
        return pr.agregar(i, nombre_, dur + extra, [p for p in pred if p in pr.acts], costo=costo, partida="")
    act("A01", "Trazo, excavación y plantillas", ["exc-mano", "plantilla"], [], 3)
    act("A02", "Cimbra, acero y colado de cimentación", ["cimbra-cim"], ["A01"], 2, 2)
    act("A03", "Relleno compactado y firme", ["relleno", "firme"], ["A02"], 2)
    act("A04", "Muros, castillos y dalas planta baja", ["block-15", "block-20", "castillo"], ["A02"], 4)
    act("A05", "Cimbra, acero y colado de entrepiso", ["cimbra-losa", "cimbra-trabe"], ["A04"], 3, 3)
    act("A06", "Acero de refuerzo (habilitado)", ["acero-ligero", "acero-medio"], ["A02"], 3)
    act("A07", "Colados con concreto premezclado", ["colado-bomba", "colado-trompo"], ["A05", "A06"], 1, 2)
    act("A08", "Dalas y cerramientos", ["dala"], ["A04"], 2)
    act("A09", "Instalación eléctrica (ranurado, tubería y cableado)", ["salida-elec"], ["A08"], 1)
    act("A10", "Instalación hidrosanitaria y gas", ["salida-hid"], ["A08"], 1)
    act("A11", "Aplanados de fachada", ["aplanado"], ["A07"], 2)
    act("A12", "Aplanados de yeso interiores y plafones", ["yeso"], ["A09", "A10", "A07"], 3)
    act("A13", "Impermeabilización", ["imper"], ["A07"], 1)
    act("A14", "Pisos y azulejos", ["piso-cer", "azulejo"], ["A12", "A03"], 2)
    act("A15", "Pintura", ["pintura"], ["A14"], 2)
    pr.calcular()
    resto = pres.subtotal - sum(a.costo for a in pr.acts.values())
    tot = sum(a.costo for a in pr.acts.values()) or 1
    for a in pr.acts.values():
        a.costo += resto * a.costo / tot
    filas, res = P.flujo_de_caja(pr, pres.subtotal, pago=P.EsquemaPago(anticipo=0.30, periodo_estimacion=2, dias_pago=1))
    return pr, filas, res


def excel(pres, ruta, q, notas, cotizar, db):
    pres.a_excel(ruta)
    from openpyxl import load_workbook
    from openpyxl.styles import Font, PatternFill
    wb = load_workbook(ruta)
    H = Font(bold=True, color="FFFFFF"); F = PatternFill("solid", fgColor="1D2328")
    ws = wb.create_sheet("Generadores")
    for j, v in enumerate(["Clave base", "Concepto", "Unidad", "Cantidad", "Origen de la cantidad"], 1):
        c = ws.cell(1, j, v); c.font = H; c.fill = F
    for i, (rid, v) in enumerate(q.items(), 2):
        r = db.rendimiento(rid)
        ws.cell(i, 1, rid); ws.cell(i, 2, r["concepto"]); ws.cell(i, 3, r["unidad"]); ws.cell(i, 4, v)
        ws.cell(i, 5, "; ".join(notas.get(rid, [])) or "Geometría de planos y cálculo estructural")
    for col, wd in zip("ABCDE", (14, 60, 8, 12, 60)):
        ws.column_dimensions[col].width = wd
    wc = wb.create_sheet("Por cotizar")
    for j, v in enumerate(["Concepto", "Unidad", "Cantidad", "Precio unitario (capturar)", "Importe"], 1):
        c = wc.cell(1, j, v); c.font = H; c.fill = F
    for i, (d, u, c) in enumerate(cotizar, 2):
        wc.cell(i, 1, d); wc.cell(i, 2, u); wc.cell(i, 3, c)
        wc.cell(i, 5, f"=C{i}*D{i}")
    n = len(cotizar) + 1
    wc.cell(n + 2, 1, "TOTAL POR COTIZAR").font = Font(bold=True)
    wc.cell(n + 2, 5, f"=SUM(E2:E{n})")
    wc.column_dimensions["A"].width = 80; wc.column_dimensions["D"].width = 22; wc.column_dimensions["E"].width = 16
    wb.save(ruta)
