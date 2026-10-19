"""Open3DModel nerves of both limbs, on both sides, for the whole-body model.

BodyParts3D has no spinal nerves: the whole body gets the upper-limb nerves of open3d.py and the lower-limb
nerves of open3d_lower.py. Both Open3D exports only have the right side. For each limb:

- right side: the Open3D bones are registered on the right BodyParts3D 4.0 bones of the whole body by one
  similarity (ICP, open3d.fit, as for upper_limb), then each bone by its own rigid ICP (`refine`); the nerves
  follow a displacement field interpolated from the bones;
- left side: the whole OBJ is mirrored (x -> -x, faces reversed to keep outward normals), then registered
  on the left bones the same way: BodyParts3D is not exactly symmetrical, a mirror alone would be off;
- the nerves that stick out of the BodyParts3D skin are pushed under it (skin.py).

Ids and names per side: a right-sided FMA concept takes its left counterpart (`LEFT`, FMA ids checked
against the FMA, EBI OLS, October 2026) and "right" becomes "left" in the English name, which is where the
app reads the side. The FMA has no sided concept for the objects that group several nerves (`SIDED`): the
right side keeps the FMA id of the generic concept (the id used by upper_limb), the left side takes that id
with the suffix "-L", and the English name says the side ("set of anterior divisions of left brachial
plexus"). French names carry no side (docs/NOMS.md).
"""
import re

import numpy as np
import trimesh
from scipy.spatial import cKDTree

from . import open3d, open3d_lower, skin
from .model import ATTRIBUTION as BP3D_ATTRIBUTION
from .model import clean, decimate

KEEP, MIN_TRIS = 0.25, 150  # context model: decimate more than upper_limb (0.5); nerves stay round tubes
SOURCES = [open3d.SOURCE, open3d_lower.SOURCE]
LICENSE = open3d.LICENSE
ATTRIBUTION = (BP3D_ATTRIBUTION.removesuffix(" Modified by the Anatomo project.")
               + f" Nerves of the limbs: {open3d.CREDIT}; {open3d_lower.CREDIT}"
               " (https://creativecommons.org/licenses/by-sa/4.0/), derived from BodyParts3D and Z-Anatomy."
               + " Modified by the Anatomo project; this model is licensed under CC BY-SA 4.0"
               " (https://creativecommons.org/licenses/by-sa/4.0/).")

# Right bone of a registration table -> the same bone on the left (median bones map to themselves).
LEFT_BONES = {"FMA23130": "FMA23131", "FMA13395": "FMA13396", "FMA13322": "FMA13323", "FMA23464": "FMA23465",
              "FMA23467": "FMA23468", "FMA24435": "FMA24436", "FMA24437": "FMA24438", "FMA24439": "FMA24440",
              "FMA24441": "FMA24442", "FMA24443": "FMA24444", "FMA23725": "FMA24445", "FMA24446": "FMA24447",
              "FMA24448": "FMA24449", "FMA24464": "FMA24465", "FMA24466": "FMA24467", "FMA24468": "FMA24469",
              "FMA24470": "FMA24471", "FMA24472": "FMA24473", **open3d_lower.LEFT_BONES}

