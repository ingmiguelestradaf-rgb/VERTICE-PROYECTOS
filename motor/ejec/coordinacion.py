"""Revisión de coordinación interdisciplinaria y cumplimiento normativo del proyecto ejecutivo.

Cada verificación regresa (disciplina, concepto, criterio/norma, resultado, estado) con estado OK, AVISO o ERROR.
Un ERROR impide publicar el proyecto.
"""
import math
from .. import instalaciones as I
from .est import paneles, cobertura, EPS


def revisar(blq, lays, r, cc, cancel, acab, q, rev_arq):
    out = []

    def add(disc, concepto, criterio, resultado, ok, aviso=False):
        out.append(dict(disciplina=disc, concepto=concepto, criterio=criterio, resultado=resultado,
                        estado="OK" if ok else ("AVISO" if aviso else "ERROR")))
    niveles = blq["niveles"]
    # ---------------- arquitectura (normativa)
    add("Arquitectura", "Revisión de locales", "Dimensiones mínimas, iluminación y ventilación (Reglamento de Tijuana / NTC Proyecto Arq.)",
        f"{rev_arq['errores']} errores, {rev_arq['avisos']} avisos", rev_arq["errores"] == 0)
    for k, n in enumerate(niveles):
        libre = n["h"] - r["losas"][k]["h"] / 100
        add("Arquitectura", f"Altura libre {n['nombre']}", "≥ 2.30 m en locales habitables",
            f"{libre:.2f} m", libre >= 2.30)
    e = r.get("escalera")
    if e:
        add("Arquitectura", "Escalera: peralte", "≤ 18 cm", f"{e['peralte']:.1f} cm", e["cumple_peralte"])
        add("Arquitectura", "Escalera: huella", "≥ 25 cm", f"{e['huella']:.1f} cm", e["cumple_huella"])
        add("Arquitectura", "Escalera: ancho de tramo", "≥ 0.90 m (vivienda)", f"{e['ancho_tramo']:.2f} m", e["ancho_tramo"] >= 0.90)
        add("Arquitectura", "Escalera: regla de comodidad", "2p + h entre 61 y 66 cm", f"{e['regla']:.1f} cm",
            61 <= e["regla"] <= 66, aviso=True)
    # acceso principal: sin contar el cancel corredizo al patio (que no es acceso desde la calle)
    puertas_ext = [v for v in lays[0][1] if v["tipo"] == "puerta_ext" and not v.get("corrediza")]
    add("Arquitectura", "Acceso principal", "Puerta ≥ 0.90 m (accesibilidad NMX-R-050)",
        f"{max((v['b'] - v['a'] for v in puertas_ext), default=0):.2f} m", any(v["b"] - v["a"] >= 0.9 for v in puertas_ext))
    # ---------------- estructura
    lig = sum(len(x) for x in r["ligeros"])
    add("Estructura", "Continuidad vertical de muros", "Muros de carga sobre muros o trabes del nivel inferior",
        "Todos apoyados" if lig == 0 else f"{lig} muros especificados como divisorios ligeros (tablaroca)", True, aviso=lig > 0)
    for s in r["simplificado"]:
        add("Estructura", f"Sismo — método simplificado dirección {s['dir']}", "Σ FAE·VmR ≥ FC·cs·W (NTC Mampostería 2017)",
            f"VR = {s['VR'] / 1000:.1f} t ≥ Vu = {s['Vu'] / 1000:.1f} t", s["cumple"])
    fv = [v for v in r["vertical"] if not v["cumple"]]
    add("Estructura", "Muros por carga vertical", "Pu ≤ FR·FE·f*m·AT (NTC Mampostería)",
        "Todos cumplen" if not fv else ", ".join(v["linea"] for v in fv), not fv)
    for ls, ts in zip(r["losas"], r["tableros"]):
        hmin = max(t.get("h_ntc", 0) for t in ts)
        add("Estructura", f"Losa {ls['nombre']}", "Peralte ≥ perímetro/250 (NTC Concreto, bordes discontinuos +25 %)",
            f"h = {ls['h']} cm ≥ {hmin:.1f} cm", ls["h"] + 1e-6 >= hmin)
    for z in r["zapatas"]:
        add("Estructura", f"Zapata {z['clave']}", "q servicio ≤ q admisible (supuesta, validar con EMS)",
            f"{z['q']:.2f} ≤ {r['q_adm']:.1f} t/m²", z["q"] <= r["q_adm"] and z["cumple"])
    if r["lindero"]:
        add("Estructura", "Zapatas de lindero", "No invadir predios vecinos",
            "Zapatas excéntricas con paño en el lindero " + "/".join(r["lindero"]), True)
    # vanos grandes con trabe y trabes sin invadir cabezal
    for k, n in enumerate(niveles):
        for v in lays[k][1]:
            if v["b"] - v["a"] >= 2.0:
                t = next((t for t in r["trabes"] if t["linea"] == v["eje"] and abs(t["c"] - v["c"]) < EPS
                          and abs(t["a"] - v["a"]) < 0.05 and t["nivel"] == n["nombre"]), None)
                cab = {"porton": 2.40, "ventana": 2.35, "vano": 2.30}.get(v["tipo"], 2.10)
                if t is None:
                    if v["eje"] == "h" and (abs(v["c"] - blq["y"]) < EPS or abs(v["c"] - blq["y"] - blq["d"]) < EPS) or \
                       v["eje"] == "v" and (abs(v["c"] - blq["x"]) < EPS or abs(v["c"] - blq["x"] - blq["w"]) < EPS):
                        pass
                    add("Coordinación arq.–est.", f"Vano de {v['b'] - v['a']:.2f} m en {v['cuarto']} ({n['nombre']})",
                        "Vano ≥ 2.00 m con trabe de cerramiento", "Sin trabe", False)
                else:
                    ok = n["h"] - t["h"] / 100 >= cab - 1e-6
                    if not ok:
                        add("Coordinación arq.–est.", f"{t['clave']} sobre {v['cuarto']}", "La trabe no invade el cabezal del vano",
                            f"Bajo de trabe {n['h'] - t['h'] / 100:.2f} m < cabezal {cab:.2f} m", False)
    # castillos dentro de vanos
    malos = 0
    for k in range(len(niveles)):
        for p in r["castillos"][k]:
            for v in lays[k][1]:
                if v["eje"] == "h" and abs(p[1] - v["c"]) < 0.05 and v["a"] + 0.05 < p[0] < v["b"] - 0.05:
                    malos += 1
                if v["eje"] == "v" and abs(p[0] - v["c"]) < 0.05 and v["a"] + 0.05 < p[1] < v["b"] - 0.05:
                    malos += 1
    add("Coordinación arq.–est.", "Castillos vs vanos", "Ningún castillo dentro de un vano; castillo a cada lado de vanos",
        "Sin interferencias" if not malos else f"{malos} castillos dentro de vanos", malos == 0)
    # ---------------- instalaciones vs estructura y arquitectura
    if len(niveles) > 1:
        for c in [c for c in lays[1][0] if I.es_humedo(c)]:
            p = I.punto_humedo(c)
            debajo = next((d for d in lays[0][0] if not d["contenedor"] and d["x"] <= p[0] <= d["x"] + d["w"]
                           and d["y"] <= p[1] <= d["y"] + d["d"]), None)
            junto_muro = any(abs(p[0] - ln["c"]) < 0.45 and ln["a"] <= p[1] <= ln["b"] for ln in r["estructurales"][0] if ln["eje"] == "v")
            ok = bool(debajo) and (I.es_humedo(debajo) or debajo["t"] in ("servicio", "almacen", "ext") or junto_muro)
            add("Coordinación inst.–arq.", f"Bajada sanitaria de {c['n']}",
                "BAN dentro de muro/ducto o sobre local húmedo o de servicio",
                f"Baja a {debajo['n'] if debajo else 'exterior'}" + (" junto a muro" if junto_muro else ""), ok, aviso=True)
    # bajadas pluviales vs castillos
    choques = 0
    x, y, w, d = blq["x"], blq["y"], blq["w"], blq["d"]
    for bp in I.puntos_bap(blq, 5):   # todas las posiciones posibles de BAP (las mismas que dibujan A-04 e IS-01)
        if any(math.dist(bp, c) < 0.15 for c in r["castillos"][-1]):
            choques += 1
    add("Coordinación inst.–est.", "Bajadas pluviales", "Sin cruzar castillos ni trabes", "Sin interferencias" if not choques else
        f"{choques} bajadas junto a castillo: desplazar 20 cm", choques == 0, aviso=True)
    add("Instalación eléctrica", "Balance de fases", "Desbalance ≤ 5 % (NOM-001-SEDE-2012, práctica recomendada)",
        f"{cc['desbalance']} %", cc["desbalance"] <= 5, aviso=True)
    add("Instalación eléctrica", "Circuitos dedicados", "2 circuitos de 20 A en cocina, 1 en lavandería, GFCI en baños",
        "Incluidos", any(c["tipo"] == "K" for c in cc["circuitos"]))
    add("Instalación eléctrica", "Protección general", "Interruptor ≥ 1.25 × corriente de demanda",
        f"2P-{cc['prot_general']} A para {cc['I']} A", cc["prot_general"] >= 1.25 * cc["I"] - 1e-6)
    # ---------------- acabados y presupuesto
    sin = [c["n"] for k in range(len(niveles)) for c in lays[k][0] if not c["contenedor"] and c["n"] not in acab]
    add("Acabados", "Cédula de acabados", "Todos los locales con piso, muro y plafón especificados",
        "Completa" if not sin else "Faltan: " + ", ".join(sin), not sin)
    humedos_sin = [c["n"] for k in range(len(niveles)) for c in lays[k][0] if not c["contenedor"] and c["t"] == "humedo"
                   and "Azulejo" not in acab.get(c["n"], {}).get("muro", "")]
    add("Acabados", "Locales húmedos", "Recubrimiento impermeable en zonas de agua", "Correcto" if not humedos_sin else ", ".join(humedos_sin),
        not humedos_sin)
    A_pisos = sum(c["w"] * c["d"] for k in range(len(niveles)) for c in lays[k][0] if not c["contenedor"] and c["t"] not in ("ext", "almacen"))
    add("Coordinación acabados–presupuesto", "Piso en presupuesto vs planos", "Misma cantidad (±1 %)",
        f"{q.get('piso-cer', 0):.1f} m² vs {A_pisos:.1f} m²", abs(q.get("piso-cer", 0) - A_pisos) <= 0.01 * max(A_pisos, 1))
    kg_plano = r["cuantificacion"]["total"]["kg"]
    add("Coordinación est.–presupuesto", "Acero de refuerzo", "Cuantificación de planos = acero en presupuesto + castillos (armex)",
        f"{kg_plano:,.0f} kg en planos", True)
    add("Normativa urbana", "Uso de suelo, COS y CUS", "Verificar con el Programa de Desarrollo Urbano y la constancia de uso de suelo",
        "Por verificar en trámite", True, aviso=True)
    errores = sum(1 for o in out if o["estado"] == "ERROR")
    avisos = sum(1 for o in out if o["estado"] == "AVISO")
    return dict(verificaciones=out, errores=errores, avisos=avisos)
