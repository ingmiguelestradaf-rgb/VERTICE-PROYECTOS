"""Programas arquitectónicos por tipología.

Modelo (dicts JSON-serializables):
proyecto = {
  terreno: {frente, fondo}, bloques: [bloque], exteriores: [elemento], ...
}
bloque = {nombre, x, y, w, d, z0, sistema, claro_max, uso, colindancias:[S|N|O|E],
          niveles: [{nombre, h, rep, zonas}]}
zona  = {p: fracción del lado largo, cuartos: [cuarto]}
cuarto = {n: nombre, p: fracción del ancho de la zona, t: tipo, sub: [zonas]?,
          grupo: bool?, inv: bool?}

Tipos: social privado humedo cocina servicio circ escalera ext tecnico almacen grande
"""
import math

T = dict(social="social", priv="privado", hum="humedo", coc="cocina", serv="servicio",
         circ="circ", esc="escalera", ext="ext", tec="tecnico", alm="almacen", gran="grande")


def C(n, p, t, sub=None, grupo=False, inv=False):
    d = dict(n=n, p=p, t=t)
    if sub:
        d["sub"] = sub
    if grupo:
        d["grupo"] = True
    if inv:
        d["inv"] = True
    return d


def G(p, sub, inv=False):
    return C("", p, "grupo", sub=sub, grupo=True, inv=inv)


def Z(p, cuartos):
    return dict(p=p, cuartos=cuartos)


def N(nombre, h, zonas, rep=1):
    return dict(nombre=nombre, h=h, rep=rep, zonas=zonas)


def B(nombre, x, y, w, d, niveles, sistema="marcos", claro_max=8.0, uso="habitacional",
      z0=0.0, colindancias=()):
    return dict(nombre=nombre, x=round(x, 2), y=round(y, 2), w=round(w, 2), d=round(d, 2),
                z0=z0, niveles=niveles, sistema=sistema, claro_max=claro_max, uso=uso,
                colindancias=list(colindancias))


def E(tipo, x, y, w=0, d=0, r=0, **kw):
    e = dict(tipo=tipo, x=round(x, 2), y=round(y, 2), w=round(w, 2), d=round(d, 2), r=r)
    e.update(kw)
    return e


def _seed(plan):
    return int(plan["fecha"].replace("-", ""))


