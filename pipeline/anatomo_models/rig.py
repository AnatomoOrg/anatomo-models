"""Skeleton rig and movements of the `os` mesh: joints, rigid skinning and glTF animations.

Each bone is rigid: all the vertices of a structure of the `os` mesh are bound to one joint (weight 1). A joint is
a glTF node placed at the anatomical centre of rotation of the joint it stands for (centre of the femoral head,
middle of the femoral epicondyles...), computed from the published geometry and the bony landmarks. Its rest
rotation is the identity and its axes are those of the model frame, so a joint's rotation is the movement of
its bone relative to the parent bone, about axes given in the anatomical position.

The movements are glTF animations of the joints' rotations (LINEAR quaternions): each one starts and ends in the
anatomical position. They are defined here as joint angles over time (anatomical degrees of freedom: flexion,
abduction, rotation...), about axes taken from the bones where the anatomy gives one (epicondyles for the elbow
and the knee, malleoli for the ankle, styloid processes for the wrist, radial head to ulnar head for the
pronation), otherwise about the axes of the frame.

Frame (glTF, m): +X = subject's left, +Y = up, +Z = anterior. The right side is at negative X.
"""
import re
from dataclasses import dataclass

import numpy as np

FPS = 24  # keyframes per second of the sampled animations


# --- Joints -------------------------------------------------------------------------------------------------------

SIDES = {"right": "d", "left": "g"}
SIDE_FR = {"right": ("droit", "droite"), "left": ("gauche", "gauche")}

LUMBAR = ["first", "second", "third", "fourth", "fifth"]
CERVICAL = ["third", "fourth", "fifth", "sixth", "seventh"]

# Structures of the os mesh -> joint (by English FMA name). `{s}` is the side: "right" or "left".
# Every structure of the mesh must match one rule (the build fails otherwise).
MIDLINE_RULES = [
    (r"(right|left) side of bony pelvis|posterior part of pelvis", "bassin"),
    *[(rf"{n} lumbar vertebra", f"lombaire-{i + 1}") for i, n in enumerate(LUMBAR)],
    (r"thoracic vertebra|\brib$|costal cartilage|manubrium|body of sternum|xiphoid process", "thorax"),
    *[(rf"{n} cervical vertebra", f"cervicale-{i + 3}") for i, n in enumerate(CERVICAL)],
    (r"^axis$", "cervicale-2"),
    (r"^atlas$", "atlas"),
    (r"^hyoid bone$", "cervicale-3"),
    (r"skeleton of mouth|\blower\b.*tooth", "mandibule"),
    (r"frontal bone|parietal bone|occipital part of head|temporal bone|sphenoid bone|basicranium|maxilla|cheek|"
     r"nasal bone|lacrimal bone|palatine bone|wall of internal nose|septum of internal nose|\bupper\b.*tooth",
     "tete"),
]
SIDE_RULES = [
    (r"clavicle|scapula", "ceinture"),
    (r"humerus", "epaule"),
    (r"\bulna\b", "coude"),
    (r"\bradius\b", "avant-bras"),
    (r"scaphoid|lunate|triquetral|pisiform|trapezium|trapezoid|capitate|hamate|metacarpal|finger|thumb", "poignet"),
    (r"femur", "hanche"),
    (r"tibia|fibula", "genou"),
    (r"patella", "patella"),
    (r"talus|calcaneus|navicular|cuboid|cuneiform|metatarsal|toe|sesamoid bone of .* foot", "cheville"),
]

