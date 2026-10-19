"""Dural venous sinuses, cranial nerves and nerves of the trunk from Z-Anatomy, geometry only, for the whole body.

Source: Z-Anatomy, "Models-of-human-anatomy" (Gauthier Kervyn, https://github.com/Z-Anatomy/Models-of-human-anatomy),
CC BY-SA 4.0: `Z-Anatomy.zip` at commit COMMIT, pinned by SHA-256 (pipeline/zanatomy.sha256) and fetched by
pipeline/fetch_zanatomy.sh, which only unpacks `Startup.blend` (Blender 3.5). The .blend is read as data by blend.py:
no Blender, nothing of the file is executed (the zip's Python add-on is never unpacked).

Licence and provenance. Z-Anatomy is CC BY-SA 4.0 as a whole, derived from BodyParts3D (CC BY-SA 2.1 JP), but its
README lists third-party models "used as reference/included and adapted", two of them non-commercial:
"Anatomy of the Inner Ear" (University of Dundee, CC BY-NC-SA 4.0; it holds the facial and vestibulocochlear nerves)
and "Kidney" (Lissie Cowley, CC BY-NC 4.0); "Brainder" and "White matter" (brain surfaces and tracts) have no
stated licence; "Cranial Nerves and Foramina" (University of Dundee, CAHID) is CC BY 4.0 per the README, CC BY-SA 4.0
on AnatomyTOOL (node/60433). Z-Anatomy does not mark provenance per object, so only the objects of `OBJECTS` are
read, an explicit whitelist:

- curves (Blender Bezier splines with a round bevel, drawn in Blender: not an import of a third-party mesh) of the
  dural sinuses, orbital veins, internal jugular vein and of cranial and trunk nerves; none of them lies in the ear
  or the kidney. The facial nerve, the chorda tympani and the vestibulocochlear nerve (cochlear and vestibular
  nerves), which run through the temporal bone where the non-commercial inner-ear model has them, are left out
  (`EXCLUDED`), as is everything of the ear, the kidney and the brain (surfaces, nuclei, tracts);
- three meshes found in none of the listed third-party models nor in BodyParts3D, hence Z-Anatomy's own work:
  the cavernous sinuses, the basilar venous plexus and the ganglia of the sympathetic trunks.

Frame. Z-Anatomy's world frame has BodyParts3D's axes, in metres, with its subject scaled by about 1.021 and moved
by about (0, -65, -106) mm. The objects are registered on the BodyParts3D 4.0 bones of the whole body like the
Open3DModel nerves (open3d_full_body.py): one similarity fitted by ICP on the skull, cervical and thoracic
vertebrae and ribs (`BONES`), then a rigid ICP per bone, the structures following the displacement field of the
bones. Splines are moved point by point, then swept into round tubes (their radius times the bevel depth): a tube
stays round whatever the field does.

Structures already in the model. BodyParts3D has the optic, trochlear and ophthalmic nerves whole: Z-Anatomy's are
not read. It has the branches of the oculomotor nerve and 4 cm of the internal jugular vein: the spline points of
Z-Anatomy's oculomotor nerve and jugular vein whose tube touches them are dropped (`TRIM`), each kept piece reaching
one point further, into the structure it continues. An object whose concept is already in the model (`MERGE`: internal
jugular veins, sympathetic trunks whose lumbo-sacral part comes from Open3DModel) is added to that structure's mesh
(source "<source>+z-anatomy").

Fixes of the source, each documented at its table: two sinuses placed 4.5 cm off by a stale parent offset
(`PARENT_FIX`), 7 mm left between sigmoid sinus and jugular vein (`BRIDGE`), thoracic sympathetic trunk stopping short
of Open3DModel's lumbar one (`BRIDGE_TO`), vagus nerves kept in the neck only (`CLIP_BELOW`).
"""
import re

import numpy as np
import trimesh

from . import open3d, open3d_full_body, skin
from .blend import Blend, tube
from .model import clean, decimate

