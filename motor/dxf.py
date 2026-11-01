"""Escritor DXF R12 (AC1009) sin dependencias externas.

R12 lo abren AutoCAD, BricsCAD, ZWCAD, LibreCAD, DraftSight y QCAD.
Unidades: metros (INSUNITS = 6).
"""
import math

# Colores ACI
ROJO, AMARILLO, VERDE, CIAN, AZUL, MAGENTA, BLANCO, GRIS, GRIS_CLARO = 1, 2, 3, 4, 5, 6, 7, 8, 9
NARANJA, CAFE = 30, 34


class DXF:
    def __init__(self):
        self.capas = {"0": (BLANCO, "CONTINUOUS")}
        self.ents = []

    # ------------------------------------------------------------ capas
    def capa(self, nombre, color=BLANCO, tipo="CONTINUOUS"):
        self.capas.setdefault(nombre, (color, tipo))
        return nombre

    # ------------------------------------------------------- entidades
    def linea(self, p1, p2, capa="0"):
        self.ents.append(("LINE", capa, [(10, p1[0]), (20, p1[1]), (30, 0.0),
                                         (11, p2[0]), (21, p2[1]), (31, 0.0)]))

    def polilinea(self, pts, capa="0", cerrada=False):
        if len(pts) < 2:
            return
        self.ents.append(("POLYLINE", capa, pts, cerrada))

    def rect(self, x, y, w, h, capa="0"):
        self.polilinea([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], capa, True)

    def circulo(self, c, r, capa="0"):
        self.ents.append(("CIRCLE", capa, [(10, c[0]), (20, c[1]), (30, 0.0), (40, r)]))

    def arco(self, c, r, a0, a1, capa="0"):
        self.ents.append(("ARC", capa, [(10, c[0]), (20, c[1]), (30, 0.0), (40, r),
                                        (50, a0), (51, a1)]))

    def texto(self, p, txt, h=0.25, capa="0", rot=0.0, centrado=False):
        txt = str(txt).replace("\n", " ")
        codes = [(10, p[0]), (20, p[1]), (30, 0.0), (40, h), (1, txt), (50, rot)]
        if centrado:
            codes += [(72, 1), (11, p[0]), (21, p[1]), (31, 0.0)]
        self.ents.append(("TEXT", capa, codes))

    def cota(self, p1, p2, off, capa="COTAS", h=0.2):
        """Cota lineal dibujada con primitivas (robusta en cualquier CAD)."""
        dx, dy = p2[0] - p1[0], p2[1] - p1[1]
        L = math.hypot(dx, dy)
        if L < 1e-6:
            return
        nx, ny = -dy / L, dx / L
        a = (p1[0] + nx * off, p1[1] + ny * off)
        b = (p2[0] + nx * off, p2[1] + ny * off)
        self.linea(p1, (a[0] + nx * 0.15 * sgn(off), a[1] + ny * 0.15 * sgn(off)), capa)
        self.linea(p2, (b[0] + nx * 0.15 * sgn(off), b[1] + ny * 0.15 * sgn(off)), capa)
        self.linea(a, b, capa)
        t = 0.12
        for q in (a, b):  # marcas a 45°
            self.linea((q[0] - t, q[1] - t), (q[0] + t, q[1] + t), capa)
        ang = math.degrees(math.atan2(dy, dx))
        if ang > 90 or ang <= -90:
            ang += 180
        m = ((a[0] + b[0]) / 2 + nx * 0.12 * sgn(off), (a[1] + b[1]) / 2 + ny * 0.12 * sgn(off))
        self.texto(m, f"{L:.2f}", h, capa, ang % 360, centrado=True)

    # ----------------------------------------------------------- salida
    def guardar(self, ruta):
        xs, ys = [0.0], [0.0]
        for e in self.ents:
            if e[0] == "POLYLINE":
                xs += [p[0] for p in e[2]]
                ys += [p[1] for p in e[2]]
            else:
                d = dict(e[2])
                xs.append(d.get(10, 0)); ys.append(d.get(20, 0))
        out = []
        w = lambda c, v: out.append(f"{c}\n{v}")
        w(0, "SECTION"); w(2, "HEADER")
        w(9, "$ACADVER"); w(1, "AC1009")
        w(9, "$DWGCODEPAGE"); w(3, "ANSI_1252")
        w(9, "$INSUNITS"); w(70, 6)
        w(9, "$EXTMIN"); w(10, f"{min(xs):.4f}"); w(20, f"{min(ys):.4f}")
        w(9, "$EXTMAX"); w(10, f"{max(xs):.4f}"); w(20, f"{max(ys):.4f}")
        w(9, "$LTSCALE"); w(40, 0.5)
        w(0, "ENDSEC")
        w(0, "SECTION"); w(2, "TABLES")
        # tipos de línea
        tipos = {"CONTINUOUS": ("Solid line", []),
                 "DASHED": ("Dashed __ __ __", [0.5, -0.25]),
                 "CENTER": ("Center ____ _ ____", [1.25, -0.25, 0.25, -0.25]),
                 "HIDDEN": ("Hidden - - - -", [0.25, -0.125]),
                 "DOT": ("Dot . . . .", [0.0, -0.25])}
        w(0, "TABLE"); w(2, "LTYPE"); w(70, len(tipos))
        for n, (desc, pat) in tipos.items():
            w(0, "LTYPE"); w(2, n); w(70, 0); w(3, desc); w(72, 65)
            w(73, len(pat)); w(40, f"{sum(abs(x) for x in pat):.4f}")
            for x in pat:
                w(49, f"{x:.4f}")
        w(0, "ENDTAB")
        w(0, "TABLE"); w(2, "LAYER"); w(70, len(self.capas))
        for n, (col, tipo) in self.capas.items():
            w(0, "LAYER"); w(2, n); w(70, 0); w(62, col); w(6, tipo)
        w(0, "ENDTAB")
        w(0, "TABLE"); w(2, "STYLE"); w(70, 1)
        w(0, "STYLE"); w(2, "STANDARD"); w(70, 0); w(40, 0.0); w(41, 0.9); w(50, 0.0)
        w(71, 0); w(42, 0.25); w(3, "txt"); w(4, "")
        w(0, "ENDTAB")
        w(0, "ENDSEC")
        w(0, "SECTION"); w(2, "ENTITIES")
        for e in self.ents:
            if e[0] == "POLYLINE":
                _, capa, pts, cerr = e
                w(0, "POLYLINE"); w(8, capa); w(66, 1); w(10, 0.0); w(20, 0.0); w(30, 0.0)
                w(70, 1 if cerr else 0)
                for p in pts:
                    w(0, "VERTEX"); w(8, capa); w(10, f"{p[0]:.4f}"); w(20, f"{p[1]:.4f}"); w(30, 0.0)
                w(0, "SEQEND"); w(8, capa)
            else:
                tipo, capa, codes = e
                w(0, tipo); w(8, capa)
                for c, v in codes:
                    w(c, f"{v:.4f}" if isinstance(v, float) else v)
        w(0, "ENDSEC"); w(0, "EOF")
        with open(ruta, "w", encoding="cp1252", errors="replace", newline="\r\n") as f:
            f.write("\n".join(out) + "\n")


def sgn(x):
    return 1 if x >= 0 else -1
