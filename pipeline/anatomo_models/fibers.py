"""Muscle fibre direction and tendon mask, per vertex, for the procedural fibres drawn by the app.

Computed on the published (decimated) mesh of each structure of the `muscles` system, in the glTF frame (m):

- fibre direction: a field running along the surface from the origin of the muscle to its insertion. The ends
  are the muscle's `origine` and `insertion` landmarks when it has both (the vertices around them, and those
  touching a bone near them: an attachment is an area, not a point), otherwise the two ends of the structure
  along its principal axis (PCA), the narrower one playing the insertion. From each end, a heat diffusion on the
  surface (cotangent Laplacian, sparse solve: the heat method) gives the direction of the geodesics leaving it;
  the fibre runs along their difference, weighted towards the insertion. The field follows curved muscles and
  converges on the insertion of fan-shaped ones (pectoralis major, deltoid, latissimus dorsi), where a single
  axis or a potential between two points would not. It is averaged over about 8 mm, made tangent to the
  smoothed surface (within a few degrees of the published normal, which follows the sculpted relief of the
  meshes) and unit length; its sign is meaningless (fibres have no orientation).
- tendon mask (0 = fleshy, 1 = tendon): parts of the structure much thinner than its body (local thickness,
  measured where the inward normal crosses the medial axis) and thinner than about 5 mm, in structures longer
  than 5 to 9 cm (smaller ones stay fleshy: coarse meshes, tendons too small to show). Structures that are
  tendinous as a whole (tendons, aponeuroses, raphes, retinacula, linea alba, iliotibial tract, inguinal
  ligament...) are 1 everywhere.

Both are approximate, computed geometrically from shapes that do not separate tendons from muscle bellies.
"""
import re

import numpy as np
import scipy.sparse as sp
from scipy.sparse.csgraph import connected_components
from scipy.sparse.linalg import spsolve
from scipy.spatial import cKDTree

# Structures whose whole mesh is tendinous tissue (English FMA names).
TENDINOUS = re.compile(r"tendon|aponeuros|raphe|retinacul|tendinous|linea alba|iliotibial tract|inguinal ligament", re.I)

END_FRACTION = 0.06  # PCA ends: last 6 % of the extent along the principal axis
PATCH = (0.004, 0.025, 0.12)  # landmark ends: radius = 12 % of the structure's length, between 4 and 25 mm
THIN_ABS = 0.007  # m: no tendon thicker than this
MIN_LENGTH = (0.05, 0.09)  # m: no tendon in structures shorter than 5 cm, fully allowed from 9 cm
CONTACT = 0.003  # m: a muscle vertex this close to a bone is attached to it (near an origin or insertion landmark)
ATTACH = 0.3  # attachment areas reach this fraction of the structure's length from their landmark
SMOOTH_RADIUS = 0.012  # m: the direction field is averaged over about this distance
STEPS = np.arange(0.00025, 0.009, 0.00025)  # depths probed along the inward normal (m)


def _adjacency(n, faces):
    i = np.concatenate([faces[:, 0], faces[:, 1], faces[:, 2]])
    j = np.concatenate([faces[:, 1], faces[:, 2], faces[:, 0]])
    a = sp.coo_matrix((np.ones(len(i)), (i, j)), shape=(n, n)).tocsr()
    return ((a + a.T) > 0).astype(float)


def _cotan_laplacian(V, F):
    """Cotangent Laplacian with negative weights clamped (M-matrix: the diffusion stays positive and monotone)."""
    n = len(V)
    a, b, c = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]

    def cot(u, v):
        return (u * v).sum(1) / np.maximum(np.linalg.norm(np.cross(u, v), axis=1), 1e-20)

    w = np.concatenate([cot(b - a, c - a), cot(c - b, a - b), cot(a - c, b - c)]) / 2
    i = np.concatenate([F[:, 1], F[:, 2], F[:, 0]])
    j = np.concatenate([F[:, 2], F[:, 0], F[:, 1]])
    w = np.clip(w, 1e-3, 1e3)
    W = sp.coo_matrix((w, (i, j)), shape=(n, n)).tocsr()
    W = W + W.T
    return sp.diags(np.asarray(W.sum(1)).ravel()) - W


def _gradient(V, F, phi):
    """Area-weighted mean, per vertex, of the gradient of phi on the incident faces."""
    a, b, c = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    n = np.cross(b - a, c - a)
    area2 = np.maximum(np.linalg.norm(n, axis=1), 1e-20)
    nu = n / area2[:, None]
    g = (phi[F[:, 0], None] * np.cross(nu, c - b) + phi[F[:, 1], None] * np.cross(nu, a - c)
         + phi[F[:, 2], None] * np.cross(nu, b - a)) / area2[:, None]
    out = np.zeros_like(V)
    for k in range(3):
        np.add.at(out, F[:, k], g * area2[:, None])
    wsum = np.zeros(len(V))
    for k in range(3):
        np.add.at(wsum, F[:, k], area2)
    return out / np.maximum(wsum, 1e-20)[:, None]