# Right-sided FMA concept -> its left counterpart (exact FMA label with "left" for "right").
LEFT = {"FMA8734": "FMA8735", "FMA8731": "FMA8732", "FMA8728": "FMA8729", "FMA8725": "FMA8726", "FMA6073": "FMA6072",
        "FMA65361": "FMA65362", "FMA65365": "FMA65366", "FMA65363": "FMA65364", "FMA45238": "FMA45239",
        "FMA45240": "FMA45241", "FMA45242": "FMA45243", "FMA65283": "FMA65284", "FMA65281": "FMA65282",
        "FMA65285": "FMA65286", "FMA66083": "FMA66084", "FMA65298": "FMA65297", "FMA65294": "FMA65295",
        "FMA65305": "FMA65306", "FMA65308": "FMA65309", "FMA37065": "FMA37066", "FMA39083": "FMA39084",
        "FMA37073": "FMA37074", "FMA305343": "FMA305345", "FMA305337": "FMA305339", "FMA37067": "FMA37068",
        "FMA65327": "FMA65328", "FMA291310": "FMA291312", "FMA44851": "FMA44852", "FMA37320": "FMA37321",
        "FMA65349": "FMA65350", "FMA292830": "FMA292832", "FMA44680": "FMA80210", "FMA44894": "FMA44932",
        "FMA65247": "FMA65248", "FMA39081": "FMA39082", "FMA37070": "FMA37071", "FMA44950": "FMA44951",
        "FMA44952": "FMA44953", "FMA39146": "FMA39147", "FMA292887": "FMA292889", "FMA65335": "FMA65336",
        # lower limb
        "FMA17673": "FMA17672", "FMA17675": "FMA17674", "FMA17678": "FMA17677", "FMA17680": "FMA17679",
        "FMA17682": "FMA17681", "FMA18068": "FMA18069", "FMA18070": "FMA18071", "FMA18072": "FMA18073",
        "FMA18075": "FMA18077", "FMA18079": "FMA18080", "FMA6438": "FMA6439", "FMA6259": "FMA6260",
        "FMA20674": "FMA20675", "FMA65536": "FMA65537", "FMA63660": "FMA63661", "FMA16491": "FMA16492",
        "FMA16493": "FMA16494", "FMA20632": "FMA20633", "FMA20634": "FMA20635", "FMA16497": "FMA16498",
        "FMA20588": "FMA20589", "FMA16499": "FMA16500", "FMA45253": "FMA45254", "FMA45263": "FMA45264",
        "FMA45326": "FMA45327", "FMA16501": "FMA16502", "FMA45308": "FMA45309", "FMA45310": "FMA45311",
        "FMA45313": "FMA45314", "FMA45344": "FMA45345", "FMA45346": "FMA45347", "FMA78706": "FMA78707",
        "FMA78712": "FMA78713", "FMA82933": "FMA82934", "FMA21863": "FMA21864", "FMA45338": "FMA45339",
        "FMA22111": "FMA22112", "FMA22109": "FMA22110", "FMA45422": "FMA45423", "FMA45424": "FMA45425",
        "FMA45426": "FMA45427", "FMA45428": "FMA45429", "FMA45432": "FMA45433", "FMA45434": "FMA45435",
        "FMA45450": "FMA45451", "FMA45458": "FMA45459", "FMA80018": "FMA80019", "FMA45357": "FMA45358",
        "FMA45361": "FMA45362", "FMA45363": "FMA45364", "FMA45365": "FMA45366", "FMA45367": "FMA45368",
        "FMA45387": "FMA45388", "FMA45395": "FMA45396", "FMA45389": "FMA45390"}

# Generic concepts (no sided FMA concept) -> English name with the side ({s}: right or left).
SIDED = {
    "FMA77549": "set of anterior divisions of {s} brachial plexus",
    "FMA77550": "set of posterior divisions of {s} brachial plexus",
    "FMA44840": "common palmar digital branch of {s} median nerve",
    "FMA44854": "proper palmar digital branch of {s} median nerve to {s} thumb",
    "FMA44853": "proper palmar digital branch of {s} median nerve",
    "FMA272344": "proper palmar digital branch of {s} ulnar nerve",
    "FMA75490": "set of dorsal digital branches of {s} radial nerve",
    "FMA75506": "set of muscular branches of {s} femoral nerve",
    "FMA75559": "set of medial crural cutaneous branches of {s} saphenous nerve",
    "FMA75468": "set of {s} superior clunial nerves",
    "FMA75470": "set of {s} inferior clunial nerves",
    "FMA75492": "set of {s} common plantar digital nerves",
    "FMA75493": "set of {s} proper plantar digital nerves",
    "FMA75491": "set of dorsal digital nerves of {s} foot",
}

# (label, OBJ file name, nerve table, registration bones)
LIMBS = (("upper limb", open3d.OBJ, open3d.NERVES, open3d.BONES),
         ("lower limb", open3d_lower.OBJ, open3d_lower.NERVES, open3d_lower.BONES))
