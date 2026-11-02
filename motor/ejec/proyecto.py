"""Proyecto ejecutivo de vivienda: láminas, memoria técnica, presupuesto, programa y revisión de coordinación."""
import json
import os
import shutil
import subprocess

from .. import planos, instalaciones as INS, revision
from ..hojas import Juego, Fila
from . import arq, estplan, inst as IE, costo, coordinacion, est as EST


def generar(V, carpeta, datos, proy, plan, corr, lays, r, spec, nombre, ins_calc):
    """Genera el proyecto ejecutivo en `carpeta`. Regresa un resumen (dict)."""
    if os.path.exists(carpeta):
        shutil.rmtree(carpeta)
    os.makedirs(carpeta)
    blq = proy["bloques"][0]
    niveles = blq["niveles"]
    t = proy["terreno"]
    esp = (r["t_x"] / 100, r["t_y"] / 100)
    xs, ys = arq.ejes(r)
    materiales = [m.strip() for m in (spec.get("materiales") or corr["materiales"]).replace(";", ".").split(".") if m.strip()]
    notas = ["Cotas en metros. Ejes, niveles y cotas rigen sobre el dibujo.",
             "Proyecto ejecutivo generado por el motor Vértice y revisado por coordinación automática.",
             "Requiere revisión y firma de DRO y corresponsables, y estudio de mecánica de suelos.",
             "Normativa: Reglamento de Edificaciones de Tijuana, NTC-2017, NOM-001-SEDE-2012, NOM-004-SEDG-2004."]
    datos = dict(datos, leyenda="Proyecto ejecutivo — para licencia requiere firma de DRO y corresponsables")
    J = Juego(carpeta, datos, notas, nombre_pdf="juego_de_planos.pdf", jpg=True)
    sep = max(4.5, blq["w"] * 0.45)

    def plantas(h, fn, titulo_fn, gris=False, sep_=sep, y_titulo=None):
        F = Fila(h["dx"], sep_, y_titulo=y_titulo)
        for k, n in enumerate(niveles):
            cu, va = lays[k]
            F.poner(blq["w"], blq["d"], lambda ox, k=k, cu=cu, va=va: fn(ox - blq["x"], -blq["y"], k, cu, va),
                    titulo_fn(n), h=0.32)
        return F

    # ------------------------------------------------ ARQUITECTÓNICO
    h = J.nueva("A-01", "Planta de conjunto", disciplina="Arquitectónico")
    planos.exteriores(h["dx"], proy)
    planos.planta_arq(h["dx"], blq, lays[0][0], lays[0][1], texto=True, cotas=False, esp=esp)
    A_t = t["frente"] * t["fondo"]
    A_c = sum(blq["w"] * blq["d"] for _ in niveles)
    filas = [("Terreno", f"{A_t:,.2f} m2"), ("Desplante", f"{blq['w'] * blq['d']:,.2f} m2"),
             ("C.O.S.", f"{blq['w'] * blq['d'] / A_t:.2f}"), ("Construcción total", f"{A_c:,.2f} m2"),
             ("C.U.S.", f"{A_c / A_t:.2f}"), ("Niveles", str(len(niveles))),
             ("Cajones de estacionamiento", "2" if A_t >= 300 else "1")]
    planos.cuadro_areas(h["dx"], t["frente"] + 6.0, t["fondo"], filas, 0.32)
    J.cerrar(h)

    h = J.nueva("A-02", "Plantas arquitectónicas amuebladas", disciplina="Arquitectónico")

    def amueb(ox, oy, k, cu, va):
        planos.planta_arq(h["dx"], blq, cu, va, ox, oy, texto=True, cotas=False, esp=esp)
        for c in cu:
            if not c["contenedor"]:
                arq.amueblar(h["dx"], c, va, ox, oy)
    plantas(h, amueb, lambda n: f"{n['nombre'].upper()} — NPT {'±0.00' if n is niveles[0] else '+' + format(sum(x['h'] for x in niveles[:niveles.index(n)]), '.2f')}")
    J.cerrar(h)

    # cortes: A-A' por la escalera (plano x), B-B' por la zona social (plano y)
    esc = next((c for c in lays[0][0] if c["t"] == "escalera" and not c["contenedor"]), None)
    xA = (esc["x"] + esc["w"] * 0.5) if esc else blq["x"] + blq["w"] * 0.3
    soc = max((c for c in lays[0][0] if c["t"] == "social" and not c["contenedor"]), key=lambda c: c["w"] * c["d"], default=None)
    yB = (soc["y"] + soc["d"] * 0.5) if soc else blq["y"] + blq["d"] * 0.7

    h = J.nueva("A-03", "Plantas acotadas a ejes", disciplina="Arquitectónico")

    def acot(ox, oy, k, cu, va):
        planos.planta_arq(h["dx"], blq, cu, va, ox, oy, texto=True, cotas=False, esp=esp)
        arq.dibujar_ejes(h["dx"], blq, xs, ys, ox, oy)
        if k == 0:
            for (p0, p1, et) in (((xA, blq["y"] - 1.0), (xA, blq["y"] + blq["d"] + 1.0), "A"),
                                 ((blq["x"] - 1.0, yB), (blq["x"] + blq["w"] + 1.0, yB), "B")):
                h["dx"].linea((p0[0] + ox, p0[1] + oy), (p1[0] + ox, p1[1] + oy), "A-EJES")
                for pp, s_ in ((p0, et), (p1, et + "'")):
                    h["dx"].texto((pp[0] + ox, pp[1] + oy), s_, 0.3, "A-TEXTO", centrado=True)
    plantas(h, acot, lambda n: n["nombre"].upper(), sep_=sep + 4.0, y_titulo=-5.2)
    J.cerrar(h)

    gas_xy = (blq["x"] + blq["w"] - 1.2, blq["y"] + blq["d"] - 1.2)
    h = J.nueva("A-04", "Planta de azotea", disciplina="Arquitectónico")
    sur_bap = corr["cubierta"].startswith("una")   # la cubierta a una agua baja al frente: bajadas al sur
    arq.azotea(h["dx"], blq, lays, r, ins_calc["resumen"]["n_baj"], gas_xy, -blq["x"], -blq["y"], sur_primero=sur_bap)
    arq.dibujar_ejes(h["dx"], blq, xs, ys, -blq["x"], -blq["y"])
    J.cerrar(h)

    h = J.nueva("A-05", "Fachadas", disciplina="Arquitectónico")
    ztop = sum(n["h"] for n in niveles) + 1.2
    dy = ztop + 4.5
    arq.fachada(h["dx"], blq, lays, corr, r, "S", 0, 0, materiales)
    arq.fachada(h["dx"], blq, lays, corr, r, "N", blq["w"] + 6, 0, materiales)
    arq.fachada(h["dx"], blq, lays, corr, r, "E", 0, -dy, materiales)
    arq.fachada(h["dx"], blq, lays, corr, r, "O", blq["d"] + 6, -dy, materiales)
    J.cerrar(h)

    h = J.nueva("A-06", "Cortes arquitectónicos", disciplina="Arquitectónico")
    arq.corte(h["dx"], blq, lays, r, "x", xA, 0, 0, "CORTE A-A' (POR ESCALERA)")
    arq.corte(h["dx"], blq, lays, r, "y", yB, 0, -(ztop + 5.0), "CORTE B-B' (POR ZONA SOCIAL)")
    J.cerrar(h)

    cancel, etiquetas = arq.claves_cancel(lays, niveles, corr, materiales)
    acab = {}
    for k in range(len(niveles)):
        for c in lays[k][0]:
            if not c["contenedor"]:
                acab.setdefault(c["n"], arq.acabados(c, materiales))
    h = J.nueva("A-07", "Cancelería y acabados", disciplina="Arquitectónico")

    def canc(ox, oy, k, cu, va):
        planos.planta_arq(h["dx"], blq, cu, va, ox, oy, texto=True, cotas=False, esp=esp)
        arq.etiquetar(h["dx"], etiquetas[k], ox, oy)
    plantas(h, canc, lambda n: n["nombre"].upper())
    y0 = -4.0
    yb = arq.tabla(h["dx"], 0, y0, ["Clave", "Tipo", "Ancho", "Alto", "Cant.", "Material / especificación"],
                   [[c["clave"], c["desc"], f"{c['ancho']:.2f}", f"{c['alto']:.2f}", c["cant"], c["mat"]] for c in cancel],
                   [1.0, 3.6, 1.0, 1.0, 0.9, 9.5], h=0.17, titulo="CUADRO DE CANCELERÍA Y PUERTAS")
    arq.tabla(h["dx"], 0, yb - 1.2, ["Local", "Piso", "Zoclo", "Muros", "Plafón"],
              [[n, a["piso"], a["zoclo"], a["muro"], a["plafon"]] for n, a in acab.items()],
              [2.9, 4.2, 2.0, 7.8, 4.0], h=0.15, titulo="CÉDULA DE ACABADOS")
    J.cerrar(h)

    # ------------------------------------------------ ESTRUCTURAL
    h = J.nueva("E-01", "Planta de cimentación", gris=True, disciplina="Estructural")
    estplan.cimentacion(h["dx"], blq, r, xs, ys, -blq["x"], -blq["y"])
    yb = arq.tabla(h["dx"], blq["w"] + 4.0, blq["d"], ["Clave", "Ubicación", "B (cm)", "h (cm)", "q serv (t/m²)", "Armado"],
                   [[z["clave"], z["desc"], f"{z['B']:.0f}", f"{z['h']:.0f}", f"{z['q']:.2f}", z["armado"]] for z in r["zapatas"]],
                   [1.1, 1.6, 1.0, 1.0, 1.5, 6.4], h=0.16, titulo="CUADRO DE ZAPATAS CORRIDAS")
    if r.get("columnas"):
        yb = arq.tabla(h["dx"], blq["w"] + 4.0, yb - 0.8, ["Clave", "Sección", "Armado", "P serv (t)"],
                       [[c["clave"], "15x30", c["armado"], f"{c['P']:.1f}"] for c in r["columnas"][:1]],
                       [1.1, 1.2, 7.0, 1.3], h=0.16, titulo="COLUMNAS")
    for i, n_ in enumerate(estplan.NOTAS):
        h["dx"].texto((blq["w"] + 4.0, yb - 1.0 - i * 0.34), n_, 0.13, "E-TEXTO")
    J.cerrar(h)

    h = J.nueva("E-02", "Losas, trabes y castillos", gris=True, disciplina="Estructural")
    F = Fila(h["dx"], sep + 4.0, y_titulo=-4.4)
    for k, n in enumerate(niveles):
        F.poner(blq["w"], blq["d"], lambda ox, k=k: estplan.losas(h["dx"], blq, r, k, xs, ys, ox - blq["x"], -blq["y"]),
                f"LOSA DE {r['losas'][k]['nombre'].upper()} h = {r['losas'][k]['h']} cm", h=0.32)
    filas_l = []
    for k, ls in enumerate(r["losas"]):
        for f in ls["filas"]:
            filas_l.append([f"L-{k + 1}", f["tablero"][:28], f"{f['a1']:.2f} x {f['a2']:.2f}", f"{f['Mu']:.0f}", f"{f['As_p']:.2f}",
                            f"#3@{f['s']}"])
    yb = arq.tabla(h["dx"], 0, -6.0, ["Losa", "Tablero", "Claros (m)", "Mu (kg·m/m)", "As (cm²/m)", "Armado"], filas_l,
                   [0.9, 4.2, 1.8, 1.6, 1.5, 1.3], h=0.15, titulo="CUADRO DE LOSAS (#3 ambos sentidos, bastones ln/4 en apoyos continuos)")
    arq.tabla(h["dx"], 12.5, -6.0, ["Clave", "Tipo", "Nivel", "b x h (cm)", "L (m)", "Lecho inf.", "Lecho sup.", "Estribos #2.5"],
              [[tb["clave"], tb["tipo"], tb["nivel"], f"{tb['b']}x{tb['h']}", f"{tb['L']:.2f}", tb["inf"], tb["sup"],
                f"@ {tb['s']:g} cm"] for tb in r["trabes"]],
              [0.9, 1.8, 1.6, 1.3, 0.9, 2.6, 1.0, 1.4], h=0.15, titulo="CUADRO DE TRABES")
    J.cerrar(h)

    h = J.nueva("E-03", "Detalles estructurales", disciplina="Estructural")
    dx = h["dx"]
    x = 0.0
    for z in r["zapatas"]:
        estplan.detalle_zapata(dx, x + z["B"] / 200 + 0.2, 0.0, z, r)
        x += max(z["B"] / 100 + 1.4, 3.6)
    tc = r["t_x"] / 100
    estplan.detalle_seccion(dx, x, 0.4, max(r["t_x"], r["t_y"]) / 100, 0.20, [0.95, 0.95], [0.95, 0.95], "E #2.5 @ 20 cm (@ 10 en 40 cm extremos)",
                            "K-1 CASTILLO", "4 #3, f'c 150 kg/cm²")
    x += 1.4
    estplan.detalle_seccion(dx, x, 0.4, max(r["t_x"], r["t_y"]) / 100, 0.20, [0.95, 0.95], [0.95, 0.95], "E #2.5 @ 20 cm",
                            "D-1 DALA", "4 #3, f'c 150 kg/cm²")
    x += 1.1
    vistos = set()
    for tb in r["trabes"]:
        key = (tb["b"], tb["h"], tb["inf"])
        if key in vistos or len(vistos) >= 4:
            continue
        vistos.add(key)
        db = {3: 0.95, 4: 1.27, 5: 1.59, 6: 1.91}[tb["num_inf"]]
        estplan.detalle_seccion(dx, x, 0.4, tb["b"] / 100, tb["h"] / 100, [0.95, 0.95], [db] * tb["n_inf"],
                                f"E #2.5 @ {tb['s']:g} cm", f"{tb['clave']} {tb['b']}x{tb['h']}", f"Inf. {tb['inf']}")
        x += max(tb["b"] / 100 + 0.5, 1.3)
    if r.get("escalera"):
        estplan.detalle_escalera(dx, 0.0, -2.9, r["escalera"])
    J.cerrar(h)

    h = J.nueva("E-04", "Cuantificación de acero y concreto", disciplina="Estructural")
    cu = r["cuantificacion"]
    arq.tabla(h["dx"], 0.0, 0.0, ["Elemento", "Cantidad", "Unidad", "#2.5 (kg)", "#3 (kg)", "#4–#6 (kg)", "Concreto (m³)"],
              [[f["elemento"], f["cantidad"], f["unidad"], f["kg2"], f["kg3"], f["kg4"], f["concreto"]] for f in cu["filas"]]
              + [["TOTAL", "", "", cu["total"]["kg2"], cu["total"]["kg3"], cu["total"]["kg4"], cu["total"]["concreto"]]],
              [7.2, 1.6, 1.1, 1.5, 1.5, 1.6, 1.8], h=0.17, titulo="CUANTIFICACIÓN DE ACERO Y CONCRETO")
    A_c = blq["w"] * blq["d"] * len(niveles)
    h["dx"].texto((0.0, -(len(cu["filas"]) + 3) * 0.33 - 0.6),
                  f"Índices: {cu['total']['kg'] / A_c:.1f} kg de acero y {cu['total']['concreto'] / A_c:.3f} m³ de concreto por m² construido. "
                  "Longitudes con traslapes y anclajes; desperdicio no incluido.", 0.16, "T-TABLA")
    J.cerrar(h)

    # ------------------------------------------------ INSTALACIONES
    cc = IE.circuitos(blq, lays)
    proy["_ci"] = False
    for clave, tit, fn in (("IH-01", "Instalación hidráulica", "ih"), ("IS-01", "Instalación sanitaria y pluvial", "is"),
                           ("IE-01", "Instalación eléctrica", "ie"), ("IG-01", "Instalación de gas LP", "ig")):
        h = J.nueva(clave, tit, gris=True, disciplina="Instalaciones")

        def dib(ox, oy, k, cu, va, fn=fn, h=h):
            planos.planta_arq(h["dx"], blq, cu, va, ox, oy, texto=fn == "ie", cotas=False, esp=esp)
            arq.dibujar_ejes(h["dx"], blq, xs, ys, ox, oy, cotas=False)
            pg = k == 0
            if fn == "ih":
                INS.hidraulica(h["dx"], proy, blq, cu, ox, oy, k, pg)
            elif fn == "is":
                INS.sanitaria(h["dx"], proy, blq, cu, ox, oy, k)
            elif fn == "ie":
                INS.electrica(h["dx"], proy, blq, cu, ox, oy, k, pg)
                IE.tag_circuitos(h["dx"], blq, lays, cc, k, ox, oy)
            else:
                INS.gas(h["dx"], proy, blq, cu, ox, oy, k, pg)
        F = plantas(h, dib, lambda n: n["nombre"].upper(), sep_=sep + 4.0, y_titulo=-4.4)
        if fn == "is":
            F.poner(blq["w"], blq["d"], lambda ox: INS.pluvial(h["dx"], proy, blq, ox - blq["x"], -blq["y"], ins_calc["resumen"]["n_baj"],
                                                    pts=INS.puntos_bap(blq, ins_calc["resumen"]["n_baj"], ox - blq["x"], -blq["y"], sur_bap)),
                    "AZOTEA — PLUVIAL", h=0.32)
        if fn == "ig":
            IE.isometrico_gas(h["dx"], blq, lays, F.x + 3.0, 0.0)
            IE.gas_tabla(h["dx"], 0, -6.2)
        J.cerrar(h)
    h = J.nueva("IH-02", "Isométrico hidráulico", disciplina="Instalaciones")
    IE.isometrico_hidraulico(h["dx"], blq, lays, 0, 0)
    J.cerrar(h)
    h = J.nueva("IE-02", "Cuadro de cargas y diagrama unifilar", disciplina="Instalaciones")
    IE.cuadro_cargas(h["dx"], 0, 0, cc)
    IE.unifilar(h["dx"], 21.0, 0.5, cc)
    J.cerrar(h)

    # ------------------------------------------------ COSTO Y TIEMPO
    q, notas_q = costo.generadores(blq, lays, r, cancel, acab)
    area = sum(blq["w"] * blq["d"] for _ in niveles)
    pres, db, solo_mo = costo.presupuesto(V, nombre, blq, q, area)
    cot = costo.por_cotizar(blq, lays, r, cancel, q, cc)
    costo.excel(pres, os.path.join(carpeta, "presupuesto.xlsx"), q, notas_q, cot, db)
    pr, flujo, res_f = costo.programa(V, nombre, pres, db, q)
    from vertice import programa as P
    gantt = os.path.join(carpeta, "programa_gantt.png")
    pr.gantt_png(gantt, titulo=f"Programa de obra — {nombre}")
    P.curva_s_png(pr, os.path.join(carpeta, "curva_s.png"))
    P.programa_a_excel(pr, flujo, res_f, os.path.join(carpeta, "programa_obra.xlsx"))
    J.imagen(gantt, "Programa de obra")

    # ------------------------------------------------ revisión de coordinación
    rev_arq = revision.revisar(proy, [lays])
    coord = coordinacion.revisar(blq, lays, r, cc, cancel, acab, q, rev_arq)
    zp = J.fin(f"{datos['clave']}_ejecutivo_dxf.zip")

    resumen = dict(hojas=J.hojas, pdf=os.path.basename(J.pdf_ruta), zip=os.path.basename(zp),
                   presupuesto=dict(subtotal=round(pres.subtotal), total=round(pres.total), por_m2=round(pres.subtotal / area),
                                    costo_directo=round(pres.costo_directo), partidas={k: round(v) for k, v in pres.por_partida().items()},
                                    solo_mano_obra=solo_mo, por_cotizar=len(cot)),
                   programa=dict(dias=pr.duracion_total, semanas=pr.semanas,
                                 financiamiento=round(res_f.get("necesidad_max_financiamiento", 0))),
                   estructura=dict(t_x=r["t_x"], t_y=r["t_y"], losas=[(l["nombre"], l["h"], l["s"]) for l in r["losas"]],
                                   sismo=r["sismo"], simplificado=r["simplificado"], zapatas=r["zapatas"],
                                   trabes=len(r["trabes"]), acero_kg=r["cuantificacion"]["total"]["kg"],
                                   concreto_m3=r["cuantificacion"]["total"]["concreto"], ajustes=r.get("ajustes", [])),
                   electrica=dict(circuitos=len(cc["circuitos"]), total=cc["total"], demanda=cc["demanda"],
                                  general=cc["prot_general"], desbalance=cc["desbalance"]),
                   coordinacion=coord, cancel=cancel, acabados=acab)
    # memoria técnica (Word) y PDF si hay LibreOffice
    from . import memoria
    doc = memoria.escribir(V, os.path.join(carpeta, "memoria_tecnica.docx"), nombre, datos, proy, blq, r, cc, coord, resumen,
                           materiales, ins_calc, spec)
    if shutil.which("libreoffice") or shutil.which("soffice"):
        try:
            subprocess.run([shutil.which("libreoffice") or shutil.which("soffice"), "--headless", "--convert-to", "pdf",
                            "--outdir", carpeta, doc], check=True, timeout=180, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass
    with open(os.path.join(carpeta, "proyecto_ejecutivo.json"), "w", encoding="utf-8") as f:
        json.dump(resumen, f, ensure_ascii=False, indent=1, default=str)
    return resumen
