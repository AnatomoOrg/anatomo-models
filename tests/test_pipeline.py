import json
import os
import re
import sys

import numpy as np
import pytest
import trimesh

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pipeline"))
import check  # noqa: E402
import full_body  # noqa: E402
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
    ("right superficial palmar arterial arch", "arteres"),
    ("right anterior interosseous artery", "arteres"),
    ("right radial vein", "veines"),
    ("right median antebrachial vein", "veines"),
    ("right brachiocephalic vein", None),
    ("right internal thoracic artery", None),
    ("right anterior circumflex humeral artery", "arteres"),
    ("right posterior circumflex humeral artery", "arteres"),
    ("right lateral thoracic artery", "arteres"),
    ("right thoracodorsal artery", "arteres"),
    ("trunk of right thoraco-acromial artery", "arteres"),
    ("deltoid branch of right thoraco-acromial artery", "arteres"),
    ("right radial recurrent artery", "arteres"),
    ("middle collateral branch of right deep brachial artery", "arteres"),
    ("radial collateral branch of right deep brachial artery", "arteres"),
    ("dorsal carpal branch of right radial artery", "arteres"),
    ("right dorsal carpal branch of ulnar artery", "arteres"),
    ("right fourth common palmar digital artery", "arteres"),
    ("medial proper palmar digital artery of right index finger", "arteres"),
    ("right arteria princeps pollicis", "arteres"),
    ("right arteria radialis indicis", "arteres"),
    ("right anterior circumflex humeral vein", "veines"),
    ("right superficial palmar venous arch", "veines"),
    ("right deep palmar venous arch", "veines"),
    ("dorsal venous network of right hand", "veines"),
    ("proper palmar digital vein of right ring finger", "veines"),
    ("ascending part of right trapezius", "muscles"),
    ("flexor retinaculum of right wrist", "muscles"),
    ("right trapezium", "os"),
    ("left lateral thoracic artery", None),
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


class NoTree:
    containers = {}

    def ancestor_in(self, concept, roots):
        return None


@pytest.mark.parametrize("name,expected", [
    ("anterior superior tributary of right hepatic biliary tree", "organes"),
    ("right superior parietal lobule", "organes"),
    ("right lacrimal gland", "organes"),
    ("proximal part of ileum", "organes"),
    ("right seventh rib", "os"),
    ("right parietal bone", "os"),
    ("right deep palmar venous arch", "veines"),
    ("right deep palmar arch", "arteres"),
    ("right vastus lateralis", "muscles"),
    ("ascending part of right trapezius", "muscles"),
    ("right trapezium", "os"),
    ("tarsal plate of right upper eyelid", "organes"),
    ("right thyrohyoid membrane", "organes"),
    ("right iliotibial tract", "organes"),
    ("choroid plexus of cerebral hemisphere", "organes"),
    ("right brachial plexus", "nerfs"),
])
def test_full_body_system_by_name(name, expected):
    assert full_body.system(NoTree(), [], name) == expected


def test_unpack_backslash_archive(tmp_path):
    """The 3.0 archive stores backslash paths; unzip warns (exit 1) but the unpack must succeed."""
    import shutil
    import subprocess
    import zipfile
    if not shutil.which("unzip"):
        pytest.skip("unzip not installed")
    with zipfile.ZipFile(tmp_path / "BodyParts3D_3.0_obj_95.zip", "w") as z:
        info = zipfile.ZipInfo("BodyParts3D_3.0_obj_95\\FMA23130.obj")
        info.create_system = 0  # made on MS-DOS/Windows, like the real archive: unzip maps backslashes
        z.writestr(info, "v 0 0 0\n")
    for name in ("isa_BP3D_4.0_obj_99", "partof_BP3D_4.0_obj_99"):
        with zipfile.ZipFile(tmp_path / f"{name}.zip", "w") as z:
            z.writestr(f"{name}/FJ1.obj", "v 0 0 0\n")
    script = os.path.join(os.path.dirname(__file__), "..", "pipeline", "unpack_bp3d.sh")
    for _ in range(2):  # second run: already unpacked, nothing to do
        subprocess.run(["bash", script, str(tmp_path)], check=True)
    assert (tmp_path / "BodyParts3D_3.0_obj_95" / "FMA23130.obj").is_file()
    assert (tmp_path / "isa_BP3D_4.0_obj_99" / "FJ1.obj").is_file()


def test_system_overrides_are_valid():
    from anatomo_models.model import SYSTEMS
    from anatomo_models.overrides import SYSTEM_OVERRIDES
    for fid, (system, reason) in SYSTEM_OVERRIDES.items():
        assert fid.startswith("FMA") and system in SYSTEMS and reason.strip(), fid