BLEND = "Startup.blend"
COMMIT = "767f14e0a4dfc55aa7c3455685b62339a4faec99"
SOURCE_ID = "z-anatomy"
SOURCE = {"name": "Z-Anatomy, Models-of-human-anatomy (Startup.blend), geometry only",
          "url": f"https://github.com/Z-Anatomy/Models-of-human-anatomy/tree/{COMMIT}", "license": "CC-BY-SA-4.0"}
# Attribution requested by the Z-Anatomy README ("Please be sure attribute any content copied or derived ...").
CREDIT = '"Z-Anatomy - The libre 3D atlas of anatomy - CC-BY-SA 4.0" (Gauthier Kervyn, https://www.z-anatomy.com/)'

# Attribution of the whole-body model: BodyParts3D, Open3DModel (nerves of the limbs) and Z-Anatomy.
ATTRIBUTION = open3d_full_body.ATTRIBUTION.replace(
    " Modified by the Anatomo project;",
    f" Dural venous sinuses, cranial nerves and nerves of the trunk: {CREDIT}"
    " (https://creativecommons.org/licenses/by-sa/4.0/), derived from BodyParts3D. Modified by the Anatomo project;", 1)
assert ATTRIBUTION != open3d_full_body.ATTRIBUTION

SUBSURF = 1  # Blender modifier type id: the meshes of the cavernous sinuses, basilar plexus and ganglia have one
SAMPLE_MM = 1.5  # spacing of the tube sections along a spline
MAX_GAP_MM = 0.5  # largest gap left between the trimmed part of an object and the structure it continues

# Z-Anatomy bone object -> FMA id of the same bone in the whole-body model: the registration targets. The occipital
# bone of BodyParts3D 4.0 is the concept 'occipital part of head'. Z-Anatomy remodelled the temporal bones (their two
# sides are exact mirror images), which fit to about 3 mm; the other bones to 1-2 mm.
BONES = {
    "Frontal bone": "FMA52734", "Occipital bone": "FMA49187", "Sphenoid bone": "FMA52736",
    "Parietal bone.r": "FMA52788", "Parietal bone.l": "FMA52789", "Temporal bone.r": "FMA52738",
    "Temporal bone.l": "FMA52739", "Maxilla.r": "FMA53649", "Maxilla.l": "FMA53650",
    "Atlas (C1)": "FMA12519", "Axis (C2)": "FMA12520", "Vertebra C3": "FMA12521", "Vertebra C4": "FMA12522",
    "Vertebra C5": "FMA12523", "Vertebra C6": "FMA12524", "Vertebra C7": "FMA12525",
    "Vertebra T1": "FMA9165", "Vertebra T2": "FMA9187", "Vertebra T3": "FMA9209", "Vertebra T4": "FMA9248",
    "Vertebra T5": "FMA9922", "Vertebra T6": "FMA9945", "Vertebra T7": "FMA9968", "Vertebra T8": "FMA9991",
    "Vertebra T9": "FMA10014", "Vertebra T10": "FMA10037", "Vertebra T11": "FMA10059", "Vertebra T12": "FMA10081",
    "Vertebra L1": "FMA13072", "Vertebra L2": "FMA13073",
    "Manubrium of sternum": "FMA7486", "Body of sternum": "FMA7487",
    "First rib.r": "FMA7857", "Second rib.r": "FMA7882", "Third rib.r": "FMA7909", "Fourth rib.r": "FMA7957",
    "Fifth rib.r": "FMA8066", "Sixth rib.r": "FMA8175", "Seventh rib.r": "FMA8229", "Eighth rib.r": "FMA8283",
    "Ninth rib.r": "FMA8364", "Tenth rib.r": "FMA8445", "Eleventh rib.r": "FMA8531", "Twelfth rib.r": "FMA8533",
    "First rib.l": "FMA7987", "Second rib.l": "FMA8012", "Third rib.l": "FMA8039", "Fourth rib.l": "FMA8148",
    "Fifth rib.l": "FMA8093", "Sixth rib.l": "FMA8202", "Seventh rib.l": "FMA8256", "Eighth rib.l": "FMA8310",
    "Ninth rib.l": "FMA8391", "Tenth rib.l": "FMA8472", "Eleventh rib.l": "FMA8532", "Twelfth rib.l": "FMA8534",
}

