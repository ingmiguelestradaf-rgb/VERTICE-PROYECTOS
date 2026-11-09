"""Planos arquitectónicos ejecutivos (vivienda): amueblado, acotado a ejes, azotea, fachadas, cortes,
cancelería y acabados. Los ejes son los mismos de los planos estructurales y de instalaciones."""
import math
from ..dxf import ROJO, GRIS, VERDE, CIAN
from .. import planos, layout

EPS = 0.02
LETRAS = "ABCDEFGHJKLMNPQRSTUVWXYZ"


def capas(dx):
    dx.capa("A-EJES", ROJO, "CENTER"); dx.capa("A-MUEBLES", GRIS); dx.capa("A-NIVELES", VERDE)
    dx.capa("A-HATCH", 8); dx.capa("A-TABLA", 7); dx.capa("T-TABLA", 7); dx.capa("T-TITULO", 3); dx.capa("A-CANCEL", CIAN)


# ------------------------------------------------------------------ utilidades
def tabla(dx, x, y, encabezados, filas, anchos, h=0.16, titulo=None, capa="T-TABLA"):
    """Tabla con líneas; (x, y) esquina superior izquierda. Regresa la y inferior."""
    if titulo:
        dx.texto((x, y + h * 0.7), titulo, h * 1.25, capa)
    fh = h * 1.9
    W = sum(anchos)
    filas = [encabezados] + [[str(c) for c in f] for f in filas]
    yy = y
    for i, f in enumerate(filas):
        dx.linea((x, yy), (x + W, yy), capa)
        xx = x
        for txt, an in zip(f, anchos):
            t = str(txt)
            maxc = max(4, int(an / (h * 0.62)))
            if len(t) > maxc:
                t = t[:maxc - 1] + "…"
            dx.texto((xx + h * 0.35, yy - fh * 0.68), t, h * (0.92 if i else 0.95), capa)
            xx += an
        yy -= fh
    dx.linea((x, yy), (x + W, yy), capa)
    xx = x
    for an in [0] + anchos:
        xx += an
        dx.linea((xx, y), (xx, yy), capa)
    return yy


def ejes(r):
    """Ejes del proyecto a partir de las líneas estructurales de todos los niveles."""
    xs, ys = [], []
    for lns in r["estructurales"]:
        for l in lns:
            (xs if l["eje"] == "v" else ys).append(l["c"])
    for t in r.get("trabes_carga", []):
        (xs if t["eje"] == "v" else ys).append(t["c"])

    def uniq(v):
        out = []
        for c in sorted(v):
            if not out or c - out[-1] > 0.05:
                out.append(c)
        return out
    return uniq(xs), uniq(ys)


def nombre_eje(i, eje):
    return str(i + 1) if eje == "x" else LETRAS[i % len(LETRAS)]


def dibujar_ejes(dx, blq, xs, ys, ox=0.0, oy=0.0, cotas=True, capa="A-EJES", r=0.32):
    x0, y0, x1, y1 = blq["x"] + ox, blq["y"] + oy, blq["x"] + blq["w"] + ox, blq["y"] + blq["d"] + oy
    ext = 1.6
    for i, x in enumerate(xs):
        dx.linea((x + ox, y0 - ext - 1.2), (x + ox, y1 + 0.6), capa)
        c = (x + ox, y0 - ext - 1.2 - r)
        dx.circulo(c, r, capa)
        dx.texto(c, nombre_eje(i, "x"), r * 0.9, capa, centrado=True)
    for j, y in enumerate(ys):
        dx.linea((x0 - ext - 1.2, y + oy), (x1 + 0.6, y + oy), capa)
        c = (x0 - ext - 1.2 - r, y + oy)
        dx.circulo(c, r, capa)
        dx.texto(c, nombre_eje(j, "y"), r * 0.9, capa, centrado=True)
    if cotas:
        for a, b in zip(xs, xs[1:]):
            dx.cota((a + ox, y0 - ext), (b + ox, y0 - ext), 0.0, h=0.17)
        dx.cota((xs[0] + ox, y0 - ext - 0.7), (xs[-1] + ox, y0 - ext - 0.7), 0.0, h=0.19)
        for a, b in zip(ys, ys[1:]):
            dx.cota((x0 - ext, a + oy), (x0 - ext, b + oy), 0.0, h=0.17)
        dx.cota((x0 - ext - 0.7, ys[0] + oy), (x0 - ext - 0.7, ys[-1] + oy), 0.0, h=0.19)


def _aberturas(c, vanos):
    """Lados del local con puerta o vano abierto."""
    out = set()
    for v in vanos:
        if v["tipo"] not in ("puerta", "vano", "puerta_ext", "porton"):
            continue
        if v["eje"] == "h":
            if v["a"] < c["x"] + c["w"] and v["b"] > c["x"]:
                if abs(v["c"] - c["y"]) < EPS:
                    out.add("S")
                if abs(v["c"] - (c["y"] + c["d"])) < EPS:
                    out.add("N")
        else:
            if v["a"] < c["y"] + c["d"] and v["b"] > c["y"]:
                if abs(v["c"] - c["x"]) < EPS:
                    out.add("O")
                if abs(v["c"] - (c["x"] + c["w"])) < EPS:
                    out.add("E")
    return out


OPUESTO = {"S": "N", "N": "S", "O": "E", "E": "O"}


def pared_libre(c, vanos, preferir_larga=False):
    ab = _aberturas(c, vanos)
    lados = ["S", "N", "O", "E"]
    largo = {"S": c["w"], "N": c["w"], "O": c["d"], "E": c["d"]}

    def score(l):
        s = 0 if l not in ab else 10
        if any(OPUESTO[l] == a for a in ab):
            s -= 2
        s -= largo[l] * (1.0 if preferir_larga else 0.1)
        return s
    return min(lados, key=score)


def _caja(dx, c, lado, ancho, fondo, despl=0.0, sep=0.08, capa="A-MUEBLES"):
    """Rectángulo apoyado en el muro `lado` del local, centrado (+despl a lo largo del muro)."""
    x, y, w, d = c["x"], c["y"], c["w"], c["d"]
    t = 0.1
    if lado in ("S", "N"):
        cx = x + w / 2 + despl - ancho / 2
        cy = y + t + sep if lado == "S" else y + d - t - sep - fondo
        rr = (cx, cy, ancho, fondo)
    else:
        cy = y + d / 2 + despl - ancho / 2
        cx = x + t + sep if lado == "O" else x + w - t - sep - fondo
        rr = (cx, cy, fondo, ancho)
    dx.rect(*rr, capa)
    return rr


