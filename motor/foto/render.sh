#!/usr/bin/env bash
# Renders fotorrealistas + recorrido virtual de un proyecto, dentro de _privado/<clave>/Anteproyecto.
# Uso: bash motor/foto/render.sh _privado/<clave> [--prueba]
set -e
base="$1"; shift || true
ap="$base/Anteproyecto"
fotos="$ap/Renders fotorrealistas"; rec="$ap/Recorrido virtual"
mkdir -p "$fotos" "$rec"
bash motor/foto/instalar_blender.sh
blender/blender -b --factory-startup -P motor/foto/blender_escena.py -- "$base/escena.json" "$fotos" "$@" 2>&1 \
  | grep -E --line-buffered "render:|recorrido|Error|Traceback|File \"" || true
[ -f "$fotos/recorrido_virtual.mp4" ] && mv "$fotos/recorrido_virtual.mp4" "$rec/"
ls -la "$fotos" "$rec"
