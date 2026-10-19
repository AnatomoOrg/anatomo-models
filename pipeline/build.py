"""Build the published models from BodyParts3D (Open3DModel for the nerves of the limbs, Z-Anatomy for the dural
sinuses, cranial nerves and nerves of the trunk of the whole body).

Usage: python3 pipeline/build.py SRC_DIR OUT_DIR [--only upper_limb|full_body] [--open3d DIR] [--zanatomy DIR]
SRC_DIR holds the BodyParts3D files fetched by pipeline/fetch_bp3d.sh; the Open3DModel OBJs (upper and
lower limb) fetched by pipeline/fetch_open3d.sh are read from DIR (default SRC_DIR/open3d), Z-Anatomy's
Startup.blend fetched by pipeline/fetch_zanatomy.sh from the --zanatomy DIR (default SRC_DIR/zanatomy).
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import full_body  # noqa: E402
import upper_limb  # noqa: E402
from anatomo_models import fibers, landmarks, open3d, open3d_full_body, zanatomy  # noqa: E402
from anatomo_models.bp3d import BP3D  # noqa: E402
from anatomo_models.landmark_catalog import CATALOGUE  # noqa: E402
from anatomo_models.model import build  # noqa: E402
from anatomo_models.overrides import SYSTEM_OVERRIDES, apply_system_overrides  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCES = [
    {"name": "BodyParts3D 4.0", "url": "https://dbarchive.biosciencedbc.jp/data/bodyparts3d/LATEST/",
     "license": "CC-BY-SA-2.1-JP"},
    {"name": "BodyParts3D 3.0 (obj_95)", "url": "https://dbarchive.biosciencedbc.jp/data/bodyparts3d/20110915/",
     "license": "CC-BY-SA-2.1-JP"},
]
# Structure counts of the last reviewed build: fewer means a selection rule or a source file regressed.
# upper_limb: 161 BodyParts3D structures + 48 Open3DModel nerves.
# full_body: 1734 BodyParts3D structures + 220 Open3DModel nerves (48 upper-limb and 62 lower-limb concepts, x 2 sides)
# + 57 Z-Anatomy structures (61 concepts, 4 of which complete a structure already there).
MIN_STRUCTURES = {"upper_limb": 209, "full_body": 2011}
# Both models include Open3DModel nerves (CC BY-SA 4.0): they are published under CC BY-SA 4.0.
MODELS = {
    "upper_limb": {"sources": SOURCES + [open3d.SOURCE], "license": open3d.LICENSE, "attribution": open3d.ATTRIBUTION},
    "full_body": {"sources": SOURCES + open3d_full_body.SOURCES + [zanatomy.SOURCE], "license": open3d_full_body.LICENSE,
                  "attribution": zanatomy.ATTRIBUTION},
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src"); ap.add_argument("out")
    ap.add_argument("--only", choices=("upper_limb", "full_body"))
    ap.add_argument("--open3d", help="directory of upper-limb.obj and lower-limb.obj (default: SRC/open3d)")
    ap.add_argument("--zanatomy", help="directory of Z-Anatomy's Startup.blend (default: SRC/zanatomy)")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    version = open(os.path.join(ROOT, "VERSION")).read().strip()
    fr = json.load(open(os.path.join(ROOT, "data", "fr_names.json"), encoding="utf-8"))
    bp = BP3D(a.src)
    names, overridden = set(), set()
    o3d = a.open3d or os.path.join(a.src, "open3d")
    zan = a.zanatomy or os.path.join(a.src, "zanatomy")

    def upper_limb_items():
        items = upper_limb.structures(bp, fr)
        return items + open3d.nerves(os.path.join(o3d, open3d.OBJ), items)

    def full_body_items():
        items = full_body.structures(bp, fr)
        items += open3d_full_body.nerves(o3d, items)
        return items + zanatomy.structures(os.path.join(zan, zanatomy.BLEND), items)

    for model, structures in (("upper_limb", upper_limb_items), ("full_body", full_body_items)):
        if a.only not in (None, model):
            continue
        items = structures()
        if len(items) < MIN_STRUCTURES[model]:
            raise SystemExit(f"{model}: {len(items)} structures, expected at least {MIN_STRUCTURES[model]}")
        # Before build(): the system decides which mesh the geometry goes to.
        overridden |= apply_system_overrides(items)
        names |= {x["en"] for x in items}
        marks, failed = landmarks.place(items, CATALOGUE)
        if failed:
            raise SystemExit(f"{model}: landmarks without a position: {failed}")
        # Fibre directions run from the origin to the insertion landmarks of the muscles that have them.
        fibers.annotate(items, marks)
        m = build(items, os.path.join(a.out, f"{model}.glb"), os.path.join(a.out, f"{model}.json"), model, version,
                  **MODELS[model])
        write_landmarks(m, marks, os.path.join(a.out, f"{model}.landmarks.json"))
        report(m, marks)
    if a.only is None and (missing := landmarks.unresolved(names, CATALOGUE)):
        raise SystemExit(f"catalogue structures found in no model (misspelt?): {missing}")
    if a.only is None and (stale := sorted(set(SYSTEM_OVERRIDES) - overridden)):
        raise SystemExit(f"system overrides matching no structure (misspelt or obsolete?): {stale}")


def write_landmarks(m, marks, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"format": m["format"], "model": m["model"], "version": m["version"], "frame": m["frame"],
                   "license": m["license"], "attribution": m["attribution"], "landmarks": marks},
                  f, ensure_ascii=False, indent=1)
        f.write("\n")


def report(m, marks):
    tris = sum(s["triangles"] for s in m["systems"])
    print(f"{m['model']}: {len(m['structures'])} structures, {tris} triangles, {len(m['systems'])} meshes, "
          f"{len(marks)} landmarks", {s["key"]: s["structures"] for s in m["systems"]})


if __name__ == "__main__":
    main()
