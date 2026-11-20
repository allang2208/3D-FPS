"""Fit two skinned neck boundaries with matching edge divisions, normals and weights."""
from bisect import bisect_right
from math import atan2, tau

import bmesh
import numpy as np
from mathutils import Vector


# The oblique section passes entirely through skin above the original shirt collar
# and below both the original chin and the low bun. Coordinates are centimetres.
BASE = 145.42
SLOPE = .24
NORMAL_LAYER = "linzhi_source_corner_normal"


def distance(co):
    return co.z - SLOPE * co.y - BASE


def key(co):
    return tuple(round(x, 4) for x in co)


def smooth(u):
    u = min(1., max(0., u))
    return u * u * (3. - 2. * u)


def copy_weights(a, b, f):
    return {k: a.get(k, 0.) * (1. - f) + b.get(k, 0.) * f for k in a.keys() | b.keys()}


def write_weights(vert, layer, mapping):
    vert[layer].clear()
    for k, w in mapping.items():
        if w > 1.e-7:
            vert[layer][k] = w


class Surface:
    def __init__(self, obj, upper):
        self.obj = obj
        geometry = obj.data
        values = np.empty(len(geometry.loops) * 3, dtype=np.float32)
        geometry.corner_normals.foreach_get("vector", values)
        attr = geometry.attributes.new(NORMAL_LAYER, "FLOAT_VECTOR", "CORNER")
        attr.data.foreach_set("vector", values)
        bm = self.bm = bmesh.new()
        bm.from_mesh(geometry)
        self.nl = bm.loops.layers.float_vector[NORMAL_LAYER]
        self.deform = bm.verts.layers.deform.verify()
        self.groups = {g.index: g.name for g in obj.vertex_groups}
        self.groups_by_name = {g.name: g.index for g in obj.vertex_groups}
        # The new bun has three small braid tips just below the original
        # cutting plane. Intersect its neck a few millimetres lower to keep them.
        self.base, self.slope = (145.20, .20) if upper else (BASE, SLOPE)
        section = bmesh.ops.bisect_plane(
            bm, geom=list(bm.verts) + list(bm.edges) + list(bm.faces),
            plane_co=(0., 0., self.base), plane_no=Vector((0., -self.slope, 1.)).normalized(),
            dist=1.e-6, clear_inner=upper, clear_outer=not upper,
        )
        edges = [e for e in section["geom_cut"]
                 if isinstance(e, bmesh.types.BMEdge) and e.is_valid and e.is_boundary]
        self.ring = Ring(self, edges)

    def finish(self):
        bm = self.bm
        # Keep every added ring vertex in the resulting triangles, including
        # collinear divisions required by the other side of the interface.
        polygons = [face for face in bm.faces if len(face.verts) > 3]
        if polygons:
            bmesh.ops.triangulate(bm, faces=polygons, quad_method="BEAUTY", ngon_method="EAR_CLIP")
        bm.to_mesh(self.obj.data)
        bm.free()
        m = self.obj.data
        m.update()
        normal_attr = m.attributes[NORMAL_LAYER]
        values = np.empty(len(m.loops) * 3, dtype=np.float32)
        normal_attr.data.foreach_get("vector", values)
        values = values.reshape(-1, 3)
        values /= np.maximum(np.linalg.norm(values, axis=1, keepdims=True), 1.e-12)
        m.normals_split_custom_set(values.tolist())
        m.attributes.remove(normal_attr)
        m.update()


