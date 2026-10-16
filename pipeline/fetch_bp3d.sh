#!/usr/bin/env bash
# Download and unpack the BodyParts3D source files (about 750 MB) into DIR, checking their SHA-256.
# Usage: pipeline/fetch_bp3d.sh DIR
set -euo pipefail
DIR=${1:?usage: fetch_bp3d.sh DIR}
HERE=$(cd "$(dirname "$0")" && pwd)
BASE=https://dbarchive.biosciencedbc.jp/data/bodyparts3d
mkdir -p "$DIR"
cd "$DIR"
while read -r sum path; do
  f=$(basename "$path")
  if [ ! -f "$f" ] || ! echo "$sum  $f" | sha256sum -c --quiet - 2>/dev/null; then
    curl -fsSL --retry 5 --retry-delay 5 -o "$f" "$BASE/$path"
  fi
  echo "$sum  $f" | sha256sum -c --quiet -
done < "$HERE/bp3d.sha256"
"$HERE/unpack_bp3d.sh" .
echo "BodyParts3D ready in $DIR"
