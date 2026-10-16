"""Anatomical landmarks placed geometrically on the meshes (BodyParts3D has none).

The catalogue (`landmark_catalog.py`) lists, structure by structure, landmarks with a placement rule:
bony landmarks (extreme point in an anatomical direction, floor of a fossa, centre of an articular
surface), muscle attachments (where the muscle meets its bone), pulse points and clinical points on
vessels and organs (point of a structure closest to a bone or to another landmark).

Rules run in the glTF frame (m) of a right-side structure: lateral = -X, medial = +X, anterior = +Z,
posterior = -Z, superior = +Y. Left-side structures are mirrored (x -> -x) before the rules run and the
result is mirrored back, so one rule serves both sides. Rules run on the full-resolution source mesh
when there is one, then the point is moved onto the published (decimated) surface and pushed 1.5 mm
outwards along its normal. Positions are approximate: they must be reviewed by an anatomist.
"""
import re

import numpy as np
from scipy.spatial import cKDTree

from .model import BP3D_TO_GLTF

OFFSET = 0.0015  # m, outwards from the surface
DIRS = {"sup": (0, 1, 0), "inf": (0, -1, 0), "ant": (0, 0, 1), "post": (0, 0, -1), "lat": (-1, 0, 0), "med": (1, 0, 0)}
KINDS = ("saillie", "articulaire", "depression", "repere", "origine", "insertion", "pouls", "clinique")
MIRROR = np.array([-1.0, 1.0, 1.0])


class Skip(Exception):
    """The landmark cannot be placed in this model (a structure it needs is missing)."""


def parse(s):
    """'lat+.4sup-0.2ant' -> unnormalised vector; also '20sup+10ant' (used as millimetres for offsets)."""
    v = np.zeros(3)
    for sign, k, name in re.findall(r"([+-]?)\s*([0-9.]*)\s*\*?\s*([a-z]+)", s):
        v += (-1 if sign == "-" else 1) * float(k or 1) * np.array(DIRS[name], float)
    return v


def vec(s):
    v = parse(s)
    return v / np.linalg.norm(v)


class Part:
    """A structure in the canonical (right-side) frame: source vertices/normals for the rules, published triangles for the snap."""

    def __init__(self, id, V, N, tris, tri_normals):
        self.id, self.V, self.N, self.tris, self.tri_normals = id, V, N, tris, tri_normals
        self._t, self._tree = {}, None

    def t(self, d):
        """Position of each vertex along direction d, 0 at the structure's extreme in -d, 1 at its extreme in d."""
        if d not in self._t:
            p = self.V @ vec(d)
            self._t[d] = (p - p.min()) / max(p.max() - p.min(), 1e-9)
        return self._t[d]

    def mask(self, bands, face=None, cos=0.3):
        m = np.ones(len(self.V), bool)
        for d, (lo, hi) in bands.items():
            t = self.t(d)
            m &= (t >= lo) & (t <= hi)
        if face:
            m &= self.N @ vec(face) > cos
        if not m.any():
            raise ValueError(f"empty selection on {self.id}: {bands} {face}")
        return np.where(m)[0]

    @property
    def tree(self):
        if self._tree is None:
            self._tree = cKDTree(self.V)
        return self._tree

    def nearest(self, idx, p):
        return self.V[idx[np.argmin(np.linalg.norm(self.V[idx] - p, axis=1))]]


def _part(id, mesh, src):
    """Part from trimesh meshes in the BodyParts3D frame (mm): `mesh` is published, `src` (optional) is full resolution."""
    s = src if src is not None else mesh
    R = BP3D_TO_GLTF.T * 0.001
    return Part(id, s.vertices @ R, _normals(s) @ BP3D_TO_GLTF.T, mesh.triangles @ R, mesh.face_normals @ BP3D_TO_GLTF.T)


def _normals(mesh):
    n = np.array(mesh.vertex_normals, float)
    ok = np.linalg.norm(n, axis=1) > 0.5
    n[~ok] = 0
    return n


def _mirror(p):
    tris = p.tris * MIRROR
    return Part(p.id, p.V * MIRROR, p.N * MIRROR, tris[:, ::-1], p.tri_normals * MIRROR)


# --- Rules: callables (world, part) -> point in the canonical frame --------------------------------------------------

def X(d, face=None, **bands):
    """Extreme vertex in direction d, within bands (fractions of the structure's extent along a direction)."""
    def rule(w, p):
        i = p.mask(bands, face)
        return p.V[i[np.argmax(p.V[i] @ vec(d))]]
    return rule


def F(d, **bands):
    """Floor of a fossa opening towards d: the vertex facing d that lies deepest (least far along d)."""
    def rule(w, p):
        i = p.mask(bands, d, 0.5)
        return p.V[i[np.argmin(p.V[i] @ vec(d))]]
    return rule


def C(face, **bands):
    """Centre of the surface facing `face` within bands (an articular surface), snapped to that surface."""
    def rule(w, p):
        i = p.mask(bands, face, 0.6)
        return p.nearest(i, p.V[i].mean(0))
    return rule


