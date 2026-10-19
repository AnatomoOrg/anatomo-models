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
    """The rig cannot be built as the data stand (a fitted sphere of the wrong size, a patella off the femur...):
    the build stops."""


class RigMissing(RigError):
    """A bone or landmark the rig needs is not in the model: the model is published without a rig."""


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
            raise RigMissing(f"missing bone: {en}")
        return self.v[en]

    def mark(self, id, side=None):
        key = (id, side)
        if key not in self.marks:
            raise RigMissing(f"missing landmark: {id} ({side})")
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
    # A degree of freedom given in the frame rather than relative to the parent joint: the joint undoes its parents'
    # rotation and turns by the curve about the axis, so that the limb stays in its plane (shoulder flexion: the
    # arm rises in the sagittal plane while the girdle lifts the shoulder; the curve is the arm's whole angle).
    sagittal: tuple | None = None


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
                  # From the supinated anatomical position to full pronation (palm down, elbow flexed), and back.
                  ("avant-bras", r, "pronation"): keys((0, 0), (0.15, 0), (0.4, 160), (0.6, 160), (0.85, 0), (1, 0))},
                 side=r, requires=("avant-bras-d",)),
        Movement("flexion-extension-poignet", "Flexion et extension du poignet", "sagittal", 5.0,
                 {("poignet", r, "flexion"): keys((0, 0), (0.3, 70), (0.4, 70), (0.7, -60), (0.8, -60), (1, 0))},
                 side=r, requires=("poignet-d",)),
        Movement("abduction-epaule", "Abduction des épaules", "frontal", 5.0,
                 {**{("epaule", s, "abduction"): scaled(UP_HOLD_DOWN, 120) for s in ("right", "left")},
                  **{("ceinture", s, "elevation"): scaled(UP_HOLD_DOWN, 30) for s in ("right", "left")}},
                 requires=("epaule-d",), one_side="Abduction de l'épaule"),
        Movement("flexion-epaule", "Flexion de l'épaule", "sagittal", 5.0,
                 # 150 degrees in all: about 120 at the glenohumeral joint and 30 from the girdle, as in abduction.
                 {("epaule", r, "flexion"): scaled(UP_HOLD_DOWN, 150),
                  ("ceinture", r, "elevation"): scaled(UP_HOLD_DOWN, 30)}, side=r, requires=("epaule-d",),
                 sagittal=("epaule", r, "flexion")),
        Movement("flexion-hanche", "Flexion de la hanche (genou fléchi)", "sagittal", 4.5,
                 {("hanche", r, "flexion"): scaled(UP_HOLD_DOWN, 110), ("genou", r, "flexion"): scaled(UP_HOLD_DOWN, 110)},
                 side=r, requires=("hanche-d", "genou-d")),
        Movement("abduction-hanche", "Abduction de la hanche", "frontal", 4.0,
                 {("hanche", r, "abduction"): scaled(UP_HOLD_DOWN, 40)}, side=r, requires=("hanche-d",)),
        Movement("flexion-genou", "Flexion du genou", "sagittal", 4.0,
                 {("genou", r, "flexion"): scaled(UP_HOLD_DOWN, 125)}, side=r, requires=("genou-d",)),
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
    POSITION array; marks: the landmarks (id, side, position). Returns None when the model has
    no bone the rig knows (no joint besides the root), or lacks a bone or a landmark a joint of its bones needs
    (the model is then published without a rig, see build.py), else a dict:
      joints: [{name, fr, parent (index or None), pivot (3,), axes {dof: (3,)}, structures [ids]}], root first,
              parents before children;
      vertex_joint: (N,) joint index per vertex of the os mesh;
      animations: [{key, fr, plane, side, duration, joints [names],
                    channels [{joint (index), path ("rotation" or "translation"), times (K,), values (K,4|3)}]}];
      measures: {name: value}, for the build report (patella gap, lowest foot vertex during the walk...).
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
    try:
        for name, base, side in names:
            p = pivots(b, name)
            if p is not None:
                found[name] = (base, side, p)
        missing = set(bound) - set(found)
        if missing:
            raise RigMissing(f"bones bound to joints without a pivot: {sorted(missing)}")
    except RigMissing as e:
        print(f"rig: none ({e})")
        return None

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
    rig = {"joints": joints, "vertex_joint": vertex_joint, "animations": [], "measures": {}}
    patellas = {}
    for side in ("right", "left"):
        knee, pat = joint_name("genou", side), joint_name("patella", side)
        if knee in index and pat in index:
            patellas[side] = PatellaTrack(b, side, joints[index[pat]]["pivot"], joints[index[pat]]["axes"]["flexion"])
    # Ground: every vertex of the feet (subsampled), not only a few landmarks.
    feet = [(index[n], np.asarray(positions, float)[vertex_joint == index[n]])
            for n in (joint_name("cheville", "right"), joint_name("cheville", "left")) if n in index]
    for mv in movements():
        if not all(r in index for r in mv.requires):
            continue
        n_keys = int(round(mv.duration * mv.fps)) + 1
        times = np.linspace(0, mv.duration, n_keys)
        t = times / mv.duration
        per_joint, angles = {}, {}
        for (base, side, dof), curve in mv.curves.items():
            n = joint_name(base, side)
            if n not in index or (base, side, dof) == mv.sagittal:
                continue
            angles[(n, dof)] = curve(t)
            q = quat(joints[index[n]]["axes"][dof], angles[(n, dof)])
            per_joint[n] = qmul(per_joint[n], q) if n in per_joint else q
        if mv.sagittal and joint_name(mv.sagittal[0], mv.sagittal[1]) in index:
            # In the plane of the frame's axis whatever its parents do: the joint first undoes the rotation of its
            # parents at each key (the girdle lifts the shoulder without swinging the arm sideways), then turns
            # about the axis as seen in the world.
            base, side, dof = mv.sagittal
            n = joint_name(base, side)
            world = np.tile([0.0, 0, 0, 1], (n_keys, 1))
            chain, p = [], joints[index[n]]["parent"]
            while p is not None:
                chain.append(joints[p]["name"])
                p = joints[p]["parent"]
            for a in reversed(chain):
                if a in per_joint:
                    world = qmul(world, per_joint[a])
            q = qmul(world * [-1, -1, -1, 1], quat(joints[index[n]]["axes"][dof], mv.curves[mv.sagittal](t)))
            per_joint[n] = qmul(per_joint[n], q) if n in per_joint else q
        channels = []
        for side, track in patellas.items():
            knee = angles.get((joint_name("genou", side), "flexion"))
            if knee is None:
                continue
            n = joint_name("patella", side)
            per_joint[n], push = track(knee)
            rest = joints[index[n]]["pivot"] - joints[joints[index[n]]["parent"]]["pivot"]
            push[0] = push[-1] = 0
            channels.append({"joint": index[n], "path": "translation", "times": times, "values": rest + push})
            worst = max(track.gap(q, sh) for q, sh in zip(per_joint[n], push))
            key = f"patella {side}: widest gap to the femur at the animation keys (mm)"
            rig["measures"][key] = max(rig["measures"].get(key, 0.0), round(worst * 1000, 2))
        for n, q in per_joint.items():
            q[0] = q[-1] = (0, 0, 0, 1)  # exactly the anatomical position at both ends
            q /= np.linalg.norm(q, axis=1, keepdims=True)
            channels.append({"joint": index[n], "path": "rotation", "times": times, "values": q})
        channels.sort(key=lambda c: (c["joint"], c["path"] != "rotation"))
        anim = {"key": mv.key, "fr": mv.fr, "plane": mv.plane, "side": mv.side, "duration": mv.duration,
                "joints": list(per_joint),
                "channels": channels}
        if mv.one_side and not any(n.endswith("-g") for n in per_joint):
            anim.update(fr=mv.one_side, side="right")
        if mv.grounded and feet:
            # The lowest point of the feet stays on the ground: the whole skeleton goes down as the legs bend.
            # The root's keys are 4 times denser than the joints': the feet turn between the joints' keys, and the
            # lowest point moves along the sole.
            rest = min(p[:, 1].min() for _, p in feet)
            fine = np.linspace(0, mv.duration, 4 * (n_keys - 1) + 1)

            def lowest(tk):
                world = pose(rig, animation_pose(rig, anim, tk))
                return min(posed_points(rig, world, j, p)[:, 1].min() for j, p in feet)
            drop = rest - np.array([lowest(tk) for tk in fine])
            drop[0] = drop[-1] = 0
            root = joints[0]["pivot"]
            channels.insert(0, {"joint": 0, "path": "translation", "times": fine,
                                "values": np.c_[np.full(len(fine), root[0]), root[1] + drop, np.full(len(fine), root[2])]})
            anim["joints"].append(joints[0]["name"])
            off = rest - np.array([lowest(tk) for tk in np.linspace(0, mv.duration, 16 * (n_keys - 1) + 1)])
            rig["measures"][f"{mv.key}: deepest foot point below the ground (mm)"] = float(round(max(off.max(), 0) * 1000, 2))
            rig["measures"][f"{mv.key}: highest lowest foot point above the ground (mm)"] = float(round(max(-off.min(), 0) * 1000, 2))
        rig["animations"].append(anim)
    for side, track in patellas.items():
        rig["measures"][f"patella {side}: gap to the femur at rest (mm)"] = round(track.rest_gap * 1000, 2)
        rig["measures"][f"patella {side}: widest gap to the femur, 0-140 deg (mm)"] = round(track.worst * 1000, 2)
    return rig


