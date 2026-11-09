"""Dibujo de plantas arquitectónicas, fachadas, cortes, conjunto y láminas."""
import math
from . import layout
from .dxf import DXF, ROJO, AMARILLO, VERDE, CIAN, AZUL, MAGENTA, BLANCO, GRIS, GRIS_CLARO, NARANJA

TI, TE = 0.075, 0.125          # medio muro interior / exterior


def capas_arq(dx):
    dx.capa("A-MUROS", BLANCO); dx.capa("A-VANOS", CIAN); dx.capa("A-PUERTAS", AMARILLO)
    dx.capa("A-TEXTO", VERDE); dx.capa("COTAS", GRIS); dx.capa("A-ESCALERA", MAGENTA)
    dx.capa("A-EXTERIOR", 82); dx.capa("A-LIMITE", ROJO, "DASHED"); dx.capa("A-FACHADA", BLANCO)
    dx.capa("A-FACHADA-VIDRIO", CIAN); dx.capa("A-CORTE", BLANCO); dx.capa("LAMINA", GRIS_CLARO)
    dx.capa("A-AREA", 252)


def _huecos(vanos, eje, c, a, b, tol=0.02):
    hs = []
    for v in vanos:
        if v["eje"] == eje and abs(v["c"] - c) < tol and v["b"] > a and v["a"] < b:
            hs.append((max(a, v["a"]), min(b, v["b"])))
    return sorted(hs)


def _linea_huecos(dx, eje, c_dib, a, b, hs, capa):
    cur = a
    for h0, h1 in hs + [(b, b)]:
        if h0 > cur + 1e-3:
            if eje == "h":
                dx.linea((cur, c_dib), (h0, c_dib), capa)
            else:
                dx.linea((c_dib, cur), (c_dib, h0), capa)
        cur = max(cur, h1)


def planta_arq(dx, blq, cuartos, vanos, ox=0.0, oy=0.0, texto=True, cotas=True, esp=(0.15, 0.15)):
    """Dibuja una planta. ox, oy: desplazamiento para acomodar varias plantas en la lámina."""
    T = lambda p: (p[0] + ox, p[1] + oy)
    vv = [dict(v, c=v["c"] + (oy if v["eje"] == "h" else ox),
               a=v["a"] + (ox if v["eje"] == "h" else oy), b=v["b"] + (ox if v["eje"] == "h" else oy)) for v in vanos]
    escala_txt = max(0.18, min(1.2, max(blq["w"], blq["d"]) / 90))
    for c in cuartos:
        if c["contenedor"] and c["t"] != "unidad":
            continue
        x, y, w, d = c["x"] + ox, c["y"] + oy, c["w"], c["d"]
        ih = esp[0] / 2 if not c["contenedor"] else TI * 0.4      # muros en X (bordes horizontales)
        iv = esp[1] / 2 if not c["contenedor"] else TI * 0.4      # muros en Y (bordes verticales)
        capa = "A-MUROS"
        _linea_huecos(dx, "h", y + ih, x + iv, x + w - iv, _huecos(vv, "h", y, x, x + w), capa)
        _linea_huecos(dx, "h", y + d - ih, x + iv, x + w - iv, _huecos(vv, "h", y + d, x, x + w), capa)
        _linea_huecos(dx, "v", x + iv, y + ih, y + d - ih, _huecos(vv, "v", x, y, y + d), capa)
        _linea_huecos(dx, "v", x + w - iv, y + ih, y + d - ih, _huecos(vv, "v", x + w, y, y + d), capa)
        if c["contenedor"]:
            continue
        if texto:
            h = max(0.12, min(escala_txt * 1.4, min(w, d) / 7))
            dx.texto((x + w / 2, y + d / 2 + h * 0.3), c["n"].upper(), h, "A-TEXTO", centrado=True)
            dx.texto((x + w / 2, y + d / 2 - h * 1.0), f"{w * d:.1f} m2", h * 0.75, "A-AREA", centrado=True)
        if c["t"] == "escalera":
            _escalera(dx, c, ox, oy)
    # perímetro exterior
    bx, by, bw, bd = blq["x"] + ox, blq["y"] + oy, blq["w"], blq["d"]
    _linea_huecos(dx, "h", by - TE, bx - TE, bx + bw + TE, _huecos(vv, "h", by, bx, bx + bw), "A-MUROS")
    _linea_huecos(dx, "h", by + bd + TE, bx - TE, bx + bw + TE, _huecos(vv, "h", by + bd, bx, bx + bw), "A-MUROS")
    _linea_huecos(dx, "v", bx - TE, by - TE, by + bd + TE, _huecos(vv, "v", bx, by, by + bd), "A-MUROS")
    _linea_huecos(dx, "v", bx + bw + TE, by - TE, by + bd + TE, _huecos(vv, "v", bx + bw, by, by + bd), "A-MUROS")
    for v in vv:
        _vano(dx, v)
    P = blq.get("pilotis")
    if P and cuartos and cuartos[0].get("piso", 0) == 0:
        # marquesina sobre pilotis: proyección punteada y columnas circulares (antes no aparecía en planta)
        f, r_ = P["fondo"], P["diam"] / 2
        for (p0, p1) in (((P["x0"], blq["y"] - f), (P["x1"], blq["y"] - f)), ((P["x0"], blq["y"]), (P["x0"], blq["y"] - f)),
                         ((P["x1"], blq["y"]), (P["x1"], blq["y"] - f))):
            L_ = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
            n_ = max(1, int(L_ / 0.45))
            for i in range(n_):
                t0, t1 = i / n_, min(1.0, (i + 0.65) / n_)
                dx.linea((p0[0] + (p1[0] - p0[0]) * t0 + ox, p0[1] + (p1[1] - p0[1]) * t0 + oy),
                         (p0[0] + (p1[0] - p0[0]) * t1 + ox, p0[1] + (p1[1] - p0[1]) * t1 + oy), "COTAS")
        yc = blq["y"] - f + r_ + 0.05
        for cx in P["cols"]:
            dx.circulo((cx + ox, yc + oy), r_, "A-MUROS")
        if texto:
            dx.texto(((P["x0"] + P["x1"]) / 2 + ox, blq["y"] - f - 0.35 + oy), "MARQUESINA SOBRE PILOTIS (PROYECCIÓN)",
                     max(0.12, escala_txt * 0.6), "A-AREA", centrado=True)
    if cotas:
        dx.cota((bx - TE, by - TE), (bx + bw + TE, by - TE), -1.2 - escala_txt)
        dx.cota((bx - TE, by - TE), (bx - TE, by + bd + TE), 1.2 + escala_txt)


