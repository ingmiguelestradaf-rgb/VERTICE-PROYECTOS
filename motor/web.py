"""Memoria descriptiva (Markdown) y sitio web estático (GitHub Pages)."""
import glob
import html
import json
import os

from .calendario import CICLO, NOMBRES

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
         "octubre", "noviembre", "diciembre"]
DISC = dict(hidraulica="Hidráulica", sanitaria="Sanitaria", pluvial="Pluvial", electrica="Eléctrica",
            gas="Gas LP", contra_incendio="Contra incendio")
SIS = dict(mamposteria="Mampostería confinada", marcos="Marcos de concreto reforzado", acero="Estructura de acero")


def fecha_larga(iso):
    a, m, d = iso.split("-")
    return f"{int(d)} de {MESES[int(m) - 1]} de {a}"


def memoria_md(r):
    L = [f"# {r['nombre']}", "", f"**Clave:** {r['clave']}  ·  **Fecha:** {fecha_larga(r['fecha'])}  ",
         f"**Tipología:** {r['tipologia_nombre']} {('— ' + r['subtipo']) if r['subtipo'] else ''}  ",
         f"**Corriente arquitectónica:** {r['corriente_nombre']}", ""]
    if r["concepto"]:
        L += ["## Concepto", "", r["concepto"], ""]
    L += ["## Datos generales", "", "| Concepto | Valor |", "|---|---|",
          f"| Terreno | {r['terreno']['frente']:.2f} x {r['terreno']['fondo']:.2f} m = {r['terreno']['area']:,.1f} m² |",
          f"| Uso de suelo | {r['uso_suelo']} |",
          f"| Área de desplante | {r['desplante']:,.1f} m² (COS {r['cos']}) |",
          f"| Área construida | {r['area_construida']:,.1f} m² (CUS {r['cus']}) |",
          f"| Niveles | {r['niveles']} |", f"| Altura máxima | {r['altura']} m |"]
    if r["cajones"]:
        L.append(f"| Cajones de estacionamiento | {r['cajones']} |")
    for k, v in r["usuarios"].items():
        L.append(f"| {k.replace('_', ' ').capitalize()} | {v:,} |")
    ex = r.get("extra") or {}
    for clave_, titulo_ in (("dictamen_arquitectura", "Dictamen del arquitecto"), ("dictamen_ingenieria", "Dictamen de ingeniería")):
        if ex.get(clave_):
            v_ = ex[clave_]
            L += ["", f"## {titulo_}", ""] + [f"- {i}" for i in (v_ if isinstance(v_, list) else [v_])]
    L += ["", "## Materiales y acabados", "", r["materiales"], "", "## Estructura", ""]
    for e in r["estructura"]:
        L += [f"### {e['bloque']} — {SIS[e['sistema']]}", "", "| Elemento | Propuesta | Observación |", "|---|---|---|"]
        L += [f"| {a} | {b} | {c} |" for a, b, c in e["tabla"]]
        L += ["", "Datos de cálculo: " + ", ".join(f"{k} = {v}" for k, v in e["calc"].items()), ""]
        L += [f"> {n}" for n in e["notas"]]
    L += ["## Instalaciones", ""]
    for k, filas in r["instalaciones"].items():
        L += [f"### {DISC.get(k, k)}", "", "| Concepto | Valor | Criterio |", "|---|---|---|"]
        L += [f"| {a} | {b} | {c} |" for a, b, c in filas] + [""]
    rv = r.get("revision")
    if rv:
        L += ["## Revisión de calidad", "", f"{rv['errores']} errores · {rv['avisos']} avisos", ""]
        L += [f"- **{o['tipo'].upper()}** · {o['nivel']}: {o['mensaje']}" for o in rv["observaciones"]] + [""]
    L += ["## Cuadro de áreas", "", "| Bloque | Nivel | Espacio | Medidas (m) | Área (m²) |", "|---|---|---|---|---|"]
    L += [f"| {a['bloque']} | {a['nivel']}{' x' + str(a['rep']) if a['rep'] > 1 else ''} | {a['espacio']} | {a['medidas']} | {a['area']:.2f} |"
          for a in r["areas"]]
    L += ["", "## Planos", ""] + [f"- **{h['clave']}** {h['titulo']} — `{h['dxf']}`" for h in r["hojas"]]
    L += ["", "---", "*Anteproyecto conceptual generado automáticamente por el motor Vértice. El predimensionamiento "
          "y los cálculos de instalaciones son preliminares: no sustituyen la memoria de cálculo definitiva, el estudio "
          "de mecánica de suelos ni la revisión y firma del DRO y corresponsables.*", ""]
    return "\n".join(L)


