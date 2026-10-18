"""Junctions of the vascular tree: distance between two meshes, and the parent -> branch pairs that must touch.

BodyParts3D cuts each vessel into one mesh per concept; a branch starts against (most often through) the wall of its
parent. check.py measures the pairs below on the published glb, so that a change of the decimation or of the
selection cannot open them. The distance is between surfaces: the distance between nearest vertices, several
millimetres on coarse tubes whose triangles are 50 mm long, says nothing about a gap.
"""
import numpy as np
import trimesh
from scipy.spatial import cKDTree

# Published distance allowed between the meshes of a junction that is closed in the source (mm).
MAX_GAP = 1.0

# Parent -> branch (or tributary) pairs of full_body, from the aorta and the venae cavae to the limbs: their meshes
# touch or cross in the BodyParts3D source (surface distance 0, measured with mesh_distance). Junctions that are open in
# the source itself are not listed, the build cannot close them: common -> internal carotid (63 mm),
# subclavian -> vertebral artery (50 mm), popliteal -> posterior tibial vein (36 mm).
JUNCTIONS = {
    "full_body": [
        ("FMA3736", "FMA3768"),  # ascending aorta -> arch of aorta
        ("FMA3768", "FMA3932"),  # arch of aorta -> brachiocephalic artery
        ("FMA3768", "FMA4058"),  # arch of aorta -> left common carotid artery
        ("FMA3768", "FMA4694"),  # arch of aorta -> left subclavian artery
        ("FMA3768", "FMA87217"),  # arch of aorta -> descending thoracic aorta
        ("FMA87217", "FMA259248"),  # descending thoracic aorta -> content of abdomen (abdominal aorta)
        ("FMA3932", "FMA3941"),  # brachiocephalic artery -> right common carotid artery
        ("FMA3932", "FMA3953"),  # brachiocephalic artery -> right subclavian artery
        ("FMA3953", "FMA22655"),  # right subclavian artery -> right axillary artery
        ("FMA4694", "FMA22656"),  # left subclavian artery -> left axillary artery
        ("FMA22655", "FMA22691"),  # right axillary artery -> right brachial artery
        ("FMA22656", "FMA22692"),  # left axillary artery -> left brachial artery
        ("FMA22691", "FMA22733"),  # right brachial artery -> right radial artery
        ("FMA22691", "FMA22797"),  # right brachial artery -> right ulnar artery
        ("FMA22692", "FMA22734"),  # left brachial artery -> left radial artery
        ("FMA22692", "FMA22798"),  # left brachial artery -> left ulnar artery
        ("FMA259248", "FMA14812"),  # content of abdomen -> celiac trunk
        ("FMA259248", "FMA66358"),  # content of abdomen -> trunk of superior mesenteric artery
        ("FMA259248", "FMA66363"),  # content of abdomen -> trunk of right renal artery
        ("FMA259248", "FMA66364"),  # content of abdomen -> trunk of left renal artery
        ("FMA259248", "FMA14753"),  # content of abdomen -> left renal artery
        ("FMA259248", "FMA14752"),  # content of abdomen -> right renal artery
        ("FMA3784", "FMA14750"),  # descending aorta -> inferior mesenteric artery
        ("FMA259248", "FMA14765"),  # content of abdomen -> right common iliac artery
        ("FMA259248", "FMA14766"),  # content of abdomen -> left common iliac artery
        ("FMA14765", "FMA18806"),  # right common iliac artery -> right external iliac artery
        ("FMA14765", "FMA18809"),  # right common iliac artery -> right internal iliac artery
        ("FMA14766", "FMA18807"),  # left common iliac artery -> left external iliac artery
        ("FMA14766", "FMA18810"),  # left common iliac artery -> left internal iliac artery
        ("FMA18806", "FMA70249"),  # right external iliac artery -> right femoral artery
        ("FMA18807", "FMA70250"),  # left external iliac artery -> left femoral artery
        ("FMA70249", "FMA77380"),  # right femoral artery -> right popliteal artery
        ("FMA70250", "FMA77381"),  # left femoral artery -> left popliteal artery
        ("FMA77380", "FMA43896"),  # right popliteal artery -> right anterior tibial artery
        ("FMA77380", "FMA43898"),  # right popliteal artery -> right posterior tibial artery
        ("FMA77381", "FMA43897"),  # left popliteal artery -> left anterior tibial artery
        ("FMA77381", "FMA43899"),  # left popliteal artery -> left posterior tibial artery
        ("FMA3958", "FMA50542"),  # right vertebral artery -> basilar artery
        ("FMA4066", "FMA50542"),  # left vertebral artery -> basilar artery
        ("FMA8612", "FMA50872"),  # pulmonary trunk -> right pulmonary artery
        ("FMA8612", "FMA50873"),  # pulmonary trunk -> left pulmonary artery
        ("FMA4720", "FMA4751"),  # superior vena cava -> right brachiocephalic vein
        ("FMA4720", "FMA4761"),  # superior vena cava -> left brachiocephalic vein
        ("FMA4720", "FMA4838"),  # superior vena cava -> azygos vein
        ("FMA4751", "FMA4754"),  # right brachiocephalic vein -> right internal jugular vein
        ("FMA4751", "FMA4755"),  # right brachiocephalic vein -> right subclavian vein
        ("FMA4761", "FMA4762"),  # left brachiocephalic vein -> left internal jugular vein
        ("FMA4761", "FMA4763"),  # left brachiocephalic vein -> left subclavian vein
        ("FMA4755", "FMA13330"),  # right subclavian vein -> right axillary vein
        ("FMA4763", "FMA13331"),  # left subclavian vein -> left axillary vein
        ("FMA13330", "FMA13325"),  # right axillary vein -> right cephalic vein
        ("FMA13330", "FMA22909"),  # right axillary vein -> right basilic vein
        ("FMA13331", "FMA13326"),  # left axillary vein -> left cephalic vein
        ("FMA13331", "FMA22910"),  # left axillary vein -> left basilic vein
        ("FMA4838", "FMA4944"),  # azygos vein -> hemiazygos vein
        ("FMA10951", "FMA21387"),  # inferior vena cava -> right common iliac vein
        ("FMA10951", "FMA21388"),  # inferior vena cava -> left common iliac vein
        ("FMA10951", "FMA14336"),  # inferior vena cava -> left renal vein
        ("FMA10951", "FMA14335"),  # inferior vena cava -> right renal vein
        ("FMA10951", "FMA14338"),  # inferior vena cava -> right hepatic vein
        ("FMA10951", "FMA14339"),  # inferior vena cava -> left hepatic vein
        ("FMA10951", "FMA14340"),  # inferior vena cava -> middle hepatic vein
        ("FMA10951", "FMA14341"),  # inferior vena cava -> right testicular vein
        ("FMA10951", "FMA14343"),  # inferior vena cava -> right suprarenal vein
        ("FMA21387", "FMA18885"),  # right common iliac vein -> right external iliac vein
        ("FMA21387", "FMA18887"),  # right common iliac vein -> right internal iliac vein
        ("FMA21388", "FMA18886"),  # left common iliac vein -> left external iliac vein
        ("FMA21388", "FMA18888"),  # left common iliac vein -> left internal iliac vein
        ("FMA18885", "FMA21188"),  # right external iliac vein -> right femoral vein
        ("FMA18886", "FMA21189"),  # left external iliac vein -> left femoral vein
        ("FMA21188", "FMA44328"),  # right femoral vein -> right popliteal vein
        ("FMA21188", "FMA21379"),  # right femoral vein -> right great saphenous vein
        ("FMA21189", "FMA44329"),  # left femoral vein -> left popliteal vein
        ("FMA21189", "FMA21380"),  # left femoral vein -> left great saphenous vein
        ("FMA44328", "FMA44336"),  # right popliteal vein -> right anterior tibial vein
        ("FMA44329", "FMA44337"),  # left popliteal vein -> left anterior tibial vein
        ("FMA50735", "FMA14332"),  # hepatic portal vein -> superior mesenteric vein
        ("FMA14332", "FMA14331"),  # superior mesenteric vein -> splenic vein
        ("FMA14331", "FMA15391"),  # splenic vein -> inferior mesenteric vein
        ("FMA14336", "FMA14345"),  # left renal vein -> left testicular vein
        ("FMA14336", "FMA14349"),  # left renal vein -> left suprarenal vein
    ],
}