class PatellaTrack:
    """Where the patella goes as the knee bends: it turns about the knee axis, held at the length of the patellar
    ligament from the tibial tuberosity, and slides towards the axis until it touches the trochlea or the condyles
    again (the femur is not a cylinder around the knee axis). Tabulated once per side over 0-140 degrees of
    flexion; __call__ gives, for knee angles, the patella's rotations (quaternions, in the femur's frame) and its
    shifts (m). `worst`: the widest gap left between the patella and the femur over the table (m)."""

    STEP = 1.25

    def __init__(self, b, side, pivot, axis):
        from scipy.spatial import cKDTree
        self.pivot, self.axis = np.asarray(pivot, float), np.asarray(axis, float)
        pat, fem = b.get(f"{side} patella"), b.get(f"{side} femur")
        self.thetas = thetas = np.arange(0, 140 + self.STEP, self.STEP)
        tree = cKDTree(fem)

        def gap(v):
            return float(tree.query(v)[0].min())
        self._gap, self._pat = gap, pat

        # The articular face: the patella's vertices closest to the femur at rest.
        d0, _ = tree.query(pat)
        face = pat[d0 < d0.min() + 0.012]
        centre = face.mean(0)
        target = max(gap(pat), 0.0015)  # the gap at rest (cartilage), at least 1.5 mm
        tub, apex = b.marks.get(("tibia.tuberosite", side)), b.marks.get(("patella.apex", side))
        length = np.linalg.norm(apex - tub) if tub is not None and apex is not None else None

        def placed(alpha):
            q = quat(self.axis, [alpha])[0]
            v = self.pivot + qrot(q, face - self.pivot)
            u = self.pivot - (self.pivot + qrot(q, (centre - self.pivot)[None])[0])
            u /= np.linalg.norm(u)
            if gap(v) <= target:
                return q, np.zeros(3)
            lo, hi = 0.0, None
            for k in range(1, 61):  # towards the axis by 0.5 mm steps, up to the first contact
                if gap(v + k * 0.0005 * u) <= target:
                    lo, hi = (k - 1) * 0.0005, k * 0.0005
                    break
            if hi is None:
                return q, 0.03 * u
            for _ in range(5):
                mid = (lo + hi) / 2
                lo, hi = (mid, hi) if gap(v + mid * u) > target else (lo, mid)
            return q, hi * u

        alphas, prev = [0.0], 0.0
        for theta in thetas[1:]:
            if length is None:
                best = 0.7 * theta
            else:
                tub_t = self.pivot + qrot(quat(self.axis, [theta])[0], (tub - self.pivot)[None])[0]

                def err(alpha):
                    q, sh = placed(alpha)
                    a = self.pivot + qrot(q, (apex - self.pivot)[None])[0] + sh
                    return abs(np.linalg.norm(a - tub_t) - length)
                best = min(np.arange(prev, min(theta, prev + 3 * self.STEP) + 1e-9, 0.25), key=err)
            alphas.append(best)
            prev = best
        # The search is coarse (0.25 degree, and a noisy objective): smooth the angles so that the patella does
        # not jerk, then slide it back onto the femur at the smoothed angles.
        a = np.array(alphas)
        a = np.convolve(np.r_[[a[0]] * 2, a, [a[-1]] * 2], np.ones(5) / 5, "valid")
        a[0] = 0.0
        self.alphas = np.maximum.accumulate(a)
        self.shifts = np.array([placed(x)[1] for x in self.alphas])
        self.rest_gap = target
        self.worst = max(gap(self.pivot + qrot(quat(self.axis, [a])[0], pat - self.pivot) + sh)
                         for a, sh in zip(self.alphas, self.shifts))
        if self.worst > target + 0.001:
            raise RigError(f"{side} patella leaves the femur by {self.worst * 1000:.1f} mm")

    def gap(self, q, shift):
        """The gap between the femur and the patella turned by q and shifted by `shift` (m)."""
        return self._gap(self.pivot + qrot(np.asarray(q, float), self._pat - self.pivot) + shift)

    def __call__(self, knee):
        knee = np.clip(np.asarray(knee, float), 0, self.thetas[-1])
        alpha = np.interp(knee, self.thetas, self.alphas)
        shift = np.c_[[np.interp(knee, self.thetas, self.shifts[:, i]) for i in range(3)]].T
        return quat(self.axis, alpha), shift


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
