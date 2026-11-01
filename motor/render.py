"""Renders volumétricos 3D por código (matplotlib), con sombreado por orientación solar."""
import math
import random
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import to_rgb
from mpl_toolkits.mplot3d.art3d import Poly3DCollection, Line3DCollection

from .planos import altura_cubierta, alturas

SOL = np.array([0.55, -0.62, 0.78]); SOL = SOL / np.linalg.norm(SOL)


class Escena:
    def __init__(self):
        self.polys, self.cols, self.flat, self.lines, self.lcols = [], [], [], [], []

    def q(self, pts, color, brillo=None):
        p = np.array(pts, float)
        if len(p) < 3:
            return
        c = np.array(to_rgb(color), np.float32)
        if brillo is not None:
            c = np.clip(c * (0.75 + 0.35 * brillo), 0, 1)
        self.polys.append(p); self.cols.append(c); self.flat.append(brillo is not None)

    def caja(self, x, y, z, w, d, h, color, techo=None):
        X, Y, Z = x + w, y + d, z + h
        self.q([(x, y, z), (X, y, z), (X, y, Z), (x, y, Z)], color)
        self.q([(X, y, z), (X, Y, z), (X, Y, Z), (X, y, Z)], color)
        self.q([(X, Y, z), (x, Y, z), (x, Y, Z), (X, Y, Z)], color)
        self.q([(x, Y, z), (x, y, z), (x, y, Z), (x, Y, Z)], color)
        self.q([(x, y, Z), (X, y, Z), (X, Y, Z), (x, Y, Z)], techo or color)

    def l(self, a, b, color, w=0.6):
        self.lines.append([a, b]); self.lcols.append((color, w))


def _sombra(E, blq, ztop, color="#8F8A7E"):
    from math import atan2
    k = -SOL[:2] / SOL[2]
    x, y, w, d = blq["x"], blq["y"], blq["w"], blq["d"]
    z0 = blq.get("z0", 0.0)
    pts = []
    for zz in (z0, ztop):
        for px, py in ((x, y), (x + w, y), (x + w, y + d), (x, y + d)):
            pts.append((px + k[0] * zz, py + k[1] * zz))
    # envolvente convexa
    pts = sorted(set(pts))
    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, hi = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(hi) >= 2 and cross(hi[-2], hi[-1], p) <= 0:
            hi.pop()
        hi.append(p)
    hull = lo[:-1] + hi[:-1]
    E.q([(p[0], p[1], 0.045) for p in hull], color, 1.0)


