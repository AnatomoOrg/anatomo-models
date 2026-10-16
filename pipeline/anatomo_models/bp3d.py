"""BodyParts3D source files: concept names, element files, is-a tree, mesh loading."""
import collections
import os

import numpy as np
import trimesh

# Version 3.0 "obj_95" meshes (2011) sit at a constant offset from version 4.0 in the arm region.
V3_TO_V4 = np.array([0.7, -3.7, -10.3])  # mm


class BP3D:
    def __init__(self, root):
        self.root = root
        self.names, self.elements, self.owners = {}, {}, collections.defaultdict(list)
        for tree in ("isa", "partof"):
            names, elems = {}, collections.defaultdict(set)
            for line in self._lines(f"{tree}_parts_list_e.txt"):
                concept, _, name = line.split("\t")
                names[concept] = name
            for line in self._lines(f"{tree}_element_parts.txt"):
                concept, _, fid = line.split("\t")
                elems[concept].add(fid)
                self.owners[fid].append(concept)
            self.names.update(names)
            self.elements[tree] = (names, elems)
        self.parents = collections.defaultdict(set)  # is-a only
        self.containers = collections.defaultdict(set)  # is-a and part-of
        for tree in ("isa", "partof"):
            for line in self._lines(f"{tree}_inclusion_relation_list.txt"):
                parent, _, child, _ = line.split("\t")
                self.containers[child].add(parent)
                if tree == "isa":
                    self.parents[child].add(parent)
        self._above = {}
        self.size = collections.Counter(c for cs in self.owners.values() for c in cs)
        self.files = {}
        for tree in ("isa", "partof"):
            d = os.path.join(root, f"{tree}_BP3D_4.0_obj_99")
            for f in sorted(os.listdir(d)):
                if f.endswith(".obj"):
                    self.files.setdefault(f[:-4], os.path.join(d, f))
        self.v3 = os.path.join(root, "BodyParts3D_3.0_obj_95")
        # Version 3.0 concept list (parts_list_e.txt) and its composite concepts (made of other 3.0 concepts).
        self.v3_names, self.v3_composites = {}, set()
        if os.path.exists(os.path.join(root, "parts_list_e.txt")):
            for line in self._lines("parts_list_e.txt"):
                concept, name = line.split("\t")
                self.v3_names[concept] = name
            self.v3_composites = {line.split("\t")[0] for line in self._lines("composite_parts.txt")}

    def _lines(self, name):
        with open(os.path.join(self.root, name), encoding="utf-8") as f:
            return f.read().splitlines()[1:]

    def above(self, concept):
        """All is-a and part-of ancestors of a concept."""
        if concept not in self._above:
            seen, todo = set(), list(self.containers[concept])
            while todo:
                x = todo.pop()
                if x not in seen:
                    seen.add(x)
                    todo += self.containers[x]
            self._above[concept] = seen
        return self._above[concept]

    def most_specific_owner(self, fid):
        """The most specific concept owning this element file.

        Owners that are an is-a or part-of ancestor of another owner are dropped (so 'body of sternum'
        wins over 'body of organ', 'abdominal part of right pectoralis major' over 'right pectoralis
        major'); ties go to the concept with the fewest element files, then to the smallest id."""
        owners = set(self.owners.get(fid, []))
        covered = set().union(*(self.above(c) for c in owners)) if owners else set()
        leaves = sorted(owners - covered) or sorted(owners)
        return min(leaves, key=lambda c: (self.size[c], c), default=None)

    def ancestor_in(self, concept, roots):
        """First is-a ancestor of `concept` (itself included) found in `roots`, or None."""
        seen, todo = set(), [concept]
        while todo:
            x = todo.pop()
            if x in roots:
                return roots[x]
            if x not in seen:
                seen.add(x)
                todo += sorted(self.parents[x])
        return None

    def load_v4(self, fid):
        return trimesh.load(self.files[fid], force="mesh", process=True)

    def load_v3(self, concept, raw=False):
        """Version 3.0 mesh for a concept, or None if 3.0 has none.

        Moved into the 4.0 frame by the constant arm offset, unless `raw` (see v3.py for the whole body)."""
        path = os.path.join(self.v3, concept + ".obj")
        if not os.path.exists(path):
            return None
        m = trimesh.load(path, force="mesh", process=True)
        if not raw:
            m.apply_translation(V3_TO_V4)
        return m