def N(ref, off=None, face=None, **bands):
    """Point of the structure closest to a landmark ('@id', optionally offset by `off` mm) or to another structure."""
    def rule(w, p):
        i = p.mask(bands, face)
        if ref.startswith("@"):
            q = w.landmark(ref[1:]) + (parse(off) * 0.001 if off else 0)
            return p.nearest(i, q)
        d, _ = w.part(ref).tree.query(p.V[i])
        return p.V[i[np.argmin(d)]]
    rule.refs = (ref[1:],) if ref.startswith("@") else ()
    return rule


def Mid(a, b, face=None):
    """Point of the structure closest to the middle of two landmarks."""
    def rule(w, p):
        i = p.mask({}, face)
        return p.nearest(i, (w.landmark(a) + w.landmark(b)) / 2)
    rule.refs = (a, b)
    return rule


def E(end, frac=0.08):
    """Centre of the end of the structure in direction `end` (last `frac` of its extent)."""
    def rule(w, p):
        i = p.mask({end: (1 - frac, 1)})
        return p.nearest(i, p.V[i].mean(0))
    return rule


def A(targets, end=None, frac=0.4):
    """Attachment of a muscle on its bones (or tendon): centre of the part of the muscle touching them,
    taken in the muscle's end towards `end` when given. Falls back on the muscle's end when no target is
    in the model (the upper-limb model has no sternum, ribs or vertebrae)."""
    targets = [targets] if isinstance(targets, str) else targets

    def rule(w, p):
        i = p.mask({end: (1 - frac, 1)}) if end else np.arange(len(p.V))
        parts = [q for t in targets if (q := w.part(t, required=False)) is not None]
        if parts:
            V, Nb = np.concatenate([q.V for q in parts]), np.concatenate([q.N for q in parts])
            d, j = cKDTree(V).query(p.V[i])
            if d.min() < 0.012:
                near = i[d <= d.min() + 0.003]
                c = p.V[near].mean(0)
                # Prefer the outer surface of the muscle there (its normal agrees with the bone's): it stays visible.
                outer = i[np.einsum("ij,ij->i", p.N[i], Nb[j]) > 0.3]
                close = outer[np.linalg.norm(p.V[outer] - c, axis=1) < 0.015]
                return p.nearest(close if len(close) else near, c)
            raise Skip  # the muscle stops short of its bone (e.g. a head ending on a common tendon)
        if not end:
            raise Skip
        return E(end)(w, p)
    return rule


def humerus_rule(slug):
    """The twelve historical landmarks of the humerus (`humerus()`, BodyParts3D frame), kept as they were placed."""
    def rule(w, p):
        if "humerus" not in w.cache:
            R = BP3D_TO_GLTF  # orthogonal: v_gltf = v_bp @ R.T, so v_bp = v_gltf @ R
            w.cache["humerus"] = {k: pos @ R.T for k, _, _, pos in humerus(p.V @ R, p.N @ R)}
        return w.cache["humerus"][slug]
    return rule


# --- Catalogue entries --------------------------------------------------------------------------------------------

class Entry:
    """Landmarks of one structure. `name` is the English FMA name, with '{side}' for paired structures.
    `paired` (midline structures only): each landmark exists on both sides (transverse processes...)."""

    def __init__(self, name, prefix, marks, paired=False):
        self.name, self.prefix, self.marks, self.paired = name, prefix, marks, paired
        self.sided = "{side}" in name
        assert not (self.sided and paired)
        for slug, fr, kind, rule in marks:
            assert kind in KINDS and re.fullmatch(r"[a-z0-9-]+", slug) and callable(rule), (prefix, slug)


def B(name, prefix, *marks, paired=False):
    return Entry(name, prefix, list(marks), paired)


def M(name, prefix, origin, insertion):
    """Muscle: origin and insertion as (French name of the site, target structures, end of the muscle)."""
    marks = []
    for slug, kind, spec in (("origine", "origine", origin), ("insertion", "insertion", insertion)):
        if spec:
            fr, targets, end = spec
            marks.append((slug, fr, kind, A(targets, end)))
    return Entry(name, prefix, marks)


# --- Placement ----------------------------------------------------------------------------------------------------

class World:
    """The structures of a model seen from one side (mirrored for the left side), and the landmarks placed so far."""

    def __init__(self, parts, side):
        self.parts, self.side, self.placed, self.cache = parts, side, {}, {}
        self._mirrored = {}

    def part(self, name, required=True):
        name = name.format(side=self.side)
        p = self.parts.get(name)
        if p is None:
            if required:
                raise Skip
            return None
        if self.side == "left":
            if name not in self._mirrored:
                self._mirrored[name] = _mirror(p)
            p = self._mirrored[name]
        return p

    def landmark(self, id):
        if id not in self.placed:
            raise Skip
        return self.placed[id]


