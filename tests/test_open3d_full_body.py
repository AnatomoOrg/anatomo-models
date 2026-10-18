"""Open3DModel nerves of both limbs and both sides in the whole-body model: tables, sides, skin, licence."""
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
from anatomo_models import open3d, open3d_full_body as fb, open3d_lower, skin  # noqa: E402
from anatomo_models.model import build  # noqa: E402


def all_sided():
    """[(right id, right en, left id, left en, fr)] of every concept of both limbs."""
    out = []
    for _, _, table, _ in fb.LIMBS:
        for fid, (en, fr, _) in sorted(fb.concepts(table).items()):
            out.append((*fb.sided(fid, en, "right"), *fb.sided(fid, en, "left"), fr))
    return out


def test_lower_nerve_table():
    concepts = fb.concepts(open3d_lower.NERVES)
    assert len(open3d_lower.NERVES) == 65 and len(concepts) == 62
    assert all(re.fullmatch(r"FMA\d+", fid) for fid in concepts)
    assert len({en for en, _, _ in concepts.values()}) == len({fr for _, fr, _ in concepts.values()}) == len(concepts)
    for fid, (en, fr, _) in concepts.items():
        assert en == en.lower() and fr.strip() and not fr[0].islower(), fid
        assert not re.search(r"\b(droite?|gauche)\b", fr), fid  # no side in French names (docs/NOMS.md)
    for fid, name in [("FMA22111", "right sciatic nerve"), ("FMA16499", "right femoral nerve"),
                      ("FMA16501", "right obturator nerve"), ("FMA22109", "right tibial nerve"),
                      ("FMA45357", "right common fibular nerve"), ("FMA20674", "right lumbar nerve plexus"),
                      ("FMA63660", "right sacral nerve plexus"), ("FMA21863", "right pudendal nerve")]:
        assert concepts[fid][0] == name


def test_both_sides_have_distinct_ids_and_sided_english_names():
    rows = all_sided()
    assert len(rows) == 48 + 62
    ids = [r[0] for r in rows] + [r[2] for r in rows]
    assert len(ids) == len(set(ids)) == 220
    for rid, ren, lid, len_, fr in rows:
        assert re.search(r"\bright\b", ren) and not re.search(r"\bleft\b", ren), ren
        assert re.search(r"\bleft\b", len_) and not re.search(r"\bright\b", len_), len_
        assert len_ == re.sub(r"\bright\b", "left", ren)  # the app pairs a left structure with its right twin
        assert re.fullmatch(r"FMA\d+", rid) and re.fullmatch(r"FMA\d+(-L)?", lid)
        assert lid.endswith("-L") == (rid in fb.SIDED) and (lid == f"{rid}-L") == (rid in fb.SIDED)
    # Upper limb: the right side keeps the ids of the upper_limb model.
    assert {r[0] for r in rows[:48]} == set(open3d.concepts())


def test_left_tables_are_consistent():
    rights = {fid for _, _, t, _ in fb.LIMBS for fid in fb.concepts(t)}
    assert set(fb.LEFT) | set(fb.SIDED) == rights and not set(fb.LEFT) & set(fb.SIDED)
    assert len(set(fb.LEFT.values())) == len(fb.LEFT) and not set(fb.LEFT.values()) & rights
    for _, _, _, bones in fb.LIMBS:
        for fid in bones.values():
            assert fid in fb.LEFT_BONES or fid in {"FMA13072", "FMA13073", "FMA13074", "FMA13075", "FMA13076",
                                                  "FMA24228"}, fid  # median bones are their own counterpart


def test_ids_do_not_clash_with_bodyparts3d_structures():
    fr = json.load(open(os.path.join(ROOT, "data", "fr_names.json"), encoding="utf-8"))
    rows = all_sided()
    assert not ({r[0] for r in rows} | {r[2] for r in rows}) & set(fr)


def test_mirror_keeps_outward_normals():
    m = trimesh.creation.icosphere(subdivisions=1)
    m.apply_translation([0.3, 0, 0])
    w = fb.mirror(m)
    assert np.allclose(w.vertices[:, 0], -m.vertices[:, 0]) and w.volume > 0 and np.isclose(w.volume, m.volume)