CSS = """
:root{--papel:#F3F0E8;--tinta:#1C1D1F;--suave:#5E6064;--linea:#D9D4C7;--acento:#B4532A;--tarjeta:#FBFAF6}
@media (prefers-color-scheme:dark){:root{--papel:#17181A;--tinta:#ECE8DF;--suave:#A3A19C;--linea:#33342F;--acento:#E07A4F;--tarjeta:#1F2022}}
*{box-sizing:border-box}body{margin:0;background:var(--papel);color:var(--tinta);font-family:'Archivo',system-ui,sans-serif;line-height:1.5}
a{color:inherit}.mono{font-family:'IBM Plex Mono',ui-monospace,monospace}
.wrap{max-width:1240px;margin:0 auto;padding:0 16px}
header.top{border-bottom:1px solid var(--linea);padding:18px 0}
header.top .wrap{display:flex;justify-content:space-between;align-items:baseline;gap:16px;flex-wrap:wrap}
.marca{font-weight:800;letter-spacing:.18em;font-size:14px;text-decoration:none}.marca span{color:var(--acento)}
.sub{color:var(--suave);font-size:13px}
h1{font-size:clamp(30px,5vw,58px);line-height:1.02;margin:36px 0 10px;font-weight:800;letter-spacing:-.02em}
h2{font-size:13px;letter-spacing:.16em;text-transform:uppercase;color:var(--suave);margin:44px 0 14px;font-weight:600}
h3{font-size:18px;margin:22px 0 8px}
.ciclo{display:grid;grid-template-columns:repeat(7,1fr);gap:6px;margin:22px 0 8px}
.ciclo div{border:1px solid var(--linea);padding:10px;font-size:12px;border-radius:2px}
.ciclo div.on{background:var(--tinta);color:var(--papel);border-color:var(--tinta)}
.ciclo b{display:block;font-size:13px}
.chips{display:flex;gap:8px;flex-wrap:wrap;margin:26px 0 18px}
.chips button{font:inherit;font-size:13px;border:1px solid var(--linea);background:transparent;color:var(--tinta);padding:6px 12px;border-radius:99px;cursor:pointer}
.chips button.on{background:var(--acento);border-color:var(--acento);color:#fff}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(290px,1fr));gap:18px;margin-bottom:60px}
.card{background:var(--tarjeta);border:1px solid var(--linea);text-decoration:none;display:block;transition:transform .15s}
.card:hover{transform:translateY(-2px)}
.card img{width:100%;aspect-ratio:16/10;object-fit:cover;display:block;border-bottom:1px solid var(--linea)}
.card .t{padding:12px 14px 14px}.card .f{font-size:12px;color:var(--suave)}.card .n{font-weight:700;font-size:16px;margin:2px 0 6px}
.tag{display:inline-block;font-size:11px;border:1px solid var(--linea);padding:2px 7px;margin-right:4px;border-radius:2px}
.hero img{width:100%;display:block;border:1px solid var(--linea)}
.datos{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));border-top:1px solid var(--linea);border-left:1px solid var(--linea);margin-top:22px}
.datos div{border-right:1px solid var(--linea);border-bottom:1px solid var(--linea);padding:12px 14px}
.datos b{display:block;font-size:21px}.datos span{font-size:12px;color:var(--suave)}
.concepto{font-size:19px;max-width:780px}
.dos{display:grid;grid-template-columns:1fr 1fr;gap:18px}@media(max-width:760px){.dos{grid-template-columns:1fr}.ciclo{grid-template-columns:repeat(4,1fr)}}
.laminas{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:14px}
.laminas a{display:block;background:#fff;border:1px solid var(--linea);text-decoration:none}
.laminas img{width:100%;aspect-ratio:4/3;object-fit:contain;display:block}
.laminas div{padding:8px 10px;font-size:13px;color:#222;border-top:1px solid #e5e5e5}
.desc a.btn{display:inline-block;border:1px solid var(--tinta);padding:9px 14px;margin:0 8px 8px 0;text-decoration:none;font-size:14px}
.desc a.btn.pri{background:var(--acento);border-color:var(--acento);color:#fff}
table{border-collapse:collapse;width:100%;font-size:14px;margin:6px 0 10px}
th,td{text-align:left;padding:7px 9px;border-bottom:1px solid var(--linea);vertical-align:top}th{font-size:12px;color:var(--suave);font-weight:600}
.tabla{overflow-x:auto}details summary{cursor:pointer;font-weight:600;padding:8px 0}
.aviso{font-size:13px;color:var(--suave);border-left:3px solid var(--acento);padding:8px 14px;margin:40px 0 60px}
"""
FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com"><link href="https://fonts.googleapis.com/css2?'
         'family=Archivo:wght@400;600;700;800&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">')


