"""Calendario de tipologías y corrientes arquitectónicas.

Ciclo de 7 meses que arranca en noviembre de 2026:
  nov-26 casas · dic-26 edificios · ene-27 naves · feb-27 plazas ·
  mar-27 hoteles y resorts · abr-27 parques de diversiones y acuáticos ·
  may-27 museos y centros recreativos · jun-27 vuelve a casas · ...
"""
import datetime as dt

INICIO = (2026, 11)

CICLO = ["casa", "edificio", "nave", "plaza", "hotel", "parque", "museo"]

NOMBRES = {
    "casa": "Casa habitación",
    "edificio": "Edificio de departamentos",
    "nave": "Nave industrial",
    "plaza": "Plaza comercial",
    "hotel": "Hotel / Resort",
    "parque": "Parque de diversiones / acuático",
    "museo": "Museo / Centro recreativo",
}

# Corrientes arquitectónicas. Cada una define cubierta, paleta y rasgos
# que el motor usa en plantas, fachadas y renders.
CORRIENTES = {
    "minimalista": dict(
        nombre="Minimalista", cubierta="plana", muro="#EEECE7", acento="#3A3A3A",
        techo="#D9D6CF", vidrio="#4C6A7A", ventana=0.55, rasgos=["volado", "muro_ciego"],
        materiales="Aplanado fino blanco, concreto aparente pulido, cancelería de aluminio negro, piso de porcelanato gran formato."),
    "contemporanea": dict(
        nombre="Contemporánea", cubierta="plana", muro="#E4E1DA", acento="#8A6A4F",
        techo="#BDB7AC", vidrio="#3E5C6E", ventana=0.65, rasgos=["volado", "celosia", "doble_altura"],
        materiales="Aplanado gris cálido, revestimiento de madera termotratada, piedra laja, cancelería negra de piso a techo."),
    "mediterranea": dict(
        nombre="Mediterránea", cubierta="dos_aguas", muro="#F4EFE6", acento="#2E5E8C",
        techo="#B5583A", vidrio="#3F5F75", ventana=0.40, rasgos=["arcos", "pergola", "terraza"],
        materiales="Aplanado rústico blanco, teja de barro, herrería azul, pisos de barro y talavera en acentos."),
    "californiana": dict(
        nombre="Californiana (Mission Revival)", cubierta="cuatro_aguas", muro="#EADBC4", acento="#6B4226",
        techo="#A0472C", vidrio="#3C5566", ventana=0.40, rasgos=["arcos", "pergola", "porche"],
        materiales="Aplanado texturizado arena, teja tipo misión, vigas de madera aparentes, cantera en marcos."),
    "colonial_mexicana": dict(
        nombre="Colonial mexicana", cubierta="plana_pretil", muro="#C9774F", acento="#4A3524",
        techo="#B9A58A", vidrio="#3A4F5C", ventana=0.30, rasgos=["patio", "arcos", "pretil"],
        materiales="Muros de block aplanados a la cal en tonos tierra, cantera, vigas de madera, herrería forjada, patio central."),
    "brutalista": dict(
        nombre="Brutalista", cubierta="plana", muro="#9C9A95", acento="#5E5C58",
        techo="#8C8A85", vidrio="#2F4552", ventana=0.35, rasgos=["volado", "muro_ciego", "parteluces"],
        materiales="Concreto aparente con cimbra de duela, elementos masivos, parteluces de concreto, vidrio claro."),
    "moderna_bauhaus": dict(
        nombre="Moderna (Bauhaus / Movimiento Moderno)", cubierta="plana", muro="#F2F2EE", acento="#B23A2E",
        techo="#CFCFC9", vidrio="#456577", ventana=0.60, rasgos=["ventana_corrida", "pilotis"],
        materiales="Aplanado blanco liso, ventanas corridas horizontales, columnas exentas (pilotis), acentos en colores primarios."),
    "industrial": dict(
        nombre="Industrial", cubierta="una_agua", muro="#8E4F3A", acento="#2B2B2B",
        techo="#5A5F63", vidrio="#3D5361", ventana=0.55, rasgos=["estructura_aparente"],
        materiales="Ladrillo aparente, acero estructural aparente, lámina corrugada, concreto pulido, cancelería tipo fábrica."),
    "nordica": dict(
        nombre="Nórdica (Escandinava)", cubierta="dos_aguas_pronunciada", muro="#2F3437", acento="#C8A97E",
        techo="#2A2D30", vidrio="#4A6878", ventana=0.50, rasgos=["sin_alero"],
        materiales="Revestimiento de madera oscura, cubierta metálica engargolada sin aleros, interiores en madera clara."),
    "art_deco": dict(
        nombre="Art Déco", cubierta="plana_pretil", muro="#E8DCC2", acento="#1F4E5F",
        techo="#CDBF9F", vidrio="#35505E", ventana=0.40, rasgos=["escalonado", "pretil", "verticalidad"],
        materiales="Aplanado color marfil, molduras geométricas escalonadas, acentos en verde petróleo y latón, terrazo."),
    "regionalismo_mexicano": dict(
        nombre="Regionalismo mexicano (arquitectura emocional)", cubierta="plana_pretil", muro="#D9564A", acento="#E7A93B",
        techo="#C9B79C", vidrio="#3C4F59", ventana=0.25, rasgos=["muro_ciego", "patio", "espejo_agua"],
        materiales="Muros de color intenso (rosa mexicano, ocre), planos ciegos, espejos de agua, celosías, luz cenital."),
    "high_tech": dict(
        nombre="High-Tech", cubierta="curva", muro="#C9D1D6", acento="#D0402B",
        techo="#B4BEC4", vidrio="#5C8296", ventana=0.80, rasgos=["estructura_aparente", "muro_cortina"],
        materiales="Muro cortina de vidrio, estructura de acero expuesta, paneles de aluminio compuesto, instalaciones aparentes."),
    "tropical_moderna": dict(
        nombre="Tropical moderna", cubierta="cuatro_aguas_baja", muro="#EDE6D8", acento="#6E5136",
        techo="#5D5146", vidrio="#3E5E66", ventana=0.60, rasgos=["alero_amplio", "celosia", "terraza"],
        materiales="Aleros amplios, celosías de madera, piedra natural, vegetación integrada, ventilación cruzada."),
    "mid_century": dict(
        nombre="Mid-Century Modern", cubierta="una_agua_baja", muro="#F0E9DB", acento="#C46A2D",
        techo="#6D6A63", vidrio="#3E6070", ventana=0.65, rasgos=["alero_amplio", "muro_cortina"],
        materiales="Cubiertas de baja pendiente con aleros, grandes ventanales, piedra y madera, acentos en naranja."),
    "deconstructivista": dict(
        nombre="Deconstructivista", cubierta="inclinada_irregular", muro="#D6D8DA", acento="#2A2E33",
        techo="#9DA2A7", vidrio="#3E5A6B", ventana=0.55, rasgos=["volado", "rotacion"],
        materiales="Volúmenes fragmentados e inclinados, paneles metálicos, vidrio estructural, geometría no ortogonal."),
    "parametrica": dict(
        nombre="Paramétrica / Orgánica", cubierta="curva", muro="#F1F0EC", acento="#8F8A80",
        techo="#E3E1DA", vidrio="#4A6A7C", ventana=0.60, rasgos=["celosia", "fachada_paramétrica"],
        materiales="Envolvente de paneles GRC/aluminio de geometría variable, celosía paramétrica, superficies curvas."),
    "neoclasica": dict(
        nombre="Neoclásica", cubierta="cuatro_aguas", muro="#EFE9DE", acento="#7A6F60",
        techo="#6E6A66", vidrio="#3A4E5A", ventana=0.40, rasgos=["columnata", "simetria", "frontón"],
        materiales="Simetría, columnatas, cornisas y molduras, cantera clara, cubierta de pizarra o lámina."),
    "japonesa": dict(
        nombre="Japonesa contemporánea", cubierta="dos_aguas_baja", muro="#E9E4DA", acento="#2F2A26",
        techo="#3B3B3B", vidrio="#4D6670", ventana=0.55, rasgos=["engawa", "celosia", "jardin"],
        materiales="Madera clara, celosías de listones, cubiertas de baja pendiente, jardín zen, engawa perimetral."),
}

