"""Rasterizador por software (numpy): z-buffer, sombras por shadow map, contornos y niebla.

Sin GPU ni dependencias de render: produce imágenes nítidas y consistentes en GitHub Actions
o en cualquier servidor.
"""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter


def _norm(v):
    v = np.asarray(v, float)
    return v / (np.linalg.norm(v) + 1e-12)


def clip_near(poly, near):
    """Sutherland–Hodgman contra el plano Z = near (coords de cámara)."""
    out = []
    n = len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        ia, ib = a[2] >= near, b[2] >= near
        if ia:
            out.append(a)
        if ia != ib:
            t = (near - a[2]) / (b[2] - a[2])
            out.append(a + (b - a) * t)
    return out


class Rasterizador:
    def __init__(self, W, H):
        self.W, self.H = W, H
        self.invz = np.zeros((H, W), np.float32)
        self.col = np.zeros((H, W, 3), np.float32)
        self.ndl = np.zeros((H, W), np.float32)
        self.flat = np.zeros((H, W), np.float32)     # 1 = sin sombreado (vidrio, líneas)
        self.wpos = np.zeros((H, W, 3), np.float32)
        self.ids = np.full((H, W), -1, np.int32)

    def camara(self, eye, target, fov_deg):
        self.eye = np.asarray(eye, float)
        f = _norm(np.asarray(target, float) - self.eye)
        r = _norm(np.cross(f, [0, 0, 1]))
        u = np.cross(r, f)
        self.R = np.stack([r, u, f])
        self.f = (self.W / 2) / math.tan(math.radians(fov_deg) / 2)

    def a_cam(self, P):
        return (np.asarray(P) - self.eye) @ self.R.T

    def tri(self, c, w, color, ndl, flat, pid):
        """c: 3x3 coords de cámara; w: 3x3 coords de mundo."""
        Z = c[:, 2]
        sx = self.W / 2 + self.f * c[:, 0] / Z
        sy = self.H / 2 - self.f * c[:, 1] / Z
        x0, x1 = int(max(0, math.floor(sx.min()))), int(min(self.W - 1, math.ceil(sx.max())))
        y0, y1 = int(max(0, math.floor(sy.min()))), int(min(self.H - 1, math.ceil(sy.max())))
        if x0 > x1 or y0 > y1:
            return
        area = (sx[1] - sx[0]) * (sy[2] - sy[0]) - (sx[2] - sx[0]) * (sy[1] - sy[0])
        if abs(area) < 1e-9:
            return
        ys, xs = np.mgrid[y0:y1 + 1, x0:x1 + 1].astype(np.float32)
        px, py = xs + 0.5, ys + 0.5
        w0 = ((sx[1] - px) * (sy[2] - py) - (sx[2] - px) * (sy[1] - py)) / area
        w1 = ((sx[2] - px) * (sy[0] - py) - (sx[0] - px) * (sy[2] - py)) / area
        w2 = 1 - w0 - w1
        m = (w0 >= -1e-4) & (w1 >= -1e-4) & (w2 >= -1e-4)
        if not m.any():
            return
        iz = w0 / Z[0] + w1 / Z[1] + w2 / Z[2]
        sub = self.invz[y0:y1 + 1, x0:x1 + 1]
        m &= iz > sub
        if not m.any():
            return
        sub[m] = iz[m]
        self.col[y0:y1 + 1, x0:x1 + 1][m] = color
        self.ndl[y0:y1 + 1, x0:x1 + 1][m] = ndl
        self.flat[y0:y1 + 1, x0:x1 + 1][m] = flat
        self.ids[y0:y1 + 1, x0:x1 + 1][m] = pid
        izm = iz[m]
        wp = self.wpos[y0:y1 + 1, x0:x1 + 1]
        for k in range(3):
            num = (w0 * w[0, k] / Z[0] + w1 * w[1, k] / Z[1] + w2 * w[2, k] / Z[2])[m]
            wp[..., k][m] = num / izm

    def poligono(self, P, color, ndl, flat, pid, near=0.3):
        c = self.a_cam(P)
        if (c[:, 2] < near).all():
            return
        if (c[:, 2] < near).any():
            cl = clip_near([np.array(p) for p in c], near)
            if len(cl) < 3:
                return
            c = np.array(cl)
            P = c @ self.R + self.eye
        for i in range(1, len(c) - 1):
            idx = [0, i, i + 1]
            self.tri(c[idx], P[idx], color, ndl, flat, pid)

    def linea(self, a, b, color, ancho, pid):
        ca, cb = self.a_cam(a), self.a_cam(b)
        if ca[2] < 0.3 and cb[2] < 0.3:
            return
        if ca[2] < 0.3 or cb[2] < 0.3:
            t = (0.3 - ca[2]) / (cb[2] - ca[2])
            if ca[2] < 0.3:
                ca = ca + (cb - ca) * t
            else:
                cb = ca + (cb - ca) * t
        pa = np.array([self.W / 2 + self.f * ca[0] / ca[2], self.H / 2 - self.f * ca[1] / ca[2]])
        pb = np.array([self.W / 2 + self.f * cb[0] / cb[2], self.H / 2 - self.f * cb[1] / cb[2]])
        n = int(max(2, np.abs(pb - pa).max()))
        if n > 6000:
            return
        t = np.linspace(0, 1, n)
        xs = pa[0] + (pb[0] - pa[0]) * t
        ys = pa[1] + (pb[1] - pa[1]) * t
        iz = 1 / ca[2] + (1 / cb[2] - 1 / ca[2]) * t
        r = max(0, int(ancho // 2))
        for dx in range(-r, r + 1):
            for dy in range(-r, r + 1):
                X = (xs + dx).astype(int); Y = (ys + dy).astype(int)
                ok = (X >= 0) & (X < self.W) & (Y >= 0) & (Y < self.H)
                X, Y, I = X[ok], Y[ok], iz[ok]
                vis = I >= self.invz[Y, X] * 0.995
                self.col[Y[vis], X[vis]] = color
                self.flat[Y[vis], X[vis]] = 1
                self.ids[Y[vis], X[vis]] = pid
                self.invz[Y[vis], X[vis]] = np.maximum(self.invz[Y[vis], X[vis]], I[vis])


def mapa_sombras(polys, sol, res=2048):
    d = _norm(sol)
    u = _norm(np.cross(d, [0, 0, 1]) if abs(d[2]) < 0.99 else np.cross(d, [1, 0, 0]))
    v = np.cross(d, u)
    todos = np.concatenate(polys)
    U, V = todos @ u, todos @ v
    u0, u1, v0, v1 = U.min(), U.max(), V.min(), V.max()
    s = (res - 1) / max(u1 - u0, v1 - v0)
    dep = np.full((res, res), -1e9, np.float32)
    for P in polys:
        pu = (P @ u - u0) * s
        pv = (P @ v - v0) * s
        pd = P @ d
        for i in range(1, len(P) - 1):
            idx = [0, i, i + 1]
            x, y, z = pu[idx], pv[idx], pd[idx]
            xa, xb = int(max(0, math.floor(x.min()))), int(min(res - 1, math.ceil(x.max())))
            ya, yb = int(max(0, math.floor(y.min()))), int(min(res - 1, math.ceil(y.max())))
            if xa > xb or ya > yb:
                continue
            area = (x[1] - x[0]) * (y[2] - y[0]) - (x[2] - x[0]) * (y[1] - y[0])
            if abs(area) < 1e-9:
                continue
            ys, xs = np.mgrid[ya:yb + 1, xa:xb + 1].astype(np.float32)
            px, py = xs + 0.5, ys + 0.5
            w0 = ((x[1] - px) * (y[2] - py) - (x[2] - px) * (y[1] - py)) / area
            w1 = ((x[2] - px) * (y[0] - py) - (x[0] - px) * (y[2] - py)) / area
            w2 = 1 - w0 - w1
            m = (w0 >= -0.02) & (w1 >= -0.02) & (w2 >= -0.02)
            zz = w0 * z[0] + w1 * z[1] + w2 * z[2]
            sub = dep[ya:yb + 1, xa:xb + 1]
            m &= zz > sub
            sub[m] = zz[m]
    return dict(u=u, v=v, d=d, u0=u0, v0=v0, s=s, dep=dep, res=res)


def visibilidad(sm, wpos, bias=0.08):
    pu = ((wpos @ sm["u"]) - sm["u0"]) * sm["s"]
    pv = ((wpos @ sm["v"]) - sm["v0"]) * sm["s"]
    pd = wpos @ sm["d"]
    X = np.clip(pu.astype(int), 0, sm["res"] - 1)
    Y = np.clip(pv.astype(int), 0, sm["res"] - 1)
    # PCF 3x3 para bordes suaves
    acc = np.zeros(pd.shape, np.float32)
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            Xs = np.clip(X + dx, 0, sm["res"] - 1); Ys = np.clip(Y + dy, 0, sm["res"] - 1)
            acc += (sm["dep"][Ys, Xs] <= pd + bias).astype(np.float32)
    return acc / 9


def componer(R, sm, cielo=((205, 222, 236), (238, 241, 240)), niebla=0.0, amb=0.55, dif=0.5):
    H, W = R.H, R.W
    vis = visibilidad(sm, R.wpos.reshape(-1, 3)).reshape(H, W) if sm else np.ones((H, W), np.float32)
    luz = amb + dif * np.clip(R.ndl, 0, 1) * vis
    luz = np.where(R.flat > 0.5, 0.92 + 0.0 * luz, luz)
    img = R.col * luz[..., None]
    # cielo
    g = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    c0, c1 = np.array(cielo[0], np.float32) / 255, np.array(cielo[1], np.float32) / 255
    sky = c0 * (1 - g) + c1 * g
    vacio = R.ids < 0
    if niebla > 0:
        z = np.where(vacio, 0, 1 / np.maximum(R.invz, 1e-6))
        k = np.clip(1 - np.exp(-z * niebla), 0, 0.85)[..., None]
        img = img * (1 - k) + c1 * k
    img = np.where(vacio[..., None], np.broadcast_to(sky, img.shape), img)
    # contornos: cambio de polígono con discontinuidad de profundidad o de orientación
    ids = R.ids
    borde = np.zeros((H, W), bool)
    for sh in ((0, 1), (1, 0)):
        a = ids; b = np.roll(ids, sh, axis=(0, 1))
        dz = np.abs(R.invz - np.roll(R.invz, sh, axis=(0, 1))) / np.maximum(R.invz, 1e-6)
        dn = np.abs(R.ndl - np.roll(R.ndl, sh, axis=(0, 1)))
        borde |= (a != b) & ((dz > 0.015) | (dn > 0.02)) & ~vacio
    img[borde] *= 0.62
    return np.clip(img, 0, 1)


def guardar(img, ruta, ss, titulo, subtitulo):
    im = Image.fromarray((img * 255).astype(np.uint8))
    if ss > 1:
        im = im.resize((im.width // ss, im.height // ss), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    try:
        f1 = ImageFont.truetype("DejaVuSans-Bold.ttf", 26)
        f2 = ImageFont.truetype("DejaVuSans.ttf", 15)
    except Exception:
        f1 = f2 = ImageFont.load_default()
    h = im.height
    d.rectangle([0, h - 78, im.width, h], fill=(250, 248, 243))
    d.line([0, h - 78, im.width, h - 78], fill=(200, 194, 182), width=1)
    d.text((28, h - 66), titulo, fill=(28, 29, 31), font=f1)
    d.text((28, h - 31), subtitulo, fill=(94, 96, 100), font=f2)
    d.text((im.width - 190, h - 50), "V É R T I C E", fill=(180, 83, 42), font=f2)
    im.save(ruta, quality=88)
