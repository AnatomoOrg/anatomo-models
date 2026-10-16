import os
import re
import sys

import numpy as np
import trimesh

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pipeline"))
from anatomo_models import landmarks as L  # noqa: E402
from anatomo_models.landmark_catalog import CATALOGUE  # noqa: E402
from anatomo_models.model import to_gltf  # noqa: E402


def box(center, extents):
    """Box in the BodyParts3D frame (mm): +x subject's left, -y anterior, +z superior."""
    b = trimesh.creation.box(extents=extents)
    b.apply_translation(center)
    return b


def ellipsoid(center, radii):
    e = trimesh.creation.icosphere(subdivisions=3)
    e.apply_scale(radii)
    e.apply_translation(center)
    return e


def pair(name, center, extents, shape=box):
    """A right/left pair of structures, mirror images of each other (the right one at negative x)."""
    cx, cy, cz = center
    return [dict(id=f"R{name}", en=f"right {name}", mesh=shape((-cx, cy, cz), extents)),
            dict(id=f"L{name}", en=f"left {name}", mesh=shape((cx, cy, cz), extents))]


def test_parse_and_vec():
    assert np.allclose(L.parse("lat+.5sup"), [-1, 0.5, 0])
    assert np.allclose(L.parse("20sup-10ant"), [0, 20, -10])
    assert np.isclose(np.linalg.norm(L.vec("lat+post")), 1)


def test_closest_on_triangles_matches_dense_sampling():
    rng = np.random.default_rng(0)
    tris = rng.normal(size=(30, 3, 3))
    for q in rng.normal(size=(20, 3)) * 2:
        pts = L.closest_on_triangles(q, tris)
        p = pts[np.argmin(np.linalg.norm(pts - q, axis=1))]
        # Dense barycentric sampling of every triangle never gets closer than the exact answer.
        u, v = np.meshgrid(np.linspace(0, 1, 60), np.linspace(0, 1, 60))
        keep = (u + v) <= 1
        u, v = u[keep], v[keep]
        pts = tris[:, 0, None] + (tris[:, 1] - tris[:, 0])[:, None] * u[:, None] + (tris[:, 2] - tris[:, 0])[:, None] * v[:, None]
        best = np.linalg.norm(pts.reshape(-1, 3) - q, axis=1).min()
        assert np.linalg.norm(p - q) <= best + 1e-9
        assert np.linalg.norm(p - q) > best - 0.1


def test_extreme_rule_and_offset():
    # An ellipsoid 40 mm tall: the superior extreme is its top, 1.5 mm above the surface.
    items = pair("bone", (50, 0, 100), (5, 5, 20), ellipsoid)
    cat = [L.B("{side} bone", "os", ("haut", "Haut", "saillie", L.X("sup")), ("lateral", "Latéral", "saillie", L.X("lat")))]
    out, failed = L.place(items, cat)
    assert not failed and len(out) == 4
    top = next(x for x in out if x["id"] == "os.haut" and x["side"] == "right")
    assert np.isclose(top["position"][1], 0.120 + L.OFFSET, atol=1e-6)
    lat_r = next(x for x in out if x["id"] == "os.lateral" and x["side"] == "right")["position"]
    lat_l = next(x for x in out if x["id"] == "os.lateral" and x["side"] == "left")["position"]
    # Lateral is away from the midline on both sides: the left landmark mirrors the right one.
    assert np.isclose(lat_r[0], -0.055 - L.OFFSET) and np.allclose(lat_l, [-lat_r[0], lat_r[1], lat_r[2]])
    assert np.allclose(top["position"][::2], [-0.05, 0], atol=1e-6)


def test_midline_paired_and_single():
    items = [dict(id="M", en="spine", mesh=ellipsoid((0, 0, 0), (20, 10, 10)))]
    cat = [L.B("spine", "s", ("avant", "Avant", "saillie", L.X("ant"))),
           L.B("spine", "s", ("cote", "Côté", "saillie", L.X("lat")), paired=True)]
    out, _ = L.place(items, cat)
    sides = {(x["id"], x["side"]): x["position"] for x in out}
    assert set(sides) == {("s.avant", None), ("s.cote", "right"), ("s.cote", "left")}
    assert sides[("s.cote", "right")][0] < 0 < sides[("s.cote", "left")][0]
    assert sides[("s.avant", None)][2] > 0.01  # anterior is +Z in the glTF frame


