# Casa Mirador Naranja

**Clave:** 2026-11-08-casa-mid-century  ·  **Fecha:** 8 de noviembre de 2026  
**Tipología:** Casa habitación   
**Corriente arquitectónica:** Mid-Century Modern

## Concepto

Vivienda de dos niveles en un lote de 16 x 25 m en Tijuana que retoma el Mid-Century Modern californiano, pariente cercano del clima de la frontera: una cubierta ligera de una agua y baja pendiente, con aleros amplios de 0.90 m, da sombra a los ventanales del sol alto del mediodía y deja que la luz baja del invierno entre a la casa. En planta baja los locales habitables se abren con muros cortina de piso a cerramiento: el despacho hacia el jardín frontal, el comedor hacia el patio norte y la sala hacia el jardín lateral poniente, y la sala sale además al patio posterior bajo una pérgola de madera; en planta alta las recámaras conservan su antepecho. El naranja quemado, color de las casas de Palm Springs, aparece sólo en la puerta de acceso, sobre muros color arena y cancelería bronce. Las ventanas en las cuatro fachadas dejan cruzar la brisa marina del poniente de lado a lado de la casa.

## Datos generales

| Concepto | Valor |
|---|---|
| Terreno | 16.00 x 25.00 m = 400.0 m² |
| Uso de suelo | Habitacional unifamiliar |
| Área de desplante | 181.7 m² (COS 0.45) |
| Área construida | 363.4 m² (CUS 0.91) |
| Niveles | 2 |
| Altura máxima | 6.6 m |
| Cajones de estacionamiento | 2 |
| Ocupantes | 6 |

## Dictamen del arquitecto

- Terreno de 16.00 x 25.00 m (400 m²); casa de 12.75 x 14.25 m a ejes en 2 niveles, 363.4 m² construidos con desplante de 181.7 m²: COS 0.45 y CUS 0.91 (por verificar con el PDU de Tijuana). Cochera doble cubierta de 5.80 x 5.60 m (2 cajones) y jardín frontal; jardín lateral poniente y patio posterior con pérgola.
- Lenguaje Mid-Century Modern: cubierta ligera a una agua de lámina sobre armadura de PTR (8 %) con aleros de 0.90 m y plafón de madera, muros color arena, cancelería bronce y acento naranja quemado en la puerta de acceso. Muros cortina de piso a cerramiento (antepecho de 10 cm, cabezal a 2.35 m) en despacho, sala y comedor: V-1 3.86 m, V-2 2.60 m, V-4 3.94 m y V-5 2.58 m x 2.25 m; render, AP-03, A-05, A-06, A-07 y Blender dibujan la misma geometría.
- Recorrido: puerta doble de 1.20 m → acceso (1.80 x 5.60 m) con paso a cochera, bodega y despacho (5.15 x 3.47 m) → vestíbulo (8.75 x 3.40 m) con medio baño, lavandería y escalera en U → sala (4.84 x 5.25 m), comedor (3.44 x 5.25 m) abierto a la cocina (4.46 x 3.67 m). La sala sale al patio posterior por un cancel corredizo P-4 de 2.30 x 2.10 m. Escalera de 1.15 m de tramo, peralte 17.5 cm y huella 29.0 cm (2p+h = 64 cm).
- Planta alta: estancia familiar (10.45 x 3.40 m) que reparte a recámaras 2 y 3 (2.90 x 5.60 m), recámara 4 (4.46 x 5.25 m), cuarto de TV (5.15 x 5.60 m) y baño 2; recámara principal (4.84 x 5.25 m) con vestidor y baño propios. Todas las recámaras ≥ 2.70 m de lado y con ventana al exterior con antepecho de 0.90 m; altura libre 2.66 m en planta baja y 2.67 m en planta alta (≥ 2.30 m). Medio baño con ventila alta y extractor.
- Correcciones de motor en revisión: el rasgo muro_cortina sólo existía en el render volumétrico (todas las ventanas, incluso las de recámaras en planta alta, bajaban a 20 cm) mientras fachadas, cortes, cancelería y Blender seguían con antepecho de 0.90 m; ahora una sola regla (layout.es_cortina) lo aplica en planta baja a locales habitables, con el mismo cabezal para no alterar cerramientos. Además: las notas de materiales se partían en el punto decimal ('aleros de 1' / '20 m'), el piso de la cédula tomaba el texto del muro cortina por contener 'piso', y el medio baño se especificaba con azulejo 'en regadera'.

