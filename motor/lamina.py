"""Vista previa (JPG) y PDF vectorial de los DXF, dibujando las mismas entidades."""
import math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.patches import Arc, Circle

ACI = {1: "#D62828", 2: "#C9A400", 3: "#2A9D3F", 4: "#0096C7", 5: "#1D4ED8", 6: "#B5179E", 7: "#111111",
       8: "#707070", 9: "#9A9A9A", 30: "#E76F00", 34: "#8B5A2B", 82: "#4C8C3A", 252: "#6B6B6B"}
DASH = {"DASHED": (0, (6, 3)), "CENTER": (0, (12, 3, 3, 3)), "HIDDEN": (0, (3, 2)), "DOT": (0, (1, 2))}


def dibujar(dx, ruta_img=None, pdf=None, gris_arq=False, titulo=""):
    xs, ys = [], []
    for e in dx.ents:
        if e[0] == "POLYLINE":
            xs += [p[0] for p in e[2]]; ys += [p[1] for p in e[2]]
        elif e[0] == "LINE":
            d = dict(e[2]); xs += [d[10], d[11]]; ys += [d[20], d[21]]
        elif e[0] in ("CIRCLE", "ARC"):
            d = dict(e[2]); xs += [d[10] - d[40], d[10] + d[40]]; ys += [d[20] - d[40], d[20] + d[40]]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    W, H = x1 - x0, y1 - y0
    pad = max(W, H) * 0.02
    ar = (H + 2 * pad) / (W + 2 * pad)
    figw, figh = (18.0, 18.0 * ar) if ar <= 1 else (18.0 / ar, 18.0)
    fig = plt.figure(figsize=(figw, figh))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(x0 - pad, x1 + pad); ax.set_ylim(y0 - pad, y1 + pad)
    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")
    fig.canvas.draw()
    bb = ax.get_window_extent()
    xl = ax.get_xlim(); yl = ax.get_ylim()
    ppu = min(bb.width / (xl[1] - xl[0]), bb.height / (yl[1] - yl[0])) * 72 / fig.dpi   # pt por metro

    def estilo(capa):
        col, tipo = dx.capas.get(capa, (7, "CONTINUOUS"))
        c = ACI.get(col, "#333333")
        if gris_arq and capa.startswith("A-"):
            c = "#B8B8B8"
        lw = 0.9 if capa in ("A-MUROS", "E-COLUMNAS", "A-FACHADA", "A-CORTE") else 0.5
        if gris_arq and capa.startswith("A-"):
            lw = 0.35
        return c, DASH.get(tipo, "solid"), lw

    grupos = {}
    for e in dx.ents:
        if e[0] == "LINE":
            d = dict(e[2]); grupos.setdefault(e[1], []).append([(d[10], d[20]), (d[11], d[21])])
        elif e[0] == "POLYLINE":
            pts = list(e[2]) + ([e[2][0]] if e[3] else [])
            grupos.setdefault(e[1], []).append(pts)
    for capa, segs in grupos.items():
        c, ls, lw = estilo(capa)
        ax.add_collection(LineCollection(segs, colors=c, linewidths=lw, linestyles=ls))
    for e in dx.ents:
        if e[0] in ("CIRCLE", "ARC", "TEXT"):
            d = dict(e[2]); c, ls, lw = estilo(e[1])
            if e[0] == "CIRCLE":
                ax.add_patch(Circle((d[10], d[20]), d[40], fill=False, ec=c, lw=lw, ls=ls))
            elif e[0] == "ARC":
                ax.add_patch(Arc((d[10], d[20]), 2 * d[40], 2 * d[40], theta1=d[50], theta2=d[51], ec=c, lw=lw))
            else:
                fs = d[40] * ppu * 1.35
                if fs < 2.2:
                    continue
                cen = d.get(72) == 1
                ax.text(d[11] if cen else d[10], d[21] if cen else d[20], d[1], fontsize=fs, color=c,
                        rotation=d.get(50, 0), ha="center" if cen else "left", va="center" if cen else "baseline",
                        family="DejaVu Sans", rotation_mode="anchor")
    if ruta_img:
        fig.savefig(ruta_img, dpi=110, facecolor="white", pil_kwargs={"quality": 82})
    if pdf is not None:
        pdf.savefig(fig, facecolor="white")
    plt.close(fig)
