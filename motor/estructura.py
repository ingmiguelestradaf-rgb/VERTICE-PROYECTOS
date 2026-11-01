"""Estructuración y predimensionamiento preliminar.

Criterios (anteproyecto; el diseño definitivo requiere análisis estructural
completo, estudio de mecánica de suelos y firma de DRO / corresponsable):
  - Combinación de carga última: 1.3 CM + 1.5 CV (NTC-Criterios 2017).
  - Columnas de concreto: Ag = Pu / (0.35 f'c), +15 % por control de desplazamientos.
  - Trabes: h = L/12 (continuas), b ≈ h/2.
  - Losa maciza perimetral: h = perímetro / 180 (NTC-Concreto). Claros ≥ 8 m → losa reticular h ≈ L/22.
  - Zapatas: A = P_serv · 1.10 / q_adm.
  - Cortante basal estático: V = (c / Q) · W  (c y Q son supuestos a confirmar con el
    espectro del sitio, MDOC-CFE 2015 / Reglamento de Edificaciones de Tijuana).
"""
import math

Q_ADM = {"default": 15.0, "mamposteria": 12.0}       # t/m² (supuesto)
C_SISMICO = 0.32                                     # supuesto zona Tijuana, suelo tipo II
CV = {"habitacional": 190, "oficinas": 250, "comercial": 350, "hotel": 190,
      "reunion": 350, "industrial": 500}             # kg/m² entrepiso (Wm)
CV_AZ = 100
IPR = [8, 10, 12, 14, 16, 18, 21, 24, 27, 30, 33, 36]


def up(x, m):
    return math.ceil(x / m - 1e-9) * m


def ejes(L, claro):
    n = max(1, math.ceil(L / claro - 1e-6))
    return [round(L * i / n, 3) for i in range(n + 1)]


