"""Minimal reader of mesh objects in a Blender .blend file (no Blender needed), for Z-Anatomy's Startup.blend.

Only what the pipeline needs: object names, world matrices, parents, modifiers' types, the triangles of meshes
(vertex positions and polygons) and the Bezier or poly splines of curves, with `tube` to sweep them. The file is parsed as data (header, file blocks, SDNA struct descriptions):
nothing in it is executed. Supports uncompressed little-endian files with 8-byte pointers, as written by
Blender 3.x (Z-Anatomy's Startup.blend is Blender 3.5, "BLENDER-v305"): vertex positions in the legacy MVert
array or in the generic "position" attribute, polygons as MPoly + MLoop or as "poly_offset_indices" +
".corner_vert".
"""
import mmap
import struct

import numpy as np

CD_MVERT, CD_MPOLY, CD_MLOOP, CD_PROP_FLOAT3, CD_PROP_INT32 = 0, 25, 26, 48, 11


class Blend:
    def __init__(self, path):
        self._f = open(path, "rb")
        self.buf = mmap.mmap(self._f.fileno(), 0, access=mmap.ACCESS_READ)
        head = self.buf[:12]
        if head[:7] != b"BLENDER" or head[7:9] != b"-v":
            raise ValueError(f"{path}: not an uncompressed little-endian 64-bit .blend file ({head!r})")
        self.version = int(head[9:12])
        self.blocks, self.by_ptr = [], {}
        off = 12
        while True:
            code, size, old, sdna, count = struct.unpack_from("<4siQii", self.buf, off)
            off += 24
            if code == b"ENDB":
                break
            if size < 0 or off + size > len(self.buf):
                raise ValueError(f"{path}: corrupt block at {off}")
            blk = (code.rstrip(b"\0").decode("latin-1"), off, size, old, sdna, count)
            self.blocks.append(blk)
            if old:
                # Blender may reuse the address of a temporary buffer for several blocks (3.5 writes legacy
                # MVert arrays from temporary copies): keep them all, resolved by file position (`block`).
                self.by_ptr.setdefault(old, []).append(len(self.blocks) - 1)
            if code == b"DNA1":
                self._sdna(off)
            off += size
        self.struct_index = {self.types[t]: i for i, (t, _) in enumerate(self.structs)}

    def close(self):
        self.buf.close(); self._f.close()

    def _sdna(self, off):
        b = self.buf
        assert b[off:off + 8] == b"SDNANAME"
        p = off + 8
        al = lambda q: off + ((q - off + 3) & ~3)  # alignment is relative to the start of the block

        def strings(p):
            n, = struct.unpack_from("<i", b, p); p += 4
            out = []
            for _ in range(n):
                e = b.find(b"\0", p)
                out.append(b[p:e].decode("latin-1")); p = e + 1
            return out, al(p)

        self.names, p = strings(p)
        assert b[p:p + 4] == b"TYPE"
        self.types, p = strings(p + 4)
        assert b[p:p + 4] == b"TLEN"
        self.tlen = list(struct.unpack_from(f"<{len(self.types)}h", b, p + 4))
        p = al(p + 4 + 2 * len(self.types))
        assert b[p:p + 4] == b"STRC"
        n, = struct.unpack_from("<i", b, p + 4); p += 8
        self.structs = []
        for _ in range(n):
            t, nf = struct.unpack_from("<hh", b, p); p += 4
            fields = struct.unpack_from(f"<{2 * nf}h", b, p); p += 4 * nf
            self.structs.append((t, [(fields[2 * i], fields[2 * i + 1]) for i in range(nf)]))
        self._layouts = {}

    def layout(self, type_name):
        """{field name (without * and [..]): (offset, type name, raw DNA name)} of a struct."""
        if type_name in self._layouts:
            return self._layouts[type_name]
        _, fields = self.structs[self.struct_index[type_name]]
        out, off = {}, 0
        for t, n in fields:
            raw = self.names[n]
            if raw.startswith("*") or raw.startswith("(*"):
                size = 8
            else:
                size = self.tlen[t]
            mult = 1
            for dim in raw.split("[")[1:]:
                mult *= int(dim.rstrip("]"))
            key = raw.lstrip("*(").split("[")[0].split(")")[0]
            out[key] = (off, self.types[t], raw)
            off += size * mult
        assert off == self.tlen[self.struct_index_type(type_name)], type_name
        self._layouts[type_name] = out
        return out

    def struct_index_type(self, type_name):
        return self.structs[self.struct_index[type_name]][0]

    def size(self, type_name):
        return self.tlen[self.struct_index_type(type_name)]

    # Field accessors on a struct at an absolute file offset.
    def field_off(self, type_name, base, name):
        return base + self.layout(type_name)[name][0]

    def i32(self, type_name, base, name):
        return struct.unpack_from("<i", self.buf, self.field_off(type_name, base, name))[0]

    def ptr(self, type_name, base, name):
        return struct.unpack_from("<Q", self.buf, self.field_off(type_name, base, name))[0]

    def string(self, type_name, base, name, n=66):
        p = self.field_off(type_name, base, name)
        raw = self.buf[p:p + n]
        return raw.split(b"\0", 1)[0].decode("utf-8", "replace")

    def floats(self, type_name, base, name, n):
        return np.frombuffer(self.buf, "<f4", n, self.field_off(type_name, base, name)).copy()

    def block(self, ptr, near=None):
        """(offset, size, struct name, count) of the block an old pointer points to (start of block only).

        A pointer shared by several blocks resolves to the first one written after file offset `near` (Blender
        writes the arrays of a struct right after it), or to the only one."""
        if not ptr or ptr not in self.by_ptr:
            raise KeyError(f"dangling pointer {ptr:#x}")
        cands = self.by_ptr[ptr]
        if len(cands) > 1:
            if near is None:
                raise ValueError(f"ambiguous pointer {ptr:#x}")
            after = [i for i in cands if self.blocks[i][1] > near]
            if not after:
                raise ValueError(f"pointer {ptr:#x}: no block after offset {near}")
            i = after[0]
        else:
            i = cands[0]
        _, off, size, _, sdna, count = self.blocks[i]
        return off, size, self.types[self.structs[sdna][0]], count

    def list_blocks(self, code):
        return [(off, size) for c, off, size, _, _, _ in self.blocks if c == code]

    # --- objects and meshes ---

    def objects(self):
        """{object name: (Object struct offset)} of every object (ID code OB)."""
        out = {}
        for off, _ in self.list_blocks("OB"):
            out[self.string("ID", self.field_off("Object", off, "id"), "name")[2:]] = off
        return out

    def object_info(self, off):
        """(type, data pointer, world matrix 4x4 (column-major as stored -> returned so v' = M @ [v, 1]),
        [modifier types], parent pointer)."""
        typ = struct.unpack_from("<h", self.buf, self.field_off("Object", off, "type"))[0]
        mat = self.floats("Object", off, "obmat" if "obmat" in self.layout("Object") else "object_to_world", 16)
        mods, p = [], self.ptr("Object", off, "modifiers")  # ListBase.first is the first field
        while p:
            moff, _, _, _ = self.block(p, off)
            mods.append(self.i32("ModifierData", moff, "type"))
            p = self.ptr("ModifierData", moff, "next")
        return typ, self.ptr("Object", off, "data"), mat.reshape(4, 4).T, mods, self.ptr("Object", off, "parent")

    def _layers(self, mesh_off, which):
        """[(type, name, data pointer)] of a CustomData of a Mesh (vdata, pdata, ldata)."""
        cd = self.field_off("Mesh", mesh_off, which)
        n = self.i32("CustomData", cd, "totlayer")
        p = self.ptr("CustomData", cd, "layers")
        if not n:
            return []
        loff, _, _, _ = self.block(p, mesh_off)
        sz = self.size("CustomDataLayer")
        out = []
        for i in range(n):
            lo = loff + i * sz
            out.append((self.i32("CustomDataLayer", lo, "type"), self.string("CustomDataLayer", lo, "name", 68),
                        self.ptr("CustomDataLayer", lo, "data"), lo))
        return out

    def _array(self, ptr, dtype, n, near):
        off, size, _, _ = self.block(ptr, near)
        a = np.frombuffer(self.buf, dtype, n, off)
        if a.nbytes > size:
            raise ValueError("array larger than its block")
        return a

    def _records(self, ptr, near, struct_name, n, field, dtype, width):
        """Column `field` (width values of dtype) of an array of n structs, checked against its block."""
        off, size, st, cnt = self.block(ptr, near)
        stride = self.size(struct_name)
        if st != struct_name or cnt < n or size < n * stride:
            raise ValueError(f"expected {n} {struct_name}, block holds {cnt} {st}")
        raw = np.frombuffer(self.buf, np.uint8, n * stride, off).reshape(n, stride)
        o = self.layout(struct_name)[field][0]
        return raw[:, o:o + 4 * width].copy().view(dtype).reshape(n, width)

    def mesh(self, mesh_off):
        """(vertices (n, 3) float64, triangles (m, 3) int64) of a Mesh, in its local frame; polygons as fans."""
        nv, npoly, nloop = (self.i32("Mesh", mesh_off, k) for k in ("totvert", "totpoly", "totloop"))
        vl, pl, ll = (self._layers(mesh_off, k) for k in ("vdata", "pdata", "ldata"))
        pos = next(((p, lo) for t, nm, p, lo in vl if t == CD_PROP_FLOAT3 and nm == "position"), None)
        if pos is not None:
            v = self._array(pos[0], "<f4", nv * 3, pos[1]).reshape(-1, 3)
        else:
            p, lo = next((p, lo) for t, _, p, lo in vl if t == CD_MVERT)
            v = self._records(p, lo, "MVert", nv, "co", "<f4", 3)
        if npoly == 0:  # vertices or edges only (Z-Anatomy's label helpers)
            return v.astype(np.float64), np.zeros((0, 3), np.int64)
        corner = next(((p, lo) for t, nm, p, lo in ll if t == CD_PROP_INT32 and nm == ".corner_vert"), None)
        if corner is not None:
            loops = self._array(corner[0], "<i4", nloop, corner[1])
        else:
            p, lo = next((p, lo) for t, _, p, lo in ll if t == CD_MLOOP)
            loops = self._records(p, lo, "MLoop", nloop, "v", "<i4", 1).ravel()
        p, lo = next((p, lo) for t, _, p, lo in pl if t == CD_MPOLY)
        start = self._records(p, lo, "MPoly", npoly, "loopstart", "<i4", 1).ravel()
        total = self._records(p, lo, "MPoly", npoly, "totloop", "<i4", 1).ravel()
        if start.min() < 0 or (start + total).max() > nloop:
            raise ValueError("polygon loops out of range")
        tris = []
        for k in range(3, int(total.max(initial=3)) + 1):
            sel = total == k
            if not sel.any():
                continue
            s = start[sel]
            for j in range(1, k - 1):
                tris.append(np.stack([loops[s], loops[s + j], loops[s + j + 1]], 1))
        f = np.concatenate(tris) if tris else np.zeros((0, 3), np.int64)
        if len(f) and (f.min() < 0 or f.max() >= nv):
            raise ValueError("face index out of range")
        return v.astype(np.float64), f.astype(np.int64)

    # --- curves (Bezier splines with a round bevel), as Z-Anatomy draws its vessels and nerves ---

    def splines(self, curve_off):
        """[(points (n, 3), radii (n,), cyclic)] of the Bezier and poly splines of a Curve, sampled like Blender
        (resolu segments between control points), in the curve's local frame; and the bevel depth."""
        lay = self.layout("Curve")
        resolu = struct.unpack_from("<h", self.buf, curve_off + lay["resolu"][0])[0]
        depth = struct.unpack_from("<f", self.buf, curve_off + lay["ext2"][0])[0]
        for k in ("bevobj", "taperobj"):
            if self.ptr("Curve", curve_off, k):
                raise ValueError(f"curve with a {k}: unsupported")
        out, p = [], self.ptr("Curve", curve_off, "nurb")
        nl = self.layout("Nurb")
        while p:
            no = self.block(p, curve_off)[0]
            typ, flagu = (struct.unpack_from("<h", self.buf, no + nl[k][0])[0] for k in ("type", "flagu"))
            n = struct.unpack_from("<i", self.buf, no + nl["pntsu"][0])[0]
            res = struct.unpack_from("<h", self.buf, no + nl["resolu"][0])[0] or resolu
            cyclic = bool(flagu & 1)
            if typ == 1:  # CU_BEZIER
                stride, bl = self.size("BezTriple"), self.layout("BezTriple")
                raw = np.frombuffer(self.buf, np.uint8, n * stride, self.block(self.ptr("Nurb", no, "bezt"), no)[0])
                raw = raw.reshape(n, stride)
                vec = raw[:, :36].copy().view("<f4").reshape(n, 3, 3).astype(float)  # handle 1, knot, handle 2
                rad = raw[:, bl["radius"][0]:bl["radius"][0] + 4].copy().view("<f4").ravel().astype(float)
                segs = n if cyclic else n - 1
                t = np.linspace(0, 1, res, endpoint=False)[:, None]
                pts, rads = [], []
                for i in range(segs):
                    j = (i + 1) % n
                    p0, p1, p2, p3 = vec[i, 1], vec[i, 2], vec[j, 0], vec[j, 1]
                    pts.append((1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1 + 3 * (1 - t) * t ** 2 * p2 + t ** 3 * p3)
                    s = t[:, 0] * t[:, 0] * (3 - 2 * t[:, 0])  # smooth radius between control points
                    rads.append(rad[i] + (rad[j] - rad[i]) * s)
                if not cyclic:
                    pts.append(vec[-1:, 1]); rads.append(rad[-1:])
                pts, rads = np.concatenate(pts), np.concatenate(rads)
            elif typ == 0:  # CU_POLY
                stride, bl = self.size("BPoint"), self.layout("BPoint")
                raw = np.frombuffer(self.buf, np.uint8, n * stride, self.block(self.ptr("Nurb", no, "bp"), no)[0])
                raw = raw.reshape(n, stride)
                pts = raw[:, :12].copy().view("<f4").reshape(n, 3).astype(float)
                rads = raw[:, bl["radius"][0]:bl["radius"][0] + 4].copy().view("<f4").ravel().astype(float)
            else:
                raise ValueError(f"spline type {typ} unsupported")
            out.append((pts, rads, cyclic))
            p = self.ptr("Nurb", no, "next")
        return out, depth


def tube(points, radii, sides=12, caps=True):
    """Closed tube mesh (vertices, triangles) of a polyline with a radius per point (parallel-transport frames)."""
    keep = np.r_[True, np.linalg.norm(np.diff(points, axis=0), axis=1) > 1e-9]
    points, radii = points[keep], np.maximum(radii[keep], 1e-6)
    n = len(points)
    if n < 2:
        return np.zeros((0, 3)), np.zeros((0, 3), np.int64)
    tang = np.gradient(points, axis=0)
    tang /= np.linalg.norm(tang, axis=1, keepdims=True)
    ref = np.eye(3)[np.argmin(np.abs(tang[0]))]
    u = np.cross(tang[0], ref); u /= np.linalg.norm(u)
    us = [u]
    for i in range(1, n):
        u = u - tang[i] * (u @ tang[i])
        u /= np.linalg.norm(u)
        us.append(u)
    us = np.array(us)
    vs = np.cross(tang, us)
    a = np.linspace(0, 2 * np.pi, sides, endpoint=False)
    ring = (np.cos(a)[None, :, None] * us[:, None] + np.sin(a)[None, :, None] * vs[:, None]) * radii[:, None, None]
    v = (points[:, None] + ring).reshape(-1, 3)
    i = np.arange(n - 1)[:, None] * sides
    k = np.arange(sides)[None]
    k1 = (k + 1) % sides
    f = np.concatenate([np.stack([i + k, i + k1, i + sides + k1], -1).reshape(-1, 3),
                        np.stack([i + k, i + sides + k1, i + sides + k], -1).reshape(-1, 3)])
    if caps:
        c0, c1 = len(v), len(v) + 1
        v = np.concatenate([v, points[:1], points[-1:]])
        last = (n - 1) * sides
        f = np.concatenate([f, np.stack([np.full(sides, c0), k1[0], k[0]], 1),
                            np.stack([np.full(sides, c1), last + k[0], last + k1[0]], 1)])
    return v, f.astype(np.int64)
