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
    # Shoulder flexion takes the elbow forwards and up (test_shoulder_flexion_stays_sagittal for the plane).
    d = _at_peak(r, "flexion-epaule", "coude-d", ELBOW)
    assert d[1] > 0.3
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


def _fine(mesh, edge=0.004):
    """A mesh with short edges (the cylinders have edges as long as themselves), as the published meshes have."""
    v, f = trimesh.remesh.subdivide_to_size(mesh.vertices, mesh.faces, max_edge=edge)
    return trimesh.Trimesh(v, f)


def test_soft_tissues_follow_the_bones(tmp_path):
    items, marks = arm()
    for x in items:  # distances to the bones are taken to their vertices
        x["mesh"] = _fine(x["mesh"], 4.0)
    mid_arm, mid_forearm = (HEAD + ELBOW) / 2, (ELBOW + WRIST) / 2
    front = np.array([0, 0, 0.02])
    items += [
        dict(id="FMA900", en="right biceps", fr="biceps", system="muscles", source="t",
             mesh=_bp3d(_fine(_rod(mid_arm + front, mid_forearm + front, 0.012)))),
        dict(id="FMA901", en="right median nerve", fr="nerf", system="nerfs", source="t",
             mesh=_bp3d(_fine(_rod(mid_arm - front, mid_forearm - front, 0.003)))),
        dict(id="FMA902", en="integumentary system", fr="peau", system="peau", source="t",
             mesh=_bp3d(_fine(_rod(mid_arm, mid_forearm, 0.04), 0.008))),
        # A trunk muscle from the arm to the chest, whose bones (the thorax) are not in the model.
        dict(id="FMA903", en="right pectoralis major", fr="grand pectoral", system="muscles", source="t",
             mesh=_bp3d(_fine(_rod(HEAD + [0.0, -0.07, 0.022], SC + [0.02, -0.12, 0.03], 0.01)))),
    ]
    m = built(tmp_path, items, marks)
    check.check(str(tmp_path / "x.json"))
    assert m["rig"]["skinned"] == ["os", "muscles", "nerfs", "peau"]
    gltf, nodes = read_glb(str(tmp_path / "x.glb"))
    assert all(n.get("skin") == 0 for n in gltf["nodes"] if "mesh" in n)
    names = [j["name"] for j in m["rig"]["joints"]]
    for system in ("muscles", "nerfs", "peau"):
        p, j, w = nodes[system]["POSITION"], nodes[system]["JOINTS_0"], nodes[system]["WEIGHTS_0"]
        top = np.array([names[k] for k in j[:, 0]])
        assert np.allclose(w.sum(1), 1, atol=1e-5)
        limb = np.ones(len(p), bool)  # the structures along the limb, not the trunk muscle
        for st in m["structures"]:
            if st["id"] == "FMA903" and system == "muscles":
                limb[st["vertices"][0]:sum(st["vertices"])] = False
        upper, lower = limb & (p[:, 1] > HEAD[1] - 0.06), limb & (p[:, 1] < WRIST[1] + 0.13)
        assert np.all(top[upper] == "epaule-d") and np.all(w[upper, 0] > 0.9), system
        forearm = np.isin(j, [names.index("coude-d"), names.index("avant-bras-d")])
        assert np.all((w * forearm)[lower].sum(1) > 0.9), system  # the ulna and the radius
        # Around the elbow, the vertices blend the arm and the forearm.
        around = limb & (np.abs(p[:, 1] - ELBOW[1]) < 0.01)
        assert np.any(w[around, 1] > 0.2), system
    # Without the thorax, the chest end of the trunk muscle stays still (the root), its arm end follows the arm.
    pec = next(s for s in m["structures"] if s["id"] == "FMA903")
    v0, n = pec["vertices"]
    p, j, w = (nodes["muscles"][k][v0:v0 + n] for k in ("POSITION", "JOINTS_0", "WEIGHTS_0"))
    chest = p[:, 0] > SC[0] - 0.01
    assert np.all((w * (j == 0))[chest].sum(1) > 0.6)
    arm_end = np.linalg.norm(p - (HEAD + [0.0, -0.07, 0.022]), axis=1) < 0.015
    assert (w * (j == 0))[arm_end].sum(1).mean() < 0.15


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