@pytest.mark.parametrize("fid,system", [
    ("FMA25058", "organes"),  # intervertebral disc C2-C3
    ("FMA55099", "organes"),  # thyroid cartilage
    ("FMA59838", "organes"),  # septal nasal cartilage
    ("FMA54241", "peau"),  # hair of head
    ("FMA54319", "peau"),  # pubic hair
    ("FMA11336", "muscles"),  # linea alba
    ("FMA15746", "organes"),  # liver segment VIII
    ("FMA259248", "arteres"),  # abdominal aorta
])
def test_system_overrides_audit(fid, system):
    from anatomo_models.overrides import SYSTEM_OVERRIDES
    assert SYSTEM_OVERRIDES[fid][0] == system


def test_system_override_moves_geometry(tmp_path):
    """An overridden structure is written in the mesh of its new system, and the manifest agrees."""
    from anatomo_models.overrides import apply_system_overrides
    items, logs = sample(), []
    found = apply_system_overrides(items, {"FMA9": ("organes", "test"), "FMA2": ("muscles", "test"),
                                           "FMA404": ("os", "test")}, log=logs.append)
    assert found == {"FMA9", "FMA2"}
    assert any("not needed" in x for x in logs)  # FMA2 already in muscles
    m = build(items, str(tmp_path / "x.glb"), str(tmp_path / "x.json"), "x", "0.0.0", [])
    check.check(str(tmp_path / "x.json"))
    assert [s["key"] for s in m["systems"]] == ["os", "muscles", "organes"]
    by_id = {s["id"]: s for s in m["structures"]}
    assert by_id["FMA9"]["system"] == "organes"
    gltf, nodes = read_glb(str(tmp_path / "x.glb"))
    c = sample()[1]["mesh"]
    assert len(nodes["organes"]["POSITION"]) == len(c.vertices)
    assert set(nodes["organes"]["_STRUCTURE"]) == {by_id["FMA9"]["index"]}
    assert set(nodes["os"]["_STRUCTURE"]) == {by_id["FMA1"]["index"]}


def test_fr_names_audit():
    fr = json.load(open(os.path.join(os.path.dirname(__file__), "..", "data", "fr_names.json"), encoding="utf-8"))
    assert fr["FMA24439"] == fr["FMA24440"] == "Triquétrum"
    assert fr["FMA25058"] == "Disque intervertébral C2-C3"  # 'intervertebral disk of axis': below the axis
    assert fr["FMA54397"] == "Gencive supérieure"  # 'upper jaw': its mesh is the gingiva
    assert fr["FMA53637"] == "Os zygomatique"  # 'right cheek': its mesh is the zygomatic bone
    # 'fourth common palmar digital artery': its mesh runs to the pulp of the little finger
    assert fr["FMA85123"] == fr["FMA85124"] == "Artère digitale palmaire propre médiale du petit doigt"
    # Meshes found elsewhere than their FMA concept (anatomical audit of 2026-10-16).
    assert fr["FMA22954"] == "Veines métatarsiennes dorsales"  # on the feet
    assert fr["FMA8620"] == "Artère segmentaire antérieure du rein"  # in the right kidney
    assert fr["FMA71562"] != "Rameaux calcanéens de l'artère tibiale postérieure"  # at the root of the thigh
    assert fr["FMA4771"] == fr["FMA44340"]  # same mesh as the superficial epigastric vein
    assert fr["FMA49214"] == fr["FMA7266"] and fr["FMA71889"] == fr["FMA76903"]  # duplicated meshes
    assert fr["FMA49052"] == "Muscle oblique supérieur de l'œil" and fr["FMA24528"] == "Os cuboïde"
    # Pulmonary segmental vessels, formerly published under the id of their lung segment (full_body.OWNER_FIXES).
    assert fr["FMA8642"] == "Artère segmentaire supérieure" and fr["FMA9438"] == "Veine segmentaire postérieure"
    assert not {"FMA7365", "FMA7386", "FMA7376", "FMA7377"} & set(fr)
    assert not any("Mâchoire" in v or "Triquetrum" in v for v in fr.values())


def test_landmark_names_audit():
    from anatomo_models.landmark_catalog import CATALOGUE
    from anatomo_models.landmarks import META
    names = {fr for e in CATALOGUE for _, fr, *_ in e.marks} | {fr for fr, _ in META.values()}
    assert "Tubercule majeur" in names and "Tubercule mineur" in names
    assert not any(re.search(r"(?i)\b(grand|petit) tubercule", n) for n in names)
    assert "Condyle latéral du tibia (plateau tibial)" in names and "Condyle latéral du fémur" in names
    assert "Processus costiforme de L3" in names and "Processus transverse de L3" not in names
    assert "Processus transverse de T1" in names
    assert "Acétabulum" not in names and "Fosse de l'acétabulum" in names


