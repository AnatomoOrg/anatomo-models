"""Whole body (context model): every BodyParts3D 4.0 element file, grouped by its most specific FMA concept,
plus the 3.0 concepts listed in V3_ADDITIONS (muscles missing from 4.0).

System from the is-a tree (ancestor 'muscle organ', 'artery'...), English names as a fallback.
Uniform decimation to about TARGET triangles; small parts keep MIN_TRIS.
"""
import collections
import re

import trimesh

from anatomo_models import v3
from anatomo_models.model import clean, decimate

TARGET, MIN_TRIS = 1_500_000, 200

# Concepts that BodyParts3D 4.0 lacks and 3.0 has (face, mastication and abdominal wall muscles, latissimus
# dorsi...), with their system. Their whole 3.0 mesh is moved into the 4.0 frame by the displacement field of
# v3.py. Chosen by hand among the 141 non-composite 3.0-only concepts: the others duplicate 4.0 geometry
# (heads of flexor digitorum superficialis, bellies of digastric, hair, taeniae, cardiac vessels, eyeball...).
_M = "muscles"
V3_ADDITIONS = {
    # Face and scalp
    "FMA46759": _M, "FMA46760": _M,  # frontalis
    "FMA46761": _M, "FMA46762": _M,  # occipitalis
    "FMA46763": _M, "FMA46764": _M,  # temporoparietalis
    "FMA46768": _M,  # aponeurosis of epicranius (tendinous part of occipitofrontalis)
    "FMA46782": _M, "FMA46783": _M, "FMA46785": _M, "FMA46786": _M,  # orbital and palpebral parts of orbicularis oculi
    "FMA46796": _M, "FMA46797": _M,  # corrugator supercilii
    "FMA55610": _M, "FMA55611": _M,  # procerus
    "FMA55606": _M, "FMA55607": _M,  # nasalis
    "FMA55608": _M, "FMA55609": _M,  # depressor septi nasi
    "FMA46803": _M, "FMA46804": _M,  # levator labii superioris alaeque nasi
    "FMA46806": _M, "FMA46807": _M,  # levator labii superioris
    "FMA46812": _M, "FMA46813": _M, "FMA46814": _M, "FMA46815": _M,  # zygomaticus major and minor
    "FMA46823": _M, "FMA46824": _M,  # levator anguli oris
    "FMA46839": _M, "FMA46840": _M,  # risorius
    "FMA46841": _M,  # orbicularis oris
    "FMA46829": _M, "FMA46830": _M,  # depressor anguli oris
    "FMA46817": _M, "FMA46818": _M,  # depressor labii inferioris
    "FMA46826": _M, "FMA46827": _M,  # mentalis
    "FMA46835": _M, "FMA46836": _M,  # buccinator
    # Mastication
    "FMA49001": _M, "FMA49002": _M, "FMA49004": _M, "FMA49005": _M,  # superficial and deep parts of masseter
    "FMA49007": _M, "FMA49008": _M,  # temporalis
    "FMA49012": _M, "FMA49013": _M,  # medial pterygoid
    "FMA49022": _M, "FMA49023": _M, "FMA49024": _M, "FMA49025": _M,  # lower and upper heads of lateral pterygoid
    # Neck: 4.0 only has the left longus colli
    "FMA46283": _M, "FMA46285": _M, "FMA46287": _M,  # parts of right longus colli
    "FMA264840": _M,  # left intermediate tendon (of digastric): 4.0 only has the right one
    # Trunk
    "FMA13358": _M, "FMA13359": _M,  # latissimus dorsi
    "FMA13377": _M, "FMA13378": _M,  # rectus abdominis
    "FMA13892": _M, "FMA13893": _M,  # internal oblique
    "FMA22344": _M, "FMA22345": _M,  # transversus abdominis
    "FMA22346": _M, "FMA22347": _M,  # pyramidalis
    "FMA22348": _M, "FMA22349": _M,  # quadratus lumborum
    "FMA22878": _M, "FMA22879": _M,  # multifidus
    "FMA21964": "organes", "FMA21965": "organes",  # inguinal ligament (ligaments go to organes, see overrides.py)
    # Foot
    "FMA51142": _M, "FMA51143": _M,  # extensor digitorum brevis
    "FMA74140": _M, "FMA74141": _M,  # set of dorsal interossei of foot
    # Heart: 4.0 has the papillary muscles of the right ventricle and one head of the anterior one of the left
    "FMA7266": "organes",  # posterior papillary muscle of left ventricle
}

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


def structures(bp, fr_names, target=TARGET, additions=V3_ADDITIONS):
    groups = collections.defaultdict(list)
    for fid in sorted(bp.files):
        groups[bp.most_specific_owner(fid) or fid].append(fid)
    meshes = {}
    for key, fids in groups.items():
        m = clean(trimesh.util.concatenate([bp.load_v4(f) for f in fids]))
        if len(m.faces):
            meshes[key] = m
    swap_sides(bp, meshes)
    for key in sorted(additions):
        if key in meshes:
            raise SystemExit(f"{key} ({bp.v3_names.get(key)}) has a 4.0 mesh: remove it from V3_ADDITIONS")
        meshes[key] = v3.load(bp, key)
        side = re.search(r"\b(right|left)\b", bp.v3_names[key])
        if side and (meshes[key].centroid[0] < 0) != (side[1] == "right"):  # subject's right at negative x
            raise SystemExit(f"{key} ({bp.v3_names[key]}): 3.0 mesh on the wrong side")
    keep = min(1.0, target / sum(len(m.faces) for m in meshes.values()))
    out = []
    for key, m in sorted(meshes.items()):
        if key in additions:
            name, sys_, source = bp.v3_names[key], additions[key], "bodyparts3d-3.0"
        else:
            # The concept first, then the other owners of its files (some concepts only sit in the part-of tree).
            concepts = [key] + sorted({c for f in groups[key] for c in bp.owners.get(f, [])} - {key})
            name = bp.names.get(key, key)
            sys_, source = system(bp, concepts, name), "bodyparts3d-4.0"
        # `src` (full resolution) is only used to place the landmarks.
        out.append(dict(id=key, en=name, fr=fr_names.get(key), system=sys_,
                        mesh=decimate(m, max(MIN_TRIS, len(m.faces) * keep)), src=m, source=source))
    return out
