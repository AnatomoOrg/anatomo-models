import os
import sys

import numpy as np
import trimesh

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pipeline"))
import check  # noqa: E402
from anatomo_models import fibers  # noqa: E402
from anatomo_models.glb import read_glb  # noqa: E402
from anatomo_models.model import build, normals  # noqa: E402
from test_pipeline import sample  # noqa: E402


def fusiform(length=0.2, belly=0.015, tendon=0.0015, tendon_len=0.04):
    """A muscle along Z (m): a thick belly between two thin tendons, as a closed surface of revolution."""
    z = np.linspace(0, length, 120)
    belly_z = np.clip((z - tendon_len) / (length - 2 * tendon_len), 0, 1)
    r = tendon + (belly - tendon) * np.sin(np.pi * belly_z) ** 1.5
    profile = np.column_stack([np.r_[0, r, 0], np.r_[0, z, length]])
    m = trimesh.creation.revolve(profile, sections=48)
    m.merge_vertices()
    return m


def run(mesh, **kw):
    return fibers.structure_fibers(mesh.vertices, mesh.faces, normals(mesh), **kw)


def test_fusiform_fibres_run_along_the_muscle():
    m = fusiform()
    d, t = run(m)
    assert np.allclose(np.linalg.norm(d, axis=1), 1, atol=1e-6)
    # Tangent to the (smoothed) surface, and along Z on the belly.
    assert np.median(np.abs((d * normals(m)).sum(1))) < 0.02
    z = m.vertices[:, 2]
    belly = (z > 0.07) & (z < 0.13)
    assert np.median(np.abs(d[belly, 2])) > 0.95


def test_tendon_mask_marks_the_thin_ends():
    m = fusiform()
    _, t = run(m)
    z = m.vertices[:, 2]
    assert t[(z > 0.08) & (z < 0.12)].max() < 0.05
    assert np.median(t[(z > 0.003) & (z < 0.025)]) > 0.8
    assert np.median(t[(z > 0.175) & (z < 0.197)]) > 0.8


def test_landmark_ends_steer_the_field():
    # Origin and insertion on the sides of a flat plate: fibres run along X, not along the plate's long axis (Y).
    plate = trimesh.creation.box(extents=(0.06, 0.1, 0.006))
    plate = plate.subdivide_to_size(0.004)
    plate.merge_vertices()
    ends = (np.array([-0.03, 0, 0]), np.array([0.03, 0, 0]))
    d, _ = run(plate, ends=ends)
    top = (plate.vertices[:, 2] > 0.0029) & (np.abs(plate.vertices[:, 1]) < 0.02) & (np.abs(plate.vertices[:, 0]) < 0.02)
    assert np.median(np.abs(d[top, 0])) > 0.9
    d2, _ = run(plate)
    assert np.median(np.abs(d2[top, 1])) > 0.9


def test_tendinous_structures_are_all_tendon():
    m = fusiform()
    _, t = run(m, tendinous=True)
    assert np.all(t == 1)
    assert fibers.TENDINOUS.search("right calcaneal tendon") and fibers.TENDINOUS.search("linea alba")
    assert not fibers.TENDINOUS.search("right biceps brachii")


def test_fibres_roundtrip_in_glb(tmp_path):
    items = sample()
    fibers.annotate(items, [])
    build(items, str(tmp_path / "x.glb"), str(tmp_path / "x.json"), "x", "0.0.0", [])
    check.check(str(tmp_path / "x.json"))
    gltf, nodes = read_glb(str(tmp_path / "x.glb"))
    mus, os_ = nodes["muscles"], nodes["os"]
    assert "_FIBER" not in os_ and "_TENDON" not in os_
    assert mus["_FIBER"].shape == (len(mus["POSITION"]), 3)
    assert np.allclose(np.linalg.norm(mus["_FIBER"], axis=1), 1, atol=0.02)
    # The box 'b' is 20 mm long along BodyParts3D z, glTF Y (its 8 corners have diagonal normals).
    assert np.all(np.argmax(np.abs(mus["_FIBER"]), axis=1) == 1)
    assert mus["_TENDON"].min() >= 0 and mus["_TENDON"].max() <= 1
    accessors = [gltf["accessors"][gltf["meshes"][1]["primitives"][0]["attributes"][k]] for k in ("_FIBER", "_TENDON")]
    assert [(a["componentType"], a["type"], a["normalized"]) for a in accessors] == [(5120, "VEC3", True), (5121, "SCALAR", True)]
