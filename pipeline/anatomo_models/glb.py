"""Minimal, deterministic glTF 2.0 binary (.glb) writer and reader for merged anatomy meshes.

One node and one mesh per system. Each mesh has a single indexed triangle primitive with
POSITION, NORMAL and the application-specific attribute `_STRUCTURE`: the index of the structure
each vertex belongs to, as listed in the model manifest. It is a float (exact for any index below
2^24) because glTF requires 4-byte aligned vertex attributes and shaders read floats anyway.
three.js exposes it as `geometry.attributes._structure`.

Optional (muscles): `_FIBER`, the unit fibre direction (VEC3, normalized BYTE), and `_TENDON`, the tendon
mask in [0, 1] (SCALAR, normalized UNSIGNED_BYTE), each in its own bufferView with a 4-byte stride.

Optional (bones, see rig.py): a skin. The `os` mesh then has JOINTS_0 (VEC4 UNSIGNED_BYTE, the joint first, then
zeros) and WEIGHTS_0 (VEC4 normalized UNSIGNED_BYTE, 1 0 0 0: rigid bones), the joints are nodes after the system
nodes, and the movements are animations of their rotations. The other meshes share the skin, with up to 4 joints
per vertex (weights summing to 255, the heaviest first).
"""
import json
import struct

import numpy as np

BYTE, UBYTE, FLOAT, USHORT, UINT = 5120, 5121, 5126, 5123, 5125
ARRAY_BUFFER, ELEMENT_ARRAY_BUFFER = 34962, 34963
GLB_MAGIC, CHUNK_JSON, CHUNK_BIN = 0x46546C67, 0x4E4F534A, 0x004E4942


def _pad(b, fill=b"\0"):
    return b + fill * (-len(b) % 4)


