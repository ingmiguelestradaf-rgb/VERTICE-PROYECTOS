"""Enlace con VERTICE-CALCULO (librería de cálculo del despacho).

Busca el paquete `vertice` en este orden:
  1. variable de entorno VERTICE_CALCULO (ruta al repo)
  2. ../VERTICE-CALCULO o ../vc junto a este repo
  3. ./_calculo (si no existe, la clona de GitHub; requiere acceso de lectura)
"""
import os
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
URL = "https://github.com/ingmiguelestradaf-rgb/VERTICE-CALCULO"


def _candidatos():
    if os.environ.get("VERTICE_CALCULO"):
        yield os.environ["VERTICE_CALCULO"]
    for n in ("VERTICE-CALCULO", "vertice-calculo", "vc"):
        yield os.path.join(os.path.dirname(RAIZ), n)
    yield os.path.join(RAIZ, "_calculo")


def cargar(clonar=True):
    """Regresa el módulo `vertice` o None si no está disponible."""
    for ruta in _candidatos():
        if os.path.isdir(os.path.join(ruta, "vertice")):
            if ruta not in sys.path:
                sys.path.insert(0, ruta)
            import vertice  # noqa
            return vertice
    if clonar:
        destino = os.path.join(RAIZ, "_calculo")
        try:
            subprocess.run(["git", "clone", "-q", "--depth", "1", URL, destino], check=True, timeout=180,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return cargar(clonar=False)
        except Exception:
            return None
    return None
