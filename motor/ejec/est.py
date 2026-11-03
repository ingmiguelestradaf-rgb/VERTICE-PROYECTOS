"""Proyecto estructural ejecutivo de vivienda de mampostería confinada (1 a 3 niveles).

Usa VERTICE-CALCULO (vertice.*) para cargas, sismo, método simplificado de mampostería, flexión,
cortante y zapatas. Este módulo extrae de las plantas la geometría real de muros, tableros y vanos.

Criterios:
- Muros de block 15x20x40 confinados (NTC Mampostería): castillos en extremos de paneles, intersecciones
  y a ≤ min(1.5H, 4 m); dalas en desplante, cerramiento y pretil.
- Un muro de planta alta que no tiene muro de carga debajo se especifica como muro divisorio ligero
  (tablaroca/durock); su peso está incluido en la carga de muros divisorios del entrepiso.
- Losas macizas perimetrales. Momentos por franjas en la dirección corta con coeficiente 1/10 (1/8 si el
  tablero no tiene bordes continuos), método conservador frente a la tabla de coeficientes de la NTC.
- Vanos ≥ 2.00 m: trabe de concreto diseñada; vanos menores: dala de cerramiento D-1.
"""
import math

EPS = 0.02
H_MURO_KG_M2 = 260.0           # block 15 cm con aplanado en ambas caras
Q_ADM = 12.0                   # t/m², SUPUESTO sin estudio de mecánica de suelos
DF = 0.80                      # m, profundidad de desplante
VM = None                      # se toma de vertice.mamposteria.VM_TIPICOS
SEP_MAX_CASTILLO = 4.0


# ------------------------------------------------------------------ geometría
def _merge(iv):
    iv = sorted(iv)
    out = []
    for a, b in iv:
        if out and a <= out[-1][1] + EPS:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out


def lineas(hojas):
    """Ejes de muro (unión de bordes de los locales). Regresa [{eje, c, a, b}]."""
    d = {}
    for r in hojas:
        x, y, w, h = r["x"], r["y"], r["w"], r["d"]
        d.setdefault(("h", round(y, 3)), []).append((x, x + w))
        d.setdefault(("h", round(y + h, 3)), []).append((x, x + w))
        d.setdefault(("v", round(x, 3)), []).append((y, y + h))
        d.setdefault(("v", round(x + w, 3)), []).append((y, y + h))
    out = []
    for (eje, c), iv in d.items():
        for a, b in _merge(iv):
            if b - a > 0.05:
                out.append(dict(eje=eje, c=c, a=round(a, 3), b=round(b, 3)))
    return out


def _sobre(v, ln):
    return v["eje"] == ln["eje"] and abs(v["c"] - ln["c"]) < EPS and v["b"] > ln["a"] and v["a"] < ln["b"]


def paneles(ln, vanos):
    """Tramos macizos de una línea de muro (descuenta todos los vanos)."""
    hs = sorted((max(ln["a"], v["a"]), min(ln["b"], v["b"])) for v in vanos if _sobre(v, ln))
    out, cur = [], ln["a"]
    for a, b in hs:
        if a > cur + 0.01:
            out.append((cur, a))
        cur = max(cur, b)
    if ln["b"] > cur + 0.01:
        out.append((cur, ln["b"]))
    return out


def cobertura(ln, otras):
    """Fracción de la línea `ln` que tiene debajo una línea de `otras`."""
    tot = 0.0
    for o in otras:
        if o["eje"] == ln["eje"] and abs(o["c"] - ln["c"]) < EPS:
            tot += max(0.0, min(o["b"], ln["b"]) - max(o["a"], ln["a"]))
    return tot / max(ln["b"] - ln["a"], 1e-6)


def _comparte(r, s):
    """Borde compartido entre rectángulos: (eje, c, a, b) o None."""
    for ya, yb in ((r["y"] + r["d"], s["y"]), (r["y"], s["y"] + s["d"])):
        if abs(ya - yb) < EPS:
            a, b = max(r["x"], s["x"]), min(r["x"] + r["w"], s["x"] + s["w"])
            if b - a > 0.3:
                return ("h", ya, a, b)
    for xa, xb in ((r["x"] + r["w"], s["x"]), (r["x"], s["x"] + s["w"])):
        if abs(xa - xb) < EPS:
            a, b = max(r["y"], s["y"]), min(r["y"] + r["d"], s["y"] + s["d"])
            if b - a > 0.3:
                return ("v", xa, a, b)
    return None


