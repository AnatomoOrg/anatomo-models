"""Whole body (context model): every BodyParts3D 4.0 element file, grouped by its most specific FMA concept.

System from the is-a tree (ancestor 'muscle organ', 'artery'...), English names as a fallback.
Uniform decimation to about TARGET triangles; small parts keep MIN_TRIS.
"""
import collections
import re

import trimesh

from anatomo_models.model import clean, decimate

TARGET, MIN_TRIS = 1_500_000, 200

ROOTS = {"FMA72979": "peau", "FMA65132": "nerfs", "FMA50720": "arteres", "FMA50723": "veines",
         "FMA5022": "muscles", "FMA10474": "muscles", "FMA85453": "muscles", "FMA5018": "os", "FMA55107": "os"}
# FMA10474 'zone of muscle organ' (acromial part of deltoid...), FMA85453 'head of muscle organ' (long head of biceps...).
BY_NAME = (
    ("nerfs", r"nerve|ganglion|(?<!choroid )plexus|spinal cord"),
    ("veines", r"vein|venous|sinus|vena"),
    ("arteres", r"arter|aorta|arch of aorta|trunk$|palmar arch"),
    ("muscles", r"muscle|tendon|aponeurosis|abductor|adductor|flexor|extensor|levator|depressor|"
                r"sphincter|diaphragm|trapezius|pectoralis|rectus|vastus|lumbrical|interosse|coccygeus|puborectalis|"
                r"longus colli|aryepiglotticus|interspinales|intertransversarii"),
    ("os", r"bone|vertebra|\bribs?\b|sternum|manubrium|xiphoid|skull|phalanx|carpal|\b(meta)?tarsal(?! plate)|femur|\btibia\b|"
           r"fibula|patella|humerus|radius|ulna|"
           r"scapula|clavicle|sacrum|coccyx|mandible|maxilla|\bhyoid\b|cartilage|ilium|ischium|pubis|calcaneus|talus|"
           r"hamate|capitate|lunate|\btrapezi(um|oid)\b|pisiform|scaphoid|cuboid|cuneiform|navicular|sesamoid|tooth|incisor|"
           r"canine|molar|ossicle|malleus|incus|stapes|vomer|ethmoid bone|sphenoid bone|occipital bone|parietal bone|"
           r"temporal bone|frontal bone|nasal bone|lacrimal bone|palatine bone|zygomatic bone|nasal concha"),
)


def system(bp, concepts, name):
    s = next((s for c in concepts if (s := bp.ancestor_in(c, ROOTS))), None)
    if s:
        return s
    n = name.lower()
    return next((s for s, rx in BY_NAME if re.search(rx, n)), "organes")


def swap_sides(bp, meshes):
    """Swap the meshes of a right/left pair when both sit on the wrong side.

    BodyParts3D 4.0 attaches FJ1469M to 'right flexor pollicis brevis' although it lies in the left hand
    (and the reverse); same for the middle pharyngeal constrictor. The subject's right side is at negative x."""
    by_name = {bp.names.get(k, k): k for k in meshes}
    for name, key in sorted(by_name.items()):
        if not re.search(r"\bright\b", name):
            continue
        other = by_name.get(re.sub(r"\bright\b", "left", name))
        # 5 mm margin: midline structures split in halves have a centroid near x = 0.
        if other and meshes[key].centroid[0] > 5 and meshes[other].centroid[0] < -5:
            print(f"swapping misplaced meshes of {name!r} and its left counterpart")
            meshes[key], meshes[other] = meshes[other], meshes[key]


def structures(bp, fr_names, target=TARGET):
    groups = collections.defaultdict(list)
    for fid in sorted(bp.files):
        groups[bp.most_specific_owner(fid) or fid].append(fid)
    meshes = {}
    for key, fids in groups.items():
        m = clean(trimesh.util.concatenate([bp.load_v4(f) for f in fids]))
        if len(m.faces):
            meshes[key] = m
    swap_sides(bp, meshes)
    keep = min(1.0, target / sum(len(m.faces) for m in meshes.values()))
    out = []
    for key, m in sorted(meshes.items()):
        # The concept first, then the other owners of its files (some concepts only sit in the part-of tree).
        concepts = [key] + sorted({c for f in groups[key] for c in bp.owners.get(f, [])} - {key})
        name = bp.names.get(key, key)
        out.append(dict(id=key, en=name, fr=fr_names.get(key), system=system(bp, concepts, name),
                        mesh=decimate(m, max(MIN_TRIS, len(m.faces) * keep)), source="bodyparts3d-4.0"))
    return out
