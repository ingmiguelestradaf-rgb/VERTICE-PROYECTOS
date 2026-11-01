# Proyecto del día — procedimiento

Instrucciones que sigue Claude cada mañana desde la tarea programada (también sirven para correrlo a mano).

## Qué se entrega

| Entregable | Dónde vive |
|---|---|
| **Anteproyecto**: renders, AP-01 conjunto, AP-02 plantas, AP-03 fachadas y corte, memoria descriptiva, `spec.json` | GitHub (`docs/proyectos/<clave>/`) → galería y app, **y** Drive |
| **Proyecto ejecutivo**: 17 láminas (A-01…A-07, E-01…E-04, IH, IS, IE, IG), memoria técnica Word/PDF, presupuesto Excel, programa de obra, revisión de coordinación | **Sólo Drive** (`Vértice - Proyectos del día/<clave>/Proyecto ejecutivo`). Nunca se sube a GitHub. |

El proyecto ejecutivo se genera en `_privado/` (ignorado por git). En GitHub sólo se guarda el diseño (`spec.json`);
el flujo `.github/workflows/drive.yml` lo regenera y lo envía a Drive por el puente de Apps Script (`drive/`).

## Calendario (ciclo de 7 meses, inicia nov-2026)

nov casas (terrenos 9x20, 10x20, 12x25 y 16x25 m) · dic edificios · ene naves · feb plazas comerciales ·
mar hoteles/resorts · abr parques de diversiones/acuáticos · may museos/centros recreativos · jun vuelve a casas.
Una corriente arquitectónica distinta cada día. Proyecto ejecutivo completo: casas. Demás tipologías: nivel básico.

## Pasos

1. Agrega los repos `ingmiguelestradaf-rgb/VERTICE-PROYECTOS` (escritura) y `ingmiguelestradaf-rgb/VERTICE-CALCULO`
   (lectura); clona VERTICE-CALCULO junto a VERTICE-PROYECTOS (carpeta hermana `VERTICE-CALCULO`).
2. `pip install -r requirements.txt --break-system-packages`; `python generar.py --plan`.
3. Si ya existe `docs/proyectos/<fecha de hoy>-*`, termina.
4. **Arquitecto** — sigue `skills/arquitecto-vertice/SKILL.md`: escribe `spec_hoy.json` (nombre, concepto, materiales,
   rasgos) y genera con `python generar.py --spec spec_hoy.json --estricto`.
5. **Ingenieros** — sigue `skills/ingenieros-vertice/SKILL.md`: revisa la salida de coordinación, las láminas E/I y
   `proyecto_ejecutivo.json`; escribe los dictámenes con los números reales en `extra` del spec y regenera con `--estricto`.
   No se publica nada con errores.
6. `git add docs && git commit -m "Proyecto del día AAAA-MM-DD: <nombre>" && git push` (sólo anteproyecto y spec.json).
   El push dispara el envío de ambas carpetas a Drive.
7. Resume en 3 líneas: nombre, superficie, presupuesto estimado, semanas de obra, resultado de coordinación y el enlace
   `https://ingmiguelestradaf-rgb.github.io/VERTICE-PROYECTOS/proyectos/<clave>/`.

## Formato de `spec_hoy.json`

```json
{
  "nombre": "Casa Patio de Luz",
  "concepto": "Texto del concepto arquitectónico…",
  "materiales": "Muros de block…; cancelería de aluminio…; porcelanato…",
  "paleta": {"muro": "#EEECE7", "acento": "#3A3A3A", "techo": "#D9D6CF", "vidrio": "#4C6A7A", "ventana": 0.55},
  "rasgos": ["volado", "muro_acento"],
  "extra": {"dictamen_arquitectura": ["…"], "dictamen_ingenieria": ["…"]}
}
```

Rasgos: volado, celosia, parteluces, pergola, porche, marco, muro_acento, jardinera, estructura_aparente, pilotis,
muro_cortina, ventana_corrida, alero_amplio. `modelo` permite reemplazar el programa (formato de `motor/programa.py`).

## Alcance y responsabilidad

Proyecto ejecutivo con cálculo estructural (NTC-2017, método simplificado de mampostería), instalaciones (NOM-001-SEDE,
NOM-004-SEDG, CESPT), presupuesto con precios de Tijuana (VERTICE-CALCULO) y revisión de coordinación automática.
Para licencia requiere estudio de mecánica de suelos, factibilidades y la firma del DRO y corresponsables.