def write_glb(path, primitives, copyright=None, extras=None, rig=None):
    """primitives: list of dicts {name, positions (N,3), normals (N,3), structure (N,), indices (M,3), color (r,g,b)},
    and optionally fiber (N,3) unit vectors and tendon (N,) in [0, 1].
    rig: optional skin of the `os` primitive, from rig.build_rig (its vertex_joint matches the os vertices)."""
    gltf = {
        "asset": {"version": "2.0", "generator": "anatomo-models pipeline"},
        "scene": 0, "scenes": [{"nodes": list(range(len(primitives)))}],
        "nodes": [], "meshes": [], "materials": [], "accessors": [], "bufferViews": [],
        "buffers": [],
    }
    if copyright:
        gltf["asset"]["copyright"] = copyright
    if extras:
        gltf["asset"]["extras"] = extras
    blob = bytearray()

    def add(array, component, kind, target, minmax=False, stride=None, normalized=False):
        data = np.ascontiguousarray(array).tobytes()
        view = {"buffer": 0, "byteOffset": len(blob), "byteLength": len(data)}
        if target:
            view["target"] = target
        if stride:
            view["byteStride"] = stride
        gltf["bufferViews"].append(view)
        blob.extend(_pad(data))
        acc = {"bufferView": len(gltf["bufferViews"]) - 1, "componentType": component,
               "count": int(len(array)), "type": kind}
        if normalized:
            acc["normalized"] = True
        if minmax:
            acc["min"] = [float(v) for v in array.min(0)]
            acc["max"] = [float(v) for v in array.max(0)]
        gltf["accessors"].append(acc)
        return len(gltf["accessors"]) - 1

    for i, p in enumerate(primitives):
        pos = np.asarray(p["positions"], np.float32)
        nrm = np.asarray(p["normals"], np.float32)
        sid = np.asarray(p["structure"], np.float32)
        idx = np.asarray(p["indices"], np.uint32).reshape(-1)
        assert len(pos) == len(nrm) == len(sid) and idx.max() < len(pos)
        attrs = {
            "POSITION": add(pos, FLOAT, "VEC3", ARRAY_BUFFER, minmax=True),
            "NORMAL": add(nrm, FLOAT, "VEC3", ARRAY_BUFFER),
            "_STRUCTURE": add(sid, FLOAT, "SCALAR", ARRAY_BUFFER),
        }
        if p.get("fiber") is not None:
            # Vertex attributes are 4-byte aligned: one padding byte per vertex after the direction, three after the mask.
            fib = np.zeros((len(pos), 4), np.int8)
            fib[:, :3] = np.round(np.clip(np.asarray(p["fiber"], float), -1, 1) * 127)
            ten = np.zeros((len(pos), 4), np.uint8)
            ten[:, 0] = np.round(np.clip(np.asarray(p["tendon"], float), 0, 1) * 255)
            attrs["_FIBER"] = add(fib, BYTE, "VEC3", ARRAY_BUFFER, stride=4, normalized=True)
            attrs["_TENDON"] = add(ten, UBYTE, "SCALAR", ARRAY_BUFFER, stride=4, normalized=True)
        if rig is not None and p["name"] == "os":
            vj = np.asarray(rig["vertex_joint"])
            assert len(vj) == len(pos) and vj.max() < len(rig["joints"]) <= 256
            joints = np.zeros((len(pos), 4), np.uint8)
            joints[:, 0] = vj
            weights = np.zeros((len(pos), 4), np.uint8)
            weights[:, 0] = 255
        elif rig is not None and p["name"] in rig.get("soft", {}):
            joints, weights = rig["soft"][p["name"]]
            assert joints.shape == weights.shape == (len(pos), 4) and joints.max() < len(rig["joints"])
            assert np.all(weights.sum(1, dtype=int) == 255)
        else:
            joints = None
        if joints is not None:
            attrs["JOINTS_0"] = add(joints, UBYTE, "VEC4", ARRAY_BUFFER)
            attrs["WEIGHTS_0"] = add(weights, UBYTE, "VEC4", ARRAY_BUFFER, normalized=True)
        ind = add(idx, UINT, "SCALAR", ELEMENT_ARRAY_BUFFER)
        r, g, b = p.get("color", (0.8, 0.8, 0.8))
        gltf["materials"].append({"name": p["name"], "pbrMetallicRoughness": {
            "baseColorFactor": [r, g, b, 1.0], "metallicFactor": 0.0, "roughnessFactor": 0.7}})
        gltf["meshes"].append({"name": p["name"], "primitives": [
            {"attributes": attrs, "indices": ind, "material": i, "mode": 4}]})
        gltf["nodes"].append({"name": p["name"], "mesh": i})
    if rig is not None:
        names = [n["name"] for n in gltf["nodes"]]
        _write_rig(gltf, rig, add, [names.index(n) for n in ["os", *rig.get("soft", {})]])
    gltf["buffers"].append({"byteLength": len(blob)})

    js = _pad(json.dumps(gltf, ensure_ascii=False, separators=(",", ":")).encode(), b" ")
    total = 12 + 8 + len(js) + 8 + len(blob)
    with open(path, "wb") as f:
        f.write(struct.pack("<III", GLB_MAGIC, 2, total))
        f.write(struct.pack("<II", len(js), CHUNK_JSON) + js)
        f.write(struct.pack("<II", len(blob), CHUNK_BIN) + bytes(blob))


