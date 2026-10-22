"""Muscles that work in the movements (rig.py): how much each one contracts along each movement, and the bulge of a
contracted muscle.

Contraction: a curve per muscle and movement, sampled on the movement's keys, from +1 (the muscle shortens fully: the
movement it produces at its full range) to -CONTRACT_STRETCH (lengthened by the opposite movement: a little thinner),
0 at rest. It follows the joint angles of the movement through ACTIONS, a textbook table of the prime movers of each
degree of freedom (not measured activity: a muscle that only steadies a joint is left out).

Bulge: an offset per vertex of the muscles mesh (glTF frame, m), the shape of a muscle at contraction +1, added before
skinning (the app scales it by the contraction). The belly swells along the vertex normals, most at the middle of
the fibres' length and not at all on the tendons; a muscle keeps its ends, attached to the bones.
"""
import re

import numpy as np
import trimesh

from .rig import joint_name

# (joint bases summed, degree of freedom, full range (degrees, the total of the bases), mirrored for the left side,
#  muscles producing the positive angle, muscles producing the negative angle). Positive angles are those of
#  rig.pivots: flexion, abduction, pronation, dorsiflexion, elevation, opening of the mouth; the spine bends forwards,
#  to the right (inclinaison) and turns to the left (rotation): `mirrored` swaps the role of the left side's muscles.
LUMBAR = tuple(f"lombaire-{k}" for k in range(1, 6))
NECK = tuple(f"cervicale-{k}" for k in range(2, 8))
ERECTOR = [r"iliocostalis (lumborum|thoracis)", r"longissimus thoracis", r"\bspinalis", r"multifidus"]
HAMSTRINGS = [r"biceps femoris", r"semitendinosus", r"semimembranosus"]
ACTIONS = [
    (("coude",), "flexion", 120, False,
     [r"biceps brachii", r"\bbrachialis", r"brachioradialis"], [r"triceps brachii", r"anconeus"]),
    (("avant-bras",), "pronation", 140, False, [r"pronator teres", r"pronator quadratus"], [r"supinator\b"]),
    (("poignet",), "flexion", 60, False,
     [r"flexor carpi", r"palmaris longus", r"flexor digitorum superficialis", r"flexor digitorum profundus"],
     [r"extensor carpi", r"extensor digitorum$"]),
    (("epaule",), "abduction", 100, False, [r"acromial part of .*deltoid", r"supraspinatus"],
     [r"latissimus dorsi", r"teres major", r"(sternocostal|abdominal) part of .*pectoralis major"]),
    (("ceinture",), "elevation", 30, False,
     # serratus anterior: upper_limb only (full_body has no such structure).
     [r"descending part of .*trapezius", r"levator scapulae", r"serratus anterior"], [r"pectoralis minor"]),
    (("epaule",), "flexion", 120, False,
     [r"clavicular part of .*deltoid", r"clavicular part of .*pectoralis major", r"coracobrachialis"],
     [r"spinal part of .*deltoid", r"latissimus dorsi", r"teres major"]),
    (("hanche",), "flexion", 100, False,
     [r"iliacus", r"psoas major", r"rectus femoris", r"sartorius", r"tensor fasciae latae", r"pectineus"],
     [r"gluteus maximus", *HAMSTRINGS]),
    (("hanche",), "abduction", 40, False, [r"gluteus medius", r"gluteus minimus", r"tensor fasciae latae"],
     [r"adductor (longus|brevis|magnus)", r"gracilis", r"pectineus"]),
    (("genou",), "flexion", 120, False, [*HAMSTRINGS, r"gracilis", r"gastrocnemius", r"popliteus"],
     [r"vastus", r"rectus femoris"]),
    (("cheville",), "flexion-dorsale", 20, False,
     [r"tibialis anterior", r"extensor digitorum longus", r"extensor hallucis longus", r"fibularis tertius"], []),
    (("cheville",), "flexion-dorsale", 45, False, [],
     [r"gastrocnemius", r"soleus", r"plantaris", r"tibialis posterior", r"fibularis (longus|brevis)",
      r"flexor digitorum longus", r"flexor hallucis longus"]),
    (LUMBAR, "flexion", 50, False, [r"rectus abdominis", r"external oblique", r"internal oblique", r"pyramidalis"],
     [*ERECTOR, r"quadratus lumborum"]),
    (LUMBAR, "inclinaison", 30, True,
     [r"external oblique", r"internal oblique", r"quadratus lumborum", r"iliocostalis lumborum"], []),
    (NECK + ("tete",), "flexion", 45, False,
     [r"sternocleidomastoid", r"longus colli", r"longus capitis", r"scalenus anterior"],
     [r"splenius", r"semispinalis (capitis|cervicis)", r"longissimus capitis", r"rectus capitis posterior",
      r"descending part of .*trapezius"]),
    # Turning the head to the left: the right sternocleidomastoid, the left splenius and inferior oblique.
    (NECK + ("atlas",), "rotation", 70, True, [r"sternocleidomastoid"], [r"splenius capitis", r"obliquus capitis inferior"]),
    (("mandibule",), "abaissement", 25, False,
     [r"digastric", r"mylohyoid", r"geniohyoid", r"lower head of .*lateral pterygoid"], [r"masseter", r"temporalis$", r"medial pterygoid"]),
]
CONTRACT_STRETCH = 0.4  # contraction of a muscle lengthened by its full range (a fraction of the bulge, thinner)
CONTRACT_MIN = 0.05  # a muscle whose contraction stays below this along a movement is left out of it
BULGE = 0.6  # each surface of a fully contracted belly moves out by this fraction of the local half thickness


def _side(en):
    return next((s for s in ("right", "left") if re.search(rf"\b{s}\b", en)), None)


