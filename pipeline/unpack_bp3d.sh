#!/usr/bin/env bash
# Unpack the BodyParts3D archives found in DIR (see fetch_bp3d.sh).
# The 3.0 archive stores paths with backslashes: Info-ZIP unzip turns them into directories but
# exits with status 1 (warning). Each archive is unpacked into a temporary directory, checked,
# then renamed, so an interrupted run never leaves a partial directory behind.
set -euo pipefail
cd "${1:?usage: unpack_bp3d.sh DIR}"
check() {  # an archive is unpacked when its directory holds the expected files
  case $1 in
    BodyParts3D_3.0_obj_95) test -f "$1/FMA23130.obj" ;;
    *) test -n "$(find "$1" -name 'FJ*.obj' -print -quit 2>/dev/null)" ;;
  esac
}
for z in isa_BP3D_4.0_obj_99 partof_BP3D_4.0_obj_99 BodyParts3D_3.0_obj_95; do
  [ -d "$z" ] && check "$z" && continue
  rm -rf "$z" ".unpack-$z"
  mkdir ".unpack-$z"
  unzip -q "$z.zip" -d ".unpack-$z" || [ $? -eq 1 ]
  mv ".unpack-$z/$z" "$z"
  rmdir ".unpack-$z"
  check "$z" || { echo "unexpected content in $z.zip" >&2; exit 1; }
done
