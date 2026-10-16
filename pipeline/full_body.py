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
         "FMA5022": "muscles", "FMA5018": "os", "FMA55107": "os"}
BY_NAME = (
    ("nerfs", r"nerve|ganglion|plexus|spinal cord"),
    ("veines", r"vein|venous|sinus|vena"),
    ("arteres", r"arter|aorta|arch of aorta|trunk$|palmar arch"),
    ("muscles", r"muscle|tendon|aponeurosis|^\w+ (head|part) of|abductor|adductor|flexor|extensor|levator|depressor|"
                r"sphincter|diaphragm|-us$|pectoralis|rectus|vastus|lumbrical|interosse|coccygeus|puborectalis|"
                r"longus colli|aryepiglotticus|interspinales|intertransversarii"),
    ("os", r"bone|vertebra|rib|sternum|manubrium|xiphoid|skull|phalanx|carpal|tarsal|femur|tibia|fibula|patella|humerus|radius|ulna|"
           r"scapula|clavicle|sacrum|coccyx|mandible|maxilla|hyoid|cartilage|ilium|ischium|pubis|calcaneus|talus|"
           r"hamate|capitate|lunate|trapezi|pisiform|scaphoid|cuboid|cuneiform|navicular|sesamoid|tooth|incisor|"
           r"canine|molar|ossicle|malleus|incus|stapes|vomer|ethmoid|sphenoid|occipital|parietal|temporal bone|"
           r"frontal bone|nasal bone|lacrimal|palatine|zygomatic|concha"),
)


def system(bp, concepts, name):
    s = next((s for c in concepts if (s := bp.ancestor_in(c, ROOTS))), None)
    if s:
        return s
    n = name.lower()
    return next((s for s, rx in BY_NAME if re.search(rx, n)), "organes")


def structures(bp, fr_names, target=TARGET):
    groups = collections.defaultdict(list)
    for fid in sorted(bp.files):
        groups[bp.most_specific_owner(fid) or fid].append(fid)
    meshes = {}
    for key, fids in groups.items():
        m = clean(trimesh.util.concatenate([bp.load_v4(f) for f in fids]))
        if len(m.faces):
            meshes[key] = m
    keep = min(1.0, target / sum(len(m.faces) for m in meshes.values()))
    out = []
    for key, m in sorted(meshes.items()):
        # The concept first, then the other owners of its files (some concepts only sit in the part-of tree).
        concepts = [key] + sorted({c for f in groups[key] for c in bp.owners.get(f, [])} - {key})
        name = bp.names.get(key, key)
        out.append(dict(id=key, en=name, fr=fr_names.get(key), system=system(bp, concepts, name),
                        mesh=decimate(m, max(MIN_TRIS, len(m.faces) * keep)), source="bodyparts3d-4.0"))
    return out
