"""Instalaciones: cálculo preliminar y trazo esquemático en planta.

Disciplinas: hidráulica (IH), sanitaria y pluvial (IS), eléctrica (IE), gas LP (IG),
contra incendio (CI, en tipologías no habitacionales unifamiliares).
Supuestos de diseño documentados en cada tabla; verificar con CESPT, CFE, NOM-001-SEDE-2012,
NOM-004-SEDG-2004 y Reglamento de Edificaciones del Municipio de Tijuana.
"""
import math
from .dxf import ROJO, AMARILLO, VERDE, CIAN, AZUL, MAGENTA, NARANJA

DOTACION = dict(casa=("L/hab/día", 150), edificio=("L/hab/día", 150), nave=("L/trabajador/día", 100),
                plaza=("L/m²/día", 6), hotel=("L/huésped/día", 300), parque=("L/visitante/día", 30),
                museo=("L/visitante/día", 12))
W_M2 = dict(habitacional=25, oficinas=50, comercial=70, hotel=45, reunion=40, industrial=110)
DIAM = [13, 19, 25, 32, 38, 51, 64, 75, 100, 150, 200]
THW = [("14", 20), ("12", 25), ("10", 35), ("8", 50), ("6", 65), ("4", 85), ("2", 115), ("1/0", 150),
       ("2/0", 175), ("3/0", 200), ("4/0", 230), ("250", 255), ("350", 310), ("500", 380)]
TRAFOS = [45, 75, 112.5, 150, 225, 300, 500, 750, 1000, 1500, 2000, 2500]

HUMEDOS = ("humedo", "cocina")


def es_humedo(c):
    return (c["t"] in HUMEDOS or "Lavander" in c["n"] or "Cocineta" in c["n"] or "Regadera" in c["n"]
            or "Vestidores" in c["n"]) and not c["contenedor"]


def _diam(q_ls, v=1.5):
    d = math.sqrt(4 * q_ls / 1000 / (math.pi * v)) * 1000
    return next((x for x in DIAM if x >= d), DIAM[-1])


def diam_um(um):
    """Diámetro nominal (mm) por unidades mueble — criterio práctico de vivienda (CPVC/PPR, v ≤ 2 m/s)."""
    for lim, d in ((3, 13), (10, 19), (30, 25), (60, 32), (120, 38)):
        if um <= lim:
            return d
    return 51


def _hunter(um):
    return 0.19 * um ** 0.6 if um > 0 else 0


def _muebles(c):
    """(UM agua, UD descarga, # muebles) estimados por espacio húmedo."""
    n = c["n"]
    A = c["w"] * c["d"]
    if "Sanitarios" in n or "Vestidores" in n or "Regaderas" in n:
        m = max(2, int(A / 4))
        return 6 * m, 5 * m, m
    if "Medio" in n:
        return 4, 5, 2
    if "Baño" in n:
        return 6, 7, 3
    if "Cocina" in n and A > 25:
        return 12, 10, 6
    if "Cocina" in n or "Cocineta" in n:
        return 2, 2, 1
    if "Lavander" in n:
        return 4, 4, 2
    return 2, 2, 1