# ------------------------------------------------------------------ CASA
def casa(plan):
    t = plan["terreno"]
    fr, fo, area = t["frente"], t["fondo"], t["area"]
    amplia = area >= 300
    lat = 0.0 if fr <= 10 else (1.0 if fr <= 12 else 1.5)
    frente_lib = 3.0 if not amplia else 3.5
    # medidas cerradas a paños exteriores de muro (muro exterior 0.25 m al eje del bloque)
    d_ext = math.floor((fo - frente_lib - max(3.0, fo * 0.15)) * 2) / 2
    post = fo - frente_lib - d_ext
    inset = 0.125
    w, d = fr - 2 * lat - 0.25, d_ext - 0.25
    col = ["O", "E"] if lat == 0 else []
    rec4 = area >= 400
    # bandas con medidas reales: cochera 5.6 m de fondo, banda de escalera+pasillo 3.4 m
    z1, z2 = 5.6 / d, 3.4 / d
    z3 = 1 - z1 - z2
    pe = 2.3 / w                        # ancho de escalera en "U" (2 tramos de 1.10 m)
    if not amplia:
        pb = N("Planta baja", 2.7, [
            Z(z1, [C("Cochera", 3.4 / w, T["ext"]), C("Acceso", (w - 3.4 - 1.7) / w, T["circ"]),
                   G(1.7 / w, [Z(.55, [C("Bodega", 1, T["alm"])]), Z(.45, [C("Medio baño", 1, T["hum"])])])]),
            Z(z2, [C("Escalera", pe, T["esc"]), C("Vestíbulo", 1 - pe, T["circ"])]),
            Z(z3, [C("Sala-comedor", .60, T["social"]),
                   G(.40, [Z(.30, [C("Lavandería", 1, T["serv"])]), Z(.70, [C("Cocina", 1, T["coc"])])])]),
        ])
        bano = max(1.4, round(w * 0.17, 2))
        r2 = max((w - bano) / 2, 2.3 + 1.3)
        rr = w - bano - r2
        pa = N("Planta alta", 2.7, [
            Z(z1, [C("Recámara 2", r2 / w, T["priv"]), C("Baño 2", bano / w, T["hum"]), C("Recámara 3", rr / w, T["priv"])]),
            Z(z2, [C("Escalera", pe, T["esc"]), C("Pasillo", 1 - pe, T["circ"])]),
            Z(z3, [C("Recámara principal", .58, T["priv"]),
                   G(.42, [Z(.42, [C("Vestidor", 1, T["priv"])]), Z(.58, [C("Baño principal", 1, T["hum"])])])]),
        ])
    else:
        mb = 1.7 / w
        pb = N("Planta baja", 2.8, [
            Z(z1, [C("Cochera doble", 5.8 / w, T["ext"]), C("Acceso", 1.8 / w, T["circ"]),
                   C("Estudio", 1 - 7.6 / w, T["social"])]),
            Z(z2, [C("Escalera", pe, T["esc"]), C("Vestíbulo", 1 - pe - mb, T["circ"]), C("Medio baño", mb, T["hum"])]),
            Z(z3, [C("Sala", .38, T["social"]), C("Comedor", .27, T["social"]),
                   G(.35, [Z(.30, [C("Lavandería", 1, T["serv"])]), Z(.70, [C("Cocina", 1, T["coc"])])])]),
        ])
        bano = 1.8
        r2 = max((w - bano) / 2, 2.3 + 1.3)
        rr = w - bano - r2
        z3c = [C("Recámara principal", .45 if rec4 else .58, T["priv"]),
               G(.25 if rec4 else .42, [Z(.42, [C("Vestidor", 1, T["priv"])]), Z(.58, [C("Baño principal", 1, T["hum"])])])]
        if rec4:
            z3c.append(C("Recámara 4", .30, T["priv"]))
        pa = N("Planta alta", 2.8, [
            Z(z1, [C("Recámara 2", r2 / w, T["priv"]), C("Baño 2", bano / w, T["hum"]), C("Recámara 3", rr / w, T["priv"])]),
            Z(z2, [C("Escalera", pe, T["esc"]), C("Estancia familiar", 1 - pe, T["circ"])]),
            Z(z3, z3c),
        ])
    bloques = [B("Casa", lat + inset, frente_lib + inset, w, d, [pb, pa], sistema="mamposteria", claro_max=5.0,
                 uso="habitacional", colindancias=col)]
    ext = [E("area_verde", 0, fo - post, fr, post, nombre="Patio posterior"),
           E("acceso", 0, 0, fr, frente_lib, nombre="Cajón y jardín frontal")]
    if area >= 400:
        ext.append(E("alberca", lat + 1.5, fo - post + 0.8, min(8, w - 3), max(2.0, post - 1.6), nombre="Alberca"))
    hab = 4 + (1 if area >= 300 else 0) + (1 if rec4 else 0)
    return dict(terreno=dict(frente=fr, fondo=fo), bloques=bloques, exteriores=ext,
                usuarios=dict(ocupantes=hab), uso_suelo="Habitacional unifamiliar")


# -------------------------------------------------------------- EDIFICIO
def _depto(nombre, p, inv=False):
    return C(nombre, p, "unidad", inv=inv, sub=[
        Z(.38, [C("Sala-comedor", .60, T["social"]), C("Recámara 2", .40, T["priv"])]),
        Z(.20, [C("Cocina", .35, T["coc"]), C("Vestíbulo", .40, T["circ"]), C("Baño 2", .25, T["hum"])]),
        Z(.42, [C("Recámara principal", .45, T["priv"]),
                G(.25, [Z(.55, [C("Baño principal", 1, T["hum"])]), Z(.45, [C("Lavandería", 1, T["serv"])])]),
                C("Recámara 3", .30, T["priv"])]),
    ])