def _bare(en):
    """English name without its side (patterns are written for `long head of biceps brachii`)."""
    return re.sub(r"\s+", " ", re.sub(r"\b(right|left)\b", "", en)).strip()


def actions_of(en):
    """[(bases, dof, range, sign)] of a muscle (sign +1: it produces the positive angle), from its English name."""
    side, bare = _side(en), _bare(en)
    out = []
    for bases, dof, full, mirrored, pos, neg in ACTIONS:
        for sign, patterns in ((1, pos), (-1, neg)):
            if any(re.search(p, bare) for p in patterns):
                if mirrored:
                    if side is None:
                        continue
                    sign = -sign if side == "left" else sign
                out.append((bases, dof, full, sign))
    return out


def contraction(en, angles):
    """Contraction curve of a muscle (en: English name) along a movement, angles: {(joint name, dof): (K,) degrees}
    at its keys; None if the muscle does nothing in it. A muscle contracts for the movements it produces (the
    strongest, when several) and is lengthened by the opposite ones only when it produces none."""
    side = _side(en)
    parts = []
    for bases, dof, full, sign in actions_of(en):
        a = 0
        for base in bases:
            # Sided joints are those of the muscle's side; a muscle of the midline has none.
            for name in {joint_name(base, side), joint_name(base)} if side else {joint_name(base)}:
                a = a + angles.get((name, dof), 0)
        if np.ndim(a):
            parts.append(np.clip(sign * np.asarray(a, float) / full, -1, 1))
    if not parts:
        return None
    parts = np.array(parts)
    pos, neg = np.clip(parts.max(0), 0, None), np.clip(parts.min(0), None, 0)
    c = np.where(pos > 0.02, pos, CONTRACT_STRETCH * neg)
    c[0] = c[-1] = 0
    return c if np.abs(c).max() >= CONTRACT_MIN else None


def muscle_curves(entries, animations):
    """{movement key: [{"structures": [ids], "values": [...]}]}: the muscles (manifest entries of the muscles system)
    that work in each movement (rig.build_rig animations, with their joint angles), grouped by identical curve."""
    out = {}
    for a in animations:
        groups = {}
        for e in entries:
            c = contraction(e["en"], a["angles"])
            if c is not None:
                key = tuple(np.round(c, 2))
                groups.setdefault(key, []).append(e["id"])
        out[a["key"]] = [{"structures": sorted(ids), "values": [float(v) for v in key]} for key, ids in groups.items()]
        out[a["key"]].sort(key=lambda g: g["structures"][0])
    return out


def _thickness(mesh):
    """Thickness of a closed mesh at each vertex (m): the distance along the inward normal to the opposite surface,
    then averaged over the vertex's neighbours. A vertex whose ray finds nothing takes the median."""
    v, n = np.asarray(mesh.vertices, float), np.asarray(mesh.vertex_normals, float)
    hit = np.full(len(v), np.nan)
    locations, rays, _ = mesh.ray.intersects_location(v - n * 1e-5, -n, multiple_hits=False)
    hit[rays] = np.linalg.norm(locations - v[rays], axis=1)
    hit[hit < 1e-4] = np.nan
    median = np.nanmedian(hit) if np.isfinite(hit).any() else 0.0
    t = np.where(np.isfinite(hit), hit, median)
    # A ray grazing a fold reaches far: never more than three times the median, then smoothed.
    t = np.clip(t, 0, 3 * median)
    edges = mesh.edges_unique
    deg = np.bincount(edges.ravel(), minlength=len(v)).astype(float)
    for _ in range(3):
        acc = t.copy()
        np.add.at(acc, edges[:, 0], t[edges[:, 1]])
        np.add.at(acc, edges[:, 1], t[edges[:, 0]])
        t = acc / (1 + deg)
    return t


def bulge(positions, normals, indices, fiber, tendon, structures):
    """(N, 3) offsets of the muscles mesh at contraction +1 for `structures` [((first vertex, count), (first
    triangle, count))], zero elsewhere. Along each muscle's mean fibre direction its belly swells most at the middle,
    its ends and tendons stay; the swelling is BULGE times the local half thickness (measured at each vertex: a flat
    sheet wrapped around the trunk swells by a fraction of its few millimetres, not of its curvature)."""
    out = np.zeros((len(positions), 3))
    for (v0, n), (t0, tn) in structures:
        if n < 8:
            continue
        p = np.asarray(positions[v0:v0 + n], float)
        mesh = trimesh.Trimesh(p, np.asarray(indices[t0:t0 + tn]) - v0, process=False)
        centred = p - p.mean(0)
        # Never more than the muscle's half thickness as a whole (its smallest spread): an oblique ray through a
        # round belly crosses more than its thickness.
        whole = 1.4 * np.sqrt(max(np.linalg.eigvalsh(np.cov(centred.T))[0], 0))
        half = np.minimum(0.5 * _thickness(mesh), whole)
        f = np.asarray(fiber[v0:v0 + n], float) if fiber is not None else None
        if f is not None and np.isfinite(f).all() and np.abs(f).sum() > 0:
            axis = np.linalg.eigh(f.T @ f)[1][:, -1]
        else:
            axis = np.linalg.eigh(centred.T @ centred)[1][:, -1]
        s_ = centred @ axis
        t = (s_ - s_.min()) / max(s_.max() - s_.min(), 1e-9)
        profile = np.sin(np.pi * t) ** 1.5
        if tendon is not None:
            profile = profile * (1 - np.asarray(tendon[v0:v0 + n], float))
        out[v0:v0 + n] = np.asarray(normals[v0:v0 + n], float) * (BULGE * half * profile)[:, None]
    return out
