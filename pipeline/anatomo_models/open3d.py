"""Upper-limb nerves from the Open3DModel (AnatomyTOOL; Leiden, Radboud...), geometry only.

Source: the "upper limb" OBJ export of the Open3DModel project, CC BY-SA 4.0, fetched by
pipeline/fetch_open3d.sh and pinned by SHA-256 (pipeline/open3d.sha256). That OBJ has no colours,
materials or textures; the textures of the Blender and glb exports are CC BY-NC-SA and are never
downloaded nor used.

The OBJ is in metres, +Y up, +Z anterior, subject's left at +X (the glTF frame of our models), and
only has the right side. Its subject sits about 12 cm away from BodyParts3D (Open3DModel descends
from BodyParts3D through Z-Anatomy, with remodelled bones): the nerves are moved onto the
BodyParts3D bones of the upper_limb model by one similarity transform (rotation, translation and a
uniform scale of about 0.97), fitted by ICP between the bones present in both models (`BONES`).

Open3D object names are not FMA names: `NERVES` maps each nerve object to an FMA concept, its FMA
English name and a French name (international anatomical terminology). Objects that share a
concept are merged into one structure.
"""
import numpy as np
import trimesh
from scipy.spatial import cKDTree

from .model import ATTRIBUTION as BP3D_ATTRIBUTION
from .model import BP3D_TO_GLTF, clean, decimate

OBJ = "upper-limb.obj"
SOURCE_ID = "open3dmodel"
SOURCE = {"name": "Open3DModel, upper limb (AnatomyTOOL), geometry only",
          "url": "https://anatomytool.org/node/63906", "license": "CC-BY-SA-4.0"}
# A model with these nerves combines BodyParts3D (CC BY-SA 2.1 JP, which allows a later version of the
# licence for adaptations, art. 5(2)) and Open3DModel (CC BY-SA 4.0): it is published under CC BY-SA 4.0.
LICENSE = {"id": "CC-BY-SA-4.0", "url": "https://creativecommons.org/licenses/by-sa/4.0/"}
# Credit line requested by AnatomyTOOL for the upper-limb model (https://anatomytool.org/node/63906).
CREDIT = ('"Open3DModel - Upper limb - English labels" at AnatomyTOOL.org by Open3D project, Jan Kooloos, '
          'RadboudUMC, Eungyeol Lee, LUMC et al, license: Creative Commons Attribution-ShareAlike')
ATTRIBUTION = (BP3D_ATTRIBUTION.removesuffix(" Modified by the Anatomo project.")
               + f" Nerves: {CREDIT} (https://creativecommons.org/licenses/by-sa/4.0/),"
               " derived from BodyParts3D and Z-Anatomy."
               + " Modified by the Anatomo project; this model is licensed under CC BY-SA 4.0"
               " (https://creativecommons.org/licenses/by-sa/4.0/).")
KEEP, MIN_TRIS = 0.5, 300  # nerves are thin tubes: decimate less than muscles
MAX_RMS_MM = 4.0  # the build fails if the bones do not fit better than this after registration

# Open3D bone object -> FMA id of the same bone in the upper_limb model: the registration targets.
# Open3DModel is about 3 % larger than BodyParts3D, so the transform is a similarity (rotation,
# translation, uniform scale). Fitted on the shoulder and arm bones only, the scale drifts and the hand
# ends up centimetres away: the carpal and metacarpal bones hold it (phalanges are left out: finger pose).
BONES = {"Humerus.r": "FMA23130", "Scapula.r": "FMA13395", "Clavicle.r": "FMA13322",
         "Radius.r": "FMA23464", "Ulna.r": "FMA23467", "Scaphoid.r": "FMA24435", "Lunate_bone.r": "FMA24437",
         "Triquetrum.r": "FMA24439", "Pisiform.r": "FMA24441", "Trapezium.r": "FMA24443",
         "Trapezoid.r": "FMA23725", "Capitate.r": "FMA24446", "Hamate.r": "FMA24448",
         "1st_metacarpal_bone.r": "FMA24464", "2nd_metacarpal_bone.r": "FMA24466",
         "3rd_metacarpal_bone.r": "FMA24468", "4th_metacarpal_bone.r": "FMA24470",
         "5th_metacarpal_bone.r": "FMA24472"}
SCALE_RANGE = (0.9, 1.1)