# One similarity is not enough here. Lower limb: 6 mm RMS on the bones (the Open3D hip and knee are not posed
# like BodyParts3D's, the Open3D tibia is 2 cm shorter). Upper limb: 2.5 mm, but the 4.0 clavicle of the whole
# body sits 5 mm away from the 3.0 one of upper_limb, and the subclavian nerve ran through it. So each bone is
# then fitted by its own rigid ICP and the nerves follow a displacement field interpolated from the bones
# (like v3.py): a nerve follows the bones it runs along.
ANCHOR_POINTS, K, EPS = 400, 64, 25.0  # points per bone, nearest anchor points, softening (mm^2) of 1/d^2
MAX_SHIFT_MM = 25.0  # largest correction of the field over the similarity: beyond, the fit went wrong
# After the per-bone fits, the bones must match within open3d.MAX_RMS_MM overall and MAX_BONE_RMS_MM each:
# the Open3D tibia is shorter than BodyParts3D's (359 mm against 380 mm) and differs in shape (4.8 mm RMS).
MAX_BONE_RMS_MM = 5.5
# The Open3D subject is not BodyParts3D's: after registration, cutaneous nerves (clunial, lateral femoral
# cutaneous, cutaneous branches of the arm and forearm...) stick out of the BodyParts3D skin by up to 9 mm.
# They are pushed under it (skin.py): no nerve vertex closer than SKIN_MARGIN_MM to the outer surface.
SKIN, EYES = "FMA72979", ("FMA58239", "FMA58240", "FMA58271", "FMA58272",  # corneas, scleras
                          "FMA59089", "FMA59090", "FMA59091", "FMA59092")  # tarsal plates of the eyelids
SKIN_MARGIN_MM = 2.5


def sided(fid, en, side):
    """(id, English name) of a concept of a nerve table on one side ('right' or 'left')."""
    if fid in SIDED:
        return (fid if side == "right" else f"{fid}-L"), SIDED[fid].format(s=side)
    if not re.search(r"\bright\b", en):
        raise ValueError(f"{fid} ({en}): neither right-sided nor in SIDED")
    return (fid, en) if side == "right" else (LEFT[fid], re.sub(r"\bright\b", "left", en))


def mirror(mesh):
    """Mirror image through the median plane (x -> -x), faces reversed to keep their orientation."""
    return trimesh.Trimesh(np.asarray(mesh.vertices) * [-1.0, 1.0, 1.0], np.asarray(mesh.faces)[:, ::-1],
                           process=False)


def concepts(table):
    """{FMA id: (English name, French name, [objects])} of a nerve table (objects sharing a concept agree)."""
    out = {}
    for obj, (fid, en, fr) in table.items():
        c = out.setdefault(fid, (en, fr, []))
        assert c[:2] == (en, fr), fid
        c[2].append(obj)
    return out


class Field:
    """Displacement field from anchor points (n, 3) and their displacements (n, 3), 1/d^2 weights."""

    def __init__(self, points, shifts):
        self.points, self.shifts, self.tree = points, shifts, cKDTree(points)

    def __call__(self, v):
        d, i = self.tree.query(v, k=min(K, len(self.points)), workers=-1)
        w = 1.0 / (d ** 2 + EPS)
        return v + (w[..., None] * self.shifts[i]).sum(1) / w.sum(1, keepdims=True)


def _icp(a, target, iterations=50, trim=0.9):
    """Rigid trimmed ICP of points a onto target points, from the identity (a is already roughly in place).

    Returns (r, t, rms of all points in mm)."""
    tree = cKDTree(target)
    r, t, prev = np.eye(3), np.zeros(3), np.inf
    for _ in range(iterations):
        d, j = tree.query(a @ r.T + t)
        keep = d <= np.quantile(d, trim)
        r, t = open3d._umeyama(a[keep], target[j[keep]], False)
        err = np.sqrt(np.mean(d[keep] ** 2))
        if prev - err < 1e-6:
            break
        prev = err
    d, _ = tree.query(a @ r.T + t)
    return r, t, float(np.sqrt(np.mean(d ** 2)))