def calcular(proy, plan, lays, area_total):
    tip = plan["tipologia"]
    u = proy["usuarios"]
    unidad, dot = DOTACION[tip]
    if tip == "plaza":
        base = area_total
    elif tip in ("parque", "museo"):
        base = u.get("visitantes_dia", u["ocupantes"])
    else:
        base = u["ocupantes"]
    if tip == "parque" and "acuático" in proy.get("subtipo", ""):
        dot = 50
    D = base * dot                       # L/día
    Qm = D / 86400
    Qmd = 1.2 * Qm
    um = ud = muebles = 0
    for bi, blq in enumerate(proy["bloques"]):
        for k, n in enumerate(blq["niveles"]):
            for c in lays[bi][k][0]:
                if es_humedo(c):
                    a, b, m = _muebles(c)
                    um += a * n["rep"]; ud += b * n["rep"]; muebles += m * n["rep"]
    Qi = _hunter(um)
    ci = 0 if tip == "casa" else max(20.0, round(area_total * 5 / 1000, 1))
    cist = math.ceil(D * 2 / 1000 + ci)
    col = 100 if ud <= 180 else 150 if ud <= 700 else 200 if ud <= 1600 else 250
    # pluvial
    # área de captación en proyección horizontal: con cubierta inclinada incluye el alero (el canalón perimetral va en
    # su borde) y suma la marquesina sobre pilotis; antes sólo contaba el desplante y subestimaba el gasto pluvial
    techo = 0.0
    for b in proy["bloques"]:
        al = (b.get("cubierta_ligera") or {}).get("alero", 0.0)
        techo += (b["w"] + 2 * al) * (b["d"] + 2 * al)
        if b.get("pilotis"):
            techo += (b["pilotis"]["x1"] - b["pilotis"]["x0"]) * b["pilotis"]["fondo"]
    i_mm = 100
    Qp = techo * i_mm / 3600
    gr = techo > 1500
    cap = 13.0 if gr else 4.5
    n_baj = max(2 if tip == "casa" else 4, math.ceil(Qp / cap))
    # eléctrica
    carga = 0
    for blq in proy["bloques"]:
        A = blq["w"] * blq["d"] * sum(n["rep"] for n in blq["niveles"])
        carga += A * W_M2.get(blq["uso"], 40)
    if tip == "casa":
        carga += 3000
    if tip == "parque":
        carga += 250000 if "diversiones" in proy.get("subtipo", "") else 150000
    fd = 0.7 if tip == "casa" else 0.75
    kw = carga * fd / 1000
    kva = kw / 0.9
    if kw <= 5:
        acom, V, fases = "Monofásica 1F-2H 127 V", 127, 1
    elif kw <= 10:
        acom, V, fases = "Bifásica 2F-3H 220/127 V", 220, 2
    elif kva <= 75:
        acom, V, fases = "Trifásica 3F-4H 220/127 V en baja tensión", 220, 3
    else:
        tr = next((t for t in TRAFOS if t >= kva * 1.15), TRAFOS[-1])
        sec = "480/277 V" if tip == "nave" else "220/127 V"
        acom, V, fases = f"Media tensión 13.2 kV, subestación con transformador de {tr} kVA, {sec}", (480 if tip == "nave" else 220), 3
    I = kw * 1000 / ((math.sqrt(3) if fases == 3 else 1) * V * 0.9) if fases != 2 else kw * 1000 / (220 * 0.9)
    cal = next((c for c, a in THW if a >= I * 1.25), "en paralelo")
    if I * 1.25 > 380:
        nn = math.ceil(I * 1.25 / 380)
        cal = f"{nn} conductores por fase cal. 500 kcmil"
    else:
        cal = f"cal. {cal} AWG/kcmil"
    lum = sum(_luminarias(c, blq)[0] * n["rep"] for bi, blq in enumerate(proy["bloques"])
              for k, n in enumerate(blq["niveles"]) for c in lays[bi][k][0] if not c["contenedor"])
    # gas
    tanques = dict(casa="300 L" if plan.get("terreno", {}).get("area", 0) < 300 else "500 L",
                   edificio="5,000 L centralizado con medidor por departamento", nave="300 L (comedor)",
                   plaza="5,000 L para food court", hotel="5,000 L x 2 (cocina, lavandería, calentadores)",
                   parque="2,000 L (restaurante)", museo="500 L (cafetería)")
    res = dict(
        hidraulica=[("Dotación", f"{dot} {unidad} × {base:,.0f}", f"{D / 1000:,.1f} m³/día"),
                    ("Gasto medio / máx. diario", f"{Qm:.2f} / {Qmd:.2f} L/s", "Qmd = 1.2 Qm"),
                    ("Toma domiciliaria", f"Ø {max(13, _diam(Qmd, 1.0))} mm", "Contrato CESPT, medidor en límite de predio"),
                    ("Unidades mueble", f"{um} UM ({muebles} muebles)", f"Gasto instantáneo (Hunter) ≈ {Qi:.2f} L/s"),
                    ("Alimentación general", f"Ø {diam_um(um)} mm", "Tubería CPVC / PPR, diámetro por unidades mueble"),
                    ("Cisterna", f"{cist} m³", "2 días de reserva" + (f" + {ci} m³ contra incendio" if ci else "")),
                    ("Equipo de bombeo", "Hidroneumático / presurizador" if tip == "casa" else
                     "Equipo hidroneumático dúplex de velocidad variable", "Presión mínima 1.0 kg/cm² en mueble más desfavorable"),
                    ("Agua caliente", "Calentador de paso a gas" if tip in ("casa", "edificio") else "Caldera / calentadores de alta eficiencia",
                     "Retorno de agua caliente en recorridos > 15 m")],
        sanitaria=[("Unidades de descarga", f"{ud} UD", "Tabla de UD por mueble"),
                   ("Colector principal", f"Ø {col} mm PVC sanitario", "Pendiente mínima 2 %"),
                   ("Registros", "40x60 cm (60x80 en > 1.5 m de prof.)", "A cada 10 m y en cambios de dirección"),
                   ("Ventilación", "Tubo de ventilación Ø 50 mm por núcleo de muebles", "Rematar 30 cm sobre azotea"),
                   ("Descarga", "A colector municipal CESPT", "Trampa de grasas en cocinas comerciales" if tip != "casa" else "Registro de banqueta")],
        pluvial=[("Área de captación", f"{techo:,.0f} m²", f"Intensidad de diseño {i_mm} mm/h (supuesta)"),
                 ("Gasto pluvial", f"{Qp:.1f} L/s", "Q = i · A / 3600"),
                 ("Bajadas", f"{n_baj} de Ø {150 if gr else 100} mm", f"Capacidad ≈ {cap} L/s c/u"),
                 ("Disposición", "A pozo de absorción / área verde y excedencias a calle", "Separada del drenaje sanitario")],
        electrica=[("Carga instalada", f"{carga / 1000:,.1f} kW", "W/m² según uso + equipos"),
                   ("Demanda", f"{kw:,.1f} kW ({kva:,.1f} kVA)", f"Factor de demanda {fd}"),
                   ("Acometida", acom, f"Corriente ≈ {I:,.0f} A"),
                   ("Alimentador general", f"{cal} THW-LS, Cu", "Ampacidad al 125 %"),
                   ("Luminarias", f"≈ {lum:,} LED", "Niveles NOM-025-STPS / NOM-007-ENER"),
                   ("Tierra física", "Electrodo de cobre 3 m + registro", "Unión equipotencial, NOM-001-SEDE-2012"),
                   ("Energía renovable", f"Sistema FV interconectado ≈ {max(2, round(kw * 0.25)):,} kWp", "Opcional, recomendado")],
        gas=[("Combustible", "Gas LP", "NOM-004-SEDG-2004"),
             ("Almacenamiento", f"Tanque estacionario {tanques[tip]}", "En patio a nivel de piso (cubierta inclinada) o en azotea, ventilado, a > 3 m de flamas"),
             ("Red", "Cobre tipo L Ø 3/8\" a 3/4\" con regulador de 2 etapas", "Prueba de hermeticidad a 1.5× presión de trabajo")],
    )
    if ci:
        res["contra_incendio"] = [("Reserva", f"{ci} m³ exclusivos en cisterna", "Succión independiente"),
                                  ("Equipo", "Bomba eléctrica + bomba de combustión + jockey", "NFPA 20"),
                                  ("Gabinetes", "Hidrantes con manguera de 30 m a cada 30 m", "Más extintores PQS 6 kg @ 15 m"),
                                  ("Detección", "Detectores de humo y alarma audiovisual", "NOM-002-STPS-2010")]
    res["resumen"] = dict(D=D, cist=cist, um=um, ud=ud, kw=kw, kva=kva, n_baj=n_baj, col=col, ci=ci)
    return res