def _write_rig(gltf, rig, add, skinned):
    """Joint nodes (after the system nodes), the skin of the skinned nodes (os first) and the animations."""
    first = len(gltf["nodes"])
    joints = rig["joints"]
    for i, j in enumerate(joints):
        offset = j["pivot"] - (joints[j["parent"]]["pivot"] if j["parent"] is not None else 0)
        node = {"name": j["name"]}
        if np.any(offset != 0):
            node["translation"] = [float(x) for x in np.float32(offset)]
        children = [first + k for k, c in enumerate(joints) if c["parent"] == i]
        if children:
            node["children"] = children
        gltf["nodes"].append(node)
    roots = [first + i for i, j in enumerate(joints) if j["parent"] is None]
    assert len(roots) == 1
    gltf["scenes"][0]["nodes"].append(roots[0])
    # Inverse bind matrices (column-major): a translation by -pivot, the joints' rest rotation being the identity.
    ibm = np.tile(np.eye(4, dtype=np.float32), (len(joints), 1, 1))
    ibm[:, :3, 3] = -np.array([j["pivot"] for j in joints], np.float32)
    acc = add(ibm.transpose(0, 2, 1).reshape(len(joints), 16), FLOAT, "MAT4", None)
    gltf["skins"] = [{"name": "squelette", "inverseBindMatrices": acc, "skeleton": roots[0],
                      "joints": list(range(first, first + len(joints)))}]
    for node in skinned:
        gltf["nodes"][node]["skin"] = 0
    anims = []
    for a in rig["animations"]:
        samplers, channels, inputs = [], [], {}
        for c in a["channels"]:
            times = np.asarray(c["times"], np.float32)
            key = times.tobytes()
            if key not in inputs:
                inputs[key] = add(times[:, None], FLOAT, "SCALAR", None, minmax=True)
            values = np.asarray(c["values"], np.float32)
            out = add(values, FLOAT, "VEC4" if c["path"] == "rotation" else "VEC3", None)
            samplers.append({"input": inputs[key], "output": out, "interpolation": "LINEAR"})
            channels.append({"sampler": len(samplers) - 1, "target": {"node": first + c["joint"], "path": c["path"]}})
        anims.append({"name": a["key"], "samplers": samplers, "channels": channels})
    if anims:
        gltf["animations"] = anims


_DTYPES = {BYTE: np.int8, UBYTE: np.uint8, FLOAT: np.float32, USHORT: np.uint16, UINT: np.uint32}
_WIDTH = {"SCALAR": 1, "VEC3": 3, "VEC4": 4, "MAT4": 16}


def read_glb(path, with_accessors=False):
    """Read a .glb written by write_glb. Returns (gltf json, {node name: {attribute: array, 'indices': (M,3)}}) for
    the mesh nodes, and with_accessors, a function reading any accessor by index as a third item.
    Normalized attributes are returned as floats (BYTE / 127, UNSIGNED_BYTE / 255)."""
    raw = open(path, "rb").read()
    magic, version, total = struct.unpack_from("<III", raw)
    assert magic == GLB_MAGIC and version == 2 and total == len(raw)
    jlen, _ = struct.unpack_from("<II", raw, 12)
    gltf = json.loads(raw[20:20 + jlen])
    blen, _ = struct.unpack_from("<II", raw, 20 + jlen)
    blob = raw[28 + jlen:28 + jlen + blen]

    def acc(i):
        a = gltf["accessors"][i]; v = gltf["bufferViews"][a["bufferView"]]
        dt, w = np.dtype(_DTYPES[a["componentType"]]), _WIDTH[a["type"]]
        stride = v.get("byteStride", dt.itemsize * w) // dt.itemsize
        arr = np.frombuffer(blob, dt, a["count"] * stride, v["byteOffset"] + a.get("byteOffset", 0))
        arr = arr.reshape(a["count"], stride)[:, :w]
        if a.get("normalized"):
            arr = np.maximum(arr / {BYTE: 127.0, UBYTE: 255.0}[a["componentType"]], -1.0).astype(np.float32)
        return arr if a["type"] != "SCALAR" else arr[:, 0]

    out = {}
    for node in gltf["nodes"]:
        if "mesh" not in node:
            continue  # joint
        prim = gltf["meshes"][node["mesh"]]["primitives"][0]
        d = {k: acc(i) for k, i in prim["attributes"].items()}
        d["indices"] = acc(prim["indices"]).reshape(-1, 3)
        out[node["name"]] = d
    return (gltf, out, acc) if with_accessors else (gltf, out)