class Ring:
    def __init__(self, surface, edges):
        self.surface = surface
        neighbors = {}
        self.edge_by_keys = {}
        verts = {}
        for edge in edges:
            a, b = edge.verts
            ka, kb = key(a.co), key(b.co)
            if ka == kb:
                raise ValueError("Neck edge shorter than the joining tolerance")
            neighbors.setdefault(ka, set()).add(kb)
            neighbors.setdefault(kb, set()).add(ka)
            verts.setdefault(ka, set()).add(a)
            verts.setdefault(kb, set()).add(b)
            self.edge_by_keys.setdefault(frozenset((ka, kb)), []).append(edge)
        if not neighbors or any(len(row) != 2 for row in neighbors.values()):
            raise ValueError(f"The section on {surface.obj.name} must form a closed ring "
                             f"({len(edges)} edges, degrees {sorted(set(map(len, neighbors.values())))})")
        start = min(neighbors)
        path = [start]
        prev, current = start, min(neighbors[start])
        while current != start:
            path.append(current)
            prev, current = current, next(p for p in neighbors[current] if p != prev)
        if len(path) != len(neighbors):
            raise ValueError(f"Section on {surface.obj.name} crosses an extra island. "
                             f"The neck occupies {len(path)} of {len(neighbors)} cut positions.")
        area = sum(p[0] * q[1] - p[1] * q[0] for p, q in zip(path, path[1:] + path[:1]))
        if area < 0.:
            path.reverse()
        self.keys = path
        self.boundary_verts = {v for group in verts.values() for v in group}
        self.coords = [next(iter(verts[k])).co.copy() for k in path]
        self.center = (np.max(self.coords, axis=0) + np.min(self.coords, axis=0)) * .5
        self.normals, self.weights = [], []
        for k in path:
            loops = [loop for v in verts[k] for loop in v.link_loops]
            self.normals.append(sum((v[surface.nl] for v in loops), Vector()).normalized())
            self.weights.append({surface.groups[i]: w for i, w in
                                 next(iter(verts[k]))[surface.deform].items()})
        n = len(path)
        lengths = np.array([(self.coords[(i + 1) % n] - p).length for i, p in enumerate(self.coords)])
        self.s = np.concatenate(([0.], np.cumsum(lengths) / np.sum(lengths)))
        # Register the two sections at the same lateral ray. This avoids
        # different tessellation densities rotating the front of the neck.
        cy = self.center[1]
        for i, a in enumerate(self.coords):
            b = self.coords[(i + 1) % n]
            if a.y <= cy < b.y and min(a.x, b.x) > self.center[0]:
                f = (cy - a.y) / (b.y - a.y)
                self.origin = self.s[i] + f * (self.s[i+1] - self.s[i])
                break
        else:
            raise ValueError("No lateral crossing on neck perimeter")
        self.params = [(s - self.origin) % 1. for s in self.s[:-1]]

    def sample(self, param):
        s = (param + self.origin) % 1.
        i = min(len(self.coords) - 1, bisect_right(self.s, s) - 1)
        j = (i + 1) % len(self.coords)
        f = float((s - self.s[i]) / (self.s[i+1] - self.s[i]))
        return (self.coords[i].lerp(self.coords[j], f), self.normals[i].lerp(self.normals[j], f).normalized(),
                copy_weights(self.weights[i], self.weights[j], f))

    def by_direction(self, co):
        # Use angle only off the seam. The joined loops themselves use true arc length.
        angle = atan2(co.y - self.center[1], co.x - self.center[0]) % tau
        if not hasattr(self, "direction_samples"):
            xy = np.asarray(self.coords)[:, :2] - self.center[:2]
            angles = np.arctan2(xy[:, 1], xy[:, 0]) % tau
            order = np.argsort(angles)
            aa = angles[order]
            pp = np.unwrap(np.asarray(self.params)[order] * tau) / tau
            self.direction_samples = (np.r_[aa[-1]-tau, aa, aa[0]+tau], np.r_[pp[-1]-1., pp, pp[0]+1.])
        return float(np.interp(angle, *self.direction_samples)) % 1.

    def subdivide(self, new_params):
        insertions = [[] for _ in self.keys]
        n = len(self.keys)
        for t in new_params:
            s = (t + self.origin) % 1.
            i = min(n - 1, bisect_right(self.s, s) - 1)
            f = (s - self.s[i]) / (self.s[i+1] - self.s[i])
            if 1.e-6 < f < 1. - 1.e-6:
                insertions[i].append((f, t))
        mapping = {}
        for i, ka in enumerate(self.keys):
            kb = self.keys[(i + 1) % n]
            for edge in self.edge_by_keys[frozenset((ka, kb))]:
                a, b = edge.verts
                if key(a.co) != ka:
                    a, b = b, a
                mapping[a] = self.params[i]
                mapping[b] = self.params[(i + 1) % n]
                previous = 0.
                for fraction, t in sorted(insertions[i]):
                    face, = edge.link_faces
                    endpoints = {l.vert: l for l in face.loops}
                    uv_data = {name: (endpoints[a][layer].uv.copy(), endpoints[b][layer].uv.copy())
                               for name, layer in self.surface.bm.loops.layers.uv.items()}
                    local_fraction = float((fraction - previous) / (1. - previous))
                    _, mid = bmesh.utils.edge_split(edge, a, local_fraction)
                    loop = next(l for l in face.loops if l.vert == mid)
                    for name, (ua, ub) in uv_data.items():
                        loop[self.surface.bm.loops.layers.uv[name]].uv = ua.lerp(ub, local_fraction)
                    mapping[mid] = t
                    previous, a = fraction, mid
                    edge = self.surface.bm.edges.get((a, b))
        return mapping


