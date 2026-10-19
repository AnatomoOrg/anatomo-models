"""Z-Anatomy sinuses and nerves of the whole body: whitelist, names, ids, tubes, trimming, .blend reader, licence."""
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
from anatomo_models import open3d_full_body as fb, zanatomy as za  # noqa: E402
from anatomo_models.blend import Blend, tube  # noqa: E402

BLEND = os.environ.get("ZANATOMY_BLEND")  # path to Startup.blend, for the tests that read it


def test_whitelist_has_no_object_of_uncertain_provenance():
    for name in list(za.OBJECTS) + list(za.BONES):
        assert not za.EXCLUDED.search(name), name
    # The facial and vestibulocochlear nerves run where the non-commercial inner-ear model has them.
    for name in ("Facial nerve (VII).r", "Chorda tympani.l", "Vestibulocochlear nerve (VIII).r", "Cochlear nerve",
                 "Vestibular nerve.l", "Cochlea.r", "Kidney.l", "Renal pyramids", "White matter of spinal cord",
                 "Nucleus of abducens nerve.l", "Optic tract.r"):
        assert za.EXCLUDED.search(name), name
        with pytest.raises(ValueError):
            za.read(None, name)
    assert za.MESHES <= set(za.OBJECTS)


def test_concepts_names_and_sides():
    concepts = za.concepts()  # asserts that objects sharing an id agree on its names
    assert len(za.OBJECTS) == 63 and len(concepts) == 61
    for fid, (en, fr, sys_, objs) in concepts.items():
        assert re.fullmatch(r"FMA\d+(-L)?", fid), fid
        assert sys_ in ("veines", "nerfs") and en == en.lower() and fr.strip() and not fr[0].islower(), fid
        # No side in French names (docs/NOMS.md); "Sinus droit" is the straight sinus.
        assert fr == "Sinus droit" or not re.search(r"\b(droite?|gauche)\b", fr), fid
        for o in objs:
            side = {".r": "right", ".l": "left"}.get(o[-2:])
            if side:
                assert re.search(rf"\b{side}\b", en) and not re.search(rf"\b{'left' if side == 'right' else 'right'}\b",
                                                                     en), (o, en)
            else:
                assert not re.search(r"\b(right|left)\b", en), (o, en)
        if fid.endswith("-L"):  # left side of a set: the right side has the FMA id of the set
            assert fid.removesuffix("-L") in concepts and re.search(r"\bleft\b", en), fid
    for fid, name in [("FMA50767", "superior sagittal sinus"), ("FMA50769", "straight sinus"),
                      ("FMA50764", "right transverse sinus"), ("FMA51294", "left sigmoid sinus"),
                      ("FMA51402", "right cavernous sinus"), ("FMA6219", "right vagus nerve"),
                      ("FMA50901", "right hypoglossal nerve"), ("FMA50886", "right abducens nerve")]:
        assert concepts[fid][0] == name
    # A right concept and its left twin have the same English name but the side.
    by_en = {en: fid for fid, (en, *_) in concepts.items()}
    for en, fid in by_en.items():
        if re.search(r"\bright\b", en):
            assert re.sub(r"\bright\b", "left", en) in by_en, en


def test_ids_new_or_merged():
    """New ids clash with nothing already in the model; ids of MERGE are those already there."""
    fr = json.load(open(os.path.join(ROOT, "data", "fr_names.json"), encoding="utf-8"))
    o3d = {fb.sided(fid, en, side)[0] for _, _, table, _ in fb.LIMBS
           for fid, (en, _, _) in fb.concepts(table).items() for side in ("right", "left")}
    existing = set(fr) | o3d
    ids = set(za.concepts())
    assert za.MERGE <= ids and za.MERGE <= existing
    assert not (ids - za.MERGE) & existing
    assert {f for t in za.TRIM.values() for f in t} | set(za.BRIDGE_TO.values()) <= existing
    assert set(za.TRIM) | set(za.BRIDGE_TO) | set(za.BRIDGE) | set(za.BRIDGE.values()) <= set(za.OBJECTS)
    assert za.PARENT_FIX <= set(za.OBJECTS) and set(za.CLIP_BELOW) <= set(za.OBJECTS)


def test_bones_are_whole_body_structures():
    fr = json.load(open(os.path.join(ROOT, "data", "fr_names.json"), encoding="utf-8"))
    assert set(za.BONES.values()) <= set(fr) and len(set(za.BONES.values())) == len(za.BONES)