# name: (French name, parent). Sided joints are suffixed -d / -g; their parent keeps the same side.
JOINTS = {
    "squelette": ("Squelette", None),
    "bassin": ("Bassin", "squelette"),
    "lombaire-5": ("L5-S1", "bassin"),
    "lombaire-4": ("L4-L5", "lombaire-5"),
    "lombaire-3": ("L3-L4", "lombaire-4"),
    "lombaire-2": ("L2-L3", "lombaire-3"),
    "lombaire-1": ("L1-L2", "lombaire-2"),
    "thorax": ("T12-L1", "lombaire-1"),
    "cervicale-7": ("C7-T1", "thorax"),
    "cervicale-6": ("C6-C7", "cervicale-7"),
    "cervicale-5": ("C5-C6", "cervicale-6"),
    "cervicale-4": ("C4-C5", "cervicale-5"),
    "cervicale-3": ("C3-C4", "cervicale-4"),
    "cervicale-2": ("C2-C3", "cervicale-3"),
    "atlas": ("Atlanto-axoïdienne", "cervicale-2"),
    "tete": ("Atlanto-occipitale", "atlas"),
    "mandibule": ("Temporo-mandibulaire", "tete"),
    "ceinture": ("Sterno-claviculaire", "thorax"),
    "epaule": ("Épaule", "ceinture"),
    "coude": ("Coude", "epaule"),
    "avant-bras": ("Radio-ulnaires", "coude"),
    "poignet": ("Poignet", "avant-bras"),
    "hanche": ("Hanche", "bassin"),
    "genou": ("Genou", "hanche"),
    "patella": ("Fémoro-patellaire", "hanche"),
    "cheville": ("Cheville", "genou"),
}
SIDED = {name for _, name in SIDE_RULES}


def joint_name(base, side=None):
    return f"{base}-{SIDES[side]}" if side else base


FEMININE = {"epaule", "hanche", "cheville", "ceinture", "patella"}  # articulation, épaule, hanche, cheville


def joint_fr(base, side=None):
    fr = JOINTS[base][0]
    if not side:
        return fr
    word = SIDE_FR[side][1 if base in FEMININE or base == "avant-bras" else 0]
    return f"{fr} {word}{'s' if base == 'avant-bras' else ''}"


def bind(en):
    """Joint (name) a structure of the os mesh is bound to, from its English name; None if no rule matches."""
    side = next((s for s in SIDES if re.search(rf"\b{s}\b", en)), None)
    for pattern, base in SIDE_RULES:
        if side and re.search(pattern, en):
            return joint_name(base, side)
    for pattern, base in MIDLINE_RULES:
        if re.search(pattern, en):
            return base
    return None


# --- Geometry helpers ---------------------------------------------------------------------------------------------

def fit_sphere(points):
    """Least-squares sphere through points: (centre, radius)."""
    p = np.asarray(points, float)
    a = np.c_[2 * p, np.ones(len(p))]
    b = (p ** 2).sum(1)
    sol, *_ = np.linalg.lstsq(a, b, rcond=None)
    c = sol[:3]
    return c, float(np.sqrt(max(sol[3] + c @ c, 0.0)))


def body_endplate(v):
    """Centre of the inferior end plate of a vertebral body (the anterior part of the vertebra), m."""
    zmin, zmax = v[:, 2].min(), v[:, 2].max()
    xmid, width = (v[:, 0].min() + v[:, 0].max()) / 2, v[:, 0].max() - v[:, 0].min()
    body = v[(v[:, 2] >= zmax - 0.35 * (zmax - zmin)) & (np.abs(v[:, 0] - xmid) <= 0.3 * width)]
    c = body.mean(0)
    return np.array([c[0], body[:, 1].min() - 0.003, c[2]])


class RigError(Exception):
    pass


class Bones:
    """Published vertices of the bones (glTF frame, m) by structure name, and the bony landmarks by (id, side)."""

    def __init__(self, structures, positions, marks):
        self.v = {}
        for s in structures:
            v0, n = s["vertices"]
            self.v[s["en"]] = np.asarray(positions[v0:v0 + n], float)
        self.marks = {(m["id"], m["side"]): np.asarray(m["position"], float) for m in marks}

    def has(self, en):
        return en in self.v

    def get(self, en):
        if en not in self.v:
            raise RigError(f"missing bone: {en}")
        return self.v[en]

    def mark(self, id, side=None):
        key = (id, side)
        if key not in self.marks:
            raise RigError(f"missing landmark: {id} ({side})")
        return self.marks[key]