# A synthetic trunk, head and lower limbs (glTF frame, m), for the directions of the other movements.
KNEE = 0.50
ANKLE = 0.09


def _box(c, extents):
    return trimesh.creation.box(extents=extents).apply_translation(c)


def body():
    """(items for model.build, landmarks): pelvis, spine, skull and mandible, and both lower limbs."""
    shapes, marks = {}, [("c2.dent", None, [0, 1.47, 0.0])]
    shapes["posterior part of pelvis"] = _box([0, 0.97, -0.03], (0.10, 0.10, 0.06))
    # Vertebrae: a body in front (+Z) and an arch behind; L5 lowest, then up to C3, the axis and the atlas.
    spine = [f"{n} lumbar vertebra" for n in reversed(rig.LUMBAR)] + ["twelfth thoracic vertebra"]
    spine += [f"{n} cervical vertebra" for n in reversed(rig.CERVICAL)] + ["axis"]
    y = 1.03
    for en in spine:
        shapes[en] = trimesh.util.concatenate([_rod([0, y - 0.01, 0.0], [0, y + 0.01, 0.0], 0.016),
                                               _box([0, y, -0.035], (0.02, 0.02, 0.04))])
        y += 0.03 if "lumbar" in en or "thoracic" in en else 0.02
    shapes["atlas"] = _box([0, 1.49, -0.005], (0.06, 0.012, 0.04))
    shapes["frontal bone"] = _sphere([0, 1.60, 0.01], 0.08)
    shapes["skeleton of mouth"] = _box([0, 1.48, 0.07], (0.09, 0.03, 0.05))
    marks += [("mandibule.processus-condylaire", s, [x, 1.53, 0.0]) for s, x in (("right", -0.05), ("left", 0.05))]
    for side, sx in (("right", -1), ("left", 1)):
        hip, knee, ankle = (np.array([sx * 0.085, 0.93, 0.02]), np.array([sx * 0.09, KNEE, 0.02]),
                            np.array([sx * 0.09, ANKLE, 0.0]))
        shapes[f"{side} side of bony pelvis"] = _box([sx * 0.11, 1.0, 0.0], (0.04, 0.12, 0.10))
        shapes[f"{side} femur"] = trimesh.util.concatenate([_sphere(hip, 0.023), _rod(hip, knee + [0, 0.03, 0], 0.012),
                                                            _sphere(knee, 0.025)])
        shapes[f"{side} tibia"] = _rod(knee - [0, 0.03, 0], ankle + [0, 0.01, 0], 0.012)
        shapes[f"{side} fibula"] = _rod(knee + [sx * -0.03, -0.04, -0.01], ankle + [sx * -0.03, 0.01, 0], 0.006)
        shapes[f"{side} patella"] = _sphere(knee + [0, 0.015, 0.0335], 0.01)
        shapes[f"{side} talus"] = _sphere(ankle - [0, 0.02, 0], 0.015)
        shapes[f"{side} calcaneus"] = _box(ankle + [0, -0.06, -0.03], (0.04, 0.05, 0.06))
        shapes[f"first metatarsal bone of {side} foot"] = _rod(ankle + [0, -0.05, 0.02], ankle + [0, -0.08, 0.14], 0.008)
        marks += [("femur.tete", side, hip + [sx * 0.023, 0, 0]),
                  ("femur.epicondyle-lateral", side, knee + [sx * 0.04, 0, 0]),
                  ("femur.epicondyle-medial", side, knee - [sx * 0.04, 0, 0]),
                  ("tibia.tuberosite", side, knee + [0, -0.06, 0.02]),
                  ("patella.apex", side, knee + [0, 0.005, 0.045]),
                  ("fibula.malleole-laterale", side, ankle + [sx * 0.03, -0.01, 0]),
                  ("tibia.malleole-mediale", side, ankle - [sx * 0.025, 0, 0])]
    items = [dict(id=f"FMA{200 + i}", en=en, fr=en, system="os", mesh=_bp3d(m), source="t")
             for i, (en, m) in enumerate(shapes.items())]
    return items, [{"id": i, "side": s, "position": np.asarray(p, float).tolist()} for i, s, p in marks]