def amueblar(dx, c, vanos, ox=0.0, oy=0.0):
    c = dict(c, x=c["x"] + ox, y=c["y"] + oy)
    vv = [dict(v, c=v["c"] + (oy if v["eje"] == "h" else ox), a=v["a"] + (ox if v["eje"] == "h" else oy),
               b=v["b"] + (ox if v["eje"] == "h" else oy)) for v in vanos]
    n, w, d = c["n"], c["w"], c["d"]
    corto, largo = min(w, d), max(w, d)
    lado = pared_libre(c, vv)
    L = "A-MUEBLES"
    if n.startswith("Recámara") and corto >= 2.6:
        princ = "principal" in n
        cw, cl = (1.6, 2.0) if princ else (1.35, 1.9)
        x0, y0, a, b = _caja(dx, c, lado, cw, cl)
        # almohadas
        if lado in ("S", "N"):
            yy = y0 + (0.1 if lado == "S" else b - 0.45)
            dx.rect(x0 + 0.1, yy, a / 2 - 0.15, 0.35, L); dx.rect(x0 + a / 2 + 0.05, yy, a / 2 - 0.15, 0.35, L)
        else:
            xx = x0 + (0.1 if lado == "O" else a - 0.45)
            dx.rect(xx, y0 + 0.1, 0.35, b / 2 - 0.15, L); dx.rect(xx, y0 + b / 2 + 0.05, 0.35, b / 2 - 0.15, L)
        for s_ in ((-1, 1) if princ else (1,)):
            _caja(dx, c, lado, 0.45, 0.4, s_ * (cw / 2 + 0.3))
        # clóset a lo largo de un muro lateral libre
        lat = [l for l in ("S", "N", "O", "E") if l not in (lado, OPUESTO[lado]) and l not in _aberturas(c, vv)]
        if lat and not princ:
            lc = lat[0]
            Lm = d if lc in ("O", "E") else w
            # el clóset deja libre el abatimiento de las puertas que están junto al muro donde se apoya
            ini, fin = 0.15, Lm - 0.15
            for v in vv:
                if v["tipo"] not in ("puerta", "vano", "puerta_ext"):
                    continue
                if lc in ("O", "E") and v["eje"] == "h" and v["a"] < c["x"] + w and v["b"] > c["x"] and \
                        (abs(v["c"] - c["y"]) < EPS or abs(v["c"] - c["y"] - d) < EPS):
                    pos = (v["a"] - c["x"]) if lc == "O" else (c["x"] + w - v["b"])
                    lejos = abs(v["c"] - c["y"]) >= EPS            # puerta en el muro N
                elif lc in ("S", "N") and v["eje"] == "v" and v["a"] < c["y"] + d and v["b"] > c["y"] and \
                        (abs(v["c"] - c["x"]) < EPS or abs(v["c"] - c["x"] - w) < EPS):
                    pos = (v["a"] - c["y"]) if lc == "S" else (c["y"] + d - v["b"])
                    lejos = abs(v["c"] - c["x"]) >= EPS            # puerta en el muro E
                else:
                    continue
                if pos < 0.6 + 0.1:
                    libre = (v["b"] - v["a"]) + 0.15
                    if lejos:
                        fin = min(fin, Lm - libre)
                    else:
                        ini = max(ini, libre)
            if ini == 0.15 and fin == Lm - 0.15:
                ini = 0.8                                          # criterio original: libre hacia el sur/oeste
            lon = fin - ini
            if lon > 1.2:
                x1, y1, a1, b1 = _caja(dx, c, lc, lon, 0.6, despl=(ini + fin) / 2 - Lm / 2, sep=0.0)
                dx.linea((x1, y1), (x1 + a1, y1 + b1), L)
                dx.texto((x1 + a1 / 2, y1 + b1 / 2), "CLÓSET", 0.12, L, centrado=True)
    elif n.startswith("Sala") or n in ("Family room", "Cuarto de TV", "Estancia familiar"):
        if n == "Estancia familiar" and corto < 2.8:
            return
        if "comedor" in n:
            # sala en la mitad lejana a la puerta, comedor en la otra
            half = dict(c, d=d / 2, y=c["y"] + d / 2) if d >= w else dict(c, w=w / 2, x=c["x"] + w / 2)
            otra = dict(c, d=d / 2) if d >= w else dict(c, w=w / 2)
            _sala(dx, half, "N" if d >= w else "E", vv)
            _comedor(dx, otra)
        else:
            _sala(dx, c, lado, vv)
    elif n == "Comedor":
        _comedor(dx, c)
    elif n.startswith("Cocina") and corto >= 1.8:
        lc = pared_libre(c, vv, preferir_larga=True)
        lon = (w if lc in ("S", "N") else d) - 0.3
        x0, y0, a, b = _caja(dx, c, lc, lon, 0.6, sep=0.0)
        # tarja, estufa, refrigerador sobre la cubierta
        if lc in ("S", "N"):
            dx.rect(x0 + 0.3, y0 + 0.08, 0.8, 0.44, L)
            ex = x0 + a / 2 + 0.2
            dx.rect(ex, y0 + 0.02, 0.76, 0.56, L)
            for i in range(2):
                for j in range(2):
                    dx.circulo((ex + 0.19 + 0.38 * i, y0 + 0.16 + 0.26 * j), 0.09, L)
            dx.rect(x0 + a - 0.9, y0, 0.85, 0.72 if lc == "S" else 0.6, L)
            dx.texto((x0 + a - 0.47, y0 + 0.3), "REF", 0.1, L, centrado=True)
        else:
            dx.rect(x0 + 0.08, y0 + 0.3, 0.44, 0.8, L)
            ey = y0 + b / 2 + 0.2
            dx.rect(x0 + 0.02, ey, 0.56, 0.76, L)
            for i in range(2):
                for j in range(2):
                    dx.circulo((x0 + 0.16 + 0.26 * j, ey + 0.19 + 0.38 * i), 0.09, L)
            dx.rect(x0, y0 + b - 0.9, 0.6, 0.85, L)
            dx.texto((x0 + 0.3, y0 + b - 0.47), "REF", 0.1, L, centrado=True)
        if corto >= 3.6:   # isla desplazada para no tapar el rótulo del local
            dx.rect(c["x"] + w / 2 - 0.6, c["y"] + d * 0.25 - 0.45, 1.2, 0.9, L)
    elif n.startswith("Baño") or n == "Medio baño":
        lb = pared_libre(c, vv, preferir_larga=True)
        lon = w if lb in ("S", "N") else d
        # WC y lavabo; regadera en baños completos
        if n != "Medio baño" and lon >= 1.9:
            x0, y0, a, b = _caja(dx, c, lb, 0.9, 0.9, despl=(lon / 2 - 0.55))
            dx.linea((x0, y0), (x0 + a, y0 + b), L); dx.linea((x0, y0 + b), (x0 + a, y0), L)
            dx.circulo((x0 + a / 2, y0 + b / 2), 0.05, L)
        _wc(dx, c, lb, -lon / 2 + 0.45 if lon > 1.6 else 0.0)
        if lon >= 1.6:
            x0, y0, a, b = _caja(dx, c, lb, 0.6, 0.45, despl=(0.15 if n != "Medio baño" else lon / 2 - 0.45) if lon > 2 else 0.35)
            dx.circulo((x0 + a / 2, y0 + b / 2), 0.14, L)
    elif n == "Lavandería" and corto >= 1.2:
        x0, y0, a, b = _caja(dx, c, lado, 0.7, 0.7, despl=-0.45)
        dx.circulo((x0 + a / 2, y0 + b / 2), 0.28, L)
        _caja(dx, c, lado, 0.7, 0.6, despl=0.45)
    elif n.startswith("Cochera"):
        n_aut = 2 if "doble" in n else 1
        for k in range(n_aut):
            off = (k - (n_aut - 1) / 2) * (w / n_aut)
            ax, ay = c["x"] + w / 2 + off - 0.9, c["y"] + 0.5
            dx.polilinea([(ax + 0.2, ay), (ax + 1.6, ay), (ax + 1.8, ay + 0.3), (ax + 1.8, ay + 4.2), (ax + 1.6, ay + 4.5),
                          (ax + 0.2, ay + 4.5), (ax, ay + 4.2), (ax, ay + 0.3)], L, True)
            dx.rect(ax + 0.2, ay + 1.3, 1.4, 1.9, L)
    elif n in ("Despacho", "Estudio") and corto >= 2.0:
        x0, y0, a, b = _caja(dx, c, lado, 1.4, 0.7)
        _caja(dx, c, lado, 0.5, 0.5, sep=0.95)
    elif n == "Vestidor":
        for l_ in [l for l in ("S", "N", "O", "E") if l not in _aberturas(c, vv)][:2]:
            lon = (w if l_ in ("S", "N") else d) - 0.3
            if lon > 0.8:
                x1, y1, a1, b1 = _caja(dx, c, l_, lon, 0.6, sep=0.0)
                dx.linea((x1, y1), (x1 + a1, y1 + b1), L)
    elif n == "Bodega":
        lon = (w if lado in ("S", "N") else d) - 0.3
        x1, y1, a1, b1 = _caja(dx, c, lado, lon, 0.45, sep=0.0)
        dx.texto((x1 + a1 / 2, y1 + b1 / 2), "ANAQUEL", 0.1, L, centrado=True)


