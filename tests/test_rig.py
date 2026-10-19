import json
import os
import sys

import numpy as np
import pytest
import trimesh

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pipeline"))
import check  # noqa: E402
from anatomo_models import rig  # noqa: E402
from anatomo_models.glb import read_glb  # noqa: E402
from anatomo_models.model import BP3D_TO_GLTF, build  # noqa: E402

# A synthetic right upper limb in the glTF frame (m): the subject's right is at -X, anterior +Z, up +Y.
SC = np.array([-0.01, 1.33, 0.13])  # sternoclavicular joint
HEAD = np.array([-0.16, 1.315, 0.075])  # centre of the humeral head
ELBOW = np.array([-0.23, 1.046, 0.07])  # centre of the capitulum
WRIST = np.array([-0.245, 0.80, 0.118])


def _bp3d(mesh):
    """A mesh built in the glTF frame (m), moved to the BodyParts3D frame (mm) that model.build expects."""
    mesh = mesh.copy()
    mesh.vertices = (np.asarray(mesh.vertices) * 1000) @ BP3D_TO_GLTF
    return mesh


def _sphere(c, r):
    m = trimesh.creation.icosphere(subdivisions=3, radius=r)
    m.apply_translation(c)
    return m


def _rod(a, b, r=0.008):
    return trimesh.creation.cylinder(radius=r, segment=[a, b], sections=12)


def arm():
    """(items for model.build, landmarks): the bones of a right upper limb, as simple shapes."""
    shapes = {
        "right clavicle": _rod(SC, HEAD + [0.01, 0.03, 0.0]),
        "right scapula": trimesh.creation.box(extents=(0.02, 0.12, 0.08)).apply_translation(HEAD + [0.04, -0.04, -0.05]),
        "right humerus": trimesh.util.concatenate([_sphere(HEAD, 0.022), _rod(HEAD - [0, 0.03, 0], ELBOW + [0, 0.03, 0], 0.01),
                                                   _sphere(ELBOW, 0.01)]),
        "right ulna": _rod(ELBOW + [0.012, -0.01, -0.01], WRIST + [0.012, 0.01, 0]),
        "right radius": _rod(ELBOW + [-0.006, -0.015, 0], WRIST + [-0.012, 0.01, 0]),
        "right lunate": _sphere(WRIST - [0, 0.015, 0], 0.007),
        "proximal phalanx of right index finger": _rod(WRIST - [0, 0.08, 0], WRIST - [0, 0.11, 0], 0.004),
    }
    items = [dict(id=f"FMA{100 + i}", en=en, fr=en, system="os", mesh=_bp3d(m), source="t")
             for i, (en, m) in enumerate(shapes.items())]
    marks = [
        ("clavicule.extremite-sternale", SC),
        ("humerus.tete", HEAD + [-0.022, 0, 0]),
        ("humerus.capitulum", ELBOW + [-0.004, -0.009, 0.002]),
        ("humerus.epicondyle-lateral", ELBOW + [-0.03, 0.005, 0]),
        ("humerus.epicondyle-medial", ELBOW + [0.035, 0.005, 0]),
        ("radius.processus-styloide", WRIST + [-0.025, 0, 0]),
        ("ulna.processus-styloide", WRIST + [0.02, 0, 0]),
    ]
    return items, [{"id": i, "side": "right", "position": p.tolist()} for i, p in marks]


def built(tmp_path, items=None, marks=None):
    if items is None:
        items, marks = arm()
    m = build(items, str(tmp_path / "x.glb"), str(tmp_path / "x.json"), "x", "0.0.0", [],
              rig=lambda entries, positions: rig.build_rig(entries, positions, marks))
    return m


