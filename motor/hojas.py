"""Juego de planos: crea láminas DXF, sus vistas JPG, el PDF del juego y el ZIP de DXF."""
import os
import re
import unicodedata
import zipfile

from matplotlib.backends.backend_pdf import PdfPages

from .dxf import DXF
from . import planos, lamina, instalaciones as inst, plano_estructural as pe
from .ejec import arq as arq_ej, estplan


def slug(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


class Juego:
    def __init__(self, carpeta, datos, notas, nombre_pdf="planos.pdf", jpg=True):
        self.carpeta, self.datos, self.notas, self.jpg = carpeta, datos, notas, jpg
        os.makedirs(os.path.join(carpeta, "planos"), exist_ok=True)
        if jpg:
            os.makedirs(os.path.join(carpeta, "laminas"), exist_ok=True)
        self.pdf_ruta = os.path.join(carpeta, nombre_pdf)
        self.pdf = PdfPages(self.pdf_ruta)
        self.hojas = []

    def nueva(self, clave, titulo, gris=False, disciplina=""):
        dx = DXF()
        planos.capas_arq(dx); inst.capas(dx); pe.capas(dx); arq_ej.capas(dx); estplan.capas(dx)
        return dict(dx=dx, clave=clave, titulo=titulo, gris=gris, disciplina=disciplina)

    def cerrar(self, h):
        dx = h["dx"]
        xs, ys = [0.0], [0.0]
        for e in dx.ents:
            if e[0] == "POLYLINE":
                xs += [p[0] for p in e[2]]; ys += [p[1] for p in e[2]]
            else:
                d = dict(e[2]); xs.append(d.get(10, 0)); ys.append(d.get(20, 0))
                if 11 in d:
                    xs.append(d[11]); ys.append(d[21])
        planos.cuadro(dx, min(xs), min(ys), max(xs), max(ys), dict(self.datos, plano=f"{h['clave']}  {h['titulo']}", notas=self.notas))
        ruta = os.path.join(self.carpeta, "planos", f"{h['clave']}_{slug(h['titulo'])}.dxf")
        dx.guardar(ruta)
        img = os.path.join(self.carpeta, "laminas", f"{h['clave']}.jpg") if self.jpg else None
        lamina.dibujar(dx, img, self.pdf, gris_arq=h["gris"])
        self.hojas.append(dict(clave=h["clave"], titulo=h["titulo"], disciplina=h.get("disciplina", ""),
                               dxf=os.path.relpath(ruta, self.carpeta), img=os.path.relpath(img, self.carpeta) if img else None))

    def imagen(self, ruta_png, titulo):
        import matplotlib.pyplot as plt
        import matplotlib.image as mpimg
        im = mpimg.imread(ruta_png)
        fig = plt.figure(figsize=(17, 17 * im.shape[0] / im.shape[1]))
        ax = fig.add_axes([0, 0, 1, 1]); ax.imshow(im); ax.axis("off")
        self.pdf.savefig(fig); plt.close(fig)

    def fin(self, nombre_zip):
        self.pdf.close()
        zp = os.path.join(self.carpeta, nombre_zip)
        with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
            for hj in self.hojas:
                z.write(os.path.join(self.carpeta, hj["dxf"]), os.path.basename(hj["dxf"]))
        return zp


class Fila:
    """Acomoda dibujos de izquierda a derecha en una lámina."""

    def __init__(self, dx, sep, y_titulo=None, capa="T-TITULO"):
        self.dx, self.x, self.sep, self.y_titulo, self.capa = dx, 0.0, sep, y_titulo, capa

    def poner(self, ancho, alto, dibujar, titulo, h=None):
        ox = self.x
        dibujar(ox)
        h = h or max(0.3, max(ancho, alto) / 45)
        yt = self.y_titulo if self.y_titulo is not None else -h * 6.5
        self.dx.texto((ox + ancho / 2, yt), titulo, h, self.capa, centrado=True)
        self.x += ancho + self.sep