def _edge_lengths(v, f):
    return np.linalg.norm(v[f] - v[np.roll(f, 1, axis=1)], axis=2)


def _vertex_faces(f, n):
    """CSR map vertex -> incident faces."""
    order = np.argsort(f.reshape(-1), kind="stable")
    starts = np.searchsorted(f.reshape(-1)[order], np.arange(n + 1))
    return order // 3, starts


def _candidate_pairs(points, radius, tree, vf):
    """(point index, face index) pairs: faces incident to a vertex of `tree` within `radius` (scalar or one per
    point) of the point."""
    faces, starts = vf
    near = tree.query_ball_point(points, radius)
    counts = np.fromiter(map(len, near), int, len(near))
    if not counts.sum():
        return np.zeros(0, int), np.zeros(0, int)
    pi = np.repeat(np.arange(len(points)), counts)
    vj = np.fromiter((j for n in near for j in n), int, counts.sum())
    deg = starts[vj + 1] - starts[vj]
    pi = np.repeat(pi, deg)
    first = np.repeat(starts[vj], deg)
    offset = np.arange(len(first)) - np.repeat(np.cumsum(deg) - deg, deg)
    fi = faces[first + offset]
    key = np.unique(pi * (len(faces) + 1) + fi)
    return key // (len(faces) + 1), key % (len(faces) + 1)


