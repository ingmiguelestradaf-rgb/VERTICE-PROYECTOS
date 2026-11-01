# Proyecto del día — procedimiento (modo híbrido)

Instrucciones que sigue Claude cada mañana desde la tarea programada. También sirven
para correrlo a mano.

## Calendario (ciclo de 7 meses, inicia nov-2026)

| Mes del ciclo | Tipología | Meses |
|---|---|---|
| 1 | Casas (terrenos 180, 200, 300 y 400 m², rotan día a día) | nov-26, jun-27, ene-28… |
| 2 | Edificios de departamentos | dic-26, jul-27… |
| 3 | Naves industriales | ene-27, ago-27… |
| 4 | Plazas comerciales | feb-27, sep-27… |
| 5 | Hoteles y resorts (alternan día a día) | mar-27, oct-27… |
| 6 | Parques de diversiones y acuáticos (alternan) | abr-27, nov-27… |
| 7 | Museos y centros recreativos (alternan) | may-27, dic-27… |

Cada día cambia la corriente arquitectónica (18 corrientes en `motor/calendario.py`).

## Pasos

1. `pip install -r requirements.txt --break-system-packages` (si hace falta).
2. `python generar.py --plan` → muestra tipología, corriente, terreno y variante de hoy
   (zona horaria America/Tijuana).
3. Si ya existe una carpeta `docs/proyectos/<fecha de hoy>-*`, termina sin hacer nada.
4. **Arquitecto** — lee y sigue `skills/arquitecto-vertice/SKILL.md`: diseña el concepto, los
   detalles creativos y los materiales en `spec_hoy.json`, genera con
   `python generar.py --spec spec_hoy.json --estricto` y revisa plantas, fachadas y renders.
   Escribe `extra.dictamen_arquitectura`.
5. **Ingenieros** — lee y sigue `skills/ingenieros-vertice/SKILL.md`: verifica que el proyecto sea
   construible conforme a norma (estructura e instalaciones), ajusta lo necesario y escribe
   `extra.dictamen_ingenieria`.
6. Regenera con `--estricto`. No se publica nada con errores de revisión.
7. `git add docs && git commit -m "Proyecto del día AAAA-MM-DD: <nombre>" && git push`.
8. Resume en 3 líneas qué se generó y deja el enlace a la página del proyecto:
   `https://ingmiguelestradaf-rgb.github.io/VERTICE-PROYECTOS/proyectos/<clave>/`.

## Formato de `spec_hoy.json`

```json
{
  "nombre": "Casa Patio de Luz",
  "concepto": "Texto del concepto arquitectónico…",
  "materiales": "Aplanado blanco, concreto aparente, …",
  "paleta": {"muro": "#EEECE7", "acento": "#3A3A3A", "techo": "#D9D6CF", "vidrio": "#4C6A7A", "ventana": 0.55},
  "rasgos": ["volado", "celosia"],
  "extra": {"dictamen_arquitectura": ["…"], "dictamen_ingenieria": ["…"]}
}
```

Claves opcionales:
- `corriente`, `variante`, `terreno`: sólo si hay una razón para salir del calendario.
- `modelo`: reemplaza partes del modelo generado (`bloques`, `exteriores`, `usuarios`).
  Los bloques usan el formato de `motor/programa.py` (zonas con fracciones `p`).
- Rasgos disponibles: volado, celosia, parteluces, pergola, porche, marco, muro_acento,
  jardinera, estructura_aparente, pilotis, muro_cortina, ventana_corrida, alero_amplio.
- `extra.dictamen_arquitectura` y `extra.dictamen_ingenieria`: listas de puntos; se publican
  en la memoria y en la página del proyecto.

## Alcance

Anteproyecto conceptual: predimensionamiento estructural (NTC-2017), cálculo preliminar de
instalaciones y planos DXF esquemáticos. No es proyecto ejecutivo; requiere revisión y firma
de DRO.