def _jambas(dx, v, t=0.13):
    for p in (v["a"], v["b"]):
        if v["eje"] == "h":
            dx.linea((p, v["c"] - t), (p, v["c"] + t), "A-MUROS")
        else:
            dx.linea((v["c"] - t, p), (v["c"] + t, p), "A-MUROS")


def _vano(dx, v):
    if v["tipo"] != "vano":
        _jambas(dx, v)
    a, b, c = v["a"], v["b"], v["c"]
    if v["tipo"] == "ventana":
        for off in (-0.03, 0.03):
            if v["eje"] == "h":
                dx.linea((a, c + off), (b, c + off), "A-VANOS")
            else:
                dx.linea((c + off, a), (c + off, b), "A-VANOS")
    elif v["tipo"] == "vano":
        pass
    elif v["tipo"] == "porton":
        if v["eje"] == "h":
            dx.linea((a, c), (b, c), "A-VANOS")
        else:
            dx.linea((c, a), (c, b), "A-VANOS")
    elif v["tipo"] == "puerta_ext" and v.get("corrediza"):
        # cancel corredizo: dos hojas de vidrio traslapadas, sin abatimiento
        m = (a + b) / 2
        for (p0, p1, off) in ((a, m + 0.05, -0.04), (m - 0.05, b, 0.04)):
            if v["eje"] == "h":
                dx.linea((p0, c + off), (p1, c + off), "A-VANOS")
            else:
                dx.linea((c + off, p0), (c + off, p1), "A-VANOS")
    elif v["tipo"] in ("puerta", "puerta_ext"):
        hojas = [(a, b)] if v["tipo"] == "puerta" else [(a, (a + b) / 2), (b, (a + b) / 2)]
        for h, e in hojas:
            wd = abs(e - h)
            dirx = 1 if e > h else -1
            if v["eje"] == "h":
                s = 1 if v.get("cy", c + 1) - c + (0.0001) > 0 else -1
                if v["tipo"] == "puerta_ext":
                    s = 1
                dx.linea((h, c), (h, c + s * wd), "A-PUERTAS")
                _arc90(dx, (h, c), wd, 90 if s > 0 else 270, 0 if dirx > 0 else 180)
            else:
                s = 1 if v.get("cx", c + 1) - c > 0 else -1
                dx.linea((c, h), (c + s * wd, h), "A-PUERTAS")
                _arc90(dx, (c, h), wd, 0 if s > 0 else 180, 90 if dirx > 0 else 270)


def _arc90(dx, cen, r, g0, g1):
    a0, a1 = sorted((g0, g1))
    if a1 - a0 > 180:
        a0, a1 = a1, a0 + 360
    dx.arco(cen, r, a0, a1, "A-PUERTAS")


