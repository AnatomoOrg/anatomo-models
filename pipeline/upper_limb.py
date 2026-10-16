"""Right upper limb (the MVP model): bones, muscles, arteries and veins, one structure per FMA concept.

Selection by English FMA name (right side, one regex per system); each element file goes to the most
specific selected concept. Meshes come from BodyParts3D 3.0 "obj_95" when it has the concept (about
5x denser than 4.0: bones and most muscles), moved into the 4.0 frame; otherwise from 4.0 "obj_99"
(vessels), keeping only the files on the right side.
Known gaps: BodyParts3D has no upper-limb nerves; latissimus dorsi and trapezius are missing.
"""
import collections
import re

import numpy as np
import trimesh

from anatomo_models import landmarks
from anatomo_models.model import clean, decimate, to_gltf

KEEP, MIN_TRIS = 0.2, 3000  # ~470k triangles in total; small parts keep their full resolution

MUSCLES = (r"deltoid|biceps brachii|triceps brachii|brachialis|coracobrachialis|brachioradialis|anconeus|supinator|"
           r"pronator (teres|quadratus)|flexor carpi|extensor carpi|palmaris longus|flexor digitorum (superficialis|profundus)|"
           r"flexor pollicis|extensor pollicis|abductor pollicis|adductor pollicis|opponens|extensor digitorum(?! longus| brevis)|"
           r"extensor indicis|extensor digiti minimi|abductor digiti minimi of right hand|flexor digiti minimi brevis of right hand|"
           r"lumbrical.*hand|interosse.*hand|supraspinatus|infraspinatus|teres (major|minor)|subscapularis|pectoralis (major|minor)|"
           r"latissimus dorsi|serratus anterior|rhomboid|levator scapulae|subclavius")
NERVES = r"median nerve|ulnar nerve|radial nerve|musculocutaneous nerve|axillary nerve"
BONES = (r"clavicle|scapula|humerus|radius|ulna|scaphoid|lunate|triquetral|pisiform|trapezium|trapezoid|capitate|hamate|"
         r"metacarpal|phalanx of right (thumb|index|middle|ring|little)")
ARTERIES = (r"(axillary|brachial|deep brachial|radial|ulnar|(common |anterior |posterior )?interosseous) artery|"
            r"(superficial|deep) palmar (arterial )?arch")
VEINS = r"\b(cephalic|basilic|median cubital|median antebrachial|axillary|brachial|radial|ulnar) vein"
LOWER_LIMB = r"foot|toe|leg|femor|hallucis|tibial|thigh|hip"


def system(name):
    n = name.lower()
    if "right" not in n or "branch" in n:
        return None
    for s, rx in (("nerfs", NERVES), ("arteres", ARTERIES), ("veines", VEINS), ("muscles", MUSCLES), ("os", BONES)):
        # 'ulna', 'scapula', 'metacarpal' also occur in vessel names (ulnar recurrent artery...).
        if s == "os" and re.search(r"artery|vein|nerve", n):
            s = "arteres" if "artery" in n else "veines" if "vein" in n else None
            if not s:
                continue
        if re.search(rx, n) and not re.search(LOWER_LIMB, n):
            return s
    return None


def structures(bp, fr_names):
    # All element files of each concept, over both trees.
    owned = {}
    for tree in ("isa", "partof"):
        for c, files in bp.elements[tree][1].items():
            owned.setdefault(c, set()).update(files)
    groups, seen = {}, set()
    for tree in ("isa", "partof"):
        names, elems = bp.elements[tree]
        sel = {c: s for c in sorted(names) if (s := system(names[c]))}
        best = {}
        for c in sel:
            for f in sorted(elems[c]):
                if f not in best or len(elems[c]) < len(elems[best[f]]):
                    best[f] = c
        for f, c in sorted(best.items()):
            if f in seen:
                continue
            seen.add(f)
            groups.setdefault(names[c], dict(id=c, system=sel[c], files=[], owned=owned[c]))["files"].append(f)
    out, marks = [], []
    for name, g in sorted(groups.items()):
        # The 3.0 mesh covers the whole concept: use it only when no other group took part of the concept's
        # files (e.g. recurrent branches of the ulnar artery), or that geometry would be drawn twice.
        whole = set(g["files"]) >= g["owned"]
        m, source = (bp.load_v3(g["id"]) if whole else None), "bodyparts3d-3.0"
        if m is None:
            # The subject's right side is at negative x; drop element files from the other side.
            parts = [p for p in map(bp.load_v4, g["files"]) if p.bounds.mean(0)[0] < 0]
            if not parts:
                continue
            m, source = trimesh.util.concatenate(parts), "bodyparts3d-4.0"
        m = clean(m)
        m = decimate(m, max(MIN_TRIS, len(m.faces) * KEEP))
        out.append(dict(id=g["id"], en=name, fr=fr_names.get(g["id"]), system=g["system"], mesh=m, source=source))
        if g["id"] == landmarks.HUMERUS:
            for slug, fr, kind, p in landmarks.humerus(m.vertices * 0.001, m.vertex_normals):
                marks.append(dict(id=f"humerus.{slug}", structure=g["id"], fr=fr, kind=kind,
                                  position=np.round(to_gltf(p * 1000), 5).tolist()))
    # A missing or misnamed 3.0 archive would otherwise silently publish a ~5x coarser model.
    v3 = sum(x["source"] == "bodyparts3d-3.0" for x in out)
    if not any(x["id"] == landmarks.HUMERUS and x["source"] == "bodyparts3d-3.0" for x in out) or v3 < len(out) // 2:
        raise SystemExit(f"BodyParts3D 3.0 meshes missing: only {v3}/{len(out)} structures from 3.0 ({bp.v3})")
    return out, marks