def test_v3_field():
    from anatomo_models.v3 import Field
    a = np.array([[0.0, 0, 0], [1, 0, 0], [0, 1, 0]])
    # One translation everywhere: every point moves by it.
    f = Field([(a, np.array([1.0, 2, 3])), (a + 100, np.array([1.0, 2, 3]))])
    assert np.allclose(f(np.array([[5.0, 5, 5], [50, 50, 50]])), [[6, 7, 8], [51, 52, 53]])
    # Two regions: a point follows the nearest one, a point halfway gets the mean.
    f = Field([(a, np.array([0.0, 0, 0])), (a + [1000, 0, 0], np.array([0.0, 0, 10]))])
    near0, near1, mid = f(np.array([[0.0, 0, 0], [1000.0, 0, 0], [500.5, 0.5, 0]]))
    assert np.allclose(near0, [0, 0, 0], atol=0.01) and np.allclose(near1, [1000, 0, 10], atol=0.01)
    assert np.allclose(mid[2], 5, atol=0.5)


def test_v3_fit_translation():
    from anatomo_models.v3 import fit_translation
    m4 = trimesh.creation.icosphere(subdivisions=3, radius=20)
    m3 = m4.copy(); m3.apply_translation((-4, 7, 12))
    t, residual, coverage, _ = fit_translation(m3, m4, t0=(0, 0, 0))
    assert np.allclose(t, (4, -7, -12), atol=0.2) and residual < 0.5 and coverage < 1


def test_v3_additions_are_named():
    from anatomo_models.model import SYSTEMS
    fr = json.load(open(os.path.join(os.path.dirname(__file__), "..", "data", "fr_names.json"), encoding="utf-8"))
    for table in (full_body.V3_ADDITIONS, upper_limb.V3_ADDITIONS):
        for fid, system in table.items():
            assert re.fullmatch(r"FMA\d+", fid) and system in SYSTEMS and fr.get(fid), fid


def test_owner_fixes():
    fr = json.load(open(os.path.join(os.path.dirname(__file__), "..", "data", "fr_names.json"), encoding="utf-8"))
    for old, new in full_body.OWNER_FIXES.items():
        assert re.fullmatch(r"FMA\d+", old) and re.fullmatch(r"FMA\d+", new) and fr.get(new), (old, new)


def test_tube_decimation_is_lighter():
    from anatomo_models.model import SYSTEMS
    assert full_body.TUBES <= set(SYSTEMS)
    assert full_body.TUBE_KEEP > 0.2 and full_body.TUBE_MIN_TRIS > full_body.MIN_TRIS


def test_mesh_distance():
    from anatomo_models.junctions import mesh_distance
    a = trimesh.creation.icosphere(subdivisions=3, radius=10)
    b = a.copy(); b.apply_translation((22, 0, 0))
    assert mesh_distance(a.vertices, a.faces, b.vertices, b.faces) == pytest.approx(2, abs=1e-6)
    b.apply_translation((-4, 0, 0))
    assert mesh_distance(a.vertices, a.faces, b.vertices, b.faces) == 0
    # Face against face with no vertex nearby; a bar through a plate with no vertex inside the plate.
    plate = trimesh.creation.box(extents=(100, 100, 1))
    cube = trimesh.creation.box(extents=(1, 1, 1)); cube.apply_translation((3, 7, 1.5))
    assert mesh_distance(plate.vertices, plate.faces, cube.vertices, cube.faces) == pytest.approx(0.5, abs=1e-6)
    bar = trimesh.creation.box(extents=(1, 1, 40))
    assert mesh_distance(plate.vertices, plate.faces, bar.vertices, bar.faces) == 0


def test_junctions_list():
    from anatomo_models.junctions import JUNCTIONS
    pairs = JUNCTIONS["full_body"]
    assert len(set(pairs)) == len(pairs) and all(a != b for a, b in pairs)
    assert all(re.fullmatch(r"FMA\d+", x) for pair in pairs for x in pair)


def test_check_junctions(tmp_path):
    m = build(sample(), str(tmp_path / "x.glb"), str(tmp_path / "x.json"), "x", "0.0.0", [])
    gltf, nodes = read_glb(str(tmp_path / "x.glb"))
    # Faceted sphere of radius 10 at the origin, box 5 mm wide centred at x = 30: 17.5 mm apart, a bit more.
    assert 17.5 <= check.check_junctions(m, nodes, [("FMA1", "FMA2")], max_gap=25) < 20
    with pytest.raises(AssertionError, match="open"):
        check.check_junctions(m, nodes, [("FMA1", "FMA2")])
    with pytest.raises(AssertionError, match="missing"):
        check.check_junctions(m, nodes, [("FMA1", "FMA404")])