def _libre_puertas(c, lado, vanos, fondo):
    """Tramo (u0, u1) a lo largo del muro `lado`, medido desde x (S/N) o y (O/E), que no invade el
    abatimiento de las puertas de los muros contiguos dentro de la franja de `fondo` junto a ese muro."""
    x, y, w, d = c["x"], c["y"], c["w"], c["d"]
    L_ = w if lado in ("S", "N") else d
    u0, u1 = 0.0, L_
    for v in vanos or ():
        if v["tipo"] not in ("puerta", "puerta_ext") or v.get("corrediza"):
            continue
        g = v["b"] - v["a"]                                  # radio del abatimiento = ancho de la hoja
        if lado in ("O", "E") and v["eje"] == "h":
            if abs(v["c"] - y) < EPS or abs(v["c"] - (y + d)) < EPS:
                fx0, fx1 = (x, x + fondo + 0.1) if lado == "O" else (x + w - fondo - 0.1, x + w)
                if v["a"] < fx1 and v["b"] > fx0:
                    if abs(v["c"] - y) < EPS:
                        u0 = max(u0, g + 0.05)
                    else:
                        u1 = min(u1, d - g - 0.05)
        elif lado in ("S", "N") and v["eje"] == "v":
            if abs(v["c"] - x) < EPS or abs(v["c"] - (x + w)) < EPS:
                fy0, fy1 = (y, y + fondo + 0.1) if lado == "S" else (y + d - fondo - 0.1, y + d)
                if v["a"] < fy1 and v["b"] > fy0:
                    if abs(v["c"] - x) < EPS:
                        u0 = max(u0, g + 0.05)
                    else:
                        u1 = min(u1, w - g - 0.05)
    return u0, u1


def _sala(dx, c, lado, vanos=None):
    L = "A-MUEBLES"
    w, d = c["w"], c["d"]
    lon = (w if lado in ("S", "N") else d)
    # el sofá no debe quedar dentro del abatimiento de puertas en los muros contiguos (p. ej. el baño que
    # abre a la estancia familiar): se acomoda en el tramo libre y se acorta si hace falta
    u0, u1 = _libre_puertas(c, lado, vanos, 0.9 + 0.08)
    sof = min(2.2, lon - 0.6, u1 - u0 - 0.1)
    if sof < 1.4:
        return
    despl = (u0 + u1) / 2 - lon / 2
    x0, y0, a, b = _caja(dx, c, lado, sof, 0.9, despl=despl)
    # mesa de centro
    cx, cy = x0 + a / 2, y0 + b / 2
    off = 1.35
    if lado == "S":
        cy += off
    elif lado == "N":
        cy -= off
    elif lado == "O":
        cx += off
    else:
        cx -= off
    dx.rect(cx - 0.5, cy - 0.3, 1.0, 0.6, L) if lado in ("S", "N") else dx.rect(cx - 0.3, cy - 0.5, 0.6, 1.0, L)


def _comedor(dx, c):
    L = "A-MUEBLES"
    w, d = c["w"], c["d"]
    larg = w >= d
    mw, md = (1.6, 0.9) if larg else (0.9, 1.6)
    if min(w, d) < 2.3:
        mw, md = (1.2, 0.8) if larg else (0.8, 1.2)
    cx, cy = c["x"] + w / 2, c["y"] + d / 2
    dx.rect(cx - mw / 2, cy - md / 2, mw, md, L)
    n = 3 if max(mw, md) >= 1.5 else 2
    for k in range(n):
        t = (k + 0.5) / n
        if larg:
            px = cx - mw / 2 + mw * t
            dx.rect(px - 0.2, cy + md / 2 + 0.05, 0.4, 0.4, L); dx.rect(px - 0.2, cy - md / 2 - 0.45, 0.4, 0.4, L)
        else:
            py = cy - md / 2 + md * t
            dx.rect(cx + mw / 2 + 0.05, py - 0.2, 0.4, 0.4, L); dx.rect(cx - mw / 2 - 0.45, py - 0.2, 0.4, 0.4, L)


def _wc(dx, c, lado, despl):
    L = "A-MUEBLES"
    x0, y0, a, b = _caja(dx, c, lado, 0.42, 0.7, despl=despl)
    # tanque + taza
    if lado in ("S", "N"):
        ty = y0 if lado == "S" else y0 + b - 0.2
        dx.rect(x0, ty, a, 0.2, L)
        cyy = y0 + 0.45 if lado == "S" else y0 + b - 0.45
        dx.circulo((x0 + a / 2, cyy), 0.19, L)
    else:
        tx = x0 if lado == "O" else x0 + a - 0.2
        dx.rect(tx, y0, 0.2, b, L)
        cxx = x0 + 0.45 if lado == "O" else x0 + a - 0.45
        dx.circulo((cxx, y0 + b / 2), 0.19, L)


# ------------------------------------------------------------------ azotea
def alero(corr):
    """Vuelo del alero de cubiertas inclinadas (igual en A-04, A-05 y renders)."""
    return 0.9 if "alero_amplio" in corr.get("rasgos", ()) else 0.6


