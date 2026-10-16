#!/usr/bin/env bash
# Download the Open3DModel upper-limb geometry (OBJ, about 21 MB, CC BY-SA 4.0) into DIR, checking its
# SHA-256, and unpack upper-limb.obj. Only the OBJ export is fetched: it has no materials nor textures.
# The textures of the Blender and glb exports are CC BY-NC-SA: never download nor use them.
# Usage: pipeline/fetch_open3d.sh DIR
set -euo pipefail
DIR=${1:?usage: fetch_open3d.sh DIR}
HERE=$(cd "$(dirname "$0")" && pwd)
BASE=https://caskanatomy.info/open3dmodelfiles
mkdir -p "$DIR"
cd "$DIR"
while read -r sum path; do
  case $path in *-obj.zip) ;; *) echo "only OBJ exports may be fetched: $path" >&2; exit 1 ;; esac
  f=$(basename "$path")
  if [ ! -f "$f" ] || ! echo "$sum  $f" | sha256sum -c --quiet - 2>/dev/null; then
    curl -fsSL --retry 5 --retry-delay 5 -o "$f" "$BASE/$path"
  fi
  echo "$sum  $f" | sha256sum -c --quiet - || {
    echo "$f: checksum mismatch (the file may have been updated upstream: check its licence and content," \
         "then update pipeline/open3d.sha256)" >&2; exit 1; }
  # The archive must hold OBJ files only; unpack them (and nothing else) next to it.
  if unzip -Z1 "$f" | grep -qv '\.obj$'; then echo "$f: unexpected non-OBJ content" >&2; exit 1; fi
  unzip -q -o "$f" '*.obj'
done < "$HERE/open3d.sha256"
test -f upper-limb.obj
echo "Open3DModel ready in $DIR"