def _rig_of(items, marks):
    entries, positions, n = [], [], 0
    for x in items:
        v = np.asarray(x["mesh"].vertices) @ BP3D_TO_GLTF.T * 0.001
        entries.append({"id": x["id"], "en": x["en"], "vertices": [n, len(v)]})
        positions.append(v)
        n += len(v)
    return rig.build_rig(entries, np.concatenate(positions), marks)


def _moved(r, key, joint, point, fraction):
    a = next(a for a in r["animations"] if a["key"] == key)
    i = [j["name"] for j in r["joints"]].index(joint)
    world = rig.pose(r, rig.animation_pose(r, a, fraction * a["duration"]))
    return rig.posed_points(r, world, i, [point])[0] - point


@pytest.fixture(scope="module")
def body_rig():
    return _rig_of(*body())


def test_rig_of_a_body(body_rig):
    names = [j["name"] for j in body_rig["joints"]]
    assert names[:9] == ["squelette", "bassin", "lombaire-5", "lombaire-4", "lombaire-3", "lombaire-2", "lombaire-1",
                         "thorax", "cervicale-7"]
    assert {"atlas", "tete", "mandibule", "hanche-d", "genou-g", "patella-d", "cheville-g"} <= set(names)
    assert {a["key"] for a in body_rig["animations"]} == {
        "flexion-hanche", "abduction-hanche", "flexion-genou", "flexion-cheville", "flexion-extension-tronc",
        "inclinaison-tronc", "flexion-extension-tete", "rotation-tete", "ouverture-bouche", "marche"}


def test_lower_limb_directions(body_rig):
    r, ankle, knee = body_rig, np.array([-0.09, ANKLE, 0.0]), np.array([-0.09, KNEE, 0.02])
    # Knee flexion takes the ankle backwards and up.
    d = _moved(r, "flexion-genou", "cheville-d", ankle, 0.5)
    assert d[2] < -0.3 and d[1] > 0.3
    # Hip flexion takes the knee forwards and up.
    d = _moved(r, "flexion-hanche", "genou-d", knee, 0.5)
    assert d[2] > 0.3 and d[1] > 0.3
    # Abduction of the right hip: the knee goes out to the subject's right (-X).
    assert _moved(r, "abduction-hanche", "genou-d", knee, 0.5)[0] < -0.2
    # Dorsiflexion first brings the toes up, plantar flexion then down.
    toe = ankle + [0, -0.08, 0.14]
    assert _moved(r, "flexion-cheville", "cheville-d", toe, 0.3)[1] > 0.03
    assert _moved(r, "flexion-cheville", "cheville-d", toe, 0.75)[1] < -0.05


