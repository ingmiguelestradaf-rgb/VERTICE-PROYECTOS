"""Ciclo de coordinación arquitectura–estructura para vivienda.

El ingeniero calcula; si la estructura no cumple, el arquitecto ajusta (ventanas y vanos abiertos) o el
ingeniero cambia el block de los muros en la dirección débil a 20 cm. Se repite hasta cumplir.
"""
import copy
from .. import layout
from . import est

PASOS = [("vano_max", 1.8, "Se limitaron los vanos abiertos entre locales a 1.80 m"),
         ("block20", None, "Se cambiaron a block de 20 cm los muros de la dirección más débil"),
         ("ventana", 0.85, "Se redujo 15 % el ancho de ventanas (sin bajar del 17.5 % de iluminación)"),
         ("vano_max", 1.2, "Se limitaron los vanos abiertos entre locales a 1.20 m"),
         ("block20b", None, "Se cambiaron a block de 20 cm los muros de la otra dirección"),
         ("ventana", 0.85, "Se redujo otro 15 % el ancho de ventanas (sin bajar del 17.5 % de iluminación)")]


def cumple(r):
    return all(x["cumple"] for x in r["simplificado"]) and all(v["cumple"] for v in r["vertical"]) \
        and all(z["cumple"] for z in r["zapatas"]) and all(z["q"] <= r["q_adm"] for z in r["zapatas"])


def resolver(V, blq, corr):
    corr = copy.deepcopy(corr)
    ajustes, t_x, t_y = [], 15, 15
    for i in range(len(PASOS) + 1):
        lays = [layout.distribuir(blq, n, corr, k) for k, n in enumerate(blq["niveles"])]
        r = est.calcular(V, blq, lays, t_x, t_y)
        # muros con carga vertical excedida: block de 20 en esa dirección
        falla_v = [v for v in r["vertical"] if not v["cumple"]]
        for v in falla_v:
            d_ = "X" if v["linea"].startswith("Y=") else "Y"
            if d_ == "X" and t_x == 15:
                t_x = 20; ajustes.append("Se cambiaron a block de 20 cm los muros en X por carga vertical")
            if d_ == "Y" and t_y == 15:
                t_y = 20; ajustes.append("Se cambiaron a block de 20 cm los muros en Y por carga vertical")
        if falla_v and (t_x == 20 or t_y == 20):
            r = est.calcular(V, blq, lays, t_x, t_y)
        if cumple(r) or i == len(PASOS):
            break
        clave, val, txt = PASOS[i]
        if clave == "ventana":
            corr["ventana"] = round(corr["ventana"] * val, 3)
        elif clave == "vano_max":
            corr["vano_max"] = val
        elif clave == "block20b":
            t_x, t_y = 20, 20
        elif clave == "block20":
            debil = min(r["simplificado"], key=lambda x: x["VR"] / max(x["Vu"], 1))["dir"]
            if debil == "X":
                t_x = 20
            else:
                t_y = 20
            txt += f" ({debil})"
        ajustes.append(txt)
    r["ajustes"] = ajustes
    r["cumple"] = cumple(r)
    return corr, lays, r