_V, _N = "veines", "nerfs"
# Whitelisted Z-Anatomy object -> (id, English name, French name, system). FMA ids and labels checked against the FMA
# (EBI OLS, October 2026). Sided concepts: the FMA's right and left concepts. The FMA has no sided concept for the
# sets (intercostal nerves, communicating branches): as for the Open3DModel nerves, the right side takes the FMA id
# of the set and the left side that id with "-L", the English name carrying the side. French names carry no side.
OBJECTS = {
    # Dural venous sinuses
    "Superior sagittal sinus": ("FMA50767", "superior sagittal sinus", "Sinus sagittal supérieur", _V),
    "Inferior sagittal sinus": ("FMA50768", "inferior sagittal sinus", "Sinus sagittal inférieur", _V),
    "Straight sinus": ("FMA50769", "straight sinus", "Sinus droit", _V),
    "Occipital sinus": ("FMA50781", "occipital sinus", "Sinus occipital", _V),
    "Transverse sinus.r": ("FMA50764", "right transverse sinus", "Sinus transverse", _V),
    "Transverse sinus.l": ("FMA50765", "left transverse sinus", "Sinus transverse", _V),
    "Sigmoid sinus.r": ("FMA51293", "right sigmoid sinus", "Sinus sigmoïde", _V),
    "Sigmoid sinus.l": ("FMA51294", "left sigmoid sinus", "Sinus sigmoïde", _V),
    "Superior petrosal sinus.r": ("FMA51289", "right superior petrosal sinus", "Sinus pétreux supérieur", _V),
    "Superior petrosal sinus.l": ("FMA51290", "left superior petrosal sinus", "Sinus pétreux supérieur", _V),
    "Inferior petrosal sinus.r": ("FMA51291", "right inferior petrosal sinus", "Sinus pétreux inférieur", _V),
    "Inferior petrosal sinus.l": ("FMA51292", "left inferior petrosal sinus", "Sinus pétreux inférieur", _V),
    "Cavernous sinus.r": ("FMA51402", "right cavernous sinus", "Sinus caverneux", _V),
    "Cavernous sinus.l": ("FMA51403", "left cavernous sinus", "Sinus caverneux", _V),
    "Anterior intercavernous sinus": ("FMA50774", "anterior intercavernous sinus", "Sinus intercaverneux antérieur", _V),
    "Posterior intercavernous sinus": ("FMA50775", "posterior intercavernous sinus",
                                       "Sinus intercaverneux postérieur", _V),
    "Basilar venous plexus": ("FMA50783", "basilar venous plexus", "Plexus basilaire", _V),
    # Orbital veins (drain into the cavernous sinus)
    "Superior ophthalmic vein.r": ("FMA51248", "right superior ophthalmic vein", "Veine ophtalmique supérieure", _V),
    "Superior ophthalmic vein.l": ("FMA51249", "left superior ophthalmic vein", "Veine ophtalmique supérieure", _V),
    "Inferior ophthalmic vein.r": ("FMA51250", "right inferior ophthalmic vein", "Veine ophtalmique inférieure", _V),
    "Inferior ophthalmic vein.l": ("FMA51251", "left inferior ophthalmic vein", "Veine ophtalmique inférieure", _V),
    # Internal jugular vein, from the jugular foramen: continues the 4 cm of BodyParts3D (MERGE)
    "Internal jugular vein.r": ("FMA4754", "right internal jugular vein", "Veine jugulaire interne", _V),
    "Internal jugular vein.l": ("FMA4762", "left internal jugular vein", "Veine jugulaire interne", _V),
    # Cranial nerves. Not VII and VIII (see EXCLUDED); not II, IV and the ophthalmic nerve either: BodyParts3D has them
    # whole (optic nerve to the chiasm, trochlear nerve to the midbrain, ophthalmic nerve from the orbit to the
    # trigeminal ganglion), and Z-Anatomy's run up to 6 mm beside them, with branches drawn 16 mm away from
    # BodyParts3D's: they would be doubled. Nor the meningeal branch of the maxillary nerve, which Z-Anatomy draws
    # partly outside the skull (one of its three splines lies entirely outside the parietal bone).
    "Olfactory nerve (I).r": ("FMA52592", "right olfactory nerve", "Nerf olfactif", _N),
    "Olfactory nerve (I).l": ("FMA52593", "left olfactory nerve", "Nerf olfactif", _N),
    "Oculomotor nerve (III).r": ("FMA50879", "right oculomotor nerve", "Nerf oculomoteur", _N),
    "Oculomotor nerve (III).l": ("FMA50880", "left oculomotor nerve", "Nerf oculomoteur", _N),
    "Trigeminal nerve (V).r": ("FMA50884", "right trigeminal nerve", "Nerf trijumeau", _N),
    "Trigeminal nerve (V).l": ("FMA50885", "left trigeminal nerve", "Nerf trijumeau", _N),
    "Maxillary nerve.r": ("FMA52725", "right maxillary nerve", "Nerf maxillaire", _N),
    "Maxillary nerve.l": ("FMA52726", "left maxillary nerve", "Nerf maxillaire", _N),
    # Z-Anatomy draws the mandibular nerve as its two trunks ("divisions").
    "Anterior division of mandibular nerve.r": ("FMA53062", "anterior trunk of right mandibular nerve",
                                                "Tronc antérieur du nerf mandibulaire", _N),
    "Anterior division of mandibular nerve.l": ("FMA53063", "anterior trunk of left mandibular nerve",
                                                "Tronc antérieur du nerf mandibulaire", _N),
    "Posterior division of mandibular nerve.r": ("FMA53064", "posterior trunk of right mandibular nerve",
                                                 "Tronc postérieur du nerf mandibulaire", _N),
    "Posterior division of mandibular nerve.l": ("FMA53065", "posterior trunk of left mandibular nerve",
                                                 "Tronc postérieur du nerf mandibulaire", _N),
    "Buccal nerve.r": ("FMA53067", "right buccal nerve", "Nerf buccal", _N),
    "Buccal nerve.l": ("FMA53068", "left buccal nerve", "Nerf buccal", _N),
    "Lingual nerve.r": ("FMA53219", "right lingual nerve", "Nerf lingual", _N),
    "Lingual nerve.l": ("FMA53220", "left lingual nerve", "Nerf lingual", _N),
    "Inferior alveolar nerve.r": ("FMA53244", "right inferior alveolar nerve", "Nerf alvéolaire inférieur", _N),
    "Inferior alveolar nerve.l": ("FMA53245", "left inferior alveolar nerve", "Nerf alvéolaire inférieur", _N),
    "Nerve to mylohyoid muscle.r": ("FMA53248", "right mylohyoid nerve", "Nerf mylohyoïdien", _N),
    "Nerve to mylohyoid muscle.l": ("FMA53249", "left mylohyoid nerve", "Nerf mylohyoïdien", _N),
    "Mental nerve.r": ("FMA53251", "right mental nerve", "Nerf mentonnier", _N),
    "Mental nerve.l": ("FMA53252", "left mental nerve", "Nerf mentonnier", _N),
    "Abducens nerve (VI).r": ("FMA50886", "right abducens nerve", "Nerf abducens", _N),
    "Abducens nerve (VI).l": ("FMA50887", "left abducens nerve", "Nerf abducens", _N),
    "Glossopharyngeal nerve (IX).r": ("FMA50892", "right glossopharyngeal nerve", "Nerf glossopharyngien", _N),
    "Glossopharyngeal nerve (IX).l": ("FMA50894", "left glossopharyngeal nerve", "Nerf glossopharyngien", _N),
    "Vagus nerve (X).r": ("FMA6219", "right vagus nerve", "Nerf vague", _N),
    "Vagus nerve (X).l": ("FMA6220", "left vagus nerve", "Nerf vague", _N),
    "Accessory nerve (XI).r": ("FMA50897", "right spinal accessory nerve", "Nerf accessoire", _N),
    "Accessory nerve (XI).l": ("FMA50899", "left spinal accessory nerve", "Nerf accessoire", _N),
    "Hypoglossal nerve (XII).r": ("FMA50901", "right hypoglossal nerve", "Nerf hypoglosse", _N),
    "Hypoglossal nerve (XII).l": ("FMA50903", "left hypoglossal nerve", "Nerf hypoglosse", _N),
    # Nerves of the trunk
    "Intercostal nerves.r": ("FMA75467", "set of right intercostal nerves", "Nerfs intercostaux", _N),
    "Intercostal nerves.l": ("FMA75467-L", "set of left intercostal nerves", "Nerfs intercostaux", _N),
    # Cervical and thoracic parts, added to the lumbo-sacral part of Open3DModel (MERGE); with its ganglia.
    "Sympathetic trunk.r": ("FMA6259", "right sympathetic trunk", "Tronc sympathique", _N),
    "Ganglia of sympathetic trunk.r": ("FMA6259", "right sympathetic trunk", "Tronc sympathique", _N),
    "Sympathetic trunk.l": ("FMA6260", "left sympathetic trunk", "Tronc sympathique", _N),
    "Ganglia of sympathetic trunk.l": ("FMA6260", "left sympathetic trunk", "Tronc sympathique", _N),
    "Sympathetic nerves.r": ("FMA75599", "set of communicating branches of right sympathetic trunk with spinal nerves",
                             "Rameaux communicants", _N),
    "Sympathetic nerves.l": ("FMA75599-L", "set of communicating branches of left sympathetic trunk with spinal nerves",
                             "Rameaux communicants", _N),
}
# The meshes among them (the others are curves).
MESHES = {"Cavernous sinus.r", "Cavernous sinus.l", "Basilar venous plexus", "Ganglia of sympathetic trunk.r",
          "Ganglia of sympathetic trunk.l"}