def _orient(axis, ref, max_deg=None):
    """Unit axis pointing like ref; with max_deg, tilted back towards ref to at most max_deg away from it (an axis
    taken from two landmarks inherits their placement error)."""
    axis = np.asarray(axis, float)
    axis = axis / np.linalg.norm(axis)
    axis = axis if axis @ ref >= 0 else -axis
    angle = np.degrees(np.arccos(np.clip(axis @ ref, -1, 1)))
    if max_deg is not None and angle > max_deg:
        perp = axis - (axis @ ref) * ref
        perp /= np.linalg.norm(perp)
        a = np.radians(max_deg)
        axis = np.cos(a) * ref + np.sin(a) * perp
    return axis


MAX_TILT = 12  # degrees between an axis taken from the bones and the frame axis of the same movement


def mirror_axis(a, side):
    """Rotation axis of the given side from the right-side one (an axial vector: x -> x, y -> -y, z -> -z)."""
    a = np.asarray(a, float)
    return a if side == "right" else a * [1, -1, -1]


def pivots(b, name):
    """(pivot, {degree of freedom: unit axis}) of a joint, or None when the model lacks its bones. Axes are oriented
    so that a positive angle is the movement named (flexion, abduction, medial rotation, pronation...)."""
    base, side = (name[:-2], {"d": "right", "g": "left"}[name[-1]]) if name[:-2] in SIDED else (name, None)
    X, Y, Z = np.eye(3)

    def m(axis):
        return mirror_axis(axis, side)

    if base == "squelette":
        return np.zeros(3), {}
    if base == "bassin":
        if not b.has("posterior part of pelvis"):
            return None
        heads = [fit_head(b, s) for s in ("right", "left")]
        return np.mean(heads, 0), {}
    if base.startswith("lombaire-") or base == "thorax" or base.startswith("cervicale-"):
        en = {"thorax": "twelfth thoracic vertebra", "cervicale-2": "axis"}.get(base)
        if not en:
            k = int(base.rsplit("-", 1)[1])
            en = f"{LUMBAR[k - 1]} lumbar vertebra" if base.startswith("lombaire") else f"{CERVICAL[k - 3]} cervical vertebra"
        if not b.has(en):
            return None
        # Flexion brings the upper body forwards; lateral flexion to the right; rotation to the left.
        return body_endplate(b.get(en)), {"flexion": X, "inclinaison": Z, "rotation": Y}
    if base == "atlas":
        if not b.has("atlas"):
            return None
        dens = b.mark("c2.dent")
        return np.array([dens[0], b.get("atlas")[:, 1].mean(), dens[2]]), {"rotation": Y}
    if base == "tete":
        if not b.has("atlas"):
            return None
        a = b.get("atlas")
        dens = b.mark("c2.dent")
        return np.array([dens[0], a[:, 1].max(), dens[2]]), {"flexion": X, "inclinaison": Z}
    if base == "mandibule":
        if not b.has("skeleton of mouth"):
            return None
        r, l = b.mark("mandibule.processus-condylaire", "right"), b.mark("mandibule.processus-condylaire", "left")
        return (r + l) / 2 - [0, 0.004, 0], {"abaissement": _orient(l - r, X)}
    if base == "ceinture":
        if not b.has(f"{side} clavicle"):
            return None
        # Elevation of the lateral end of the clavicle (and upward rotation of the scapula), about the AP axis.
        return b.mark("clavicule.extremite-sternale", side), {"elevation": m(-Z), "protraction": m(Y)}
    if base == "epaule":
        if not b.has(f"{side} humerus"):
            return None
        hv = b.get(f"{side} humerus")
        c, r = fit_sphere(hv[np.linalg.norm(hv - b.mark("humerus.tete", side), axis=1) < 0.024])
        if not 0.015 < r < 0.035:
            raise RigError(f"{side} humeral head: radius {r * 1000:.1f} mm")
        return c, {"flexion": -X, "abduction": m(-Z), "rotation": m(Y)}
    if base == "coude":
        if not b.has(f"{side} ulna"):
            return None
        lat, med = b.mark("humerus.epicondyle-lateral", side), b.mark("humerus.epicondyle-medial", side)
        hv = b.get(f"{side} humerus")
        c, r = fit_sphere(hv[np.linalg.norm(hv - b.mark("humerus.capitulum", side), axis=1) < 0.012])
        axis = _orient(med - lat, -X, MAX_TILT)
        if not 0.006 < r < 0.02:
            raise RigError(f"{side} capitulum: radius {r * 1000:.1f} mm")
        # The flexion axis runs through the centre of the capitulum, along the epicondyles.
        return c, {"flexion": axis}
    if base == "avant-bras":
        if not b.has(f"{side} radius"):
            return None
        rv, uv = b.get(f"{side} radius"), b.get(f"{side} ulna")
        head = rv[rv[:, 1] > rv[:, 1].max() - 0.01].mean(0)
        ulna_head = uv[uv[:, 1] < uv[:, 1].min() + 0.012].mean(0)
        # Pronation turns the palm backwards, about the axis from the radial head to the ulnar head.
        return head, {"pronation": _orient(head - ulna_head, m(Y), 20)}
    if base == "poignet":
        if not b.has(f"{side} lunate"):
            return None
        rs, us = b.mark("radius.processus-styloide", side), b.mark("ulna.processus-styloide", side)
        lunate = b.get(f"{side} lunate").mean(0)
        # Flexion brings the palm forwards (anatomical position: palm anterior); ulnar deviation, little finger side.
        return lunate, {"flexion": _orient(us - rs, -X, MAX_TILT), "deviation": m(Z)}
    if base == "hanche":
        if not b.has(f"{side} femur"):
            return None
        return fit_head(b, side), {"flexion": -X, "abduction": m(-Z), "rotation": m(Y)}
    if base in ("genou", "patella"):
        if not b.has(f"{side} tibia" if base == "genou" else f"{side} patella"):
            return None
        lat, med = b.mark("femur.epicondyle-lateral", side), b.mark("femur.epicondyle-medial", side)
        # About the frame's transverse axis: the epicondylar line of the file is tilted by some 8 degrees, enough
        # to swing the foot several centimetres sideways in a deep flexion.
        return (lat + med) / 2, {"flexion": X}
    if base == "cheville":
        if not b.has(f"{side} talus"):
            return None
        lat, med = b.mark("fibula.malleole-laterale", side), b.mark("tibia.malleole-mediale", side)
        # Dorsiflexion brings the foot up; the axis runs through the tips of the malleoli.
        return (lat + med) / 2, {"flexion-dorsale": _orient(med - lat, -X, MAX_TILT)}
    raise RigError(f"unknown joint {name}")