def shell(radius, center):
    """A closed skin shell 2 mm thick: outer sphere, inner sphere turned inside out."""
    outer = trimesh.creation.icosphere(subdivisions=4, radius=radius)
    inner = trimesh.creation.icosphere(subdivisions=4, radius=radius - 2)
    inner.faces = inner.faces[:, ::-1]
    m = trimesh.util.concatenate([outer, inner])
    m.apply_translation(center)
    return m


def test_under_skin_pushes_a_tube_inside(monkeypatch):
    monkeypatch.setattr(skin, "MIN_VOLUME_L", 1.0)
    body = skin.Body(shell(120.0, [0, 0, 0]))
    assert 6.0 < body.volume < 8.5  # sphere of radius 120 mm: 7.2 L
    tube = trimesh.creation.cylinder(radius=1.5, height=60, sections=12)
    tube.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [0, 1, 0]))
    tube.apply_translation([95, 0, 0])  # x from 65 to 125: sticks out by 5 mm
    v, n, most = skin.under_skin(tube.vertices, body, margin=2.5)
    assert n > 0 and 6 < most < 12
    assert body(v).min() >= 2.0
    assert np.allclose(v[tube.vertices[:, 0] < 80], tube.vertices[tube.vertices[:, 0] < 80])  # the deep end stays
    # Cross-sections move as a whole: the end of the tube keeps its shape.
    end = tube.vertices[:, 0] > 120
    d0 = np.linalg.norm(tube.vertices[end][:, None] - tube.vertices[end][None], axis=2)
    d1 = np.linalg.norm(v[end][:, None] - v[end][None], axis=2)
    assert end.sum() >= 12 and np.allclose(d0, d1, atol=0.05)
    deep = np.array([[0.0, 0, 0], [50, 0, 0]])
    assert np.allclose(skin.under_skin(deep, body)[0], deep)


def test_leaking_skin_stops_the_build():
    with pytest.raises(SystemExit):
        skin.Body(trimesh.creation.icosphere(subdivisions=3, radius=50.0))  # 0.5 L: under MIN_VOLUME_L


def test_licence_of_the_whole_body():
    m = build_script.MODELS["full_body"]
    assert m["license"] == {"id": "CC-BY-SA-4.0", "url": "https://creativecommons.org/licenses/by-sa/4.0/"}
    a = m["attribution"]
    assert "BodyParts3D" in a and "Open3DModel - Upper limb" in a and "Open3DModel - Lower limb" in a
    assert "Jan Kooloos" in a and "Eungyeol Lee" in a and "licensed under CC BY-SA 4.0" in a
    assert {s["license"] for s in m["sources"]} == {"CC-BY-SA-2.1-JP", "CC-BY-SA-4.0"}
    assert {s["url"] for s in m["sources"]} >= {"https://anatomytool.org/node/63906", "https://anatomytool.org/node/63936"}


def test_lower_limb_geometry_only_is_pinned():
    entries = [ln.split() for ln in open(os.path.join(ROOT, "pipeline", "open3d.sha256")) if ln.strip()]
    assert [e[1] for e in entries] == ["upper-limb/upper-limb-obj.zip", "lower-limb/lower-limb-obj.zip"]


def _rot_x(deg):
    return trimesh.transformations.rotation_matrix(np.radians(deg), [1, 0, 0])[:3, :3]