def cubierta_inclinada(dx, blq, corr, r_est, n_baj, gas_xy, ox, oy, sur_primero):
    """Planta de azotea con cubierta inclinada sobre la losa: faldones, cumbrera, limatesas, pendientes,
    canalón perimetral y bajadas; el tanque de gas va en el patio (no sobre la cubierta)."""
    from .. import instalaciones as INS
    x, y, w, d = blq["x"] + ox, blq["y"] + oy, blq["w"], blq["d"]
    cub, cl = corr["cubierta"], blq["cubierta_ligera"]
    al = alero(corr)
    rr = planos.altura_cubierta(blq, corr)
    X0, Y0, X1, Y1 = x - al, y - al, x + w + al, y + d + al
    W, D = X1 - X0, Y1 - Y0
    dx.rect(X0, Y0, W, D, "A-MUROS")                                  # borde del alero / canalón
    dx.rect(x, y, w, d, "A-HATCH")                                    # paramento de muros (oculto)
    flechas = []
    if cub.startswith("cuatro"):
        span = min(w, d) / 2
        if W >= D:
            a, b = (X0 + D / 2, Y0 + D / 2), (X1 - D / 2, Y0 + D / 2)
            flechas = [((a[0] + b[0]) / 2, a[1], 0, -1), ((a[0] + b[0]) / 2, a[1], 0, 1), (a[0], a[1], -1, 0), (b[0], b[1], 1, 0)]
        else:
            a, b = (X0 + W / 2, Y0 + W / 2), (X0 + W / 2, Y1 - W / 2)
            flechas = [(a[0], (a[1] + b[1]) / 2, -1, 0), (a[0], (a[1] + b[1]) / 2, 1, 0), (a[0], a[1], 0, -1), (b[0], b[1], 0, 1)]
        dx.linea(a, b, "A-MUROS")
        for p_, esq in ((a, (X0, Y0)), (a, (X1, Y0) if W < D else (X0, Y1)), (b, (X1, Y1)), (b, (X0, Y1) if W < D else (X1, Y0))):
            dx.linea(p_, esq, "A-MUROS")
        dx.texto(((a[0] + b[0]) / 2 - (0.25 if W < D else 0), (a[1] + b[1]) / 2 + (0 if W < D else 0.25)), "CUMBRERA", 0.13,
                 "A-TEXTO", rot=90 if W < D else 0, centrado=True)
    elif cub.startswith("dos"):
        span = min(w, d) / 2
        if w >= d:
            dx.linea((X0, (Y0 + Y1) / 2), (X1, (Y0 + Y1) / 2), "A-MUROS")
            flechas = [((X0 + X1) / 2, (Y0 + Y1) / 2, 0, -1), ((X0 + X1) / 2, (Y0 + Y1) / 2, 0, 1)]
        else:
            dx.linea(((X0 + X1) / 2, Y0), ((X0 + X1) / 2, Y1), "A-MUROS")
            flechas = [((X0 + X1) / 2, (Y0 + Y1) / 2, -1, 0), ((X0 + X1) / 2, (Y0 + Y1) / 2, 1, 0)]
    else:
        span = min(w, d)
        flechas = [((X0 + X1) / 2, (Y0 + Y1) / 2, 0, -1)]
    pend = rr / span * 100 if span else 0
    for (px, py, ux, uy) in flechas:
        L_ = 1.8
        p0 = (px + ux * 1.0, py + uy * 1.0)
        p1 = (px + ux * (1.0 + L_), py + uy * (1.0 + L_))
        dx.linea(p0, p1, "A-MUROS")
        for s_ in (-1, 1):
            dx.linea(p1, (p1[0] - ux * 0.3 - uy * s_ * 0.15, p1[1] - uy * 0.3 + ux * s_ * 0.15), "A-MUROS")
        # texto junto a la flecha, sin encimarse con la cumbrera ni con las otras flechas
        mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
        if uy:
            dx.texto((mx + 0.25, my), f"PEND. {pend:.0f} %", 0.15, "A-TEXTO", rot=90, centrado=True)
        else:
            dx.texto((mx, my + 0.25), f"PEND. {pend:.0f} %", 0.15, "A-TEXTO", centrado=True)
    for p in INS.puntos_bap(blq, n_baj, ox, oy, sur_primero):
        dx.circulo(p, 0.12, "A-MUROS")
        dx.texto((p[0] + 0.2, p[1] - 0.35 if p[1] > y + d / 2 else p[1] + 0.25), "BAP Ø100", 0.15, "A-TEXTO")
    if gas_xy:
        gx, gy = gas_xy[0] + ox, gas_xy[1] + oy
        dx.circulo((gx, gy), 0.55, "A-MUROS")
        dx.texto((min(gx, X1 - 2.6), gy + 0.75), "TANQUE ESTACIONARIO GAS LP EN PATIO (NPT ±0.00)", 0.14, "A-TEXTO", centrado=True)
    mat = cl["material"].upper()
    notas = [f"CUBIERTA {cub.replace('_', ' ').upper()} DE {mat}, PENDIENTE {pend:.0f} %, SOBRE TRIPLAY 16 mm, FIELTRO ASFÁLTICO 30 lb",
             "Y ARMADURA LIGERA DE PTR GALVANIZADO ANCLADA A LA LOSA DE AZOTEA (CÁMARA VENTILADA BAJO LA CUBIERTA)",
             f"ALERO DE {al:.2f} m CON CANALÓN PERIMETRAL DE LÁMINA GALV. CAL. 24 A BAJADAS PLUVIALES Ø100",
             f"PESO DE CUBIERTA {cl['cm']} kg/m² INCLUIDO EN LA CARGA MUERTA DE AZOTEA (VER MEMORIA)",
             f"LOSA DE AZOTEA h = {r_est['losas'][-1]['h']} cm, PLANA, CON IMPERMEABILIZANTE APP 4 mm (VER PLANO E-02)"]
    for i, t in enumerate(notas):
        dx.texto((X1 + 1.6, Y1 - 0.4 - i * 0.32), t, 0.16, "A-TEXTO")


def azotea(dx, blq, lays, r_est, n_baj, gas_xy, ox=0.0, oy=0.0, pretil=0.6, sur_primero=False, corr=None):
    if corr is not None and blq.get("cubierta_ligera"):
        return cubierta_inclinada(dx, blq, corr, r_est, n_baj, gas_xy, ox, oy, sur_primero)
    x, y, w, d = blq["x"] + ox, blq["y"] + oy, blq["w"], blq["d"]
    dx.rect(x - 0.125, y - 0.125, w + 0.25, d + 0.25, "A-MUROS")
    dx.rect(x + 0.025, y + 0.025, w - 0.05, d - 0.05, "A-MUROS")
    # bajadas en esquinas y puntos medios del lado posterior (pendiente al norte y a los lados)
    from .. import instalaciones as INS
    pts = INS.puntos_bap(blq, n_baj, ox, oy, sur_primero)
    for p in pts:
        dx.circulo(p, 0.12, "A-MUROS")
        dx.texto((p[0] + 0.2, p[1] - 0.35 if p[1] > y + d / 2 else p[1] + 0.25), "BAP Ø100", 0.15, "A-TEXTO")
    # cumbreras de pendientes (divisorias) y flechas hacia las bajadas
    cx, cy = x + w / 2, y + d / 2
    for p in pts:
        dx.linea((cx, cy), p, "A-HATCH")
        mx, my = (cx + p[0]) / 2, (cy + p[1]) / 2
        ang = math.degrees(math.atan2(p[1] - cy, p[0] - cx))
        dx.texto((mx, my), "PEND. 2 %  →", 0.15, "A-TEXTO", rot=ang if -90 < ang < 90 else ang + 180)
    if gas_xy:
        gx, gy = gas_xy[0] + ox, gas_xy[1] + oy
        dx.circulo((gx, gy), 0.55, "A-MUROS")
        # etiqueta bajo el tanque para no encimarse con las bajadas pluviales de las esquinas
        dx.texto((min(gx, x + w - 1.9), gy - 0.85), "TANQUE ESTACIONARIO GAS LP", 0.15, "A-TEXTO", centrado=True)
    dx.rect(x + w * 0.1, y + d * 0.42, 2.0, 1.1, "A-MUEBLES")
    dx.texto((x + w * 0.1 + 1.0, y + d * 0.42 + 0.55), "CALENTADOR SOLAR (OPCIONAL)", 0.12, "A-TEXTO", centrado=True)
    notas = [f"PRETIL DE BLOCK h = {pretil:.2f} m CON DALA D-2 Y CHAFLÁN EN ENCUENTROS",
             "RELLENO PARA PENDIENTES (PROM. 10 cm), ENTORTADO 3 cm",
             "IMPERMEABILIZANTE PREFABRICADO APP 4 mm + RECUBRIMIENTO BLANCO REFLECTIVO",
             f"LOSA DE AZOTEA h = {r_est['losas'][-1]['h']} cm (VER PLANO E-02)"]
    for i, t in enumerate(notas):
        dx.texto((x + w + 2.2, y + d - 0.4 - i * 0.32), t, 0.16, "A-TEXTO")


# ------------------------------------------------------------------ fachadas
def _u(blq, lado, t):
    if lado == "S":
        return t - blq["x"]
    if lado == "N":
        return blq["x"] + blq["w"] - t
    if lado == "E":
        return t - blq["y"]
    return blq["y"] + blq["d"] - t