# Never read, whatever the tables say: provenance not established as CC BY-SA compatible (see the module docstring).
EXCLUDED = re.compile(r"facial nerve|chorda tympani|vestibul|cochle|tympan|\bear\b|auditory|semicircular|ossicle|"
                      r"malleus|incus|stapes|kidney|renal|nephr|white matter|tract\b|nucleus|nuclei|gyrus|sulcus|"
                      r"cortex|hemisphere", re.I)

# Parts of objects left out, as a height in Z-Anatomy's world frame (m) below which spline points are dropped. The vagus
# nerves of Z-Anatomy are reliable in the neck only: below the root of the neck, the left one turns back towards the
# vertebral column and stops at T2, and the right one runs down to the stomach where it carries the anterior gastric
# branches, on the left side (those come from the left vagus). Only their cervical part (down to the first ribs) is kept.
CLIP_BELOW = {"Vagus nerve (X).r": 1.42, "Vagus nerve (X).l": 1.42}
# Objects that Z-Anatomy draws in the wrong place: their parent offset (parent's world matrix times their parent inverse
# matrix) is 44.5 mm along y instead of the identity of every other whitelisted object, which puts the straight sinus
# 4.5 cm in front of the confluence of sinuses (it then ends in the middle cranial fossa) and the occipital sinus inside
# the posterior cranial fossa. Without that offset, the straight sinus runs from the end of the inferior sagittal sinus
# to the confluence, and the occipital sinus from the confluence down to the foramen magnum. Their parent offset is
# dropped; read() checks that every other object has none.
PARENT_FIX = {"Straight sinus", "Occipital sinus"}
# Object -> object whose nearest spline end its nearest spline end is extended to: Z-Anatomy leaves 7 mm between the
# sigmoid sinus and the internal jugular vein (the jugular bulb).
BRIDGE = {"Internal jugular vein.r": "Sigmoid sinus.r", "Internal jugular vein.l": "Sigmoid sinus.l"}
# Existing structures an object continues: its spline points whose tube touches them are dropped.
TRIM = {
    "Internal jugular vein.r": ("FMA4754", "FMA4751"), "Internal jugular vein.l": ("FMA4762", "FMA4761"),
    # BodyParts3D has the superior and inferior branches of the oculomotor nerve, and the ciliary ganglion.
    "Oculomotor nerve (III).r": ("FMA52574", "FMA52576", "FMA53549"),
    "Oculomotor nerve (III).l": ("FMA52575", "FMA52577", "FMA53550"),
}
# Object -> structure of the model its nearest spline end is extended to (the nearest point of its surface, after
# registration): the thoracic sympathetic trunk of Z-Anatomy stops 1 cm from the lumbar one of Open3DModel.
BRIDGE_TO = {"Sympathetic trunk.r": "FMA6259", "Sympathetic trunk.l": "FMA6260"}
# Concepts already in the model (BodyParts3D, Open3DModel) that Z-Anatomy completes: its geometry is added to theirs.
MERGE = {"FMA4754", "FMA4762", "FMA6259", "FMA6260"}
SKIN, EYES, SKIN_MARGIN_MM = open3d_full_body.SKIN, open3d_full_body.EYES, open3d_full_body.SKIN_MARGIN_MM