def edificio(plan):
    s = _seed(plan)
    niveles_tipo = 5 + s % 8            # 5..12 niveles tipo
    ancho = [24.0, 30.0, 36.0][s % 3]
    fondo = 26.0
    lote_fr, lote_fo = ancho + 12, fondo + 24
    por_lado = 2 if ancho < 30 else 3
    p = 1 / por_lado
    nucleo = G(.30, [Z(.5, [C("Escaleras", 1, T["esc"])]), Z(.5, [C("Elevadores", 1, T["esc"])])])
    pb = N("Planta baja", 4.5, [
        Z(.40, [C("Local comercial 1", .35, T["ext"]), C("Lobby", .30, T["circ"]), C("Local comercial 2", .35, T["ext"])]),
        Z(.20, [C("Cuarto de máquinas", .25, T["tec"]), nucleo, C("Administración", .20, T["serv"]),
                C("Bodegas", .25, T["alm"])]),
        Z(.40, [C("Gimnasio", .45, T["social"]), C("Cuarto de residuos", .15, T["serv"]),
                C("Salón de usos múltiples", .40, T["social"])]),
    ])
    letras = "ABCDEF"
    tipo = N("Nivel tipo", 3.0, [
        Z(.40, [_depto(f"Depto {letras[i]}", p) for i in range(por_lado)]),
        Z(.20, [C("Pasillo", .25, T["circ"]), nucleo, C("Pasillo ", .45, T["circ"])]),
        Z(.40, [_depto(f"Depto {letras[i + por_lado]}", p, inv=True) for i in range(por_lado)]),
    ], rep=niveles_tipo)
    bloques = [B("Torre", 6, 12, ancho, fondo, [pb, tipo], sistema="marcos", claro_max=8.0, uso="habitacional")]
    ext = [E("estacionamiento", 0, 0, lote_fr, 10.5, nombre="Estacionamiento visitas"),
           E("area_verde", 0, 12 + fondo + 1, lote_fr, lote_fo - fondo - 13, nombre="Área verde y amenidades")]
    deptos = por_lado * 2 * niveles_tipo
    return dict(terreno=dict(frente=lote_fr, fondo=lote_fo), bloques=bloques, exteriores=ext,
                usuarios=dict(ocupantes=deptos * 4, departamentos=deptos),
                uso_suelo="Habitacional plurifamiliar con comercio en PB",
                nota_estacionamiento="Estacionamiento de residentes en sótano (fuera del alcance del anteproyecto diario).")


# ------------------------------------------------------------------ NAVE
def nave(plan):
    s = _seed(plan)
    area = [2500, 4000, 6000, 8000][s % 4]
    w = round(math.sqrt(area * 0.62) / 6) * 6          # claro múltiplo de 6 m
    d = round(area / w / 9) * 9                          # crujías de 9 m
    h = [10.0, 11.0, 12.0][s % 3]
    ofi_w = min(w * 0.5, 30)
    lote_fr = w + 12
    lote_fo = 14 + 22 + d + 36
    ofi = B("Oficinas", 6 + (w - ofi_w) / 2, 22, ofi_w, 12, [
        N("Planta baja oficinas", 3.5, [Z(.5, [C("Recepción", .35, T["circ"]), C("Sala de juntas", .30, T["social"]),
                                              C("Sanitarios", .35, T["hum"])]),
                                       Z(.5, [C("Comedor", .45, T["social"]), C("Escalera", .15, T["esc"]),
                                              C("Cocineta", .15, T["coc"]), C("Site", .25, T["tec"])])]),
        N("Planta alta oficinas", 3.5, [Z(.5, [C("Oficinas abiertas", .65, T["social"]), C("Sanitarios", .35, T["hum"])]),
                                       Z(.5, [C("Gerencia", .45, T["social"]), C("Escalera", .15, T["esc"]),
                                              C("Archivo", .40, T["alm"])])]),
    ], sistema="marcos", claro_max=7.0, uso="oficinas")
    nav = B("Nave", 6, 34, w, d, [
        N("Nave", h, [Z(.10, [C("Vestidores y sanitarios", .30, T["hum"]), C("Mantenimiento", .25, T["serv"]),
                               C("Cuarto eléctrico", .15, T["tec"]), C("Cuarto de bombas CI", .15, T["tec"]),
                               C("Residuos", .15, T["serv"])]),
                      Z(.80, [C("Área de producción / almacenaje", 1, T["gran"])]),
                      Z(.10, [C("Andenes de carga", .75, T["ext"]), C("Control de embarques", .25, T["serv"])])]),
    ], sistema="acero", claro_max=9.0, uso="industrial")
    ext = [E("estacionamiento", 6, 0, lote_fr - 12, 20, nombre="Estacionamiento personal"),
           E("caseta", 1, 2, 4, 4, nombre="Caseta de vigilancia"),
           E("patio", 0, 34 + d, lote_fr, 36, nombre="Patio de maniobras"),
           E("cisterna", lote_fr - 5, 26, 4, 6, nombre="Cisterna contra incendio")]
    return dict(terreno=dict(frente=lote_fr, fondo=lote_fo), bloques=[ofi, nav], exteriores=ext,
                usuarios=dict(ocupantes=int(area / 40)), altura_libre=h, uso_suelo="Industrial ligera")