def test_attachment_on_touching_bone_and_skip_when_short():
    # Muscle from z=0 to 100 mm; its top touches a bone above, its bottom stops 30 mm short of another bone.
    items = pair("muscle", (30, 0, 50), (10, 10, 100)) + pair("upper", (30, 0, 110), (20, 20, 20)) \
        + pair("lower", (30, 0, -40), (20, 20, 20))
    cat = [L.M("{side} muscle", "m", ("Haut", "{side} upper", "sup"), ("Bas", "{side} lower", "inf"))]
    out, failed = L.place(items, cat)
    assert not failed
    assert {x["id"] for x in out} == {"m.origine"}  # the insertion is skipped: the muscle does not reach its bone
    for x in out:
        assert x["position"][1] > 0.09  # at the top of the muscle


def test_attachment_falls_back_on_muscle_end_without_target():
    items = pair("muscle", (30, 0, 50), (10, 10, 100))
    cat = [L.M("{side} muscle", "m", ("Haut", [], "sup"), None)]
    out, _ = L.place(items, cat)
    assert len(out) == 2 and all(x["position"][1] > 0.09 for x in out)


def test_landmark_reference_and_missing_structure():
    items = pair("bone", (30, 0, 0), (10, 10, 40)) + pair("vessel", (40, 0, 0), (4, 4, 60))
    cat = [L.B("{side} bone", "os", ("haut", "Haut", "saillie", L.X("sup"))),
           L.B("{side} vessel", "v", ("pouls", "Pouls", "pouls", L.N("@os.haut"))),
           L.B("{side} absent", "a", ("x", "X", "saillie", L.X("sup"))),
           L.B("{side} vessel", "v", ("y", "Y", "clinique", L.N("{side} absent")))]
    out, failed = L.place(items, cat)
    assert not failed
    assert sorted({x["id"] for x in out}) == ["os.haut", "v.pouls"]
    assert L.unresolved([x["en"] for x in items], cat) == ["{side} absent"]


def test_empty_band_is_reported():
    items = pair("bone", (30, 0, 0), (10, 10, 40))
    cat = [L.B("{side} bone", "os", ("x", "X", "saillie", L.F("post", sup=(0.4, 0.41), med=(0.99, 1))))]
    out, failed = L.place(items, cat)
    assert not out and len(failed) == 2


def test_humerus_rule_converts_frames(monkeypatch):
    # humerus() works in the BodyParts3D frame (m): its result comes back in the glTF frame.
    m = ellipsoid((-170, 0, 1100), (12, 12, 150))
    seen = {}

    def fake(V, N):
        seen["V"] = V
        return [("tete", "Tête", "articulaire", V[np.argmax(V[:, 2])])]
    monkeypatch.setattr(L, "humerus", fake)
    p = L._part("FMA23130", m, None)
    got = L.humerus_rule("tete")(L.World({"right humerus": p}, "right"), p)
    assert np.allclose(seen["V"], m.vertices * 0.001)
    assert np.allclose(got, to_gltf(m.vertices[np.argmax(m.vertices[:, 2])]))


def test_catalogue_is_consistent():
    seen = []
    for e in CATALOGUE:
        for slug, fr, kind, rule in e.marks:
            lid = f"{e.prefix}.{slug}"
            key = (lid, e.name)
            assert key not in seen, key
            seen.append(key)
            assert fr.strip() and fr[0].isupper(), lid
    # Ids are stable keys: lower-case ascii slugs.
    assert all(re.fullmatch(r"[a-z0-9-]+\.[a-z0-9-]+", lid) for lid, _ in seen)
    # One id per structure kind of landmark (an id never names two different structures).
    names = {}
    for lid, name in seen:
        assert names.setdefault(lid, name) == name, lid


def test_references_point_to_earlier_landmarks():
    placed = set()
    for e in CATALOGUE:
        for slug, fr, kind, rule in e.marks:
            for ref in getattr(rule, "refs", ()):
                assert ref in placed, (e.prefix, slug, ref)
            placed.add(f"{e.prefix}.{slug}")


def test_build_and_check_landmarks(tmp_path):
    import json

    import check
    from anatomo_models.model import build
    from build import write_landmarks
    items = [dict(x, fr=None, system="os", source="t") for x in pair("bone", (50, 0, 100), (5, 5, 20), ellipsoid)]
    m = build(items, str(tmp_path / "x.glb"), str(tmp_path / "x.json"), "x", "0.0.0", [])
    marks, _ = L.place(items, [L.B("{side} bone", "os", ("haut", "Haut", "saillie", L.X("sup")))])
    write_landmarks(m, marks, str(tmp_path / "x.landmarks.json"))
    check.check(str(tmp_path / "x.json"))
    # A landmark on the wrong side of a paired structure is caught.
    lm = json.load(open(tmp_path / "x.landmarks.json"))
    lm["landmarks"][0]["side"] = "left"
    json.dump(lm, open(tmp_path / "x.landmarks.json", "w"))
    try:
        check.check(str(tmp_path / "x.json"))
    except AssertionError:
        return
    raise AssertionError("wrong side not detected")
