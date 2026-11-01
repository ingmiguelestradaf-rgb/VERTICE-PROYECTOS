"""Renders fotorrealistas y recorrido virtual en Blender (Cycles).

Uso (Blender 4.2 LTS):
  blender -b -P motor/foto/blender_escena.py -- escena.json carpeta_salida [--prueba] [--sin-video] [--sin-fotos]
"""
import json
import time
import math
import os
import sys

import bpy
from mathutils import Vector

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
RUTA, SALIDA = ARGS[0], ARGS[1]
PRUEBA = "--prueba" in ARGS
os.makedirs(SALIDA, exist_ok=True)
E = json.load(open(RUTA, encoding="utf-8"))
EPS = 0.02


def hexrgb(h, a=1.0):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple((x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4) for x in c) + (a,)


# ------------------------------------------------------------------ escena base
bpy.ops.wm.read_factory_settings(use_empty=True)
SC = bpy.context.scene


# ------------------------------------------------------------------ materiales
def material(nombre, color, rough=0.8, metal=0.0, trans=0.0, ruido=0.0, escala=4.0, bump=0.0, emision=None, alpha=1.0):
    m = bpy.data.materials.get(nombre)
    if m:
        return m
    m = bpy.data.materials.new(nombre)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = color
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if trans:
        b.inputs["Transmission Weight"].default_value = trans
        b.inputs["IOR"].default_value = 1.45
    if emision:
        b.inputs["Emission Color"].default_value = emision
        b.inputs["Emission Strength"].default_value = 3.0
    if ruido or bump:
        tc = nt.nodes.new("ShaderNodeTexCoord")
        nz = nt.nodes.new("ShaderNodeTexNoise")
        nz.inputs["Scale"].default_value = escala
        nz.inputs["Detail"].default_value = 8.0
        nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
        if ruido:
            mix = nt.nodes.new("ShaderNodeMixRGB")
            mix.blend_type = "MULTIPLY"
            mix.inputs["Fac"].default_value = ruido
            mix.inputs["Color1"].default_value = color
            ramp = nt.nodes.new("ShaderNodeValToRGB")
            ramp.color_ramp.elements[0].color = (0.75, 0.75, 0.75, 1)
            ramp.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1)
            nt.links.new(nz.outputs["Fac"], ramp.inputs["Fac"])
            nt.links.new(ramp.outputs["Color"], mix.inputs["Color2"])
            nt.links.new(mix.outputs["Color"], b.inputs["Base Color"])
        if bump:
            bp = nt.nodes.new("ShaderNodeBump")
            bp.inputs["Strength"].default_value = bump
            nt.links.new(nz.outputs["Fac"], bp.inputs["Height"])
            nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