def letras(n):
    s = "ABCDEFGHJKLMNPQRSTUVWXYZ"
    return [s[i] if i < len(s) else s[i // len(s) - 1] + s[i % len(s)] for i in range(n)]


def _muros(cuartos):
    segs = set()
    for c in cuartos:
        if c.get("contenedor") and c["t"] != "unidad":
            continue
        x, y, w, d = c["x"], c["y"], c["w"], c["d"]
        for s in (((x, y), (x + w, y)), ((x + w, y), (x + w, y + d)), ((x, y + d), (x + w, y + d)), ((x, y), (x, y + d))):
            a = tuple(round(v, 2) for v in s[0]); b = tuple(round(v, 2) for v in s[1])
            segs.add((min(a, b), max(a, b)))
    return sorted(segs)


def _castillos(segs, sep=3.5):
    pts = set()
    for a, b in segs:
        pts.add(a); pts.add(b)
        L = math.dist(a, b)
        n = int(L // sep)
        for k in range(1, n + 1):
            t = k / (n + 1)
            pts.add((round(a[0] + (b[0] - a[0]) * t, 2), round(a[1] + (b[1] - a[1]) * t, 2)))
    return sorted(pts)


def predimensionar(blq, niveles_lay, bloques):
    sistema = blq["sistema"]
    x0, y0, w, d = blq["x"], blq["y"], blq["w"], blq["d"]
    n_niv = sum(n["rep"] for n in blq["niveles"])
    # niveles de otro bloque bajo éste (torre sobre podio)
    extra = 0
    if blq.get("z0", 0) > 0:
        for o in bloques:
            if o is not blq and o.get("z0", 0) == 0 and o["x"] <= x0 + 0.1 and o["x"] + o["w"] >= x0 + w - 0.1:
                extra = sum(n["rep"] for n in o["niveles"])
    uso = blq["uso"]
    cv = CV.get(uso, 250)
    res = dict(sistema=sistema, niveles=n_niv, niveles_bajo=extra, tabla=[], notas=[], calc={})
    area_planta = w * d

    if sistema == "mamposteria":
        cuartos = niveles_lay[0][0]
        segs = _muros(cuartos)
        cast = _castillos(segs)
        mayor = max((c for c in cuartos if not c["contenedor"]), key=lambda c: c["w"] * c["d"])
        per = 2 * (mayor["w"] + mayor["d"])
        h_losa = max(10, up(per * 100 / 180, 1))
        cm = h_losa / 100 * 2400 + 150 + 40
        # carga lineal en muro de planta baja (ancho tributario ≈ 2.0 m)
        w_lin = n_niv * (2.0 * (cm + cv) / 1000 + 0.20 * 2.7 * 1.5)  # t/m (incluye muro de block)
        B = max(0.60, up(w_lin * 1.1 / Q_ADM["mamposteria"], 0.05))
        res.update(ejes_x=sorted({round(s[0][0] - x0, 2) for s in segs} | {round(s[1][0] - x0, 2) for s in segs}),
                   ejes_y=sorted({round(s[0][1] - y0, 2) for s in segs} | {round(s[1][1] - y0, 2) for s in segs}),
                   muros=segs, castillos=cast, zap_corrida=B, columnas=[], trabes=[], zapatas=[])
        W = n_niv * area_planta * (cm + 0.5 * cv) / 1000
        V = C_SISMICO / 2.0 * W
        res["calc"] = dict(h_losa_cm=h_losa, CM_kgm2=round(cm), CV_kgm2=cv, carga_lineal_tm=round(w_lin, 2),
                           ancho_zapata_m=B, q_adm_tm2=Q_ADM["mamposteria"], W_t=round(W, 1), Q=2.0,
                           c=C_SISMICO, V_basal_t=round(V, 1))
        res["tabla"] = [
            ("Muros", "Block hueco de concreto 15x20x40 cm, f'm ≥ 20 kg/cm², junteado con mortero tipo I", "Mampostería confinada"),
            ("Castillos K-1", "15x20 cm, 4 vars #3, est. #2 @ 20 cm (@10 en extremos)", f"{len(cast)} piezas en planta baja"),
            ("Dalas D-1", "15x20 cm, 4 vars #3, est. #2 @ 20 cm", "En desplante, cerramiento y pretil"),
            ("Losas", f"Losa maciza h = {h_losa} cm, f'c = 250 kg/cm², vars #3 @ 20 cm ambos sentidos", f"Claro crítico {mayor['n']}"),
            ("Cimentación", f"Zapata corrida de concreto f'c = 250, ancho {B:.2f} m, h = 20 cm, con contratrabe 20x40 cm",
             f"q_adm supuesta {Q_ADM['mamposteria']} t/m²"),
            ("Firme", "Concreto f'c = 150 kg/cm², h = 10 cm, malla 6x6-10/10", "Sobre terreno compactado 95 % Proctor"),
        ]
        return res

    if sistema == "acero":
        claro = w if w <= 48 else w / 2
        ex = [0.0, w] if w <= 48 else [0.0, w / 2, w]
        ey = ejes(d, blq["claro_max"])
        sy = d / (len(ey) - 1)
        H = max(n["h"] for n in blq["niveles"])
        marco_rigido = claro <= 30
        if marco_rigido:
            pr = next((p for p in IPR if p * 2.54 / 100 >= claro / 38), IPR[-1])
            viga = f'IPR {pr}" con cartelas en rodilla y cumbrera'
        else:
            per = up(claro / 15, 0.1)
            viga = f"Armadura de acero (ángulos LI / PTR), peralte {per:.1f} m"
            pr = next((p for p in IPR if p * 2.54 / 100 >= H / 22), IPR[-1])
        pc = next((p for p in IPR if p * 2.54 / 100 >= max(H / 25, min(claro, 30) / 45)), IPR[-1])
        w_cub = 35 + 25 + 40            # kg/m²: lámina+aislante, estructura, CV
        P = claro / 2 * sy * w_cub / 1000 + 1.5
        Az = P * 1.1 / Q_ADM["default"]
        Bz = max(1.5, up(math.sqrt(Az), 0.1))
        cols = [(x0 + x, y0 + y) for x in ex for y in ey]
        # columnas de fachada (cabezales) a cada ~8 m
        for y in (0.0, d):
            n = max(1, round(w / 8))
            for k in range(1, n):
                xx = w * k / n
                if all(abs(xx - e) > 1 for e in ex):
                    cols.append((x0 + xx, y0 + y))
        res.update(ejes_x=ex, ejes_y=ey, columnas=[(x, y, 0.40, 0.40) for x, y in cols],
                   trabes=[((x0, y0 + y), (x0 + w, y0 + y)) for y in ey],
                   zapatas=[(x, y, Bz) for x, y in cols], largueros=1.5)
        res["calc"] = dict(claro_m=round(claro, 2), crujia_m=round(sy, 2), altura_m=H, carga_cubierta_kgm2=w_cub,
                           P_columna_t=round(P, 1), zapata_m=Bz, q_adm_tm2=Q_ADM["default"])
        res["tabla"] = [
            ("Marcos transversales", viga, f"Claro {claro:.1f} m @ {sy:.2f} m"),
            ("Columnas", f'IPR {pc}" con placa base y 4 anclas Ø 1"', f"Altura libre {H:.1f} m"),
            ("Largueros", 'Polín monten 8" cal. 12 @ 1.50 m', "Con tensores de redondo Ø 1/2\" a tercios"),
            ("Contraventeo", 'Redondo Ø 3/4" en cruz en crujías extremas (cubierta y muros)', "Más puntal de PTR en cumbrera"),
            ("Cubierta", "Lámina KR-18 cal. 24 con aislante de fibra de vidrio 2\" y 10 % de láminas traslúcidas", "Pendiente 5 %"),
            ("Cimentación", f"Zapatas aisladas {Bz:.2f} x {Bz:.2f} m, h = 40 cm, dado 50x50 cm", f"q_adm supuesta {Q_ADM['default']} t/m²"),
            ("Firme", "Concreto MR 45 kg/cm², h = 18 cm, con fibra y juntas aserradas @ 4.5 m", "Para montacargas"),
        ]
        res["notas"].append("Revisar marcos por viento (Manual CFE-Viento 2020) y sismo; esbeltez y pandeo lateral de rafters.")
        return res

    # marcos de concreto
    ex = ejes(w, blq["claro_max"])
    ey = ejes(d, blq["claro_max"])
    sx, sy = w / (len(ex) - 1), d / (len(ey) - 1)
    L = max(sx, sy)
    if L >= 8:
        h_losa = up(L * 100 / 22, 5)
        tipo_losa = f"Losa reticular aligerada h = {h_losa} cm (casetón 60x60, nervaduras 15 cm)"
        w_losa = h_losa / 100 * 1400
    else:
        h_losa = max(10, up(2 * (sx + sy) * 100 / 180, 1))
        tipo_losa = f"Losa maciza perimetral h = {h_losa} cm"
        w_losa = h_losa / 100 * 2400
    cm = w_losa + 150 + 100 + 40
    total = n_niv + extra
    fc = 300 if total > 6 else 250
    A_t = sx * sy
    Ps = A_t * total * (cm + cv) / 1000
    Pu = A_t * total * (1.3 * cm + 1.5 * cv) / 1000
    Ag = Pu * 1000 / (0.35 * fc)
    bc = max(35 if total > 3 else 30, up(math.sqrt(Ag * 1.15), 5))
    ht = max(40, up(L * 100 / 12, 5))
    bt = max(25, up(ht / 2, 5))
    Az = Ps * 1.1 / Q_ADM["default"]
    Bz = up(math.sqrt(Az), 0.1)
    losa_cim = Bz > 0.7 * min(sx, sy)
    W = sum(area_planta * (cm + 0.5 * cv) / 1000 * n["rep"] for n in blq["niveles"])
    Q = 3.0
    V = C_SISMICO / Q * W
    cols = [(x0 + x, y0 + y, bc / 100, bc / 100) for x in ex for y in ey]
    trabes = [((x0, y0 + y), (x0 + w, y0 + y)) for y in ey] + [((x0 + x, y0), (x0 + x, y0 + d)) for x in ex]
    res.update(ejes_x=ex, ejes_y=ey, columnas=cols, trabes=trabes,
               zapatas=[] if losa_cim else [(x, y, Bz) for x, y, *_ in cols], losa_cim=losa_cim)
    res["calc"] = dict(claro_x=round(sx, 2), claro_y=round(sy, 2), area_trib_m2=round(A_t, 1), niveles=total,
                       CM_kgm2=round(cm), CV_kgm2=cv, P_serv_t=round(Ps, 1), Pu_t=round(Pu, 1), fc=fc,
                       columna_cm=bc, trabe_cm=f"{bt}x{ht}", losa_cm=h_losa, zapata_m=Bz,
                       q_adm_tm2=Q_ADM["default"], W_t=round(W, 1), Q=Q, c=C_SISMICO, V_basal_t=round(V, 1))
    cim = (f"Losa de cimentación con contratrabes {max(40, up(L*100/8,5)//2)}x{up(L*100/8,5)} cm "
           f"(zapatas aisladas calculadas de {Bz:.1f} m se traslapan) — evaluar pilas según estudio geotécnico"
           if losa_cim else f"Zapatas aisladas {Bz:.2f} x {Bz:.2f} m, h = {max(30, up(Bz*22,5)):.0f} cm, con contratrabes de liga")
    res["tabla"] = [
        ("Columnas C-1", f"{bc}x{bc} cm, f'c = {fc} kg/cm², fy = 4200 kg/cm²", f"Pu ≈ {Pu:.0f} t (interior)"),
        ("Trabes T-1", f"{bt}x{ht} cm, f'c = {fc} kg/cm²", f"Claro {L:.2f} m"),
        ("Losas", tipo_losa, f"Tablero {sx:.2f} x {sy:.2f} m"),
        ("Cimentación", cim, f"q_adm supuesta {Q_ADM['default']} t/m²"),
        ("Sistema sismorresistente", f"Marcos dúctiles de concreto, Q = {Q:.0f}", f"V basal ≈ {V:.0f} t ({V / W * 100:.1f} % W)"),
    ]
    if total > 8:
        res["tabla"].append(("Muros de cortante", "Núcleo de escaleras/elevadores en muros de concreto e = 25 cm",
                             "Control de distorsiones (≤ 0.015)"))
    if extra:
        res["notas"].append("Torre desplantada sobre podio: columnas continuas hasta cimentación; evitar transferencias.")
    return res