def tableros(hojas, estructurales, excluir=()):
    """Tableros de losa: locales unidos a través de muros no estructurales (envolvente rectangular)."""
    rs = [dict(x=r["x"], y=r["y"], w=r["w"], d=r["d"], n=[r["n"]]) for r in hojas if r["n"] not in excluir]
    cambio = True
    while cambio:
        cambio = False
        for i in range(len(rs)):
            for j in range(i + 1, len(rs)):
                sh = _comparte(rs[i], rs[j])
                if not sh:
                    continue
                eje, c, a, b = sh
                seg = dict(eje=eje, c=c, a=a, b=b)
                if cobertura(seg, estructurales) < 0.9:
                    p, q = rs[i], rs[j]
                    x0, y0 = min(p["x"], q["x"]), min(p["y"], q["y"])
                    x1, y1 = max(p["x"] + p["w"], q["x"] + q["w"]), max(p["y"] + p["d"], q["y"] + q["d"])
                    rs[i] = dict(x=x0, y=y0, w=x1 - x0, d=y1 - y0, n=p["n"] + q["n"])
                    rs.pop(j)
                    cambio = True
                    break
            if cambio:
                break
    for t in rs:
        t["a1"], t["a2"] = min(t["w"], t["d"]), max(t["w"], t["d"])
    return rs


def _bordes(t):
    return [("h", t["y"], t["x"], t["x"] + t["w"]), ("h", t["y"] + t["d"], t["x"], t["x"] + t["w"]),
            ("v", t["x"], t["y"], t["y"] + t["d"]), ("v", t["x"] + t["w"], t["y"], t["y"] + t["d"])]


def partir(ts, lineas_apoyo):
    """Divide tableros atravesados de lado a lado por una línea de apoyo (trabe)."""
    out = list(ts)
    for ln in lineas_apoyo:
        nuevos = []
        for t in out:
            if ln["eje"] == "v" and t["x"] + 0.3 < ln["c"] < t["x"] + t["w"] - 0.3 and ln["a"] <= t["y"] + EPS and ln["b"] >= t["y"] + t["d"] - EPS:
                izq = dict(t, w=ln["c"] - t["x"], n=[n + " (izq.)" for n in t["n"]])
                der = dict(t, x=ln["c"], w=t["x"] + t["w"] - ln["c"], n=[n + " (der.)" for n in t["n"]])
                nuevos += [izq, der]
            elif ln["eje"] == "h" and t["y"] + 0.3 < ln["c"] < t["y"] + t["d"] - 0.3 and ln["a"] <= t["x"] + EPS and ln["b"] >= t["x"] + t["w"] - EPS:
                inf = dict(t, d=ln["c"] - t["y"], n=[n + " (inf.)" for n in t["n"]])
                sup = dict(t, y=ln["c"], d=t["y"] + t["d"] - ln["c"], n=[n + " (sup.)" for n in t["n"]])
                nuevos += [inf, sup]
            else:
                nuevos.append(t)
        out = nuevos
    for t in out:
        t["a1"], t["a2"] = min(t["w"], t["d"]), max(t["w"], t["d"])
    return out


def tributaria(tab, ln):
    """Área (m²) que el tablero entrega a la línea de muro por el método de los sobres (45°)."""
    a1, a2 = tab["a1"], tab["a2"]
    lados = [("h", tab["y"], tab["x"], tab["x"] + tab["w"], tab["w"]), ("h", tab["y"] + tab["d"], tab["x"], tab["x"] + tab["w"], tab["w"]),
             ("v", tab["x"], tab["y"], tab["y"] + tab["d"], tab["d"]), ("v", tab["x"] + tab["w"], tab["y"], tab["y"] + tab["d"], tab["d"])]
    area = 0.0
    for eje, c, a, b, L in lados:
        if eje != ln["eje"] or abs(c - ln["c"]) > EPS:
            continue
        sol = max(0.0, min(b, ln["b"]) - max(a, ln["a"]))
        if sol <= 0:
            continue
        if abs(L - a1) < 1e-6:
            A = a1 * a1 / 4
        else:
            A = (a2 + (a2 - a1)) * (a1 / 2) / 2
        area += A * sol / L
    return area


