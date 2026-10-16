"""Minimal, deterministic glTF 2.0 binary (.glb) writer and reader for merged anatomy meshes.

One node and one mesh per system. Each mesh has a single indexed triangle primitive with
POSITION, NORMAL and the application-specific attribute `_STRUCTURE`: the index of the structure
each vertex belongs to, as listed in the model manifest. It is a float (exact for any index below
2^24) because glTF requires 4-byte aligned vertex attributes and shaders read floats anyway.
three.js exposes it as `geometry.attributes._structure`.
"""
import json
import struct

import numpy as np

FLOAT, USHORT, UINT = 5126, 5123, 5125
ARRAY_BUFFER, ELEMENT_ARRAY_BUFFER = 34962, 34963
GLB_MAGIC, CHUNK_JSON, CHUNK_BIN = 0x46546C67, 0x4E4F534A, 0x004E4942


def _pad(b, fill=b"\0"):
    return b + fill * (-len(b) % 4)


def write_glb(path, primitives, copyright=None, extras=None):
    """primitives: list of dicts {name, positions (N,3), normals (N,3), structure (N,), indices (M,3), color (r,g,b)}."""
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

    def add(array, component, kind, target, minmax=False):
        data = np.ascontiguousarray(array).tobytes()
        gltf["bufferViews"].append({"buffer": 0, "byteOffset": len(blob), "byteLength": len(data), "target": target})
        blob.extend(_pad(data))
        acc = {"bufferView": len(gltf["bufferViews"]) - 1, "componentType": component,
               "count": int(len(array)), "type": kind}
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
        ind = add(idx, UINT, "SCALAR", ELEMENT_ARRAY_BUFFER)
        r, g, b = p.get("color", (0.8, 0.8, 0.8))
        gltf["materials"].append({"name": p["name"], "pbrMetallicRoughness": {
            "baseColorFactor": [r, g, b, 1.0], "metallicFactor": 0.0, "roughnessFactor": 0.7}})
        gltf["meshes"].append({"name": p["name"], "primitives": [
            {"attributes": attrs, "indices": ind, "material": i, "mode": 4}]})
        gltf["nodes"].append({"name": p["name"], "mesh": i})
    gltf["buffers"].append({"byteLength": len(blob)})

    js = _pad(json.dumps(gltf, ensure_ascii=False, separators=(",", ":")).encode(), b" ")
    total = 12 + 8 + len(js) + 8 + len(blob)
    with open(path, "wb") as f:
        f.write(struct.pack("<III", GLB_MAGIC, 2, total))
        f.write(struct.pack("<II", len(js), CHUNK_JSON) + js)
        f.write(struct.pack("<II", len(blob), CHUNK_BIN) + bytes(blob))


_DTYPES = {FLOAT: np.float32, USHORT: np.uint16, UINT: np.uint32}
_WIDTH = {"SCALAR": 1, "VEC3": 3}


def read_glb(path):
    """Read a .glb written by write_glb. Returns (gltf json, {node name: {attribute: array, 'indices': (M,3)}})."""
    raw = open(path, "rb").read()
    magic, version, total = struct.unpack_from("<III", raw)
    assert magic == GLB_MAGIC and version == 2 and total == len(raw)
    jlen, _ = struct.unpack_from("<II", raw, 12)
    gltf = json.loads(raw[20:20 + jlen])
    blen, _ = struct.unpack_from("<II", raw, 20 + jlen)
    blob = raw[28 + jlen:28 + jlen + blen]

    def acc(i):
        a = gltf["accessors"][i]; v = gltf["bufferViews"][a["bufferView"]]
        arr = np.frombuffer(blob, _DTYPES[a["componentType"]], a["count"] * _WIDTH[a["type"]], v["byteOffset"])
        return arr.reshape(a["count"], -1) if a["type"] != "SCALAR" else arr

    out = {}
    for node in gltf["nodes"]:
        prim = gltf["meshes"][node["mesh"]]["primitives"][0]
        d = {k: acc(i) for k, i in prim["attributes"].items()}
        d["indices"] = acc(prim["indices"]).reshape(-1, 3)
        out[node["name"]] = d
    return gltf, out