def to_mm(v):
    """Z-Anatomy world frame (m, BodyParts3D axes) -> BodyParts3D axes in mm (before registration)."""
    return np.asarray(v, float) * 1000.0


def concepts():
    """{id: (English name, French name, system, [objects])}; objects sharing an id agree on its names."""
    out = {}
    for obj, (fid, en, fr, sys_) in OBJECTS.items():
        c = out.setdefault(fid, (en, fr, sys_, []))
        assert c[:3] == (en, fr, sys_), fid
        c[3].append(obj)
    return out


def read(blend, name):
    """Geometry of a whitelisted object in Z-Anatomy's world frame (m): ('mesh', vertices, faces) or
    ('curve', [(points, radii)]) with the radius of the swept circle at each point."""
    if name not in OBJECTS and name not in BONES:
        raise ValueError(f"{name}: not whitelisted")
    if EXCLUDED.search(name):
        raise ValueError(f"{name}: excluded (provenance)")
    objs = blend.objects()
    typ, data, mat, mods, parent = blend.object_info(objs[name])
    if parent:
        off = blend.block(parent)[0]
        pinv = np.frombuffer(blend.buf, "<f4", 16, blend.field_off("Object", objs[name], "parentinv"))
        offset = blend.object_info(off)[2] @ pinv.reshape(4, 4).T.astype(float)
        fixed = name in PARENT_FIX
        if fixed == np.allclose(offset, np.eye(4), atol=1e-4):
            raise ValueError(f"{name}: parent offset {np.round(offset[:3, 3] * 1000, 1)} mm, expected "
                             + ("one" if fixed else "none"))
        if fixed:
            mat = np.linalg.inv(offset) @ mat
    allowed = {SUBSURF} if name in MESHES else set()
    if set(mods) - allowed:
        raise ValueError(f"{name}: unexpected modifiers {mods}")
    if typ == 1:
        v, f = blend.mesh(blend.block(data)[0])
        v = v @ mat[:3, :3].T + mat[:3, 3]
        if SUBSURF in mods:  # Blender shows a Catmull-Clark surface: smooth the cage like it (Loop subdivision),
            n = len(f)       # then back to about the cage's triangle count
            v, f = trimesh.remesh.subdivide_loop(v, f, iterations=1)
            sm = decimate(clean(trimesh.Trimesh(v, f, process=False)), n * 1.5)
            v, f = sm.vertices, sm.faces
        return "mesh", v, f
    if typ == 2 and name not in MESHES:
        scale = np.cbrt(abs(np.linalg.det(mat[:3, :3])))
        splines, depth = blend.splines(blend.block(data)[0])
        out = [(p @ mat[:3, :3].T + mat[:3, 3], r * depth * scale) for p, r, _ in splines]
        if name in CLIP_BELOW:
            out = [run for p, r in out for run in runs(p, r, p[:, 2] >= CLIP_BELOW[name]) if len(run[0]) > 1]
        return "curve", out
    raise ValueError(f"{name}: object type {typ} unexpected")