# ----------------------------------------------------------------- PLAZA
def plaza(plan):
    s = _seed(plan)
    dos = s % 2 == 1
    w, d = [72.0, 84.0, 96.0][s % 3], 30.0
    lote_fr, lote_fo = w + 16, d + 62
    n_loc = 8
    pl = .40 / n_loc
    nucleo = G(.12, [Z(.5, [C("Sanitarios H", .5, T["hum"]), C("Sanitarios M", .5, T["hum"])]),
                     Z(.5, [C("Escalera y elevador" if dos else "Cuarto de limpieza", 1, T["esc"] if dos else T["serv"])])])
    serv = Z(.18, [C("Pasillo de servicio", .70, T["circ"]), C("Cuarto eléctrico", .10, T["tec"]),
                   C("Basura", .10, T["serv"]), C("Bodega", .10, T["alm"])])
    pb = N("Planta baja", 5.0, [
        Z(.14, [C("Portal comercial", 1, T["circ"])]),
        Z(.68, [C("Tienda ancla", .30, T["ext"])] + [C(f"Local {i + 1}", pl, T["ext"]) for i in range(n_loc)]
              + [C("Food court", .18, T["gran"]), nucleo]),
        serv])
    niveles = [pb]
    if dos:
        niveles.append(N("Planta alta", 4.5, [
            Z(.14, [C("Corredor / balcón", 1, T["circ"])]),
            Z(.68, [C("Gimnasio", .30, T["gran"])] + [C(f"Local {i + 9}", pl, T["ext"]) for i in range(n_loc)]
                  + [C("Terraza de comida", .18, T["gran"]), nucleo]),
            serv]))
    bloques = [B("Plaza", 8, lote_fo - d - 6, w, d, niveles, sistema="marcos", claro_max=9.0, uso="comercial")]
    ext = [E("estacionamiento", 2, 2, lote_fr - 4, lote_fo - d - 12, nombre="Estacionamiento"),
           E("patio", 8, lote_fo - 6, w, 6, nombre="Patio de servicio / carga")]
    return dict(terreno=dict(frente=lote_fr, fondo=lote_fo), bloques=bloques, exteriores=ext,
                usuarios=dict(ocupantes=int(w * d * len(niveles) / 5)), uso_suelo="Comercial y de servicios")


# ----------------------------------------------------------------- HOTEL
def _hab(i, p):
    return C(f"Hab. {i}", p, "unidad", sub=[Z(.70, [C("Habitación", 1, T["priv"])]),
                                            Z(.30, [C("Baño", .6, T["hum"]), C("Closet", .4, T["alm"])])], inv=True)