def fachada(dx, blq, lays, corr, r_est, lado, ox, oy, materiales):
    niveles = blq["niveles"]
    L = blq["w"] if lado in ("S", "N") else blq["d"]
    hs = [n["h"] for n in niveles]
    ztop = sum(hs)
    cub = corr["cubierta"]
    par = 0.6 if cub == "plana" else (1.1 if cub == "plana_pretil" else 0.0)
    F = "A-FACHADA"
    dx.linea((ox - 1.5, oy), (ox + L + 1.5, oy), F)
    dx.rect(ox, oy, L, ztop, F)
    if par:
        dx.rect(ox - 0.02, oy + ztop, L + 0.04, par, F)
    rr = planos.altura_cubierta(blq, corr)
    if rr > 0:
        ridge_x = blq["w"] >= blq["d"]
        gable = (lado in ("S", "N") and not ridge_x) or (lado in ("E", "O") and ridge_x)
        al = alero(corr)
        if cub == "curva":
            dx.polilinea([(ox - al + (L + 2 * al) * i / 20, oy + ztop + rr * 4 * (i / 20) * (1 - i / 20)) for i in range(21)], F)
        elif cub.startswith("una"):
            # una agua: baja al sur (y0) y sube al norte, igual que en los renders y en AP-03
            if lado in ("S", "N"):
                dx.polilinea([(ox - al, oy + ztop), (ox + L + al, oy + ztop), (ox + L + al, oy + ztop + rr),
                              (ox - al, oy + ztop + rr)], F, True)
                if lado == "S":
                    dx.linea((ox - al, oy + ztop + 0.15), (ox + L + al, oy + ztop + 0.15), F)
            elif lado == "E":
                dx.polilinea([(ox - al, oy + ztop), (ox + L + al, oy + ztop), (ox + L + al, oy + ztop + rr), (ox - al, oy + ztop + 0.15)], F, True)
            else:
                dx.polilinea([(ox - al, oy + ztop), (ox + L + al, oy + ztop), (ox + L + al, oy + ztop + 0.15), (ox - al, oy + ztop + rr)], F, True)
        elif cub == "inclinada_irregular":
            dx.polilinea([(ox - al, oy + ztop), (ox + L + al, oy + ztop), (ox + L + al, oy + ztop + rr), (ox - al, oy + ztop + 0.15)], F, True)
        elif gable:
            dx.polilinea([(ox - al, oy + ztop), (ox + L / 2, oy + ztop + rr), (ox + L + al, oy + ztop)], F, True)
        else:
            # cuatro aguas: faldones laterales en escorzo; dos aguas: hastiales verticales con su volado
            # (con k = 0 la vista lateral de un dos aguas parecía cuatro aguas)
            k = min(L / 2, rr * 1.5) if cub.startswith("cuatro") else -al
            dx.polilinea([(ox - al, oy + ztop), (ox + k, oy + ztop + rr), (ox + L - k, oy + ztop + rr), (ox + L + al, oy + ztop)], F, True)
    z = 0.0
    for k, n in enumerate(niveles):
        if k:
            dx.linea((ox, oy + z), (ox + L, oy + z), F)
        for v in lays[k][1]:
            if v.get("lado") != lado:
                continue
            a, b = sorted((_u(blq, lado, v["a"]), _u(blq, lado, v["b"])))
            h = n["h"]
            if v["tipo"] == "ventana":
                z1, z2 = (1.6, 2.2) if v.get("alta") else (0.9, min(h - 0.35, 2.35))
                if layout.es_cortina(corr, k, v):
                    z1 = layout.ANTEPECHO_CORTINA
            elif v["tipo"] == "porton":
                z1, z2 = 0.0, min(h - 0.35, 2.4)
            else:
                z1, z2 = 0.0, 2.1
            capa = "A-FACHADA-VIDRIO" if v["tipo"] in ("ventana", "puerta_ext") or v.get("vidrio") else F
            dx.rect(ox + a, oy + z + z1, b - a, z2 - z1, F)
            dx.rect(ox + a + 0.05, oy + z + z1 + 0.05, b - a - 0.1, z2 - z1 - 0.1, capa)
            if v["tipo"] == "ventana":
                nm = max(1, int((b - a) / 1.1))
                for i in range(1, nm):
                    xm = ox + a + (b - a) * i / nm
                    dx.linea((xm, oy + z + z1 + 0.05), (xm, oy + z + z2 - 0.05), capa)
                dx.rect(ox + a - 0.05, oy + z + z1 - 0.05, b - a + 0.1, 0.05, F)
            elif v["tipo"] == "porton" and not v.get("vidrio"):
                for i in range(1, 8):
                    zz = oy + z + z1 + (z2 - z1) * i / 8
                    dx.linea((ox + a + 0.05, zz), (ox + b - 0.05, zz), F)
            elif v["tipo"] == "puerta_ext":
                dx.linea((ox + (a + b) / 2, oy + z + 0.05), (ox + (a + b) / 2, oy + z + z2 - 0.05), capa)
        z += n["h"]
    # rasgos en fachada principal
    if lado == "S":
        if "volado" in corr["rasgos"]:
            dx.rect(ox - 0.3, oy + ztop - 0.35, L * 0.65 + 0.3, 0.35, F)
        pv = [(_u(blq, lado, v["a"]), _u(blq, lado, v["b"])) for k_ in range(len(niveles)) for v in lays[k_][1] if v.get("lado") == "S"]
        libres, cur = [], 0.0
        for a_, b_ in sorted((min(p), max(p)) for p in pv):
            if a_ - 0.3 > cur:
                libres.append((cur, a_ - 0.3))
            cur = max(cur, b_ + 0.3)
        libres.append((cur, L))
        a_, b_ = max(libres, key=lambda q: q[1] - q[0])
        if "muro_acento" in corr["rasgos"] and b_ - a_ > 0.9:
            for i in range(int(ztop / 0.3)):
                zz = oy + i * 0.3
                dx.linea((ox + a_, zz), (ox + b_, zz), "A-HATCH")
                off = 0.4 if i % 2 else 0.0
                xx = ox + a_ + off
                while xx < ox + b_:
                    dx.linea((xx, zz), (xx, zz + 0.3), "A-HATCH")
                    xx += 0.8
            dx.rect(ox + a_, oy, b_ - a_, ztop, F)
        pv0 = [(min(p), max(p)) for p in ((_u(blq, lado, v["a"]), _u(blq, lado, v["b"])) for v in lays[0][1] if v.get("lado") == "S")]
        lib0, cur = [], 0.0
        for a0_, b0_ in sorted(pv0):
            if a0_ - 0.3 > cur:
                lib0.append((cur, a0_ - 0.3))
            cur = max(cur, b0_ + 0.3)
        lib0.append((cur, L))
        ja, jb = max(lib0, key=lambda q: q[1] - q[0])
        if "jardinera" in corr["rasgos"] and jb - ja > 1.0:
            dx.rect(ox + ja + 0.1, oy, jb - ja - 0.2, 0.5, F)
        # parteluces y marco volumétrico: misma geometría que el render (render.py) para que plano y modelo coincidan
        zb1 = niveles[0]["h"] if len(niveles) > 1 else 0.3
        if "celosia" in corr["rasgos"] or "parteluces" in corr["rasgos"]:
            ancho = 0.08 if "celosia" in corr["rasgos"] else 0.15
            for k_ in range(int(L * 0.4 / 0.35)):
                dx.rect(ox + L * 0.55 + k_ * 0.35, oy + zb1, ancho, ztop - zb1, F)
        if "porche" in corr["rasgos"]:
            # porche cubierto sobre el acceso: misma geometría que render.py (postes, viga y cubierta a +2.55)
            pe = next((v for v in lays[0][1] if v["tipo"] == "puerta_ext" and v.get("lado") == "S"), None)
            if pe is not None:
                pa_ = max(0.0, _u(blq, lado, pe["a"]) - 0.6)
                pb_ = L if L - _u(blq, lado, pe["b"]) < L / 2 else min(L, _u(blq, lado, pe["b"]) + 3.0)
                dx.rect(ox + pa_, oy + 2.37, pb_ - pa_, 0.32, F)                 # viga de madera + cubierta
                for xx in (pa_, pb_ - 0.2):
                    dx.rect(ox + xx, oy, 0.2, 2.37, F)                           # postes de madera 20x20
                # rótulo bajo la viga, entre la puerta y el poste (sobre la viga se encimaba con la celosía);
                # el material de la cubierta va en las notas de materiales (antes decía teja siempre)
                db_ = max(_u(blq, lado, pe["a"]), _u(blq, lado, pe["b"]))
                xt = (db_ + pb_) / 2 if pb_ - db_ > 1.8 else (pa_ + pb_) / 2
                dx.texto((ox + xt, oy + 2.15), "PORCHE DE MADERA", 0.12, "A-TEXTO", centrado=True)
        if "pilotis" in corr["rasgos"] and len(niveles) > 1:
            # marquesina de concreto a nivel de entrepiso sobre pilotis (misma geometría que render y AP-03)
            P = layout.pilotis(blq, lays[0][1])
            e_, r_ = P["losa"], P["diam"] / 2
            dx.rect(ox, oy + zb1 - e_, L, e_, F)
            for cx in P["cols"]:
                u = _u(blq, lado, cx)
                dx.rect(ox + u - r_, oy, 2 * r_, zb1 - e_, F)
            dx.texto((ox + L / 2, oy + zb1 + 0.25),
                     f"MARQUESINA DE CONCRETO e = {e_ * 100:.0f} CM, VUELO {P['fondo']:.2f} M, SOBRE PILOTIS Ø{r_ * 200:.0f} CM",
                     0.12, "A-TEXTO", centrado=True)
        if "ventana_corrida" in corr["rasgos"] and len(niveles) > 1:
            zk = 0.0
            for k_, n_ in enumerate(niveles):
                if k_:
                    bc = layout.banda_corrida(lays[k_][1])
                    if bc:
                        a_, b_ = sorted((_u(blq, lado, bc[0]), _u(blq, lado, bc[1])))
                        z2_ = min(n_["h"] - 0.35, 2.35)
                        dx.rect(ox + a_ - 0.05, oy + zk + 0.85, b_ - a_ + 0.1, z2_ - 0.8, F)
                        dx.texto((ox + (a_ + b_) / 2, oy + zk + 0.6), "BANDA CORRIDA: CANCELERÍA Y PANELES DE ALUMINIO",
                                 0.11, "A-TEXTO", centrado=True)
                zk += n_["h"]
        if "marco" in corr["rasgos"] and len(niveles) > 1:
            fa, fb, e_ = layout.inicio_marco(lays[1][1], blq["x"], L), L + 0.05, 0.3
            dx.rect(ox + fa, oy + zb1 - 0.3, fb - fa, ztop - zb1 + 0.3, F)
            dx.rect(ox + fa + e_, oy + zb1, fb - fa - 2 * e_, ztop - zb1 - e_, F)
    # pérgola posterior: vigas vistas de testa en la fachada norte y de canto en las laterales
    # (misma geometría que render y Blender vía layout.pergola; antes ningún plano la dibujaba)
    if "pergola" in corr["rasgos"]:
        PG = layout.pergola(blq)
        zp, hv, pp = PG["z"], PG["viga"], PG["poste"]
        if lado == "N":
            for xv in PG["vigas"]:
                u = _u(blq, lado, xv + PG["ancho_viga"])
                dx.rect(ox + u, oy + zp, PG["ancho_viga"], hv, F)
            dx.linea((ox + _u(blq, lado, PG["x1"]), oy + zp), (ox + _u(blq, lado, PG["x0"]), oy + zp), F)
            for xx in PG["postes"]:
                dx.rect(ox + _u(blq, lado, xx + pp), oy, pp, zp, F)
            dx.texto((ox + L / 2, oy + zp + hv + 0.12), "PÉRGOLA DE MADERA TERMOTRATADA (VUELO 2.50 M)", 0.12,
                     "A-TEXTO", centrado=True)
        elif lado in ("E", "O"):
            ua, ub = sorted((_u(blq, lado, PG["y0"]), _u(blq, lado, PG["y1"])))
            dx.linea((ox + min(ua, -1.5), oy), (ox + max(ub, L + 1.5), oy), F)
            dx.rect(ox + ua, oy + zp, ub - ua, hv, F)
            up = sorted((_u(blq, lado, PG["y_poste"]), _u(blq, lado, PG["y_poste"] + pp)))
            dx.rect(ox + up[0], oy, pp, zp, F)
    # niveles
    zz = 0.0
    marcas = [(0.0, "NPT ±0.00")]
    for n in niveles[:-1]:
        zz += n["h"]
        marcas.append((zz, f"NPT +{zz:.2f}"))
    marcas.append((ztop, f"NLA +{ztop:.2f}"))
    if par:
        marcas.append((ztop + par, f"PRETIL +{ztop + par:.2f}"))
    # en la lateral oriente la pérgola vuela 2.50 m a la derecha: las marcas de nivel se recorren para no encimarse
    xn = L + (layout.PERGOLA_FONDO if lado == "E" and "pergola" in corr["rasgos"] else 0.0)
    for z_, t in marcas:
        dx.polilinea([(ox + xn + 0.4, oy + z_), (ox + xn + 0.65, oy + z_ + 0.2), (ox + xn + 0.15, oy + z_ + 0.2)], "A-NIVELES", True)
        dx.linea((ox + xn + 0.4, oy + z_), (ox + xn + 1.9, oy + z_), "A-NIVELES")
        dx.texto((ox + xn + 0.75, oy + z_ + 0.06), t, 0.15, "A-NIVELES")
    dx.cota((ox, oy), (ox + L, oy), -0.7, h=0.17)
    # materiales con líneas de llamada
    if lado == "S":
        # notas arriba de la cubierta (no sobre ella) y sin truncar: se parten en renglones
        import textwrap
        renglones = []
        for i, m in enumerate(materiales[:4]):
            for j, t_ in enumerate(textwrap.wrap(f"{i + 1}. {m.upper()}", 80)):
                renglones.append(t_ if j == 0 else "    " + t_)
        base = ztop + max(par or 0.0, rr if rr > 0 else 0.0) + 0.5
        for i, t_ in enumerate(reversed(renglones)):
            dx.texto((ox, oy + base + i * 0.26), t_, 0.14, "A-TEXTO")
    if lado in ("E", "O") and lado in set(blq.get("colindancias", [])):
        dx.texto((ox + L / 2, oy + niveles[0]["h"] / 2), "MURO DE COLINDANCIA: APLANADO DE MORTERO, SELLADOR E IMPERMEABILIZANTE", 0.17,
                 "A-TEXTO", centrado=True)
    nombre = {"S": "FACHADA PRINCIPAL (SUR)", "N": "FACHADA POSTERIOR (NORTE)", "E": "FACHADA LATERAL ORIENTE",
              "O": "FACHADA LATERAL PONIENTE"}[lado]
    dx.texto((ox + L / 2, oy - 1.4), nombre, 0.3, "T-TITULO", centrado=True)