def _cubierta(E, blq, corr, ztop):
    x, y, w, d = blq["x"], blq["y"], blq["w"], blq["d"]
    cub = corr["cubierta"]
    r = altura_cubierta(blq, corr)
    tc = corr["techo"]
    al = 0.9 if ("alero_amplio" in corr["rasgos"] or cub.endswith("baja")) else 0.4
    if blq["sistema"] == "acero" and cub in ("plana", "plana_pretil"):
        cub, r = "dos_aguas", 0.05 * min(w, d) / 2
    if cub in ("plana", "plana_pretil") or r <= 0:
        par = 0.6 if cub == "plana" else 1.1
        if blq["sistema"] == "mamposteria" and cub == "plana":
            par = 0.4
        for (a, b) in [((x, y), (x + w, y)), ((x + w, y), (x + w, y + d)), ((x + w, y + d), (x, y + d)), ((x, y + d), (x, y))]:
            E.q([(a[0], a[1], ztop), (b[0], b[1], ztop), (b[0], b[1], ztop + par), (a[0], a[1], ztop + par)], corr["muro"])
        E.q([(x + .2, y + .2, ztop + .05), (x + w - .2, y + .2, ztop + .05), (x + w - .2, y + d - .2, ztop + .05),
             (x + .2, y + d - .2, ztop + .05)], tc)
        return ztop + par
    X0, Y0, X1, Y1 = x - al, y - al, x + w + al, y + d + al
    ridge_x = w >= d
    if cub == "curva":
        n = 16
        for i in range(n):
            t0, t1 = i / n, (i + 1) / n
            z0 = ztop + r * 4 * t0 * (1 - t0) * 2; z1 = ztop + r * 4 * t1 * (1 - t1) * 2
            if ridge_x:
                ya, yb = Y0 + (Y1 - Y0) * t0, Y0 + (Y1 - Y0) * t1
                E.q([(X0, ya, z0), (X1, ya, z0), (X1, yb, z1), (X0, yb, z1)], tc)
            else:
                xa, xb = X0 + (X1 - X0) * t0, X0 + (X1 - X0) * t1
                E.q([(xa, Y0, z0), (xa, Y1, z0), (xb, Y1, z1), (xb, Y0, z1)], tc)
        return ztop + r * 2
    if cub.startswith("una") or cub == "inclinada_irregular":
        zf, zb = ztop + 0.1, ztop + r
        if cub == "inclinada_irregular":
            E.q([(X0, Y0, zf), (X1, Y0, zf + r * 0.6), (X1, Y1, zb + r * 0.3), (X0, Y1, zb)], tc)
        else:
            E.q([(X0, Y0, zf), (X1, Y0, zf), (X1, Y1, zb), (X0, Y1, zb)], tc)
        for xx in (x, x + w):
            E.q([(xx, y, ztop), (xx, y + d, ztop), (xx, y + d, ztop + r * (d / (Y1 - Y0))), (xx, y, ztop + 0.1)], corr["muro"])
        E.q([(x, y + d, ztop), (x + w, y + d, ztop), (x + w, y + d, zb - 0.2), (x, y + d, zb - 0.2)], corr["muro"])
        return zb
    zr = ztop + r
    if cub.startswith("cuatro"):
        if ridge_x:
            k = min(w / 2, d / 2)
            E.q([(X0, Y0, ztop), (X1, Y0, ztop), (x + w - k, y + d / 2, zr), (x + k, y + d / 2, zr)], tc)
            E.q([(X1, Y1, ztop), (X0, Y1, ztop), (x + k, y + d / 2, zr), (x + w - k, y + d / 2, zr)], tc)
            E.q([(X0, Y1, ztop), (X0, Y0, ztop), (x + k, y + d / 2, zr)], tc)
            E.q([(X1, Y0, ztop), (X1, Y1, ztop), (x + w - k, y + d / 2, zr)], tc)
        else:
            k = min(w / 2, d / 2)
            E.q([(X0, Y0, ztop), (x + w / 2, y + k, zr), (x + w / 2, y + d - k, zr), (X0, Y1, ztop)], tc)
            E.q([(X1, Y1, ztop), (x + w / 2, y + d - k, zr), (x + w / 2, y + k, zr), (X1, Y0, ztop)], tc)
            E.q([(X0, Y0, ztop), (X1, Y0, ztop), (x + w / 2, y + k, zr)], tc)
            E.q([(X1, Y1, ztop), (X0, Y1, ztop), (x + w / 2, y + d - k, zr)], tc)
        return zr
    # dos aguas (normal, pronunciada, baja)
    if ridge_x:
        E.q([(X0, Y0, ztop), (X1, Y0, ztop), (X1, y + d / 2, zr), (X0, y + d / 2, zr)], tc)
        E.q([(X1, Y1, ztop), (X0, Y1, ztop), (X0, y + d / 2, zr), (X1, y + d / 2, zr)], tc)
        for xx in (x, x + w):
            E.q([(xx, y, ztop), (xx, y + d, ztop), (xx, y + d / 2, zr - 0.05)], corr["muro"])
    else:
        E.q([(X0, Y0, ztop), (x + w / 2, Y0, zr), (x + w / 2, Y1, zr), (X0, Y1, ztop)], tc)
        E.q([(X1, Y1, ztop), (x + w / 2, Y1, zr), (x + w / 2, Y0, zr), (X1, Y0, ztop)], tc)
        for yy in (y, y + d):
            E.q([(x, yy, ztop), (x + w, yy, ztop), (x + w / 2, yy, zr - 0.05)], corr["muro"])
    return zr


