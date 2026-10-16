"""BodyParts3D 3.0 meshes moved into the 4.0 frame by a displacement field.

The 3.0 body (2011) is not a rigid copy of the 4.0 one: a constant translation (V3_TO_V4) matches the
arm to 0.4 mm, but is off by 8 mm at the atlas and the pelvis and by 40 mm at the foot. The field is
measured on the concepts that have a mesh in both versions ("anchors"): each anchor's translation is
fitted by a trimmed point-to-point ICP (translation only), and anchors that do not match well (other
shape, partial mesh) are dropped. A 3.0 vertex moves by the inverse-distance-weighted mean of the
translations of the nearest anchor points: a muscle follows the bones it lies on, end by end.
Leave-one-out on the anchors: median error 1.1 mm, 90 % under 5 mm (constant translation: median 8.6 mm).
"""
import numpy as np
import trimesh
from scipy.spatial import cKDTree

from .bp3d import V3_TO_V4
from .model import clean, decimate

ANCHOR_SAMPLES, ANCHOR_POINTS = 4000, 200
MAX_RESIDUAL, MAX_COVERAGE = 1.0, 2.0  # mm: median distances 3.0 -> 4.0 and 4.0 -> 3.0 after the fit
K, EPS = 64, 25.0  # nearest anchor points, softening (mm^2) of the 1/d^2 weights


def fit_translation(m3, m4, t0=V3_TO_V4, iters=20):
    """Translation moving 3.0 mesh m3 onto 4.0 mesh m4, with the median residuals both ways (mm)."""
    tree = cKDTree(trimesh.sample.sample_surface(m4, 20000, seed=1)[0])
    p = trimesh.sample.sample_surface(m3, ANCHOR_SAMPLES, seed=2)[0]
    t = np.array(t0, float)
    for _ in range(iters):
        d, i = tree.query(p + t)
        keep = d <= np.percentile(d, 90)
        t = t + (tree.data[i[keep]] - (p[keep] + t)).mean(0)
    residual = float(np.median(tree.query(p + t)[0]))
    coverage = float(np.median(cKDTree(p + t).query(trimesh.sample.sample_surface(m4, 4000, seed=3)[0])[0]))
    return t, residual, coverage, p


class Field:
    """Displacement field from the 3.0 frame to the 4.0 frame, built from anchors [(points (n, 3), t)]."""

    def __init__(self, anchors):
        self.points = np.concatenate([p for p, _ in anchors])
        self.t = np.concatenate([np.repeat([t], len(p), axis=0) for p, t in anchors])
        self.tree = cKDTree(self.points)
        self.anchors = len(anchors)

    def __call__(self, v):
        d, i = self.tree.query(v, k=min(K, len(self.points)), workers=-1)
        d, i = d.reshape(len(v), -1), i.reshape(len(v), -1)
        w = 1.0 / (d ** 2 + EPS)
        return v + (w[..., None] * self.t[i]).sum(1) / w.sum(1, keepdims=True)


def field(bp, max_files=40, log=print):
    """Field from every non-composite concept with a 3.0 mesh and 4.0 element files (bones, muscles...).

    Computed once per BP3D object (a few minutes: every anchor's 4.0 files are loaded)."""
    if getattr(bp, "_v3_field", None) is None:
        bp._v3_field = _field(bp, max_files, log)
    return bp._v3_field


def load(bp, concept, keep=0.2, min_tris=200):
    """3.0 mesh of a concept in the 4.0 frame, decimated to about the density of 4.0 (3.0 is ~5x denser)."""
    m = bp.load_v3(concept, raw=True)
    if m is None:
        raise SystemExit(f"no BodyParts3D 3.0 mesh for {concept} ({bp.v3})")
    m.vertices = field(bp)(np.asarray(m.vertices))
    m = clean(m)
    return decimate(m, max(min_tris, len(m.faces) * keep))


def _field(bp, max_files, log):
    files = {}
    for f, owners in bp.owners.items():
        for c in owners:
            files.setdefault(c, set()).add(f)
    cache, anchors, rejected = {}, [], 0
    rng = np.random.default_rng(0)
    for c in sorted(bp.v3_names):
        if c in bp.v3_composites or c not in files or len(files[c]) > max_files:
            continue
        m3 = bp.load_v3(c, raw=True)
        if m3 is None:
            continue
        for f in files[c]:
            if f not in cache:
                cache[f] = bp.load_v4(f)
        m4 = trimesh.util.concatenate([cache[f] for f in sorted(files[c])])
        t, residual, coverage, p = fit_translation(m3, m4)
        if residual < MAX_RESIDUAL and coverage < MAX_COVERAGE:
            anchors.append((p[rng.choice(len(p), ANCHOR_POINTS, replace=False)], t))
        else:
            rejected += 1
    log(f"3.0 -> 4.0 field: {len(anchors)} anchors ({rejected} rejected: residual or coverage too large)")
    return Field(anchors)