def punto_humedo(c, ox=0.0, oy=0.0):
    """Punto de alimentación / descarga del local húmedo: junto al muro oriente del local, a media
    profundidad. Las bajadas (BAN) corren dentro de ese muro o en un ducto adosado."""
    return (c["x"] + ox + c["w"] - 0.30, c["y"] + oy + c["d"] / 2)


def _luminarias(c, blq):
    A = c["w"] * c["d"]
    if c["t"] == "grande" or blq["sistema"] == "acero":
        sp = 8.0 if blq["sistema"] == "acero" else 5.0
    elif blq["uso"] == "habitacional":
        sp = 3.2
    else:
        sp = 4.5
    nx = max(1, round(c["w"] / sp))
    ny = max(1, round(c["d"] / sp))
    return nx * ny, nx, ny


# ------------------------------------------------------------- dibujo
def capas(dx):
    dx.capa("IH-AGUA-FRIA", AZUL); dx.capa("IH-AGUA-CALIENTE", ROJO, "DASHED"); dx.capa("IH-EQUIPOS", CIAN)
    dx.capa("IS-SANITARIA", 34); dx.capa("IS-REGISTROS", 34); dx.capa("IS-PLUVIAL", VERDE, "DASHED")
    dx.capa("IE-ALUMBRADO", AMARILLO); dx.capa("IE-CONTACTOS", MAGENTA); dx.capa("IE-CIRCUITOS", NARANJA, "DASHED")
    dx.capa("IE-TABLEROS", ROJO); dx.capa("IG-GAS", AMARILLO, "CENTER"); dx.capa("CI-INCENDIO", ROJO)
    dx.capa("I-TEXTO", VERDE)


