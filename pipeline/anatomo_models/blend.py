"""Minimal reader of mesh objects in a Blender .blend file (no Blender needed), for Z-Anatomy's Startup.blend.

Only what the pipeline needs: object names, world matrices, parents, modifiers' types, the triangles of meshes
(vertex positions and polygons) and the Bezier or poly splines of curves, with `tube` to sweep them. The file is parsed as data (header, file blocks, SDNA struct descriptions):
nothing in it is executed. Supports uncompressed little-endian files with 8-byte pointers, as written by
Blender 3.x (Z-Anatomy's Startup.blend is Blender 3.5, "BLENDER-v305"): vertex positions in the legacy MVert
array or in the generic "position" attribute, polygons as MPoly + MLoop or as "poly_offset_indices" +
".corner_vert".

The file is untrusted input: every offset, count and index read from it is checked against the file, its block or
the SDNA tables before use, and a malformed file raises ValueError (never an assert, which `python -O` drops).
"""
import mmap
import struct

import numpy as np

CD_MVERT, CD_MPOLY, CD_MLOOP, CD_PROP_FLOAT3, CD_PROP_INT32 = 0, 25, 26, 48, 11


class Blend:
    def __init__(self, path):
        self._f = open(path, "rb")
        try:
            self.buf = mmap.mmap(self._f.fileno(), 0, access=mmap.ACCESS_READ)
        except ValueError:  # empty file
            self._f.close()
            raise ValueError(f"{path}: empty file")
        try:
            self._parse(path)
        except (ValueError, KeyError, IndexError, struct.error) as e:
            self.close()
            raise ValueError(f"{path}: malformed .blend file: {e}") from e

    def _parse(self, path):
        head = self.buf[:12]
        if len(head) < 12 or head[:7] != b"BLENDER" or head[7:9] != b"-v" or not head[9:12].isdigit():
            raise ValueError(f"not an uncompressed little-endian 64-bit .blend file ({head!r})")
        self.version = int(head[9:12])
        self.blocks, self.by_ptr, self.at = [], {}, {}
        self.names = self.types = self.tlen = self.structs = None
        off = 12
        while True:
            if off + 24 > len(self.buf):
                raise ValueError("no ENDB block")
            code, size, old, sdna, count = struct.unpack_from("<4siQii", self.buf, off)
            off += 24
            if code == b"ENDB":
                break
            if size < 0 or count < 0 or off + size > len(self.buf):
                raise ValueError(f"corrupt block at {off}")
            blk = (code.rstrip(b"\0").decode("latin-1"), off, size, old, sdna, count)
            self.blocks.append(blk)
            self.at[off] = len(self.blocks) - 1
            if old:
                # Blender may reuse the address of a temporary buffer for several blocks (3.5 writes legacy
                # MVert arrays from temporary copies): keep them all, resolved by file position (`block`).
                self.by_ptr.setdefault(old, []).append(len(self.blocks) - 1)
            if code == b"DNA1":
                if self.structs is not None:
                    raise ValueError("several DNA1 blocks")
                self._sdna(off, off + size)
            off += size
        if self.structs is None:
            raise ValueError("no DNA1 block")
        for _, _, _, _, sdna, _ in self.blocks:
            if not 0 <= sdna < len(self.structs):
                raise ValueError(f"block with SDNA index {sdna} out of range")
        self.struct_index = {self.types[t]: i for i, (t, _) in enumerate(self.structs)}

    def close(self):
        self.buf.close(); self._f.close()

    def _sdna(self, off, end):
        """Names, types, type lengths and struct descriptions of the DNA1 block [off, end), bounds-checked."""
        b = self.buf

        def need(p, n, what):
            if n < 0 or p < off or p + n > end:
                raise ValueError(f"SDNA: {what} beyond its block")

        def tag(p, t):
            need(p, 4, t.decode())
            if b[p:p + 4] != t:
                raise ValueError(f"SDNA: {t.decode()} expected at {p}")
            return p + 4

        def count(p, what, minsize):
            need(p, 4, what)
            n, = struct.unpack_from("<i", b, p)
            if n < 0 or n * minsize > end - p - 4:  # every item takes at least minsize bytes
                raise ValueError(f"SDNA: {n} {what} cannot fit in the block")
            return n, p + 4

        al = lambda q: off + ((q - off + 3) & ~3)  # alignment is relative to the start of the block

        def strings(p, what):
            n, p = count(p, what, 1)
            out = []
            for _ in range(n):
                e = b.find(b"\0", p, end)
                if e < 0:
                    raise ValueError(f"SDNA: unterminated {what} string")
                out.append(b[p:e].decode("latin-1")); p = e + 1
            return out, al(p)

        self.names, p = strings(tag(tag(off, b"SDNA"), b"NAME"), "names")
        self.types, p = strings(tag(p, b"TYPE"), "types")
        p = tag(p, b"TLEN")
        need(p, 2 * len(self.types), "TLEN")
        self.tlen = list(struct.unpack_from(f"<{len(self.types)}h", b, p))
        p = al(p + 2 * len(self.types))
        n, p = count(tag(p, b"STRC"), "structs", 4)
        structs = []
        for _ in range(n):
            need(p, 4, "struct")
            t, nf = struct.unpack_from("<hh", b, p); p += 4
            need(p, 4 * nf, "struct fields")
            fields = struct.unpack_from(f"<{2 * nf}h", b, p); p += 4 * nf
            fields = [(fields[2 * i], fields[2 * i + 1]) for i in range(nf)]
            if not 0 <= t < len(self.types) or any(not (0 <= ft < len(self.types) and 0 <= fn < len(self.names))
                                                   for ft, fn in fields):
                raise ValueError("SDNA: struct with a type or name index out of range")
            structs.append((t, fields))
        self.structs = structs
        self._layouts = {}

    def layout(self, type_name):
        """{field name (without * and [..]): (offset, type name, raw DNA name)} of a struct."""
        if type_name in self._layouts:
            return self._layouts[type_name]
        if type_name not in self.struct_index:
            raise ValueError(f"no struct {type_name} in the SDNA")
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
                dim = dim.rstrip("]")
                if not dim.isdigit():
                    raise ValueError(f"SDNA: bad array size in {raw!r}")
                mult *= int(dim)
            key = raw.lstrip("*(").split("[")[0].split(")")[0]
            out[key] = (off, self.types[t], raw)
            off += size * mult
        if off != self.tlen[self.struct_index_type(type_name)]:
            raise ValueError(f"SDNA: fields of {type_name} do not add up to its length")
        self._layouts[type_name] = out
        return out

    def struct_index_type(self, type_name):
        return self.structs[self.struct_index[type_name]][0]

    def size(self, type_name):
        return self.tlen[self.struct_index_type(type_name)]

    # Field accessors on a struct at an absolute file offset (callers check the struct lies in its block: `check`).
    def field_off(self, type_name, base, name):
        lay = self.layout(type_name)
        if name not in lay:
            raise ValueError(f"no field {name} in {type_name}")
        return base + lay[name][0]

    def check(self, off, type_name, n=1):
        """Raise ValueError unless a block starts at `off` holding at least n structs `type_name`."""
        i = self.at.get(off)
        if i is None:
            raise ValueError(f"no block at offset {off}")
        _, _, size, _, sdna, count = self.blocks[i]
        st = self.types[self.structs[sdna][0]]
        if st != type_name or count < n or size < n * self.size(type_name):
            raise ValueError(f"block at {off}: expected {n} {type_name}, holds {count} {st} in {size} bytes")
        return off

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
            raise ValueError(f"dangling pointer {ptr:#x}")
        cands = self.by_ptr[ptr]
        if near is not None and not 0 <= near <= len(self.buf):
            raise ValueError(f"offset {near} outside the file")
        if len(cands) > 1:
            if near is None:
                raise ValueError(f"ambiguous pointer {ptr:#x}")
            after = [i for i in cands if self.blocks[i][1] > near]
            if not after:
                raise ValueError(f"pointer {ptr:#x}: no block after offset {near}")
            i = after[0]
        else:
            i = cands[0]
        _, off, size, _, sdna, count = self.blocks[i]  # sdna checked in range when the file was opened
        return off, size, self.types[self.structs[sdna][0]], count

    def list_blocks(self, code):
        return [(off, size) for c, off, size, _, _, _ in self.blocks if c == code]

    # --- objects and meshes ---

    def objects(self):
        """{object name: (Object struct offset)} of every object (ID code OB)."""
        out = {}
        for off, _ in self.list_blocks("OB"):
            self.check(off, "Object")
            out[self.string("ID", self.field_off("Object", off, "id"), "name")[2:]] = off
        return out

    def object_info(self, off):
        """(type, data pointer, world matrix 4x4 (column-major as stored -> returned so v' = M @ [v, 1]),
        [modifier types], parent pointer)."""
        self.check(off, "Object")
        typ = struct.unpack_from("<h", self.buf, self.field_off("Object", off, "type"))[0]
        mat = self.floats("Object", off, "obmat" if "obmat" in self.layout("Object") else "object_to_world", 16)
        mods, p, seen = [], self.ptr("Object", off, "modifiers"), set()  # ListBase.first is the first field
        while p:
            if p in seen or len(seen) > 1000:
                raise ValueError("modifier list loops")
            seen.add(p)
            moff, size, _, _ = self.block(p, off)
            if size < self.size("ModifierData"):
                raise ValueError("modifier block too small")
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
        loff, size, st, cnt = self.block(p, mesh_off)
        sz = self.size("CustomDataLayer")
        if n < 0 or st != "CustomDataLayer" or cnt < n or size < n * sz:
            raise ValueError(f"expected {n} CustomDataLayer, block holds {cnt} {st}")
        out = []
        for i in range(n):
            lo = loff + i * sz
            out.append((self.i32("CustomDataLayer", lo, "type"), self.string("CustomDataLayer", lo, "name", 68),
                        self.ptr("CustomDataLayer", lo, "data"), lo))
        return out

    def _array(self, ptr, dtype, n, near):
        off, size, _, _ = self.block(ptr, near)
        if n < 0 or n * np.dtype(dtype).itemsize > size:
            raise ValueError("array larger than its block")
        return np.frombuffer(self.buf, dtype, n, off)

    def _records(self, ptr, near, struct_name, n, field, dtype, width):
        """Column `field` (width values of dtype) of an array of n structs, checked against its block."""
        off, size, st, cnt = self.block(ptr, near)
        stride = self.size(struct_name)
        if n < 0 or st != struct_name or cnt < n or size < n * stride:
            raise ValueError(f"expected {n} {struct_name}, block holds {cnt} {st}")
        raw = np.frombuffer(self.buf, np.uint8, n * stride, off).reshape(n, stride)
        o = self.layout(struct_name)[field][0]
        return raw[:, o:o + 4 * width].copy().view(dtype).reshape(n, width)

    def mesh(self, mesh_off):
        """(vertices (n, 3) float64, triangles (m, 3) int64) of a Mesh, in its local frame; polygons as fans."""
        self.check(mesh_off, "Mesh")
        nv, npoly, nloop = (self.i32("Mesh", mesh_off, k) for k in ("totvert", "totpoly", "totloop"))
        if min(nv, npoly, nloop) < 0:
            raise ValueError("negative element count")
        vl, pl, ll = (self._layers(mesh_off, k) for k in ("vdata", "pdata", "ldata"))
        pos = next(((p, lo) for t, nm, p, lo in vl if t == CD_PROP_FLOAT3 and nm == "position"), None)
        if pos is not None:
            v = self._array(pos[0], "<f4", nv * 3, pos[1]).reshape(-1, 3)
        else:
            p, lo = self._layer(vl, CD_MVERT)
            v = self._records(p, lo, "MVert", nv, "co", "<f4", 3)
        if npoly == 0:  # vertices or edges only (Z-Anatomy's label helpers)
            return v.astype(np.float64), np.zeros((0, 3), np.int64)
        corner = next(((p, lo) for t, nm, p, lo in ll if t == CD_PROP_INT32 and nm == ".corner_vert"), None)
        if corner is not None:
            loops = self._array(corner[0], "<i4", nloop, corner[1])
        else:
            p, lo = self._layer(ll, CD_MLOOP)
            loops = self._records(p, lo, "MLoop", nloop, "v", "<i4", 1).ravel()
        p, lo = self._layer(pl, CD_MPOLY)
        start = self._records(p, lo, "MPoly", npoly, "loopstart", "<i4", 1).ravel()
        total = self._records(p, lo, "MPoly", npoly, "totloop", "<i4", 1).ravel()
        if start.min() < 0 or total.min() < 0 or (start.astype(np.int64) + total).max() > nloop:
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

    @staticmethod
    def _layer(layers, typ):
        hit = next(((p, lo) for t, _, p, lo in layers if t == typ), None)
        if hit is None:
            raise ValueError(f"mesh without a layer of type {typ}")
        return hit

    # --- curves (Bezier splines with a round bevel), as Z-Anatomy draws its vessels and nerves ---

    def splines(self, curve_off):
        """[(points (n, 3), radii (n,), cyclic)] of the Bezier and poly splines of a Curve, sampled like Blender
        (resolu segments between control points), in the curve's local frame; and the bevel depth."""
        self.check(curve_off, "Curve")
        lay = self.layout("Curve")
        resolu = struct.unpack_from("<h", self.buf, curve_off + lay["resolu"][0])[0]
        depth = struct.unpack_from("<f", self.buf, curve_off + lay["ext2"][0])[0]
        for k in ("bevobj", "taperobj"):
            if self.ptr("Curve", curve_off, k):
                raise ValueError(f"curve with a {k}: unsupported")
        out, p = [], self.ptr("Curve", curve_off, "nurb")
        nl, seen = self.layout("Nurb"), set()
        while p:
            if p in seen or len(seen) > 10000:
                raise ValueError("spline list loops")
            seen.add(p)
            no, size, st, _ = self.block(p, curve_off)
            if st != "Nurb" or size < self.size("Nurb"):
                raise ValueError(f"expected a Nurb, block holds {st}")
            typ, flagu = (struct.unpack_from("<h", self.buf, no + nl[k][0])[0] for k in ("type", "flagu"))
            n = struct.unpack_from("<i", self.buf, no + nl["pntsu"][0])[0]
            res = struct.unpack_from("<h", self.buf, no + nl["resolu"][0])[0] or resolu
            if n < 1 or not 1 <= res <= 1024:
                raise ValueError(f"spline with {n} points and resolution {res}")
            cyclic = bool(flagu & 1)
            if typ == 1:  # CU_BEZIER
                stride, bl = self.size("BezTriple"), self.layout("BezTriple")
                raw = self._points(self.ptr("Nurb", no, "bezt"), no, "BezTriple", n)
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
                raw = self._points(self.ptr("Nurb", no, "bp"), no, "BPoint", n)
                pts = raw[:, :12].copy().view("<f4").reshape(n, 3).astype(float)
                rads = raw[:, bl["radius"][0]:bl["radius"][0] + 4].copy().view("<f4").ravel().astype(float)
            else:
                raise ValueError(f"spline type {typ} unsupported")
            out.append((pts, rads, cyclic))
            p = self.ptr("Nurb", no, "next")
        return out, depth

    def _points(self, ptr, near, struct_name, n):
        """(n, struct size) bytes of the n control points of a spline, checked against their block."""
        off, size, st, cnt = self.block(ptr, near)
        stride = self.size(struct_name)
        if st != struct_name or cnt < n or size < n * stride:
            raise ValueError(f"expected {n} {struct_name}, block holds {cnt} {st}")
        return np.frombuffer(self.buf, np.uint8, n * stride, off).reshape(n, stride)


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