@pytest.mark.parametrize("en,joint", [
    ("left side of bony pelvis", "bassin"),
    ("posterior part of pelvis", "bassin"),
    ("third lumbar vertebra", "lombaire-3"),
    ("twelfth thoracic vertebra", "thorax"),
    ("right first costal cartilage", "thorax"),
    ("left eleventh rib", "thorax"),
    ("xiphoid process", "thorax"),
    ("seventh cervical vertebra", "cervicale-7"),
    ("axis", "cervicale-2"),
    ("atlas", "atlas"),
    ("hyoid bone", "cervicale-3"),
    ("skeleton of mouth", "mandibule"),
    ("right lower first secondary molar tooth", "mandibule"),
    ("left upper secondary canine tooth", "tete"),
    ("right cheek", "tete"),
    ("right temporal bone", "tete"),
    ("basicranium", "tete"),
    ("left lateral wall of internal nose", "tete"),
    ("right clavicle", "ceinture-d"),
    ("left scapula", "ceinture-g"),
    ("right humerus", "epaule-d"),
    ("left ulna", "coude-g"),
    ("right radius", "avant-bras-d"),
    ("left pisiform", "poignet-g"),
    ("distal phalanx of right thumb", "poignet-d"),
    ("middle phalanx of left little finger", "poignet-g"),
    ("right femur", "hanche-d"),
    ("left fibula", "genou-g"),
    ("right patella", "patella-d"),
    ("navicular bone of left foot", "cheville-g"),
    ("sesamoid bone of right foot", "cheville-d"),
    ("proximal phalanx of left big toe", "cheville-g"),
    ("right intermediate cuneiform bone", "cheville-d"),
    ("stapes", None),
])
def test_bind(en, joint):
    assert rig.bind(en) == joint


def test_joint_names_are_safe_node_names():
    # three.js PropertyBinding drops [ ] . : / from node names: the animations would not find their joints.
    for base in rig.JOINTS:
        for side in (("right", "left") if base in rig.SIDED else (None,)):
            name = rig.joint_name(base, side)
            assert name.isascii() and not set("[].:/ ") & set(name), name
    assert rig.joint_fr("epaule", "left") == "Épaule gauche" and rig.joint_fr("coude", "right") == "Coude droit"
    assert rig.joint_fr("avant-bras", "right") == "Radio-ulnaires droites"


def test_fit_sphere():
    rng = np.random.default_rng(0)
    d = rng.normal(size=(200, 3))
    d = d[d[:, 1] > 0]  # a cap only, as on a femoral head
    p = [0.1, 0.8, 0.05] + 0.023 * d / np.linalg.norm(d, axis=1, keepdims=True)
    c, r = rig.fit_sphere(p)
    assert np.allclose(c, [0.1, 0.8, 0.05], atol=1e-9) and abs(r - 0.023) < 1e-9


def test_orient_limits_the_tilt():
    x = np.array([1.0, 0, 0])
    a = rig._orient([-1, 1, 0], x)
    assert np.allclose(a, np.array([1, -1, 0]) / np.sqrt(2))
    b = rig._orient([-1, 1, 0], x, 12)
    assert abs(np.degrees(np.arccos(b @ x)) - 12) < 1e-9 and b[1] < 0 and abs(np.linalg.norm(b) - 1) < 1e-12


def test_quaternions():
    q = rig.quat([0, 0, 1], [90])
    assert np.allclose(rig.qrot(q[0], np.array([[1.0, 0, 0]])), [[0, 1, 0]])
    two = rig.qmul(q, q)
    assert np.allclose(rig.qrot(two[0], np.array([[1.0, 0, 0]])), [[-1, 0, 0]])


def _arm_rig():
    items, marks = arm()
    entries, positions, n = [], [], 0
    for x in items:
        v = np.asarray(x["mesh"].vertices) @ BP3D_TO_GLTF.T * 0.001
        entries.append({"id": x["id"], "en": x["en"], "vertices": [n, len(v)]})
        positions.append(v)
        n += len(v)
    return rig.build_rig(entries, np.concatenate(positions), marks)


def test_rig_of_an_arm():
    r = _arm_rig()
    names = [j["name"] for j in r["joints"]]
    assert names == ["squelette", "ceinture-d", "epaule-d", "coude-d", "avant-bras-d", "poignet-d"]
    by = {j["name"]: j for j in r["joints"]}
    assert by["coude-d"]["parent"] == names.index("epaule-d") and by["squelette"]["parent"] is None
    # The shoulder turns about the centre of the humeral head, the elbow about the capitulum's.
    assert np.allclose(by["epaule-d"]["pivot"], HEAD, atol=1e-3)
    assert np.allclose(by["coude-d"]["pivot"], ELBOW, atol=1e-3)
    assert np.allclose(by["ceinture-d"]["pivot"], SC)
    # The finger and the lunate go with the wrist.
    assert by["poignet-d"]["structures"] == ["FMA105", "FMA106"]
    # Only the movements of the limb, and the abduction of one shoulder is named so.
    anims = {a["key"]: a for a in r["animations"]}
    assert set(anims) == {"flexion-coude", "pronation-supination", "flexion-extension-poignet", "abduction-epaule",
                          "flexion-epaule"}
    assert anims["abduction-epaule"]["fr"] == "Abduction de l'épaule" and anims["abduction-epaule"]["side"] == "right"


