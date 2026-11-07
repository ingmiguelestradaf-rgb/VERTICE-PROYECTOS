"""Planos estructurales ejecutivos de vivienda: cimentación, losas y trabes, detalles y cuantificación."""
import math
from . import arq
from .est import paneles, EPS

NOTAS = [
    "1. Cotas en metros salvo indicación; las cotas rigen sobre el dibujo. Verificar en obra contra planos arquitectónicos.",
    "2. Concreto en zapatas, losas, trabes y escalera f'c = 250 kg/cm²; castillos y dalas f'c = 150 kg/cm². Agregado máx. 3/4\".",
    "3. Acero de refuerzo NMX-B-506 grado 42 (fy = 4200 kg/cm²); estribos #2.5 (5/16\") o alambrón de 1/4\" según cuadro.",
    "4. Recubrimientos libres: zapatas 5 cm (sobre plantilla), trabes 3 cm, losas 2 cm, castillos y dalas 2 cm.",
    "5. Block hueco de concreto 15x20x40 / 20x20x40 cm, f*m ≥ 20 kg/cm², junteado con mortero tipo I (1:¼:3).",
    "6. Castillos en extremos de muros, en ambos lados de vanos e intersecciones, a no más de 4.00 m; dalas en desplante, cerramiento y pretil.",
    "7. Traslapes: #3 = 40 cm, #4 = 55 cm, #5 = 70 cm, #6 = 85 cm; no traslapar más del 50 % del acero en una sección.",
    "8. Capacidad de carga supuesta q adm = 12 t/m² a -0.80 m: VALIDAR CON ESTUDIO DE MECÁNICA DE SUELOS antes de construir.",
    "9. Diseño conforme a Reglamento de Edificaciones de Tijuana, NTC-2017 (Mampostería, Concreto, Cimentaciones, Sismo) y MDOC-CFE.",
]


def capas(dx):
    dx.capa("E-EJES", 1, "CENTER"); dx.capa("E-MUROS", 7); dx.capa("E-CASTILLOS", 2); dx.capa("E-ZAPATAS", 6, "DASHED")
    dx.capa("E-TRABES", 4, "DASHED"); dx.capa("E-ACERO", 1); dx.capa("E-TEXTO", 3); dx.capa("E-LOSA", 8)
    dx.capa("E-CONCRETO", 7)


def _muro(dx, ln, t, ox, oy, capa="E-MUROS", vanos=None):
    segs = paneles(ln, vanos) if vanos is not None else [(ln["a"], ln["b"])]
    for a, b in segs:
        if ln["eje"] == "h":
            dx.rect(a + ox, ln["c"] - t / 2 + oy, b - a, t, capa)
        else:
            dx.rect(ln["c"] - t / 2 + ox, a + oy, t, b - a, capa)


def _castillo(dx, p, tx, ty, ox, oy):
    x, y = p[0] + ox, p[1] + oy
    w, h = ty, tx
    dx.rect(x - w / 2, y - h / 2, w, h, "E-CASTILLOS")
    dx.linea((x - w / 2, y - h / 2), (x + w / 2, y + h / 2), "E-CASTILLOS")
    dx.linea((x - w / 2, y + h / 2), (x + w / 2, y - h / 2), "E-CASTILLOS")


def cimentacion(dx, blq, r, xs, ys, ox=0.0, oy=0.0):
    tx, ty = r["t_x"] / 100, r["t_y"] / 100
    arq.dibujar_ejes(dx, blq, xs, ys, ox, oy, capa="E-EJES")
    col = set(blq.get("colindancias", []))
    for cl in r["cargas_lineas"]:
        z = r["zap_linea"][(cl["eje"], round(cl["c"], 3), cl["a"])]
        B = z["B"] / 100
        t = tx if cl["eje"] == "h" else ty
        # zapata (excéntrica en lindero: paño exterior en el límite del predio)
        off = 0.0
        if z.get("lindero"):
            sgn = -1 if z["lado"] in ("O", "S") else 1
            off = -sgn * (B / 2 - 0.125)
        if cl["eje"] == "h":
            dx.rect(cl["a"] - B / 2 + ox, cl["c"] - B / 2 + off + oy, cl["b"] - cl["a"] + B, B, "E-ZAPATAS")
        else:
            dx.rect(cl["c"] - B / 2 + off + ox, cl["a"] - B / 2 + oy, B, cl["b"] - cl["a"] + B, "E-ZAPATAS")
        _muro(dx, cl, t, ox, oy)
        L = cl["b"] - cl["a"]
        if L > 2.0:
            m = (cl["a"] + cl["b"]) / 2
            et = z["clave"] + (" (LINDERO)" if z.get("lindero") else "")
            if cl["eje"] == "h":
                dx.texto((m + ox, cl["c"] + oy + B / 2 + 0.12), et, 0.15, "E-TEXTO", centrado=True)
            else:
                dx.texto((cl["c"] + ox + B / 2 + 0.25, m + oy), et, 0.15, "E-TEXTO", rot=90)
    for p in r["castillos"][0]:
        _castillo(dx, p, tx, ty, ox, oy)
    for c in r.get("columnas", []):
        dx.rect(c["x"] - 0.075 + ox, c["y"] - 0.15 + oy, 0.15, 0.30, "E-CASTILLOS")
        dx.texto((c["x"] + 0.2 + ox, c["y"] + oy + 0.25), "C-1", 0.15, "E-TEXTO")
    P = blq.get("pilotis")
    if P:
        # pilotis de la marquesina: zapatas aisladas fuera del paño (antes la cimentación no las incluía)
        r_, f = P["diam"] / 2, P["fondo"]
        yc = blq["y"] - f + r_ + 0.05
        for cx in P["cols"]:
            dx.rect(cx - 0.4 + ox, yc - 0.4 + oy, 0.8, 0.8, "E-ZAPATAS")
            dx.circulo((cx + ox, yc + oy), r_, "E-CASTILLOS")
        dx.texto(((P["x0"] + P["x1"]) / 2 + ox, yc - 0.75 + oy),
                 f"ZA-P: ZAPATA AISLADA 80x80x20 CM BAJO PILOTI Ø{P['diam'] * 100:.0f} CM (4 #4 + E #2.5 @ 15) — MARQUESINA e = {P['losa'] * 100:.0f} CM",
                 0.15, "E-TEXTO", centrado=True)
    dx.texto((blq["x"] + ox, blq["y"] + blq["d"] + oy + 1.0), "K-1: CASTILLO (VER DETALLE)   ZC: ZAPATA CORRIDA (VER CUADRO)", 0.17, "E-TEXTO")


