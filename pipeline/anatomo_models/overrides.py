"""Explicit corrections of the anatomical system of a structure, by FMA ID.

The pipeline derives a structure's system from BodyParts3D (FMA is-a tree, English names as a fallback,
see full_body.py and upper_limb.py). A few structures end up in the wrong mesh: cartilages and
intervertebral discs under 'cartilage organ' (a root of 'os'), liver segments matched by the word
'venous', hair in the catch-all 'organes'... The table below overrides the system of these structures
when the models are built (build.py), whatever the model. Each entry states its reason.

Conventions for the cases the format has no system for (see docs/FORMAT.md, "Systèmes"):
- os: bones, plus costal cartilages (part of the ribs in the TA) and teeth (hard tissue, shown with the
  skull in atlases);
- organes: everything that is not otherwise classified, including cartilages outside the ribs (larynx,
  nose), intervertebral discs, ligaments and membranes;
- muscles: muscles and their tendinous parts (tendons, aponeuroses, raphes, retinacula, tendinous rings);
- peau: skin and its appendages (hair).
"""
from .model import SYSTEMS

R_DISC = "intervertebral disc: fibrocartilage of a joint, not bone ('cartilage organ' is a root of 'os')"
R_LARYNX = "cartilage of the larynx: respiratory organ, not bone"
R_NOSE = "cartilage of the external nose: respiratory organ, not bone"
R_HAIR = "hair: appendage of the skin"
R_TENDON = "tendinous part of muscles"
R_LIGAMENT = "ligament or membrane, not muscle (matched 'interosse'/'rectus' in the name fallback)"
R_HEART = "part of the heart, not a skeletal muscle"
R_LIVER = "liver segment (organ region), matched 'venous' in the name fallback"

SYSTEM_OVERRIDES = {
    # --- os -> organes: intervertebral discs (named after the vertebra above them) -----------------------------
    "FMA25058": ("organes", R_DISC),  # intervertebral disk of axis (C2-C3)
    **{f: ("organes", R_DISC) for f in (
        "FMA13896", "FMA13897", "FMA13898", "FMA13899", "FMA13900",  # C3-C4 ... C7-T1
        "FMA10458", "FMA13495", "FMA13500", "FMA13501", "FMA13502", "FMA13503", "FMA13504",  # T1-T2 ... T7-T8
        "FMA13505", "FMA13506", "FMA13507", "FMA13508",  # T8-T9 ... T11-T12
        "FMA10446",  # 'intervertebral disk': the T12-L1 disc by its position
        "FMA16033", "FMA16034", "FMA16035", "FMA16036", "FMA16037",  # L1-L2 ... L5-S1
    )},
    # --- os -> organes: cartilages of the larynx and of the nose ----------------------------------------------
    "FMA55099": ("organes", R_LARYNX),  # thyroid cartilage
    "FMA9615": ("organes", R_LARYNX),  # cricoid cartilage
    "FMA55113": ("organes", R_LARYNX), "FMA55114": ("organes", R_LARYNX),  # arytenoid cartilages
    "FMA55115": ("organes", R_LARYNX), "FMA55116": ("organes", R_LARYNX),  # corniculate cartilages
    "FMA55117": ("organes", R_LARYNX), "FMA55118": ("organes", R_LARYNX),  # cuneiform cartilages
    "FMA59505": ("organes", R_NOSE), "FMA59506": ("organes", R_NOSE),  # major alar cartilages
    "FMA59512": ("organes", R_NOSE), "FMA59513": ("organes", R_NOSE),  # lateral nasal cartilages
    "FMA59838": ("organes", R_NOSE),  # cartilaginous part of nasal septum (septal nasal cartilage)
    # --- organes -> peau: hair --------------------------------------------------------------------------------
    "FMA54241": ("peau", R_HAIR),  # hair of head
    "FMA54319": ("peau", R_HAIR),  # pubic hair
    "FMA54237": ("peau", R_HAIR),  # eyebrow
    # --- organes -> muscles: tendinous structures -------------------------------------------------------------
    "FMA11336": ("muscles", R_TENDON + ": linea alba, aponeurotic raphe of the abdominal muscles"),
    "FMA58776": ("muscles", R_TENDON + ": iliotibial tract, tendon of tensor fasciae latae and gluteus maximus"),
    "FMA58777": ("muscles", R_TENDON + ": iliotibial tract, tendon of tensor fasciae latae and gluteus maximus"),
    "FMA55077": ("muscles", R_TENDON + ": pharyngeal raphe, insertion of the pharyngeal constrictors"),
    "FMA55619": ("muscles", R_TENDON + ": pterygomandibular raphe, buccinator and superior constrictor"),
    "FMA55620": ("muscles", R_TENDON + ": pterygomandibular raphe, buccinator and superior constrictor"),
    "FMA49072": ("muscles", R_TENDON + ": common tendinous ring, origin of the recti of the eye"),
    "FMA49073": ("muscles", R_TENDON + ": common tendinous ring, origin of the recti of the eye"),
    "FMA58406": ("muscles", "the mesh is the flexor retinaculum of the left wrist (the right one is in muscles)"),
    # --- muscles -> organes: ligaments and membranes, heart -----------------------------------------------------
    "FMA23707": ("organes", R_LIGAMENT), "FMA23708": ("organes", R_LIGAMENT),  # interosseous membrane of forearm
    "FMA35192": ("organes", R_LIGAMENT), "FMA35193": ("organes", R_LIGAMENT),  # interosseous membrane of leg
    "FMA49144": ("organes", R_LIGAMENT), "FMA49145": ("organes", R_LIGAMENT),  # check ligaments of lateral rectus
    "FMA49147": ("organes", R_LIGAMENT), "FMA49148": ("organes", R_LIGAMENT),  # check ligaments of medial rectus
    "FMA7260": ("organes", R_HEART), "FMA7261": ("organes", R_HEART), "FMA7262": ("organes", R_HEART),  # papillary muscles
    # --- veines -> organes: liver segments ----------------------------------------------------------------------
    **{f: ("organes", R_LIVER) for f in (
        "FMA15739", "FMA15741", "FMA15742", "FMA15743", "FMA15744", "FMA15745", "FMA15746", "FMA15747")},
    # --- organes -> arteres -------------------------------------------------------------------------------------
    "FMA259248": ("arteres", "'content of abdomen': its only mesh is the abdominal aorta"),
}

assert all(s in SYSTEMS and r for s, r in SYSTEM_OVERRIDES.values())


def apply_system_overrides(structures, overrides=SYSTEM_OVERRIDES, log=print):
    """Set the system of the structures listed in `overrides`, in place. Returns the ids found."""
    found = set()
    for x in structures:
        if x["id"] in overrides:
            found.add(x["id"])
            new, reason = overrides[x["id"]]
            if x["system"] == new:
                log(f"system override of {x['id']} ({x['en']}) is not needed any more: already {new}")
            else:
                log(f"system override: {x['id']} ({x['en']}) {x['system']} -> {new}")
                x["system"] = new
    return found