def hotel(plan):
    s = _seed(plan)
    if plan.get("variante", 0) == 0:          # hotel urbano
        torre_n = 7 + s % 8
        lote_fr, lote_fo = 56.0, 74.0
        pod = B("Podio", 8, 10, 40, 48, [
            N("Planta baja", 5.0, [Z(.35, [C("Lobby y recepción", .40, T["circ"]), C("Restaurante", .35, T["social"]),
                                           C("Bar", .25, T["social"])]),
                                   Z(.25, [C("Administración", .30, T["serv"]),
                                           G(.20, [Z(.5, [C("Escaleras", 1, T["esc"])]), Z(.5, [C("Elevadores", 1, T["esc"])])]),
                                           C("Cocina", .30, T["coc"]), C("Sanitarios", .20, T["hum"])]),
                                   Z(.40, [C("Salón de eventos", .50, T["gran"]), C("Lavandería y ropería", .25, T["serv"]),
                                           C("Cuarto de máquinas", .25, T["tec"])])]),
            N("Nivel amenidades", 4.5, [Z(.35, [C("Gimnasio", .35, T["social"]), C("Spa", .35, T["social"]),
                                                C("Business center", .30, T["social"])]),
                                        Z(.25, [C("Vestidores", .30, T["hum"]),
                                                G(.20, [Z(.5, [C("Escaleras", 1, T["esc"])]), Z(.5, [C("Elevadores", 1, T["esc"])])]),
                                                C("Salas de juntas", .50, T["social"])]),
                                        Z(.40, [C("Terraza con alberca", 1, T["ext"])])])],
            sistema="marcos", claro_max=9.0, uso="hotel")
        k = 8
        torre = B("Torre de habitaciones", 8, 10, 40, 18, [
            N("Nivel tipo habitaciones", 3.2, [
                Z(.42, [_hab(i + 1, 1 / k) for i in range(k)]),
                Z(.16, [C("Pasillo", 1, T["circ"])]),
                Z(.42, [_hab(i + 9, 1 / k) for i in range(3)] +
                       [G(2 / k, [Z(.5, [C("Escaleras", 1, T["esc"])]), Z(.5, [C("Elevadores y ropería", 1, T["esc"])])])] +
                       [_hab(i + 12, 1 / k) for i in range(3)])], rep=torre_n)],
            sistema="marcos", claro_max=8.0, uso="hotel", z0=9.5)
        for z in torre["niveles"][0]["zonas"][2]["cuartos"]:
            if z["t"] == "unidad":
                z["inv"] = False
        habs = 14 * torre_n
        ext = [E("acceso", 0, 0, lote_fr, 8, nombre="Bahía de ascenso y descenso"),
               E("estacionamiento", 0, 60, lote_fr, 14, nombre="Estacionamiento / acceso a sótano")]
        return dict(terreno=dict(frente=lote_fr, fondo=lote_fo), bloques=[pod, torre], exteriores=ext,
                    usuarios=dict(ocupantes=habs * 2, habitaciones=habs), subtipo="Hotel urbano",
                    uso_suelo="Turístico / hospedaje")
    # resort
    lote_fr, lote_fo = 130.0, 150.0
    main = B("Edificio principal", 35, 12, 60, 24, [
        N("Planta baja", 4.5, [Z(.5, [C("Lobby", .35, T["circ"]), C("Restaurante", .40, T["social"]), C("Bar", .25, T["social"])]),
                               Z(.5, [C("Cocina", .30, T["coc"]), C("Administración", .20, T["serv"]),
                                      C("Escalera", .10, T["esc"]), C("Sanitarios", .15, T["hum"]),
                                      C("Cuarto de máquinas", .25, T["tec"])])]),
        N("Planta alta", 4.0, [Z(.5, [C("Spa", .45, T["social"]), C("Gimnasio", .30, T["social"]), C("Terraza", .25, T["ext"])]),
                               Z(.5, [C("Salón de eventos", .55, T["gran"]), C("Escalera", .10, T["esc"]),
                                      C("Vestidores", .35, T["hum"])])])],
        sistema="marcos", claro_max=8.0, uso="hotel")
    villas = []
    pos = [(10, 52), (90, 52), (10, 100), (90, 100), (50, 122)]
    hab_n = 0
    for i, (x, y) in enumerate(pos):
        k = 5
        villas.append(B(f"Villa {i + 1}", x, y, 30, 12, [
            N("Planta baja", 3.2, [Z(1, [_hab(j + 1 + hab_n, 1 / k) for j in range(k)])]),
            N("Planta alta", 3.2, [Z(1, [_hab(j + 6 + hab_n, 1 / k) for j in range(k)])])],
            sistema="marcos", claro_max=6.0, uso="hotel"))
        hab_n += 10
    ext = [E("alberca", 45, 62, 40, 22, nombre="Alberca principal"),
           E("alberca", 52, 90, 16, 8, nombre="Chapoteadero"),
           E("area_verde", 0, 40, lote_fr, lote_fo - 40, nombre="Jardines"),
           E("estacionamiento", 0, 0, 30, 36, nombre="Estacionamiento")]
    return dict(terreno=dict(frente=lote_fr, fondo=lote_fo), bloques=[main] + villas, exteriores=ext,
                usuarios=dict(ocupantes=hab_n * 2, habitaciones=hab_n), subtipo="Resort",
                uso_suelo="Turístico / hospedaje")