def fit_head(b, side):
    fv = b.get(f"{side} femur")
    c, r = fit_sphere(fv[np.linalg.norm(fv - b.mark("femur.tete", side), axis=1) < 0.03])
    if not 0.015 < r < 0.04:
        raise RigError(f"{side} femoral head: radius {r * 1000:.1f} mm")
    return c


# --- Movements ----------------------------------------------------------------------------------------------------

def smooth(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)


def keys(*points):
    """Piecewise smooth curve through (t, value) points, t in [0, 1]: f(t) for an array t."""
    ts, vs = np.array([p[0] for p in points], float), np.array([p[1] for p in points], float)

    def f(t):
        t = np.asarray(t, float)
        i = np.clip(np.searchsorted(ts, t, side="right") - 1, 0, len(ts) - 2)
        u = smooth((t - ts[i]) / (ts[i + 1] - ts[i]))
        return vs[i] + (vs[i + 1] - vs[i]) * u
    return f


UP_HOLD_DOWN = keys((0, 0), (0.4, 1), (0.6, 1), (1, 0))


def scaled(f, k):
    return lambda t: k * f(t)


@dataclass
class Movement:
    key: str
    fr: str
    plane: str  # sagittal, frontal, transverse: the plane the movement is best seen in
    duration: float  # s
    # (joint base, side or None, degree of freedom) -> angle (degrees) as a function of t in [0, 1]
    curves: dict
    side: str | None = None  # the side shown, for a one-sided movement
    requires: tuple = ()  # joints without which the movement is left out
    fps: int = FPS
    grounded: bool = False  # the skeleton goes down so that the lowest foot stays on the ground
    one_side: str | None = None  # name when the model has only the right side of a two-sided movement