def _escalera(dx, c, ox, oy):
    x, y, w, d = c["x"] + ox, c["y"] + oy, c["w"], c["d"]
    if "Elevador" in c["n"]:
        n = max(1, int(w // 2.2)) if w >= d else max(1, int(d // 2.2))
        for k in range(n):
            if w >= d:
                cx0, cx1, cy0, cy1 = x + w * k / n + 0.2, x + w * (k + 1) / n - 0.2, y + 0.3, y + min(d, 2.4) - 0.2
            else:
                cx0, cx1, cy0, cy1 = x + 0.3, x + min(w, 2.4) - 0.2, y + d * k / n + 0.2, y + d * (k + 1) / n - 0.2
            dx.rect(cx0, cy0, cx1 - cx0, cy1 - cy0, "A-ESCALERA")
            dx.linea((cx0, cy0), (cx1, cy1), "A-ESCALERA"); dx.linea((cx0, cy1), (cx1, cy0), "A-ESCALERA")
        return
    # escalera en "U": dos tramos a lo largo del lado mayor, descanso al fondo
    larg = w >= d
    L, A = (w, d) if larg else (d, w)
    huella = 0.28
    desc = max(1.0, A / 2)
    run = L - desc - 0.1
    n = int(run / huella)
    ini = 0.05

    def P(a, b):
        """a: avance a lo largo del tramo, b: posición transversal."""
        return (x + a, y + b) if larg else (x + b, y + a)
    dx.linea(P(ini, A / 2), P(ini + run, A / 2), "A-ESCALERA")              # muro intermedio
    dx.linea(P(ini + run, 0.05), P(ini + run, A - 0.05), "A-ESCALERA")      # borde del descanso
    for k in range(1, n + 1):
        p = ini + k * huella
        if p >= ini + run:
            break
        dx.linea(P(p, 0.05), P(p, A / 2 - 0.05), "A-ESCALERA")
        dx.linea(P(p, A / 2 + 0.05), P(p, A - 0.05), "A-ESCALERA")
    # flecha de recorrido
    q1, q2 = A * 0.25, A * 0.75
    ruta = [P(ini + 0.3, q1), P(ini + run + desc / 2, q1), P(ini + run + desc / 2, q2), P(ini + 0.5, q2)]
    dx.polilinea(ruta, "A-ESCALERA")
    fin = ruta[-1]
    t = 0.18
    if larg:
        dx.polilinea([(fin[0] + t, fin[1] + t * 0.6), fin, (fin[0] + t, fin[1] - t * 0.6)], "A-ESCALERA")
    else:
        dx.polilinea([(fin[0] - t * 0.6, fin[1] + t), fin, (fin[0] + t * 0.6, fin[1] + t)], "A-ESCALERA")
    dx.circulo(ruta[0], 0.07, "A-ESCALERA")
    sube = c.get("piso", 0) == 0
    ultimo = c.get("ultimo", False)
    etq = "SUBE" if sube else ("BAJA" if ultimo else "SUBE / BAJA")
    pt = P(ini + 0.15, q1 + 0.15)
    dx.texto(pt, etq, 0.14, "A-ESCALERA")
    if not sube:   # línea de corte de la planta superior
        dx.linea(P(ini + run * 0.45, 0.05), P(ini + run * 0.6, A / 2 - 0.05), "A-ESCALERA")


def exteriores(dx, proy, ox=0.0, oy=0.0):
    t = proy["terreno"]
    F, Fo = t["frente"], t["fondo"]
    th = max(0.22, F / 75)
    dx.rect(ox, oy, F, Fo, "A-LIMITE")
    # banqueta 2.0 m y arroyo de calle
    dx.linea((ox - 3, oy - 2.0), (ox + F + 3, oy - 2.0), "A-EXTERIOR")
    dx.linea((ox - 3, oy - 2.15), (ox + F + 3, oy - 2.15), "A-EXTERIOR")
    dx.texto((ox + F * 0.02, oy - 1.2), "BANQUETA", th * 0.8, "A-TEXTO")
    dx.texto((ox + F / 2, oy - 4.5), "C A L L E", th * 1.3, "A-TEXTO", centrado=True)
    dx.cota((ox, oy - 6.5), (ox + F, oy - 6.5), -0.1)
    dx.cota((ox + F, oy), (ox + F, oy + Fo), -(3.0 + th * 4))
    # colindancias
    if F < 40:
        for xx, rot in ((ox - th * 1.6, 90), (ox + F + th * 2.4, 90)):
            dx.texto((xx, oy + Fo * 0.62), "COLINDANCIA", th * 0.8, "A-TEXTO", rot=rot)
    dx.texto((ox + F / 2, oy + Fo + th * 1.6), "COLINDANCIA", th * 0.8, "A-TEXTO", centrado=True)
    # restricciones del bloque principal
    bl = max(proy["bloques"], key=lambda b: b["w"] * b["d"])
    if bl["y"] > 0.3:
        dx.cota((ox + bl["x"] + bl["w"] * 0.85, oy), (ox + bl["x"] + bl["w"] * 0.85, oy + bl["y"]), 0.6)
    post = Fo - (bl["y"] + bl["d"])
    if post > 0.3:
        dx.cota((ox + bl["x"] + bl["w"] * 0.85, oy + bl["y"] + bl["d"]), (ox + bl["x"] + bl["w"] * 0.85, oy + Fo), 0.6)
    if bl["x"] > 0.5:
        dx.cota((ox, oy + bl["y"] + bl["d"] * 0.5), (ox + bl["x"], oy + bl["y"] + bl["d"] * 0.5), 0.6)
    for e in proy["exteriores"]:
        x, y, w, d, r = e["x"] + ox, e["y"] + oy, e["w"], e["d"], e.get("r", 0)
        tp = e["tipo"]
        lx, ly, cen = x + 0.4, y + 0.4, False
        if tp in ("alberca", "espejo_agua"):
            dx.rect(x, y, w, d, "A-EXTERIOR"); dx.rect(x + 0.3, y + 0.3, w - 0.6, d - 0.6, "A-EXTERIOR")
            lx, ly, cen = x + w / 2, y + d / 2, True
        elif tp == "estacionamiento":
            dx.rect(x, y, w, d, "A-EXTERIOR")
            _cajones(dx, x, y, w, d)
            lx, ly = x + 0.6, y + d - th * 1.6
        elif tp == "rio":
            dx.circulo((x, y), r, "A-EXTERIOR"); dx.circulo((x, y), r - 6, "A-EXTERIOR")
            lx, ly, cen = x, y, True
        elif tp in ("rueda", "carrusel"):
            dx.circulo((x, y), r, "A-EXTERIOR"); dx.circulo((x, y), 1.0, "A-EXTERIOR")
            lx, ly, cen = x, y - r - th * 2, True
        elif tp == "montaña_rusa":
            pts = [(x + w / 2 + w / 2 * math.cos(a) * (1 + 0.25 * math.sin(3 * a)),
                    y + d / 2 + d / 2 * math.sin(a)) for a in [i * 2 * math.pi / 60 for i in range(60)]]
            dx.polilinea(pts, "A-EXTERIOR", True)
            lx, ly, cen = x + w / 2, y + d / 2, True
        elif tp == "palapas":
            for i in range(3):
                for j in range(3):
                    dx.circulo((x + w * (i + .5) / 3, y + d * (j + .5) / 3), 2.0, "A-EXTERIOR")
        elif tp == "cancha":
            dx.rect(x, y, w, d, "A-EXTERIOR"); dx.linea((x + w / 2, y), (x + w / 2, y + d), "A-EXTERIOR")
            dx.circulo((x + w / 2, y + d / 2), min(w, d) / 6, "A-EXTERIOR")
        elif tp == "acceso":
            dx.rect(x, y, w, d, "A-EXTERIOR")
            lx, ly = x + 0.4, y + d * 0.35
        elif tp == "area_verde" and any(o["tipo"] != "area_verde" and o["x"] >= e["x"] and o["y"] >= e["y"] for o in proy["exteriores"]):
            dx.rect(x, y, w, d, "A-EXTERIOR")
            lx, ly = x + 0.4, y + d - th * 1.6
        else:
            dx.rect(x, y, w, d, "A-EXTERIOR")
            lx, ly = x + 0.4, y + d - th * 1.6
        dx.texto((lx, ly), e.get("nombre", tp).upper(), th, "A-TEXTO", centrado=cen)


def cuadro_areas(dx, x, y, filas, h):
    """Tabla de áreas dibujada con texto y líneas."""
    ancho = h * 26
    dx.texto((x, y + h * 0.6), "CUADRO DE ÁREAS", h * 1.1, "A-TEXTO")
    yy = y - h * 0.4
    for i, (a, b) in enumerate(filas):
        dx.linea((x, yy), (x + ancho, yy), "COTAS")
        dx.texto((x + h * 0.3, yy - h * 1.25), a, h * 0.85, "A-TEXTO")
        dx.texto((x + ancho * 0.72, yy - h * 1.25), b, h * 0.85, "A-TEXTO")
        yy -= h * 1.9
    dx.linea((x, yy), (x + ancho, yy), "COTAS")
    dx.linea((x, y - h * 0.4), (x, yy), "COTAS"); dx.linea((x + ancho, y - h * 0.4), (x + ancho, yy), "COTAS")
    dx.linea((x + ancho * 0.7, y - h * 0.4), (x + ancho * 0.7, yy), "COTAS")


def _cajones(dx, x, y, w, d):
    """Cajones de 2.50 x 5.00 m en baterías a 90° con pasillo de 6.0 m."""
    cajon, fondo, pas = 2.5, 5.0, 6.0
    fila, yy = 0, y + 0.5
    while yy + fondo <= y + d - 0.5:
        n = int((w - 1.0) // cajon)
        for k in range(n + 1):
            xx = x + 0.5 + k * cajon
            dx.linea((xx, yy), (xx, yy + fondo), "A-EXTERIOR")
        dx.linea((x + 0.5, yy + (fondo if fila % 2 == 0 else 0)), (x + 0.5 + n * cajon, yy + (fondo if fila % 2 == 0 else 0)), "A-EXTERIOR")
        yy += fondo + (pas if fila % 2 == 0 else 0)
        fila += 1


def contar_cajones(w, d):
    n = int((w - 1.0) // 2.5)
    filas, yy, f = 0, 0.5, 0
    while yy + 5.0 <= d - 0.5:
        filas += 1
        yy += 5.0 + (6.0 if f % 2 == 0 else 0)
        f += 1
    return n * filas


def cuadro(dx, x0, y0, x1, y1, datos):
    """Marco de lámina, cuadro de datos y norte."""
    m = max(1.0, (x1 - x0) / 60)
    ancho = x1 - x0 + 2 * m
    W = max(2.2, ancho * 0.42)
    h = W / 44
    H = h * 11.5
    X0, X1 = x0 - m, x1 + m
    if ancho < W * 1.95:
        X1 = X0 + W * 1.95
    bx, by = X1 - W, y0 - m - H
    dx.rect(X0, y0 - m, X1 - X0, y1 - y0 + 2 * m, "LAMINA")
    dx.rect(X0, by, X1 - X0, H, "LAMINA")
    dx.linea((bx, by), (bx, by + H), "LAMINA")
    lineas = [("VÉRTICE  Ingeniería, Arquitectura y Proyectos", 1.3), (datos["proyecto"], 1.05), (datos["plano"], 1.05),
              (f"Clave: {datos['clave']}   Fecha: {datos['fecha']}   Unidades: metros", 0.72),
              (datos.get("leyenda", "Anteproyecto generado automáticamente — sin validez para construcción"), 0.72),
              ("Para revisión de: Ing. Miguel Estrada (DRO / Perito en edificación)", 0.72)]
    yy = by + H - h * 1.7
    for t, f in lineas:
        dx.texto((bx + h * 0.8, yy), t, h * f, "LAMINA")
        yy -= h * f * 1.75
    # norte y notas a la izquierda del cuadro
    r = H * 0.28
    nx, ny = X0 + r * 1.6, by + H / 2
    dx.circulo((nx, ny), r, "LAMINA")
    dx.polilinea([(nx, ny + r), (nx - r * 0.35, ny - r * 0.55), (nx, ny - r * 0.2), (nx + r * 0.35, ny - r * 0.55)], "LAMINA", True)
    dx.texto((nx, ny + r * 1.3), "N", r * 0.5, "LAMINA", centrado=True)
    disp = bx - (nx + r * 2)
    hn = min(h * 0.62, disp / 50) if disp > 0 else 0
    if hn > 0.02:
        yy = by + H - h * 1.7
        for t in datos.get("notas", [])[:6]:
            dx.texto((nx + r * 2, yy), t, hn, "LAMINA")
            yy -= hn * 1.9


# ------------------------------------------------------------ fachadas y corte
def altura_cubierta(blq, corr):
    cub = corr["cubierta"]
    span = min(blq["w"], blq["d"])
    pend = {"dos_aguas": 0.30, "cuatro_aguas": 0.30, "dos_aguas_pronunciada": 0.80, "una_agua": 0.12,
            "una_agua_baja": 0.08, "cuatro_aguas_baja": 0.18, "dos_aguas_baja": 0.18, "curva": 0.10,
            "inclinada_irregular": 0.15}.get(cub, 0)
    if blq["sistema"] == "acero" and pend == 0:
        pend = 0.05
    if blq["sistema"] == "acero":
        pend = min(pend, 0.10)
    r = pend * span / (1 if cub.startswith("una") or cub == "inclinada_irregular" else 2)
    return min(r, 8.0 if blq["sistema"] != "mamposteria" else 3.2)


def alturas(blq):
    zs, z = [], blq.get("z0", 0.0)
    for n in blq["niveles"]:
        for _ in range(n["rep"]):
            zs.append((z, n["h"], n))
            z += n["h"]
    return zs, z


def fachada(dx, proy, lays, corr, ox, oy, lado="S"):
    """Alzado ortogonal. lado S: eje horizontal = x. lado E: eje horizontal = y."""
    t = proy["terreno"]
    Lt = t["frente"] if lado == "S" else t["fondo"]
    dx.linea((ox - 2, oy), (ox + Lt + 2, oy), "A-FACHADA")
    orden = sorted(proy["bloques"], key=lambda b: -(b["y"] if lado == "S" else b["x"] + b["w"]))
    for blq in orden:
        a0 = blq["x"] if lado == "S" else blq["y"]
        L = blq["w"] if lado == "S" else blq["d"]
        zs, ztop = alturas(blq)
        z0 = blq.get("z0", 0.0)
        x0 = ox + a0
        dx.rect(x0, oy + z0, L, ztop - z0, "A-FACHADA")
        par = 0.0 if corr["cubierta"] not in ("plana", "plana_pretil") else (0.6 if corr["cubierta"] == "plana" else 1.1)
        if par:
            dx.rect(x0, oy + ztop, L, par, "A-FACHADA")
        r = altura_cubierta(blq, corr)
        cub = corr["cubierta"]
        if r > 0:
            ridge_x = blq["w"] >= blq["d"]
            frontal_gable = (lado == "S" and not ridge_x) or (lado == "E" and ridge_x)
            al = 0.6 if "alero" in " ".join(corr["rasgos"]) or cub.startswith("cuatro") else 0.3
            if cub == "curva":
                pts = [(x0 - al + (L + 2 * al) * i / 20, oy + ztop + r * 4 * (i / 20) * (1 - i / 20)) for i in range(21)]
                dx.polilinea(pts, "A-FACHADA")
            elif cub.startswith("una"):
                # Cubierta a una agua: baja al frente (sur, y0) y sube hacia el fondo (norte), como en los renders.
                if lado == "S":
                    dx.polilinea([(x0 - al, oy + ztop), (x0 + L + al, oy + ztop), (x0 + L + al, oy + ztop + r),
                                  (x0 - al, oy + ztop + r)], "A-FACHADA", True)
                    dx.linea((x0 - al, oy + ztop + 0.1), (x0 + L + al, oy + ztop + 0.1), "A-FACHADA")
                else:
                    dx.polilinea([(x0 - al, oy + ztop), (x0 + L + al, oy + ztop), (x0 + L + al, oy + ztop + r),
                                  (x0 - al, oy + ztop + 0.1)], "A-FACHADA", True)
            elif cub == "inclinada_irregular":
                dx.polilinea([(x0 - al, oy + ztop), (x0 + L + al, oy + ztop), (x0 + L + al, oy + ztop + r), (x0 - al, oy + ztop + r * 0.15)], "A-FACHADA", True)
            elif frontal_gable:
                dx.polilinea([(x0 - al, oy + ztop), (x0 + L / 2, oy + ztop + r), (x0 + L + al, oy + ztop)], "A-FACHADA", True)
            elif cub.startswith("cuatro"):
                dx.polilinea([(x0 - al, oy + ztop), (x0 + min(L / 2, r * 1.5), oy + ztop + r),
                              (x0 + L - min(L / 2, r * 1.5), oy + ztop + r), (x0 + L + al, oy + ztop)], "A-FACHADA", True)
            else:
                # dos aguas visto desde el alero: faldón entre el alero (ztop) y la cumbrera horizontal (ztop + r),
                # con los volados de los hastiales a ambos lados (antes se dibujaba como una sola agua)
                dx.polilinea([(x0 - al, oy + ztop), (x0 - al, oy + ztop + r), (x0 + L + al, oy + ztop + r),
                              (x0 + L + al, oy + ztop)], "A-FACHADA", True)
        # vanos del lado de la fachada
        bi = proy["bloques"].index(blq)
        nivel_vanos = {id(n): lays[bi][k][1] for k, n in enumerate(blq["niveles"])}
        for zb, h, n in zs:
            dx.linea((x0, oy + zb), (x0 + L, oy + zb), "A-FACHADA")
            for v in nivel_vanos[id(n)]:
                if v.get("lado") != lado:
                    continue
                a = (v["a"] if lado == "S" else v["a"]) + ox
                b = v["b"] + ox
                if v["tipo"] == "ventana":
                    z1, z2 = (1.6, 2.2) if v.get("alta") else (0.9 if h < 4 else 1.0, min(h - 0.3, 2.4 if h < 4 else h - 0.8))
                    if layout.es_cortina(corr, blq["niveles"].index(n), v):
                        z1, z2 = layout.ANTEPECHO_CORTINA, min(h - 0.35, 2.35)
                else:
                    z1, z2 = 0.0, min(h - 0.3, 2.4 if h < 3.2 else h - 0.9)
                capa = "A-FACHADA-VIDRIO" if v["tipo"] == "ventana" or v.get("vidrio") else "A-FACHADA"
                dx.rect(a, oy + zb + z1, b - a, z2 - z1, capa)
                if v["tipo"] == "porton" and not v.get("vidrio"):
                    for k in range(1, 6):
                        zz = zb + z1 + (z2 - z1) * k / 6
                        dx.linea((a, oy + zz), (b, oy + zz), "A-FACHADA")
        if lado == "E" and "pergola" in corr["rasgos"]:
            # pérgola posterior vista de canto (misma geometría que render y A-05 vía layout.pergola)
            PG = layout.pergola(blq)
            dx.rect(ox + PG["y0"], oy + z0 + PG["z"], PG["y1"] - PG["y0"], PG["viga"], "A-FACHADA")
            dx.rect(ox + PG["y_poste"], oy + z0, PG["poste"], PG["z"], "A-FACHADA")
        if lado == "S" and len(zs) > 1:
            # parteluces y marco con la geometría del render
            zb1 = zs[1][0] - z0
            if "celosia" in corr["rasgos"] or "parteluces" in corr["rasgos"]:
                for k in range(int(L * 0.4 / 0.35)):
                    dx.rect(x0 + L * 0.55 + k * 0.35, oy + z0 + zb1, 0.15, ztop - z0 - zb1, "A-FACHADA")
            # porche y jardinera: misma geometría que A-05 y render (antes AP-03 no los dibujaba)
            v0 = nivel_vanos[id(zs[0][2])]
            pe = next((v for v in v0 if v["tipo"] == "puerta_ext" and v.get("lado") == "S"), None)
            if "porche" in corr["rasgos"] and pe is not None:
                pa_ = max(0.0, pe["a"] - blq["x"] - 0.6)
                pb_ = L if L - (pe["b"] - blq["x"]) < L / 2 else min(L, pe["b"] - blq["x"] + 3.0)
                dx.rect(x0 + pa_, oy + z0 + 2.37, pb_ - pa_, 0.32, "A-FACHADA")
                for xx in (pa_, pb_ - 0.2):
                    dx.rect(x0 + xx, oy + z0, 0.2, 2.37, "A-FACHADA")
            if "jardinera" in corr["rasgos"]:
                libres, cur = [], 0.0
                for a_, b_ in sorted((v["a"] - blq["x"], v["b"] - blq["x"]) for v in v0 if v.get("lado") == "S"):
                    if a_ - 0.3 > cur:
                        libres.append((cur, a_ - 0.3))
                    cur = max(cur, b_ + 0.3)
                libres.append((cur, L))
                ja, jb = max(libres, key=lambda q: q[1] - q[0])
                if jb - ja > 1.0:
                    dx.rect(x0 + ja + 0.1, oy + z0, jb - ja - 0.2, 0.5, "A-FACHADA")
            if "pilotis" in corr["rasgos"]:
                # marquesina de concreto sobre pilotis: misma geometría que render, A-05 y Blender
                P = layout.pilotis(blq, v0)
                e_, r_ = P["losa"], P["diam"] / 2
                dx.rect(ox + P["x0"], oy + z0 + zb1 - e_, P["x1"] - P["x0"], e_, "A-FACHADA")
                for cx in P["cols"]:
                    dx.rect(ox + cx - r_, oy + z0, 2 * r_, zb1 - e_, "A-FACHADA")
            if "ventana_corrida" in corr["rasgos"]:
                for zb, h, n in zs[1:]:
                    bc = layout.banda_corrida(nivel_vanos[id(n)])
                    if bc:
                        dx.rect(ox + bc[0] - 0.05, oy + zb + 0.85, bc[1] - bc[0] + 0.1, min(h - 0.3, 2.4) - 0.8, "A-FACHADA")
            if "marco" in corr["rasgos"]:
                fa, fb = layout.inicio_marco(nivel_vanos[id(zs[1][2])], blq["x"], L), L + 0.05
                dx.rect(x0 + fa, oy + z0 + zb1 - 0.3, fb - fa, ztop - z0 - zb1 + 0.3, "A-FACHADA")
                dx.rect(x0 + fa + 0.3, oy + z0 + zb1, fb - fa - 0.6, ztop - z0 - zb1 - 0.3, "A-FACHADA")
        dx.texto((x0 + 0.3, oy + ztop + 0.3), f"NPT +{ztop:.2f}", max(0.2, L / 80), "COTAS")
    dx.texto((ox + Lt / 2, oy - max(1.5, Lt / 25)), f"FACHADA {'PRINCIPAL (SUR)' if lado == 'S' else 'LATERAL (ORIENTE)'}",
             max(0.35, Lt / 50), "A-TEXTO", centrado=True)


def corte(dx, proy, lays, corr, ox, oy):
    """Corte longitudinal por el eje medio del bloque principal (plano y-z)."""
    blq = max(proy["bloques"], key=lambda b: b["w"] * b["d"] * len(b["niveles"]))
    bi = proy["bloques"].index(blq)
    xm = blq["x"] + blq["w"] * 0.37
    zs, ztop = alturas(blq)
    y0, L = blq["y"], blq["d"]
    dx.linea((ox + y0 - 3, oy), (ox + y0 + L + 3, oy), "A-CORTE")
    losa = 0.12 if blq["sistema"] == "mamposteria" else 0.25
    for k, (zb, h, n) in enumerate(zs + [(ztop, 0, None)]):
        dx.rect(ox + y0 - TE, oy + zb - losa if zb > blq.get("z0", 0) else oy + zb - 0.1, L + 2 * TE, losa, "A-CORTE")
        dx.texto((ox + y0 + L + 1.0, oy + zb), f"N +{zb:.2f}", max(0.18, L / 90), "COTAS")
    # muros cortados en cada nivel distinto
    for k, n in enumerate(blq["niveles"]):
        cuartos = lays[bi][k][0]
        cortes = sorted({round(c["y"], 2) for c in cuartos if c["x"] <= xm <= c["x"] + c["w"] and not c["contenedor"]}
                        | {round(y0 + L, 2)})
        for zb, h, nn in zs:
            if nn is not n:
                continue
            for yy in cortes:
                dx.rect(ox + yy - 0.075, oy + zb, 0.15, h - losa, "A-CORTE")
            for c in cuartos:
                if c["x"] <= xm <= c["x"] + c["w"] and not c["contenedor"] and h > 2.2:
                    nom = c["n"].upper()
                    # tamaño limitado por el ancho del local en el corte para que los nombres no se encimen
                    tam = min(0.5, (c["d"] - 0.3) / (0.9 * max(len(nom), 1)))
                    dx.texto((ox + c["y"] + c["d"] / 2, oy + zb + h * 0.45), nom,
                             max(0.12, tam), "A-TEXTO", centrado=True)
    P = blq.get("pilotis")
    if P and len(zs) > 1:
        zb1, f, e_ = zs[1][0], P["fondo"], P["losa"]
        dx.rect(ox + y0 - TE - f, oy + zb1 - e_, f, e_, "A-CORTE")                      # marquesina en voladizo
        r_ = P["diam"] / 2
        dx.rect(ox + y0 - f + 0.05, oy + blq.get("z0", 0.0), 2 * r_, zb1 - e_, "A-FACHADA")   # pilotis (vista)
    if corr["cubierta"] in ("plana", "plana_pretil"):
        par = 0.6 if corr["cubierta"] == "plana" else 1.1
        for yy in (y0 - TE, y0 + L + TE - 0.15):
            dx.rect(ox + yy, oy + ztop, 0.15, par, "A-CORTE")                     # pretil (antes faltaba en el corte)
    r = altura_cubierta(blq, corr)
    if r:
        cub = corr["cubierta"]
        if cub.startswith("una") or cub == "inclinada_irregular":
            # una agua: sube del frente (y0) al fondo, igual que fachadas y renders
            dx.polilinea([(ox + y0 - 0.4, oy + ztop), (ox + y0 + L + 0.4, oy + ztop), (ox + y0 + L + 0.4, oy + ztop + r),
                          (ox + y0 - 0.4, oy + ztop + 0.1)], "A-CORTE", True)
        elif cub == "curva":
            dx.polilinea([(ox + y0 - 0.4 + (L + 0.8) * i / 20, oy + ztop + r * 4 * (i / 20) * (1 - i / 20)) for i in range(21)], "A-CORTE")
        elif blq["w"] >= blq["d"]:
            # cumbrera paralela a x: el corte (plano y-z) corta el hastial → triángulo
            dx.polilinea([(ox + y0 - 0.4, oy + ztop), (ox + y0 + L / 2, oy + ztop + r), (ox + y0 + L + 0.4, oy + ztop)], "A-CORTE")
        else:
            # cumbrera paralela al corte: faldón cortado a la altura que corresponde a xm y cumbrera vista detrás
            # (antes se dibujaba un hastial triangular que no coincidía con fachadas, azotea ni renders)
            zc = r * min(xm - blq["x"], blq["x"] + blq["w"] - xm) / (blq["w"] / 2)
            k = min(L / 2, r * 1.5) if cub.startswith("cuatro") else -0.4
            dx.polilinea([(ox + y0 - 0.4, oy + ztop), (ox + y0 + k, oy + ztop + r), (ox + y0 + L - k, oy + ztop + r),
                          (ox + y0 + L + 0.4, oy + ztop)], "A-CORTE")
            dx.rect(ox + y0 - 0.4, oy + ztop + zc - 0.05, L + 0.8, 0.1, "A-CORTE")
    dx.cota((ox + y0 - 1.5, oy), (ox + y0 - 1.5, oy + ztop), 1.0)
    dx.texto((ox + y0 + L / 2, oy - max(1.5, L / 25)), "CORTE LONGITUDINAL A-A'", max(0.35, L / 50), "A-TEXTO", centrado=True)