# ---------------------------------------------------------------- PARQUE
def parque(plan):
    acuatico = plan.get("variante", 0) == 1
    lote_fr, lote_fo = 180.0, 220.0
    acceso = B("Acceso y taquillas", 60, 30, 60, 15, [N("Planta baja", 5.0, [
        Z(1, [C("Taquillas", .20, T["serv"]), C("Vestíbulo de acceso", .30, T["circ"]),
              C("Enfermería", .10, T["serv"]), C("Sanitarios", .15, T["hum"]),
              C("Administración", .15, T["serv"]), C("Tienda", .10, T["social"])])])],
        sistema="acero", claro_max=8.0, uso="reunion")
    rest = B("Restaurante y food court", 120, 70, 40, 24, [N("Planta baja", 5.5, [
        Z(.65, [C("Área de comensales", 1, T["gran"])]),
        Z(.35, [C("Cocina", .45, T["coc"]), C("Sanitarios", .25, T["hum"]), C("Bodega", .30, T["alm"])])])],
        sistema="acero", claro_max=9.0, uso="reunion")
    bloques = [acceso, rest]
    ext = [E("estacionamiento", 0, 0, lote_fr, 26, nombre="Estacionamiento"),
           E("plaza", 50, 45, 80, 20, nombre="Plaza de acceso")]
    if acuatico:
        bloques.append(B("Vestidores y regaderas", 20, 70, 36, 16, [N("Planta baja", 4.0, [
            Z(1, [C("Vestidores H", .30, T["hum"]), C("Regaderas", .20, T["hum"]), C("Vestidores M", .30, T["hum"]),
                  C("Lockers", .20, T["alm"])])])], sistema="marcos", claro_max=6.0, uso="reunion"))
        bloques.append(B("Cuarto de máquinas y filtrado", 20, 190, 30, 14, [N("Planta baja", 4.5, [
            Z(1, [C("Filtros y bombas", .6, T["tec"]), C("Cloración", .2, T["tec"]), C("Taller", .2, T["serv"])])])],
            sistema="marcos", claro_max=7.0, uso="industrial"))
        ext += [E("alberca", 60, 100, 50, 30, nombre="Alberca de olas"),
                E("rio", 90, 160, 0, 0, r=28, nombre="Río lento"),
                E("alberca", 20, 100, 24, 16, nombre="Alberca infantil"),
                E("toboganes", 140, 120, 12, 12, h=18, nombre="Torre de toboganes"),
                E("palapas", 20, 130, 30, 30, nombre="Zona de palapas"),
                E("area_verde", 0, 26, lote_fr, lote_fo - 26, nombre="Áreas verdes")]
        sub = "Parque acuático"
        cap = 3500
    else:
        bloques.append(B("Atracción bajo techo (dark ride)", 20, 150, 50, 36, [N("Nave de atracción", 12.0, [
            Z(.75, [C("Recorrido de atracción", 1, T["gran"])]),
            Z(.25, [C("Fila y preshow", .6, T["circ"]), C("Cuarto de control", .2, T["tec"]), C("Taller", .2, T["serv"])])])],
            sistema="acero", claro_max=10.0, uso="reunion"))
        ext += [E("rueda", 140, 160, r=22, nombre="Rueda de la fortuna"),
                E("montaña_rusa", 95, 125, 70, 50, h=24, nombre="Montaña rusa"),
                E("carrusel", 40, 105, r=9, nombre="Carrusel"),
                E("juegos", 20, 70, 30, 20, nombre="Zona infantil"),
                E("area_verde", 0, 26, lote_fr, lote_fo - 26, nombre="Áreas verdes")]
        sub = "Parque de diversiones"
        cap = 5000
    return dict(terreno=dict(frente=lote_fr, fondo=lote_fo), bloques=bloques, exteriores=ext,
                usuarios=dict(ocupantes=cap, visitantes_dia=cap), subtipo=sub, uso_suelo="Recreativo")


