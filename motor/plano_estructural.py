"""Planos estructurales: cimentación y planta estructural tipo."""
from .dxf import ROJO, AMARILLO, VERDE, CIAN, MAGENTA, BLANCO, GRIS
from .estructura import letras


def capas(dx):
    dx.capa("E-EJES", ROJO, "CENTER"); dx.capa("E-COLUMNAS", AMARILLO); dx.capa("E-TRABES", CIAN)
    dx.capa("E-ZAPATAS", MAGENTA, "DASHED"); dx.capa("E-MUROS", BLANCO); dx.capa("E-CASTILLOS", AMARILLO)
    dx.capa("E-TEXTO", VERDE); dx.capa("E-LOSA", GRIS, "HIDDEN")


def _ejes(dx, blq, est, ox, oy):
    x0, y0, w, d = blq["x"] + ox, blq["y"] + oy, blq["w"], blq["d"]
    ex = est["ejes_x"]; ey = est["ejes_y"]
    if est["sistema"] == "mamposteria":
        ex = sorted(set(round(v, 1) for v in ex)); ey = sorted(set(round(v, 1) for v in ey))
    r = max(0.35, max(w, d) / 70)
    ext = r * 4
    for i, x in enumerate(ex):
        dx.linea((x0 + x, y0 - ext), (x0 + x, y0 + d + ext), "E-EJES")
        dx.circulo((x0 + x, y0 + d + ext + r), r, "E-EJES")
        dx.texto((x0 + x, y0 + d + ext + r), str(i + 1), r, "E-TEXTO", centrado=True)
    for x1, x2 in zip(ex, ex[1:]):
        dx.cota((x0 + x1, y0 + d + ext * 0.6), (x0 + x2, y0 + d + ext * 0.6), 0.3)
    L = letras(len(ey))
    for j, y in enumerate(ey):
        dx.linea((x0 - ext, y0 + y), (x0 + w + ext, y0 + y), "E-EJES")
        dx.circulo((x0 - ext - r, y0 + y), r, "E-EJES")
        dx.texto((x0 - ext - r, y0 + y), L[j], r, "E-TEXTO", centrado=True)
    for y1, y2 in zip(ey, ey[1:]):
        dx.cota((x0 - ext * 0.6, y0 + y1), (x0 - ext * 0.6, y0 + y2), -0.3)


def cimentacion(dx, blq, est, ox, oy):
    _ejes(dx, blq, est, ox, oy)
    th = max(0.2, max(blq["w"], blq["d"]) / 90)
    if est["sistema"] == "mamposteria":
        B = est["zap_corrida"]
        for a, b in est["muros"]:
            if abs(a[1] - b[1]) < 1e-6:
                dx.rect(min(a[0], b[0]) + ox - B / 2, a[1] + oy - B / 2, abs(b[0] - a[0]) + B, B, "E-ZAPATAS")
            else:
                dx.rect(a[0] + ox - B / 2, min(a[1], b[1]) + oy - B / 2, B, abs(b[1] - a[1]) + B, "E-ZAPATAS")
            dx.linea((a[0] + ox, a[1] + oy), (b[0] + ox, b[1] + oy), "E-MUROS")
        for p in est["castillos"]:
            dx.rect(p[0] + ox - 0.075, p[1] + oy - 0.1, 0.15, 0.2, "E-CASTILLOS")
        dx.texto((blq["x"] + ox, blq["y"] + oy - 2.5), f"ZC-1: ZAPATA CORRIDA B = {B:.2f} m CON CONTRATRABE CT-1 20x40",
                 th, "E-TEXTO")
        return
    if est.get("losa_cim"):
        dx.rect(blq["x"] + ox - 0.5, blq["y"] + oy - 0.5, blq["w"] + 1, blq["d"] + 1, "E-ZAPATAS")
        for a, b in est["trabes"]:
            dx.linea((a[0] + ox, a[1] + oy), (b[0] + ox, b[1] + oy), "E-TRABES")
        dx.texto((blq["x"] + ox, blq["y"] + oy - 3), "LOSA DE CIMENTACIÓN CON CONTRATRABES (VER TABLA)", th, "E-TEXTO")
    for x, y, B in est["zapatas"]:
        dx.rect(x + ox - B / 2, y + oy - B / 2, B, B, "E-ZAPATAS")
    for x, y, b, h in est["columnas"]:
        dx.rect(x + ox - b / 2, y + oy - h / 2, b, h, "E-COLUMNAS")
    if est["zapatas"]:
        B = est["zapatas"][0][2]
        dx.texto((blq["x"] + ox, blq["y"] + oy - 3), f"Z-1: ZAPATA AISLADA {B:.2f} x {B:.2f} m", th, "E-TEXTO")


