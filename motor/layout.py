"""Distribución de espacios y vanos (puertas, ventanas, portones) por nivel."""

EPS = 1e-3


def _lay(rect, zonas, eje, inv, out, padre, unidad):
    x, y, w, d = rect
    zonas = list(reversed(zonas)) if inv else list(zonas)
    tz = sum(z["p"] for z in zonas) or 1
    off = 0.0
    for z in zonas:
        cuartos = z["cuartos"]
        tc = sum(c["p"] for c in cuartos) or 1
        if eje == "y":
            zh = d * z["p"] / tz
            zr = (x, y + off, w, zh)
            off += zh
        else:
            zw = w * z["p"] / tz
            zr = (x + off, y, zw, d)
            off += zw
        o2 = 0.0
        for c in cuartos:
            if eje == "y":
                cw = zr[2] * c["p"] / tc
                r = (zr[0] + o2, zr[1], cw, zr[3])
                o2 += cw
            else:
                ch = zr[3] * c["p"] / tc
                r = (zr[0], zr[1] + o2, zr[2], ch)
                o2 += ch
            r = tuple(round(v, 3) for v in r)
            if c.get("sub"):
                sub_eje = "y" if r[3] >= r[2] else "x"
                u = unidad
                if not c.get("grupo"):
                    u = len(out)
                    out.append(dict(n=c["n"], t=c["t"], x=r[0], y=r[1], w=r[2], d=r[3],
                                    contenedor=True, unidad=unidad))
                _lay(r, c["sub"], sub_eje, c.get("inv", False), out, c["n"] or padre, u)
            else:
                out.append(dict(n=c["n"], t=c["t"], x=r[0], y=r[1], w=r[2], d=r[3],
                                contenedor=False, unidad=unidad))


def _overlap(a0, a1, b0, b1):
    return max(a0, b0), min(a1, b1)


def vecinos(a, b):
    """Segmento compartido entre dos rectángulos: (eje, coord, ini, fin) o None."""
    # pared horizontal (y constante)
    for ya, yb in ((a["y"] + a["d"], b["y"]), (a["y"], b["y"] + b["d"])):
        if abs(ya - yb) < EPS:
            i, f = _overlap(a["x"], a["x"] + a["w"], b["x"], b["x"] + b["w"])
            if f - i > 0.85:
                return ("h", ya, i, f)
    for xa, xb in ((a["x"] + a["w"], b["x"]), (a["x"], b["x"] + b["w"])):
        if abs(xa - xb) < EPS:
            i, f = _overlap(a["y"], a["y"] + a["d"], b["y"], b["y"] + b["d"])
            if f - i > 0.85:
                return ("v", xa, i, f)
    return None


def bordes_ext(r, blq):
    """Bordes del cuarto que coinciden con el perímetro del bloque."""
    bx, by, bw, bd = blq["x"], blq["y"], blq["w"], blq["d"]
    out = []
    if abs(r["y"] - by) < EPS:
        out.append(("S", "h", by, r["x"], r["x"] + r["w"]))
    if abs(r["y"] + r["d"] - (by + bd)) < EPS:
        out.append(("N", "h", by + bd, r["x"], r["x"] + r["w"]))
    if abs(r["x"] - bx) < EPS:
        out.append(("O", "v", bx, r["y"], r["y"] + r["d"]))
    if abs(r["x"] + r["w"] - (bx + bw)) < EPS:
        out.append(("E", "v", bx + bw, r["y"], r["y"] + r["d"]))
    return out


PRIORIDAD = {
    "humedo": ["circ", "privado", "social", "servicio", "cocina"],
    "privado": ["circ", "escalera", "social", "privado"],
    "almacen": ["cocina", "circ", "servicio", "privado", "grande", "social"],
    "default": ["circ", "social", "grande", "cocina", "servicio", "privado"],
}
VENTANA_T = {"social", "privado", "cocina", "grande", "humedo"}
ANCHO_PUERTA = {"humedo": 0.8, "almacen": 0.8, "privado": 0.9, "escalera": 1.2, "grande": 2.0,
                "tecnico": 1.0, "servicio": 0.9, "social": 0.9, "cocina": 0.9}


