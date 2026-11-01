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
    "humedo": ["privado", "circ", "social", "servicio", "cocina"],
    "privado": ["circ", "escalera", "social", "privado"],
    "almacen": ["cocina", "circ", "servicio", "privado", "grande", "social"],
    "default": ["circ", "social", "grande", "cocina", "servicio", "privado"],
}
VENTANA_T = {"social", "privado", "cocina", "grande", "humedo"}
ANCHO_PUERTA = {"humedo": 0.8, "almacen": 0.8, "privado": 0.9, "escalera": 1.2, "grande": 2.0,
                "tecnico": 1.0, "servicio": 0.9, "social": 0.9, "cocina": 0.9}


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
    for i, r in enumerate(hojas):
        if r["t"] in ("circ", "ext"):
            continue
        pri = PRIORIDAD.get(r["t"], PRIORIDAD["default"])
        mejor, rank = None, 99
        for j, o in enumerate(hojas):
            if i == j or o["unidad"] != r["unidad"]:
                continue
            seg = vecinos(r, o)
            if not seg:
                continue
            k = pri.index(o["t"]) if o["t"] in pri else (len(pri) + (0 if o["t"] == "escalera" else 3))
            if r["t"] == "escalera" and o["t"] == "escalera":
                k = 0
            if k < rank:
                mejor, rank = seg, k
        if mejor and not (r["t"] == "escalera" and rank > 2 and piso_idx > 0):
            vanos.append(_puerta(mejor, ANCHO_PUERTA.get(r["t"], 0.9) * (2 if big and r["t"] == "humedo" else 1), r))
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
    # vanos al exterior
    col = set(blq.get("colindancias", []))
    for r in hojas:
        ext = [e for e in bordes_ext(r, blq) if e[0] not in col]
        if r["t"] == "ext":
            frente = [e for e in ext if e[0] == "S"] or ext
            if frente:
                lado, eje, c, i, f = frente[0]
                L = f - i
                ancho = min(L - 0.4, 3.0 if "Cochera" in r["n"] and L < 6 else L * 0.8)
                a = (i + f - ancho) / 2
                vanos.append(dict(tipo="porton", eje=eje, c=c, a=round(a, 3), b=round(a + ancho, 3),
                                  lado=lado, cuarto=r["n"], vidrio=("Local" in r["n"] or "Tienda" in r["n"]
                                                                    or "Terraza" in r["n"])))
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
    if not any(v["tipo"] in ("porton", "puerta_ext") and v.get("lado") == "S" for v in vanos):
        frente = [r for r in hojas if abs(r["y"] - blq["y"]) < EPS and r["t"] in ("circ", "social", "grande")]
        if frente:
            r = max(frente, key=lambda q: q["w"])
            cx = r["x"] + r["w"] / 2
            vanos = [v for v in vanos if not (v["eje"] == "h" and abs(v["c"] - blq["y"]) < EPS
                                               and v["a"] < cx + 1 and v["b"] > cx - 1)]
            vanos.append(dict(tipo="puerta_ext", eje="h", c=blq["y"], a=round(cx - 1.0, 3), b=round(cx + 1.0, 3),
                              lado="S", cuarto=r["n"], cx=cx, cy=r["y"] + r["d"] / 2))
    for c in cuartos:
        c["area"] = round(c["w"] * c["d"], 2)
    return cuartos, vanos
