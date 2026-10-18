"""Keep registered structures under the skin of the whole-body model.

The skin of BodyParts3D is a closed shell about 2 mm thick (outer and inner surfaces joined at the
orifices; the palpebral fissures are open, so the eyeballs are rasterised with it). The body is voxelised (VOXEL mm): the shell is rasterised, then the outside is flood-filled from
the corner of the grid; everything the flood does not reach is the body. A signed distance to the outside
(positive in the body: depth under the outer surface of the skin) is computed on the grid and interpolated.

`under_skin` moves the parts of a mesh that stick out of the skin, or lie closer than `margin` to its outer
surface, inwards along the gradient of that depth. Each displacement is spread over the mesh vertices within
`radius` (the largest one wins), so a nerve tube moves as a whole instead of being flattened against the skin.
"""
import numpy as np
from scipy import ndimage
from scipy.spatial import cKDTree

VOXEL = 2.0  # mm
MIN_VOLUME_L = 40.0  # a body smaller than this means the flood leaked into it through a gap of the shell


def _surface_points(mesh, step, batch=20000):
    """Points covering every triangle of a mesh, no farther apart than `step` (barycentric grid per
    triangle), yielded by batches of triangles."""
    tri = np.asarray(mesh.vertices, float)[np.asarray(mesh.faces)]
    edge = np.linalg.norm(tri - np.roll(tri, 1, axis=1), axis=2).max(1)
    n = np.maximum(1, np.ceil(edge / step).astype(int))
    for k in np.unique(n):
        i, j = np.meshgrid(np.arange(k + 1), np.arange(k + 1), indexing="ij")
        keep = i + j <= k
        a, b = i[keep] / k, j[keep] / k
        w = np.stack([1 - a - b, a, b], axis=1)  # (m, 3)
        t = tri[n == k]
        for s in range(0, len(t), batch):
            yield np.einsum("mk,tkd->tmd", w, t[s:s + batch]).reshape(-1, 3)


class Body:
    """Signed depth under the skin (mm): positive inside the body, negative outside."""

    def __init__(self, skin, blockers=()):
        # The palpebral fissures are open (the shell is joined around them): the eyeballs close them.
        meshes = (skin, *blockers)
        lo = np.min([m.bounds[0] for m in meshes], axis=0)
        hi = np.max([m.bounds[1] for m in meshes], axis=0)
        self.origin = lo - 3 * VOXEL
        shell = np.zeros(np.ceil((hi + 3 * VOXEL - self.origin) / VOXEL).astype(int) + 1, bool)
        for m in meshes:
            for pts in _surface_points(m, VOXEL / 2):
                idx = np.floor((pts - self.origin) / VOXEL).astype(np.int32)
                shell[idx[:, 0], idx[:, 1], idx[:, 2]] = True
        labels, _ = ndimage.label(~shell)  # 6-connected: a rasterised surface stops the flood
        outside = labels == labels[0, 0, 0]
        volume = (~outside).sum() * VOXEL ** 3 / 1e6
        if volume < MIN_VOLUME_L:
            raise SystemExit(f"skin voxelisation: body volume {volume:.0f} L, the shell leaks")
        del labels
        # Distances between voxel centres; the outermost body voxels hold the outer surface (depth 0 there).
        depth = ndimage.distance_transform_edt(~outside).astype(np.float32)
        depth -= ndimage.distance_transform_edt(outside).astype(np.float32)
        depth[~outside] -= 1
        # Smoothed a little: the gradient of a raw distance map turns by steps from one voxel to the next.
        self.depth = ndimage.gaussian_filter(depth * VOXEL, 1.0)
        self.volume = volume

    def __call__(self, p):
        g = (np.asarray(p, float) - self.origin) / VOXEL - 0.5  # value i of the grid is the centre of voxel i
        return ndimage.map_coordinates(self.depth, g.T, order=1, mode="nearest")

    def inward(self, p):
        """Unit gradient of the depth (pointing into the body)."""
        h = 2 * VOXEL
        g = np.stack([self(p + h * e) - self(p - h * e) for e in np.eye(3)], axis=1)
        return g / np.maximum(np.linalg.norm(g, axis=1, keepdims=True), 1e-9)


def under_skin(vertices, body, margin=2.5, radius=4.0, iterations=3):
    """Vertices (mm) moved so that none lies outside the skin or within `margin` of its outer surface.

    Returns (new vertices, number of vertices that needed a move, largest move in mm)."""
    v = np.asarray(vertices, float)
    bad = np.flatnonzero(body(v) < margin)
    if not len(bad):
        return v, 0, 0.0
    p = v[bad].copy()
    for _ in range(iterations):  # the gradient bends near the joints of the skin: step, then look again
        need = np.maximum(margin - body(p), 0.0)
        if not need.any():
            break
        p += body.inward(p) * need[:, None]
    move = p - v[bad]
    mag = np.linalg.norm(move, axis=1)
    # Spread: each vertex within `radius` of a moved one takes the largest move among them.
    tree = cKDTree(v[bad])
    out = v.copy()
    close = np.flatnonzero(tree.query(v, distance_upper_bound=radius)[0] <= radius)
    for i, nb in zip(close, tree.query_ball_point(v[close], radius)):
        out[i] = v[i] + move[nb[int(np.argmax(mag[nb]))]]
    return out, len(bad), float(mag.max())
