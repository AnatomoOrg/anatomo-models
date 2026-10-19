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
from anatomo_models.junctions import JUNCTIONS, MAX_GAP, mesh_distance  # noqa: E402
from anatomo_models.landmarks import KINDS  # noqa: E402


def check(manifest_path):
    m = json.load(open(manifest_path, encoding="utf-8"))
    gltf, nodes, accessor = read_glb(os.path.join(os.path.dirname(manifest_path), m["glb"]), with_accessors=True)
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
        if "JOINTS_0" in n or "WEIGHTS_0" in n:  # optional: the os mesh, then the others (rig.skinned)
            assert "JOINTS_0" in n and "WEIGHTS_0" in n, f"{sys_['key']}: skin attributes"
            assert "rig" in m, f"{sys_['key']}: a skin (JOINTS_0) but the manifest has no rig section"
        if "_FIBER" in n or "_TENDON" in n:  # optional, muscles only
            assert sys_["key"] == "muscles" and "_FIBER" in n and "_TENDON" in n, sys_["key"]
            assert len(n["_FIBER"]) == len(n["_TENDON"]) == len(sid)
            assert np.allclose(np.linalg.norm(n["_FIBER"], axis=1), 1, atol=0.02)
            assert n["_TENDON"].min() >= 0 and n["_TENDON"].max() <= 1
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
    rig = check_rig(m, gltf, nodes, accessor) if "rig" in m or "skins" in gltf else ""
    tris = sum(s["triangles"] for s in m["systems"])
    missing_fr = sum(s["fr"] is None for s in m["structures"])
    marks = check_landmarks(m, manifest_path.removesuffix(".json") + ".landmarks.json")
    worst = check_junctions(m, nodes, JUNCTIONS.get(m["model"], []))
    print(f"{manifest_path}: OK ({len(m['structures'])} structures, {tris} triangles, "
          f"{len(nodes)} meshes, {missing_fr} without French name, {marks} landmarks, "
          f"{len(JUNCTIONS.get(m['model'], []))} vascular junctions, widest {worst:.2f} mm{rig})")