def _head(titulo, raiz=""):
    """raiz: ruta relativa a docs/ ('' en la galería, '../../' en cada proyecto)."""
    pwa = (f'<link rel="manifest" href="{raiz}manifest.json"><meta name="theme-color" content="#1C1D1F">'
           f'<link rel="icon" href="{raiz}icon-192.png"><link rel="apple-touch-icon" href="{raiz}apple-touch-icon.png">'
           '<meta name="apple-mobile-web-app-capable" content="yes"><meta name="mobile-web-app-capable" content="yes">'
           '<meta name="apple-mobile-web-app-title" content="Vértice">'
           f'<script>if("serviceWorker" in navigator)navigator.serviceWorker.register("{raiz}sw.js",{{scope:"{raiz or "./"}"}}).catch(function(){{}});</script>')
    return (f'<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cut">'
            f'<title>{html.escape(titulo)}</title>{pwa}{FONTS}<style>{CSS}</style></head><body>')


def _tabla(filas, cab):
    h = "".join(f"<th>{c}</th>" for c in cab)
    b = "".join("<tr>" + "".join(f"<td>{html.escape(str(x))}</td>" for x in f) + "</tr>" for f in filas)
    return f'<div class="tabla"><table><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table></div>'


def pagina_proyecto(r):
    e = html.escape
    datos = [(f"{r['terreno']['area']:,.0f} m²", f"Terreno {r['terreno']['frente']:.1f} x {r['terreno']['fondo']:.1f}"),
             (f"{r['area_construida']:,.0f} m²", "Área construida"), (str(r["niveles"]), "Niveles"),
             (f"{r['altura']} m", "Altura máxima"), (f"{r['cos']} / {r['cus']}", "COS / CUS")]
    if r["cajones"]:
        datos.append((str(r["cajones"]), "Cajones"))
    for k, v in list(r["usuarios"].items())[:2]:
        datos.append((f"{v:,}", k.replace("_", " ").capitalize()))
    s = [_head(r["nombre"], "../../"), '<header class="top"><div class="wrap"><a class="marca" href="../../index.html">VÉRTICE<span>·</span>PROYECTO DEL DÍA</a>',
         f'<span class="sub mono">{e(r["clave"])}</span></div></header><main class="wrap">',
         f'<p class="sub mono" style="margin-top:28px">{fecha_larga(r["fecha"])} · {e(r["tipologia_nombre"])}'
         f'{(" · " + e(r["subtipo"])) if r["subtipo"] else ""}</p>',
         f'<h1>{e(r["nombre"])}</h1><p class="sub">Corriente: <b>{e(r["corriente_nombre"])}</b></p>',
         '<div class="hero"><img src="render_aereo.jpg" alt="Render aéreo"></div>',
         '<div class="datos">' + "".join(f"<div><b>{a}</b><span>{b}</span></div>" for a, b in datos) + "</div>"]
    if r["concepto"]:
        s.append(f'<h2>Concepto</h2><p class="concepto">{e(r["concepto"])}</p>')
    ex = r.get("extra") or {}
    for clave_, titulo_ in (("dictamen_arquitectura", "Dictamen del arquitecto"), ("dictamen_ingenieria", "Dictamen de ingeniería")):
        if ex.get(clave_):
            v_ = ex[clave_]
            items = v_ if isinstance(v_, list) else [v_]
            s.append(f"<h2>{titulo_}</h2><ul>" + "".join(f"<li>{e(str(i))}</li>" for i in items) + "</ul>")
    s += [f'<h2>Materiales</h2><p>{e(r["materiales"])}</p>',
          '<h2>Vistas</h2><div class="dos"><img src="render_peatonal.jpg" style="width:100%;border:1px solid var(--linea)" alt="Render peatonal">'
          '<img src="render_aereo.jpg" style="width:100%;border:1px solid var(--linea)" alt="Render aéreo"></div>',
          '<h2>Descargas</h2><div class="desc">'
          f'<a class="btn pri" href="{e(r["zip"])}" download>Planos DXF (.zip)</a><a class="btn" href="planos.pdf">Juego de planos PDF</a>'
          '<a class="btn" href="memoria.md">Memoria (.md)</a><a class="btn" href="proyecto.json">Datos (.json)</a></div>',
          '<h2>Planos</h2><div class="laminas">']
    for h in r["hojas"]:
        s.append(f'<a href="{e(h["img"])}"><img loading="lazy" src="{e(h["img"])}" alt="{e(h["titulo"])}">'
                 f'<div><b>{e(h["clave"])}</b> {e(h["titulo"])} · <span class="mono" style="font-size:11px">'
                 f'<object><a href="{e(h["dxf"])}" download style="color:#B4532A">DXF</a></object></span></div></a>')
    s.append("</div><h2>Estructura</h2>")
    for est in r["estructura"]:
        s.append(f"<h3>{e(est['bloque'])} — {SIS[est['sistema']]}</h3>" + _tabla(est["tabla"], ["Elemento", "Propuesta", "Observación"]))
        s.append('<p class="sub mono" style="font-size:12px">' + " · ".join(f"{e(k)}={e(str(v))}" for k, v in est["calc"].items()) + "</p>")
        for n in est["notas"]:
            s.append(f'<p class="sub">{e(n)}</p>')
    s.append("<h2>Instalaciones</h2><div class='dos'>")
    for k, filas in r["instalaciones"].items():
        s.append(f"<div><h3>{DISC.get(k, k)}</h3>{_tabla(filas, ['Concepto', 'Valor', 'Criterio'])}</div>")
    rv = r.get("revision")
    if rv:
        estado = "Sin errores" if not rv["errores"] else f"{rv['errores']} errores"
        s.append(f"</div><h2>Revisión de calidad</h2><p><b>{estado}</b> · {rv['avisos']} avisos</p>")
        if rv["observaciones"]:
            s.append(_tabla([(o["tipo"].capitalize(), o["nivel"], o["mensaje"]) for o in rv["observaciones"]], ["Tipo", "Nivel", "Observación"]))
        s.append("<div>")
    s.append("</div><h2>Cuadro de áreas</h2><details><summary>Ver los "
             f"{len(r['areas'])} espacios</summary>")
    s.append(_tabla([(a["bloque"], a["nivel"] + (f" ×{a['rep']}" if a["rep"] > 1 else ""), a["espacio"], a["medidas"], f"{a['area']:.2f}")
                     for a in r["areas"]], ["Bloque", "Nivel", "Espacio", "Medidas (m)", "Área (m²)"]))
    s.append('</details><p class="aviso">Anteproyecto conceptual generado por el motor Vértice. El predimensionamiento estructural '
             'y los cálculos de instalaciones son preliminares y no sustituyen la memoria de cálculo definitiva, el estudio de '
             'mecánica de suelos ni la revisión y firma del DRO y corresponsables.</p></main></body></html>')
    return "".join(s)