# ------------------------------------------------------------------ cortes
def corte(dx, blq, lays, r_est, eje, pos, ox, oy, titulo, corr=None):
    """eje='x': plano x = pos (se ve el eje y en horizontal). eje='y': plano y = pos."""
    niveles = blq["niveles"]
    if eje == "x":
        a0, L = blq["y"], blq["d"]
        lin_eje = "h"
    else:
        a0, L = blq["x"], blq["w"]
        lin_eje = "v"
    C_ = "A-CORTE"
    zap = r_est["zapatas"][0]
    B, hz, Df = zap["B"] / 100, zap["h"] / 100, r_est["Df"]
    dx.linea((ox - 1.5, oy), (ox + L + 1.5, oy), C_)
    dx.texto((ox - 1.4, oy + 0.08), "NTN", 0.13, "A-NIVELES")
    # firme
    dx.rect(ox, oy - 0.10, L, 0.10, "A-HATCH")
    z = 0.0
    for k, n in enumerate(niveles):
        h = n["h"]
        losa = r_est["losas"][k]["h"] / 100
        lns = [l for l in r_est["estructurales"][k] if l["eje"] == lin_eje and l["a"] - EPS <= pos <= l["b"] + EPS]
        t_ = (r_est["t_x"] if lin_eje == "h" else r_est["t_y"]) / 100
        for l in lns:
            u = l["c"] - a0
            vano = next((v for v in lays[k][1] if v["eje"] == lin_eje and abs(v["c"] - l["c"]) < EPS and v["a"] <= pos <= v["b"]), None)
            if vano is None:
                dx.rect(ox + u - t_ / 2, oy + z, t_, h - losa, C_)
            else:
                if vano["tipo"] == "ventana":
                    z1, z2 = (1.6, 2.2) if vano.get("alta") else (0.9, min(h - 0.35, 2.35))
                    if corr and layout.es_cortina(corr, k, vano):
                        z1 = layout.ANTEPECHO_CORTINA
                    dx.rect(ox + u - t_ / 2, oy + z, t_, z1, C_)
                    dx.rect(ox + u - t_ / 2, oy + z + z2, t_, h - losa - z2, C_)
                    dx.linea((ox + u, oy + z + z1), (ox + u, oy + z + z2), "A-FACHADA-VIDRIO")
                else:
                    z2 = 2.1 if vano["tipo"] in ("puerta", "puerta_ext") else min(h - 0.35, 2.4)
                    if vano["tipo"] == "vano":
                        z2 = 2.3
                    dx.rect(ox + u - t_ / 2, oy + z + z2, t_, h - losa - z2, C_)
            if k == 0:   # cimentación bajo el muro
                dx.rect(ox + u - B / 2, oy - Df, B, hz, C_)
                dx.rect(ox + u - t_ / 2, oy - Df + hz, t_, Df - hz - 0.10, C_)
        # losa (con hueco de escalera en entrepisos)
        esc = next((c for c in lays[k][0] if c["t"] == "escalera" and not c["contenedor"]), None)
        huecos = []
        if esc and k < len(niveles) - 1:
            (pa, pb) = (esc["y"], esc["y"] + esc["d"]) if eje == "x" else (esc["x"], esc["x"] + esc["w"])
            inside = (esc["x"] <= pos <= esc["x"] + esc["w"]) if eje == "x" else (esc["y"] <= pos <= esc["y"] + esc["d"])
            if inside:
                huecos.append((pa - a0, pb - a0))
                # rampa de escalera dibujada como línea inclinada
                dx.linea((ox + pa - a0, oy + z), (ox + pb - a0 - 1.1, oy + z + h / 2), C_)
                dx.linea((ox + pb - a0 - 1.1, oy + z + h / 2), (ox + pb - a0, oy + z + h / 2), C_)
                dx.linea((ox + pb - a0, oy + z + h / 2), (ox + pa - a0 + 0.6, oy + z + h), C_)
        cur = -0.125
        for ha, hb in sorted(huecos) + [(L + 0.125, L + 0.125)]:
            if ha > cur:
                dx.rect(ox + cur, oy + z + h - losa, ha - cur, losa, C_)
            cur = max(cur, hb)
        # locales cortados
        for c in lays[k][0]:
            if c["contenedor"]:
                continue
            inside = (c["x"] <= pos <= c["x"] + c["w"]) if eje == "x" else (c["y"] <= pos <= c["y"] + c["d"])
            if not inside:
                continue
            (pa, pb) = (c["y"], c["y"] + c["d"]) if eje == "x" else (c["x"], c["x"] + c["w"])
            if pb - pa < 1.0:
                continue
            dx.texto((ox + (pa + pb) / 2 - a0, oy + z + h * 0.62), c["n"].upper(), min(0.2, (pb - pa) / 9), "A-TEXTO", centrado=True)
            if pb - pa > 1.8 and c["t"] != "escalera":
                dx.cota((ox + (pa + pb) / 2 - a0 + 0.35, oy + z), (ox + (pa + pb) / 2 - a0 + 0.35, oy + z + h - losa), 0.0, h=0.13)
        z += h
    cl = blq.get("cubierta_ligera")
    if cl:
        # cubierta inclinada sobre la losa de azotea (antes el corte dibujaba pretiles que no existen y no
        # mostraba la cubierta que sí aparece en A-04, A-05 y renders)
        tipo, al = cl["tipo"], cl["alero"]
        una = tipo.startswith("una") or tipo == "inclinada_irregular"
        rr = cl["pend"] * min(blq["w"], blq["d"]) / (1 if una else 2)
        ridge_x = blq["w"] >= blq["d"]
        perp = (eje == "x") == ridge_x                      # cumbrera perpendicular al plano de corte
        if una:
            if eje == "x":
                pts = [(-al, z), (L + al, z + rr)]
            else:
                zc = rr * (pos - blq["y"]) / blq["d"]
                pts = [(-al, z + zc), (L + al, z + zc)]
            dx.polilinea([(ox + a, oy + b) for a, b in pts], C_)
        elif perp:
            dx.polilinea([(ox - al, oy + z), (ox + L / 2, oy + z + rr), (ox + L + al, oy + z)], C_)
        else:
            if eje == "x":
                zc = rr * min(pos - blq["x"], blq["x"] + blq["w"] - pos) / (blq["w"] / 2)
            else:
                zc = rr * min(pos - blq["y"], blq["y"] + blq["d"] - pos) / (blq["d"] / 2)
            k = min(L / 2, rr * 1.5) if tipo.startswith("cuatro") else -al
            dx.polilinea([(ox - al, oy + z), (ox + k, oy + z + rr), (ox + L - k, oy + z + rr), (ox + L + al, oy + z)], C_)
            dx.rect(ox - al, oy + z + zc - 0.04, L + 2 * al, 0.08, C_)
        dx.texto((ox + L / 2, oy + z + rr + 0.25), f"CUBIERTA DE {cl['material'].upper()} SOBRE ARMADURA DE PTR "
                 f"(PEND. {cl['pend'] * 100:.0f} %)", 0.13, "A-TEXTO", centrado=True)
    else:
        # pretil
        dx.rect(ox - 0.125, oy + z, 0.15, 0.6, C_)
        dx.rect(ox + L - 0.025, oy + z, 0.15, 0.6, C_)
    P = blq.get("pilotis")
    om = 0.0
    if P and eje == "x" and len(niveles) > 1:
        # marquesina en voladizo al frente y pilotis en vista (misma geometría que fachadas y render)
        zb1, f, e_, r_ = niveles[0]["h"], P["fondo"], P["losa"], P["diam"] / 2
        dx.rect(ox - 0.125 - f, oy + zb1 - e_, f, e_, C_)
        dx.rect(ox - f + 0.05, oy, 2 * r_, zb1 - e_, "A-FACHADA")
        dx.rect(ox - f + 0.05 - 0.3, oy - Df, 2 * r_ + 0.6, 0.25, C_)            # zapata aislada del piloti
        om = f + 0.3                                                           # niveles a la izquierda de la marquesina
    for z_, t in [(0.0, "NPT ±0.00")] + [(sum(n["h"] for n in niveles[:i + 1]), f"N +{sum(n['h'] for n in niveles[:i + 1]):.2f}")
                                          for i in range(len(niveles))] + [(-Df, f"DESPLANTE -{Df:.2f}")]:
        dx.polilinea([(ox - om - 0.9, oy + z_), (ox - om - 0.65, oy + z_ + 0.2), (ox - om - 1.15, oy + z_ + 0.2)], "A-NIVELES", True)
        dx.texto((ox - om - 2.9, oy + z_ + 0.06), t, 0.14, "A-NIVELES")
    dx.texto((ox + L / 2, oy - Df - 0.9), titulo, 0.3, "T-TITULO", centrado=True)


