#!/usr/bin/env python3
"""Sube un proyecto (Anteproyecto y Proyecto ejecutivo) a Google Drive a través del puente de Apps Script.

Uso:  VERTICE_DRIVE_URL=... VERTICE_DRIVE_TOKEN=... python drive/subir.py _privado/<clave>
"""
import base64
import json
import mimetypes
import os
import sys
import time
import urllib.request

MIME = {".dxf": "application/dxf", ".md": "text/markdown", ".json": "application/json",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}


def subir(url, token, ruta_local, ruta_drive):
    with open(ruta_local, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    ext = os.path.splitext(ruta_local)[1].lower()
    cuerpo = json.dumps(dict(token=token, ruta=ruta_drive, nombre=os.path.basename(ruta_local),
                             mime=MIME.get(ext) or mimetypes.guess_type(ruta_local)[0] or "application/octet-stream",
                             base64=b64)).encode()
    for intento in range(4):
        try:
            req = urllib.request.Request(url, data=cuerpo, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=180) as r:
                txt = r.read().decode(errors="replace")
            try:
                res = json.loads(txt)
            except ValueError:
                import re
                vis = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", txt, flags=re.S | re.I)
                vis = " ".join(re.sub(r"<[^>]+>", " ", vis).split())
                raise RuntimeError("el puente no respondió JSON: " + vis[:280])
            if not res.get("ok"):
                raise RuntimeError(f"el puente respondió: {res.get('error')}")
            return res
        except Exception as e:  # reintento con espera
            if intento == 3:
                print(f"::error::Drive: {ruta_local}: {str(e)[:300]}")
                sys.exit(1)
            print(f"  reintento {intento + 1}: {e}")
            time.sleep(5 * (intento + 1))


def main():
    url, token = os.environ.get("VERTICE_DRIVE_URL"), os.environ.get("VERTICE_DRIVE_TOKEN")
    if not url or not token:
        falta = [n for n, v in (("VERTICE_DRIVE_URL", url), ("VERTICE_DRIVE_TOKEN", token)) if not v]
        print(f"::error::Faltan los secretos de GitHub {', '.join(falta)} (Settings → Secrets and variables → Actions → "
              "pestaña Secrets → Repository secrets): no se subió nada a Drive.")
        sys.exit(1)
    if "/exec" not in url:
        print("::warning::VERTICE_DRIVE_URL debería terminar en /exec (implementación de Aplicación web)")
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            import re
            txt = r.read().decode(errors="replace")
            vis = " ".join(re.sub(r"<[^>]+>", " ", re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", txt, flags=re.S | re.I)).split())
            print(f"::notice::Puente (GET {url[:45]}…{url[-12:]}): {vis[:200]}")
    except Exception as e:
        print(f"::error::Drive: el puente no responde a GET ({str(e)[:200]})")
    base = sys.argv[1].rstrip("/")
    solo = sys.argv[sys.argv.index("--solo") + 1:] if "--solo" in sys.argv else None
    clave = os.path.basename(base)
    n = 0
    carpeta = None
    for raiz, _, archivos in os.walk(base):
        for a in sorted(archivos):
            if a == "escena.json":
                continue
            local = os.path.join(raiz, a)
            if solo and not any(os.path.relpath(local, base).startswith(p) for p in solo):
                continue
            rel = os.path.relpath(raiz, os.path.dirname(base)).split(os.sep)   # [clave, Anteproyecto, planos...]
            res = subir(url, token, local, rel)
            carpeta = carpeta or res.get("carpeta")
            n += 1
            print(f"  ✓ {'/'.join(rel)}/{a}")
    print(f"Subidos {n} archivos de {clave} a Drive.")


if __name__ == "__main__":
    main()
