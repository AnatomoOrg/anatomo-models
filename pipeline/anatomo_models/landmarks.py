"""Bony landmarks of the right humerus, placed geometrically on the mesh (BodyParts3D has none).

Computed in the BodyParts3D frame, in metres: lateral = -x, medial = +x, anterior = -y,
posterior = +y, superior = +z. t = position along the long axis, 0 = distal end, 1 = proximal end.
Each landmark is the extreme vertex in a direction within a band of t (or a fossa floor), pushed
1.5 mm outwards along the normal. Approximate: positions must be reviewed by an anatomist.
"""
import numpy as np

HUMERUS = "FMA23130"

META = {
    "tete": ("Tête de l'humérus", "articulaire"), "grand-tubercule": ("Grand tubercule", "saillie"),
    "petit-tubercule": ("Petit tubercule", "saillie"), "sillon-intertuberculaire": ("Sillon intertuberculaire", "depression"),
    "col-chirurgical": ("Col chirurgical", "repere"), "tuberosite-deltoidienne": ("Tubérosité deltoïdienne", "saillie"),
    "epicondyle-lateral": ("Épicondyle latéral", "saillie"), "epicondyle-medial": ("Épicondyle médial", "saillie"),
    "capitulum": ("Capitulum de l'humérus", "articulaire"), "trochlee": ("Trochlée de l'humérus", "articulaire"),
    "fosse-olecranienne": ("Fosse olécrânienne", "depression"), "fosse-coronoidienne": ("Fosse coronoïdienne", "depression"),
}


def humerus(V, N):
    """V, N: (n,3) vertices (m) and unit normals of the right humerus, BodyParts3D frame.
    Returns [(slug, fr, kind, position)] with positions in the same frame."""
    V, N = np.asarray(V, float), np.asarray(N, float)
    z0, z1 = V[:, 2].min(), V[:, 2].max()
    t = (V[:, 2] - z0) / (z1 - z0)

    def extreme(lo, hi, d, mask=None):
        m = (t >= lo) & (t <= hi)
        if mask is not None:
            m &= mask
        idx = np.where(m)[0]
        d = np.array(d, float) / np.linalg.norm(d)
        return idx[np.argmax(V[idx] @ d)]

    def fossa(lo, hi, side, xc, halfw):
        # Floor of a fossa on the anterior (side=-1) or posterior (+1) face: outward-facing vertex closest to the core.
        m = (t >= lo) & (t <= hi) & (N[:, 1] * side > 0.5) & (np.abs(V[:, 0] - xc) < halfw)
        idx = np.where(m)[0]
        return idx[np.argmin(V[idx, 1] * side)]

    L = {}
    L["tete"] = extreme(0.85, 1.0, (1, 0.3, 0.7))
    L["grand-tubercule"] = extreme(0.85, 1.0, (-1, 0, 0.4))
    L["petit-tubercule"] = extreme(0.82, 0.93, (0.3, -1, 0))
    gx, lx = V[L["grand-tubercule"], 0], V[L["petit-tubercule"], 0]
    L["sillon-intertuberculaire"] = extreme(0.82, 0.88, (0, -1, 0), np.abs(V[:, 0] - (0.4 * gx + 0.6 * lx)) < 0.002)
    L["col-chirurgical"] = extreme(0.76, 0.80, (-0.6, -0.8, 0))
    L["tuberosite-deltoidienne"] = extreme(0.50, 0.62, (-1, -0.3, 0))
    L["epicondyle-lateral"] = extreme(0.0, 0.15, (-1, 0, 0))
    L["epicondyle-medial"] = extreme(0.0, 0.15, (1, 0, 0))
    mx, lx2 = V[L["epicondyle-medial"], 0], V[L["epicondyle-lateral"], 0]
    xc = (mx + lx2) / 2
    L["capitulum"] = extreme(0.0, 0.08, (-0.5, -0.6, -0.6), V[:, 0] < xc)
    L["trochlee"] = extreme(0.0, 0.06, (0.2, 0, -1), V[:, 0] > xc)
    L["fosse-olecranienne"] = fossa(0.06, 0.14, +1, xc + 0.1 * (mx - xc), 0.006)
    L["fosse-coronoidienne"] = fossa(0.07, 0.14, -1, xc + 0.2 * (mx - xc), 0.005)
    return [(k, *META[k], V[i] + N[i] * 0.0015) for k, i in L.items()]
