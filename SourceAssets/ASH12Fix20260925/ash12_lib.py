"""Shared skinning helpers for the ASH-12 arm probes (topology-independent).

Blender's evaluated mesh can reorder vertices, so stretch is measured with a linear
blend skinning evaluation built from the mesh's own vertex groups and rest matrices:
that is also exactly what the engine evaluates.
"""
import bpy
import numpy as np
from collections import defaultdict


class SkinSurface:
    def __init__(self, rig, mesh, side=None):
        self.rig = rig
        self.mesh = mesh
        groups = {g.index: g.name for g in mesh.vertex_groups}
        rows, groups_of, per_bone = [], [], {}
        for v in mesh.data.vertices:
            pairs = [(groups[g.group], g.weight) for g in v.groups
                     if g.group in groups and g.weight > 1e-6]
            if side:
                pairs = [(n, w) for n, w in pairs if n.endswith('_' + side)]
            if not pairs:
                continue
            total = sum(w for _, w in pairs)
            best = max(pairs, key=lambda p: p[1])[0]
            stem = best.split('_')[0]
            group = 'fingers' if stem in ('thumb', 'index', 'middle', 'ring', 'pinky') else stem
            row = len(rows)
            rows.append(v.index)
            groups_of.append((best[-1], group))
            for name, weight in pairs:
                local = rig.data.bones[name].matrix_local.inverted() @ v.co
                per_bone.setdefault(name, []).append(
                    (row, [local.x, local.y, local.z, 1.0], weight / total))
        self.ids = rows
        self.groups = np.array([g[1] for g in groups_of])
        self.sides = np.array([g[0] for g in groups_of])
        self.by_bone = {name: (np.array([e[0] for e in entries], dtype=np.int64),
                               np.array([e[1] for e in entries], dtype=float),
                               np.array([e[2] for e in entries], dtype=float))
                        for name, entries in per_bone.items()}
        self.rest = self.positions({n: m.matrix_local.copy() for n, m in rig.data.bones.items()})
        # bind self-check: a consistent bind reproduces the mesh's own rest positions
        local = np.array([[v.co.x, v.co.y, v.co.z] for v in mesh.data.vertices])
        rest_ids = np.array(self.ids)
        print('BIND_CHECK max_mm', round(float(np.abs(self.rest - local[rest_ids]).max()) * 1000, 3),
              'vertices', len(self.ids), flush=True)
        # unique edges inside the same side (fingers/arm only, so a seam cannot fake stretch)
        index = {vid: i for i, vid in enumerate(self.ids)}
        edges = set()
        for poly in mesh.data.polygons:
            vs = [index[v] for v in poly.vertices if v in index]
            for i in range(len(vs)):
                a, b = vs[i], vs[(i + 1) % len(vs)]
                if self.sides[a] == self.sides[b]:
                    edges.add((a, b) if a < b else (b, a))
        self.edges = np.array(sorted(edges), dtype=np.int64)
        self.rest_len = np.linalg.norm(self.rest[self.edges[:, 0]] - self.rest[self.edges[:, 1]], axis=1)
        # Drop degenerate edges: a 0.6 mm rest edge turns any pose into a fake 4x ratio.
        keep = self.rest_len > 0.0015
        self.edges = self.edges[keep]
        self.rest_len = self.rest_len[keep]

    def positions(self, pose):
        out = np.zeros((len(self.ids), 4))
        for name, (ids, coords, weights) in self.by_bone.items():
            matrix = np.array(pose[name], dtype=float)
            out[ids] += (coords @ matrix.T) * weights[:, None]
        return out[:, :3]

    def stretch(self, pose):
        p = self.positions(pose)
        posed = np.linalg.norm(p[self.edges[:, 0]] - p[self.edges[:, 1]], axis=1)
        return posed / np.maximum(self.rest_len, 1e-9), posed - self.rest_len

    def group_of(self, row):
        return self.groups[row], self.sides[row]