def inicio_marco(vanos, bx, L, e=0.3, rel=0.38):
    """Arranque (local, desde el paño poniente de la fachada sur) del marco volumétrico de planta alta.
    Busca el macizo entre ventanas más cercano a rel·L donde quepa el poste (e) para que el marco
    no cruce una ventana; si no hay, regresa rel·L."""
    vs = sorted((v["a"] - bx, v["b"] - bx) for v in vanos if v.get("lado") == "S")
    huecos, cur = [], 0.0
    for a, b in vs:
        if a > cur:
            huecos.append((cur, a))
        cur = max(cur, b)
    huecos.append((cur, L))
    obj, mejor = rel * L, None
    for a, b in huecos:
        if b - a < e + 0.1 or a > 0.6 * L:
            continue
        f = min(max(obj, a + 0.05), b - e - 0.05)
        if mejor is None or abs(f - obj) < abs(mejor - obj):
            mejor = f
    return round(mejor, 3) if mejor is not None else obj


def _puerta(seg, ancho, cuarto, tipo="puerta"):
    eje, c, i, f = seg
    ancho = min(ancho, f - i - 0.2)
    if f - i > ancho + 1.2:
        a = i + 0.25
    else:
        a = (i + f - ancho) / 2
    return dict(tipo=tipo, eje=eje, c=round(c, 3), a=round(a, 3), b=round(a + ancho, 3),
                cuarto=cuarto["n"], cx=cuarto["x"] + cuarto["w"] / 2, cy=cuarto["y"] + cuarto["d"] / 2)