def synthetic(tmp_path):
    """Both OBJs (glTF frame, m) with every bone and nerve object, and a whole body (BodyParts3D frame, mm) with
    the bones of both sides moved by a known similarity that commutes with the mirror (rotation about x, no
    x translation), a skin around everything and the eyes. Median bones are symmetric."""
    m_true = 0.97 * _rot_x(1.5)
    t_true = np.array([0.0, -100.0, -25.0])
    items = {}

    def add_target(fid, src_m):
        mesh = trimesh.Trimesh(open3d.to_bp3d(src_m.vertices) @ m_true.T + t_true, src_m.faces)
        items[fid] = dict(id=fid, en=fid, fr=None, system="os", mesh=mesh, src=mesh, source="t")

    for k, (label, obj, table, bones) in enumerate(fb.LIMBS):
        lines, nv = [], 0

        def add(name, mesh):
            nonlocal nv
            lines.append(f"o {name}")
            lines.extend(f"v {x:.6f} {y:.6f} {z:.6f}" for x, y, z in mesh.vertices)
            lines.extend("f " + " ".join(str(i + 1 + nv) for i in f) for f in mesh.faces)
            nv += len(mesh.vertices)

        done = set()
        for j, (name, fid) in enumerate(bones.items()):
            b = trimesh.creation.icosphere(subdivisions=2, radius=0.006 + 0.001 * (j % 4))
            b.apply_scale([1, 1.4 + 0.05 * j, 1])
            median = fid not in fb.LEFT_BONES
            x = 0.0 if median else -0.03 - 0.004 * j
            b.apply_translation([x, 0.05 * k + 0.012 * j - 0.1, 0.004 * (j % 3)])
            add(name, b)
            if fid in done:  # sacrum and coccyx: one mesh in BodyParts3D
                items[fid]["mesh"] = items[fid]["src"] = trimesh.util.concatenate(
                    [items[fid]["mesh"], trimesh.Trimesh(open3d.to_bp3d(b.vertices) @ m_true.T + t_true, b.faces)])
                continue
            done.add(fid)
            add_target(fid, b)
            if not median:
                add_target(fb.LEFT_BONES[fid], fb.mirror(b))
        for j, name in enumerate(table):
            n = trimesh.creation.cylinder(radius=0.0015, height=0.02, sections=8)
            n.apply_translation([-0.03 - 0.0005 * j, 0.05 * k + 0.002 * j - 0.1, 0.006])
            add(name, n)
        (tmp_path / obj).write_text("\n".join(lines) + "\n", encoding="utf-8")
    items = list(items.values())
    center = np.mean([x["mesh"].centroid for x in items], axis=0)
    items.append(dict(id=fb.SKIN, en="integumentary system", fr="Peau", system="peau", mesh=None,
                      src=shell(300.0, center), source="t"))
    items[-1]["mesh"] = items[-1]["src"]
    return items


def test_nerves_of_both_sides_in_a_model(tmp_path, monkeypatch):
    monkeypatch.setattr(skin, "MIN_VOLUME_L", 1.0)
    monkeypatch.setattr(skin, "VOXEL", 6.0)  # a coarse grid for a body 60 cm wide
    items = synthetic(tmp_path)
    logs = []
    nerves = fb.nerves(str(tmp_path), items, log=logs.append)
    assert len(nerves) == 220 and len({x["id"] for x in nerves}) == 220
    assert sum("scale 0.9700" in ln for ln in logs) == 4  # upper/lower limb, right/left
    assert {x["system"] for x in nerves} == {"nerfs"} and {x["source"] for x in nerves} == {"open3dmodel"}
    by = {x["id"]: x for x in nerves}
    right, left = by["FMA22111"], by["FMA22112"]  # sciatic nerve
    assert right["en"] == "right sciatic nerve" and left["en"] == "left sciatic nerve" and right["fr"] == left["fr"]
    assert np.allclose(np.sort(left["src"].vertices, 0), np.sort(right["src"].vertices * [-1, 1, 1], 0), atol=0.05)
    assert by["FMA77549-L"]["en"] == "set of anterior divisions of left brachial plexus"
    for x in items:
        if x["id"] == fb.SKIN:
            x["mesh"] = trimesh.Trimesh(x["src"].vertices, x["src"].faces)
    fbm = build_script.MODELS["full_body"]
    m = build(items + nerves, str(tmp_path / "fb.glb"), str(tmp_path / "fb.json"), "full_body", "0.0.0", **fbm)
    check.check(str(tmp_path / "fb.json"))
    assert m["license"]["id"] == "CC-BY-SA-4.0"
    sides = [s for s in m["structures"] if s["system"] == "nerfs"]
    assert all((s["bbox"][1][0] < 0.001) == bool(re.search(r"\bright\b", s["en"])) for s in sides)