# FMA ids and English names checked against the FMA (EBI OLS, FMA 5.0 OWL). A right-sided concept is
# used when the FMA has one; Open3D objects that group several nerves map to the FMA set or class.
# Open3D object -> (FMA id, FMA English name, French name)
NERVES = {
    # Roots (anterior rami) of the brachial plexus
    "C5_root.r": ("FMA8734", "anterior ramus of right fifth cervical nerve",
                  "Rameau antérieur du 5e nerf cervical (racine C5 du plexus brachial)"),
    "C6_root.r": ("FMA8731", "anterior ramus of right sixth cervical nerve",
                  "Rameau antérieur du 6e nerf cervical (racine C6 du plexus brachial)"),
    "C7_root.r": ("FMA8728", "anterior ramus of right seventh cervical nerve",
                  "Rameau antérieur du 7e nerf cervical (racine C7 du plexus brachial)"),
    "C8_root.r": ("FMA8725", "anterior ramus of right eighth cervical nerve",
                  "Rameau antérieur du 8e nerf cervical (racine C8 du plexus brachial)"),
    # FMA: 'right first intercostal nerve', synonym 'anterior ramus of right first thoracic nerve'.
    "T1_root.r": ("FMA6073", "right first intercostal nerve",
                  "Rameau antérieur du 1er nerf thoracique (racine T1 du plexus brachial)"),
    # Trunks, divisions, cords
    "Superior_trunk_of_brachial_plexus.r": ("FMA65361", "superior trunk of right brachial nerve plexus",
                                            "Tronc supérieur du plexus brachial"),
    "Middle_trunk_of_brachial_plexus.r": ("FMA65365", "middle trunk of right brachial nerve plexus",
                                          "Tronc moyen du plexus brachial"),
    "Inferior_trunk_of_brachial_plexus.r": ("FMA65363", "inferior trunk of right brachial nerve plexus",
                                            "Tronc inférieur du plexus brachial"),
    "Anterior_divisions_of_brachial_plexus.r": ("FMA77549", "set of anterior divisions of brachial plexus",
                                                "Divisions antérieures du plexus brachial"),
    "Posterior_divisions_of_brachial_plexus.r": ("FMA77550", "set of posterior divisions of brachial plexus",
                                                 "Divisions postérieures du plexus brachial"),
    "Lateral_cord_of_brachial_plexus.r": ("FMA45238", "lateral cord of right brachial nerve plexus",
                                          "Faisceau latéral du plexus brachial"),
    "Medial_cord_of_brachial_plexus.r": ("FMA45240", "medial cord of right brachial nerve plexus",
                                         "Faisceau médial du plexus brachial"),
    "Posterior_cord_of_brachial_plexus.r": ("FMA45242", "posterior cord of right brachial nerve plexus",
                                            "Faisceau postérieur du plexus brachial"),
    # Collateral branches of the plexus
    "Dorsal_scapular_nerve.r": ("FMA65283", "right dorsal scapular nerve", "Nerf dorsal de la scapula"),
    "Long_thoracic_nerve.r": ("FMA65281", "right long thoracic nerve", "Nerf thoracique long"),
    "Subclavian_nerve.r": ("FMA65285", "right subclavian nerve", "Nerf subclavier"),
    "Suprascapular_nerve.r": ("FMA66083", "right suprascapular nerve", "Nerf suprascapulaire"),
    "Lateral_pectoral_nerve.r": ("FMA65298", "right lateral pectoral nerve", "Nerf pectoral latéral"),
    "Medial_pectoral_nerve.r": ("FMA65294", "right medial pectoral nerve", "Nerf pectoral médial"),
    "Upper_subscapular_nerve.r": ("FMA65305", "right superior subscapular nerve", "Nerf subscapulaire supérieur"),
    "Lower_subscapular_nerve.r": ("FMA65308", "right inferior subscapular nerve", "Nerf subscapulaire inférieur"),
    # Terminal branches
    "Musculocutaneus_nerve.r": ("FMA37065", "right musculocutaneous nerve", "Nerf musculocutané"),
    "Musculocutaneus_nerve__-_lateral_antebrachial_cutaneous_nerve.r": (
        "FMA39083", "lateral cutaneous nerve of right forearm", "Nerf cutané latéral de l'avant-bras"),
    # The Open3D object is the axillary nerve with its superior lateral cutaneous nerve of arm.
    "Axillary_nerve_-_superior_lateral_br_cutaneous_nerve.r": ("FMA37073", "right axillary nerve", "Nerf axillaire"),
    "Lateral_root_of_median_nerve.r": ("FMA305343", "lateral root of right median nerve",
                                       "Racine latérale du nerf médian"),
    "Medial_root_of_median_nerve.r": ("FMA305337", "medial root of right median nerve",
                                      "Racine médiale du nerf médian"),
    "Median_nerve.r": ("FMA37067", "right median nerve", "Nerf médian"),
    "Median_nerve_Palmar_br": ("FMA65327", "palmar branch of right median nerve", "Rameau palmaire du nerf médian"),
    "Median_nerve_Recurrent_br": ("FMA291310", "thenar muscular branch of right median nerve",
                                  "Rameau thénarien du nerf médian (rameau récurrent)"),
    "Median_nerve_Common_palmar_digital_nerve_of_the_thumb": (
        "FMA44851", "first common palmar digital branch of right median nerve",
        "1er nerf digital palmaire commun du nerf médian"),
    "Median_nerve_Common_palmar_digital_nerves": ("FMA44840", "common palmar digital branch of median nerve",
                                                  "Nerfs digitaux palmaires communs du nerf médian"),
    "Median_nerve_Proper_palmar_digital_nerves_of_the_thumb": (
        "FMA44854", "proper palmar digital branch of median nerve to thumb",
        "Nerfs digitaux palmaires propres du pouce"),
    "Median_nerve_Proper_palmar_digital_nerves": ("FMA44853", "proper palmar digital branch of median nerve",
                                                  "Nerfs digitaux palmaires propres du nerf médian"),
    "Ulnar_nerve.r": ("FMA37320", "right ulnar nerve", "Nerf ulnaire"),
    "Ulnar_nerve_Palmar_cutaneous_br": ("FMA65349", "palmar branch of right ulnar nerve",
                                        "Rameau palmaire du nerf ulnaire"),
    "Ulnar_nerve_Dorsal_cutaneous_br": ("FMA292830", "dorsal branch of right ulnar nerve",
                                        "Rameau dorsal du nerf ulnaire"),
    "Ulnar_nerve_Deep_br": ("FMA44680", "deep branch of right ulnar nerve", "Rameau profond du nerf ulnaire"),
    # The Open3D object runs from the division of the ulnar nerve to the fourth web space: the
    # superficial branch and its common palmar digital nerve. Its communicating branch with the median
    # nerve has no FMA concept outside 'variant anatomical structure': it is merged here.
    "Ulnar_nerve_Superficial_br_Common_palmar_digital_n": ("FMA44894", "superficial branch of right ulnar nerve",
                                                           "Rameau superficiel du nerf ulnaire"),
    "Ulnar_nerve_Communicating_br": ("FMA44894", "superficial branch of right ulnar nerve",
                                     "Rameau superficiel du nerf ulnaire"),
    "Ulnar_nerve_Superficial_br_Proper_palmar_digital_nn": (
        "FMA272344", "proper palmar digital branch of ulnar nerve", "Nerfs digitaux palmaires propres du nerf ulnaire"),
    "Medial_brachial_cutaneous_nerve.r": ("FMA65247", "medial cutaneous nerve of right arm",
                                          "Nerf cutané médial du bras"),
    "Medial_antebrachial_cutaneous_nerve.r": ("FMA39081", "medial cutaneous nerve of right forearm",
                                              "Nerf cutané médial de l'avant-bras"),
    "Radial_nerve.r": ("FMA37070", "right radial nerve", "Nerf radial"),
    "Radial_nerve_(posterior_brachial_cutaneous_n).r": ("FMA44950", "posterior cutaneous nerve of right arm",
                                                        "Nerf cutané postérieur du bras"),
    "Radial_nerve_(inferior_lateral_brachial_cutaneous_n).r": (
        "FMA44952", "inferior lateral cutaneous nerve of right arm", "Nerf cutané latéral inférieur du bras"),
    "Radial_nerve_(posterior_antebrachial_cutaneous_n).r": (
        "FMA39146", "posterior cutaneous nerve of right forearm", "Nerf cutané postérieur de l'avant-bras"),
    "Radial_nerve_(superficial_br).r": ("FMA292887", "superficial branch of right radial nerve",
                                        "Rameau superficiel du nerf radial"),
    # FMA: 'right posterior interosseous nerve', synonym 'deep branch of right radial nerve'.
    "Radial_nerve_(deep_branch).r": ("FMA65335", "right posterior interosseous nerve",
                                     "Rameau profond du nerf radial et nerf interosseux postérieur"),
    "Radial_nerve_(posterior_interosseus_n).r": ("FMA65335", "right posterior interosseous nerve",
                                                 "Rameau profond du nerf radial et nerf interosseux postérieur"),
    "Radial_nerve_(dorsal_digital_nn).r": ("FMA75490", "set of dorsal digital branches of radial nerve",
                                           "Nerfs digitaux dorsaux du nerf radial"),
}