def _point_triangle(points, tris):
    if not len(points):
        return np.inf
    return float(np.linalg.norm(trimesh.triangles.closest_point(tris, points) - points, axis=1).min())


def _segments_cross(seg, tris):
    """Whether any segment (n, 2, 3) crosses its paired triangle (n, 3, 3) (Moller-Trumbore)."""
    if not len(seg):
        return False
    o, d = seg[:, 0], seg[:, 1] - seg[:, 0]
    e1, e2 = tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0]
    h = np.cross(d, e2)
    a = np.einsum("ij,ij->i", e1, h)
    ok = np.abs(a) > 1e-12
    inv = np.where(ok, 1 / np.where(ok, a, 1), 0)
    sv = o - tris[:, 0]
    u = inv * np.einsum("ij,ij->i", sv, h)
    q = np.cross(sv, e1)
    v = inv * np.einsum("ij,ij->i", d, q)
    w = inv * np.einsum("ij,ij->i", e2, q)
    return bool(np.any(ok & (u >= 0) & (v >= 0) & (u + v <= 1) & (w >= 0) & (w <= 1)))


def _crop(v, f, other, margin):
    """Faces of (v, f) whose bounding box meets the bounding box of the points `other`, grown by `margin`."""
    lo, hi = other.min(axis=0) - margin, other.max(axis=0) + margin
    t = v[f]
    return f[np.all(t.max(axis=1) >= lo, axis=1) & np.all(t.min(axis=1) <= hi, axis=1)]


def mesh_distance(va, fa, vb, fb, step=1.5, cutoff=10.0):
    """Smallest distance (mm) between the surfaces of two triangle meshes (vertices, faces), 0 if they cross.

    Both meshes are first subdivided to edges of at most `step` mm (same surface): BodyParts3D tubes and decimated
    meshes have long axial triangles. Then exact vertex-triangle distances in both directions, and a test of edges
    crossing triangles; when the closest points both lie inside edges, the result exceeds the true distance by less
    than `step`. Beyond `cutoff` mm, returns the distance between the nearest vertices (an upper bound)."""
    va, vb = np.asarray(va, float), np.asarray(vb, float)
    fa, fb = np.asarray(fa, np.int64), np.asarray(fb, np.int64)
    # Only the faces that can be within `cutoff` of the other mesh matter.
    fa, fb = _crop(va, fa, vb, cutoff), _crop(vb, fb, va, cutoff)
    if not len(fa) or not len(fb):
        return float(cKDTree(vb).query(va)[0].min())
    va, fa = trimesh.remesh.subdivide_to_size(va, fa, step)
    vb, fb = trimesh.remesh.subdivide_to_size(vb, fb, step)
    ta, tb = cKDTree(va), cKDTree(vb)
    da, db = tb.query(va)[0], ta.query(vb)[0]
    d = float(min(da.min(), db.min()))
    if d > cutoff:
        return d
    la, lb = _edge_lengths(va, fa), _edge_lengths(vb, fb)
    # A closest point lies on a triangle whose vertices are within (d + edge length) of the other mesh's vertex.
    for (v, dist, other, of, ol) in ((va, da, tb, fb, lb), (vb, db, ta, fa, la)):
        r = d + ol.max() + 1e-9
        idx = np.flatnonzero(dist <= r)
        pi, fi = _candidate_pairs(v[idx], r, other, _vertex_faces(of, len(other.data)))
        d = min(d, _point_triangle(v[idx][pi], other.data[of[fi]]))
    if d < 1e-6:
        return 0.0
    # Crossing meshes: the middle of a crossing edge is within half its length of the other surface.
    if d <= max(la.max(), lb.max()):
        for (v, f, own, other, of, ol) in ((va, fa, la, tb, fb, lb), (vb, fb, lb, ta, fa, la)):
            e = np.unique(np.sort(np.concatenate([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]]), axis=1), axis=0)
            mid = v[e].mean(axis=1)
            r = own.max() / 2 + ol.max() + 1e-9
            near = np.flatnonzero(np.isfinite(other.query(mid, distance_upper_bound=r)[0]))
            ei, fi = _candidate_pairs(mid[near], r, other, _vertex_faces(of, len(other.data)))
            if _segments_cross(v[e[near][ei]], other.data[of[fi]]):
                return 0.0
    return d

