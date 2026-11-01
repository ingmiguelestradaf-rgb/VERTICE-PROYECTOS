#!/usr/bin/env bash
# Descarga Blender 4.2 LTS (Linux x64) en ./blender si no existe.
set -e
[ -x blender/blender ] && exit 0
V=4.2.3
sudo apt-get install -y -qq --no-install-recommends libxi6 libxxf86vm1 libxfixes3 libxrender1 libgl1 libxkbcommon0 libsm6 > /dev/null || true
curl -sSL "https://download.blender.org/release/Blender4.2/blender-${V}-linux-x64.tar.xz" -o /tmp/blender.tar.xz
mkdir -p blender && tar -xJf /tmp/blender.tar.xz -C blender --strip-components=1
blender/blender --version | head -1
