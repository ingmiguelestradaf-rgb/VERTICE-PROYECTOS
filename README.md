# VÉRTICE · Proyecto del día

Cada día se genera un **anteproyecto arquitectónico, estructural y de instalaciones completo**:

- Planta de conjunto, plantas arquitectónicas, fachadas y corte (DXF R12, abren en AutoCAD/BricsCAD/ZWCAD/LibreCAD)
- Cimentación y planta estructural con predimensionamiento (mampostería confinada, marcos de concreto o acero)
- Instalación hidráulica + contra incendio, sanitaria + pluvial, eléctrica y gas LP, con cálculo preliminar
- Dos renders (aéreo y peatonal) con sombras, juego de planos en PDF y memoria descriptiva

**Galería:** https://ingmiguelestradaf-rgb.github.io/vertice-proyectos/

## Calendario

nov casas (180/200/300/400 m²) · dic edificios · ene naves industriales · feb plazas comerciales ·
mar hoteles y resorts · abr parques de diversiones y acuáticos · may museos y centros recreativos ·
jun vuelve a casas y sigue el mismo orden. Una corriente arquitectónica distinta cada día.

## Uso

```bash
pip install -r requirements.txt
python generar.py                    # proyecto de hoy
python generar.py --fecha 2027-03-02 # otra fecha
python generar.py --plan             # qué toca hoy
python generar.py --spec spec.json   # con el diseño propuesto por Claude
```

Salida en `docs/proyectos/<fecha>-<tipología>-<corriente>/`.

## Cómo corre solo

1. **Tarea programada de Claude** (cada mañana): diseña el concepto, nombre y materiales y ejecuta el motor
   (ver `PROYECTO_DEL_DIA.md`).
2. **GitHub Actions** (`.github/workflows/diario.yml`): respaldo a las 9:20 a. m.; si no hay proyecto del día, lo genera
   con el motor automático.

## Estructura

```
generar.py            orquestador
motor/calendario.py   tipología del mes, corrientes y terrenos
motor/programa.py     programas arquitectónicos por tipología
motor/layout.py       distribución de espacios, puertas y ventanas
motor/estructura.py   estructuración y predimensionamiento
motor/instalaciones.py cálculo y trazo de instalaciones
motor/planos.py, plano_estructural.py  dibujo DXF
motor/rast.py, render.py  renders por software (z-buffer + sombras)
motor/web.py          memoria y galería (GitHub Pages desde /docs)
```

> Anteproyecto conceptual generado automáticamente. No sustituye la memoria de cálculo definitiva, el estudio de
> mecánica de suelos ni la revisión y firma del DRO y corresponsables.