## Dictamen de ingeniería

- Veredicto: construible conforme a norma — 0 errores y 0 avisos en 28 verificaciones de coordinación —, sujeto a los supuestos por validar indicados abajo. Los muros cortina no cambian cabezales (2.35 m) ni longitud de muros, así que castillos, cerramientos y el método simplificado no se ven afectados.
- Mampostería confinada con block de 20 cm en ambas direcciones (ajuste de coordinación por carga vertical y dirección X), castillos K-1 15x20 (64 en PB y 58 en PA) y dalas; trabe de carga T-1 30x50 de 5.60 m (5 #6) sobre la cochera con columna C-1 15x30 (4 #4, 10.6 t) entre portones, y 17 cerramientos de 15x30 a 20x40 cm (claro máximo 4.35 m). Dos muros de planta alta sin muro inferior se especifican como divisorios de tablaroca. Método simplificado NTC: X VR 92.7 t ≥ Vu 75.8 t (margen 22 %); Y VR 120.8 t ≥ 75.8 t; V basal 68.9 t con c = 0.213 supuesto y T = 0.18 s.
- Losas macizas de 14 cm en entrepiso (≥ 13.1 cm) y 13 cm en azotea (≥ 12.9 cm), f'c 250 kg/cm²; cubierta ligera de lámina sobre PTR (30 kg/m² en el análisis) apoyada en la losa de azotea.
- Zapatas corridas: ZC-1 perimetral de 50 x 20 cm (q = 5.38 t/m²) y ZC-2 interior de 75 x 20 cm (q = 10.39 t/m²) contra una q adm supuesta de 12 t/m² a -0.80 m: requiere estudio de mecánica de suelos y confirmar el espectro sísmico del sitio. Cuantificación: 8,021 kg de acero y 91.5 m³ de concreto.
- Instalaciones: toma Ø13 mm, 22 UM (1.21 L/s), alimentación Ø25 mm, cisterna de 2 m³ con hidroneumático de 1/2 HP y calentador de paso; 25 UD, bajadas de baño 2 (al acceso) y baño principal (al comedor) junto a muro, colector Ø100 mm al 2 % a la red CESPT; gasto pluvial 5.0 L/s a 2 bajadas Ø100 mm; 18 circuitos (16.5 kW instalados, 11.55 kW de demanda, 58.3 A), interruptor general 2P-100 A, desbalance 0.6 %; gas LP con tanque estacionario de 500 L ventilado y a más de 3 m de flamas. Factibilidades de CESPT y CFE por tramitar.
- Presupuesto de $1,950,476 + IVA ($2,106,514 con IVA; $5,368/m²) y programa de 24 semanas (141 días); la cancelería, los muros cortina, la cubierta de lámina y la pérgola quedan en la hoja "Por cotizar" (46 partidas) hasta tener cotización de proveedores de Tijuana.

## Materiales y acabados

Muros de block de concreto de 20 cm con aplanado fino y pintura elastomérica color arena; losa maciza de azotea impermeabilizada bajo cubierta ligera a una agua de lámina engargolada sobre armadura de PTR (pendiente 8 %), con aleros de 0.90 m y plafón de madera termotratada; cancelería de aluminio bronce con vidrio templado 6 mm; muros cortina de piso a cerramiento en planta baja y ventanas corredizas en planta alta; pérgola de madera termotratada en el patio posterior; puerta de acceso de madera de parota con acabado en naranja quemado; porcelanato 60x120 tipo madera clara; antiderrapante 60x60 en baños

## Proyecto ejecutivo

Proyecto ejecutivo completo: 17 láminas. Se entrega por separado (Drive).
Revisión de coordinación y normativa: 28 verificaciones, 0 errores, 0 avisos.

- A-01 Planta de conjunto
- A-02 Plantas arquitectónicas amuebladas
- A-03 Plantas acotadas a ejes
- A-04 Planta de azotea
- A-05 Fachadas
- A-06 Cortes arquitectónicos
- A-07 Cancelería y acabados
- E-01 Planta de cimentación
- E-02 Losas, trabes y castillos
- E-03 Detalles estructurales
- E-04 Cuantificación de acero y concreto
- IH-01 Instalación hidráulica
- IS-01 Instalación sanitaria y pluvial
- IE-01 Instalación eléctrica
- IG-01 Instalación de gas LP
- IH-02 Isométrico hidráulico
- IE-02 Cuadro de cargas y diagrama unifilar

## Revisión de calidad

0 errores · 0 avisos


## Cuadro de áreas

| Bloque | Nivel | Espacio | Medidas (m) | Área (m²) |
|---|---|---|---|---|
| Casa | Planta baja | Cochera doble | 5.80 x 5.60 | 32.48 |
| Casa | Planta baja | Acceso | 1.80 x 5.60 | 10.08 |
| Casa | Planta baja | Despacho | 5.15 x 3.47 | 17.88 |
| Casa | Planta baja | Bodega | 5.15 x 2.13 | 10.96 |
| Casa | Planta baja | Medio baño | 1.70 x 3.40 | 5.78 |
| Casa | Planta baja | Vestíbulo | 8.75 x 3.40 | 29.75 |
| Casa | Planta baja | Escalera | 2.30 x 3.40 | 7.82 |
| Casa | Planta baja | Sala | 4.84 x 5.25 | 25.44 |
| Casa | Planta baja | Comedor | 3.44 x 5.25 | 18.08 |
| Casa | Planta baja | Lavandería | 4.46 x 1.57 | 7.03 |
| Casa | Planta baja | Cocina | 4.46 x 3.67 | 16.40 |
| Casa | Planta alta | Recámara 2 | 2.90 x 5.60 | 16.24 |
| Casa | Planta alta | Recámara 3 | 2.90 x 5.60 | 16.24 |
| Casa | Planta alta | Baño 2 | 1.80 x 5.60 | 10.08 |
| Casa | Planta alta | Cuarto de TV | 5.15 x 5.60 | 28.84 |
| Casa | Planta alta | Estancia familiar | 10.45 x 3.40 | 35.53 |
| Casa | Planta alta | Escalera | 2.30 x 3.40 | 7.82 |
| Casa | Planta alta | Recámara principal | 4.84 x 5.25 | 25.44 |
| Casa | Planta alta | Vestidor | 3.44 x 2.36 | 8.14 |
| Casa | Planta alta | Baño principal | 3.44 x 2.89 | 9.94 |
| Casa | Planta alta | Recámara 4 | 4.46 x 5.25 | 23.43 |

## Láminas del anteproyecto

- **AP-01** Planta de conjunto — `planos/AP-01_planta-de-conjunto.dxf`
- **AP-02** Plantas arquitectónicas — `planos/AP-02_plantas-arquitectonicas.dxf`
- **AP-03** Fachadas y corte — `planos/AP-03_fachadas-y-corte.dxf`

---
*Anteproyecto conceptual generado automáticamente por el motor Vértice. El predimensionamiento y los cálculos de instalaciones son preliminares: no sustituyen la memoria de cálculo definitiva, el estudio de mecánica de suelos ni la revisión y firma del DRO y corresponsables.*