def galeria(dir_proy, ruta_index):
    items = []
    for p in sorted(glob.glob(os.path.join(dir_proy, "*", "proyecto.json")), reverse=True):
        r = json.load(open(p, encoding="utf-8"))
        items.append(dict(clave=r["clave"], fecha=r["fecha"], nombre=r["nombre"], tipologia=r["tipologia"],
                          tipologia_nombre=r["tipologia_nombre"], corriente=r["corriente_nombre"],
                          area=r["area_construida"], terreno=r["terreno"]["area"], subtipo=r.get("subtipo", "")))
    with open(os.path.join(os.path.dirname(ruta_index), "proyectos.json"), "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=1)
    from .calendario import indice_ciclo
    import datetime as dt
    hoy = dt.date.fromisoformat(items[0]["fecha"]) if items else dt.date.today()
    ic = indice_ciclo(hoy)
    e = html.escape
    s = [_head("Vértice · Proyecto del día"),
         '<header class="top"><div class="wrap"><a class="marca" href="index.html">VÉRTICE<span>·</span>PROYECTO DEL DÍA</a>'
         '<span class="sub">Ingeniería, Arquitectura y Proyectos · Tijuana, B.C.</span></div></header><main class="wrap">',
         '<h1>Un proyecto completo,<br>cada día.</h1>',
         '<p class="sub" style="max-width:720px">Anteproyecto arquitectónico, estructural y de instalaciones con planos DXF, '
         'renders y memoria. Cada mes una tipología; cada día una corriente arquitectónica distinta.</p>'
         '<p class="desc" style="margin:14px 0 0"><a class="btn pri" href="vertice.apk" download>Descargar app Android (.apk)</a></p>'
         '<div class="ciclo">']
    for i, t in enumerate(CICLO):
        s.append(f'<div class="{"on" if i == ic else ""}"><b>{e(NOMBRES[t].split(" /")[0])}</b>Mes {i + 1} del ciclo</div>')
    s.append('</div><div class="chips" id="chips"><button class="on" data-t="">Todos</button>')
    for t in CICLO:
        if any(it["tipologia"] == t for it in items):
            s.append(f'<button data-t="{t}">{e(NOMBRES[t].split(" /")[0])}</button>')
    s.append('</div><div class="grid" id="grid">')
    for it in items:
        s.append(f'<a class="card" data-t="{it["tipologia"]}" href="proyectos/{e(it["clave"])}/index.html">'
                 f'<img loading="lazy" src="proyectos/{e(it["clave"])}/render_aereo.jpg" alt="">'
                 f'<div class="t"><div class="f mono">{fecha_larga(it["fecha"])}</div><div class="n">{e(it["nombre"])}</div>'
                 f'<span class="tag">{e(it["tipologia_nombre"])}</span><span class="tag">{it["area"]:,.0f} m²</span>'
                 f'<div class="f" style="margin-top:6px">{e(it["corriente"])}</div></div></a>')
    if not items:
        s.append('<p class="sub">Aún no hay proyectos.</p>')
    s.append('</div></main><script>document.getElementById("chips").addEventListener("click",function(ev){var b=ev.target.closest("button");'
             'if(!b)return;document.querySelectorAll("#chips button").forEach(function(x){x.classList.toggle("on",x===b)});'
             'var t=b.dataset.t;document.querySelectorAll("#grid .card").forEach(function(c){c.style.display=!t||c.dataset.t===t?"":"none"})});'
             '</script></body></html>')
    with open(ruta_index, "w", encoding="utf-8") as f:
        f.write("".join(s))