def concepts():
    """{FMA id: (English name, French name, [Open3D objects])}; objects sharing a concept agree on its names."""
    out = {}
    for obj, (fid, en, fr) in NERVES.items():
        c = out.setdefault(fid, (en, fr, []))
        assert c[:2] == (en, fr), fid
        c[2].append(obj)
    return out


def read_obj(path, names):
    """Meshes of the named objects of an OBJ file, as {name: trimesh} (file units and axes, no processing).

    Only `v`, `f` and `o` records are read: UVs, normals, materials and groups are ignored. Polygons are
    triangulated as fans. Face indices are global to the file (1-based, or negative = relative)."""
    names = set(names)
    verts, faces, current = [], {}, None
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            tag = line[:2]
            if tag == "v ":
                verts.append(line)
            elif tag == "f " and current is not None:
                nv = len(verts)
                idx = [int(t.split("/", 1)[0]) for t in line.split()[1:]]
                idx = [i - 1 if i > 0 else nv + i for i in idx]
                faces[current].extend((idx[0], idx[k], idx[k + 1]) for k in range(1, len(idx) - 1))
            elif tag == "o ":
                name = line[2:].strip()
                current = name if name in names else None
                if current is not None:
                    if current in faces:
                        raise ValueError(f"duplicate object {name!r} in {path}")
                    faces[current] = []
    if missing := names - set(faces):
        raise ValueError(f"objects missing from {path}: {sorted(missing)}")
    v = np.array([ln.split()[1:4] for ln in verts], float).reshape(-1, 3)
    out = {}
    for name, fs in faces.items():
        fs = np.array(fs, np.int64).reshape(-1, 3)
        if len(fs) == 0 or fs.min() < 0 or fs.max() >= len(v):
            raise ValueError(f"object {name!r}: no faces or face index out of range")
        used, inv = np.unique(fs, return_inverse=True)
        out[name] = trimesh.Trimesh(v[used], inv.reshape(-1, 3), process=False)
    return out