def fit(body, head):
    source, target = head.ring, body.ring
    body_verts = target.subdivide(source.params)
    head_verts = source.subdivide(target.params)
    hd = head.groups_by_name["head"]
    for vert in head.bm.verts:
        if vert in head_verts:
            continue
        d = vert.co.z - head.slope * vert.co.y - head.base
        if d > 4.0:
            write_weights(vert, head.deform, {hd: 1.})
            continue
        t = source.by_direction(vert.co)
        original, _, _ = source.sample(t)
        pos, _, weight = target.sample(t)
        radial = (vert.co.xy - Vector(source.center[:2])).length
        neck_radius = (original.xy - Vector(source.center[:2])).length
        # Outside of the neck column the bun and the chin keep their source silhouette.
        local = 1. - smooth((radial - neck_radius - .25) / 1.65)
        blend = local * (1. - smooth(d / 3.2))
        vert.co += (pos - original) * blend
        weight = copy_weights({"head": 1.}, weight, local * (1. - smooth(d / 3.9)))
        write_weights(vert, head.deform, {head.groups_by_name[k]: v for k, v in weight.items()})
    for surface, mapping in ((body, body_verts), (head, head_verts)):
        for v, t in mapping.items():
            p, normal, weights = target.sample(t)
            v.co = p
            write_weights(v, surface.deform, {surface.groups_by_name[k]: w for k, w in weights.items()})
            for loop in v.link_loops:
                loop[surface.nl] = normal
    head.bm.normal_update()
    for v in head.bm.verts:
        d = distance(v.co)
        if v in head_verts or d > 2.7:
            continue
        t = source.by_direction(v.co)
        original, _, _ = source.sample(t)
        radial = (v.co.xy - Vector(source.center[:2])).length
        radius = (original.xy - Vector(source.center[:2])).length
        local = (1. - smooth((radial - radius - .25) / 1.65)) * (1. - smooth(d / 2.7))
        _, seam_normal, _ = target.sample(t)
        normal = v.normal.lerp(seam_normal, 1. - smooth(d / 1.0)).normalized()
        for loop in v.link_loops:
            loop[head.nl] = loop[head.nl].lerp(normal, local).normalized()
    return {"body_ring_source": len(target.keys), "head_ring_source": len(source.keys),
            "matched_ring_positions": len({key(v.co) for v in body_verts}),
            "cut_z_at_y_zero_cm": BASE, "cut_rise_per_cm_y": SLOPE}
