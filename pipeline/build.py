"""Build the published models from BodyParts3D.

Usage: python3 pipeline/build.py SRC_DIR OUT_DIR [--only upper_limb|full_body]
SRC_DIR holds the BodyParts3D files fetched by pipeline/fetch_bp3d.sh.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import full_body  # noqa: E402
import upper_limb  # noqa: E402
from anatomo_models.bp3d import BP3D  # noqa: E402
from anatomo_models.model import build  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCES = [
    {"name": "BodyParts3D 4.0", "url": "https://dbarchive.biosciencedbc.jp/data/bodyparts3d/LATEST/",
     "license": "CC-BY-SA-2.1-JP"},
    {"name": "BodyParts3D 3.0 (obj_95)", "url": "https://dbarchive.biosciencedbc.jp/data/bodyparts3d/20110915/",
     "license": "CC-BY-SA-2.1-JP"},
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src"); ap.add_argument("out")
    ap.add_argument("--only", choices=("upper_limb", "full_body"))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    version = open(os.path.join(ROOT, "VERSION")).read().strip()
    fr = json.load(open(os.path.join(ROOT, "data", "fr_names.json"), encoding="utf-8"))
    bp = BP3D(a.src)
    if a.only in (None, "upper_limb"):
        items, marks = upper_limb.structures(bp, fr)
        m = build(items, os.path.join(a.out, "upper_limb.glb"), os.path.join(a.out, "upper_limb.json"),
                  "upper_limb", version, SOURCES)
        with open(os.path.join(a.out, "upper_limb.landmarks.json"), "w", encoding="utf-8") as f:
            json.dump({"format": m["format"], "version": version, "frame": m["frame"], "landmarks": marks},
                      f, ensure_ascii=False, indent=1)
            f.write("\n")
        report(m)
    if a.only in (None, "full_body"):
        items = full_body.structures(bp, fr)
        report(build(items, os.path.join(a.out, "full_body.glb"), os.path.join(a.out, "full_body.json"),
                     "full_body", version, SOURCES[:1]))


def report(m):
    tris = sum(s["triangles"] for s in m["systems"])
    print(f"{m['model']}: {len(m['structures'])} structures, {tris} triangles, {len(m['systems'])} meshes",
          {s["key"]: s["structures"] for s in m["systems"]})


if __name__ == "__main__":
    main()