def _at_peak(r, key, joint, point):
    a = next(a for a in r["animations"] if a["key"] == key)
    i = [j["name"] for j in r["joints"]].index(joint)
    world = rig.pose(r, rig.animation_pose(r, a, a["duration"] / 2))
    return rig.posed_points(r, world, i, [point])[0] - point


def test_movement_directions():
    r = _arm_rig()
    # Elbow flexion brings the wrist forwards and up.
    d = _at_peak(r, "flexion-coude", "poignet-d", WRIST)
    assert d[1] > 0.3 and d[2] > 0
    # Shoulder flexion takes the elbow forwards and up, without swinging it sideways.
    d = _at_peak(r, "flexion-epaule", "coude-d", ELBOW)
    assert d[1] > 0.3 and abs(d[0]) < 0.01
    # Abduction of the right shoulder: up and out to the subject's right (-X) at first, then up.
    a = next(a for a in r["animations"] if a["key"] == "abduction-epaule")
    i = [j["name"] for j in r["joints"]].index("coude-d")
    early = rig.posed_points(r, rig.pose(r, rig.animation_pose(r, a, 0.15 * a["duration"])), i, [ELBOW])[0]
    assert early[0] < ELBOW[0] - 0.05
    assert _at_peak(r, "abduction-epaule", "coude-d", ELBOW)[1] > 0.4
    # Wrist flexion (palm forwards in the anatomical position) takes the fingers forwards.
    finger = WRIST - [0, 0.1, 0]
    assert _at_peak(r, "flexion-extension-poignet", "poignet-d", finger)[2] > 0.03


def test_movements_start_and_end_at_rest():
    r = _arm_rig()
    for a in r["animations"]:
        for t in (0, a["duration"]):
            world = rig.pose(r, rig.animation_pose(r, a, t))
            for (q, tr), j in zip(world, r["joints"]):
                assert np.allclose(q, [0, 0, 0, 1]) and np.allclose(tr, j["pivot"]), (a["key"], t)


def test_unbound_bone_fails():
    with pytest.raises(rig.RigError, match="stapes"):
        rig.build_rig([{"id": "x", "en": "stapes", "vertices": [0, 10]}], np.zeros((10, 3)), [])


def test_skinned_glb(tmp_path):
    m = built(tmp_path)
    check.check(str(tmp_path / "x.json"))
    assert [j["name"] for j in m["rig"]["joints"]][:2] == ["squelette", "ceinture-d"]
    assert m["rig"]["movements"][0] == {"key": "flexion-coude", "fr": "Flexion du coude", "side": "right",
                                        "plane": "sagittal", "duration": 4.0, "joints": ["coude-d"]}
    gltf, nodes = read_glb(str(tmp_path / "x.glb"))
    # The system nodes come first and keep their names; the joints follow, under one root in the scene.
    assert [n["name"] for n in gltf["nodes"][:1]] == ["os"] and gltf["nodes"][0]["skin"] == 0
    assert gltf["scenes"][0]["nodes"] == [0, 1]
    assert gltf["nodes"][1]["name"] == "squelette" and "mesh" not in gltf["nodes"][1]
    assert set(nodes) == {"os"}
    assert nodes["os"]["JOINTS_0"].dtype == np.uint8 and nodes["os"]["WEIGHTS_0"].max() == 1
    # Readers that know nothing of skins still see the meshes.
    scene = trimesh.load(str(tmp_path / "x.glb"))
    assert sorted(scene.geometry) == ["os"]
    manifest = json.load(open(tmp_path / "x.json"))
    assert manifest["rig"]["joints"][2]["parent"] == "ceinture-d"


def test_check_catches_a_bone_bound_elsewhere(tmp_path):
    built(tmp_path)
    m = json.load(open(tmp_path / "x.json"))
    joints = m["rig"]["joints"]
    joints[3]["structures"], joints[2]["structures"] = joints[2]["structures"], joints[3]["structures"]
    json.dump(m, open(tmp_path / "x.json", "w"))
    with pytest.raises(AssertionError):
        check.check(str(tmp_path / "x.json"))


def test_no_rig_without_known_bones(tmp_path):
    items, marks = arm()
    for x in items:
        x["system"] = "muscles"
    m = built(tmp_path, items, marks)
    assert "rig" not in m
    gltf, _ = read_glb(str(tmp_path / "x.glb"))
    assert "skins" not in gltf and "animations" not in gltf
