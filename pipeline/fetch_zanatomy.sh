#!/usr/bin/env bash
# Download Z-Anatomy's Blender template (Z-Anatomy.zip, 87 MB, CC BY-SA 4.0) into DIR, checking its SHA-256, and unpack
# its Startup.blend (307 MB) only. The pipeline reads that file as data (pipeline/anatomo_models/blend.py): Blender is
# not needed, and the Python add-on of the zip (Anatomy-shortcuts.py, __init__.py) is never unpacked nor run.
#
# The file is pinned by commit in the upstream repository (https://github.com/Z-Anatomy/Models-of-human-anatomy) and
# by SHA-256 (pipeline/zanatomy.sha256: "<sha256> <commit>/Z-Anatomy.zip"). Unlike the Open3DModel zips, the releases
# of this repository do not mirror it: its URL is versioned, and the zip also holds third-party parts under
# non-commercial licences (inner ear, kidney) that we do not republish. Sources tried in order, each checked against
# the pinned checksum (a file with another checksum is discarded):
#   1. $ZANATOMY_MIRROR/Z-Anatomy.zip if set (a private copy, should the upstream repository go away);
#   2. the upstream file at the pinned commit.
# Usage: pipeline/fetch_zanatomy.sh DIR
set -euo pipefail
DIR=${1:?usage: fetch_zanatomy.sh DIR}
HERE=$(cd "$(dirname "$0")" && pwd)
UPSTREAM=https://raw.githubusercontent.com/Z-Anatomy/Models-of-human-anatomy
mkdir -p "$DIR"
cd "$DIR"

ok() { echo "$1  $2" | sha256sum -c --quiet - >/dev/null 2>&1; }

read -r sum path < "$HERE/zanatomy.sha256"
f=$(basename "$path")
[ "$f" = Z-Anatomy.zip ] || { echo "unexpected file in zanatomy.sha256: $path" >&2; exit 1; }
urls=()
[ -n "${ZANATOMY_MIRROR:-}" ] && urls+=("${ZANATOMY_MIRROR%/}/$f")
urls+=("$UPSTREAM/$path")
for url in "${urls[@]}"; do
  ok "$sum" "$f" && break
  rm -f "$f.part"
  if curl -fsSL --retry 3 --retry-delay 5 -o "$f.part" "$url" && ok "$sum" "$f.part"; then
    mv "$f.part" "$f"
    echo "$f: from $url"
  else
    echo "$f: not available with the pinned checksum at $url" >&2
    rm -f "$f.part"
  fi
done
ok "$sum" "$f" || { echo "$f: no source with the pinned checksum" >&2; exit 1; }
# Only the scene file is unpacked, flat into DIR.
unzip -q -o -j "$f" 'Z-Anatomy/Startup.blend'
test -f Startup.blend
echo "Z-Anatomy ready in $DIR"