# ------------------------------------------------------------------ cancelería y acabados
def claves_cancel(lays, niveles, corr, materiales):
    """Agrupa puertas y ventanas por tipo y medida: regresa (tipos, etiquetas por nivel)."""
    tipos = {}
    etiquetas = []
    mat_v = next((m for m in materiales if "cancel" in m.lower()), "Aluminio línea 3\" color negro, vidrio claro 6 mm")
    # puerta de acceso: la que describa el arquitecto en materiales (antes siempre decía parota, aunque el spec
    # pidiera otra madera o un acabado de color)
    mat_pa = next((m[0].upper() + m[1:] + ", chapa de seguridad" for m in materiales if "puerta de acceso" in m.lower()),
                  "Puerta de madera sólida de parota, chapa de seguridad")
    for k, (cu, va) in enumerate(lays):
        et = []
        for v in va:
            if v["tipo"] == "vano":
                continue
            ancho = round(v["b"] - v["a"], 2)
            if v["tipo"] == "ventana":
                cort = layout.es_cortina(corr, k, v)
                alto = 0.6 if v.get("alta") else (round(2.35 - layout.ANTEPECHO_CORTINA, 2) if cort else 1.45)
                key = ("V", ancho, alto)
                desc = "Ventana fija/corrediza" if not v.get("alta") else "Ventila de baño (abatible)"
                if cort:
                    desc = "Muro cortina fijo + corredizo"
                mat = mat_v
            elif v["tipo"] == "porton":
                alto = 2.4
                key = ("PT", ancho, alto)
                desc = "Portón seccional" if not v.get("vidrio") else "Cancel de vidrio templado"
                mat = "Portón seccional de lámina acanalada aislada, motor opcional"
            else:
                alto = 2.1
                ext = v["tipo"] == "puerta_ext"
                cor = bool(v.get("corrediza"))
                key = ("P", ancho, alto, ext, cor)
                desc = "Cancel corredizo al patio" if cor else ("Puerta de acceso doble" if ext else ("Puerta de baño" if ancho <= 0.8 else "Puerta interior"))
                mat = mat_v if cor else (mat_pa if ext else "Puerta de tambor MDF 6 mm, marco de pino, chapa de paso")
            if key not in tipos:
                pref = key[0]
                n = sum(1 for kk in tipos if kk[0] == pref) + 1
                tipos[key] = dict(clave=f"{pref}-{n}", desc=desc, ancho=ancho, alto=alto, mat=mat, cant=0)
            tipos[key]["cant"] += 1
            et.append((v, tipos[key]["clave"]))
        etiquetas.append(et)
    return list(tipos.values()), etiquetas