ORDEN_CORRIENTES = list(CORRIENTES)

# Terrenos de casas que se rotan día con día (m², frente x fondo en m)
TERRENOS_CASA = [(180, 9.0, 20.0), (200, 10.0, 20.0), (300, 12.0, 25.0), (400, 16.0, 25.0)]


def indice_ciclo(fecha):
    meses = (fecha.year - INICIO[0]) * 12 + (fecha.month - INICIO[1])
    return meses % len(CICLO)


def tipologia(fecha):
    return CICLO[indice_ciclo(fecha)]


def corriente(fecha):
    """Distinta cada día; no repite corriente dentro de un mismo mes de 18 días seguidos."""
    base = (fecha - dt.date(*INICIO, 1)).days
    return ORDEN_CORRIENTES[(base * 7) % len(ORDEN_CORRIENTES)]


def plan_del_dia(fecha):
    t = tipologia(fecha)
    c = corriente(fecha)
    d = dict(fecha=fecha.isoformat(), tipologia=t, tipologia_nombre=NOMBRES[t],
             corriente=c, corriente_nombre=CORRIENTES[c]["nombre"])
    if t == "casa":
        area, fr, fo = TERRENOS_CASA[(fecha.day - 1) % 4]
        d["terreno"] = dict(area=area, frente=fr, fondo=fo)
    # variante del día (0..n) usada por las tipologías con subtipos
    d["variante"] = fecha.toordinal() % 2
    return d


if __name__ == "__main__":
    import json, sys
    f = dt.date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else dt.date.today()
    print(json.dumps(plan_del_dia(f), ensure_ascii=False, indent=2))