def refine(src, items, bones, m, t, log=print, label="open3d", to_frame=None):
    """Per-bone rigid ICP after the similarity (m, t); returns the displacement field of the bones.

    src: Open3D meshes (glTF frame, m); bones: {Open3D bone: model FMA id}. Points of a bone move by its own
    rigid fit; a bone that several objects map to (sacrum and coccyx) is fitted as one. to_frame: source vertices ->
    BodyParts3D axes in mm (default open3d.to_bp3d, from the glTF frame in metres)."""
    to_frame = to_frame or open3d.to_bp3d
    by_id = {x["id"]: x for x in items}
    rng = np.random.default_rng(0)
    points, shifts, report, sq, n = [], [], [], 0.0, 0
    for fid in dict.fromkeys(bones.values()):
        objs = [o for o, f in bones.items() if f == fid]
        a = np.concatenate([to_frame(src[o].vertices) for o in objs]) @ m.T + t
        x = by_id[fid]
        target = open3d._surface_points(x["src"] if x.get("src") is not None else x["mesh"])
        r, tt, rms = _icp(a, target)
        moved = a @ r.T + tt
        shift = np.linalg.norm(moved - a, axis=1).max()
        if rms > MAX_BONE_RMS_MM or shift > MAX_SHIFT_MM:
            raise SystemExit(f"{label}: bone {fid} rms {rms:.1f} mm, shift {shift:.0f} mm after per-bone ICP")
        sq, n = sq + rms ** 2 * len(a), n + len(a)
        k = rng.choice(len(a), min(ANCHOR_POINTS, len(a)), replace=False)
        points.append(a[k]); shifts.append(moved[k] - a[k])
        report.append(f"{'+'.join(o.removesuffix('.r') for o in objs)} {rms:.1f}/{shift:.0f}")
    rms = float(np.sqrt(sq / n))
    log(f"   per-bone ICP: bone rms {rms:.2f} mm; " + ", ".join(report) + " (rms, max shift; mm)")
    if rms > open3d.MAX_RMS_MM:
        raise SystemExit(f"{label}: bone rms {rms:.2f} mm after per-bone ICP")
    return Field(np.concatenate(points), np.concatenate(shifts))


def nerves(obj_dir, items, log=print):
    """Nerve structures of both limbs and both sides, registered on the whole-body bones.

    items: the whole-body structures (BodyParts3D frame, mm) with the bones of the registration tables.
    Returns structure dicts {id, en, fr, system, mesh, src, source} (BodyParts3D frame, mm)."""
    by_id = {x["id"]: x for x in items}
    if SKIN not in by_id:
        raise SystemExit("open3d nerves: the whole-body model has no skin to keep the nerves under")
    body = skin.Body(by_id[SKIN]["src"], [by_id[e]["src"] for e in EYES if e in by_id])
    out, pushed = [], []
    for label, obj, table, bones in LIMBS:
        meshes = open3d.read_obj(f"{obj_dir}/{obj}", list(table) + list(bones))
        for side in ("right", "left"):
            src = meshes if side == "right" else {k: mirror(v) for k, v in meshes.items()}
            targets = bones if side == "right" else {k: LEFT_BONES.get(f, f) for k, f in bones.items()}
            name = f"open3d {label} {side}"
            m, t, _ = open3d.fit(src, items, log, bones=targets, label=name, check=False)
            move = refine(src, items, targets, m, t, log, name)
            for fid, (en, fr, objs) in sorted(concepts(table).items()):
                sid, sen = sided(fid, en, side)
                parts = [trimesh.Trimesh(move(open3d.to_bp3d(src[o].vertices) @ m.T + t), src[o].faces, process=False)
                         for o in objs]
                full = clean(trimesh.util.concatenate(parts))
                v, n, most = skin.under_skin(full.vertices, body, SKIN_MARGIN_MM)
                if n:
                    full = trimesh.Trimesh(v, full.faces, process=False)
                    pushed.append((most, sen))
                mesh = decimate(full.copy(), max(MIN_TRIS, len(full.faces) * KEEP))
                out.append(dict(id=sid, en=sen, fr=fr, system="nerfs", mesh=mesh, src=full, source=open3d.SOURCE_ID))
    pushed.sort(reverse=True)
    log(f"open3d nerves: {len(pushed)} of {len(out)} pushed under the skin (body {body.volume:.0f} L), up to "
        + ", ".join(f"{d:.1f} mm ({en})" for d, en in pushed[:3]))
    # The subject's right is at negative x (BodyParts3D frame): a side mix-up would put a nerve across.
    for x in out:
        cx = x["src"].centroid[0]
        if (cx < 0) != bool(re.search(r"\bright\b", x["en"])):
            raise SystemExit(f"{x['id']} ({x['en']}) lies on the wrong side (centroid x {cx:.0f} mm)")
    return out