def losas(dx, blq, r, k, xs, ys, ox=0.0, oy=0.0):
    tx, ty = r["t_x"] / 100, r["t_y"] / 100
    arq.dibujar_ejes(dx, blq, xs, ys, ox, oy, capa="E-EJES", cotas=False)
    ls = r["losas"][k]
    for ln in r["estructurales"][k]:
        _muro(dx, ln, (tx if ln["eje"] == "h" else ty), ox, oy, capa="E-LOSA")
    for t in r["tableros"][k]:
        x, y, w, d = t["x"] + ox, t["y"] + oy, t["w"], t["d"]
        # armado: flechas en ambas direcciones
        cx, cy = x + w / 2, y + d / 2
        dx.linea((x + 0.25, cy), (x + w - 0.25, cy), "E-ACERO")
        dx.linea((cx, y + 0.25), (cx, y + d - 0.25), "E-ACERO")
        for (a, b) in (((x + 0.25, cy), 0), ((x + w - 0.25, cy), 180), ((cx, y + 0.25), 90), ((cx, y + d - 0.25), 270)):
            ang = math.radians(b)
            dx.linea(a, (a[0] + 0.18 * math.cos(ang + 0.5), a[1] + 0.18 * math.sin(ang + 0.5)), "E-ACERO")
            dx.linea(a, (a[0] + 0.18 * math.cos(ang - 0.5), a[1] + 0.18 * math.sin(ang - 0.5)), "E-ACERO")
        hh = min(0.17, min(w, d) / 9)
        dx.texto((cx, cy + 0.22), f"L-{k + 1} h={ls['h']}", hh, "E-TEXTO", centrado=True)
        dx.texto((cx, cy - 0.32), f"#3@{t.get('s', ls['s'])} a.s.", hh * 0.9, "E-TEXTO", centrado=True)
    # hueco de escalera en entrepisos
    if k < len(r["losas"]) - 1:
        lays_esc = [c for c in r.get("_hojas", [[]])[k] if c["t"] == "escalera"]
        for c in lays_esc:
            x, y = c["x"] + ox, c["y"] + oy
            dx.rect(x, y, c["w"], c["d"], "E-LOSA")
            dx.linea((x, y), (x + c["w"], y + c["d"]), "E-LOSA"); dx.linea((x, y + c["d"]), (x + c["w"], y), "E-LOSA")
            dx.texto((x + c["w"] / 2, y + c["d"] / 2 + 0.3), "HUECO ESCALERA", 0.14, "E-TEXTO", centrado=True)
    # trabes del nivel
    for t in r["trabes"]:
        if t["nivel"] != blq["niveles"][k]["nombre"]:
            continue
        b = t["b"] / 100
        if t["linea"] == "h":
            dx.rect(t["a"] + ox - 0.05, t["c"] - b / 2 + oy, t["bb"] - t["a"] + 0.1, b, "E-TRABES")
            dx.texto(((t["a"] + t["bb"]) / 2 + ox, t["c"] + oy + b / 2 + 0.08), f"{t['clave']} {t['b']}x{t['h']}", 0.14, "E-TEXTO", centrado=True)
        else:
            dx.rect(t["c"] - b / 2 + ox, t["a"] + oy - 0.05, b, t["bb"] - t["a"] + 0.1, "E-TRABES")
            dx.texto((t["c"] + ox + b / 2 + 0.12, (t["a"] + t["bb"]) / 2 + oy), f"{t['clave']} {t['b']}x{t['h']}", 0.14, "E-TEXTO", rot=90)
    for p in r["castillos"][k]:
        _castillo(dx, p, tx, ty, ox, oy)


