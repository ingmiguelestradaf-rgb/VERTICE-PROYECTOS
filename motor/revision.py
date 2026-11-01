"""Revisión automática del anteproyecto (control de calidad antes de publicar).

Criterios de referencia (habitacional): Reglamento de Edificaciones para el Municipio de
Tijuana y Normas Técnicas Complementarias para el Proyecto Arquitectónico (CDMX) como
referencia de dimensiones mínimas. Son verificaciones de anteproyecto: el DRO confirma.
"""
from . import layout

# (lado mínimo m, área mínima m²) por tipo de espacio en vivienda
MIN_HAB = {
    "Recámara": (2.70, 7.0), "Sala": (2.70, 7.3), "Comedor": (2.30, 6.3), "Cocina": (1.50, 3.0),
    "Baño": (1.20, 2.5), "Medio baño": (0.90, 1.5), "Cochera": (2.70, 15.0), "Escalera": (2.0, 6.5),
    "Pasillo": (0.90, 0), "Vestíbulo": (0.90, 0), "Lavandería": (1.40, 1.7), "Estudio": (2.20, 5.0),
}
ILUMINAR = ("social", "privado", "cocina", "grande")


def _min(nombre):
    for k, v in MIN_HAB.items():
        if nombre.startswith(k) or k in nombre:
            return k, v
    return None, None


def revisar(proy, lays):
    obs = []
    t = proy["terreno"]

    def add(nivel, tipo, msg):
        obs.append(dict(nivel=nivel, tipo=tipo, mensaje=msg))

    for bi, blq in enumerate(proy["bloques"]):
        if blq["x"] < -0.01 or blq["y"] < -0.01 or blq["x"] + blq["w"] > t["frente"] + 0.01 or blq["y"] + blq["d"] > t["fondo"] + 0.01:
            add(blq["nombre"], "error", "El edificio rebasa los linderos del predio.")
        for k, n in enumerate(blq["niveles"]):
            cu, va = lays[bi][k]
            hojas = [c for c in cu if not c["contenedor"]]
            etq = f"{blq['nombre']} · {n['nombre']}"
            vis = layout.alcanzables(hojas, va, k)
            for i, c in enumerate(hojas):
                if i not in vis:
                    add(etq, "error", f"{c['n']}: sin acceso (no conecta con la entrada ni con la escalera).")
            con_ventana = {v["cuarto"] for v in va if v["tipo"] in ("ventana", "porton", "puerta_ext") and v.get("lado")}
            autos = [v["cuarto"] for v in va if v.get("auto")]
            if autos:
                add(etq, "aviso", "Acceso agregado por la revisión automática en: " + ", ".join(sorted(set(autos))) + ".")
            for c in hojas:
                if blq["uso"] == "habitacional":
                    k_, mn = _min(c["n"])
                    if mn:
                        lado, area = mn
                        if min(c["w"], c["d"]) + 1e-6 < lado:
                            add(etq, "error", f"{c['n']}: lado de {min(c['w'], c['d']):.2f} m < mínimo {lado:.2f} m.")
                        if c["w"] * c["d"] + 1e-6 < area:
                            add(etq, "error", f"{c['n']}: área de {c['w'] * c['d']:.1f} m² < mínimo {area:.1f} m².")
                if c["t"] in ILUMINAR and c["n"] not in con_ventana and not any(k in c["n"] for k in ("Vestidor", "Closet", "Bodega")) and blq["uso"] in ("habitacional", "hotel", "oficinas"):
                    add(etq, "aviso", f"{c['n']}: sin ventana al exterior; requiere iluminación cenital o patio de luz.")
                if c["t"] == "humedo" and c["n"] not in con_ventana:
                    add(etq, "aviso", f"{c['n']}: ventilación mecánica (extractor) obligatoria.")
            # vanos encimados sobre el mismo muro
            for a in range(len(va)):
                for b in range(a + 1, len(va)):
                    p, q = va[a], va[b]
                    if p["eje"] == q["eje"] and abs(p["c"] - q["c"]) < 0.01 and p["a"] < q["b"] - 0.05 and q["a"] < p["b"] - 0.05 \
                            and "ventana" not in (p["tipo"], q["tipo"]):
                        add(etq, "aviso", f"Vanos encimados entre {p['cuarto']} y {q['cuarto']}.")
    errores = sum(1 for o in obs if o["tipo"] == "error")
    return dict(observaciones=obs, errores=errores, avisos=len(obs) - errores)