def to_bp3d(points_m):
    """glTF frame (m) -> BodyParts3D frame (mm): the inverse of model.to_gltf."""
    return np.asarray(points_m, float) * 1000.0 @ BP3D_TO_GLTF


def _umeyama(a, b, scale):
    """Linear part m (rotation times uniform scale if `scale`) and translation t minimising |a @ m.T + t - b|."""
    ca, cb = a.mean(0), b.mean(0)
    u, sv, vt = np.linalg.svd((a - ca).T @ (b - cb))
    d = np.diag([1, 1, np.sign(np.linalg.det(vt.T @ u.T))])
    r = vt.T @ d @ u.T
    if scale:
        r = r * (np.trace(np.diag(sv) @ d) / ((a - ca) ** 2).sum())
    return r, cb - ca @ r.T


def register(pairs, iterations=100, trim=0.9, scale=False):
    """ICP between bones (rigid, or similarity with `scale`). pairs: [(source points (N,3), target points (M,3))], one per bone, same frame.

    Each source point is matched to the nearest target point of the same bone; the worst (1 - trim) of
    the matches are left out of each fit (remodelled bone ends, missing cartilage). Starts from the
    translation between the centroids. With `scale`, fits a similarity (r is then a rotation times a
    uniform scale). Returns (r, t, {bone index: (rms, median, p95) in input units})."""
    trees = [cKDTree(b) for _, b in pairs]
    src = np.concatenate([a for a, _ in pairs])
    r, t = np.eye(3), np.concatenate([b for _, b in pairs]).mean(0) - src.mean(0)
    prev = np.inf
    for _ in range(iterations):
        a_all, b_all, d_all = [], [], []
        for (a, b), tree in zip(pairs, trees):
            d, j = tree.query(a @ r.T + t)
            a_all.append(a); b_all.append(b[j]); d_all.append(d)
        a_all, b_all, d_all = map(np.concatenate, (a_all, b_all, d_all))
        keep = d_all <= np.quantile(d_all, trim)
        r, t = _umeyama(a_all[keep], b_all[keep], scale)
        err = np.sqrt(np.mean(d_all[keep] ** 2))
        if prev - err < 1e-6:
            break
        prev = err
    stats = {}
    for i, ((a, b), tree) in enumerate(zip(pairs, trees)):
        d, _ = tree.query(a @ r.T + t)
        stats[i] = (float(np.sqrt(np.mean(d ** 2))), float(np.median(d)), float(np.quantile(d, 0.95)))
    return r, t, stats