def test_tube_is_closed_and_round():
    t = np.linspace(0, 1, 30)
    pts = np.stack([np.cos(t * 3), np.sin(t * 3), t * 2], 1) * 10
    v, f = tube(pts, np.full(len(pts), 1.5), sides=8)
    m = trimesh.Trimesh(v, f)
    assert m.is_watertight and m.volume > 0
    d = np.linalg.norm(v[:-2].reshape(len(pts), 8, 3) - pts[:, None], axis=2)
    assert np.allclose(d, 1.5)


def test_resample_and_sides():
    p = np.array([[0, 0, 0], [10, 0, 0], [10, 5, 0]], float)
    q, r = za.resample(p, np.array([1.0, 2.0, 3.0]), 1.5)
    assert np.allclose(q[0], p[0]) and np.allclose(q[-1], p[-1])
    assert np.linalg.norm(np.diff(q, axis=0), axis=1).max() <= 1.5 + 1e-9
    assert r[0] == 1 and r[-1] == 3
    assert za.sides(0.3) == 6 and za.sides(1) == 8 and za.sides(4) == 12


def test_runs_outside_drops_the_part_touching_and_overlaps_it():
    box = trimesh.creation.box(extents=[20, 20, 20])  # -10..10
    p = np.stack([np.linspace(-30, 30, 61), np.zeros(61), np.zeros(61)], 1)
    runs = za.runs_outside(p, np.full(61, 1.0), [box])
    assert len(runs) == 2
    (a, _), (b, _) = runs
    # Points whose tube touches the box are dropped; each run reaches one point further, into the box.
    assert a[-2, 0] == -11 and a[-1, 0] == -10 and b[0, 0] == 10 and b[1, 0] == 11
    (a, _), (b, _) = za.runs_outside(p, np.full(61, 5.0), [box])
    assert a[-2, 0] == -15 and b[1, 0] == 15


def test_bridge_extends_the_nearest_end():
    a = [(np.array([[0, 0, 0], [0, 0, 10.0]]), np.array([1.0, 2.0]))]
    other = [(np.array([[5, 0, 30], [0, 0, 13.0]]), np.array([1.0, 1.0]))]
    (p, r), = za.bridge(a, other)
    assert np.allclose(p[-1], [0, 0, 13]) and len(p) == 3 and r[-1] == 2


def test_runs_cut_where_asked():
    p = np.stack([np.zeros(10), np.zeros(10), np.arange(10.0)], 1)
    (q, r), = za.runs(p, np.ones(10), p[:, 2] >= 4)
    assert q[0, 2] == 3 and q[-1, 2] == 9


def test_licence_and_attribution():
    m = build_script.MODELS["full_body"]
    assert m["license"]["id"] == "CC-BY-SA-4.0"
    assert za.SOURCE in m["sources"] and za.SOURCE["license"] == "CC-BY-SA-4.0"
    assert za.COMMIT in za.SOURCE["url"]
    assert "Z-Anatomy - The libre 3D atlas of anatomy - CC-BY-SA 4.0" in m["attribution"]
    assert "Open3DModel - Lower limb" in m["attribution"] and "BodyParts3D" in m["attribution"]
    assert "Z-Anatomy" not in build_script.MODELS["upper_limb"]["attribution"].split("derived from")[0]
    pin = open(os.path.join(ROOT, "pipeline", "zanatomy.sha256")).read().split()
    assert len(pin) == 2 and re.fullmatch(r"[0-9a-f]{64}", pin[0]) and pin[1] == f"{za.COMMIT}/Z-Anatomy.zip"


@pytest.mark.skipif(not BLEND, reason="set ZANATOMY_BLEND to Z-Anatomy's Startup.blend")
def test_blend_objects_and_geometry():
    b = Blend(BLEND)
    try:
        objs = b.objects()
        assert set(za.OBJECTS) | set(za.BONES) <= set(objs)
        kind, v, f = za.read(b, "Frontal bone")
        m = trimesh.Trimesh(v, f)
        assert kind == "mesh" and len(f) > 5000 and 0.1 < m.extents.max() < 0.2  # metres
        kind, splines = za.read(b, "Superior sagittal sinus")
        assert kind == "curve" and len(splines) == 1
        p, r = splines[0]
        assert 0.3 < np.linalg.norm(np.diff(p, axis=0), axis=1).sum() < 0.4 and 0 < r.max() < 0.005
        kind, v, f = za.read(b, "Cavernous sinus.r")
        assert kind == "mesh" and v[:, 0].mean() < 0  # subject's right at negative x
    finally:
        b.close()
