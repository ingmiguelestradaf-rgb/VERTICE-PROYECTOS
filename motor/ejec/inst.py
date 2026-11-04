"""Instalaciones ejecutivas de vivienda: circuitos y cuadro de cargas (NOM-001-SEDE-2012), diagrama unifilar,
isométrico hidráulico con diámetros por ramal y cálculo de gas LP de referencia (NOM-004-SEDG-2004)."""
import math
from .. import instalaciones as I
from . import arq

W_LUM = 18          # W por luminaria LED
W_CONT = 180        # W por contacto (NOM-001-SEDE, 180 VA)
COS30, SEN30 = math.cos(math.radians(30)), 0.5


def contactos(c, blq):
    sep = 3.5 if blq["uso"] == "habitacional" else 6.0
    per = 2 * (c["w"] + c["d"])
    k = max(1, int(per // sep)) if c["t"] not in ("circ", "escalera") else 1
    return min(k, 24)


def circuitos(blq, lays):
    """Asigna circuitos por nivel y balancea fases (sistema 2F-3H 220/127 V)."""
    cs = []
    otros_cont = 0

    def nuevo(desc, tipo, lum=0, cont=0, otros=0, prot=15, cal="14"):
        cs.append(dict(desc=desc, tipo=tipo, lum=lum, cont=cont, otros=otros, prot=prot, cal=cal,
                       W=lum * W_LUM + cont * W_CONT + otros))
    for k, n in enumerate(blq["niveles"]):
        hojas = [c for c in lays[k][0] if not c["contenedor"]]
        lum = sum(I._luminarias(c, blq)[0] for c in hojas)
        grupos = math.ceil(lum / 14)
        for g in range(grupos):
            q = lum // grupos + (1 if g < lum % grupos else 0)
            nuevo(f"Alumbrado {n['nombre']}" + (f" ({g + 1})" if grupos > 1 else ""), "A", lum=q)
        gen = [c for c in hojas if c["t"] not in ("cocina", "humedo", "servicio")]
        cont = sum(contactos(c, blq) for c in gen)
        grupos = math.ceil(cont / 8)
        for g in range(grupos):
            q = cont // grupos + (1 if g < cont % grupos else 0)
            nuevo(f"Contactos {n['nombre']}" + (f" ({g + 1})" if grupos > 1 else ""), "C", cont=q, prot=20, cal="12")
        banos = [c for c in hojas if c["t"] == "humedo"]
        if banos:
            nuevo(f"Contactos baños {n['nombre']} (con protección GFCI)", "C", cont=len(banos), prot=20, cal="12")
    hojas_all = [c for k in range(len(lays)) for c in lays[k][0] if not c["contenedor"]]
    if any(c["t"] == "cocina" for c in hojas_all):
        nuevo("Cocina — pequeños aparatos 1", "K", otros=1500, prot=20, cal="12")
        nuevo("Cocina — pequeños aparatos 2 y refrigerador", "K", otros=1500, prot=20, cal="12")
    if any("Lavander" in c["n"] for c in hojas_all):
        nuevo("Lavandería (lavadora)", "L", otros=1500, prot=20, cal="12")
    nuevo("Equipo hidroneumático 1/2 HP", "M", otros=750, prot=20, cal="12")
    # balanceo de fases (mayor a menor, a la fase con menos carga)
    fa = fb = 0
    for i, c in enumerate(sorted(cs, key=lambda q: -q["W"])):
        if fa <= fb:
            c["fase"] = "A"; fa += c["W"]
        else:
            c["fase"] = "B"; fb += c["W"]
    for i, c in enumerate(cs):
        c["num"] = i + 1
    tot = fa + fb
    desb = abs(fa - fb) / max(fa, fb) * 100 if max(fa, fb) else 0
    dem = tot * 0.7
    I_dem = dem / (220 * 0.9)
    prot_g = next(p for p in (30, 40, 50, 60, 70, 100) if p >= I_dem * 1.25)
    cal_g = next(c for c, a in (("10", 35), ("8", 50), ("6", 65), ("4", 85), ("2", 115)) if a >= prot_g)
    return dict(circuitos=cs, total=tot, fase_a=fa, fase_b=fb, desbalance=round(desb, 1), demanda=round(dem),
                I=round(I_dem, 1), prot_general=prot_g, cal_general=cal_g,
                espacios=len(cs) + 2, tablero=f"Centro de carga 2F-3H 220/127 V de {max(8, math.ceil((len(cs) + 2) / 4) * 4)} espacios")


def cuadro_cargas(dx, x, y, cc, h=0.16):
    filas = []
    for c in cc["circuitos"]:
        filas.append([f"C-{c['num']}", c["desc"], c["lum"] or "", c["cont"] or "", c["otros"] or "", c["W"],
                      c["W"] if c["fase"] == "A" else "", c["W"] if c["fase"] == "B" else "",
                      f"1P-{c['prot']} A", f"2-{c['cal']} + 1-{c['cal']}d", "PVC 16 mm"])
    filas.append(["", "TOTAL", "", "", "", cc["total"], cc["fase_a"], cc["fase_b"], "", "", ""])
    yy = arq.tabla(dx, x, y, ["Circ.", "Descripción", f"Lum {W_LUM} W", f"Cont {W_CONT} W", "Otros W", "Total W",
                              "Fase A", "Fase B", "Protección", "Conductor THW-LS", "Tubería"],
                   filas, [0.9, 5.4, 1.1, 1.1, 1.0, 1.1, 1.0, 1.0, 1.3, 2.0, 1.3], h=h, titulo="CUADRO DE CARGAS")
    notas = [f"Carga instalada {cc['total']:,} W · factor de demanda 0.70 · demanda {cc['demanda']:,} W · I = {cc['I']} A",
             f"Interruptor general 2P-{cc['prot_general']} A · alimentador 2-{cc['cal_general']} + 1-{cc['cal_general']}N + 1-10d THW-LS Cu",
             f"Desbalance entre fases {cc['desbalance']} % (NOM-001-SEDE recomienda ≤ 5 %) · {cc['tablero']}",
             "Contactos en baños, cocina y exteriores con protección por falla a tierra (GFCI). Puesta a tierra con electrodo de 3 m."]
    for i, t in enumerate(notas):
        dx.texto((x, yy - 0.4 - i * 0.32), t, h * 0.95, "A-TABLA")
    return yy - 0.4 - len(notas) * 0.32


def unifilar(dx, x, y, cc):
    L = "IE-TABLEROS"
    dx.texto((x, y + 0.5), "DIAGRAMA UNIFILAR", 0.22, "I-TEXTO")
    dx.linea((x, y), (x, y - 0.8), L); dx.texto((x + 0.15, y - 0.3), "ACOMETIDA CFE 2F-3H 220/127 V", 0.13, "I-TEXTO")
    dx.circulo((x, y - 1.1), 0.3, L); dx.texto((x, y - 1.1), "M", 0.2, "I-TEXTO", centrado=True)
    dx.linea((x, y - 1.4), (x, y - 1.9), L)
    dx.rect(x - 0.3, y - 2.5, 0.6, 0.6, L); dx.texto((x + 0.45, y - 2.25), f"INT. GRAL. 2P-{cc['prot_general']} A", 0.13, "I-TEXTO")
    dx.linea((x, y - 2.5), (x, y - 3.0), L)
    n = len(cc["circuitos"])
    paso = 0.75
    xb0, xb1 = x - 0.2, x + paso * (n - 1) + 0.2
    dx.linea((xb0, y - 3.0), (xb1, y - 3.0), L); dx.linea((xb0, y - 3.05), (xb1, y - 3.05), L)
    dx.texto((xb1 + 0.2, y - 3.05), "TABLERO", 0.13, "I-TEXTO")
    for i, c in enumerate(cc["circuitos"]):
        xx = x + paso * i
        dx.linea((xx, y - 3.05), (xx, y - 3.6), L)
        dx.rect(xx - 0.1, y - 3.85, 0.2, 0.25, L)
        dx.linea((xx, y - 3.85), (xx, y - 4.5), L)
        dx.texto((xx, y - 4.6), f"C-{c['num']} {c['fase']}", 0.11, "I-TEXTO", rot=270)
        dx.texto((xx + 0.13, y - 4.6), f"1P-{c['prot']}A {c['W']} W", 0.1, "I-TEXTO", rot=270)
    dx.linea((x - 0.6, y - 1.6), (x - 1.2, y - 1.6), L); dx.linea((x - 1.2, y - 1.6), (x - 1.2, y - 2.1), L)
    for i in range(3):
        dx.linea((x - 1.2 - 0.25 + i * 0.08, y - 2.1 - i * 0.08), (x - 1.2 + 0.25 - i * 0.08, y - 2.1 - i * 0.08), L)
    dx.texto((x - 2.6, y - 2.45), "TIERRA FÍSICA", 0.11, "I-TEXTO")


def tag_circuitos(dx, blq, lays, cc, k, ox, oy):
    """Etiqueta en planta el circuito de alumbrado y de contactos de cada local."""
    n = blq["niveles"][k]["nombre"]
    ca = [c for c in cc["circuitos"] if c["tipo"] == "A" and n in c["desc"]]
    cg = [c for c in cc["circuitos"] if c["tipo"] == "C" and n in c["desc"] and "baños" not in c["desc"]]
    cb = next((c for c in cc["circuitos"] if "baños" in c["desc"] and n in c["desc"]), None)
    ck = [c for c in cc["circuitos"] if c["tipo"] == "K"]
    cl = next((c for c in cc["circuitos"] if c["tipo"] == "L"), None)
    hojas = [c for c in lays[k][0] if not c["contenedor"]]
    ia = ig = 0
    acum_a = acum_g = 0
    for c in hojas:
        la = I._luminarias(c, blq)[0]
        acum_a += la
        if ca and acum_a > ca[ia]["lum"] and ia < len(ca) - 1:
            ia += 1; acum_a = la
        txt = [f"C-{ca[ia]['num']}" if ca else ""]
        if c["t"] == "humedo" and cb:
            txt.append(f"C-{cb['num']}")
        elif c["t"] == "cocina" and ck:
            txt.append("/".join(f"C-{q['num']}" for q in ck))
        elif "Lavander" in c["n"] and cl:
            txt.append(f"C-{cl['num']}")
        elif cg:
            acum_g += contactos(c, blq)
            if acum_g > cg[ig]["cont"] and ig < len(cg) - 1:
                ig += 1; acum_g = contactos(c, blq)
            txt.append(f"C-{cg[ig]['num']}")
        dx.texto((c["x"] + ox + 0.15, c["y"] + oy + 0.15), " ".join(t for t in txt if t), 0.13, "IE-CIRCUITOS")
        # apagador junto a la puerta (lado interior)
        dx.texto((c["x"] + ox + c["w"] - 0.45, c["y"] + oy + c["d"] - 0.35), "S", 0.15, "IE-ALUMBRADO")


# ---------------------------------------------------------------- hidráulica
def iso(p):
    x, y, z = p
    return ((x - y) * COS30, (x + y) * SEN30 + z)


def _lin(dx, a, b, capa, ox, oy):
    pa, pb = iso(a), iso(b)
    dx.linea((pa[0] + ox, pa[1] + oy), (pb[0] + ox, pb[1] + oy), capa)


def isometrico_hidraulico(dx, blq, lays, ox, oy):
    """Isométrico de agua fría (y caliente desde el calentador) con diámetros por ramal (método de Hunter)."""
    x0, y0 = blq["x"], blq["y"]
    t = (x0 + 0.45, y0 + 0.45)
    cis = (x0 + 1.6, y0 + 1.4)
    h_acum = 0.0
    tramos = []
    um_tot = 0
    por_nivel = []
    for k, n in enumerate(blq["niveles"]):
        hum = [c for c in lays[k][0] if I.es_humedo(c)]
        um_n = sum(I._muebles(c)[0] for c in hum)
        por_nivel.append((h_acum, n["h"], hum, um_n))
        um_tot += um_n
        h_acum += n["h"]
    # cisterna -> hidroneumático -> columna
    z_red = 0.45
    _lin(dx, (cis[0], cis[1], -1.5), (cis[0], cis[1], 0.3), "IH-AGUA-FRIA", ox, oy)
    _lin(dx, (cis[0], cis[1], 0.3), (t[0], t[1], 0.3), "IH-AGUA-FRIA", ox, oy)
    pc = iso((cis[0], cis[1], -1.5))
    dx.texto((pc[0] + ox + 0.2, pc[1] + oy), "CISTERNA (SUCCIÓN)", 0.14, "I-TEXTO")
    ph = iso(((cis[0] + t[0]) / 2, (cis[1] + t[1]) / 2, 0.3))
    dx.circulo((ph[0] + ox, ph[1] + oy), 0.18, "IH-EQUIPOS"); dx.texto((ph[0] + ox + 0.25, ph[1] + oy), "HIDRONEUMÁTICO", 0.13, "I-TEXTO")
    d_gral = I.diam_um(um_tot)
    top = por_nivel[-1][0] + z_red
    _lin(dx, (t[0], t[1], 0.3), (t[0], t[1], top), "IH-AGUA-FRIA", ox, oy)
    pt = iso((t[0], t[1], top / 2))
    dx.texto((pt[0] + ox + 0.15, pt[1] + oy), f"COLUMNA AF Ø{d_gral} mm ({um_tot} UM)", 0.14, "I-TEXTO")
    for z0, h, hum, um_n in por_nivel:
        zr = z0 + z_red
        d_n = I.diam_um(um_n) if um_n else 13
        for c in hum:
            p = I.punto_humedo(c)
            um = I._muebles(c)[0]
            dd = I.diam_um(um)
            a, b, cc = (t[0], t[1], zr), (t[0], p[1], zr), (p[0], p[1], zr)
            _lin(dx, a, b, "IH-AGUA-FRIA", ox, oy); _lin(dx, b, cc, "IH-AGUA-FRIA", ox, oy)
            _lin(dx, cc, (p[0], p[1], zr + 0.6), "IH-AGUA-FRIA", ox, oy)
            q = iso((p[0], p[1], zr + 0.65))
            dx.circulo((q[0] + ox, q[1] + oy), 0.05, "IH-AGUA-FRIA")
            dx.texto((q[0] + ox + 0.1, q[1] + oy + 0.05), f"{c['n'].upper()} Ø{dd} ({um} UM)", 0.12, "I-TEXTO")
            if any(k_ in c["n"] for k_ in ("Baño", "Cocina", "Lavander", "Regadera")):
                off = 0.15
                _lin(dx, (t[0] + off, t[1], zr + 0.15), (t[0] + off, p[1] + off, zr + 0.15), "IH-AGUA-CALIENTE", ox, oy)
                _lin(dx, (t[0] + off, p[1] + off, zr + 0.15), (p[0] + off, p[1] + off, zr + 0.15), "IH-AGUA-CALIENTE", ox, oy)
        pz = iso((t[0], t[1], zr))
        dx.texto((pz[0] + ox - 3.0, pz[1] + oy), f"NIVEL +{z0:.2f} · ramal Ø{d_n}", 0.13, "I-TEXTO")
    dx.texto((ox - 2, oy - 3.0), "ISOMÉTRICO HIDRÁULICO (SIN ESCALA)  —  AF: azul continuo · AC: rojo discontinuo · tubería CPVC/PPR",
             0.16, "I-TEXTO")
    return d_gral


# ---------------------------------------------------------------- gas
APARATOS_GAS = [("Estufa con horno, 4 quemadores", 8600), ("Calentador de paso 16 L/min", 24000), ("Secadora de ropa", 5000)]
PCS_LP = 22400   # kcal/m³ de vapor de gas LP (referencia)


def gas_tabla(dx, x, y, patio=False):
    filas = []
    tot = 0
    for n, kcal in APARATOS_GAS:
        q = kcal / PCS_LP
        tot += q
        filas.append([n, f"{kcal:,}", f"{q:.2f}", "3/8\" (9.5 mm) cobre L"])
    filas.append(["TOTAL SIMULTÁNEO", "", f"{tot:.2f}", "Troncal 1/2\" (12.7 mm) cobre L"])
    yy = arq.tabla(dx, x, y, ["Aparato", "kcal/h (ref.)", "m³/h", "Diámetro"], filas, [4.6, 1.7, 1.2, 3.6], h=0.15,
                   titulo="CONSUMOS DE GAS LP (VALORES DE REFERENCIA)")
    notas = ["Consumos de referencia: verificar con la ficha técnica de los aparatos instalados.",
             "Regulador de 2 etapas; baja presión regulada 27.94 g/cm² (11\" c.a.). Llave de paso en cada aparato.",
             ("Tanque estacionario a nivel de patio sobre base de concreto, a cielo abierto, a ≥ 3 m de flamas, vanos y equipos eléctricos."
              if patio else "Tanque estacionario en azotea, ventilado, a ≥ 3 m de flamas y equipos eléctricos."),
             "Prueba de hermeticidad a 1.5 veces la presión de trabajo; dictamen de unidad de verificación (NOM-004-SEDG-2004)."]
    for i, t in enumerate(notas):
        dx.texto((x, yy - 0.35 - i * 0.28), t, 0.14, "A-TABLA")
    return tot


def isometrico_gas(dx, blq, lays, ox, oy):
    x0, y0 = blq["x"], blq["y"]
    from .. import instalaciones as INS
    tq = INS.tanque_gas(blq)
    ztop = sum(n["h"] for n in blq["niveles"]) if "tanque_gas" not in blq else 0.3
    pt = iso((tq[0], tq[1], ztop + 0.3))
    dx.circulo((pt[0] + ox, pt[1] + oy), 0.35, "IG-GAS"); dx.texto((pt[0] + ox + 0.45, pt[1] + oy), "TANQUE ESTACIONARIO + REGULADOR", 0.13, "I-TEXTO")
    _lin(dx, (tq[0], tq[1], ztop + 0.3), (tq[0], tq[1], 0.6), "IG-GAS", ox, oy)
    for c in [c for c in lays[0][0] if not c["contenedor"] and (c["t"] == "cocina" or "Lavander" in c["n"])]:
        p = (c["x"] + c["w"] * 0.7, c["y"] + c["d"] * 0.7)
        _lin(dx, (tq[0], tq[1], 0.6), (tq[0], p[1], 0.6), "IG-GAS", ox, oy)
        _lin(dx, (tq[0], p[1], 0.6), (p[0], p[1], 0.6), "IG-GAS", ox, oy)
        q = iso((p[0], p[1], 0.6))
        dx.rect(q[0] + ox - 0.08, q[1] + oy - 0.08, 0.16, 0.16, "IG-GAS")
        dx.texto((q[0] + ox + 0.15, q[1] + oy + 0.05), ("ESTUFA" if c["t"] == "cocina" else "CALENTADOR / SECADORA") + " — LLAVE DE PASO",
                 0.12, "I-TEXTO")
    dx.texto((ox - 2, oy - 2.5), "ISOMÉTRICO DE GAS LP (SIN ESCALA) — cobre tipo L", 0.15, "I-TEXTO")