def _surface_points(mesh):
    """Vertices and face centroids of a mesh: a denser target for nearest-point matching."""
    return np.concatenate([mesh.vertices, mesh.triangles_center])


def fit(meshes, items, log=print, bones=None, label="open3d", check=True):
    """Similarity transform (m, t) from the Open3D bones (BodyParts3D frame, mm) onto the model's bones.

    bones: {Open3D bone object: FMA id of the same bone in the model} (default `BONES`). With `check`, the
    build stops when the bones do not fit within MAX_RMS_MM (without: only the scale is checked, for a fit
    that a per-bone refinement completes).
    Returns (m, t, {bone: (rms, median, p95) in mm}); m is a rotation times a uniform scale."""
    bones = BONES if bones is None else bones
    by_id = {x["id"]: x for x in items}
    if missing := sorted(f for f in bones.values() if f not in by_id):
        raise SystemExit(f"Open3D registration: bones missing from the model: {missing}")
    pairs = []
    for name, fid in bones.items():
        x = by_id[fid]
        target = x["src"] if x.get("src") is not None else x["mesh"]
        pairs.append((to_bp3d(meshes[name].vertices), _surface_points(target)))
    m, t, st = register(pairs, scale=True)
    scale = float(np.cbrt(np.linalg.det(m)))
    angle = np.degrees(np.arccos(np.clip((np.trace(m / scale) - 1) / 2, -1, 1)))
    stats = dict(zip(bones, st.values()))
    n = np.array([len(a) for a, _ in pairs])
    rms = float(np.sqrt(np.sum(n * np.array([s[0] for s in st.values()]) ** 2) / n.sum()))
    log(f"{label} registration: scale {scale:.4f}, rotation {angle:.2f} deg, translation {np.round(t, 1).tolist()} mm, "
        f"bone rms {rms:.2f} mm")
    log("   " + ", ".join(f"{k.removesuffix('.r')} {v[0]:.1f}" for k, v in stats.items()) + " (rms, mm)")
    if (check and rms > MAX_RMS_MM) or not SCALE_RANGE[0] < scale < SCALE_RANGE[1]:
        raise SystemExit(f"Open3D registration failed ({label}): bone rms {rms:.2f} mm, scale {scale:.3f}")
    return m, t, stats


def nerves(obj_path, items, log=print):
    """Nerve structures of the upper_limb model, registered on its bones.

    items: the upper_limb structures already built (BodyParts3D frame, mm), with the bones of `BONES`
    (their full resolution `src` mesh is used when present). Returns new structure dicts {id, en, fr,
    system, mesh, src, source}, in the BodyParts3D frame (mm)."""
    meshes = read_obj(obj_path, list(NERVES) + list(BONES))
    m, t, _ = fit(meshes, items, log)
    out = []
    for fid, (en, fr, objs) in sorted(concepts().items()):
        parts = [trimesh.Trimesh(to_bp3d(meshes[o].vertices) @ m.T + t, meshes[o].faces, process=False) for o in objs]
        src = clean(trimesh.util.concatenate(parts))
        mesh = decimate(src.copy(), max(MIN_TRIS, len(src.faces) * KEEP))
        out.append(dict(id=fid, en=en, fr=fr, system="nerfs", mesh=mesh, src=src, source=SOURCE_ID))
    return out
