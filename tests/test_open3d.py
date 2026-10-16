"""Upper-limb nerves from Open3DModel: name table, OBJ reader, registration, licence of each model."""
import json
import os
import re
import sys

import numpy as np
import pytest
import trimesh

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "pipeline"))
import build as build_script  # noqa: E402
import check  # noqa: E402
from anatomo_models import open3d  # noqa: E402
from anatomo_models.glb import read_glb  # noqa: E402
from anatomo_models.model import build, to_gltf  # noqa: E402


def test_nerve_table_maps_each_object_to_one_fma_concept():
    concepts = open3d.concepts()  # asserts that objects sharing a concept agree on its names
    assert len(concepts) == 48 and len(open3d.NERVES) == 50
    assert all(re.fullmatch(r"FMA\d+", fid) for fid in concepts)
    # One concept per name, one name per concept, in English and in French.
    assert len({en for en, _, _ in concepts.values()}) == len(concepts)
    assert len({fr for _, fr, _ in concepts.values()}) == len(concepts)
    for fid, (en, fr, objs) in concepts.items():
        assert en == en.lower() and en.strip() and fr.strip() and not fr[0].islower(), fid
        assert not re.search(r"\b(droit|gauche)\b", fr), fid  # no side in French names (docs/NOMS.md)
    # Only the deep branch / posterior interosseous nerve and the ulnar superficial branch merge objects.
    assert sorted(len(objs) for *_, objs in concepts.values())[-2:] == [2, 2]


def test_main_nerves_present():
    ids = open3d.concepts()
    for fid, name in [("FMA37067", "right median nerve"), ("FMA37320", "right ulnar nerve"),
                      ("FMA37070", "right radial nerve"), ("FMA37065", "right musculocutaneous nerve"),
                      ("FMA37073", "right axillary nerve"), ("FMA45238", "lateral cord of right brachial nerve plexus"),
                      ("FMA45240", "medial cord of right brachial nerve plexus"),
                      ("FMA45242", "posterior cord of right brachial nerve plexus"),
                      ("FMA65361", "superior trunk of right brachial nerve plexus")]:
        assert ids[fid][0] == name


def test_nerve_ids_do_not_clash_with_bodyparts3d_structures():
    fr = json.load(open(os.path.join(ROOT, "data", "fr_names.json"), encoding="utf-8"))
    assert not set(open3d.concepts()) & set(fr)


def test_licence_per_model():
    ul, fb = build_script.MODELS["upper_limb"], build_script.MODELS["full_body"]
    assert ul["license"] == {"id": "CC-BY-SA-4.0", "url": "https://creativecommons.org/licenses/by-sa/4.0/"}
    assert fb["license"] == {"id": "CC-BY-SA-2.1-JP", "url": "https://creativecommons.org/licenses/by-sa/2.1/jp/"}
    assert "Open3DModel" in ul["attribution"] and "BodyParts3D" in ul["attribution"]
    assert "Jan Kooloos" in ul["attribution"] and "Eungyeol Lee" in ul["attribution"]
    assert "Open3D" not in fb["attribution"]
    assert {s["license"] for s in ul["sources"]} == {"CC-BY-SA-2.1-JP", "CC-BY-SA-4.0"}
    assert {s["license"] for s in fb["sources"]} == {"CC-BY-SA-2.1-JP"}
    for f in ("CC-BY-SA-4.0.txt", "CC-BY-SA-2.1-JP.txt"):
        assert os.path.getsize(os.path.join(ROOT, "LICENSES", f)) > 10_000


def test_only_geometry_is_fetched():
    """The OBJ export has no textures; the Blender/glb exports carry CC BY-NC-SA textures."""
    lines = open(os.path.join(ROOT, "pipeline", "open3d.sha256")).read().split("\n")
    entries = [ln.split() for ln in lines if ln.strip()]
    assert entries and all(len(e) == 2 and re.fullmatch(r"[0-9a-f]{64}", e[0]) and e[1].endswith("-obj.zip")
                           for e in entries)
    script = open(os.path.join(ROOT, "pipeline", "fetch_open3d.sh")).read()
    assert not re.search(r"(blender|-glb)\.zip|texture-", script)


def test_read_obj(tmp_path):
    p = tmp_path / "x.obj"
    p.write_text("mtllib x.mtl\no A\nv 0 0 0\nv 1 0 0\nv 1 1 0\nv 0 1 0\nvt 0 0\nvn 0 0 1\nusemtl skin\n"
                 "f 1/1/1 2/1/1 3/1/1 4/1/1\no B\nv 5 5 5\nv 6 5 5\nv 6 6 5\nf -3 -2 -1\n", encoding="utf-8")
    m = open3d.read_obj(str(p), ["A", "B"])
    assert len(m["A"].faces) == 2 and len(m["A"].vertices) == 4  # quad as a fan
    assert np.allclose(m["B"].vertices, [[5, 5, 5], [6, 5, 5], [6, 6, 5]]) and len(m["B"].faces) == 1
    with pytest.raises(ValueError):
        open3d.read_obj(str(p), ["A", "C"])


