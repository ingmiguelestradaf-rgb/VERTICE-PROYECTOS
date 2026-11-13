#!/usr/bin/env python3
"""Genera el proyecto arquitectónico y estructural del día.

Uso:
  python generar.py                       # proyecto de hoy (zona horaria America/Tijuana)
  python generar.py --fecha 2026-11-01    # de una fecha específica
  python generar.py --plan                # sólo muestra tipología/corriente/terreno del día
  python generar.py --spec spec.json      # usa el diseño propuesto por Claude (modo híbrido)
  python generar.py --si-no-existe        # no hace nada si ya existe el proyecto del día
"""
import argparse
import copy
import datetime as dt
import json
import os
import re
import shutil
import sys
import unicodedata
import zipfile

from matplotlib.backends.backend_pdf import PdfPages

from motor import calendario, programa, layout, estructura, instalaciones as inst, planos, plano_estructural as pe
from motor import render as rd, lamina, web, revision
from motor.dxf import DXF
from motor.hojas import Juego, Fila

RAIZ = os.path.dirname(os.path.abspath(__file__))
SALIDA = os.path.join(RAIZ, "docs", "proyectos")


def slug(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def hoy_tijuana():
    try:
        from zoneinfo import ZoneInfo
        return dt.datetime.now(ZoneInfo("America/Tijuana")).date()
    except Exception:
        return (dt.datetime.utcnow() - dt.timedelta(hours=8)).date()


def fusionar(base, extra):
    for k, v in extra.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            fusionar(base[k], v)
        else:
            base[k] = v
    return base


class Hoja:
    """Acomoda varios dibujos en una lámina, de izquierda a derecha."""

    def __init__(self, dx, sep):
        self.dx, self.x, self.sep, self.ymax = dx, 0.0, sep, 0.0

    def poner(self, ancho, alto, dibujar, titulo):
        ox = self.x
        dibujar(ox)
        h = max(0.35, max(ancho, alto) / 45)
        self.dx.texto((ox + ancho / 2, -h * 6.5), titulo, h, "A-TEXTO", centrado=True)
        self.x += ancho + self.sep
        self.ymax = max(self.ymax, alto)


def niveles_unicos(blq):
    return [(k, n) for k, n in enumerate(blq["niveles"])]


PRIVADO = os.environ.get("VERTICE_PRIVADO", os.path.join(RAIZ, "_privado"))


def construir(fecha, spec=None, salida=SALIDA, privado=PRIVADO, ejecutivo=True):
    """Anteproyecto en `salida/<clave>` (público) y proyecto ejecutivo en `privado/<clave>/Proyecto ejecutivo`."""
    plan = calendario.plan_del_dia(fecha)
    spec = spec or {}
    for k in ("corriente", "variante", "terreno"):
        if k in spec:
            plan[k] = spec[k] if k != "terreno" else fusionar(plan.get("terreno", {}), spec[k])
    plan["corriente_nombre"] = calendario.CORRIENTES[plan["corriente"]]["nombre"]
    corr = copy.deepcopy(calendario.CORRIENTES[plan["corriente"]])
    if spec.get("paleta"):
        corr.update(spec["paleta"])
    if spec.get("rasgos"):
        corr["rasgos"] = spec["rasgos"]
    proy = programa.generar(plan)
    if spec.get("modelo"):
        fusionar(proy, spec["modelo"])
    # cubierta inclinada sobre la losa de azotea (vivienda de mampostería): material y peso para estructura,
    # planta de azotea y ubicación del tanque de gas (no se coloca sobre una cubierta inclinada)
    mats = (spec.get("materiales") or corr["materiales"]).lower()
    for blq in proy["bloques"]:
        blq["pretil"] = layout.altura_pretil(corr["cubierta"])
        if blq["sistema"] == "mamposteria" and corr["cubierta"] not in ("plana", "plana_pretil") \
                and planos.altura_cubierta(blq, corr) > 0:
            teja = "teja" in mats
            al = 0.9 if "alero_amplio" in corr["rasgos"] else 0.6
            span = min(blq["w"], blq["d"]) / (1 if corr["cubierta"].startswith("una") else 2)
            blq["cubierta_ligera"] = dict(tipo=corr["cubierta"], material="teja de barro" if teja else "lámina",
                                          cm=100 if teja else 30, alero=al,
                                          pend=round(planos.altura_cubierta(blq, corr) / span, 3),
                                          rasgos=[r_ for r_ in corr["rasgos"] if r_ in ("porche", "pergola")])
            # tanque de gas LP a nivel de patio posterior, junto a la colindancia oriente y a >= 3 m de la fachada
            blq["gas_L"] = "300 L" if plan["terreno"]["area"] < 300 else "500 L"   # igual que instalaciones.calcular
            libre = plan["terreno"]["fondo"] - (blq["y"] + blq["d"])
            blq["tanque_gas"] = [round(blq["x"] + blq["w"] - 0.6, 2),
                                 round(blq["y"] + blq["d"] + max(1.2, min(3.6, libre - 1.0)), 2)]
    nombre = spec.get("nombre") or f"{plan['tipologia_nombre']} {plan['corriente_nombre']}"
    concepto = spec.get("concepto") or ""
    clave = f"{fecha.isoformat()}-{plan['tipologia']}-{slug(plan['corriente'])}"
    carpeta = os.path.join(salida, clave)
    if os.path.exists(carpeta):
        shutil.rmtree(carpeta)
    os.makedirs(carpeta)

    # ---- distribución (en vivienda, con ciclo de coordinación arquitectura–estructura)
    V = r_est = None
    es_casa = plan["tipologia"] == "casa" and len(proy["bloques"]) == 1
    if es_casa and ejecutivo:
        from motor.ejec import enlace, coordina
        V = enlace.cargar()
        if V is not None:
            corr, lays0, r_est = coordina.resolver(V, proy["bloques"][0], corr)
            lays = [lays0]
    if r_est is None:
        lays = [[layout.distribuir(blq, n, corr, k) for k, n in enumerate(blq["niveles"])] for blq in proy["bloques"]]
    # geometría única de la marquesina sobre pilotis para plantas y cortes (render, fachadas y Blender la recalculan igual)
    for i, blq in enumerate(proy["bloques"]):
        if "pilotis" in corr["rasgos"] and len(blq["niveles"]) > 1:
            blq["pilotis"] = layout.pilotis(blq, lays[i][0][1])
        if "volado" in corr["rasgos"] and blq["sistema"] != "acero":
            # losa en volado de la fachada principal: la pluvial y el presupuesto la cuentan (antes sólo se dibujaba)
            blq["volado"] = layout.volado(blq, corr["rasgos"], lays[i][1][1] if len(lays[i]) > 1 else None)
    esp = (r_est["t_x"] / 100, r_est["t_y"] / 100) if r_est else (0.15, 0.15)
    area_total = sum(b["w"] * b["d"] * sum(n["rep"] for n in b["niveles"]) for b in proy["bloques"])
    desplante = sum(b["w"] * b["d"] for b in proy["bloques"] if b.get("z0", 0) == 0)
    t = proy["terreno"]
    a_terreno = t["frente"] * t["fondo"]
    ests = [estructura.predimensionar(b, lays[i], proy["bloques"]) for i, b in enumerate(proy["bloques"])]
    rev = revision.revisar(proy, lays)
    proy["_ci"] = plan["tipologia"] != "casa"
    ins = inst.calcular(proy, plan, lays, area_total)
    datos = dict(proyecto=nombre.upper(), clave=clave, fecha=fecha.isoformat())
    big = max(max(b["w"], b["d"]) for b in proy["bloques"])
    sep = max(6.0, big * 0.35)

    # ================= ANTEPROYECTO (público)
    notas_a = ["Cotas en metros. Verificar en sitio.", "Anteproyecto: el proyecto ejecutivo (estructura, instalaciones,",
               "presupuesto y programa) se entrega por separado.", "Normativa: Reglamento de Edificaciones de Tijuana y NTC-2017."]
    J = Juego(carpeta, datos, notas_a, nombre_pdf="anteproyecto.pdf")
    h = J.nueva("AP-01", "Planta de conjunto", disciplina="Anteproyecto")
    planos.exteriores(h["dx"], proy)
    varios = len(proy["bloques"]) > 1
    for i, blq in enumerate(proy["bloques"]):
        planos.planta_arq(h["dx"], blq, lays[i][0][0], lays[i][0][1], texto=varios or blq["w"] < 30, cotas=False, esp=esp)
        if varios:
            h["dx"].texto((blq["x"] + blq["w"] / 2, blq["y"] + blq["d"] + max(0.4, blq["w"] / 40)), blq["nombre"].upper(),
                          max(0.3, max(blq["w"], blq["d"]) / 35), "A-TEXTO", centrado=True)
    verde = sum(e["w"] * e["d"] for e in proy["exteriores"] if e["tipo"] == "area_verde")
    caj = sum(planos.contar_cajones(e["w"], e["d"]) for e in proy["exteriores"] if e["tipo"] == "estacionamiento")
    if plan["tipologia"] == "casa":
        caj = 2 if a_terreno >= 300 else 1
    filas = [("Terreno", f"{a_terreno:,.2f} m2"), ("Desplante", f"{desplante:,.2f} m2"), ("C.O.S.", f"{desplante / a_terreno:.2f}"),
             ("Construcción total", f"{area_total:,.2f} m2"), ("C.U.S.", f"{area_total / a_terreno:.2f}"),
             ("Área libre", f"{a_terreno - desplante:,.2f} m2"), ("Área verde (aprox.)", f"{verde:,.2f} m2"),
             ("Niveles", str(max(sum(n['rep'] for n in b['niveles']) for b in proy['bloques']))),
             ("Cajones de estacionamiento", str(caj))]
    hc = max(0.3, max(t["frente"], t["fondo"]) / 70)
    planos.cuadro_areas(h["dx"], t["frente"] + max(6.0, t["frente"] * 0.15), t["fondo"], filas, hc)
    J.cerrar(h)
    h = J.nueva("AP-02", "Plantas arquitectónicas", disciplina="Anteproyecto")
    H = Fila(h["dx"], sep)
    for i, blq in enumerate(proy["bloques"]):
        if blq["nombre"].startswith("Villa") and i > 1:
            continue
        for k, n in enumerate(blq["niveles"]):
            cu, va = lays[i][k]
            rep = f" (x{n['rep']})" if n["rep"] > 1 else ""
            H.poner(blq["w"], blq["d"], lambda ox, blq=blq, cu=cu, va=va: planos.planta_arq(h["dx"], blq, cu, va, ox - blq["x"], -blq["y"], esp=esp),
                    f"{n['nombre'].upper()}{rep} — {blq['nombre'].upper()}")
    J.cerrar(h)
    h = J.nueva("AP-03", "Fachadas y corte", disciplina="Anteproyecto")
    planos.fachada(h["dx"], proy, lays, corr, 0, 0, "S")
    planos.fachada(h["dx"], proy, lays, corr, t["frente"] + sep, 0, "E")
    zmax = max(planos.alturas(b)[1] + planos.altura_cubierta(b, corr) for b in proy["bloques"])
    planos.corte(h["dx"], proy, lays, corr, 0, -(zmax + max(8.0, t["fondo"] * 0.12)) - max(3.0, zmax * 0.3))
    J.cerrar(h)
    zp = J.fin(f"{clave}_anteproyecto_dxf.zip")
    ra = os.path.join(carpeta, "render_aereo.jpg")
    rp = os.path.join(carpeta, "render_peatonal.jpg")
    rd.render(proy, lays, corr, ra, rp, nombre, seed=int(fecha.strftime("%Y%m%d")))

    # ================= PROYECTO EJECUTIVO (privado: sólo Drive)
    ej = None
    carpeta_ej = os.path.join(privado, clave, "Proyecto ejecutivo")
    if ejecutivo:
        if r_est is not None:
            from motor.ejec import proyecto as PE
            ej = PE.generar(V, carpeta_ej, datos, proy, plan, corr, lays[0], r_est, spec, nombre, ins)
        else:
            ej = ejecutivo_basico(carpeta_ej, datos, proy, lays, ests, ins, sep)

    areas = []
    for i, blq in enumerate(proy["bloques"]):
        for k, n in enumerate(blq["niveles"]):
            for c in lays[i][k][0]:
                if not c["contenedor"]:
                    areas.append(dict(bloque=blq["nombre"], nivel=n["nombre"], rep=n["rep"], espacio=c["n"],
                                      area=round(c["w"] * c["d"], 2), medidas=f"{c['w']:.2f} x {c['d']:.2f}"))
    altura_max = max(planos.alturas(b)[1] + planos.altura_cubierta(b, corr) for b in proy["bloques"])
    ficha_ej = None
    if ej:
        ficha_ej = dict(laminas=[dict(clave=hj["clave"], titulo=hj["titulo"], disciplina=hj.get("disciplina", "")) for hj in ej["hojas"]],
                        coordinacion=dict(errores=ej["coordinacion"]["errores"], avisos=ej["coordinacion"]["avisos"],
                                          verificaciones=len(ej["coordinacion"]["verificaciones"])) if ej.get("coordinacion") else None,
                        nivel="Proyecto ejecutivo completo" if r_est is not None else "Proyecto ejecutivo nivel básico",
                        documentos=[d for d in ("Memoria técnica (Word/PDF)", "Presupuesto (Excel)", "Programa de obra (Excel y Gantt)",
                                                "Juego de planos (PDF y DXF)") if r_est is not None or "planos" in d])
    resumen = dict(clave=clave, fecha=fecha.isoformat(), nombre=nombre, concepto=concepto,
                   tipologia=plan["tipologia"], tipologia_nombre=plan["tipologia_nombre"],
                   subtipo=proy.get("subtipo", ""), corriente=plan["corriente"], corriente_nombre=corr["nombre"],
                   materiales=spec.get("materiales") or corr["materiales"], uso_suelo=proy.get("uso_suelo", ""),
                   terreno=dict(frente=t["frente"], fondo=t["fondo"], area=round(a_terreno, 1)),
                   area_construida=round(area_total, 1), desplante=round(desplante, 1),
                   cos=round(desplante / a_terreno, 2), cus=round(area_total / a_terreno, 2),
                   niveles=max(sum(n["rep"] for n in b["niveles"]) for b in proy["bloques"]),
                   altura=round(altura_max, 1), cajones=caj, usuarios=proy.get("usuarios", {}),
                   areas=areas, hojas=J.hojas, render=["render_aereo.jpg", "render_peatonal.jpg"],
                   pdf=os.path.basename(J.pdf_ruta), zip=os.path.basename(zp), extra=spec.get("extra", {}),
                   revision=rev, ejecutivo=ficha_ej,
                   generado_por="híbrido (Claude + motor)" if spec else "motor automático")
    with open(os.path.join(carpeta, "proyecto.json"), "w", encoding="utf-8") as f:
        json.dump(resumen, f, ensure_ascii=False, indent=1)
    with open(os.path.join(carpeta, "spec.json"), "w", encoding="utf-8") as f:
        json.dump(spec, f, ensure_ascii=False, indent=1)      # diseño reproducible (el ejecutivo se regenera desde aquí)
    with open(os.path.join(carpeta, "memoria_descriptiva.md"), "w", encoding="utf-8") as f:
        f.write(web.memoria_md(resumen))
    with open(os.path.join(carpeta, "index.html"), "w", encoding="utf-8") as f:
        f.write(web.pagina_proyecto(resumen))
    web.galeria(salida, os.path.join(os.path.dirname(salida), "index.html"))
    # copia del anteproyecto para Drive
    if ejecutivo:
        dest = os.path.join(privado, clave, "Anteproyecto")
        if os.path.exists(dest):
            shutil.rmtree(dest)
        shutil.copytree(carpeta, dest, ignore=shutil.ignore_patterns("index.html", "laminas", "spec.json", "proyecto.json"))
    if ejecutivo:
        from motor.foto import escena as ESC
        ESC.exportar(os.path.join(privado, clave, "escena.json"), proy, lays, corr, plan, nombre, r_est, spec)
    resumen["_ejecutivo"] = ej
    resumen["_carpeta_privada"] = os.path.join(privado, clave) if ejecutivo else None
    return carpeta, resumen


def ejecutivo_basico(carpeta, datos, proy, lays, ests, ins, sep):
    """Tipologías sin motor ejecutivo completo todavía: estructura e instalaciones esquemáticas."""
    if os.path.exists(carpeta):
        shutil.rmtree(carpeta)
    notas = ["Proyecto ejecutivo NIVEL BÁSICO: predimensionamiento y trazo esquemático.",
             "Requiere memoria de cálculo definitiva, estudio de mecánica de suelos y firma de DRO.",
             "Normativa de referencia: Reglamento de Edificaciones de Tijuana, NTC-2017, NOM-001-SEDE-2012."]
    J = Juego(carpeta, datos, notas, nombre_pdf="juego_de_planos.pdf")
    for clave_h, tit, fn in (("E-01", "Planta de cimentación", "cim"), ("E-02", "Planta estructural", "est")):
        h = J.nueva(clave_h, tit, gris=True, disciplina="Estructural")
        H = Fila(h["dx"], sep * 1.3)
        for i, blq in enumerate(proy["bloques"]):
            if blq["nombre"].startswith("Villa") and i > 1:
                continue
            est = ests[i]
            if fn == "cim":
                H.poner(blq["w"], blq["d"], lambda ox, blq=blq, est=est: pe.cimentacion(h["dx"], blq, est, ox - blq["x"], -blq["y"]),
                        f"CIMENTACIÓN — {blq['nombre'].upper()}")
            else:
                H.poner(blq["w"], blq["d"], lambda ox, blq=blq, est=est, i=i: pe.planta_est(h["dx"], blq, est, lays[i][0][0], ox - blq["x"], -blq["y"]),
                        f"ESTRUCTURA TIPO — {blq['nombre'].upper()}")
        J.cerrar(h)
    for clave_h, tit, d in (("IH-01", "Instalación hidráulica y contra incendio", "ih"), ("IS-01", "Instalación sanitaria y pluvial", "is"),
                            ("IE-01", "Instalación eléctrica", "ie"), ("IG-01", "Instalación de gas LP", "ig")):
        h = J.nueva(clave_h, tit, gris=True, disciplina="Instalaciones")
        H = Fila(h["dx"], sep)
        primero = True
        for i, blq in enumerate(proy["bloques"]):
            if blq["nombre"].startswith("Villa") and i > 1:
                continue
            for k, n in enumerate(blq["niveles"]):
                cu, va = lays[i][k]

                def dib(ox, blq=blq, cu=cu, va=va, k=k, pg=primero, h=h, d=d):
                    oxx, oyy = ox - blq["x"], -blq["y"]
                    planos.planta_arq(h["dx"], blq, cu, va, oxx, oyy, texto=d == "ie")
                    {"ih": lambda: inst.hidraulica(h["dx"], proy, blq, cu, oxx, oyy, k, pg),
                     "is": lambda: inst.sanitaria(h["dx"], proy, blq, cu, oxx, oyy, k,
                                                  [l_[0] for l_ in lays[i][k + 1:]] if k == 0 else ()),
                     "ie": lambda: inst.electrica(h["dx"], proy, blq, cu, oxx, oyy, k, pg),
                     "ig": lambda: inst.gas(h["dx"], proy, blq, cu, oxx, oyy, k, pg)}[d]()
                H.poner(blq["w"], blq["d"], dib, f"{n['nombre'].upper()} — {blq['nombre'].upper()}")
                primero = False
        J.cerrar(h)
    zp = J.fin(f"{datos['clave']}_ejecutivo_dxf.zip")
    with open(os.path.join(carpeta, "estructura_e_instalaciones.json"), "w", encoding="utf-8") as f:
        json.dump(dict(estructura=[dict(sistema=e["sistema"], tabla=e["tabla"], calc=e["calc"]) for e in ests],
                       instalaciones={k: v for k, v in ins.items() if k != "resumen"}), f, ensure_ascii=False, indent=1)
    return dict(hojas=J.hojas, pdf=os.path.basename(J.pdf_ruta), zip=os.path.basename(zp), coordinacion=None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fecha")
    ap.add_argument("--spec")
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--si-no-existe", action="store_true")
    ap.add_argument("--galeria", action="store_true", help="sólo regenera la galería")
    ap.add_argument("--estricto", action="store_true", help="termina con error si la revisión encuentra errores")
    ap.add_argument("--sin-ejecutivo", action="store_true", help="sólo anteproyecto")
    a = ap.parse_args()
    fecha = dt.date.fromisoformat(a.fecha) if a.fecha else hoy_tijuana()
    if a.galeria:
        web.galeria(SALIDA, os.path.join(os.path.dirname(SALIDA), "index.html"))
        return
    if a.plan:
        print(json.dumps(calendario.plan_del_dia(fecha), ensure_ascii=False, indent=2))
        return
    if a.si_no_existe and os.path.isdir(SALIDA) and any(n.startswith(fecha.isoformat()) for n in os.listdir(SALIDA)):
        print(f"Ya existe el proyecto del {fecha}; nada que hacer.")
        return
    spec = json.load(open(a.spec, encoding="utf-8")) if a.spec else None
    carpeta, r = construir(fecha, spec, ejecutivo=not a.sin_ejecutivo)
    rv = r["revision"]
    print(f"OK {r['clave']}: {r['nombre']} — {r['area_construida']} m²")
    print(f"  Anteproyecto: {len(r['hojas'])} láminas → {os.path.relpath(carpeta, RAIZ)}")
    ej = r.get("_ejecutivo")
    if ej:
        print(f"  Proyecto ejecutivo: {len(ej['hojas'])} láminas → {r['_carpeta_privada']}")
        if ej.get("coordinacion"):
            co = ej["coordinacion"]
            print(f"  Coordinación: {co['errores']} errores, {co['avisos']} avisos")
            for v in co["verificaciones"]:
                if v["estado"] != "OK":
                    print(f"    [{v['estado']}] {v['disciplina']} — {v['concepto']}: {v['resultado']}")
        if ej.get("presupuesto"):
            p = ej["presupuesto"]
            print(f"  Presupuesto: ${p['subtotal']:,.0f} + IVA (${p['por_m2']:,.0f}/m²), {p['por_cotizar']} partidas por cotizar; "
                  f"programa {ej['programa']['semanas']} semanas")
    print(f"Revisión: {rv['errores']} errores, {rv['avisos']} avisos")
    for o in rv["observaciones"]:
        print(f"  [{o['tipo'].upper()}] {o['nivel']}: {o['mensaje']}")
    co = (ej or {}).get("coordinacion") or {}
    if a.estricto and (rv["errores"] or co.get("errores")):
        sys.exit(1)


if __name__ == "__main__":
    main()