def resample(points, radii, step):
    """Points every `step` along a polyline (ends kept), with interpolated radii."""
    s = np.r_[0, np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))]
    if s[-1] == 0:
        return points[:1], radii[:1]
    t = np.linspace(0, s[-1], max(2, int(np.ceil(s[-1] / step)) + 1))
    return np.stack([np.interp(t, s, points[:, k]) for k in range(3)], 1), np.interp(t, s, radii)


def sides(radius_mm):
    """Sides of a tube: fine nerves do with 6, sinuses and veins get up to 12."""
    return 6 if radius_mm < 0.75 else 8 if radius_mm < 2 else 12


def runs(points, radii, keep):
    """Pieces of a polyline where `keep` is true, each with one more point on each side where it was cut."""
    out, i = [], 0
    while i < len(points):
        if not keep[i]:
            i += 1
            continue
        j = i
        while j < len(points) and keep[j]:
            j += 1
        a, b = max(0, i - 1), min(len(points), j + 1)
        out.append((points[a:b], radii[a:b]))
        i = j
    return out


def runs_outside(points, radii, meshes):
    """Pieces of a polyline whose tube does not touch one of `meshes` (closed trimeshes): points inside a mesh or
    closer to its surface than their radius are dropped.

    Each kept piece takes one more point on each side where it was cut, so it reaches the structure it continues.
    Returns [(points, radii)]."""
    inside = np.zeros(len(points), bool)
    for m in meshes:
        lo, hi = m.bounds
        near = np.all((points >= lo - radii[:, None] - 1) & (points <= hi + radii[:, None] + 1), axis=1)
        if not near.any():
            continue
        depth = np.full(len(points), -np.inf)
        depth[near] = trimesh.proximity.signed_distance(m, points[near])  # > 0 inside
        inside |= depth > -radii
    return runs(points, radii, ~inside)