def etiquetar(dx, et, ox, oy):
    for v, clave in et:
        m = (v["a"] + v["b"]) / 2
        if v["eje"] == "h":
            p = (m + ox, v["c"] + oy + (0.45 if v.get("lado") != "N" else -0.45))
        else:
            p = (v["c"] + ox + (0.45 if v.get("lado") != "E" else -0.45), m + oy)
        if clave.startswith("V"):
            dx.polilinea([(p[0] - 0.28, p[1]), (p[0] - 0.14, p[1] + 0.2), (p[0] + 0.14, p[1] + 0.2), (p[0] + 0.28, p[1]),
                          (p[0] + 0.14, p[1] - 0.2), (p[0] - 0.14, p[1] - 0.2)], "A-CANCEL", True)
        else:
            dx.circulo(p, 0.24, "A-CANCEL")
        dx.texto(p, clave, 0.12, "A-CANCEL", centrado=True)


def acabados(c, materiales):
    t, n = c["t"], c["n"]
    # primero el porcelanato; "piso" sólo como respaldo (un "muro cortina de piso a cerramiento" no es un acabado de piso)
    piso_g = next((m for m in materiales if "porcelanato" in m.lower()),
                  next((m for m in materiales if m.lower().startswith("piso")), "Porcelanato 60x120 tono arena"))
    piso_g = piso_g if len(piso_g) < 60 else "Porcelanato 60x120 rectificado"
    piso_g = piso_g[:1].upper() + piso_g[1:]   # la cédula de acabados empieza con mayúscula
    # zoclo del mismo material que el piso (antes era siempre porcelanato aunque el piso fuera de barro o madera)
    zoclo_g = "Porcelanato 10 cm" if "porcelanato" in piso_g.lower() else "Zoclo de 10 cm del mismo material del piso"
    if t == "humedo" and "MEDIO" in n.upper():
        return dict(piso="Porcelanato antiderrapante 60x60", zoclo="—", muro="Azulejo 30x60 a 1.20 m en muro de lavabo; resto pintura esmalte",
                    plafon="Aplanado de yeso + pintura antihongos", clave="B")
    if t == "humedo":
        return dict(piso="Porcelanato antiderrapante 60x60", zoclo="—", muro="Azulejo 30x60 a 2.10 m en regadera y lavabo; resto pintura esmalte",
                    plafon="Aplanado de yeso + pintura antihongos", clave="B")
    if t == "cocina":
        return dict(piso=piso_g, zoclo=zoclo_g, muro="Salpicadero de azulejo 60 cm sobre cubierta; resto pintura vinílica lavable",
                    plafon="Aplanado de yeso + pintura vinílica", clave="C")
    if t == "servicio":
        return dict(piso="Cerámico antiderrapante 45x45", zoclo="Cerámico 10 cm", muro="Azulejo a 1.20 m; resto pintura esmalte",
                    plafon="Aplanado de yeso + pintura", clave="S")
    if t == "ext" and "Cochera" in n:
        return dict(piso="Concreto f'c 200 escobillado, juntas a 3 m", zoclo="—", muro="Aplanado de mortero + pintura vinílica",
                    plafon="Aplanado de mortero + pintura", clave="E")
    if t == "escalera":
        return dict(piso="Huella y peralte de porcelanato con nariz antiderrapante", zoclo="Porcelanato 10 cm",
                    muro="Aplanado fino + pintura vinílica; barandal de herrería h = 0.90 m", plafon="Aplanado de yeso + pintura", clave="ES")
    if t == "almacen":
        return dict(piso="Concreto pulido", zoclo="—", muro="Aplanado de mortero + pintura vinílica", plafon="Aplanado + pintura", clave="A")
    return dict(piso=piso_g, zoclo=zoclo_g, muro="Aplanado fino de yeso + pintura vinílica mate",
                plafon="Aplanado de yeso a regla + pintura vinílica", clave="H")