def _bloque(E, blq, lay, corr, rnd):
    x, y, w, d = blq["x"], blq["y"], blq["w"], blq["d"]
    zs, ztop = alturas(blq)
    z0 = blq.get("z0", 0.0)
    muro = corr["muro"]
    if blq["sistema"] == "acero" and blq["uso"] == "industrial":
        muro = "#D5D8DA"
    E.caja(x, y, z0, w, d, ztop - z0, muro, techo=corr["techo"])
    vid = corr["vidrio"]
    off = 0.04
    banda = any(k in corr["rasgos"] for k in ("volado", "ventana_corrida", "muro_cortina")) or blq["sistema"] == "marcos"
    nivel_vanos = {id(n): lay[k][1] for k, n in enumerate(blq["niveles"])}
    for zb, h, n in zs:
        if banda and zb > z0 and blq["sistema"] != "mamposteria":
            for (a, b, nx, ny) in [((x, y), (x + w, y), 0, -1), ((x + w, y), (x + w, y + d), 1, 0),
                                   ((x + w, y + d), (x, y + d), 0, 1), ((x, y + d), (x, y), -1, 0)]:
                o = 0.06
                E.q([(a[0] + nx * o, a[1] + ny * o, zb - 0.15), (b[0] + nx * o, b[1] + ny * o, zb - 0.15),
                     (b[0] + nx * o, b[1] + ny * o, zb + 0.15), (a[0] + nx * o, a[1] + ny * o, zb + 0.15)], corr["acento"] if "brut" not in corr["nombre"].lower() else "#8A8883")
        for v in nivel_vanos[id(n)]:
            lado = v.get("lado")
            if not lado:
                continue
            if v["tipo"] == "ventana":
                z1, z2 = (1.6, 2.2) if v.get("alta") else ((0.9, min(h - 0.35, 2.4)) if h < 4 else (1.0, h - 0.8))
                if "muro_cortina" in corr["rasgos"] or "ventana_corrida" in corr["rasgos"]:
                    z1 = 0.2 if "muro_cortina" in corr["rasgos"] else 0.9
                    z2 = h - 0.35 if "muro_cortina" in corr["rasgos"] else min(h - 0.3, 2.2)
                col = vid
            else:
                z1, z2 = 0.0, min(h - 0.3, 2.4 if h < 3.2 else h - 0.9)
                col = vid if (v.get("vidrio") or v["tipo"] == "puerta_ext") else "#55524E"
            a, b = v["a"], v["b"]
            za, zb2 = zb + z1, zb + z2
            if lado == "S":
                E.q([(a, y - off, za), (b, y - off, za), (b, y - off, zb2), (a, y - off, zb2)], col, 0.85)
            elif lado == "N":
                E.q([(b, y + d + off, za), (a, y + d + off, za), (a, y + d + off, zb2), (b, y + d + off, zb2)], col, 0.7)
            elif lado == "O":
                E.q([(x - off, b, za), (x - off, a, za), (x - off, a, zb2), (x - off, b, zb2)], col, 0.75)
            elif lado == "E":
                E.q([(x + w + off, a, za), (x + w + off, b, za), (x + w + off, b, zb2), (x + w + off, a, zb2)], col, 0.8)
    ztech = _cubierta(E, blq, corr, ztop)
    # rasgos de estilo
    ac = corr["acento"]
    if "volado" in corr["rasgos"] and blq["sistema"] != "acero":
        E.caja(x - 0.3, y - 1.6, ztop - 0.35, w * 0.65 + 0.3, 1.6, 0.35, ac)
    if "celosia" in corr["rasgos"] or "parteluces" in corr["rasgos"]:
        n = int(w * 0.4 / 0.35)
        x1 = x + w * 0.55
        top = min(ztop, z0 + 7.0 if blq["sistema"] == "mamposteria" else ztop)
        base = z0 + (zs[1][0] - z0 if len(zs) > 1 else 0.3)
        for k in range(n):
            xx = x1 + k * 0.35
            E.caja(xx, y - 0.35, base, 0.08 if "celosia" in corr["rasgos"] else 0.15, 0.25, top - base, ac)
    if "pergola" in corr["rasgos"] or "porche" in corr["rasgos"]:
        zp = z0 + 2.7
        for k in range(int(w / 0.6)):
            E.caja(x + k * 0.6, y + d, zp, 0.08, 2.5, 0.18, "#6B4B32")
        for xx in (x + 0.2, x + w - 0.4):
            E.caja(xx, y + d + 2.2, z0, 0.2, 0.2, zp - z0, "#6B4B32")
    if "estructura_aparente" in corr["rasgos"] and blq["sistema"] != "mamposteria":
        for xx in np.linspace(x, x + w, max(2, int(w / 8)) + 1):
            E.caja(xx - 0.15, y - 0.35, z0, 0.3, 0.3, ztop - z0 + 0.3, ac)
    if "pilotis" in corr["rasgos"] and len(zs) > 1:
        for xx in np.linspace(x + 0.5, x + w - 0.5, max(2, int(w / 5))):
            E.caja(xx - 0.12, y - 1.2, z0, 0.24, 0.24, zs[1][0] - z0, "#F2F2EE")
    return ztech


