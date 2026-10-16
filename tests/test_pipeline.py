import json
import os
import sys

import numpy as np
import pytest
import trimesh

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pipeline"))
import check  # noqa: E402
import upper_limb  # noqa: E402
from anatomo_models.glb import read_glb  # noqa: E402
from anatomo_models.model import build, to_gltf  # noqa: E402


def sample():
    a = trimesh.creation.icosphere(subdivisions=2, radius=10)
    b = trimesh.creation.box(extents=(5, 5, 20)); b.apply_translation((30, 0, 0))
    c = trimesh.creation.cylinder(radius=3, height=40); c.apply_translation((0, 30, 0))
    return [
        dict(id="FMA2", en="b", fr="B", system="muscles", mesh=b, source="t"),
        dict(id="FMA9", en="c", fr=None, system="os", mesh=c, source="t"),
        dict(id="FMA1", en="a", fr="A", system="os", mesh=a, source="t"),
    ]


def test_build_roundtrip(tmp_path):
    m = build(sample(), str(tmp_path / "x.glb"), str(tmp_path / "x.json"), "x", "0.0.0", [])
    check.check(str(tmp_path / "x.json"))
    # Systems in display order, structures sorted by id within a system.
    assert [s["key"] for s in m["systems"]] == ["os", "muscles"]
    assert [s["id"] for s in m["structures"]] == ["FMA1", "FMA9", "FMA2"]
    gltf, nodes = read_glb(str(tmp_path / "x.glb"))
    os_ = nodes["os"]
    assert os_["_STRUCTURE"].dtype == np.float32 and set(os_["_STRUCTURE"]) == {0, 1}
    # Positions are the source meshes converted to the glTF frame.
    a = sample()[2]["mesh"]
    assert np.allclose(os_["POSITION"][:len(a.vertices)], to_gltf(a.vertices), atol=1e-6)


def test_glb_loads_in_trimesh(tmp_path):
    build(sample(), str(tmp_path / "x.glb"), str(tmp_path / "x.json"), "x", "0.0.0", [])
    scene = trimesh.load(str(tmp_path / "x.glb"))
    assert sorted(scene.geometry) == ["muscles", "os"]
    assert sum(len(g.faces) for g in scene.geometry.values()) == sum(len(s["mesh"].faces) for s in sample())


def test_frame():
    # BodyParts3D: anterior = -y, superior = +z, subject's left = +x (mm). glTF: +Z, +Y, +X (m).
    assert np.allclose(to_gltf([[0, -1000, 0]]), [[0, 0, 1]])
    assert np.allclose(to_gltf([[0, 0, 1000]]), [[0, 1, 0]])
    assert np.allclose(to_gltf([[1000, 0, 0]]), [[1, 0, 0]])


def test_duplicate_ids_rejected(tmp_path):
    items = sample(); items[1]["id"] = "FMA1"
    with pytest.raises(AssertionError):
        build(items, str(tmp_path / "x.glb"), str(tmp_path / "x.json"), "x", "0.0.0", [])


@pytest.mark.parametrize("name,expected", [
    ("right humerus", "os"),
    ("right ulnar artery", "arteres"),
    ("ulnar recurrent artery of right upper limb", "arteres"),  # bone word in a vessel name
    ("right cephalic vein", "veines"),
    ("right biceps brachii", "muscles"),
    ("extensor digitorum longus of right leg", None),
    ("left humerus", None),
    ("branch of right brachial artery", None),
])
def test_upper_limb_system(name, expected):
    assert upper_limb.system(name) == expected


def test_fr_names_are_fma_ids():
    fr = json.load(open(os.path.join(os.path.dirname(__file__), "..", "data", "fr_names.json"), encoding="utf-8"))
    assert all(k.startswith("FMA") and v.strip() for k, v in fr.items())


def test_most_specific_owner(tmp_path):
    from anatomo_models.bp3d import BP3D
    H = "concept id\trepresentation id\tname\n"
    (tmp_path / "isa_parts_list_e.txt").write_text(H + "FMA1\tx\tbody of organ\nFMA2\tx\tbody of sternum\n")
    (tmp_path / "partof_parts_list_e.txt").write_text(H + "FMA3\tx\tsternum\n")
    E = "concept id\trepresentation id\telement file id\n"
    (tmp_path / "isa_element_parts.txt").write_text(E + "FMA1\tx\tFJ1\nFMA2\tx\tFJ1\nFMA2\tx\tFJ2\n")
    (tmp_path / "partof_element_parts.txt").write_text(E + "FMA3\tx\tFJ1\nFMA3\tx\tFJ2\n")
    R = "parent id\tparent name\tchild id\tchild name\n"
    (tmp_path / "isa_inclusion_relation_list.txt").write_text(R + "FMA1\tbody of organ\tFMA2\tbody of sternum\n")
    (tmp_path / "partof_inclusion_relation_list.txt").write_text(R + "FMA3\tsternum\tFMA2\tbody of sternum\n")
    for d in ("isa_BP3D_4.0_obj_99", "partof_BP3D_4.0_obj_99"):
        (tmp_path / d).mkdir()
    bp = BP3D(str(tmp_path))
    # 'body of organ' owns fewer files but is an ancestor of 'body of sternum'.
    assert bp.most_specific_owner("FJ1") == "FMA2"
    assert bp.most_specific_owner("FJ2") == "FMA2"
    assert bp.most_specific_owner("FJ9") is None
