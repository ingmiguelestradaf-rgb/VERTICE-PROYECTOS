"""Memoria técnica del proyecto ejecutivo (Word) con el formato de VERTICE-CALCULO."""


def escribir(V, ruta, nombre, datos, proy, blq, r, cc, coord, res, materiales, ins_calc, spec):
    from vertice.memoria import Documento, NORMATIVA_BC
    t = proy["terreno"]
    doc = Documento(nombre, f"{nombre} — {datos['clave']}", cliente="Proyecto del día Vértice",
                    tipo="MEMORIA TÉCNICA DEL PROYECTO EJECUTIVO")
    doc.seccion("Supuestos a validar antes de construir")
    doc.supuestos([
        ("Capacidad de carga del terreno (sin estudio de mecánica de suelos)", f"{r['q_adm']} t/m² a -{r['Df']:.2f} m", "Ancho de zapatas"),
        ("Espectro sísmico (forma tipo PRODISIS, terreno II, Tijuana)", f"c/Q'R = {r['sismo']['c']}", "Cortante basal y revisión de muros"),
        ("Resistencia de la mampostería", f"v*m = {r['vm']} kg/cm², f*m = {r['fm']} kg/cm²", "Capacidad de muros (pruebas de pilas y muretes)"),
        ("Uso de suelo, COS, CUS y restricciones", "Según PDUCP Tijuana", "Licencia de construcción"),
        ("Factibilidades CESPT y CFE", "Por tramitar", "Acometidas e instalaciones")])
    doc.seccion("1. Datos generales y normativa aplicada")
    doc.tabla(["Concepto", "Valor"], [("Proyecto", nombre), ("Clave", datos["clave"]), ("Ubicación", "Tijuana, B.C."),
                                      ("Terreno", f"{t['frente']:.2f} x {t['fondo']:.2f} m"),
                                      ("Superficie construida", f"{blq['w'] * blq['d'] * len(blq['niveles']):,.2f} m²"),
                                      ("Niveles", str(len(blq["niveles"]))), ("Grupo de la estructura", "B (habitación)")])
    doc.tabla(["Norma", "Ámbito"], NORMATIVA_BC + [("NOM-001-SEDE-2012 Instalaciones eléctricas", "Eléctrica"),
                                                  ("NOM-004-SEDG-2004 Instalaciones de gas LP", "Gas"),
                                                  ("Normas técnicas de la CESPT", "Hidrosanitaria")])
    doc.seccion("2. Descripción arquitectónica")
    if spec.get("concepto"):
        doc.parrafo(spec["concepto"])
    doc.vinetas(materiales[:8])
    doc.seccion("Cédula de acabados", 2)
    doc.tabla(["Local", "Piso", "Muros", "Plafón"], [(n, a["piso"], a["muro"], a["plafon"]) for n, a in res["acabados"].items()])
    doc.seccion("Cancelería", 2)
    doc.tabla(["Clave", "Tipo", "Medida (m)", "Cant.", "Especificación"],
              [(c["clave"], c["desc"], f"{c['ancho']:.2f} x {c['alto']:.2f}", c["cant"], c["mat"]) for c in res["cancel"]])
    doc.seccion("3. Estructuración")
    doc.parrafo(f"Muros de carga de block hueco de concreto confinados con castillos y dalas (mampostería confinada, Q = 1.5). "
                f"Muros en dirección X de {r['t_x']} cm y en dirección Y de {r['t_y']} cm. Losas macizas perimetrales de concreto "
                f"f'c 250 kg/cm². Cimentación de zapatas corridas de concreto reforzado"
                + (" con zapatas excéntricas en linderos." if r["lindero"] else ".")
                + (" Trabe de carga sobre la cochera doble apoyada en columna C-1 entre portones." if r.get("columnas") else ""))
    if r.get("ajustes"):
        doc.parrafo("Ajustes de coordinación arquitectura–estructura aplicados:", True)
        doc.vinetas(r["ajustes"])
    doc.seccion("4. Análisis de cargas")
    for titulo, des, cm, cv in (("Entrepiso", r["desglose_ent"], r["cm_ent"], r["cv_ent"]), ("Azotea", r["desglose_azo"], r["cm_azo"], r["cv_azo"])):
        doc.parrafo(titulo, True)
        doc.tabla(["Capa", "Espesor (m)", "Peso vol. (kg/m³)", "kg/m²"], des)
        doc.parrafo(f"CM = {cm} kg/m² · CV máx = {cv[0]} · CV inst = {cv[1]} kg/m² (NTC Criterios y Acciones)")
    doc.formula(f"wu entrepiso = {r['w_ent']} kg/m²; wu azotea = {r['w_azo']} kg/m²", "1.3 CM + 1.5 CV")
    doc.seccion("5. Análisis sísmico")
    doc.formula(f"T = {r['sismo']['T']} s · c/(Q'R) = {r['sismo']['c']} · V basal = {r['sismo']['V']} t", "MDOC-CFE Sismo, método estático")
    doc.tabla(["Nivel", "Fi (t)", "Vi (t)"], r["sismo"]["fuerzas"])
    doc.seccion("Revisión de muros — método simplificado (NTC Mampostería)", 2)
    doc.tabla(["Dirección", "Vu (t)", "Σ FAE·VmR (t)", "Área efectiva (cm²)", "Resultado"],
              [(s["dir"], round(s["Vu"] / 1000, 1), round(s["VR"] / 1000, 1), s["Aef"], "Cumple" if s["cumple"] else "No cumple")
               for s in r["simplificado"]])
    doc.seccion("Revisión de muros por carga vertical", 2)
    doc.tabla(["Línea de muro", "Pu (kg/m)", "PR (kg/m)", "Resultado"],
              [(v["linea"], v["Pu"], v["PR"], "Cumple" if v["cumple"] else "No cumple") for v in r["vertical"] if v["Pu"]])
    doc.seccion("6. Diseño de losas")
    for ls in r["losas"]:
        doc.parrafo(f"Losa de {ls['nombre']}: h = {ls['h']} cm, wu = {ls['wu']} kg/m². {ls['armado']}.", True)
        doc.tabla(["Tablero", "a1 x a2 (m)", "Mu+ (kg·m/m)", "Mu- (kg·m/m)", "As+ (cm²/m)", "As- (cm²/m)"],
                  [(f["tablero"], f"{f['a1']} x {f['a2']}", f["Mu"], f["Mneg"], f["As_p"], f["As_n"]) for f in ls["filas"]])
    doc.parrafo("Momentos por franjas en la dirección corta con coeficientes 1/10 (1/8 sin continuidad), método conservador "
                "respecto a la tabla de coeficientes de la NTC Concreto; espesor mínimo por perímetro/250 con bordes discontinuos +25 %.")
    doc.seccion("7. Trabes y cerramientos")
    doc.tabla(["Clave", "Tipo", "L (m)", "b x h (cm)", "Mu (t·m)", "Vu (t)", "Lecho inferior", "Estribos"],
              [(tb["clave"], tb["tipo"], tb["L"], f"{tb['b']}x{tb['h']}", tb["Mu"], tb["Vu"], tb["inf"], f"#2.5 @ {tb['s']:g}") for tb in r["trabes"]])
    if r.get("escalera"):
        e = r["escalera"]
        doc.seccion("8. Escalera")
        doc.formula(f"{e['peldanos']} peraltes de {e['peralte']} cm, huella {e['huella']} cm, 2p+h = {e['regla']} cm; "
                    f"losa h = {e['h']} cm, Mu = {e['Mu']} kg·m/m, #3 @ {e['s']} cm", "NTC Concreto / Reglamento")
    doc.seccion("9. Cimentación")
    doc.tabla(["Clave", "Ubicación", "w serv (t/m)", "B (cm)", "h (cm)", "q (t/m²)", "Armado"],
              [(z["clave"], z["desc"], z["w"], z["B"], z["h"], z["q"], z["armado"]) for z in r["zapatas"]])
    cu = r["cuantificacion"]
    doc.seccion("Cuantificación de acero y concreto", 2)
    doc.tabla(["Elemento", "Cantidad", "#2.5 kg", "#3 kg", "#4–#6 kg", "Concreto m³"],
              [(f["elemento"], f"{f['cantidad']} {f['unidad']}", f["kg2"], f["kg3"], f["kg4"], f["concreto"]) for f in cu["filas"]])
    doc.parrafo(f"Total: {cu['total']['kg']:,.0f} kg de acero y {cu['total']['concreto']:.1f} m³ de concreto "
                f"({cu['total']['kg'] / (blq['w'] * blq['d'] * len(blq['niveles'])):.1f} kg/m² construido).")
    doc.seccion("10. Instalaciones")
    for k, titulo in (("hidraulica", "Hidráulica"), ("sanitaria", "Sanitaria"), ("pluvial", "Pluvial"), ("gas", "Gas LP")):
        doc.parrafo(titulo, True)
        doc.tabla(["Concepto", "Valor", "Criterio"], ins_calc[k])
    doc.parrafo("Eléctrica — cuadro de cargas", True)
    doc.tabla(["Circuito", "Descripción", "W", "Fase", "Protección", "Conductor"],
              [(f"C-{c['num']}", c["desc"], c["W"], c["fase"], f"1P-{c['prot']} A", f"cal. {c['cal']}") for c in cc["circuitos"]])
    doc.parrafo(f"Carga instalada {cc['total']:,} W, demanda {cc['demanda']:,} W, I = {cc['I']} A; interruptor general "
                f"2P-{cc['prot_general']} A, alimentador cal. {cc['cal_general']}; desbalance {cc['desbalance']} %.")
    doc.seccion("11. Revisión de coordinación y normativa")
    doc.parrafo(f"{coord['errores']} errores · {coord['avisos']} avisos", True)
    doc.tabla(["Disciplina", "Concepto", "Criterio / norma", "Resultado", "Estado"],
              [(v["disciplina"], v["concepto"], v["criterio"], v["resultado"], v["estado"]) for v in coord["verificaciones"]])
    p = res["presupuesto"]
    doc.seccion("12. Presupuesto y programa")
    doc.parrafo(f"Subtotal presupuestado ${p['subtotal']:,.0f} (sin IVA), ${p['por_m2']:,.0f}/m². Conceptos con material por "
                f"cotizar: {', '.join(p['solo_mano_obra']) or 'ninguno'}; suministros por cotizar: {p['por_cotizar']} partidas "
                f"(ver hoja 'Por cotizar' del presupuesto). Programa: {res['programa']['dias']} días hábiles "
                f"({res['programa']['semanas']} semanas).")
    doc.seccion("13. Responsiva")
    doc.responsiva()
    doc.guardar(ruta)
    return ruta