def _gait(phase):
    """Simplified sagittal joint angles (degrees) of a walking cycle, phase in [0, 1) from heel strike.
    Smooth curves shaped on the textbook gait angles (hip, knee, ankle), not measured data."""
    two = 2 * np.pi * phase
    hip = 10 + 22 * np.cos(two)  # +32 flexion at heel strike, -12 extension at the end of stance
    knee = keys((0, 5), (0.15, 18), (0.4, 4), (0.6, 38), (0.72, 62), (0.9, 10), (1, 5))(phase)
    ankle = keys((0, 0), (0.08, -6), (0.45, 10), (0.62, -16), (0.75, 2), (1, 0))(phase)
    return hip, knee, ankle


def _walk(cycles=3, period=1.2, ramp=0.6):
    total = cycles * period + 2 * ramp

    def at(t, side, what):
        s = t * total
        env = smooth(s / ramp) * smooth((total - s) / ramp)
        phase = (s / period + (0.5 if side == "left" else 0.0)) % 1.0
        hip, knee, ankle = _gait(phase)
        values = {"hip": hip, "knee": knee, "ankle": ankle,
                  "arm": -0.6 * (hip - 10),  # arm swing, opposite to the leg of the same side
                  "elbow": 15 - 0.3 * (hip - 10)}
        return env * values[what]

    curves = {}
    for side in ("right", "left"):
        curves[("hanche", side, "flexion")] = (lambda sd: lambda t: at(t, sd, "hip"))(side)
        curves[("genou", side, "flexion")] = (lambda sd: lambda t: at(t, sd, "knee"))(side)
        curves[("patella", side, "flexion")] = (lambda sd: lambda t: 0.6 * at(t, sd, "knee"))(side)
        curves[("cheville", side, "flexion-dorsale")] = (lambda sd: lambda t: at(t, sd, "ankle"))(side)
        curves[("epaule", side, "flexion")] = (lambda sd: lambda t: at(t, sd, "arm"))(side)
        curves[("coude", side, "flexion")] = (lambda sd: lambda t: at(t, sd, "elbow"))(side)
    return Movement("marche", "Marche (simplifiée)", "sagittal", total, curves,
                    requires=("hanche-d", "hanche-g", "genou-d", "genou-g", "cheville-d", "cheville-g"), grounded=True)


def _spine(dof, amplitude, base_joints, curve):
    """The same curve spread over several segments of the spine (amplitude in degrees, in total)."""
    per = amplitude / len(base_joints)
    return {(j, None, dof): scaled(curve, per) for j in base_joints}


LUMBAR_JOINTS = [f"lombaire-{k}" for k in range(1, 6)]
NECK_JOINTS = [f"cervicale-{k}" for k in range(2, 8)]