# ----------------------------------------------------------------- MUSEO
def museo(plan):
    if plan.get("variante", 0) == 0:
        lote_fr, lote_fo = 90.0, 110.0
        nuc = G(.16, [Z(.5, [C("Escalera", 1, T["esc"])]), Z(.5, [C("Elevador y montacargas", 1, T["esc"])])])
        m = B("Museo", 20, 26, 54, 42, [
            N("Planta baja", 6.0, [Z(.30, [C("Vestíbulo y taquilla", .40, T["circ"]), C("Tienda", .20, T["social"]),
                                           C("Cafetería", .40, T["social"])]),
                                   Z(.40, [C("Sala permanente 1", .44, T["gran"]), nuc, C("Sala temporal", .40, T["gran"])]),
                                   Z(.30, [C("Auditorio", .35, T["gran"]), C("Talleres educativos", .25, T["social"]),
                                           C("Acervo y bodega", .25, T["alm"]), C("Andén de carga", .15, T["ext"])])]),
            N("Planta alta", 5.5, [Z(.30, [C("Terraza mirador", .40, T["ext"]), C("Biblioteca", .35, T["social"]),
                                           C("Sanitarios", .25, T["hum"])]),
                                   Z(.40, [C("Sala permanente 2", .44, T["gran"]), nuc, C("Sala permanente 3", .40, T["gran"])]),
                                   Z(.30, [C("Oficinas", .35, T["social"]), C("Conservación y restauración", .35, T["serv"]),
                                           C("Cuarto de máquinas", .30, T["tec"])])])],
            sistema="marcos", claro_max=12.0, uso="reunion")
        ext = [E("plaza", 10, 10, 74, 14, nombre="Plaza de acceso"),
               E("espejo_agua", 22, 12, 24, 6, nombre="Espejo de agua"),
               E("estacionamiento", 0, 72, lote_fr, 38, nombre="Estacionamiento"),
               E("area_verde", 76, 26, 14, 42, nombre="Jardín escultórico")]
        return dict(terreno=dict(frente=lote_fr, fondo=lote_fo), bloques=[m], exteriores=ext,
                    usuarios=dict(ocupantes=900, visitantes_dia=1500), subtipo="Museo", uso_suelo="Cultural")
    lote_fr, lote_fo = 110.0, 120.0
    c = B("Centro recreativo", 15, 24, 70, 44, [N("Planta baja", 9.0, [
        Z(.25, [C("Recepción", .25, T["circ"]), C("Cafetería", .30, T["social"]), C("Ludoteca", .25, T["social"]),
                C("Administración", .20, T["serv"])]),
        Z(.50, [C("Gimnasio de duela", .40, T["gran"]), C("Vestidores", .15, T["hum"]),
                C("Alberca semiolímpica techada", .45, T["gran"])]),
        Z(.25, [C("Salones de usos múltiples", .35, T["social"]), C("Talleres", .25, T["social"]),
                C("Sanitarios", .15, T["hum"]), C("Cuarto de máquinas", .25, T["tec"])])])],
        sistema="acero", claro_max=12.0, uso="reunion")
    ext = [E("estacionamiento", 0, 0, lote_fr, 20, nombre="Estacionamiento"),
           E("cancha", 15, 76, 30, 16, nombre="Cancha de usos múltiples"),
           E("cancha", 52, 76, 30, 16, nombre="Cancha de fútbol rápido"),
           E("area_verde", 0, 96, lote_fr, 24, nombre="Parque y juegos")]
    return dict(terreno=dict(frente=lote_fr, fondo=lote_fo), bloques=[c], exteriores=ext,
                usuarios=dict(ocupantes=800, visitantes_dia=1200), subtipo="Centro recreativo", uso_suelo="Recreativo")


GENERADORES = dict(casa=casa, edificio=edificio, nave=nave, plaza=plaza, hotel=hotel, parque=parque, museo=museo)


def generar(plan):
    return GENERADORES[plan["tipologia"]](plan)