def _tangent(d, normals):
    return d - normals * (d * normals).sum(1, keepdims=True)


def _unit(d):
    return d / np.maximum(np.linalg.norm(d, axis=1, keepdims=True), 1e-20)


def principal_axis(V):
    c = V - V.mean(0)
    w, U = np.linalg.eigh(c.T @ c)
    axis = U[:, -1]
    # Deterministic sign: the largest component positive.
    return axis * np.sign(axis[np.argmax(np.abs(axis))])


def thickness(V, N):
    """Local thickness (m): twice the depth, along the inward normal, at which the nearest vertex starts facing
    the other way (the medial axis is crossed). STEPS[-1] * 2 when not crossed within the probed depths."""
    tree = cKDTree(V)
    out = np.full(len(V), STEPS[-1] * 2)
    todo = np.arange(len(V))
    for d in STEPS:
        if not len(todo):
            break
        _, j = tree.query(V[todo] - N[todo] * d)
        crossed = (N[j] * N[todo]).sum(1) < -0.2
        out[todo[crossed]] = 2 * d
        todo = todo[~crossed]
    return out


def _smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


class Context:
    """What the structures of a model share: the bones they attach to (glTF frame, m)."""

    def __init__(self, bone_vertices=None):
        b = None if bone_vertices is None else np.asarray(bone_vertices, float)
        self.bones = cKDTree(b) if b is not None and len(b) else None


def ends_of(landmarks, structure):
    """(origin, insertion) positions of a structure's landmarks (glTF frame), or None unless it has both."""
    e = {m["kind"]: np.asarray(m["position"], float) for m in landmarks
         if m["structure"] == structure and m["kind"] in ("origine", "insertion")}
    return (e["origine"], e["insertion"]) if len(e) == 2 else None


def _heat_direction(L, V, F, N, seeds, h):
    """Direction away from `seeds` along the surface: gradient of the log of a heat diffusion from them (heat method)."""
    area = _vertex_area(V, F)
    delta = np.zeros(len(V))
    delta[seeds] = area[seeds]
    u = spsolve((sp.diags(area) + (4 * h) ** 2 * L).tocsc(), delta)
    return _tangent(_gradient(V, F, -np.log(np.maximum(u, 1e-300))), N)


def _vertex_area(V, F):
    a = np.linalg.norm(np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]]), axis=1) / 6
    out = np.zeros(len(V))
    for k in range(3):
        np.add.at(out, F[:, k], a)
    return np.maximum(out, 1e-20)


def _seeds(Vk, ck, axis, length, ends):
    """(origin, insertion) vertex sets of one connected piece of a structure, or None (piece too small to tell)."""
    if ends is not None:
        r = np.clip(PATCH[2] * length, PATCH[0], PATCH[1])
        d0 = np.linalg.norm(Vk - ends[0], axis=1)
        d1 = np.linalg.norm(Vk - ends[1], axis=1)
        # The attachment: around the landmark, and where the muscle touches a bone near it.
        reach = ATTACH * length
        s = np.where(((d0 < r) | (ck & (d0 < reach))) & (d0 < d1))[0]
        e = np.where(((d1 < r) | (ck & (d1 < reach))) & (d1 < d0))[0]
        if len(s) and len(e):
            return s, e
    t = Vk @ axis
    lo, hi = t.min(), t.max()
    span = hi - lo
    if span < 0.15 * length:
        return None
    start = np.where(t <= lo + END_FRACTION * span)[0]
    end = np.where(t >= hi - END_FRACTION * span)[0]
    # Without landmarks, the fibres converge on the narrower end (a tendon): it plays the insertion.
    spread = [np.ptp(Vk[x] - np.outer(Vk[x] @ axis, axis), axis=0).max() for x in (start, end)]
    return (end, start) if spread[0] < spread[1] else (start, end)