def movements():
    r = "right"
    out = [
        Movement("flexion-coude", "Flexion du coude", "sagittal", 4.0,
                 {("coude", r, "flexion"): scaled(UP_HOLD_DOWN, 135)}, side=r, requires=("coude-d",)),
        Movement("pronation-supination", "Pronation et supination", "transverse", 6.0,
                 {("coude", r, "flexion"): keys((0, 0), (0.15, 90), (0.85, 90), (1, 0)),
                  ("avant-bras", r, "pronation"): keys((0, 0), (0.15, 0), (0.4, 85), (0.6, 85), (0.85, 0), (1, 0))},
                 side=r, requires=("avant-bras-d",)),
        Movement("flexion-extension-poignet", "Flexion et extension du poignet", "sagittal", 5.0,
                 {("poignet", r, "flexion"): keys((0, 0), (0.3, 70), (0.4, 70), (0.7, -60), (0.8, -60), (1, 0))},
                 side=r, requires=("poignet-d",)),
        Movement("abduction-epaule", "Abduction des épaules", "frontal", 5.0,
                 {**{("epaule", s, "abduction"): scaled(UP_HOLD_DOWN, 120) for s in ("right", "left")},
                  **{("ceinture", s, "elevation"): scaled(UP_HOLD_DOWN, 30) for s in ("right", "left")}},
                 requires=("epaule-d",), one_side="Abduction de l'épaule"),
        Movement("flexion-epaule", "Flexion de l'épaule", "sagittal", 5.0,
                 {("epaule", r, "flexion"): scaled(UP_HOLD_DOWN, 150)}, side=r, requires=("epaule-d",)),
        Movement("flexion-hanche", "Flexion de la hanche (genou fléchi)", "sagittal", 4.5,
                 {("hanche", r, "flexion"): scaled(UP_HOLD_DOWN, 110), ("genou", r, "flexion"): scaled(UP_HOLD_DOWN, 110),
                  ("patella", r, "flexion"): scaled(UP_HOLD_DOWN, 66)}, side=r, requires=("hanche-d", "genou-d")),
        Movement("abduction-hanche", "Abduction de la hanche", "frontal", 4.0,
                 {("hanche", r, "abduction"): scaled(UP_HOLD_DOWN, 40)}, side=r, requires=("hanche-d",)),
        Movement("flexion-genou", "Flexion du genou", "sagittal", 4.0,
                 {("genou", r, "flexion"): scaled(UP_HOLD_DOWN, 125), ("patella", r, "flexion"): scaled(UP_HOLD_DOWN, 75)},
                 side=r, requires=("genou-d",)),
        Movement("flexion-cheville", "Flexion dorsale et plantaire", "sagittal", 5.0,
                 {("cheville", r, "flexion-dorsale"): keys((0, 0), (0.25, 20), (0.35, 20), (0.7, -45), (0.8, -45), (1, 0))},
                 side=r, requires=("cheville-d",)),
        Movement("flexion-extension-tronc", "Flexion et extension du tronc", "sagittal", 6.0,
                 _spine("flexion", 50, LUMBAR_JOINTS, keys((0, 0), (0.3, 1), (0.4, 1), (0.7, -0.5), (0.8, -0.5), (1, 0))),
                 requires=tuple(LUMBAR_JOINTS)),
        Movement("inclinaison-tronc", "Inclinaison latérale du tronc", "frontal", 6.0,
                 _spine("inclinaison", 30, LUMBAR_JOINTS, keys((0, 0), (0.25, 1), (0.35, 1), (0.65, -1), (0.75, -1), (1, 0))),
                 requires=tuple(LUMBAR_JOINTS)),
        Movement("flexion-extension-tete", "Flexion et extension de la tête", "sagittal", 6.0,
                 {**_spine("flexion", 35, NECK_JOINTS, keys((0, 0), (0.3, 1), (0.4, 1), (0.7, -1.4), (0.8, -1.4), (1, 0))),
                  ("tete", None, "flexion"): keys((0, 0), (0.3, 10), (0.4, 10), (0.7, -15), (0.8, -15), (1, 0))},
                 requires=tuple(NECK_JOINTS) + ("tete",)),
        Movement("rotation-tete", "Rotation de la tête", "transverse", 6.0,
                 {("atlas", None, "rotation"): keys((0, 0), (0.25, 40), (0.35, 40), (0.65, -40), (0.75, -40), (1, 0)),
                  **_spine("rotation", 30, NECK_JOINTS, keys((0, 0), (0.25, 1), (0.35, 1), (0.65, -1), (0.75, -1), (1, 0)))},
                 requires=("atlas",)),
        Movement("ouverture-bouche", "Ouverture de la bouche", "sagittal", 3.0,
                 {("mandibule", None, "abaissement"): scaled(UP_HOLD_DOWN, 25)}, requires=("mandibule",)),
        _walk(),
    ]
    return out


# --- Rig ----------------------------------------------------------------------------------------------------------

