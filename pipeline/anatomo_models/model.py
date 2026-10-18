"""Merge per-structure meshes into one mesh per system, and describe them in a manifest.

Within a system mesh, structures are laid out one after the other (sorted by FMA id): each
structure owns a contiguous range of vertices and of triangles, recorded in the manifest, and each
vertex carries the structure index in `_STRUCTURE`. A ray hit's face index therefore maps back to
its structure, and per-structure colour, visibility or transparency is a lookup on that index.
"""
import json

import fast_simplification
import numpy as np
import trimesh

from .glb import write_glb

FORMAT = "anatomo-models/1"

# Display order and viewer colours (the app sets its own materials).
SYSTEMS = {
    "os": "#e8dcc4", "muscles": "#b5534a", "arteres": "#d6262b", "veines": "#2f5fd0",
    "nerfs": "#e8c547", "organes": "#c98fa6", "peau": "#e0b49a",
}

# BodyParts3D frame (mm): +x = subject's left, -y = anterior, +z = superior.
# glTF frame (m): +Y up, +Z front (anterior), +X = subject's left. Proper rotation (det = +1).
BP3D_TO_GLTF = np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0]], float)

ATTRIBUTION = ("BodyParts3D, © The Database Center for Life Science, licensed under "
               "CC Attribution-Share Alike 2.1 Japan (https://creativecommons.org/licenses/by-sa/2.1/jp/). "
               "Modified by the Anatomo project.")
LICENSE = {"id": "CC-BY-SA-2.1-JP", "url": "https://creativecommons.org/licenses/by-sa/2.1/jp/"}


def to_gltf(points_mm):
    return np.asarray(points_mm, float) @ BP3D_TO_GLTF.T * 0.001


def clean(mesh):
    # Merging duplicated vertices makes BodyParts3D meshes watertight; decimating unmerged meshes tore holes.
    mesh.merge_vertices()
    mesh.update_faces(mesh.nondegenerate_faces())
    mesh.remove_unreferenced_vertices()
    return mesh


def normals(mesh):
    """Unit vertex normals; a vertex whose face normals cancel out takes the normal of one of its faces."""
    n = np.array(mesh.vertex_normals, float)
    bad = np.linalg.norm(n, axis=1) < 0.5
    if bad.any():
        first = np.full(len(n), -1)
        first[mesh.faces[::-1].reshape(-1)] = np.repeat(np.arange(len(mesh.faces))[::-1], 3)
        n[bad] = mesh.face_normals[first[bad]]
    return n / np.linalg.norm(n, axis=1, keepdims=True)


def decimate(mesh, target):
    if len(mesh.faces) <= target * 1.1:
        return mesh
    v, f = fast_simplification.simplify(mesh.vertices.astype(np.float32), mesh.faces.astype(np.int32),
                                        target_count=int(target))
    return clean(trimesh.Trimesh(v, f, process=True))


def build(structures, glb_path, manifest_path, model, version, sources, license=LICENSE, attribution=ATTRIBUTION):
    """structures: list of dicts {id, en, fr, system, mesh (trimesh, BodyParts3D frame, mm), source}, and optionally
    fiber (n,3, glTF frame) and tendon (n,) per vertex of mesh (fibers.annotate), for every structure of a system.

    license ({id, url}) and attribution apply to the whole model (glb asset and manifest)."""
    by_system = {s: sorted((x for x in structures if x["system"] == s), key=lambda x: x["id"]) for s in SYSTEMS}
    assert all(x["system"] in SYSTEMS for x in structures), "unknown system"
    ids = [x["id"] for x in structures]
    assert len(ids) == len(set(ids)), "duplicate structure id"
    primitives, entries, systems = [], [], []
    for system, items in by_system.items():
        if not items:
            continue
        pos, nrm, sid, idx, fib, ten = [], [], [], [], [], []
        nv = nt = 0
        with_fibers = [x.get("fiber") is not None for x in items]
        assert all(with_fibers) or not any(with_fibers), f"{system}: fibres on some structures only"
        for x in items:
            m, index = x["mesh"], len(entries)
            v = to_gltf(m.vertices)
            n = normals(m) @ BP3D_TO_GLTF.T
            pos.append(v); nrm.append(n); sid.append(np.full(len(v), index)); idx.append(m.faces + nv)
            if with_fibers[0]:
                assert len(x["fiber"]) == len(x["tendon"]) == len(v), x["id"]
                fib.append(x["fiber"]); ten.append(x["tendon"])
            entries.append({
                "index": index, "id": x["id"], "en": x["en"], "fr": x.get("fr"), "system": system,
                "vertices": [nv, len(v)], "triangles": [nt, len(m.faces)],
                "bbox": [np.round(v.min(0), 5).tolist(), np.round(v.max(0), 5).tolist()],
                "source": x["source"],
            })
            nv += len(v); nt += len(m.faces)
        color = tuple(int(SYSTEMS[system][i:i + 2], 16) / 255 for i in (1, 3, 5))
        primitives.append({"name": system, "positions": np.concatenate(pos), "normals": np.concatenate(nrm),
                           "structure": np.concatenate(sid), "indices": np.concatenate(idx), "color": color,
                           "fiber": np.concatenate(fib) if fib else None, "tendon": np.concatenate(ten) if ten else None})
        systems.append({"key": system, "node": system, "vertices": nv, "triangles": nt, "structures": len(items)})
    write_glb(glb_path, primitives, copyright=attribution,
              extras={"format": FORMAT, "model": model, "version": version, "license": license})
    manifest = {
        "format": FORMAT, "model": model, "version": version, "glb": glb_path.rsplit("/", 1)[-1],
        "frame": {"units": "m", "up": "+Y", "anterior": "+Z", "subject_left": "+X"},
        "license": license, "attribution": attribution, "sources": sources,
        "systems": systems, "structures": entries,
    }
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
        f.write("\n")
    return manifest