def test_spine_and_head_directions(body_rig):
    r, vertex, chin = body_rig, np.array([0, 1.68, 0.01]), np.array([0, 1.465, 0.095])
    # Trunk flexion takes the head forwards and down, extension backwards.
    d = _moved(r, "flexion-extension-tronc", "tete", vertex, 0.35)
    assert d[2] > 0.2 and d[1] < -0.05
    assert _moved(r, "flexion-extension-tronc", "tete", vertex, 0.75)[2] < -0.05
    # Lateral flexion to the right (-X) first, then to the left.
    assert _moved(r, "inclinaison-tronc", "tete", vertex, 0.3)[0] < -0.1
    assert _moved(r, "inclinaison-tronc", "tete", vertex, 0.7)[0] > 0.1
    # Head flexion: the top of the head forwards, the chin down; then extension: the top of the head backwards.
    d = _moved(r, "flexion-extension-tete", "tete", vertex, 0.35)
    assert d[2] > 0.05 and _moved(r, "flexion-extension-tete", "tete", chin, 0.35)[1] < -0.01
    assert _moved(r, "flexion-extension-tete", "tete", vertex, 0.75)[2] < -0.05
    # Rotation: the face turns to the subject's left (+X), then to the right.
    nose = np.array([0, 1.58, 0.09])
    assert _moved(r, "rotation-tete", "tete", nose, 0.3)[0] > 0.04
    assert _moved(r, "rotation-tete", "tete", nose, 0.7)[0] < -0.04
    # Opening the mouth takes the chin down.
    assert _moved(r, "ouverture-bouche", "mandibule", chin, 0.5)[1] < -0.02


def test_patella_stays_on_the_femur(body_rig):
    m = body_rig["measures"]
    for side in ("right", "left"):
        rest = m[f"patella {side}: gap to the femur at rest (mm)"]
        assert m[f"patella {side}: widest gap to the femur, 0-140 deg (mm)"] < max(rest, 1.5) + 1
        assert m[f"patella {side}: widest gap to the femur at the animation keys (mm)"] < max(rest, 1.5) + 1
    # The patella turns with the knee and is held by its ligament: its apex follows the tibial tuberosity.
    a = next(a for a in body_rig["animations"] if a["key"] == "flexion-genou")
    assert {"genou-d", "patella-d"} <= set(a["joints"])


def test_walk_keeps_the_feet_on_the_ground(body_rig):
    m = body_rig["measures"]
    assert m["marche: deepest foot point below the ground (mm)"] < 1
    assert m["marche: highest lowest foot point above the ground (mm)"] < 3


def test_shoulder_flexion_stays_sagittal():
    r = _arm_rig()
    # The humerus stays in the sagittal plane: the elbow keeps its side offset from the head of the humerus (the
    # girdle moves the shoulder itself a little sideways).
    for f in (0.1, 0.2, 0.3, 0.5):
        arm = ELBOW + _moved(r, "flexion-epaule", "coude-d", ELBOW, f) - HEAD - _moved(r, "flexion-epaule", "epaule-d", HEAD, f)
        assert abs(arm[0] - (ELBOW - HEAD)[0]) < 0.002, f
    # The arm rises above the horizontal (150 degrees in all) while the girdle lifts the shoulder.
    assert _moved(r, "flexion-epaule", "coude-d", ELBOW, 0.5)[1] > 0.4
    assert _moved(r, "flexion-epaule", "epaule-d", HEAD, 0.5)[1] > 0.02


@pytest.mark.parametrize("drop", ["left femur", ("femur.tete", "left")])
def test_no_rig_when_a_bone_or_landmark_is_missing(drop, capsys):
    items, marks = body()
    if isinstance(drop, str):
        items = [x for x in items if x["en"] != drop]
    else:
        marks = [x for x in marks if (x["id"], x["side"]) != drop]
    assert _rig_of(items, marks) is None
    assert "rig: none (missing" in capsys.readouterr().out


def test_check_needs_the_rig_section_of_a_skinned_glb(tmp_path):
    built(tmp_path)
    m = json.load(open(tmp_path / "x.json"))
    del m["rig"]
    json.dump(m, open(tmp_path / "x.json", "w"))
    with pytest.raises(AssertionError, match="no rig section"):
        check.check(str(tmp_path / "x.json"))


def test_check_catches_a_pivot_off_its_node(tmp_path):
    built(tmp_path)
    m = json.load(open(tmp_path / "x.json"))
    m["rig"]["joints"][3]["pivot"][1] += 0.01
    json.dump(m, open(tmp_path / "x.json", "w"))
    with pytest.raises(AssertionError, match="do not add up"):
        check.check(str(tmp_path / "x.json"))