def quat(axis, degrees):
    """Unit quaternions (x, y, z, w) of rotations about a unit axis, for an array of angles."""
    a = np.radians(np.asarray(degrees, float)) / 2
    return np.c_[np.outer(np.sin(a), axis), np.cos(a)]


def qmul(a, b):
    ax, ay, az, aw = a.T
    bx, by, bz, bw = b.T
    return np.c_[aw * bx + ax * bw + ay * bz - az * by, aw * by - ax * bz + ay * bw + az * bx,
                 aw * bz + ax * by - ay * bx + az * bw, aw * bw - ax * bx - ay * by - az * bz]


def qrot(q, v):
    """Rotate vectors v (n,3) by quaternions q (n,4) or one quaternion (4,)."""
    q = np.broadcast_to(q, (len(v), 4))
    u, w = q[:, :3], q[:, 3:]
    t = 2 * np.cross(u, v)
    return v + w * t + np.cross(u, t)


def build_rig(structures, positions, marks):
    """Rig of the `os` mesh. structures: the manifest entries of the os system (en, vertices); positions: the os
    POSITION array; marks: the landmarks (id, side, position). Returns None when the model has no bone the rig
    knows (no joint besides the root), else a dict:
      joints: [{name, fr, parent (index or None), pivot (3,), axes {dof: (3,)}, structures [ids]}], root first,
              parents before children;
      vertex_joint: (N,) joint index per vertex of the os mesh;
      animations: [{key, fr, plane, side, duration, joints [names],
                    channels [{joint (index), path ("rotation" or "translation"), times (K,), values (K,4|3)}]}].
    """
    b = Bones(structures, positions, marks)
    bound = {}
    for s in structures:
        j = bind(s["en"])
        if j is None:
            raise RigError(f"bone bound to no joint: {s['en']}")
        bound.setdefault(j, []).append(s)
    # Joints present: the bound ones and their ancestors (a missing joint hands its children to its parent).
    names = []
    for base, (fr, parent) in JOINTS.items():
        for side in (("right", "left") if base in SIDED else (None,)):
            names.append((joint_name(base, side), base, side))
    found = {}
    for name, base, side in names:
        p = pivots(b, name)
        if p is not None:
            found[name] = (base, side, p)
    missing = set(bound) - set(found)
    if missing:
        raise RigError(f"bones bound to joints without a pivot: {sorted(missing)}")

    def parent_of(name, base, side):
        p = JOINTS[base][1]
        while p is not None:
            pn = joint_name(p, side if p in SIDED else None)
            if pn in found:
                return pn
            p = JOINTS[p][1]
        return None

    order = [n for n, _, _ in names if n in found]
    # Joints that bind nothing and lead to nothing bound are dropped (an empty chain).
    needed = set()
    for n in bound:
        while n is not None:
            needed.add(n)
            base, side, _ = found[n]
            n = parent_of(n, base, side)
    needed.add("squelette")
    order = [n for n in order if n in needed]
    if len(order) <= 1:
        return None
    index = {n: i for i, n in enumerate(order)}
    joints = []
    for n in order:
        base, side, (pivot, axes) = found[n]
        par = parent_of(n, base, side)
        joints.append({"name": n, "fr": joint_fr(base, side), "parent": index[par] if par else None,
                       "pivot": np.asarray(pivot, float), "axes": axes,
                       "structures": sorted(s["id"] for s in bound.get(n, []))})
    assert all(j["parent"] is None or j["parent"] < i for i, j in enumerate(joints))
    vertex_joint = np.zeros(len(positions), np.uint8)
    for n, items in bound.items():
        for s in items:
            v0, k = s["vertices"]
            vertex_joint[v0:v0 + k] = index[n]
    rig = {"joints": joints, "vertex_joint": vertex_joint, "animations": []}
    feet = _feet(b, index)
    for mv in movements():
        if not all(r in index for r in mv.requires):
            continue
        n_keys = int(round(mv.duration * mv.fps)) + 1
        times = np.linspace(0, mv.duration, n_keys)
        t = times / mv.duration
        per_joint = {}
        for (base, side, dof), curve in mv.curves.items():
            n = joint_name(base, side)
            if n not in index:
                continue
            axis = joints[index[n]]["axes"][dof]
            q = quat(axis, curve(t))
            per_joint[n] = qmul(per_joint[n], q) if n in per_joint else q
        channels = []
        for n, q in per_joint.items():
            q[0] = q[-1] = (0, 0, 0, 1)  # exactly the anatomical position at both ends
            q /= np.linalg.norm(q, axis=1, keepdims=True)
            channels.append({"joint": index[n], "path": "rotation", "times": times, "values": q})
        anim = {"key": mv.key, "fr": mv.fr, "plane": mv.plane, "side": mv.side, "duration": mv.duration,
                "joints": list(per_joint), "channels": channels}
        if mv.one_side and not any(n.endswith("-g") for n in per_joint):
            anim.update(fr=mv.one_side, side="right")
        if mv.grounded and feet:
            # The lowest foot stays on the ground: the whole skeleton goes down as the legs bend.
            drop = np.zeros(n_keys)
            rest = min(p[1] for _, p in feet)
            for k, tk in enumerate(times):
                world = pose(rig, animation_pose(rig, anim, tk))
                drop[k] = rest - min(posed_points(rig, world, j, [p])[0][1] for j, p in feet)
            drop[0] = drop[-1] = 0
            root = joints[0]["pivot"]
            channels.append({"joint": 0, "path": "translation", "times": times,
                             "values": np.c_[np.full(n_keys, root[0]), root[1] + drop, np.full(n_keys, root[2])]})
            anim["joints"].append(joints[0]["name"])
        rig["animations"].append(anim)
    return rig