def _rotation(deg, axis):
    return trimesh.transformations.rotation_matrix(np.radians(deg), axis)[:3, :3]


def synthetic(tmp_path):
    """An OBJ with every bone and nerve object (glTF frame, m), and the same bones in the model (BodyParts3D, mm),
    moved by a known similarity: returns (obj path, model items, expected transform in the BodyParts3D frame)."""
    rng = np.random.default_rng(0)
    m_true = 0.97 * _rotation(1.5, [0.3, 1, 0.2])
    t_true = np.array([5.0, -100.0, -25.0])
    lines, items, nv = [], [], 0

    def add(name, mesh):
        nonlocal nv
        lines.append(f"o {name}")
        lines.extend(f"v {x:.6f} {y:.6f} {z:.6f}" for x, y, z in mesh.vertices)
        lines.extend("f " + " ".join(str(i + 1 + nv) for i in f) for f in mesh.faces)
        nv += len(mesh.vertices)

    for k, (name, fid) in enumerate(open3d.BONES.items()):
        b = trimesh.creation.icosphere(subdivisions=2, radius=0.01 + 0.002 * (k % 5))
        b.apply_scale([1, 1.5 + 0.1 * k, 1])
        b.apply_translation([-0.15 - 0.01 * k, 1.4 - 0.04 * k, 0.03 * rng.standard_normal()])
        add(name, b)
        target = trimesh.Trimesh(open3d.to_bp3d(b.vertices) @ m_true.T + t_true, b.faces)
        items.append(dict(id=fid, en=f"bone {name}", fr=None, system="os", mesh=target, src=target, source="t"))
    for k, name in enumerate(open3d.NERVES):
        n = trimesh.creation.cylinder(radius=0.002, height=0.05, sections=8)
        n.apply_translation([-0.2 + 0.003 * k, 1.0 + 0.008 * k, 0.01])
        add(name, n)
    (tmp_path / open3d.OBJ).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(tmp_path / open3d.OBJ), items, (m_true, t_true)


def test_nerves_registered_on_model_bones(tmp_path):
    path, items, (m_true, t_true) = synthetic(tmp_path)
    logs = []
    nerves = open3d.nerves(path, items, log=logs.append)
    assert "scale 0.9700" in logs[0]
    assert sorted(x["id"] for x in nerves) == sorted(open3d.concepts())
    assert {x["system"] for x in nerves} == {"nerfs"} and {x["source"] for x in nerves} == {open3d.SOURCE_ID}
    raw = open3d.read_obj(path, ["Median_nerve.r"])["Median_nerve.r"]
    median = next(x for x in nerves if x["id"] == "FMA37067")
    expected = open3d.to_bp3d(raw.vertices) @ m_true.T + t_true
    assert np.allclose(np.sort(median["src"].vertices, 0), np.sort(expected, 0), atol=0.05)  # mm


def test_registration_failure_stops_the_build(tmp_path):
    path, items, _ = synthetic(tmp_path)
    items[0]["src"] = items[0]["mesh"] = trimesh.Trimesh(items[0]["mesh"].vertices * 1.5, items[0]["mesh"].faces)
    with pytest.raises(SystemExit):
        open3d.nerves(path, items, log=lambda *_: None)
    with pytest.raises(SystemExit):
        open3d.nerves(path, items[1:], log=lambda *_: None)  # a bone missing from the model


def test_model_with_nerves(tmp_path):
    path, items, _ = synthetic(tmp_path)
    items += open3d.nerves(path, items, log=lambda *_: None)
    ul = build_script.MODELS["upper_limb"]
    m = build(items, str(tmp_path / "ul.glb"), str(tmp_path / "ul.json"), "upper_limb", "0.0.0", **ul)
    check.check(str(tmp_path / "ul.json"))
    assert [s["key"] for s in m["systems"]] == ["os", "nerfs"]
    assert m["license"]["id"] == "CC-BY-SA-4.0" and m["attribution"] == ul["attribution"]
    nerfs = [s for s in m["structures"] if s["system"] == "nerfs"]
    assert len(nerfs) == 48 and all(s["fr"] and s["source"] == "open3dmodel" for s in nerfs)
    gltf, nodes = read_glb(str(tmp_path / "ul.glb"))
    assert gltf["asset"]["extras"]["license"]["id"] == "CC-BY-SA-4.0"
    assert gltf["asset"]["copyright"] == ul["attribution"]
    # Geometry only: no image, texture, sampler nor texture coordinates.
    assert not {"images", "textures", "samplers"} & set(gltf)
    assert all("TEXCOORD_0" not in p["attributes"] for mesh in gltf["meshes"] for p in mesh["primitives"])
    assert np.allclose(nodes["nerfs"]["POSITION"][:3], to_gltf(next(x for x in items if x["id"] == nerfs[0]["id"])
                                                               ["mesh"].vertices[:3]), atol=1e-6)