def planta_est(dx, blq, est, cuartos, ox, oy):
    _ejes(dx, blq, est, ox, oy)
    th = max(0.2, max(blq["w"], blq["d"]) / 90)
    if est["sistema"] == "mamposteria":
        for a, b in est["muros"]:
            dx.linea((a[0] + ox, a[1] + oy), (b[0] + ox, b[1] + oy), "E-MUROS")
        for p in est["castillos"]:
            dx.rect(p[0] + ox - 0.075, p[1] + oy - 0.1, 0.15, 0.2, "E-CASTILLOS")
        for c in cuartos:
            if not c["contenedor"]:
                dx.texto((c["x"] + ox + c["w"] / 2, c["y"] + oy + c["d"] / 2), f"L-1 h={est['calc']['h_losa_cm']}",
                         min(0.25, c["w"] / 10), "E-TEXTO", centrado=True)
                dx.linea((c["x"] + ox + 0.3, c["y"] + oy + 0.3), (c["x"] + ox + c["w"] - 0.3, c["y"] + oy + c["d"] - 0.3), "E-LOSA")
        dx.texto((blq["x"] + ox, blq["y"] + oy - 2.5), "MUROS DE BLOCK 15 cm, CASTILLOS K-1 15x20, DALAS D-1 15x20", th, "E-TEXTO")
        return
    for x, y, b, h in est["columnas"]:
        dx.rect(x + ox - b / 2, y + oy - h / 2, b, h, "E-COLUMNAS")
    if est["sistema"] == "acero":
        for a, b in est["trabes"]:
            dx.linea((a[0] + ox, a[1] + oy), (b[0] + ox, b[1] + oy), "E-TRABES")
        y0, d = blq["y"] + oy, blq["d"]
        n = int(d / 1.5)
        x0, w = blq["x"] + ox, blq["w"]
        for k in range(n + 1):
            dx.linea((x0, y0 + k * 1.5), (x0 + w, y0 + k * 1.5), "E-LOSA")
        ey = est["ejes_y"]
        for ya, yb in ((ey[0], ey[1]), (ey[-2], ey[-1])):
            dx.linea((x0, y0 + ya), (x0 + w, y0 + yb), "E-TRABES")
            dx.linea((x0, y0 + yb), (x0 + w, y0 + ya), "E-TRABES")
        dx.texto((x0, y0 - 3), "MR-1: MARCO RÍGIDO / ARMADURA (VER TABLA) — LARGUEROS MONTEN 8\" @ 1.50 m — CONTRAVENTEO EN CRUZ",
                 th, "E-TEXTO")
        return
    for a, b in est["trabes"]:
        dx.linea((a[0] + ox, a[1] + oy), (b[0] + ox, b[1] + oy), "E-TRABES")
    c = est["calc"]
    ex, ey = est["ejes_x"], est["ejes_y"]
    for i in range(len(ex) - 1):
        for j in range(len(ey) - 1):
            cx = blq["x"] + ox + (ex[i] + ex[i + 1]) / 2
            cy = blq["y"] + oy + (ey[j] + ey[j + 1]) / 2
            dx.texto((cx, cy), f"L-1 h={c['losa_cm']}", th * 0.8, "E-TEXTO", centrado=True)
    dx.texto((blq["x"] + ox, blq["y"] + oy - 3),
             f"C-1 {c['columna_cm']}x{c['columna_cm']}   T-1 {c['trabe_cm']}   f'c={c['fc']} kg/cm2   fy=4200 kg/cm2", th, "E-TEXTO")