def _arbol(E, x, y, rnd, esc=1.0):
    h = (4.5 + rnd.random() * 2.5) * esc
    E.caja(x - 0.11, y - 0.11, 0, 0.22, 0.22, h * 0.45, "#6B4F35")
    r = h * 0.3
    zc = h * 0.68
    verde = rnd.choice(["#6F9A55", "#5F8C4C", "#7AA35C", "#58834A"])
    nl, nv = 8, 5
    P = []
    for j in range(nv + 1):
        ph = math.pi * j / nv - math.pi / 2
        P.append([(x + r * math.cos(ph) * math.cos(2 * math.pi * i / nl + j * 0.4),
                   y + r * math.cos(ph) * math.sin(2 * math.pi * i / nl + j * 0.4),
                   zc + r * 0.85 * math.sin(ph)) for i in range(nl)])
    for j in range(nv):
        for i in range(nl):
            a, b2 = P[j][i], P[j][(i + 1) % nl]
            c, d = P[j + 1][(i + 1) % nl], P[j + 1][i]
            E.q([a, b2, c, d], verde)


def _exteriores(E, proy, rnd):
    t = proy["terreno"]
    F, Fo = t["frente"], t["fondo"]
    mg = max(6.0, 0.12 * max(F, Fo))
    E.q([(-mg, -12, -0.02), (F + mg, -12, -0.02), (F + mg, Fo + mg, -0.02), (-mg, Fo + mg, -0.02)], "#C9C4B5", 0.95)
    E.q([(-mg, -12, 0), (F + mg, -12, 0), (F + mg, -3, 0), (-mg, -3, 0)], "#5C5F62", 0.9)
    E.q([(-mg, -3, 0.01), (F + mg, -3, 0.01), (F + mg, 0, 0.01), (-mg, 0, 0.01)], "#BDB8AC", 0.95)
    for k in range(int((F + 2 * mg) / 6)):
        xx = -mg + k * 6
        E.l((xx, -7.5, 0.02), (xx + 3, -7.5, 0.02), "#E6E2D4", 1.2)
    E.q([(0, 0, 0.005), (F, 0, 0.005), (F, Fo, 0.005), (0, Fo, 0.005)], "#D8D3C5", 0.95)
    for e in proy["exteriores"]:
        x, y, w, d, r = e["x"], e["y"], e["w"], e["d"], e.get("r", 0)
        tp = e["tipo"]
        z = 0.03
        if tp == "area_verde":
            E.q([(x, y, z), (x + w, y, z), (x + w, y + d, z), (x, y + d, z)], "#9DB57A", 0.95)
            bl = [(b["x"], b["y"], b["w"], b["d"]) for b in proy["bloques"]]
            ocup = [(o["x"], o["y"], o["w"], o["d"]) for o in proy["exteriores"] if o["tipo"] not in ("area_verde",) and o["w"]]
            n = int(min(60, max(3, w * d / 60)))
            for _ in range(n):
                px, py = x + 1 + rnd.random() * max(0.1, w - 2), y + 1 + rnd.random() * max(0.1, d - 2)
                if any(bx - 2 < px < bx + bw + 2 and by - 2 < py < by + bd + 2 for bx, by, bw, bd in bl + ocup):
                    continue
                _arbol(E, px, py, rnd, 0.8 if w < 20 else 1.2)
        elif tp in ("alberca", "espejo_agua"):
            E.q([(x - .4, y - .4, z + .01), (x + w + .4, y - .4, z + .01), (x + w + .4, y + d + .4, z + .01), (x - .4, y + d + .4, z + .01)], "#EDE7DA", 1)
            E.q([(x, y, z + .02), (x + w, y, z + .02), (x + w, y + d, z + .02), (x, y + d, z + .02)], "#3FA7C9", 1)
        elif tp in ("estacionamiento", "patio", "acceso", "plaza", "servicio"):
            col = {"estacionamiento": "#7A7D80", "patio": "#8D9093", "acceso": "#BDB8AC", "plaza": "#D9CDB5", "servicio": "#BDB8AC"}[tp]
            E.q([(x, y, z), (x + w, y, z), (x + w, y + d, z), (x, y + d, z)], col, 0.95)
            if tp == "estacionamiento":
                yy, f = y + 0.5, 0
                while yy + 5 <= y + d - 0.5:
                    for k in range(int((w - 1) // 2.5) + 1):
                        xx = x + 0.5 + k * 2.5
                        E.l((xx, yy, z + .02), (xx, yy + 5, z + .02), "#F0F0F0", 0.5)
                    yy += 5 + (6 if f % 2 == 0 else 0); f += 1
                for _ in range(int(w * d / 120)):
                    cx, cy = x + 2 + rnd.random() * (w - 4), y + 2 + rnd.random() * (d - 6)
                    E.caja(cx, cy, z, 1.8, 4.3, 1.4, rnd.choice(["#2F3A45", "#B8BCC0", "#8C2F2B", "#E6E6E6", "#3C5A78"]))
        elif tp == "caseta":
            E.caja(x, y, 0, w, d, 3, "#E2DED4")
        elif tp == "cisterna":
            E.caja(x, y, 0, w, d, 0.4, "#9A9A96")
        elif tp == "rio":
            n = 40
            for k in range(n):
                a0, a1 = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n
                E.q([(x + r * math.cos(a0), y + r * math.sin(a0), z + .02), (x + r * math.cos(a1), y + r * math.sin(a1), z + .02),
                     (x + (r - 6) * math.cos(a1), y + (r - 6) * math.sin(a1), z + .02), (x + (r - 6) * math.cos(a0), y + (r - 6) * math.sin(a0), z + .02)],
                    "#45B0CF", 1)
        elif tp == "toboganes":
            h = e.get("h", 18)
            E.caja(x, y, 0, w, d, h, "#E8E2D2")
            for k, col in enumerate(["#E4572E", "#F3A712", "#29335C"]):
                pts = [(x + w / 2 + (8 + 3 * k) * math.cos(t * 0.9 + k), y + d / 2 + (8 + 3 * k) * math.sin(t * 0.9 + k), h - t * h / 14)
                       for t in np.linspace(0, 14, 60)]
                for p, q2 in zip(pts, pts[1:]):
                    E.l(p, q2, col, 3.0)
        elif tp == "palapas":
            for i in range(3):
                for j in range(3):
                    cx, cy = x + w * (i + .5) / 3, y + d * (j + .5) / 3
                    E.caja(cx - .1, cy - .1, 0, .2, .2, 2.6, "#6B4F35")
                    ring = [(cx + 2.2 * math.cos(2 * math.pi * k / 8), cy + 2.2 * math.sin(2 * math.pi * k / 8), 2.6) for k in range(8)]
                    for k in range(8):
                        E.q([ring[k], ring[(k + 1) % 8], (cx, cy, 3.8)], "#C9A66B")
        elif tp == "rueda":
            n = 48
            pts = [(x + r * math.cos(2 * math.pi * k / n), y, r + 3 + r * math.sin(2 * math.pi * k / n)) for k in range(n)]
            for k in range(n):
                E.l(pts[k], pts[(k + 1) % n], "#D04A3A", 2.2)
                if k % 4 == 0:
                    E.l((x, y, r + 3), pts[k], "#9A9A9A", 0.6)
                    E.caja(pts[k][0] - .7, y - .7, pts[k][2] - 1.6, 1.4, 1.4, 1.4, rnd.choice(["#F3A712", "#29335C", "#E4572E", "#3FA7C9"]))
            for s in (-1, 1):
                E.l((x - r * 0.45, y + s * 2, 0), (x, y, r + 3), "#7A7A7A", 2)
                E.l((x + r * 0.45, y + s * 2, 0), (x, y, r + 3), "#7A7A7A", 2)
        elif tp == "carrusel":
            n = 16
            ring = [(x + r * math.cos(2 * math.pi * k / n), y + r * math.sin(2 * math.pi * k / n)) for k in range(n)]
            for k in range(n):
                a, b = ring[k], ring[(k + 1) % n]
                E.q([(a[0], a[1], 0), (b[0], b[1], 0), (b[0], b[1], 0.8), (a[0], a[1], 0.8)], "#E4C35A")
                E.q([(a[0], a[1], 4.5), (b[0], b[1], 4.5), (x, y, 7.5)], "#D04A3A" if k % 2 else "#F5F0E6")
        elif tp == "montaña_rusa":
            h = e.get("h", 24)
            pts = []
            for i in range(121):
                a = 2 * math.pi * i / 120
                pts.append((x + w / 2 + w / 2 * math.cos(a) * (1 + 0.25 * math.sin(3 * a)), y + d / 2 + d / 2 * math.sin(a),
                            4 + (h - 4) * (0.5 + 0.5 * math.sin(2 * a + 1)) ** 1.6))
            for p, q2 in zip(pts, pts[1:]):
                E.l(p, q2, "#29335C", 3.0)
            for p in pts[::6]:
                E.l((p[0], p[1], 0), p, "#9A9A9A", 0.8)
        elif tp == "cancha":
            E.q([(x, y, z), (x + w, y, z), (x + w, y + d, z), (x, y + d, z)], "#B85C3B", 0.95)
            E.l((x + w / 2, y, z + .02), (x + w / 2, y + d, z + .02), "#FFFFFF", 0.8)
        elif tp == "juegos":
            E.q([(x, y, z), (x + w, y, z), (x + w, y + d, z), (x, y + d, z)], "#E2B66A", 0.95)
            for k in range(5):
                E.caja(x + 2 + rnd.random() * (w - 6), y + 2 + rnd.random() * (d - 6), 0, 3, 3, 2 + rnd.random() * 3,
                       rnd.choice(["#E4572E", "#F3A712", "#3FA7C9", "#76B041"]))
    # árboles de banqueta
    xs_arb = [1.2, F - 1.2] if F < 24 else [2 + k * 9 for k in range(int((F - 2) / 9) + 1)]
    for xa in xs_arb:
        _arbol(E, xa, -1.5, rnd, 0.85)


def render(proy, lays, corr, ruta_aereo, ruta_peatonal, titulo, seed=1, ss=2, W=1600, H=1000):
    from . import rast
    rnd = random.Random(seed)
    E = Escena()
    _exteriores(E, proy, rnd)
    zmax = 0
    for bi, blq in enumerate(proy["bloques"]):
        zmax = max(zmax, _bloque(E, blq, lays[bi], corr, rnd))
    t = proy["terreno"]
    F, Fo = t["frente"], t["fondo"]
    sm = rast.mapa_sombras([P for P, fl in zip(E.polys, E.flat) if not fl], SOL, 2048)
    normales = []
    for P in E.polys:
        n = np.cross(P[1] - P[0], P[2] - P[0])
        if np.linalg.norm(n) < 1e-9 and len(P) > 3:
            n = np.cross(P[2] - P[0], P[3] - P[0])
        normales.append(n / (np.linalg.norm(n) + 1e-12))
    cen = np.array([F / 2, Fo / 2, 0.0])
    Rb = 0.5 * math.sqrt(F ** 2 + Fo ** 2 + (zmax * 1.6) ** 2)
    vistas = [(ruta_aereo, -124, 31, 40, np.array([F / 2, Fo / 2, zmax * 0.25]), 1.12 if Rb < 40 else 0.92),
              (ruta_peatonal, -104, 11, 50, np.array([F / 2, Fo * 0.40, zmax * 0.40]), 0.78)]
    for ruta, az, el, fov, tgt, k in vistas:
        fv = 2 * math.atan(math.tan(math.radians(fov / 2)) * H / W)
        dist = Rb / math.tan(fv / 2) * k
        a, e = math.radians(az), math.radians(el)
        eye = tgt + dist * np.array([math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), math.sin(e)])
        eye[2] = max(eye[2], 1.7)
        R = rast.Rasterizador(W * ss, H * ss)
        R.camara(eye, tgt, fov)
        for i, (P, c, fl, n) in enumerate(zip(E.polys, E.cols, E.flat, normales)):
            if np.dot(n, eye - P.mean(axis=0)) < 0:
                n = -n
            R.poligono(P, c, float(max(0.0, np.dot(n, SOL))), 1.0 if fl else 0.0, i)
        base = len(E.polys)
        for j, ((pa, pb), (col, w)) in enumerate(zip(E.lines, E.lcols)):
            R.linea(np.array(pa, float), np.array(pb, float), np.array(to_rgb(col), np.float32), max(1, int(w * ss)), base + j)
        img = rast.componer(R, sm, niebla=0.0012 / max(1.0, Rb / 40))
        rast.guardar(img, ruta, ss, titulo, f"{corr['nombre']}  ·  render volumétrico de anteproyecto")
    return [ruta_aereo, ruta_peatonal]