def _L(dx, a, b, capa, primero="x"):
    """Ruta ortogonal a→b."""
    m = (b[0], a[1]) if primero == "x" else (a[0], b[1])
    dx.polilinea([a, m, b], capa)


def hidraulica(dx, proy, blq, cuartos, ox, oy, nivel_idx, primero_global):
    t = blq["x"] + ox + 0.45, blq["y"] + oy + 0.45
    hum = [c for c in cuartos if es_humedo(c)]
    if nivel_idx == 0:
        if primero_global:
            toma = (blq["x"] + ox + 0.6, oy)
            dx.rect(toma[0] - 0.3, toma[1] + 0.1, 0.6, 0.4, "IH-EQUIPOS")
            dx.texto((toma[0] + 0.5, toma[1] + 0.2), "MEDIDOR CESPT", 0.18, "I-TEXTO")
            cis = (blq["x"] + ox + 1.6, blq["y"] + oy + 1.4)
            dx.rect(cis[0] - 1.0, cis[1] - 0.8, 2.0, 1.6, "IH-EQUIPOS")
            dx.texto((cis[0] - 0.9, cis[1] - 0.2), "CISTERNA", 0.18, "I-TEXTO")
            dx.polilinea([toma, (toma[0], cis[1] - 0.8)], "IH-AGUA-FRIA")
            dx.circulo((cis[0] + 1.4, cis[1]), 0.3, "IH-EQUIPOS")
            dx.texto((cis[0] + 1.8, cis[1]), "HN", 0.18, "I-TEXTO")
            dx.linea((cis[0] + 1.1, cis[1]), t, "IH-AGUA-FRIA")
        else:
            dx.linea((t[0], blq["y"] + oy - 2.0), t, "IH-AGUA-FRIA")
    dx.circulo(t, 0.15, "IH-EQUIPOS")
    dx.texto((t[0] + 0.25, t[1] - 0.35), "SAF / SAC" if nivel_idx else "SAF", 0.18, "I-TEXTO")
    cal = next((c for c in cuartos if "Lavander" in c["n"] or "máquinas" in c["n"] or "Cocina" in c["n"]), None)
    calp = (cal["x"] + ox + 0.5, cal["y"] + oy + 0.5) if cal else None
    if calp and nivel_idx == 0:
        dx.circulo(calp, 0.25, "IH-EQUIPOS")
        dx.texto((calp[0] + 0.3, calp[1]), "CALENTADOR", 0.16, "I-TEXTO")
        _L(dx, t, calp, "IH-AGUA-FRIA")
    for c in hum:
        p = punto_humedo(c, ox, oy)
        _L(dx, t, p, "IH-AGUA-FRIA", "y")
        dx.circulo(p, 0.08, "IH-AGUA-FRIA")
        if (calp or nivel_idx) and ("Cocina" in c["n"] or "Baño" in c["n"] or "Regadera" in c["n"] or "Lavander" in c["n"] or "Vestidor" in c["n"]):
            q = (p[0] + 0.25, p[1] + 0.25)
            _L(dx, (t[0] + 0.25, t[1] + 0.25) if nivel_idx else calp, q, "IH-AGUA-CALIENTE", "x")
    # contra incendio
    if proy.get("_ci"):
        for c in cuartos:
            if c["t"] in ("circ", "grande") and not c["contenedor"]:
                n = max(1, int(max(c["w"], c["d"]) // 30))
                for k in range(n):
                    if c["w"] >= c["d"]:
                        p = (c["x"] + ox + c["w"] * (k + .5) / n, c["y"] + oy + 0.4)
                    else:
                        p = (c["x"] + ox + 0.4, c["y"] + oy + c["d"] * (k + .5) / n)
                    dx.rect(p[0] - 0.4, p[1] - 0.2, 0.8, 0.4, "CI-INCENDIO")
                    dx.texto((p[0] + 0.5, p[1]), "GCI", 0.2, "CI-INCENDIO")


def sanitaria(dx, proy, blq, cuartos, ox, oy, nivel_idx, superiores=()):
    """superiores: listas de cuartos de los niveles de arriba; en planta baja sus bajadas (BAN) se
    conectan al colector con su propio ramal."""
    hum = [c for c in cuartos if es_humedo(c)]
    col = set(blq.get("colindancias", []))
    xc = blq["x"] + ox + (blq["w"] - 0.6 if "E" in col else blq["w"] + 1.2)
    ypts = []
    for c in hum:
        p = punto_humedo(c, ox, oy)
        dx.circulo(p, 0.12, "IS-SANITARIA")
        dx.texto((p[0] + 0.2, p[1] + 0.2), "BAN Ø100" if nivel_idx else "Ø100", 0.15, "I-TEXTO")
        if nivel_idx == 0:
            dx.linea(p, (xc, p[1]), "IS-SANITARIA")
            ypts.append(p[1])
    if nivel_idx == 0:
        vistos = {(round(x_, 2), round(y_, 2)) for x_, y_ in (punto_humedo(c, ox, oy) for c in hum)}
        for cs in superiores:
            for c in cs:
                if not es_humedo(c):
                    continue
                p = punto_humedo(c, ox, oy)
                if (round(p[0], 2), round(p[1], 2)) in vistos:
                    continue
                vistos.add((round(p[0], 2), round(p[1], 2)))
                dx.circulo(p, 0.12, "IS-SANITARIA")
                dx.texto((p[0] + 0.2, p[1] + 0.2), "LLEGA BAN Ø100", 0.15, "I-TEXTO")
                dx.linea(p, (xc, p[1]), "IS-SANITARIA")
                ypts.append(p[1])
    if nivel_idx == 0 and ypts:
        ytop = max(ypts)
        y0 = oy
        dx.linea((xc, ytop), (xc, y0), "IS-SANITARIA")
        n = max(1, int((ytop - y0) // 10))
        regs = sorted(set([round(y, 2) for y in ypts] + [round(y0 + (ytop - y0) * k / n, 2) for k in range(n + 1)]))
        # ningún registro bajo la escalera: se recorre al paño libre más cercano (el ramal entra con "Y")
        escs = [c for c in cuartos if c["t"] == "escalera" and c["x"] + ox <= xc <= c["x"] + ox + c["w"]]
        def libre(y):
            for c in escs:
                ya, yb = c["y"] + oy, c["y"] + oy + c["d"]
                if ya - 0.25 < y < yb + 0.25:
                    return round(ya - 0.35 if y - ya < yb - y else yb + 0.35, 2)
            return y
        regs = sorted({libre(y) for y in regs})
        for y in regs:
            dx.rect(xc - 0.3, y - 0.2, 0.6, 0.4, "IS-REGISTROS")
        dx.texto((xc + 0.4, (ytop + y0) / 2), "COLECTOR PVC 2%", 0.2, "I-TEXTO", rot=90)
        dx.texto((xc + 0.4, y0 + 0.3), "A RED MUNICIPAL", 0.18, "I-TEXTO")


def puntos_bap(blq, n_baj, ox=0.0, oy=0.0, sur_primero=False):
    """Bajadas de agua pluvial de un bloque de vivienda: una sola fuente para A-04, IS-01 y la coordinación.
    Esquinas del lado bajo de la cubierta primero (norte por omisión; sur si la cubierta a una agua baja al frente)."""
    x, y, w, d = blq["x"] + ox, blq["y"] + oy, blq["w"], blq["d"]
    norte = [(x + 0.35, y + d - 0.35), (x + w - 0.35, y + d - 0.35)]
    sur = [(x + 0.35, y + 0.35), (x + w - 0.35, y + 0.35)]
    pts = sur + norte if sur_primero else norte + sur
    if n_baj > 4:
        pts.append((x + w / 2, (y + 0.35) if sur_primero else (y + d - 0.35)))
    return pts[:max(2, n_baj)]


def pluvial(dx, proy, blq, ox, oy, n_baj, pts=None):
    x, y, w, d = blq["x"] + ox, blq["y"] + oy, blq["w"], blq["d"]
    dx.rect(x, y, w, d, "IS-PLUVIAL")
    per = 2 * (w + d)
    n = max(2, n_baj // max(1, len(proy["bloques"])))
    if pts is not None:
        n = 0
    else:
        pts = []
    for k in range(n):
        s = per * (k + 0.5) / n
        if s < w:
            pts.append((x + s, y + 0.3))
        elif s < w + d:
            pts.append((x + w - 0.3, y + s - w))
        elif s < 2 * w + d:
            pts.append((x + w - (s - w - d), y + d - 0.3))
        else:
            pts.append((x + 0.3, y + d - (s - 2 * w - d)))
    cl = blq.get("cubierta_ligera")
    if cl:
        # cubierta inclinada: el agua baja por los faldones al canalón perimetral del alero y de ahí a las BAP
        # (antes se dibujaban pendientes de 2 % de azotea plana hacia el centro, contrario a A-04)
        al = cl["alero"]
        dx.rect(x - al, y - al, w + 2 * al, d + 2 * al, "IS-PLUVIAL")
        for p in pts:
            dx.circulo(p, 0.2, "IS-PLUVIAL")
        dx.texto((x + w / 2, y + d / 2 + 0.4), f"CUBIERTA INCLINADA {cl['pend'] * 100:.0f} %: CANALÓN PERIMETRAL A BAP",
                 max(0.2, w / 60), "I-TEXTO", centrado=True)
        return
    for p in pts:
        dx.circulo(p, 0.2, "IS-PLUVIAL")
        dx.linea(p, (x + w / 2, y + d / 2), "IS-PLUVIAL")
    dx.texto((x + w / 2, y + d / 2 + 0.4), "AZOTEA - PENDIENTES 2 % HACIA BAP", max(0.2, w / 60), "I-TEXTO", centrado=True)


def electrica(dx, proy, blq, cuartos, ox, oy, nivel_idx, primero_global):
    hojas = [c for c in cuartos if not c["contenedor"]]
    ent = min(hojas, key=lambda c: (c["y"], -c["x"]))
    tab = (ent["x"] + ox + ent["w"] - 0.4, ent["y"] + oy + 0.6)
    dx.rect(tab[0] - 0.25, tab[1] - 0.15, 0.5, 0.3, "IE-TABLEROS")
    dx.texto((tab[0] - 0.3, tab[1] + 0.25), "TABLERO" if nivel_idx == 0 else f"TAB. N{nivel_idx}", 0.18, "I-TEXTO")
    if nivel_idx == 0 and primero_global:
        med = (blq["x"] + ox + blq["w"] - 0.5, oy + 0.2)
        dx.rect(med[0] - 0.3, med[1], 0.6, 0.4, "IE-TABLEROS")
        dx.texto((med[0] - 2.2, med[1] + 0.1), "MEDICIÓN CFE", 0.18, "I-TEXTO")
        dx.linea((med[0], med[1] + 0.4), tab, "IE-CIRCUITOS")
    nlum = 0
    for c in hojas:
        n, nx, ny = _luminarias(c, blq)
        for i in range(nx):
            for j in range(ny):
                p = (c["x"] + ox + c["w"] * (i + .5) / nx, c["y"] + oy + c["d"] * (j + .5) / ny)
                r = 0.18 if blq["sistema"] != "acero" else 0.35
                dx.circulo(p, r, "IE-ALUMBRADO")
                dx.linea((p[0] - r, p[1] - r), (p[0] + r, p[1] + r), "IE-ALUMBRADO")
                dx.linea((p[0] - r, p[1] + r), (p[0] + r, p[1] - r), "IE-ALUMBRADO")
                nlum += 1
        cen = (c["x"] + ox + c["w"] / 2, c["y"] + oy + c["d"] / 2)
        if len(hojas) <= 80:
            dx.linea(tab, cen, "IE-CIRCUITOS")
        # contactos sobre el perímetro
        sep = 3.5 if blq["uso"] == "habitacional" else 6.0
        per = 2 * (c["w"] + c["d"])
        k = max(1, int(per // sep)) if c["t"] not in ("circ", "escalera") else 1
        for q in range(min(k, 24)):
            s = per * (q + 0.3) / k
            x0, y0 = c["x"] + ox, c["y"] + oy
            if s < c["w"]:
                p, a = (x0 + s, y0 + 0.2), 90
            elif s < c["w"] + c["d"]:
                p, a = (x0 + c["w"] - 0.2, y0 + s - c["w"]), 180
            elif s < 2 * c["w"] + c["d"]:
                p, a = (x0 + c["w"] - (s - c["w"] - c["d"]), y0 + c["d"] - 0.2), 270
            else:
                p, a = (x0 + 0.2, y0 + c["d"] - (s - 2 * c["w"] - c["d"])), 0
            dx.circulo(p, 0.1, "IE-CONTACTOS")
    return nlum


def tanque_gas(blq):
    """Ubicación del tanque estacionario: en patio si la cubierta es inclinada (blq["tanque_gas"]); si no, en azotea."""
    if blq.get("tanque_gas"):
        return tuple(blq["tanque_gas"])
    return (blq["x"] + blq["w"] - 1.2, blq["y"] + blq["d"] - 1.2)


def gas(dx, proy, blq, cuartos, ox, oy, nivel_idx, primero_global):
    coc = [c for c in cuartos if ("Cocina" in c["n"] or "Lavander" in c["n"] or "máquinas" in c["n"]
                                  or "Cocineta" in c["n"]) and not c["contenedor"]]
    if not coc:
        return
    t0 = tanque_gas(blq)
    tq = (t0[0] + ox, t0[1] + oy)
    patio = "tanque_gas" in blq
    if nivel_idx == 0 and primero_global:
        dx.circulo(tq, 0.6, "IG-GAS")
        dx.texto((tq[0] - 2.5, tq[1] + 0.8), "TANQUE ESTACIONARIO (PATIO, NPT ±0.00)" if patio else "TANQUE ESTACIONARIO (AZOTEA)",
                 0.18, "I-TEXTO")
    else:
        dx.circulo(tq, 0.12, "IG-GAS")
    for c in coc:
        p = (c["x"] + ox + c["w"] * 0.7, c["y"] + oy + c["d"] * 0.7)
        _L(dx, tq, p, "IG-GAS", "y")
        dx.rect(p[0] - 0.15, p[1] - 0.15, 0.3, 0.3, "IG-GAS")
        dx.texto((p[0] + 0.25, p[1]), "LLAVE DE PASO", 0.14, "I-TEXTO")