def castillos(lns, vanos, H):
    pts = []
    sep = min(1.5 * H, SEP_MAX_CASTILLO)

    def P(ln, t):
        return (round(t, 3), round(ln["c"], 3)) if ln["eje"] == "h" else (round(ln["c"], 3), round(t, 3))
    for ln in lns:
        for a, b in paneles(ln, vanos):
            if b - a < 0.25:
                continue
            n = max(1, math.ceil((b - a) / sep - 1e-6))
            for k in range(n + 1):
                pts.append(P(ln, a + (b - a) * k / n))
    # intersecciones
    hs = [l for l in lns if l["eje"] == "h"]
    vs = [l for l in lns if l["eje"] == "v"]
    for h in hs:
        for v in vs:
            if h["a"] - EPS <= v["c"] <= h["b"] + EPS and v["a"] - EPS <= h["c"] <= v["b"] + EPS:
                pts.append((round(v["c"], 3), round(h["c"], 3)))
    out = []
    for p in sorted(pts):
        if all(math.dist(p, q) > 0.30 for q in out):
            out.append(p)
    return out


# ------------------------------------------------------------------ cálculo
def calcular(V, blq, lays, t_x=15, t_y=15):
    """V: módulo vertice. lays: [(cuartos, vanos)] por nivel (PB, PA...). Regresa dict con todo el diseño."""
    from vertice import cargas as K, sismo as S, mamposteria as M, concreto as C, cimentacion as Z
    from vertice.materiales import Concreto, Acero, VARILLAS
    conc, acero = Concreto(250), Acero(4200)
    niveles = blq["niveles"]
    hojas = [[c for c in cu if not c["contenedor"]] for cu, _ in lays]
    vanos = [va for _, va in lays]
    L = [lineas(h) for h in hojas]
    H = niveles[0]["h"]
    # estructuralidad de muros por nivel (nivel 0 todos; superiores si tienen muro debajo)
    tcarga = [dict(t, tipo="trabe") for t in blq.get("trabes_carga", [])]
    apoyo_tr = [[t for t in tcarga if t["nivel"] == k] for k in range(len(L))]
    estr = [L[0]]
    ligeros = []
    for k in range(1, len(L)):
        ok, no = [], []
        for ln in L[k]:
            (ok if cobertura(ln, estr[k - 1] + apoyo_tr[k - 1]) >= 0.9 else no).append(ln)
        estr.append(ok)
        ligeros.append(no)
    # tableros: entrepisos sobre nivel k (k < último) y azotea sobre último
    escalera = {c["n"] for c in hojas[0] if c["t"] == "escalera"}
    tabs = []
    for k in range(len(L)):
        excl = escalera if k < len(L) - 1 else ()
        tabs.append(partir(tableros(hojas[k], estr[k] + apoyo_tr[k], excl), apoyo_tr[k]))

    # ---- cargas
    ent = K.entrepiso_tipico(0.12)
    azo = K.azotea_tipica(0.12)
    cv_ent, cv_azo = K.CARGAS_VIVAS["habitacion"], K.CARGAS_VIVAS["azotea_pendiente_hasta_5pct"]
    w_ent = K.combinaciones_ntc(ent.carga_muerta, cv_ent[0], cv_ent[1])["envolvente"]
    w_azo = K.combinaciones_ntc(azo.carga_muerta, cv_azo[0], cv_azo[1])["envolvente"]

    # ---- losas
    def disenar_losa(ts, wu, nombre):
        filas = []
        hmax = 10.0
        w_serv = wu / 1.4
        k_ntc = 0.032 * (2520 * w_serv) ** 0.25 if w_serv > 380 else 1.0
        for t in ts:
            per = 0.0
            for eje, c, a, b in _bordes(t):
                cont = any(o is not t and _comparte(t, o) and _comparte(t, o)[1] == c for o in ts)
                per += (b - a) * (1.0 if cont else 1.25)
            dmin = k_ntc * per * 100 / 250
            if t["a2"] / t["a1"] > 2.0:            # trabaja en una dirección (ACI 7.3.1.1)
                dmin = C.espesor_min_losa_una_direccion(t["a1"] * 100, "ambos_continuos") - 2.5
            t["h_ntc"] = round(dmin + 2.5, 1)
            hmax = max(hmax, dmin + 2.5)
        h = max(10, math.ceil(hmax))
        d = h - 2.0 - VARILLAS[3][0] / 2
        smin = 30
        for t in ts:
            cont = sum(1 for o in ts if o is not t and _comparte(t, o))
            coef = 10 if cont else 8
            a1 = t["a1"]
            Mu = wu * a1 ** 2 / coef            # kg·m por metro
            Mneg = wu * a1 ** 2 / 10 if cont else wu * a1 ** 2 / 24
            fl = C.flexion_rectangular(Mu * 100, 100, d, conc, acero)
            fn = C.flexion_rectangular(Mneg * 100, 100, d, conc, acero)
            As_t = C.acero_temperatura(100, h)
            As_p = max(fl.As_diseno, As_t)
            As_n = max(fn.As_diseno, As_t)
            s_p = C.separacion_losa(As_p, 3, h)
            s_n = C.separacion_losa(As_n, 3, h)
            smin = min(smin, s_p, s_n)
            s_t = min(30, max(10, int(min(s_p, s_n) // 5 * 5)))
            t["s"] = s_t
            filas.append(dict(tablero="+".join(t["n"]), a1=round(a1, 2), a2=round(t["a2"], 2), Mu=round(Mu, 1),
                              Mneg=round(Mneg, 1), As_p=round(As_p, 2), As_n=round(As_n, 2), s_p=s_p, s_n=s_n, s=s_t))
        s = max(f["s"] for f in filas)
        return dict(nombre=nombre, h=h, wu=round(wu), d=round(d, 2), s=s, filas=filas,
                    armado=f"#3 en ambos sentidos en lecho inferior con la separación indicada por tablero (general @ {s} cm); "
                           f"bastones #3 a la misma separación en lecho superior sobre apoyos continuos, longitud ln/4 a cada lado")
    losas = []
    for k in range(len(L)):
        ultimo = k == len(L) - 1
        losas.append(disenar_losa(tabs[k], w_azo if ultimo else w_ent, "Azotea" if ultimo else
                                  ("Entrepiso" if len(L) == 2 else f"Entrepiso N{k + 1}")))

    # ---- cargas por línea de muro (servicio, kg) del nivel 0
    cm_e, cm_a = ent.carga_muerta, azo.carga_muerta
    def carga_linea(ln0):
        P = 0.0
        for k in range(len(L)):
            ultimo = k == len(L) - 1
            q = (cm_a + cv_azo[0]) if ultimo else (cm_e + cv_ent[0])
            # la carga del tablero baja por el muro estructural del nivel k que coincide con ln0
            for t in tabs[k]:
                for lk in estr[k]:
                    if lk["eje"] == ln0["eje"] and abs(lk["c"] - ln0["c"]) < EPS and cobertura(lk, [ln0]) > 0.0:
                        P += tributaria(t, dict(lk, a=max(lk["a"], ln0["a"]), b=min(lk["b"], ln0["b"]))) * q
            # peso propio de muros del nivel k sobre esta línea
            for lk in estr[k]:
                if lk["eje"] == ln0["eje"] and abs(lk["c"] - ln0["c"]) < EPS:
                    a, b = max(lk["a"], ln0["a"]), min(lk["b"], ln0["b"])
                    if b > a:
                        maciza = sum(max(0, min(pb, b) - max(pa, a)) for pa, pb in paneles(lk, vanos[k]))
                        P += maciza * niveles[k]["h"] * H_MURO_KG_M2
        return P
    cargas_lin = []
    for ln in L[0]:
        P = carga_linea(ln)
        Lm = ln["b"] - ln["a"]
        cargas_lin.append(dict(ln, P=P, w=P / Lm / 1000))

    # ---- sismo
    area_p = blq["w"] * blq["d"]
    pesos = []
    for k in range(len(L)):
        ultimo = k == len(L) - 1
        sist, cv = (azo, cv_azo) if ultimo else (ent, cv_ent)
        muros_kg = sum(sum(b - a for a, b in paneles(ln, vanos[k])) for ln in estr[k]) * niveles[k]["h"] * H_MURO_KG_M2
        W = (sist.carga_muerta + cv[1]) * area_p + muros_kg * (0.5 if ultimo else 1.0)
        if k + 1 < len(L):
            W += sum(sum(b - a for a, b in paneles(ln, vanos[k + 1])) for ln in estr[k + 1]) * niveles[k + 1]["h"] * H_MURO_KG_M2 * 0.5
        pesos.append(W / 1000)
    alt = 0.0
    nivs = []
    for k in range(len(L)):
        alt += niveles[k]["h"]
        nivs.append(S.Nivel("Azotea" if k == len(L) - 1 else f"Entrepiso {k + 1}", pesos[k], alt, niveles[k]["h"]))
    # SUPUESTO: forma espectral tipo PRODISIS para terreno tipo II en Tijuana (sustituir por la del sitio)
    esp = S.Espectro.cfe_parametrico(a0=0.22, c=0.60, Ta=0.10, Tb=0.60, k=1.5, r=0.5, Q=1.5, R0=2.0)
    sis = S.metodo_estatico(nivs, esp, sistema="mamposteria")
    vm = M.VM_TIPICOS["block_concreto_hueco_mortero_I"]
    muros_m = []
    Wtot = sum(pesos)
    for cl in cargas_lin:
        for a, b in paneles(cl, vanos[0]):
            Lp = b - a
            if Lp < 0.5:
                continue
            P = cl["P"] * Lp / (cl["b"] - cl["a"])
            nombre = f"{'Y' if cl['eje'] == 'h' else 'X'}={cl['c']:.2f} [{a:.2f}-{b:.2f}]"
            tt = t_x if cl["eje"] == "h" else t_y
            muros_m.append(M.Muro(nombre, "X" if cl["eje"] == "h" else "Y", Lp * 100, tt, H * 100, P))
    simp = M.metodo_simplificado(muros_m, Wtot * 1000, sis.c_diseno, vm)

    # ---- revisión por carga vertical (NTC Mampostería: PR = FR·FE·(f*m·AT + ΣAs·fy))
    fm, FR = 20.0, 0.6
    vert = []
    for cl in cargas_lin:
        maciza = sum(b - a for a, b in paneles(cl, vanos[0])) or 1e-6
        if maciza / (cl["b"] - cl["a"]) < 0.4:
            vert.append(dict(linea=f"{'Y' if cl['eje'] == 'h' else 'X'}={cl['c']:.2f}", Pu=0, PR=0, cumple=True,
                             nota="Línea abierta: la carga la toman la trabe de borde y los castillos de apoyo"))
            continue
        Pu_m = 1.4 * cl["P"] / maciza                      # kg por metro de muro macizo
        FE = 0.7 if not _perimetral(cl, blq) else 0.6
        tt = t_x if cl["eje"] == "h" else t_y
        PR_m = FR * FE * fm * tt * 100
        vert.append(dict(linea=f"{'Y' if cl['eje'] == 'h' else 'X'}={cl['c']:.2f}", Pu=round(Pu_m), PR=round(PR_m),
                         cumple=Pu_m <= PR_m))

    # ---- trabes
    def disenar_trabe(Lt, w_serv, h_max=95):
        wu = 1.4 * w_serv
        h0 = max(30, math.ceil(Lt * 100 / 12 / 5) * 5)
        cands = sorted(((b_t, h_t) for b_t in (15, 20, 25, 30) for h_t in range(min(h0, h_max), h_max + 1, 5)), key=lambda q: (q[0] * q[1], q[1]))
        for b_t, h_t in cands:
            dd = h_t - 4 - 0.8 - 0.8
            wpp = h_t / 100 * b_t / 100 * 2.4 * 1.3
            Mu = (wu + wpp) * Lt ** 2 / 8
            Vu = (wu + wpp) * Lt / 2
            fl = C.flexion_rectangular(Mu * 1e5, b_t, dd, conc, acero)
            if fl.As_diseno != fl.As_diseno:
                continue
            pv = C.proponer_varillas(fl.As_diseno, opciones=(3, 4, 5, 6), b=b_t, estribo=2.5)
            if not pv:
                continue
            co = C.cortante_viga(Vu * 1000, b_t, dd, Av_num=2.5)
            if co.cumple and co.s_diseno >= 7.5:
                return dict(L=round(Lt, 2), b=b_t, h=h_t, wu=round(wu + wpp, 2), Mu=round(Mu, 2), Vu=round(Vu, 2),
                            As=round(fl.As_diseno, 2), inf=pv["texto"], n_inf=pv["n"], num_inf=pv["num"],
                            sup="2 #3", s=max(7.5, min(co.s_diseno, dd / 2) // 2.5 * 2.5), R=round(Vu / 1.4, 2))
        raise ValueError(f"No se encontró sección de trabe para L={Lt:.2f} m, w={w_serv:.2f} t/m")
    trabes = []
    for t in tcarga:
        Lt = t["b"] - t["a"]
        P = 0.0
        for k in range(len(L)):
            ultimo = k == len(L) - 1
            q = (cm_a + cv_azo[0]) if ultimo else (cm_e + cv_ent[0])
            if k == t["nivel"]:
                for tb in tabs[k]:
                    P += tributaria(tb, t) * q
            if k > t["nivel"]:
                for lk in estr[k]:
                    if lk["eje"] == t["eje"] and abs(lk["c"] - t["c"]) < EPS:
                        seg = dict(lk, a=max(lk["a"], t["a"]), b=min(lk["b"], t["b"]))
                        if seg["b"] > seg["a"]:
                            P += sum(max(0, min(pb, seg["b"]) - max(pa, seg["a"])) for pa, pb in paneles(lk, vanos[k])) \
                                * niveles[k]["h"] * H_MURO_KG_M2
                            for tb in tabs[k]:
                                P += tributaria(tb, seg) * q
        d_ = disenar_trabe(Lt, P / Lt / 1000)
        trabes.append(dict(d_, clave=f"T-{len(trabes) + 1}", tipo="Trabe de carga", nivel=niveles[t["nivel"]]["nombre"],
                           vano="Bajo muro de planta alta", linea=t["eje"], c=t["c"], a=t["a"], bb=t["b"]))
    for k in range(len(L)):
        for v in vanos[k]:
            ancho = v["b"] - v["a"]
            if ancho < 2.0:
                continue
            ln = next((cl for cl in (cargas_lin if k == 0 else [dict(l, w=0.0) for l in estr[k]]) if _sobre(v, cl)), None)
            if ln is None:
                continue
            # la trabe no debe bajar del cabezal del vano (coordinación con arquitectura)
            cab = {"porton": 2.40, "ventana": 2.35, "vano": 2.30}.get(v["tipo"], 2.10)
            h_max = int((niveles[k]["h"] - cab) * 100 // 5 * 5)
            d_ = disenar_trabe(ancho + 0.15, max(ln.get("w", 0.0), 1.2), max(30, h_max))
            trabes.append(dict(d_, clave=f"T-{len(trabes) + 1}", tipo="Cerramiento", nivel=niveles[k]["nombre"],
                               vano=v["cuarto"], linea=v["eje"], c=v["c"], a=v["a"], bb=v["b"]))
    columnas = []
    for t in [x for x in trabes if x["tipo"] == "Trabe de carga"]:
        for yy in (t["a"], t["bb"]):
            columnas.append(dict(clave="C-1", x=t["c"], y=yy, b=15, h=30, armado="4 #4, E #2.5 @ 15 cm (@ 7.5 cm en 45 cm extremos)",
                                 P=t["R"]))

    # ---- escalera
    esc = None
    ce = next((c for c in hojas[0] if c["t"] == "escalera"), None)
    if ce:
        Llargo = max(ce["w"], ce["d"])
        desc = max(1.0, min(ce["w"], ce["d"]) / 2)
        run = Llargo - desc
        alto = H / 2
        n_pel = math.ceil(alto / 0.18)
        peralte = alto / n_pel
        huella = run / max(1, n_pel - 1)
        # regla de comodidad 2p + h ≤ 66 cm: la huella no se estira de más; el sobrante se va al descanso
        h_com = max(0.25, 0.64 - 2 * peralte)
        if huella > h_com:
            huella = h_com
            run = huella * max(1, n_pel - 1)
            desc = Llargo - run
        Lh = run + desc / 2
        h_e = max(10, math.ceil(Lh * 100 / 20))
        wu_e = 1.3 * (h_e / 100 * 2400 / math.cos(math.atan(alto / run)) + peralte / 2 * 2400 + 100) + 1.5 * 350
        Mu_e = wu_e * Lh ** 2 / 8
        de = h_e - 2.5
        fe = C.flexion_rectangular(Mu_e * 100, 100, de, conc, acero)
        s_e = C.separacion_losa(max(fe.As_diseno, C.acero_temperatura(100, h_e)), 3, h_e)
        esc = dict(ancho_tramo=round(min(ce["w"], ce["d"]) / 2, 2), run=round(run, 2), desc=round(desc, 2),
                   peldanos=n_pel, peralte=round(peralte * 100, 1), huella=round(huella * 100, 1), h=h_e,
                   Mu=round(Mu_e), s=max(10, int(s_e // 5 * 5)), Lh=round(Lh, 2),
                   cumple_peralte=peralte <= 0.18 + 1e-6, cumple_huella=huella >= 0.25 - 1e-6,
                   regla=round(2 * peralte * 100 + huella * 100, 1))

    # ---- cimentación
    perim = [cl for cl in cargas_lin if _perimetral(cl, blq)]
    inter = [cl for cl in cargas_lin if not _perimetral(cl, blq)]
    col = set(blq.get("colindancias", []))
    zaps = []
    for clave, grupo in (("ZC-1", perim), ("ZC-2", inter)):
        if not grupo:
            continue
        w = max(cl["w"] for cl in grupo)
        r = Z.zapata_corrida(w, 1.4 * w, 15, Q_ADM, Df=DF)
        zaps.append(dict(clave=clave, w=round(w, 2), B=r["B"], h=r["h"], q=round(r["q_serv"], 2),
                         armado=r["armado"], cumple=r["cumple"], As_m=round(r["As_m"], 2),
                         desc="Perimetral" if clave == "ZC-1" else "Interior"))
    lindero = []
    for cl in perim:
        lado = _lado(cl, blq)
        if lado in col:
            lindero.append(lado)
    zap_por_linea = {}
    for cl in cargas_lin:
        zc = zaps[0] if _perimetral(cl, blq) else (zaps[1] if len(zaps) > 1 else zaps[0])
        lado = _lado(cl, blq) if _perimetral(cl, blq) else None
        zap_por_linea[(cl["eje"], round(cl["c"], 3), cl["a"])] = dict(zc, lindero=lado in col if lado else False, lado=lado)

    # ---- castillos y cuantificación
    cast = [castillos(estr[k], vanos[k], niveles[k]["h"]) for k in range(len(L))]
    res = dict(ok=True, _hojas=hojas, lineas=L, estructurales=estr, ligeros=ligeros, tableros=tabs, losas=losas,
               cargas_lineas=cargas_lin, pesos=pesos, sismo=dict(T=round(sis.T, 3), c=round(sis.c_diseno, 4),
                                                                  V=round(sis.Vbase, 2),
                                                                  fuerzas=[(n, round(f, 2), round(v, 2)) for n, f, v in sis.fuerzas]),
               simplificado=[dict(dir=r.direccion, Vu=round(r.Vu), VR=round(r.VR), Aef=round(r.area_efectiva),
                                  cumple=r.cumple) for r in simp],
               vertical=vert, trabes=trabes, columnas=columnas, trabes_carga=tcarga, escalera=esc, zapatas=zaps, zap_linea=zap_por_linea,
               castillos=cast, lindero=sorted(set(lindero)), vm=vm, fm=fm, q_adm=Q_ADM, Df=DF, t_x=t_x, t_y=t_y,
               w_ent=round(w_ent), w_azo=round(w_azo), cm_ent=round(ent.carga_muerta), cm_azo=round(azo.carga_muerta),
               cv_ent=cv_ent, cv_azo=cv_azo, desglose_ent=ent.desglose(), desglose_azo=azo.desglose())
    res["cuantificacion"] = cuantificar(res, blq, niveles, vanos, VARILLAS)
    return res


def _perimetral(ln, blq):
    if ln["eje"] == "h":
        return abs(ln["c"] - blq["y"]) < EPS or abs(ln["c"] - (blq["y"] + blq["d"])) < EPS
    return abs(ln["c"] - blq["x"]) < EPS or abs(ln["c"] - (blq["x"] + blq["w"])) < EPS


def _lado(ln, blq):
    if ln["eje"] == "h":
        return "S" if abs(ln["c"] - blq["y"]) < EPS else "N"
    return "O" if abs(ln["c"] - blq["x"]) < EPS else "E"


def cuantificar(r, blq, niveles, vanos, VAR):
    """Volúmenes y acero por elemento (kg). Longitudes con traslapes y anclajes de obra."""
    kg = lambda num, m: VAR[num][2] * m
    filas = []
    n_lev = len(niveles)
    # castillos: 4#3 + E#2 @20 (@10 en 2 x 40 cm por nivel)
    for k in range(n_lev):
        n = len(r["castillos"][k])
        h = niveles[k]["h"]
        long_v = n * 4 * (h + 0.40 + (0.30 if k == 0 else 0))
        est = n * (h / 0.20 + 4) * 0.62
        filas.append(dict(elemento=f"Castillos K-1 15x20 ({niveles[k]['nombre']})", cantidad=n, unidad="pza",
                          longitud=round(n * h, 2), kg3=round(kg(3, long_v), 1), kg2=round(kg(2.5, est), 1), kg4=0.0,
                          concreto=round(n * h * 0.15 * 0.20, 3)))
    # dalas: desplante (nivel 0), cerramiento en cada nivel, pretil
    def largo(lns):
        return sum(l["b"] - l["a"] for l in lns)
    for etiqueta, lns in [("Dala de desplante D-1", r["estructurales"][0])] + \
            [(f"Dala de cerramiento D-1 ({niveles[k]['nombre']})", r["estructurales"][k]) for k in range(n_lev)] + \
            [("Dala de pretil D-2", [l for l in r["estructurales"][-1] if _perimetral(l, blq)])]:
        Lm = largo(lns) * 1.06
        filas.append(dict(elemento=etiqueta, cantidad=round(Lm, 2), unidad="ml", longitud=round(Lm, 2),
                          kg3=round(kg(3, 4 * Lm), 1), kg2=round(kg(2.5, Lm / 0.20 * 0.62), 1), kg4=0.0,
                          concreto=round(Lm * 0.15 * 0.20, 3)))
    # losas
    for ls, ts in zip(r["losas"], r["tableros"]):
        A = sum(t["w"] * t["d"] for t in ts)
        m_lecho = sum(2 * t["w"] * t["d"] / (t.get("s", ls["s"]) / 100) for t in ts) * 1.08
        bast = sum(_bastones(t, ts) / (t.get("s", ls["s"]) / 100) for t in ts)
        filas.append(dict(elemento=f"Losa {ls['nombre']} h={ls['h']} cm", cantidad=round(A, 2), unidad="m²",
                          longitud=0, kg3=round(kg(3, m_lecho + bast), 1), kg2=0.0, kg4=0.0,
                          concreto=round(A * ls["h"] / 100, 3)))
    # zapatas corridas
    for z in r["zapatas"]:
        lns = [cl for cl in r["cargas_lineas"] if (_perimetral(cl, blq) == (z["clave"] == "ZC-1"))]
        Lm = largo(lns)
        B = z["B"] / 100
        s = float(z["armado"].split("@")[1].split("cm")[0])
        transv = Lm / (s / 100) * (B - 0.10 + 0.30)
        filas.append(dict(elemento=f"Zapata corrida {z['clave']} B={z['B']:.0f} cm h={z['h']:.0f} cm", cantidad=round(Lm, 2),
                          unidad="ml", longitud=round(Lm, 2), kg3=round(kg(3, 4 * Lm * 1.06), 1), kg2=0.0,
                          kg4=round(kg(4, transv), 1), concreto=round(Lm * B * z["h"] / 100, 3)))
    # trabes
    for t in r["trabes"]:
        Lt = t["L"] + 0.30
        filas.append(dict(elemento=f"Trabe {t['clave']} {t['b']}x{t['h']}", cantidad=1, unidad="pza", longitud=Lt,
                          kg3=round(kg(3, 2 * Lt) + (kg(3, t['n_inf'] * Lt) if t['num_inf'] == 3 else 0), 1),
                          kg2=round(kg(2.5, Lt / (t["s"] / 100) * (2 * (t["b"] + t["h"]) / 100)), 1),
                          kg4=round(kg(t["num_inf"], t["n_inf"] * Lt) if t["num_inf"] != 3 else 0, 1),
                          concreto=round(Lt * t["b"] * t["h"] / 1e4, 3)))
    if r["escalera"]:
        e = r["escalera"]
        Lr = math.hypot(e["run"], 1.35) * 2 + e["desc"] * 2
        anch = e["ancho_tramo"]
        m = (anch / (e["s"] / 100)) * Lr + (Lr / 0.25) * anch * 2
        filas.append(dict(elemento=f"Escalera (rampas y descanso) h={e['h']} cm", cantidad=1, unidad="lote", longitud=round(Lr, 2),
                          kg3=round(kg(3, m), 1), kg2=0.0, kg4=0.0,
                          concreto=round(Lr * anch * e["h"] / 100 + e["peldanos"] * 2 * anch * 0.18 * 0.28 / 2, 3)))
    tot = dict(kg3=round(sum(f["kg3"] for f in filas), 1), kg2=round(sum(f["kg2"] for f in filas), 1),
               kg4=round(sum(f["kg4"] for f in filas), 1), concreto=round(sum(f["concreto"] for f in filas), 2))
    tot["kg"] = round(tot["kg3"] + tot["kg2"] + tot["kg4"], 1)
    return dict(filas=filas, total=tot)


def _bastones(t, ts):
    """Metros de bastón por metro de ancho: ln/4 a cada lado de cada borde continuo."""
    m = 0.0
    for o in ts:
        if o is t:
            continue
        sh = _comparte(t, o)
        if sh:
            m += (sh[3] - sh[2]) * 0 + t["a1"] / 4
    return m * (t["a2"])