def bridge(splines, others):
    """Splines with the end nearest to an end of `others` extended to that end (same radius)."""
    ends = np.array([p[k] for p, _ in others for k in (0, -1)])
    best = min(((np.linalg.norm(ends - p[k], axis=1).min(), i, k) for i, (p, _) in enumerate(splines) for k in (0, -1)))
    _, i, k = best
    p, r = splines[i]
    target = ends[np.argmin(np.linalg.norm(ends - p[k], axis=1))]
    p, r = (np.vstack([target, p]), np.r_[r[0], r]) if k == 0 else (np.vstack([p, target]), np.r_[r, r[-1]])
    return splines[:i] + [(p, r)] + splines[i + 1:]


def _tubes(polylines):
    vs, fs, n = [], [], 0
    for p, r in polylines:
        if len(p) < 2:
            continue
        v, f = tube(p, r, sides=sides(float(np.median(r))))
        vs.append(v); fs.append(f + n); n += len(v)
    if not vs:
        return None
    return clean(trimesh.Trimesh(np.concatenate(vs), np.concatenate(fs), process=False))


def register(blend_path, items, log=print):
    """Whitelisted geometry of Z-Anatomy ({object: read() result}, Z-Anatomy frame), the function that places Z-Anatomy
    points on the whole-body bones (BodyParts3D frame, mm) and the scale of the similarity."""
    blend = Blend(blend_path)
    try:
        bones = {}
        for name in BONES:
            _, v, f = read(blend, name)
            bones[name] = trimesh.Trimesh(v, f, process=False)
        geo = {name: read(blend, name) for name in OBJECTS}
    finally:
        blend.close()
    for obj, other in BRIDGE.items():
        geo[obj] = ("curve", bridge(geo[obj][1], geo[other][1]))
    m, t, _ = open3d.fit(bones, items, log, bones=BONES, label="z-anatomy", check=False, to_frame=to_mm)
    move = open3d_full_body.refine(bones, items, BONES, m, t, log, "z-anatomy", to_frame=to_mm)
    place = lambda v: move(to_mm(v) @ m.T + t)  # noqa: E731
    return geo, place, float(np.cbrt(np.linalg.det(m)))