def material_piedra(nombre, color):
    m = bpy.data.materials.new(nombre)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    vo = nt.nodes.new("ShaderNodeTexVoronoi")
    vo.inputs["Scale"].default_value = 6.0
    vo.feature = "DISTANCE_TO_EDGE"
    nt.links.new(tc.outputs["Object"], vo.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = (0.08, 0.075, 0.07, 1)
    ramp.color_ramp.elements[1].position = 0.06
    ramp.color_ramp.elements[1].color = color
    nt.links.new(vo.outputs["Distance"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.6
    nt.links.new(vo.outputs["Distance"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    b.inputs["Roughness"].default_value = 0.9
    return m


C = E["corriente"]
M = dict(
    muro=material("Aplanado exterior", hexrgb(C["muro"]), 0.9, ruido=0.25, escala=6, bump=0.08),
    interior=material("Aplanado interior", hexrgb("#E4DED3"), 0.85, ruido=0.08, escala=5),
    acento=material("Acento", hexrgb(C["acento"]), 0.55, ruido=0.15, escala=3, bump=0.05),
    techo=material("Cubierta", hexrgb(C["techo"]), 0.75, ruido=0.2, escala=8, bump=0.1),
    losa=material("Concreto", hexrgb("#9C9A95"), 0.85, ruido=0.3, escala=10, bump=0.05),
    vidrio=material("Vidrio", (0.85, 0.92, 0.95, 1), 0.02, trans=1.0),
    marco=material("Cancelería", hexrgb("#2B2C2E"), 0.35, metal=0.7),
    madera=material("Madera", hexrgb("#7A5236"), 0.5, ruido=0.35, escala=2.5),
    piso=material("Piso de madera", hexrgb("#9A7350"), 0.35, ruido=0.08, escala=1.2),
    piso_bano=material("Porcelanato baño", hexrgb("#BDB7AD"), 0.3, ruido=0.08, escala=1.5),
    concreto_piso=material("Concreto escobillado", hexrgb("#A7A49C"), 0.9, ruido=0.25, escala=12, bump=0.1),
    pasto=material("Pasto", hexrgb("#5E7F3E"), 0.95, ruido=0.45, escala=25, bump=0.3),
    asfalto=material("Asfalto", hexrgb("#3B3D3F"), 0.9, ruido=0.3, escala=30, bump=0.15),
    banqueta=material("Banqueta", hexrgb("#B9B4A8"), 0.85, ruido=0.2, escala=8),
    porton=material("Portón", hexrgb("#4A4846"), 0.45, metal=0.5),
    tela=material("Tela", hexrgb("#8E8A80"), 0.9, ruido=0.1, escala=20),
    blanco=material("Blanco", hexrgb("#ECEAE5"), 0.4),
    ceramica=material("Cerámica", hexrgb("#F4F4F2"), 0.1),
    follaje=material("Follaje", hexrgb("#4F6F35"), 0.8, ruido=0.6, escala=6, bump=0.5),
    tronco=material("Tronco", hexrgb("#5B4433"), 0.9, ruido=0.3, escala=10),
    cubierta_cocina=material("Cubierta cocina", hexrgb("#2F2F31"), 0.2, ruido=0.15, escala=4),
    auto=material("Auto", hexrgb("#2D3E50"), 0.2, metal=0.8),
    llanta=material("Llanta", hexrgb("#1A1A1A"), 0.8),
    barda=material("Barda", hexrgb("#D8D2C4"), 0.9, ruido=0.2, escala=6, bump=0.05),
)
M["piedra"] = material_piedra("Piedra laja", hexrgb("#8E8579"))


# ------------------------------------------------------------------ geometría acumulada por material
class Malla:
    def __init__(self):
        self.g = {}

    def caja(self, mat, x0, y0, z0, x1, y1, z1):
        if x1 - x0 < 1e-4 or y1 - y0 < 1e-4 or z1 - z0 < 1e-4:
            return
        v, f = self.g.setdefault(mat, ([], []))
        i = len(v)
        v += [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
        f += [(i, i + 3, i + 2, i + 1), (i + 4, i + 5, i + 6, i + 7), (i, i + 1, i + 5, i + 4),
              (i + 1, i + 2, i + 6, i + 5), (i + 2, i + 3, i + 7, i + 6), (i + 3, i, i + 4, i + 7)]

    def poli(self, mat, pts):
        v, f = self.g.setdefault(mat, ([], []))
        i = len(v)
        v += list(pts)
        f.append(tuple(range(i, i + len(pts))))

    def crear(self):
        for mat, (v, f) in self.g.items():
            me = bpy.data.meshes.new(mat)
            me.from_pydata(v, [], f)
            me.update()
            ob = bpy.data.objects.new(mat, me)
            ob.data.materials.append(M[mat])
            SC.collection.objects.link(ob)


G = Malla()


def segmentos(a, b, huecos):
    out, cur = [], a
    for h0, h1 in sorted(huecos):
        if h0 > cur + 1e-3:
            out.append((cur, h0))
        cur = max(cur, h1)
    if b > cur + 1e-3:
        out.append((cur, b))
    return out


def perimetral(ln, blq):
    if ln["eje"] == "h":
        return abs(ln["c"] - blq["y"]) < EPS or abs(ln["c"] - (blq["y"] + blq["d"])) < EPS
    return abs(ln["c"] - blq["x"]) < EPS or abs(ln["c"] - (blq["x"] + blq["w"])) < EPS


def muro(ln, a, b, z0, z1, t, mat):
    if ln["eje"] == "h":
        G.caja(mat, a, ln["c"] - t / 2, z0, b, ln["c"] + t / 2, z1)
    else:
        G.caja(mat, ln["c"] - t / 2, a, z0, ln["c"] + t / 2, b, z1)


# ------------------------------------------------------------------ edificio
z_top_global = 0.0
for blq in E["bloques"]:
    for nv in blq["niveles"]:
        z, h, losa = nv["z"], nv["h"], nv["losa"]
        zc = z + h - losa
        lados = [dict(eje="h", c=blq["y"], a=blq["x"] - nv["ty"] / 2, b=blq["x"] + blq["w"] + nv["ty"] / 2),
                 dict(eje="h", c=blq["y"] + blq["d"], a=blq["x"] - nv["ty"] / 2, b=blq["x"] + blq["w"] + nv["ty"] / 2),
                 dict(eje="v", c=blq["x"], a=blq["y"], b=blq["y"] + blq["d"]),
                 dict(eje="v", c=blq["x"] + blq["w"], a=blq["y"], b=blq["y"] + blq["d"])]
        for ln in [m for m in nv["muros"] if not perimetral(m, blq)] + lados:
            t = nv["tx"] if ln["eje"] == "h" else nv["ty"]
            ext = ln in lados
            t_ = t + (0.05 if ext else 0.03)
            mat = "muro" if ext else "interior"
            vs = [v for v in nv["vanos"] if v["eje"] == ln["eje"] and abs(v["c"] - ln["c"]) < EPS and v["b"] > ln["a"] and v["a"] < ln["b"]]
            for a, b in segmentos(ln["a"], ln["b"], [(v["a"], v["b"]) for v in vs]):
                muro(ln, a, b, z, zc, t_, mat)
            for v in vs:
                a, b = max(v["a"], ln["a"]), min(v["b"], ln["b"])
                muro(ln, a, b, z + v["z2"], zc, t_, mat)               # cerramiento
                if v["z1"] > 0.01:
                    muro(ln, a, b, z, z + v["z1"], t_, mat)            # antepecho
                if v["tipo"] in ("ventana",) or (v["tipo"] in ("porton", "puerta_ext") and v.get("vidrio")):
                    # vidrio y marco
                    fz0, fz1 = z + v["z1"], z + v["z2"]
                    fr = 0.05
                    if ln["eje"] == "h":
                        G.caja("vidrio", a + fr, ln["c"] - 0.006, fz0 + fr, b - fr, ln["c"] + 0.006, fz1 - fr)
                        for (x0, x1, q0, q1) in ((a, a + fr, fz0, fz1), (b - fr, b, fz0, fz1), (a, b, fz0, fz0 + fr), (a, b, fz1 - fr, fz1)):
                            G.caja("marco", x0, ln["c"] - 0.04, q0, x1, ln["c"] + 0.04, q1)
                        n = max(1, int((b - a) / 1.1))
                        for i in range(1, n):
                            xm = a + (b - a) * i / n
                            G.caja("marco", xm - 0.025, ln["c"] - 0.04, fz0, xm + 0.025, ln["c"] + 0.04, fz1)
                    else:
                        G.caja("vidrio", ln["c"] - 0.006, a + fr, fz0 + fr, ln["c"] + 0.006, b - fr, fz1 - fr)
                        for (y0, y1, q0, q1) in ((a, a + fr, fz0, fz1), (b - fr, b, fz0, fz1), (a, b, fz0, fz0 + fr), (a, b, fz1 - fr, fz1)):
                            G.caja("marco", ln["c"] - 0.04, y0, q0, ln["c"] + 0.04, y1, q1)
                elif v["tipo"] == "porton":
                    if ln["eje"] == "h":
                        G.caja("porton", a, ln["c"] - 0.03, z, b, ln["c"] + 0.03, z + v["z2"])
                    else:
                        G.caja("porton", ln["c"] - 0.03, a, z, ln["c"] + 0.03, b, z + v["z2"])
                elif v["tipo"] == "puerta_ext":
                    # puerta principal de madera abierta 75°
                    hoja = (b - a) / 2
                    if ln["eje"] == "h":
                        G.caja("madera", a, ln["c"] + 0.05, z, a + 0.05, ln["c"] + 0.05 + hoja, z + v["z2"])
                        G.caja("madera", b - 0.05, ln["c"] + 0.05, z, b, ln["c"] + 0.05 + hoja, z + v["z2"])
        # losa del nivel (sobre locales, sin hueco de escalera salvo el último nivel)
        ultimo = nv is blq["niveles"][-1]
        X0, Y0 = blq["x"] - nv["ty"] / 2 - 0.03, blq["y"] - nv["tx"] / 2 - 0.03
        X1, Y1 = blq["x"] + blq["w"] + nv["ty"] / 2 + 0.03, blq["y"] + blq["d"] + nv["tx"] / 2 + 0.03
        hueco = None if ultimo else next((c for c in nv["locales"] if c["t"] == "escalera"), None)
        if hueco:
            hx0, hy0, hx1, hy1 = hueco["x"], hueco["y"], hueco["x"] + hueco["w"], hueco["y"] + hueco["d"]
            G.caja("losa", X0, Y0, zc, hx0, Y1, z + h)
            G.caja("losa", hx1, Y0, zc, X1, Y1, z + h)
            G.caja("losa", hx0, Y0, zc, hx1, hy0, z + h)
            G.caja("losa", hx0, hy1, zc, hx1, Y1, z + h)
        else:
            G.caja("losa", X0, Y0, zc, X1, Y1, z + h)
        # plafón interior
        for c in nv["locales"]:
            if c is not hueco:
                G.caja("interior", c["x"], c["y"], zc - 0.01, c["x"] + c["w"], c["y"] + c["d"], zc)
        # pisos terminados
        for c in nv["locales"]:
            mat = "piso_bano" if c["t"] == "humedo" else ("concreto_piso" if c["t"] in ("ext", "almacen") else "piso")
            if c["t"] == "escalera" and nv["piso"] > 0:
                continue
            G.caja(mat, c["x"], c["y"], z, c["x"] + c["w"], c["y"] + c["d"], z + 0.02)
        # escalera en U
        for c in nv["locales"]:
            if c["t"] != "escalera" or ultimo:
                continue
            larg = c["w"] >= c["d"]
            L, A = (c["w"], c["d"]) if larg else (c["d"], c["w"])
            desc = max(1.0, A / 2)
            run = L - desc - 0.1
            n = max(6, round((h / 2) / 0.17))
            p, hu = (h / 2) / n, run / n
            for tramo in (0, 1):
                for i in range(n):
                    if tramo == 0:
                        s0 = 0.05 + i * hu
                        zt = z + (i + 1) * p
                        q0, q1 = 0.05, A / 2 - 0.03
                    else:
                        s0 = 0.05 + run - (i + 1) * hu
                        zt = z + h / 2 + (i + 1) * p
                        q0, q1 = A / 2 + 0.03, A - 0.05
                    zb = zt - 0.25 if tramo == 0 else zt - 0.25
                    if larg:
                        G.caja("losa", c["x"] + s0, c["y"] + q0, max(z, zb), c["x"] + s0 + hu, c["y"] + q1, zt)
                    else:
                        G.caja("losa", c["x"] + q0, c["y"] + s0, max(z, zb), c["x"] + q1, c["y"] + s0 + hu, zt)
            # descanso
            if larg:
                G.caja("losa", c["x"] + 0.05 + run, c["y"] + 0.05, z + h / 2 - 0.15, c["x"] + L - 0.05, c["y"] + A - 0.05, z + h / 2)
            else:
                G.caja("losa", c["x"] + 0.05, c["y"] + 0.05 + run, z + h / 2 - 0.15, c["x"] + A - 0.05, c["y"] + L - 0.05, z + h / 2)
        z_top_global = max(z_top_global, z + h)
    # cubierta
    top = blq["niveles"][-1]["z"] + blq["niveles"][-1]["h"]
    x0, y0, w, d = blq["x"], blq["y"], blq["w"], blq["d"]
    cub = C["cubierta"]
    if cub in ("plana", "plana_pretil") or blq["sistema"] != "mamposteria" and not cub.startswith(("dos", "cuatro", "una")):
        par = 0.6 if cub == "plana" else 1.1
        e = 0.15
        for (a0, b0, a1, b1) in ((x0 - e, y0 - e, x0 + w + e, y0), (x0 - e, y0 + d, x0 + w + e, y0 + d + e),
                                 (x0 - e, y0, x0, y0 + d), (x0 + w, y0, x0 + w + e, y0 + d)):
            G.caja("muro", a0, b0, top, a1, b1, top + par)
    else:
        al = 0.6
        X0, Y0, X1, Y1 = x0 - al, y0 - al, x0 + w + al, y0 + d + al
        span = min(w, d)
        pend = {"dos_aguas_pronunciada": 0.8, "dos_aguas_baja": 0.18, "cuatro_aguas_baja": 0.18}.get(cub, 0.3)
        r = min(3.2, pend * span / 2)
        if cub.startswith("una") or cub == "inclinada_irregular" or cub == "curva":
            G.poli("techo", [(X0, Y0, top + 0.1), (X1, Y0, top + 0.1), (X1, Y1, top + r), (X0, Y1, top + r)])
            G.poli("muro", [(x0, y0, top), (x0, y0 + d, top), (x0, y0 + d, top + r * 0.95)])
            G.poli("muro", [(x0 + w, y0, top), (x0 + w, y0 + d, top + r * 0.95), (x0 + w, y0 + d, top)])
            G.caja("muro", x0, y0 + d - 0.15, top, x0 + w, y0 + d, top + r * 0.95)
        elif cub.startswith("cuatro"):
            if w >= d:
                k = d / 2
                G.poli("techo", [(X0, Y0, top), (X1, Y0, top), (x0 + w - k, y0 + d / 2, top + r), (x0 + k, y0 + d / 2, top + r)])
                G.poli("techo", [(X1, Y1, top), (X0, Y1, top), (x0 + k, y0 + d / 2, top + r), (x0 + w - k, y0 + d / 2, top + r)])
                G.poli("techo", [(X0, Y1, top), (X0, Y0, top), (x0 + k, y0 + d / 2, top + r)])
                G.poli("techo", [(X1, Y0, top), (X1, Y1, top), (x0 + w - k, y0 + d / 2, top + r)])
            else:
                k = w / 2
                G.poli("techo", [(X0, Y0, top), (x0 + w / 2, y0 + k, top + r), (x0 + w / 2, y0 + d - k, top + r), (X0, Y1, top)])
                G.poli("techo", [(X1, Y1, top), (x0 + w / 2, y0 + d - k, top + r), (x0 + w / 2, y0 + k, top + r), (X1, Y0, top)])
                G.poli("techo", [(X0, Y0, top), (X1, Y0, top), (x0 + w / 2, y0 + k, top + r)])
                G.poli("techo", [(X1, Y1, top), (X0, Y1, top), (x0 + w / 2, y0 + d - k, top + r)])
        else:   # dos aguas, cumbrera paralela al lado largo
            if w >= d:
                G.poli("techo", [(X0, Y0, top), (X1, Y0, top), (X1, y0 + d / 2, top + r), (X0, y0 + d / 2, top + r)])
                G.poli("techo", [(X1, Y1, top), (X0, Y1, top), (X0, y0 + d / 2, top + r), (X1, y0 + d / 2, top + r)])
                for xx in (x0, x0 + w):
                    G.poli("muro", [(xx, y0, top), (xx, y0 + d, top), (xx, y0 + d / 2, top + r - 0.05)])
            else:
                G.poli("techo", [(X0, Y0, top), (x0 + w / 2, Y0, top + r), (x0 + w / 2, Y1, top + r), (X0, Y1, top)])
                G.poli("techo", [(X1, Y1, top), (x0 + w / 2, Y1, top + r), (x0 + w / 2, Y0, top + r), (X1, Y0, top)])
                for yy in (y0, y0 + d):
                    G.poli("muro", [(x0, yy, top), (x0 + w, yy, top), (x0 + w / 2, yy, top + r - 0.05)])

    # rasgos de fachada principal (sur)
    ras = C["rasgos"]
    vs_sur = [(v["a"], v["b"]) for nv in blq["niveles"] for v in nv["vanos"] if v.get("lado") == "S"]
    libres, cur = [], x0
    for a, b in sorted(vs_sur):
        if a - 0.3 > cur:
            libres.append((cur, a - 0.3))
        cur = max(cur, b + 0.3)
    libres.append((cur, x0 + w))
    la, lb = max(libres, key=lambda q: q[1] - q[0])
    if "volado" in ras:
        G.caja("acento", x0 - 0.3, y0 - 1.6, top - 0.35, x0 + w * 0.65, y0 - 0.1, top)
    if "muro_acento" in ras and lb - la > 0.9:
        G.caja("piedra", la, y0 - 0.16, 0.0, lb, y0 - 0.1, top)
    if "jardinera" in ras:
        vs0 = [(v["a"], v["b"]) for v in blq["niveles"][0]["vanos"] if v.get("lado") == "S"]
        lib0, cur = [], x0
        for a, b in sorted(vs0):
            if a - 0.3 > cur:
                lib0.append((cur, a - 0.3))
            cur = max(cur, b + 0.3)
        lib0.append((cur, x0 + w))
        ja, jb = max(lib0, key=lambda q: q[1] - q[0])
        if jb - ja > 1.0:
            G.caja("losa", ja + 0.1, y0 - 0.85, 0, jb - 0.1, y0 - 0.25, 0.5)
            G.caja("pasto", ja + 0.15, y0 - 0.8, 0.45, jb - 0.15, y0 - 0.3, 0.55)
    if "celosia" in ras or "parteluces" in ras:
        n = int(w * 0.35 / 0.3)
        for i in range(n):
            xx = x0 + w * 0.6 + i * 0.3
            G.caja("madera" if "celosia" in ras else "losa", xx, y0 - 0.45, blq["niveles"][0]["h"], xx + 0.06, y0 - 0.2, top)
    if "pergola" in ras or "porche" in ras:
        for i in range(int(w / 0.6)):
            G.caja("madera", x0 + i * 0.6, y0 + d, 2.7, x0 + i * 0.6 + 0.08, y0 + d + 2.6, 2.88)
        for xx in (x0 + 0.2, x0 + w - 0.4):
            G.caja("madera", xx, y0 + d + 2.3, 0, xx + 0.2, y0 + d + 2.5, 2.7)
    if "marco" in ras and len(blq["niveles"]) > 1:
        zb1 = blq["niveles"][1]["z"]
        fx0 = x0 + w * 0.38
        G.caja("acento", fx0, y0 - 0.9, zb1 - 0.3, x0 + w + 0.05, y0, zb1)
        G.caja("acento", fx0, y0 - 0.9, top - 0.3, x0 + w + 0.05, y0, top)
        G.caja("acento", fx0, y0 - 0.9, zb1 - 0.3, fx0 + 0.3, y0, top)
        G.caja("acento", x0 + w - 0.25, y0 - 0.9, zb1 - 0.3, x0 + w + 0.05, y0, top)


# ------------------------------------------------------------------ mobiliario
def aberturas(c, vanos):
    out = set()
    for v in vanos:
        if v["tipo"] not in ("puerta", "vano", "puerta_ext", "porton"):
            continue
        if v["eje"] == "h" and v["a"] < c["x"] + c["w"] and v["b"] > c["x"]:
            if abs(v["c"] - c["y"]) < EPS:
                out.add("S")
            if abs(v["c"] - c["y"] - c["d"]) < EPS:
                out.add("N")
        if v["eje"] == "v" and v["a"] < c["y"] + c["d"] and v["b"] > c["y"]:
            if abs(v["c"] - c["x"]) < EPS:
                out.add("O")
            if abs(v["c"] - c["x"] - c["w"]) < EPS:
                out.add("E")
    return out


OP = {"S": "N", "N": "S", "O": "E", "E": "O"}


def pared(c, vanos, larga=False):
    ab = aberturas(c, vanos)
    L = {"S": c["w"], "N": c["w"], "O": c["d"], "E": c["d"]}
    return min("SNOE", key=lambda l: (0 if l not in ab else 10) - (2 if OP[l] in ab else 0) - L[l] * (1 if larga else 0.1))


def contra(c, lado, ancho, fondo, z0, z1, mat, despl=0.0, sep=0.1):
    x, y, w, d = c["x"], c["y"], c["w"], c["d"]
    if lado in ("S", "N"):
        cx = x + w / 2 + despl - ancho / 2
        cy = y + sep if lado == "S" else y + d - sep - fondo
        G.caja(mat, cx, cy, z0, cx + ancho, cy + fondo, z1)
        return cx, cy, ancho, fondo
    cy = y + d / 2 + despl - ancho / 2
    cx = x + sep if lado == "O" else x + w - sep - fondo
    G.caja(mat, cx, cy, z0, cx + fondo, cy + ancho, z1)
    return cx, cy, fondo, ancho


for blq in E["bloques"]:
    if not E["unifamiliar"]:
        break
    for nv in blq["niveles"]:
        z = nv["z"]
        for c in nv["locales"]:
            n, corto = c["n"], min(c["w"], c["d"])
            lado = pared(c, nv["vanos"])
            if n.startswith("Recámara") and corto >= 2.6:
                bw, bl = (1.6, 2.0) if "principal" in n else (1.35, 1.9)
                bx, by, ba, bb = contra(c, lado, bw, bl, z, z + 0.45, "tela")
                G.caja("blanco", bx + 0.03, by + 0.03, z + 0.45, bx + ba - 0.03, by + bb - 0.03, z + 0.55)
                contra(c, lado, bw + 0.1, 0.08, z, z + 1.1, "madera", sep=0.02)
                for s in (-1, 1):
                    contra(c, lado, 0.45, 0.4, z, z + 0.55, "madera", despl=s * (bw / 2 + 0.35))
            elif (n.startswith("Sala") or n in ("Family room", "Cuarto de TV")) and corto >= 2.8:
                sx, sy, sa, sb = contra(c, lado, min(2.3, corto - 0.6), 0.9, z, z + 0.42, "tela")
                contra(c, lado, min(2.3, corto - 0.6), 0.2, z, z + 0.85, "tela", sep=0.1)
                contra(c, lado, 1.1, 0.6, z, z + 0.4, "madera", sep=1.5)
                if "comedor" in n:
                    lc = OP[lado]
                    contra(c, lc, 1.6, 0.9, z + 0.72, z + 0.76, "madera", sep=0.9)
                    contra(c, lc, 0.1, 0.1, z, z + 0.72, "madera", sep=1.3)
            elif n == "Comedor":
                cx, cy = c["x"] + c["w"] / 2, c["y"] + c["d"] / 2
                G.caja("madera", cx - 0.8, cy - 0.45, z + 0.72, cx + 0.8, cy + 0.45, z + 0.76)
                G.caja("madera", cx - 0.05, cy - 0.05, z, cx + 0.05, cy + 0.05, z + 0.72)
            elif n.startswith("Cocina") and corto >= 1.8:
                lc = pared(c, nv["vanos"], larga=True)
                lon = (c["w"] if lc in ("S", "N") else c["d"]) - 0.3
                contra(c, lc, lon, 0.6, z, z + 0.86, "blanco", sep=0.08)
                contra(c, lc, lon, 0.62, z + 0.86, z + 0.9, "cubierta_cocina", sep=0.07)
                contra(c, lc, lon, 0.35, z + 1.5, z + 2.2, "blanco", sep=0.08)
                contra(c, lc, 0.85, 0.7, z, z + 1.9, "blanco", despl=lon / 2 - 0.45, sep=0.08)
            elif n.startswith("Baño") or n == "Medio baño":
                lb = pared(c, nv["vanos"], larga=True)
                contra(c, lb, 0.8, 0.5, z + 0.5, z + 0.85, "blanco", despl=0.3)
                contra(c, lb, 0.4, 0.65, z, z + 0.42, "ceramica", despl=-0.5)
            elif n.startswith("Cochera"):
                autos = 2 if "doble" in n else 1
                for k in range(autos):
                    cx = c["x"] + c["w"] * (k + 0.5) / autos
                    y1 = c["y"] + 0.6
                    G.caja("auto", cx - 0.9, y1, z + 0.3, cx + 0.9, y1 + 4.4, z + 0.95)
                    G.caja("vidrio", cx - 0.8, y1 + 1.2, z + 0.95, cx + 0.8, y1 + 3.3, z + 1.45)
                    for dx in (-0.85, 0.65):
                        for dy in (0.7, 3.4):
                            G.caja("llanta", cx + dx, y1 + dy, z, cx + dx + 0.2, y1 + dy + 0.6, z + 0.6)

# ------------------------------------------------------------------ exteriores
T = E["terreno"]
F, Fo = T["frente"], T["fondo"]
G.caja("asfalto", -120, -12, -0.05, F + 120, -2.2, 0.0)
G.caja("banqueta", -120, -2.2, -0.05, F + 120, 0.0, 0.12)
G.caja("pasto", -120, 0.0, -0.06, F + 120, Fo + 120, -0.01)
G.caja("pasto", -120, -150, -0.07, F + 120, -12, -0.03)
for e in E["exteriores"]:
    x, y, w, d = e["x"], e["y"], e["w"], e["d"]
    tp = e["tipo"]
    if tp == "area_verde" and w and d:
        G.caja("pasto", x, y, -0.02, x + w, y + d, 0.02)
    elif tp in ("acceso", "estacionamiento", "patio", "plaza", "servicio"):
        G.caja("concreto_piso" if tp != "plaza" else "banqueta", x, y, -0.02, x + w, y + d, 0.03)
    elif tp in ("alberca", "espejo_agua"):
        G.caja("banqueta", x - 0.4, y - 0.4, 0, x + w + 0.4, y + d + 0.4, 0.04)
        G.caja("vidrio", x, y, -0.4, x + w, y + d, 0.0)
if E["unifamiliar"]:
    b0 = E["bloques"][0]
    for xx in (0.0, F - 0.15):
        G.caja("barda", xx, b0["y"] + b0["d"], 0, xx + 0.15, Fo, 2.4)
    G.caja("barda", 0, Fo - 0.15, 0, F, Fo, 2.4)


def arbol(x, y, s=1.0):
    h = 4.5 * s
    G.caja("tronco", x - 0.12, y - 0.12, 0, x + 0.12, y + 0.12, h * 0.55)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=1.5 * s, location=(x, y, h * 0.75))
    ob = bpy.context.active_object
    ob.scale = (1.0, 1.0, 0.85)
    ob.data.materials.append(M["follaje"])
    bpy.ops.object.modifier_add(type="DISPLACE")
    tx = bpy.data.textures.new("ruido_follaje", "CLOUDS")
    tx.noise_scale = 0.6
    ob.modifiers["Displace"].texture = tx
    ob.modifiers["Displace"].strength = 0.5


for xa in ([F - 0.7] if F < 24 else [2 + k * 9 for k in range(int((F - 2) / 9) + 1)]):
    arbol(xa, -1.2, 0.9)
arbol(F * 0.25, Fo - 1.4, 1.1)
arbol(-6, Fo * 0.6, 1.3)
arbol(F + 6, Fo * 0.4, 1.2)
G.crear()

# ------------------------------------------------------------------ luz
W = bpy.data.worlds.new("Cielo")
SC.world = W
W.use_nodes = True
nt = W.node_tree
sky = nt.nodes.new("ShaderNodeTexSky")
sky.sky_type = "NISHITA"
sky.sun_elevation = math.radians(38)
sky.sun_rotation = math.radians(215)
sky.sun_size = math.radians(1.2)
bg = nt.nodes["Background"]
bg.inputs["Strength"].default_value = 0.22
nt.links.new(sky.outputs["Color"], bg.inputs["Color"])

for blq in E["bloques"]:
    for nv in blq["niveles"]:
        for c in nv["locales"]:
            if c["w"] * c["d"] < 2.0:
                continue
            L = bpy.data.lights.new(f"Luz {c['n']}", "AREA")
            L.shape = "RECTANGLE"
            L.size, L.size_y = c["w"] * 0.6, c["d"] * 0.6
            L.energy = 9 * c["w"] * c["d"]
            L.color = (1.0, 0.87, 0.72)
            ob = bpy.data.objects.new(L.name, L)
            ob.location = (c["x"] + c["w"] / 2, c["y"] + c["d"] / 2, nv["z"] + nv["h"] - nv["losa"] - 0.05)
            SC.collection.objects.link(ob)

# ------------------------------------------------------------------ render
SC.render.engine = "CYCLES"
SC.cycles.device = "CPU"
SC.cycles.use_denoising = True
SC.cycles.denoiser = "OPENIMAGEDENOISE"
SC.cycles.use_adaptive_sampling = True
SC.cycles.adaptive_threshold = 0.03
SC.cycles.max_bounces = 6
SC.cycles.caustics_reflective = False
SC.cycles.caustics_refractive = False
SC.view_settings.view_transform = "AgX"
SC.view_settings.look = "AgX - Medium High Contrast"
SC.render.use_persistent_data = True
SC.render.threads_mode = "AUTO"


def camara(nombre, pos, mira, lente=24):
    cd = bpy.data.cameras.new(nombre)
    cd.lens = lente
    cd.clip_start = 0.05
    cd.clip_end = 600
    ob = bpy.data.objects.new(nombre, cd)
    SC.collection.objects.link(ob)
    ob.location = pos
    d = Vector(mira) - Vector(pos)
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return ob


b0 = E["bloques"][0]
bx, by, bw, bd = b0["x"], b0["y"], b0["w"], b0["d"]
Ht = z_top_global
cen = (bx + bw / 2, by + bd / 2, Ht * 0.35)
R = max(bw, bd, Ht * 1.5)
vistas = [
    ("render_1_aereo", (bx + bw / 2 - R * 1.05, by - R * 1.25, Ht + R * 0.75), cen, 28),
    ("render_2_peatonal", (bx + bw * 0.75, by - max(9.0, bw * 0.95), 1.65), (bx + bw * 0.45, by + 1.0, Ht * 0.48), 22),
    ("render_3_posterior", (bx + bw + R * 0.6, by + bd + R * 0.9, Ht * 0.9 + 3), (bx + bw / 2, by + bd / 2, Ht * 0.4), 26),
]
# vista interior: desde el acceso hacia la zona social de planta baja
nv0 = b0["niveles"][0]
social = max((c for c in nv0["locales"] if c["t"] == "social"), key=lambda c: c["w"] * c["d"], default=None)
if social:
    vistas.append(("render_4_interior", (social["x"] + social["w"] * 0.85, social["y"] + 0.4, 1.5),
                   (social["x"] + social["w"] * 0.2, social["y"] + social["d"] * 0.9, 1.1), 16))

if "--sin-fotos" not in ARGS:
    SC.render.resolution_x, SC.render.resolution_y = (960, 600) if PRUEBA else (1600, 1000)
    SC.cycles.samples = 48 if PRUEBA else 128
    SC.cycles.time_limit = 60 if PRUEBA else 300
    SC.render.image_settings.file_format = "JPEG"
    SC.render.image_settings.quality = 90
    for nombre, pos, mira, lente in vistas:
        SC.camera = camara(nombre, pos, mira, lente)
        SC.render.filepath = os.path.join(SALIDA, nombre + ".jpg")
        t0 = time.time()
        bpy.ops.render.render(write_still=True)
        print(f"render: {nombre} {time.time() - t0:.0f} s", flush=True)


# ------------------------------------------------------------------ recorrido virtual
def ruta_interior():
    """Calle → acceso → recorrido por circulaciones y zona social/cocina de planta baja."""
    pe = next((v for v in nv0["vanos"] if v["tipo"] == "puerta_ext"), None)
    if not pe or not E["unifamiliar"]:
        return []
    px = (pe["a"] + pe["b"]) / 2
    pts = [(px, by - 9.0), (px, by - 2.5), (px, by - 0.6), (px, by + 0.8)]
    locales = nv0["locales"]

    def dentro(x, y):
        return next((c for c in locales if c["x"] - 1e-3 <= x <= c["x"] + c["w"] + 1e-3 and c["y"] - 1e-3 <= y <= c["y"] + c["d"] + 1e-3), None)
    actual = dentro(px, by + 0.8)
    visitados = {actual["n"]} if actual else set()
    prioridad = {"circ": 0, "social": 1, "cocina": 2}
    for _ in range(4):
        if not actual:
            break
        cands = []
        for v in nv0["vanos"]:
            if v["tipo"] not in ("vano", "puerta"):
                continue
            m = (v["a"] + v["b"]) / 2
            if v["eje"] == "h":
                if not (actual["x"] <= m <= actual["x"] + actual["w"]):
                    continue
                if abs(v["c"] - actual["y"]) < EPS:
                    nxt, q = (m, v["c"] - 0.7), (m, v["c"] + 0.7)
                elif abs(v["c"] - actual["y"] - actual["d"]) < EPS:
                    nxt, q = (m, v["c"] + 0.7), (m, v["c"] - 0.7)
                else:
                    continue
            else:
                if not (actual["y"] <= m <= actual["y"] + actual["d"]):
                    continue
                if abs(v["c"] - actual["x"]) < EPS:
                    nxt, q = (v["c"] - 0.7, m), (v["c"] + 0.7, m)
                elif abs(v["c"] - actual["x"] - actual["w"]) < EPS:
                    nxt, q = (v["c"] + 0.7, m), (v["c"] - 0.7, m)
                else:
                    continue
            sig = dentro(*nxt)
            if not sig or sig["n"] in visitados or sig["t"] not in prioridad:
                continue
            cands.append((prioridad[sig["t"]], q, nxt, sig))
        if not cands:
            break
        cands.sort(key=lambda t: t[0])
        _, q, nxt, sig = cands[0]
        pts += [q, nxt, (sig["x"] + sig["w"] / 2, sig["y"] + sig["d"] / 2)]
        visitados.add(sig["n"])
        actual = sig
    return pts


if "--sin-video" not in ARGS:
    fps = 24 if PRUEBA else 15
    vel = 1.1                         # m/s caminando
    pts = ruta_interior()
    cam = camara("Recorrido", (0, 0, 1.6), (0, 1, 1.6), 18)
    obj = bpy.data.objects.new("Objetivo", None)
    SC.collection.objects.link(obj)
    con = cam.constraints.new("TRACK_TO")
    con.target = obj
    con.track_axis = "TRACK_NEGATIVE_Z"
    con.up_axis = "UP_Y"
    f = 1
    claves = []
    if pts:
        for i, p in enumerate(pts):
            claves.append((f, (p[0], p[1], 1.6)))
            if i + 1 < len(pts):
                f += max(12, int(math.dist(p, pts[i + 1]) / vel * fps))
        for (fr, p), (fr2, p2) in zip(claves, claves[1:] + [claves[-1]]):
            cam.location = p
            cam.keyframe_insert("location", frame=fr)
            dx, dy = p2[0] - p[0], p2[1] - p[1]
            n = math.hypot(dx, dy) or 1
            obj.location = (p[0] + dx / n * 3, p[1] + dy / n * 3, 1.45)
            obj.keyframe_insert("location", frame=fr)
        # giro final para ver el espacio
        last = claves[-1][1]
        for k_, ang in enumerate((0, 120, 240)):
            fr = f + 1 + k_ * 36
            obj.location = (last[0] + 3 * math.cos(math.radians(ang + 90)), last[1] + 3 * math.sin(math.radians(ang + 90)), 1.4)
            obj.keyframe_insert("location", frame=fr)
            cam.location = last
            cam.keyframe_insert("location", frame=fr)
        f += 1 + 3 * 36
    # vuelo exterior alrededor del proyecto (corte a cámara aérea)
    aer = camara("Vuelo", cen, cen, 26)
    con2 = aer.constraints.new("TRACK_TO")
    obj2 = bpy.data.objects.new("Centro", None)
    obj2.location = cen
    SC.collection.objects.link(obj2)
    con2.target = obj2
    con2.track_axis = "TRACK_NEGATIVE_Z"
    con2.up_axis = "UP_Y"
    f0 = f + 1
    dur = 8 * fps
    for i in range(0, dur + 1, 12):
        a = math.radians(-120 + 160 * i / dur)
        aer.location = (cen[0] + R * 1.45 * math.cos(a), cen[1] + R * 1.45 * math.sin(a), Ht + R * 0.55)
        aer.keyframe_insert("location", frame=f0 + i)
    m1 = SC.timeline_markers.new("interior", frame=1)
    m1.camera = cam
    m2 = SC.timeline_markers.new("vuelo", frame=f0)
    m2.camera = aer
    SC.camera = cam if pts else aer
    SC.frame_start = 1 if pts else f0
    SC.frame_end = f0 + dur
    if PRUEBA:
        SC.frame_step = 6
    SC.render.fps = fps
    SC.render.resolution_x, SC.render.resolution_y = (640, 360) if PRUEBA else (960, 540)
    SC.cycles.samples = 8 if PRUEBA else 12
    SC.cycles.time_limit = 0
    SC.render.image_settings.file_format = "FFMPEG"
    SC.render.ffmpeg.format = "MPEG4"
    SC.render.ffmpeg.codec = "H264"
    SC.render.ffmpeg.constant_rate_factor = "MEDIUM"
    SC.render.filepath = os.path.join(SALIDA, "recorrido_virtual.mp4")
    print(f"recorrido: {SC.frame_end - SC.frame_start + 1} cuadros", flush=True)
    t0 = time.time()
    bpy.ops.render.render(animation=True)
    print(f"recorrido listo {time.time() - t0:.0f} s", flush=True)