def check_rig(m, gltf, nodes, accessor):
    """Skin of the os mesh: every bone bound whole to the joint the manifest gives it, joints and movements of the
    manifest are the glb's nodes and animations, and each movement starts and ends in the anatomical position.
    The other skinned meshes (rig.skinned) have well-formed weights."""
    assert "rig" in m, "the glb has a skin (skins) but the manifest has no rig section"
    assert len(gltf.get("skins", [])) == 1, "the manifest has a rig section but the glb has no skin (or several)"
    rig = m["rig"]
    names = [j["name"] for j in rig["joints"]]
    skin, = gltf["skins"]
    node_names = [gltf["nodes"][i]["name"] for i in skin["joints"]]
    assert node_names == names, "skin joints differ from the manifest"
    skinned = [n["name"] for n in gltf["nodes"] if n.get("mesh") is not None and n.get("skin") == 0]
    assert sum("skin" in n for n in gltf["nodes"]) == len(skinned), "a node uses another skin"
    weighted = [name for name, n in nodes.items() if "JOINTS_0" in n]
    assert sorted(weighted) == sorted(skinned), f"skin attributes on {weighted}, skinned nodes {skinned}"
    assert rig.get("skinned", [rig["node"]]) == skinned and skinned[0] == rig["node"], "skinned nodes differ"
    for name in skinned[1:]:
        # Soft tissues: up to 4 joints, weights summing to 1, the heaviest first, and a joint of the skin.
        j_, w_ = nodes[name]["JOINTS_0"], nodes[name]["WEIGHTS_0"]
        assert np.allclose(w_.sum(1), 1, atol=1e-5) and np.all(np.diff(w_, axis=1) <= 1e-6), name
        assert j_.max() < len(names) and np.all(j_[w_ == 0] == 0), name
    os_ = nodes[rig["node"]]
    joint, weight = os_["JOINTS_0"], os_["WEIGHTS_0"]
    assert np.all(weight[:, 0] == 1) and np.all(weight[:, 1:] == 0) and np.all(joint[:, 1:] == 0)
    bound = {}
    for k, j in enumerate(rig["joints"]):
        assert (j["parent"] is None) == (k == 0) and (j["parent"] is None or names.index(j["parent"]) < k), j["name"]
        for sid in j["structures"]:
            assert sid not in bound, sid
            bound[sid] = k
    bones = [s for s in m["structures"] if s["system"] == rig["node"]]
    assert set(bound) == {s["id"] for s in bones}, "bones without a joint, or joints binding other structures"
    for s in bones:
        v0, vn = s["vertices"]
        assert np.all(joint[v0:v0 + vn, 0] == bound[s["id"]]), s["id"]
    # Joint nodes at rest: no rotation or scale, and their translations add up, from the root, to the pivots.
    pivot_of = {}
    for i, name in zip(skin["joints"], names):
        node = gltf["nodes"][i]
        assert "rotation" not in node and "scale" not in node and "matrix" not in node, f"{name}: not at rest"
        children = [gltf["nodes"][c]["name"] for c in node.get("children", [])]
        assert all(c in names for c in children), f"{name}: a child is not a joint"
        j = rig["joints"][names.index(name)]
        base = pivot_of[j["parent"]] if j["parent"] is not None else np.zeros(3)
        if j["parent"] is not None:
            parent_node = gltf["nodes"][skin["joints"][names.index(j["parent"])]]
            assert i in parent_node.get("children", []), f"{name}: not a child of {j['parent']} in the glb"
        pivot_of[name] = base + np.asarray(node.get("translation", [0, 0, 0]), float)
        assert np.allclose(pivot_of[name], j["pivot"], atol=1e-5), f"{name}: node translations do not add up to its pivot"
    root = skin["joints"][0]
    assert any(root in sc.get("nodes", []) for sc in gltf["scenes"]), "the joint tree's root is not in the scene"
    # Inverse bind matrices: a translation by -pivot.
    ibm = accessor(skin["inverseBindMatrices"]).reshape(-1, 4, 4).transpose(0, 2, 1)
    pivots = np.array([j["pivot"] for j in rig["joints"]])
    assert np.allclose(ibm[:, :3, :3], np.eye(3)) and np.allclose(ibm[:, :3, 3], -pivots, atol=1e-5)
    anims = {a["name"]: a for a in gltf.get("animations", [])}
    assert [mv["key"] for mv in rig["movements"]] == list(anims), "movements differ from the glb animations"
    for mv in rig["movements"]:
        a = anims[mv["key"]]
        moved = set()
        for c in a["channels"]:
            sampler = a["samplers"][c["sampler"]]
            t, v = accessor(sampler["input"]), accessor(sampler["output"])
            node = gltf["nodes"][c["target"]["node"]]
            moved.add(node["name"])
            assert np.all(np.diff(t) > 0) and t[0] == 0 and abs(t[-1] - mv["duration"]) < 1e-4, mv["key"]
            if c["target"]["path"] == "rotation":
                assert np.allclose(np.linalg.norm(v, axis=1), 1, atol=1e-5), mv["key"]
                assert np.allclose(v[[0, -1]], [0, 0, 0, 1]), f"{mv['key']}: does not start and end at rest"
            else:
                assert c["target"]["path"] == "translation", mv["key"]
                rest = np.asarray(node.get("translation", [0, 0, 0]))
                assert np.allclose(v[[0, -1]], rest, atol=1e-6), f"{mv['key']}: does not start and end at rest"
        assert moved == set(mv["joints"]), mv["key"]
    return f", {len(names)} joints, {len(anims)} movements"


def structure_mesh(s, nodes):
    """Vertices (mm) and faces of one structure of the glb."""
    n = nodes[s["system"]]
    (v0, vn), (t0, tn) = s["vertices"], s["triangles"]
    return n["POSITION"][v0:v0 + vn].astype(float) * 1000, n["indices"][t0:t0 + tn].reshape(-1, 3) - v0


def check_junctions(m, nodes, junctions, max_gap=MAX_GAP):
    """Parent -> branch pairs that touch in the source stay within `max_gap` mm of each other. Returns the widest."""
    by_id = {s["id"]: s for s in m["structures"]}
    worst, failed = 0.0, []
    for parent, branch in junctions:
        assert parent in by_id and branch in by_id, f"junction {parent} -> {branch}: structure missing from the model"
        d = mesh_distance(*structure_mesh(by_id[parent], nodes), *structure_mesh(by_id[branch], nodes))
        worst = max(worst, d)
        if d >= max_gap:
            failed.append(f"{by_id[parent]['en']} -> {by_id[branch]['en']}: {d:.2f} mm")
    assert not failed, f"vascular junctions open (>= {max_gap} mm): {failed}"
    return worst


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