def distribuir(blq, nivel, corriente, piso_idx=0):
    cuartos = []
    _lay((blq["x"], blq["y"], blq["w"], blq["d"]), nivel["zonas"], "y", False, cuartos, "", None)
    hojas = [c for c in cuartos if not c["contenedor"]]
    vanos = []
    big = max(blq["w"], blq["d"]) > 40
    # puertas interiores
    habit = blq.get("uso") == "habitacional"
    ABIERTO = ("social", "cocina", "circ")
    for i, r in enumerate(hojas):
        if r["t"] in ("circ", "escalera") and "Elevador" not in r["n"]:
            continue
        if r["t"] == "ext" and "Cochera" not in r["n"]:
            continue
        pri = PRIORIDAD.get(r["t"], PRIORIDAD["default"])
        if r["t"] == "ext":
            pri = ["circ", "social", "servicio", "cocina"]
        if "Elevador" in r["n"]:
            pri = ["circ"]
        dependiente = "Vestidor" in r["n"] or ("principal" in r["n"] and r["t"] == "humedo")
        mejor, rank, obj = None, 99, None
        for j, o in enumerate(hojas):
            if i == j or o["unidad"] != r["unidad"] or o["t"] == "escalera":
                continue
            if o["t"] == "ext" and r["t"] != "grande":
                continue
            seg = vecinos(r, o)
            if not seg:
                continue
            k = pri.index(o["t"]) if o["t"] in pri else len(pri) + 3
            if dependiente and "principal" in o["n"] and o["t"] == "privado":
                k = -1
            if k < rank:
                mejor, rank, obj = seg, k, o
        if not mejor:
            continue
        if habit and r["t"] in ABIERTO and obj["t"] in ABIERTO:
            eje, c, i0, f0 = mejor
            ancho = min(f0 - i0 - 0.4, corriente.get("vano_max", 2.4) if "social" in (r["t"], obj["t"]) else 1.2)
            m = (i0 + f0) / 2
            vanos.append(dict(tipo="vano", eje=eje, c=round(c, 3), a=round(m - ancho / 2, 3), b=round(m + ancho / 2, 3),
                              cuarto=r["n"]))
        else:
            vanos.append(_puerta(mejor, ANCHO_PUERTA.get(r["t"], 0.9) * (2 if big and r["t"] == "humedo" else 1), r))
    # circulaciones contiguas se comunican (vestíbulo-pasillo, acceso-vestíbulo)
    for i, r in enumerate(hojas):
        if r["t"] != "circ":
            continue
        for j, o in enumerate(hojas):
            if j > i and o["t"] == "circ" and o["unidad"] == r["unidad"]:
                seg = vecinos(r, o)
                if seg:
                    eje, c, i0, f0 = seg
                    m = (i0 + f0) / 2; an = min(1.5, f0 - i0 - 0.3)
                    vanos.append(dict(tipo="vano" if habit else "puerta", eje=eje, c=round(c, 3), a=round(m - an / 2, 3),
                                      b=round(m + an / 2, 3), cuarto=r["n"], cx=r["x"] + r["w"] / 2, cy=r["y"] + r["d"] / 2))
    # cocina abierta al comedor en vivienda
    if habit:
        for r in hojas:
            if r["t"] != "cocina":
                continue
            for o in hojas:
                if o["t"] == "social" and o["unidad"] == r["unidad"]:
                    seg = vecinos(r, o)
                    if seg and not any(v["eje"] == seg[0] and abs(v["c"] - seg[1]) < EPS and v["b"] > seg[2] and v["a"] < seg[3] for v in vanos):
                        eje, c, i0, f0 = seg
                        m = (i0 + f0) / 2; an = min(corriente.get("vano_max", 2.4) * 0.75, f0 - i0 - 0.6)
                        vanos.append(dict(tipo="vano", eje=eje, c=round(c, 3), a=round(m - an / 2, 3), b=round(m + an / 2, 3), cuarto=r["n"]))
    # escaleras abiertas hacia la circulación (sin puerta)
    for r in hojas:
        if r["t"] != "escalera" or "Elevador" in r["n"]:
            continue
        # si la escalera colinda con una circulación, abre sólo a ella (no desemboca en recámaras ni estancias
        # cerradas, y evita un borde abierto sin barandal hacia un local habitable)
        tipos = ("circ", "social", "grande")
        if any(o is not r and o["unidad"] == r["unidad"] and o["t"] == "circ" and vecinos(r, o) for o in hojas):
            tipos = ("circ",)
        for o in hojas:
            if o is r or o["unidad"] != r["unidad"] or o["t"] not in tipos:
                continue
            seg = vecinos(r, o)
            if seg:
                eje, c, i0, f0 = seg
                vanos.append(dict(tipo="vano", eje=eje, c=round(c, 3), a=round(i0 + 0.15, 3), b=round(f0 - 0.15, 3),
                                  cuarto=r["n"]))
    # acceso a cada unidad (depto, habitación) desde la circulación común
    unidades = {c["unidad"] for c in hojas if c["unidad"] is not None}
    for u in unidades:
        mejores = []
        for r in hojas:
            if r["unidad"] != u:
                continue
            for o in hojas:
                if o["unidad"] is None and o["t"] in ("circ",):
                    seg = vecinos(r, o)
                    if seg:
                        pr = {"circ": 0, "social": 1, "privado": 2}.get(r["t"], 5)
                        mejores.append((pr, seg, r))
        if mejores:
            mejores.sort(key=lambda m: m[0])
            vanos.append(_puerta(mejores[0][1], 1.0, mejores[0][2]))
        else:   # unidad que abre directo al exterior (villas, cabañas)
            col_ = set(blq.get("colindancias", []))
            cand = []
            for r in hojas:
                if r["unidad"] != u:
                    continue
                for lado, eje, c, i0, f0 in bordes_ext(r, blq):
                    if lado not in col_ and f0 - i0 > 1.4:
                        pr = {"S": 0, "N": 1}.get(lado, 2) + {"privado": 0, "circ": 0, "social": 0}.get(r["t"], 3)
                        cand.append((pr, lado, eje, c, i0, f0, r))
            if cand:
                cand.sort(key=lambda t: t[0])
                _, lado, eje, c, i0, f0, r = cand[0]
                m = (i0 + f0) / 2
                vanos.append(dict(tipo="puerta_ext", eje=eje, c=c, a=round(m - 0.5, 3), b=round(m + 0.5, 3), lado=lado,
                                  cuarto=r["n"], cx=r["x"] + r["w"] / 2, cy=r["y"] + r["d"] / 2))
    # vanos al exterior
    col = set(blq.get("colindancias", []))
    # vivienda: la zona social de planta baja sale al patio posterior por un cancel corredizo (antes ninguna casa
    # tenía puerta al patio: el jardín y el tanque de gas quedaban sin acceso)
    import math as _m
    patio = piso_idx == 0 and blq.get("z0", 0) == 0 and blq.get("uso") == "habitacional" and len(blq["niveles"]) <= 3
    for r in hojas:
        ext = [e for e in bordes_ext(r, blq) if e[0] not in col]
        if r["t"] == "ext" and not any(e[0] == "S" for e in ext) and "Cochera" not in r["n"]:
            ops = [(vecinos(r, o), o) for o in hojas if o["t"] == "circ" and o["unidad"] == r["unidad"]]
            ops = [(sg, o) for sg, o in ops if sg]
            if ops:
                (eje, c, i0, f0), o = max(ops, key=lambda t: t[0][3] - t[0][2])
                an = (f0 - i0) * 0.8
                m = (i0 + f0) / 2
                vanos.append(dict(tipo="porton", eje=eje, c=c, a=round(m - an / 2, 3), b=round(m + an / 2, 3),
                                  lado=None, cuarto=r["n"], vidrio=True))
                continue
        if r["t"] == "ext":
            frente = [e for e in ext if e[0] == "S"] or ext
            if frente:
                lado, eje, c, i, f = frente[0]
                L = f - i
                vid = "Local" in r["n"] or "Tienda" in r["n"] or "Terraza" in r["n"]
                if "Cochera doble" in r["n"]:
                    # dos portones con columna central (apoyo de la trabe de carga)
                    m = (i + f) / 2
                    an = min(2.6, (L - 0.8) / 2)
                    for a, b in ((m - 0.2 - an, m - 0.2), (m + 0.2, m + 0.2 + an)):
                        vanos.append(dict(tipo="porton", eje=eje, c=c, a=round(a, 3), b=round(b, 3), lado=lado,
                                          cuarto=r["n"], vidrio=False))
                    continue
                ancho = min(L - 0.4, 3.0 if "Cochera" in r["n"] and L < 6 else L * 0.8)
                a = (i + f - ancho) / 2
                vanos.append(dict(tipo="porton", eje=eje, c=c, a=round(a, 3), b=round(a + ancho, 3),
                                  lado=lado, cuarto=r["n"], vidrio=vid))
            continue
        if r["t"] not in VENTANA_T and r["t"] != "circ":
            continue
        for lado, eje, c, i, f in ext:
            L = f - i
            if L < 1.0:
                continue
            if r["t"] == "humedo":
                ancho = min(0.8, L - 0.3)
            elif r["t"] == "circ":
                ancho = min(1.2, L * 0.3)
                if not ("Lobby" in r["n"] or "Vestíbulo" in r["n"] or "Acceso" in r["n"] or "Recepción" in r["n"]):
                    continue
                if lado == "S":
                    vanos.append(dict(tipo="puerta_ext", eje=eje, c=c, a=round((i + f) / 2 - 0.6, 3),
                                      b=round((i + f) / 2 + 0.6, 3), lado=lado, cuarto=r["n"],
                                      cx=r["x"] + r["w"] / 2, cy=r["y"] + r["d"] / 2))
                    continue
            else:
                ancho = max(0.8, min(L - 0.6, L * corriente["ventana"] * (1.25 if r["t"] == "social" else 1)))
                # iluminación natural mínima: 17.5 % del área del local (ventana de 1.45 m de alto)
                n_fach = sum(1 for e_ in ext if e_[4] - e_[3] >= 1.0)
                req = 0.175 * r["w"] * r["d"] / 1.45 / max(1, n_fach) + 0.05
                ancho = max(ancho, min(L - 0.6, req))
            if patio and r["t"] == "social" and lado == "N" and L >= 2.4:
                # ancho justo para el 17.5 % de iluminación con hoja de 2.10 m (mínimo 1.80 m): un cancel más ancho
                # quita longitud de muro en la dirección X, que suele ser la crítica por sismo en lotes angostos
                an = min(L - 0.6, max(1.8, _m.ceil((0.175 * r["w"] * r["d"] / 2.0 + 0.05) * 20) / 20))
                cen = (i + f) / 2
                vanos.append(dict(tipo="puerta_ext", eje=eje, c=c, a=round(cen - an / 2, 3), b=round(cen + an / 2, 3),
                                  lado=lado, cuarto=r["n"], vidrio=True, corrediza=True,
                                  cx=r["x"] + r["w"] / 2, cy=r["y"] + r["d"] / 2))
                patio = False
                continue
            # ventanas repartidas en claros grandes
            n = max(1, int(L // 9)) if L > 12 else 1
            paso = L / n
            for k in range(n):
                cen = i + paso * (k + 0.5)
                aw = min(ancho / n if n > 1 else ancho, paso - 0.6)
                vanos.append(dict(tipo="ventana", eje=eje, c=c, a=round(cen - aw / 2, 3),
                                  b=round(cen + aw / 2, 3), lado=lado, cuarto=r["n"],
                                  alta=r["t"] == "humedo"))
    # acceso principal al bloque si nada da al frente
    if piso_idx == 0 and blq.get("z0", 0) == 0 and not any(v["tipo"] in ("porton", "puerta_ext") and v.get("lado") == "S" for v in vanos):
        frente = [r for r in hojas if abs(r["y"] - blq["y"]) < EPS and r["t"] in ("circ", "social", "grande")]
        if not frente:
            frente = [r for r in hojas if abs(r["y"] - blq["y"]) < EPS and r["t"] not in ("tecnico", "almacen")]
        if frente:
            r = max(frente, key=lambda q: q["w"])
            cx = r["x"] + r["w"] / 2
            vanos = [v for v in vanos if not (v["eje"] == "h" and abs(v["c"] - blq["y"]) < EPS
                                               and v["a"] < cx + 1 and v["b"] > cx - 1)]
            vanos.append(dict(tipo="puerta_ext", eje="h", c=blq["y"], a=round(cx - 1.0, 3), b=round(cx + 1.0, 3),
                              lado="S", cuarto=r["n"], cx=cx, cy=r["y"] + r["d"] / 2))
    vanos += conectar(hojas, vanos, blq, piso_idx)
    for c in cuartos:
        c["area"] = round(c["w"] * c["d"], 2)
        c["piso"] = piso_idx
        c["ultimo"] = piso_idx == len(blq["niveles"]) - 1
    return cuartos, vanos


def _lados(r, v):
    """¿El vano v está sobre un borde del cuarto r?"""
    if v["eje"] == "h":
        on = abs(r["y"] - v["c"]) < EPS or abs(r["y"] + r["d"] - v["c"]) < EPS
        return on and v["a"] < r["x"] + r["w"] - 0.05 and v["b"] > r["x"] + 0.05
    on = abs(r["x"] - v["c"]) < EPS or abs(r["x"] + r["w"] - v["c"]) < EPS
    return on and v["a"] < r["y"] + r["d"] - 0.05 and v["b"] > r["y"] + 0.05


def grafo(hojas, vanos):
    n = len(hojas)
    ady = {i: set() for i in range(n)}
    entradas = set()
    for v in vanos:
        lados = [i for i, r in enumerate(hojas) if _lados(r, v)]
        if v["tipo"] in ("puerta_ext", "porton") or (v["tipo"] == "ventana" and False):
            entradas.update(lados)
        for i in lados:
            for j in lados:
                if i != j:
                    ady[i].add(j)
    return ady, entradas


def alcanzables(hojas, vanos, piso_idx):
    ady, entradas = grafo(hojas, vanos)
    inicio = set(entradas)
    if piso_idx > 0 or not inicio:
        inicio |= {i for i, r in enumerate(hojas) if r["t"] == "escalera"}
    vistos, pila = set(inicio), list(inicio)
    while pila:
        i = pila.pop()
        for j in ady[i]:
            if j not in vistos:
                vistos.add(j); pila.append(j)
    return vistos


def conectar(hojas, vanos, blq, piso_idx):
    """Garantiza que todo espacio tenga acceso desde la entrada / escalera.
    Elige siempre la mejor conexión disponible (circulación antes que escalera o habitación)."""
    nuevos = []
    for _ in range(len(hojas)):
        vis = alcanzables(hojas, vanos + nuevos, piso_idx)
        aislados = [i for i in range(len(hojas)) if i not in vis]
        if not aislados:
            break
        opciones = []
        for i in aislados:
            r = hojas[i]
            for j in vis:
                o = hojas[j]
                if r["unidad"] is not None and o["unidad"] != r["unidad"] and o["t"] != "circ":
                    continue
                seg = vecinos(r, o)
                if seg:
                    pr = {"circ": 0, "social": 2, "privado": 3, "escalera": 6, "ext": 5}.get(o["t"], 4)
                    pr += 3 if r["t"] == "escalera" else 0
                    opciones.append((pr, seg, r))
        if not opciones:
            break
        opciones.sort(key=lambda t: t[0])
        pv = _puerta(opciones[0][1], 0.9, opciones[0][2])
        pv["auto"] = True
        nuevos.append(pv)
    return nuevos


# ------------------------------------------------------------------ rasgos de fachada con geometría compartida
PILOTIS_FONDO = 1.20       # vuelo de la marquesina de concreto al frente (m)
PILOTIS_DIAM = 0.30        # columnas circulares de concreto aparente (m)
PILOTIS_LOSA = 0.15        # peralte de la marquesina (m)


def pilotis(blq, vanos_pb, sep_max=4.0):
    """Marquesina de concreto a nivel de entrepiso sobre pilotis, al frente (sur) del bloque.

    Devuelve dict(x0, x1, fondo, losa, cols=[x centro...]) en coordenadas absolutas. Las columnas van en los
    extremos y en los macizos de la fachada de planta baja (nunca frente a un portón o una puerta), a no más de
    `sep_max` entre ejes; antes el render dibujaba postes sueltos que no cargaban nada y los planos los omitían.
    """
    x0, x1 = blq["x"], blq["x"] + blq["w"]
    r = PILOTIS_DIAM / 2
    huecos = sorted((v["a"], v["b"]) for v in vanos_pb if v.get("lado") == "S")
    cand, cur = [], x0
    for a, b in huecos:
        if a - cur >= PILOTIS_DIAM + 0.1:
            cand.append((cur + a) / 2)
        cur = max(cur, b)
    cols = [x0 + r, x1 - r]
    for _ in range(12):
        cols.sort()
        gaps = [(cols[i + 1] - cols[i], i) for i in range(len(cols) - 1)]
        g, i = max(gaps)
        if g <= sep_max:
            break
        mid = (cols[i] + cols[i + 1]) / 2
        dentro = [c for c in cand if cols[i] + 0.8 < c < cols[i + 1] - 0.8]
        if not dentro:
            break
        cols.append(min(dentro, key=lambda c: abs(c - mid)))
    return dict(x0=x0, x1=x1, fondo=PILOTIS_FONDO, losa=PILOTIS_LOSA, diam=PILOTIS_DIAM,
                cols=[round(c, 3) for c in sorted(cols)])


# Pérgola posterior de madera: vigas de 8 x 18 cm @ 60 cm con su cara superior a +2.88 (desplantadas a +2.70) que
# vuelan 2.50 m desde la fachada norte, sobre dos postes de 20 x 20 cm. Una sola geometría para render, Blender,
# AP-03 y A-05 (antes sólo los renders la dibujaban y Blender usaba 2.60 m de vuelo).
PERGOLA_FONDO = 2.50
PERGOLA_Z = 2.70
PERGOLA_VIGA = 0.18
PERGOLA_SEP = 0.60
PERGOLA_POSTE = 0.20


def pergola(blq):
    """Geometría de la pérgola posterior en coordenadas absolutas (x a lo ancho, y hacia el fondo)."""
    x0, w, y1 = blq["x"], blq["w"], blq["y"] + blq["d"]
    return dict(x0=x0, x1=x0 + w, y0=y1, y1=y1 + PERGOLA_FONDO, z=PERGOLA_Z, viga=PERGOLA_VIGA, ancho_viga=0.08,
                vigas=[round(x0 + k * PERGOLA_SEP, 3) for k in range(int(w / PERGOLA_SEP))],
                postes=[round(x0 + 0.2, 3), round(x0 + w - 0.2 - PERGOLA_POSTE, 3)],
                y_poste=round(y1 + PERGOLA_FONDO - 0.3, 3), poste=PERGOLA_POSTE)


def altura_pretil(cubierta):
    """Altura del pretil sobre la losa de azotea según la cubierta de la corriente: una sola fuente para fachadas,
    cortes, azotea, render, Blender y presupuesto (antes A-06, A-03 y el presupuesto usaban 0.60 m mientras
    AP-03, A-05 y los renders dibujaban 1.10 m en azoteas con pretil alto, p. ej. Art Déco o colonial)."""
    return 0.6 if cubierta == "plana" else (1.1 if cubierta == "plana_pretil" else 0.0)


PARTELUZ_SEP = 0.35


def parteluces(blq, celosia=False):
    """Parteluces (o celosía) de la fachada principal en planta alta, en coordenadas absolutas: una sola geometría
    para render, AP-03, A-05 y Blender (antes Blender usaba otro arranque, separación, número y sección)."""
    x0, w = blq["x"], blq["w"]
    return dict(xs=[round(x0 + 0.55 * w + k * PARTELUZ_SEP, 3) for k in range(int(w * 0.4 / PARTELUZ_SEP))],
                ancho=0.08 if celosia else 0.15, y0=0.35, y1=0.10)     # y0/y1: distancia hacia la calle desde el paño


def banda_corrida(vanos_nivel):
    """Tramo (a, b) de la banda corrida de cancelería en la fachada sur de un nivel superior, o None."""
    vs = [(v["a"], v["b"]) for v in vanos_nivel if v["tipo"] == "ventana" and v.get("lado") == "S"]
    if len(vs) < 2:
        return None
    return min(a for a, _ in vs), max(b for _, b in vs)


# Muro cortina: en planta baja las ventanas de los locales habitables bajan su antepecho a un zoclo de 10 cm
# (cancel de piso a cerramiento) con el mismo cabezal de 2.35 m, de modo que cerramientos, castillos y cargas
# no cambian. En planta alta se conserva el antepecho de 0.90 m (protección contra caídas) y nunca aplica a
# cocina, lavandería, baños ni ventilas altas.
ANTEPECHO_CORTINA = 0.10
_SIN_CORTINA = ("COCINA", "LAVANDER", "BAÑO", "BODEGA", "COCHERA", "ESCALERA", "VESTIDOR")


def es_cortina(corr, piso_idx, v):
    return ("muro_cortina" in corr.get("rasgos", ()) and piso_idx == 0 and v.get("tipo") == "ventana"
            and not v.get("alta") and v.get("lado") and not any(s in str(v.get("cuarto", "")).upper() for s in _SIN_CORTINA))