# ---------------------------------------------------------------- detalles
def _barra(dx, x, y, r=0.008):
    dx.circulo((x, y), r, "E-ACERO")


def detalle_zapata(dx, x0, y0, z, r):
    """Sección de zapata corrida a escala real (m). x0,y0: centro del desplante."""
    B, h = z["B"] / 100, z["h"] / 100
    Df = r["Df"]
    t = 0.15
    dx.rect(x0 - B / 2 - 0.05, y0 - 0.05, B + 0.1, 0.05, "E-CONCRETO")          # plantilla
    dx.rect(x0 - B / 2, y0, B, h, "E-CONCRETO")                                  # zapata
    dx.rect(x0 - t / 2, y0 + h, t, Df - h - 0.20, "E-CONCRETO")                   # enrase de block relleno
    dx.rect(x0 - t / 2, y0 + Df - 0.20, t, 0.20, "E-CONCRETO")                    # dala de desplante
    dx.rect(x0 - t / 2, y0 + Df, t, 0.6, "E-MUROS")                               # arranque de muro
    dx.linea((x0 - B / 2 - 0.4, y0 + Df), (x0 + B / 2 + 0.4, y0 + Df), "E-CONCRETO")
    # acero transversal (línea) y longitudinal (puntos)
    dx.linea((x0 - B / 2 + 0.05, y0 + 0.06), (x0 + B / 2 - 0.05, y0 + 0.06), "E-ACERO")
    for i in range(4):
        _barra(dx, x0 - B / 2 + 0.08 + (B - 0.16) * i / 3, y0 + 0.08)
    for dxx in (-0.045, 0.045):
        for dyy in (0.045, 0.155):
            _barra(dx, x0 + dxx, y0 + Df - 0.20 + dyy)
    h_t = 0.07
    dx.texto((x0 - B / 2, y0 - 0.22), f"{z['clave']}: B = {z['B']:.0f} cm, h = {z['h']:.0f} cm", h_t, "E-TEXTO")
    dx.texto((x0 - B / 2, y0 - 0.32), f"{z['armado']}", h_t * 0.85, "E-TEXTO")
    dx.texto((x0 - B / 2, y0 - 0.41), "Plantilla f'c 100 kg/cm² de 5 cm; dala de desplante D-1 15x20", h_t * 0.85, "E-TEXTO")
    dx.texto((x0 + B / 2 + 0.1, y0 + Df + 0.02), f"NPT ±0.00 / desplante -{Df:.2f}", h_t * 0.85, "E-TEXTO")


def detalle_seccion(dx, x0, y0, b, h, sup, inf, est, titulo, nota=""):
    """Sección rectangular (m): sup/inf listas de diámetros en cm para dibujar barras."""
    rec = 0.03
    dx.rect(x0, y0, b, h, "E-CONCRETO")
    dx.rect(x0 + rec, y0 + rec, b - 2 * rec, h - 2 * rec, "E-ACERO")
    for fila, yy in ((inf, y0 + rec + 0.012), (sup, y0 + h - rec - 0.012)):
        n = len(fila)
        for i, db in enumerate(fila):
            xx = x0 + rec + 0.012 + (b - 2 * rec - 0.024) * (i / (n - 1) if n > 1 else 0.5)
            dx.circulo((xx, yy), db / 200, "E-ACERO")
    dx.texto((x0, y0 - 0.09), titulo, 0.06, "E-TEXTO")
    if nota:
        dx.texto((x0, y0 - 0.17), nota, 0.05, "E-TEXTO")
    if est:
        dx.texto((x0, y0 - 0.25), est, 0.05, "E-TEXTO")


def detalle_escalera(dx, x0, y0, e):
    """Corte de rampa de escalera a escala real."""
    p, hu = e["peralte"] / 100, e["huella"] / 100
    n = e["peldanos"]
    pts = [(x0, y0)]
    for i in range(n):
        x, y = pts[-1]
        pts += [(x, y + p), (x + hu, y + p)]
    dx.polilinea(pts, "E-CONCRETO")
    L = hu * n
    H = p * n
    ang = math.atan2(H, L)
    hl = e["h"] / 100 / math.cos(ang)
    dx.linea((x0, y0 - hl), (x0 + L, y0 + H - hl), "E-CONCRETO")
    dx.linea((x0 + 0.03, y0 - hl + 0.03), (x0 + L - 0.03, y0 + H - hl + 0.03), "E-ACERO")
    dx.texto((x0, y0 - hl - 0.25), f"ESCALERA: {n} peraltes de {e['peralte']:.1f} cm, huella {e['huella']:.1f} cm, "
                                    f"losa h = {e['h']} cm, #3 @ {e['s']} cm longitudinal y #3 @ 25 cm transversal", 0.06, "E-TEXTO")
