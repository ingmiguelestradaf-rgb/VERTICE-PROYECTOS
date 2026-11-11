"""Exporta la escena 3D del proyecto (JSON) para renderizarla en Blender (renders fotorrealistas y recorrido virtual).

La escena sale de la misma geometría que los planos: muros por nivel con sus vanos, losas, escalera, cubierta,
cancelería, terreno, exteriores y materiales de la corriente arquitectónica.
"""
import json

from ..ejec import est as EST
from .. import layout

ALTOS = {"ventana": (0.90, 2.35), "ventana_alta": (1.60, 2.20), "puerta": (0.0, 2.10), "puerta_ext": (0.0, 2.10),
         "porton": (0.0, 2.40), "vano": (0.0, 2.30)}


def exportar(ruta, proy, lays, corr, plan, nombre, r_est=None, spec=None):
    bloques = []
    for bi, blq in enumerate(proy["bloques"]):
        niveles = []
        z = blq.get("z0", 0.0)
        for k, n in enumerate(blq["niveles"]):
            cu, va = lays[bi][k]
            hojas = [c for c in cu if not c["contenedor"]]
            lns = EST.lineas(hojas)
            losa = (r_est["losas"][k]["h"] / 100) if r_est else 0.12
            tx = (r_est["t_x"] / 100) if r_est else 0.15
            ty = (r_est["t_y"] / 100) if r_est else 0.15
            vanos = []
            for v in va:
                tipo = "ventana_alta" if v["tipo"] == "ventana" and v.get("alta") else v["tipo"]
                z1, z2 = ALTOS.get(tipo, (0.0, 2.1))
                if v["tipo"] == "ventana" and n["h"] > 3.5:
                    z1, z2 = 1.0, n["h"] - 0.8
                elif layout.es_cortina(corr, k, v):
                    z1 = layout.ANTEPECHO_CORTINA
                vanos.append(dict(eje=v["eje"], c=v["c"], a=v["a"], b=v["b"], tipo=v["tipo"], z1=z1, z2=min(z2, n["h"] - losa - 0.05),
                                  lado=v.get("lado"), vidrio=bool(v.get("vidrio")), cuarto=v.get("cuarto")))
            for rep in range(n["rep"]):
                niveles.append(dict(nombre=n["nombre"], z=round(z, 3), h=n["h"], losa=losa, tx=tx, ty=ty,
                                    locales=[dict(n=c["n"], t=c["t"], x=c["x"], y=c["y"], w=c["w"], d=c["d"]) for c in hojas],
                                    muros=lns, vanos=vanos, piso=k))
                z += n["h"]
        bloques.append(dict(nombre=blq["nombre"], x=blq["x"], y=blq["y"], w=blq["w"], d=blq["d"], niveles=niveles,
                            sistema=blq["sistema"], colindancias=blq.get("colindancias", []),
                            alero=layout.alero(blq, 0.6),
                            pilotis=layout.pilotis(blq, lays[bi][0][1])
                            if "pilotis" in corr.get("rasgos", []) and len(blq["niveles"]) > 1 else None,
                            # misma geometría que render, AP-03 y A-05 (antes Blender las recalculaba con otros valores)
                            parteluces=layout.parteluces(blq, "celosia" in corr.get("rasgos", [])),
                            marco_x0=round(blq["x"] + layout.inicio_marco(lays[bi][1][1], blq["x"], blq["w"]), 3)
                            if len(blq["niveles"]) > 1 else None))
    escena = dict(nombre=nombre, clave=plan.get("fecha"), tipologia=plan["tipologia"],
                  corriente=dict(nombre=corr["nombre"], cubierta=corr["cubierta"], muro=corr["muro"], acento=corr["acento"],
                                 techo=corr["techo"], vidrio=corr["vidrio"], rasgos=corr.get("rasgos", [])),
                  materiales=(spec or {}).get("materiales") or corr.get("materiales", ""),
                  terreno=proy["terreno"], exteriores=proy["exteriores"], bloques=bloques,
                  unifamiliar="unifamiliar" in proy.get("uso_suelo", ""))
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(escena, f, ensure_ascii=False)
    return ruta