def _feet(b, index):
    """Ground contact points of the feet: (ankle joint index, point) for the heel and the head of the first
    metatarsal of each side the model has."""
    out = []
    for side in ("right", "left"):
        j = index.get(joint_name("cheville", side))
        if j is None:
            continue
        for mark in ("calcaneus.tuberosite", "metatarsien-1.tete"):
            if (mark, side) in b.marks:
                out.append((j, b.marks[(mark, side)]))
    return out


def pose(rig, local):
    """World transform (rotation quaternion, translation) of each joint, from local transforms {joint index:
    {"rotation": (4,), "translation": (3,)}} (missing: the rest pose, identity rotation and the pivot offset from
    the parent)."""
    out = []
    for i, j in enumerate(rig["joints"]):
        x = local.get(i, {})
        q = np.asarray(x.get("rotation", (0, 0, 0, 1)), float)
        rest = j["pivot"] - (rig["joints"][j["parent"]]["pivot"] if j["parent"] is not None else 0)
        t = np.asarray(x.get("translation", rest), float)
        if j["parent"] is None:
            out.append((q, t))
            continue
        pq, pt = out[j["parent"]]
        out.append((qmul(pq[None], q[None])[0], pt + qrot(pq, t[None])[0]))
    return out


def posed_points(rig, world, joint, points):
    """Rest points bound to a joint, moved by a pose (from `pose`)."""
    q, t = world[joint]
    return t + qrot(q, np.asarray(points, float) - rig["joints"][joint]["pivot"])


def animation_pose(rig, anim, time):
    """Local transforms of an animation at a time (s), for `pose`: linear interpolation of the keys (normalised
    lerp for the rotations: close to the slerp of glTF LINEAR at these key spacings)."""
    out = {}
    for c in anim["channels"]:
        times, v = c["times"], c["values"]
        i = int(np.clip(np.searchsorted(times, time, side="right") - 1, 0, len(times) - 2))
        u = float(np.clip((time - times[i]) / (times[i + 1] - times[i]), 0, 1))
        a, b = v[i], v[i + 1]
        if c["path"] == "rotation":
            b = b if a @ b >= 0 else -b
            r = (1 - u) * a + u * b
            r = r / np.linalg.norm(r)
        else:
            r = (1 - u) * a + u * b
        out.setdefault(c["joint"], {})[c["path"]] = r
    return out