def closest_on_triangles(q, tris):
    """Closest point to q on each triangle of a set (n,3,3) (Ericson, Real-Time Collision Detection, 5.1.5)."""
    a, b, c = tris[:, 0], tris[:, 1], tris[:, 2]
    ab, ac, ap = b - a, c - a, q - a
    d1, d2 = (ab * ap).sum(1), (ac * ap).sum(1)
    bp = q - b
    d3, d4 = (ab * bp).sum(1), (ac * bp).sum(1)
    cp = q - c
    d5, d6 = (ab * cp).sum(1), (ac * cp).sum(1)
    va, vb, vc = d3 * d6 - d5 * d4, d5 * d2 - d1 * d6, d1 * d4 - d3 * d2
    with np.errstate(divide="ignore", invalid="ignore"):
        denom = va + vb + vc
        v, w_ = vb / denom, vc / denom
        out = a + ab * v[:, None] + ac * w_[:, None]  # inside the face
        # Edge regions.
        t = d1 / (d1 - d3)
        m = (vc <= 0) & (d1 >= 0) & (d3 <= 0)
        out[m] = (a + ab * t[:, None])[m]
        t = d2 / (d2 - d6)
        m = (vb <= 0) & (d2 >= 0) & (d6 <= 0)
        out[m] = (a + ac * t[:, None])[m]
        t = (d4 - d3) / ((d4 - d3) + (d5 - d6))
        m = (va <= 0) & ((d4 - d3) >= 0) & ((d5 - d6) >= 0)
        out[m] = (b + (c - b) * t[:, None])[m]
    # Vertex regions last (they take precedence).
    out[(d1 <= 0) & (d2 <= 0)] = a[(d1 <= 0) & (d2 <= 0)]
    out[(d3 >= 0) & (d4 <= d3)] = b[(d3 >= 0) & (d4 <= d3)]
    out[(d6 >= 0) & (d5 <= d6)] = c[(d6 >= 0) & (d5 <= d6)]
    return np.nan_to_num(out, nan=np.inf)


def snap(p, q):
    """Move q onto the published surface of p, then 1.5 mm outwards. On an edge or a vertex shared by several
    faces, the direction is the mean normal of those faces."""
    pts = closest_on_triangles(q, p.tris)
    d = np.linalg.norm(pts - q, axis=1)
    k = d <= d.min() + 1e-7
    n = p.tri_normals[k].sum(0)
    n = n / np.linalg.norm(n) if np.linalg.norm(n) > 1e-9 else p.tri_normals[np.argmin(d)]
    return pts[np.argmin(d)] + n * OFFSET


def place(items, catalogue):
    """items: [{id, en, mesh (published), src (optional, full resolution)}], meshes in the BodyParts3D frame (mm).
    Returns (landmarks, failed): landmarks in the glTF frame of the model, and the (id, side, reason) of those
    whose structure is in the model but whose rule found no vertex (the build fails on them)."""
    parts = {x["en"]: _part(x["id"], x["mesh"], x.get("src")) for x in items}
    out, failed = [], []
    for side in ("right", "left"):
        w = World(parts, side)
        for e in catalogue:
            if not e.sided and not e.paired and side == "left":
                continue
            p = w.part(e.name, required=False)
            if p is None:
                continue
            for slug, fr, kind, rule in e.marks:
                lid = f"{e.prefix}.{slug}"
                try:
                    q = np.asarray(rule(w, p), float)
                except Skip:
                    continue
                except ValueError as err:
                    failed.append((lid, side, str(err)))
                    continue
                w.placed[lid] = q
                pos = snap(p, q)
                if side == "left":
                    pos = pos * MIRROR
                out.append({"id": lid, "structure": p.id, "side": side if (e.sided or e.paired) else None,
                            "fr": fr, "kind": kind, "position": np.round(pos, 5).tolist()})
    return out, failed


def unresolved(names, catalogue):
    """Catalogue structures found in neither side of `names` (a typo would silently drop landmarks)."""
    names = set(names)
    return [e.name for e in catalogue if not ({e.name.format(side=s) for s in ("right", "left")} & names)]


# --- Humerus (historical rules, BodyParts3D frame) ----------------------------------------------------------------

HUMERUS = "FMA23130"

META = {
    "tete": ("Tête de l'humérus", "articulaire"), "grand-tubercule": ("Tubercule majeur", "saillie"),
    "petit-tubercule": ("Tubercule mineur", "saillie"), "sillon-intertuberculaire": ("Sillon intertuberculaire", "depression"),
    "col-chirurgical": ("Col chirurgical de l'humérus", "repere"), "tuberosite-deltoidienne": ("Tubérosité deltoïdienne", "saillie"),
    "epicondyle-lateral": ("Épicondyle latéral de l'humérus", "saillie"), "epicondyle-medial": ("Épicondyle médial de l'humérus", "saillie"),
    "capitulum": ("Capitulum de l'humérus", "articulaire"), "trochlee": ("Trochlée de l'humérus", "articulaire"),
    "fosse-olecranienne": ("Fosse olécrânienne", "depression"), "fosse-coronoidienne": ("Fosse coronoïdienne", "depression"),
}


def humerus(V, N):
    """V, N: (n,3) vertices (m) and unit normals of the right humerus, BodyParts3D frame (lateral = -x,
    anterior = -y, superior = +z). Returns [(slug, fr, kind, position)] with positions in the same frame,
    on the surface (the caller moves them outwards)."""
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
    return [(k, *META[k], V[i]) for k, i in L.items()]