def structures(blend_path, items, log=print):
    """Z-Anatomy structures registered on the whole-body bones, and the existing structures they complete.

    items: the whole-body structures (BodyParts3D frame, mm), with the bones of `BONES`, the skin and the structures
    of `TRIM` and `MERGE`. Merged geometry is added to those items in place (their `src`, `mesh` and `source`).
    Returns the new structure dicts {id, en, fr, system, mesh, src, source} (BodyParts3D frame, mm)."""
    by_id = {x["id"]: x for x in items}
    if missing := sorted((MERGE | {f for t in TRIM.values() for f in t} | set(BRIDGE_TO.values()) | {SKIN})
                         - set(by_id)):
        raise SystemExit(f"z-anatomy: structures missing from the model: {missing}")
    geo, place, scale = register(blend_path, items, log)
    body = skin.Body(by_id[SKIN]["src"], [by_id[e]["src"] for e in EYES if e in by_id])
    out, pushed, trimmed = {}, [], []
    for fid, (en, fr, sys_, objs) in concepts().items():
        parts = []
        for obj in objs:
            g = geo[obj]
            if g[0] == "mesh":
                parts.append(trimesh.Trimesh(place(g[1]), g[2], process=False))
                continue
            polys = []
            for p, r in g[1]:
                p, r = resample(place(p), r * 1000.0 * scale, SAMPLE_MM)
                polys.append((p, r))
            if obj in BRIDGE_TO:
                target = by_id[BRIDGE_TO[obj]]["src"]
                ends = [(trimesh.proximity.closest_point(target, p[[0, -1]])[1][k], i, k)
                        for i, (p, _) in enumerate(polys) for k in (0, 1)]
                _, i, k = min(ends)
                p, r = polys[i]
                q = trimesh.proximity.closest_point(target, p[[-k]])[0]
                polys[i] = (np.vstack([p, q]), np.r_[r, r[-1]]) if k else (np.vstack([q, p]), np.r_[r[0], r])
                log(f"z-anatomy: {obj} extended by {min(ends)[0]:.1f} mm to {by_id[BRIDGE_TO[obj]]['en']}")
            if obj in TRIM:
                targets = [by_id[f]["src"] for f in TRIM[obj]]
                before = sum(len(p) for p, _ in polys)
                polys = [run for p, r in polys for run in runs_outside(p, r, targets)]
                trimmed.append(f"{obj} {1 - sum(len(p) for p, _ in polys) / before:.0%}")
            if (tb := _tubes(polys)) is not None:
                parts.append(tb)
        if not parts:
            raise SystemExit(f"z-anatomy: nothing left of {objs} after trimming")
        full = clean(trimesh.util.concatenate(parts))
        if sys_ == _N:  # nerves stay under the skin (cutaneous ends of the intercostal nerves...)
            v, n, most = skin.under_skin(full.vertices, body, SKIN_MARGIN_MM)
            if n:
                full = trimesh.Trimesh(v, full.faces, process=False)
                pushed.append((most, en))
        out[fid] = dict(id=fid, en=en, fr=fr, system=sys_, mesh=full.copy(), src=full, source=SOURCE_ID)
    log("z-anatomy trimmed (share of spline points touching the structure continued): " + ", ".join(trimmed))
    pushed.sort(reverse=True)
    log(f"z-anatomy: {len(pushed)} nerves pushed under the skin"
        + (", up to " + ", ".join(f"{d:.1f} mm ({en})" for d, en in pushed[:3]) if pushed else ""))
    new = []
    for fid, x in out.items():
        if fid in MERGE:
            old = by_id[fid]
            if old["en"] != x["en"] or old["system"] != x["system"]:
                raise SystemExit(f"z-anatomy: {fid} is {old['en']!r} ({old['system']}) in the model, not {x['en']!r}")
            old["src"] = clean(trimesh.util.concatenate([old["src"], x["src"]]))
            old["mesh"] = clean(trimesh.util.concatenate([old["mesh"], x["mesh"]]))
            old["source"] = f"{old['source']}+{SOURCE_ID}"
            old["fr"] = x["fr"] if old["source"].startswith("open3dmodel") else old["fr"]
            continue
        if fid in by_id:
            raise SystemExit(f"z-anatomy: {fid} ({x['en']}) is already in the model and not in MERGE")
        new.append(x)
    if stale := MERGE - set(out):
        raise SystemExit(f"z-anatomy: MERGE entries without object: {sorted(stale)}")
    # The subject's right is at negative x (BodyParts3D frame): a side mix-up would put a structure across.
    for x in list(out.values()):
        side = re.search(r"\b(right|left)\b", x["en"])
        cx = x["src"].centroid[0]
        if side and (cx < 0) != (side[1] == "right"):
            raise SystemExit(f"z-anatomy: {x['id']} ({x['en']}) lies on the wrong side (centroid x {cx:.0f} mm)")
    return new
