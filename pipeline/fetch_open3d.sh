#!/usr/bin/env bash
# Download the Open3DModel upper-limb geometry (OBJ, about 21 MB, CC BY-SA 4.0) into DIR, checking its
# SHA-256, and unpack upper-limb.obj. Only the OBJ export is fetched: it has no materials nor textures.
# The textures of the Blender and glb exports are CC BY-NC-SA: never download nor use them.
#
# The upstream URL is not versioned (AnatomyTOOL replaces the file in place), so each release of this
# repository also publishes the pinned zip as an asset. Sources tried in order, each checked against
# pipeline/open3d.sha256 (a file with another checksum is discarded):
#   1. $OPEN3D_MIRROR/<file> if set (e.g. https://github.com/OWNER/REPO/releases/download/v1.3.0);
#   2. the latest release of this repository (public, no token): .../releases/latest/download/<file>;
#   3. the upstream URL.
# Usage: pipeline/fetch_open3d.sh DIR
set -euo pipefail
DIR=${1:?usage: fetch_open3d.sh DIR}
HERE=$(cd "$(dirname "$0")" && pwd)
UPSTREAM=https://caskanatomy.info/open3dmodelfiles
REPO=${OPEN3D_REPO:-AnatomoOrg/anatomo-models}
mkdir -p "$DIR"
cd "$DIR"

ok() { echo "$1  $2" | sha256sum -c --quiet - >/dev/null 2>&1; }

while read -r sum path; do
  [ -n "$sum" ] || continue
  case $path in *-obj.zip) ;; *) echo "only OBJ exports may be fetched: $path" >&2; exit 1 ;; esac
  f=$(basename "$path")
  urls=()
  [ -n "${OPEN3D_MIRROR:-}" ] && urls+=("${OPEN3D_MIRROR%/}/$f")
  urls+=("https://github.com/$REPO/releases/latest/download/$f" "$UPSTREAM/$path")
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
  ok "$sum" "$f" || {
    echo "$f: no source with the pinned checksum (the file may have been updated upstream: see README," \
         "'Si le fichier Open3DModel change en amont')" >&2; exit 1; }
  # The archive must hold OBJ files only; unpack them (and nothing else) next to it.
  bad=$(unzip -Z1 "$f" | grep -v '\.obj$' || true)
  [ -z "$bad" ] || { echo "$f: unexpected non-OBJ content: $bad" >&2; exit 1; }
  unzip -q -o "$f" '*.obj'
done < "$HERE/open3d.sha256"
test -f upper-limb.obj
echo "Open3DModel ready in $DIR"