def structure_fibers(V, F, N, ends=None, tendinous=False, ctx=None):
    """V (n,3) vertices (m), F (m,3) triangles, N (n,3) unit normals of one structure; ends: optional
    (origin, insertion) points (m); ctx: Context (bones). Returns (direction (n,3) unit tangent vectors,
    tendon (n,) in [0, 1])."""
    V, F, N = np.asarray(V, float), np.asarray(F, np.int64), np.asarray(N, float)
    n = len(V)
    axis = principal_axis(V)
    length = max(np.ptp(V @ axis), 1e-6)
    A = _adjacency(n, F)
    L = _cotan_laplacian(V, F)
    contact = np.zeros(n, bool)
    if ctx is not None and ctx.bones is not None:
        contact = ctx.bones.query(V, distance_upper_bound=CONTACT)[0] < CONTACT
    ncomp, comp = connected_components(A, directed=False)
    W = np.zeros((n, 3))
    for k in range(ncomp):
        idx = np.where(comp == k)[0]
        if len(idx) < 8:
            continue
        local = np.full(n, -1)
        local[idx] = np.arange(len(idx))
        Fk = local[F[np.all(local[F] >= 0, axis=1)]]
        Vk, Nk = V[idx], N[idx]
        seeds = _seeds(Vk, contact[idx], axis, length, ends)
        if seeds is None or not len(Fk):
            continue  # small detached piece: falls back on the axis
        h = np.mean(np.linalg.norm(Vk[Fk[:, 0]] - Vk[Fk[:, 1]], axis=1))
        Lk = L[idx][:, idx]
        # Unit directions away from the insertion and away from the origin, along the surface. Between the two
        # ends they are opposite; in a tendon that branches off (one landmark for several tendons) they agree,
        # so the insertion field leads.
        away_ins = _unit(_heat_direction(Lk, Vk, Fk, Nk, seeds[1], h))
        away_org = _unit(_heat_direction(Lk, Vk, Fk, Nk, seeds[0], h))
        W[idx] = 2 * away_ins - away_org
    deg = np.asarray(A.sum(1)).ravel()
    avg = sp.diags(1 / np.maximum(deg, 1)) @ A
    # The app draws streaks a millimetre apart, several millimetres long: the field must be smooth at that scale
    # (a few degrees per millimetre), and tangent to the smoothed surface rather than to its sculpted relief.
    h = np.median(np.linalg.norm(V[F[:, 0]] - V[F[:, 1]], axis=1)) if len(F) else SMOOTH_RADIUS
    for _ in range(int(np.clip(2 * (SMOOTH_RADIUS / max(h, 1e-6)) ** 2, 3, 60))):
        W = 0.5 * W + 0.5 * (avg @ W)
    Ns = N.copy()
    for _ in range(10):
        Ns = 0.5 * Ns + 0.5 * (avg @ Ns)
    Ns = _unit(Ns)
    Ns[np.linalg.norm(Ns, axis=1) < 0.5] = N[np.linalg.norm(Ns, axis=1) < 0.5]
    W = _tangent(W, Ns)
    bad = np.linalg.norm(W, axis=1) < 1e-6
    W[bad] = _tangent(np.broadcast_to(axis, (bad.sum(), 3)), Ns[bad])
    bad = np.linalg.norm(W, axis=1) < 1e-6  # axis along the normal: any tangent
    W[bad] = np.cross(Ns[bad], [0.0, 0.0, 1.0] if abs(axis[2]) < 0.9 else [1.0, 0.0, 0.0])
    direction = _unit(W)

    if tendinous:
        return direction, np.ones(n)
    # Tendon: much thinner than the structure's body, and thin in absolute terms. Small muscles (face, deep neck,
    # intrinsic muscles of the foot) are left fleshy: their meshes are too coarse for the thickness, and their
    # tendons too small to show.
    T = thickness(V, N)
    ref = np.percentile(T, 90)
    tendon = _smoothstep(0.45 * ref, 0.25 * ref, T) * _smoothstep(THIN_ABS, 0.55 * THIN_ABS, T)
    tendon *= _smoothstep(MIN_LENGTH[0], MIN_LENGTH[1], length)
    for _ in range(5):
        tendon = 0.5 * tendon + 0.5 * (avg @ tendon)
    return direction, np.clip(tendon, 0, 1)


def annotate(items, landmarks, system="muscles", log=print):
    """Adds `fiber` (n,3, glTF frame) and `tendon` (n,) to each item of `system`, aligned with the vertices of its
    published mesh. landmarks: the model's landmarks (glTF frame), for the origin and insertion of muscles."""
    from .model import BP3D_TO_GLTF, normals, to_gltf

    bones = [to_gltf(x["mesh"].vertices) for x in items if x["system"] == "os"]
    ctx = Context(np.concatenate(bones) if bones else None)
    stats = {"landmarks": 0, "axis": 0, "tendinous": 0}
    for x in items:
        if x["system"] != system:
            continue
        mesh = x["mesh"]
        V, N = to_gltf(mesh.vertices), normals(mesh) @ BP3D_TO_GLTF.T
        ends = ends_of(landmarks, x["id"])
        tendinous = bool(TENDINOUS.search(x["en"]))
        x["fiber"], x["tendon"] = structure_fibers(V, np.asarray(mesh.faces), N, ends, tendinous, ctx)
        stats["tendinous" if tendinous else "landmarks" if ends is not None else "axis"] += 1
    log(f"fibres ({system}): {stats}")
