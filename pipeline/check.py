"""Check that a built model is consistent with its manifest.

Usage: python3 pipeline/check.py OUT_DIR/upper_limb.json [...]
"""
import json
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from anatomo_models.glb import read_glb  # noqa: E402
from anatomo_models.landmarks import KINDS  # noqa: E402


def check(manifest_path):
    m = json.load(open(manifest_path, encoding="utf-8"))
    gltf, nodes = read_glb(os.path.join(os.path.dirname(manifest_path), m["glb"]))
    assert gltf["asset"]["copyright"] == m["attribution"]
    assert gltf["asset"].get("extras", {}).get("license") == m["license"]
    # Geometry only: some source textures (Open3DModel) are under a non-commercial licence.
    assert not {"images", "textures", "samplers"} & set(gltf), "the model must not embed textures"
    assert [s["key"] for s in m["systems"]] == list(nodes)
    assert [s["index"] for s in m["structures"]] == list(range(len(m["structures"])))
    assert len({s["id"] for s in m["structures"]}) == len(m["structures"])
    for sys_ in m["systems"]:
        n = nodes[sys_["key"]]
        sid, tri = n["_STRUCTURE"], n["indices"]
        assert len(n["POSITION"]) == len(sid) == sys_["vertices"] and len(tri) == sys_["triangles"]
        assert np.all(np.isfinite(n["POSITION"])) and np.allclose(np.linalg.norm(n["NORMAL"], axis=1), 1, atol=1e-3)
        mine = [s for s in m["structures"] if s["system"] == sys_["key"]]
        assert len(mine) == sys_["structures"]
        v_end = t_end = 0
        for s in mine:
            (v0, vn), (t0, tn) = s["vertices"], s["triangles"]
            assert v0 == v_end and t0 == t_end and vn > 0 and tn > 0, s["id"]
            v_end, t_end = v0 + vn, t0 + tn
            assert np.all(sid[v0:v0 + vn] == s["index"]), s["id"]
            t = tri[t0:t0 + tn]
            assert t.min() >= v0 and t.max() < v0 + vn, s["id"]
            p = n["POSITION"][v0:v0 + vn]
            assert np.allclose(p.min(0), s["bbox"][0], atol=1e-5) and np.allclose(p.max(0), s["bbox"][1], atol=1e-5)
        assert v_end == sys_["vertices"] and t_end == sys_["triangles"]
    tris = sum(s["triangles"] for s in m["systems"])
    missing_fr = sum(s["fr"] is None for s in m["structures"])
    marks = check_landmarks(m, manifest_path.removesuffix(".json") + ".landmarks.json")
    print(f"{manifest_path}: OK ({len(m['structures'])} structures, {tris} triangles, "
          f"{len(nodes)} meshes, {missing_fr} without French name, {marks} landmarks)")


def check_landmarks(m, path):
    """Landmarks reference structures of the model, are unique per (id, side) and lie on their structure."""
    if not os.path.exists(path):
        return 0
    lm = json.load(open(path, encoding="utf-8"))
    assert lm["format"] == m["format"] and lm["version"] == m["version"] and lm["attribution"] == m["attribution"]
    by_id = {s["id"]: s for s in m["structures"]}
    keys = set()
    for x in lm["landmarks"]:
        key = (x["id"], x["side"])
        assert key not in keys, key
        keys.add(key)
        assert x["kind"] in KINDS and x["side"] in (None, "right", "left") and x["fr"].strip(), key
        s = by_id[x["structure"]]
        lo, hi = np.array(s["bbox"]) + [[-0.005], [0.005]]
        assert np.all(x["position"] >= lo) and np.all(x["position"] <= hi), key
        # A sided structure carries its side; on a midline structure, the subject's right is at negative x.
        named = next((w for w in ("right", "left") if re.search(rf"\b{w}\b", s["en"])), None)
        if named:
            assert x["side"] == named, key
        elif x["side"]:
            assert (x["position"][0] < 0.002) if x["side"] == "right" else (x["position"][0] > -0.002), key
    return len(lm["landmarks"])


if __name__ == "__main__":
    for p in sys.argv[1:]:
        check(p)
