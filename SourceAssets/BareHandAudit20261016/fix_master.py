"""Candidate V8 surface topology for the shared bare-arm master (writes a candidate only).

1. The four 09-25 fan patches (palm and thumb root, both hands) fold over their
   own concave perimeter. Each fan, plus any adjacent face whose winding disagrees
   with the fan, is replaced by a fold-free ear-clipped triangulation of the
   perimeter (the 10-14 derived-mesh method), using the perimeter's own corners.
2. Two micro-edge clusters per palm (edges < 0.03 mm) carry zero-area faces; the
   shorter edge is collapsed onto its partner by re-pointing faces.
Vertex positions, weights and per-corner UV / normals are kept; no vertex is
moved or deleted (orphans stay so every Authored profile keeps index parity).
"""
import json, sys
from collections import defaultdict
from pathlib import Path
import numpy as np

O = Path(__file__).parent
sys.path.insert(0, str(O.parent / 'BarePalmHoleRepair20261014'))
from triangulate_patch import triangulate

B = O.parent / 'ModularOutfit20260925/BarePalmV7'


def edge_map(tris):
    e = defaultdict(list)
    for ti, f in enumerate(tris):
        if f is None:
            continue
        for a, b in zip(f, f[1:] + f[:1]):
            e[(min(a, b), max(a, b))].append((ti, a, b))
    return e


def plan(d, centers):
    """Face operations computed on one dataset; replayable by index on index-parity profiles."""
    v = np.asarray(d['positions'], float)
    tris = [list(f) for f in d['triangles']]
    ops = dict(remove=[], add=[], repoint={})
    # 2. Micro-edge collapse (zero-area faces).
    cross = np.cross(v[[f[1] for f in tris]] - v[[f[0] for f in tris]], v[[f[2] for f in tris]] - v[[f[0] for f in tris]])
    area = .5 * np.linalg.norm(cross, axis=1)
    for ti in np.where(area < 1e-6)[0]:
        f = tris[ti]
        lens = [(np.linalg.norm(v[f[i]] - v[f[(i + 1) % 3]]), f[i], f[(i + 1) % 3]) for i in range(3)]
        length, a, b = min(lens)
        if length < .003 and b not in ops['repoint'] and a not in ops['repoint'].values():
            keep, drop = (a, b) if a < b else (b, a)
            ops['repoint'][drop] = keep
    def resolve(x):
        while x in ops['repoint']:
            x = ops['repoint'][x]
        return x
    for ti, f in enumerate(tris):
        g = [resolve(x) for x in f]
        if len(set(g)) < 3:
            ops['remove'].append(ti)
            tris[ti] = None
        elif g != f:
            tris[ti] = g
    # 1. Fan patches.
    edges = edge_map(tris)
    for c in centers:
        region = {ti for ti, f in enumerate(tris) if f is not None and c in f}
        for _ in range(3):
            grow = set()
            for ti in region:
                f = tris[ti]
                for a, b in zip(f, f[1:] + f[:1]):
                    for tj, x, y in edges[(min(a, b), max(a, b))]:
                        if tj not in region and (x, y) == (a, b):
                            grow.add(tj)           # neighbour runs the edge the same way: folded
            if not grow:
                break
            region |= grow
        local = defaultdict(list)
        for ti in region:
            f = tris[ti]
            for a, b in zip(f, f[1:] + f[:1]):
                local[(min(a, b), max(a, b))].append((ti, a, b))
        boundary = [r[0] for r in local.values() if len(r) == 1]
        nxt = {}
        for ti, a, b in boundary:
            if a in nxt:
                raise RuntimeError('Branched patch boundary near vertex %d' % c)
            nxt[a] = (b, ti)
        loop, cur = [], boundary[0][1]
        while cur not in loop:
            loop.append(cur)
            cur = nxt[cur][0]
        if len(loop) != len(boundary):
            raise RuntimeError('Patch boundary is not one loop near vertex %d' % c)
        # Corner attributes from the faces that are removed (same as the 10-14 install).
        corner = {}
        for vi in loop:
            ti = nxt[vi][1]
            k = tris[ti].index(vi)
            corner[vi] = (ti, k)
        normals = [np.asarray(d['normals'][corner[vi][0]][corner[vi][1]]) for vi in loop]
        # The surface convention of this mesh is opposite to the right-hand rule (UE native).
        fill = triangulate([v[vi].tolist() for vi in loop], [(-n).tolist() for n in normals])
        new = []
        for a, b, cc in fill:
            face = [loop[a], loop[b], loop[cc]]
            new.append(face)
        # Keep the region's exterior traversal: boundary edges must run as they did in the removed faces.
        wanted = {(a, b) for _, a, b in boundary}
        produced = {(f[i], f[(i + 1) % 3]) for f in new for i in range(3)}
        if not wanted <= produced:
            new = [f[::-1] for f in new]
            produced = {(f[i], f[(i + 1) % 3]) for f in new for i in range(3)}
            if not wanted <= produced:
                raise RuntimeError('Re-triangulation does not keep the perimeter orientation near vertex %d' % c)
        for ti in region:
            ops['remove'].append(ti)
            tris[ti] = None
        for f in new:
            ops['add'].append(dict(face=f, corners=[corner[x] for x in f], material=int(d['triangle_materials'][corner[f[0]][0]])))
        edges = edge_map(tris + [a['face'] for a in ops['add']])
    return ops


def apply(d, ops):
    out = dict(d)
    tris = [list(f) for f in d['triangles']]
    def resolve(x):
        while x in ops['repoint']:
            x = ops['repoint'][x]
        return x
    # Corner attributes are read from the original faces before removal.
    added = []
    for a in ops['add']:
        added.append(dict(triangles=a['face'],
                          uv=[d['uv'][ti][k] for ti, k in a['corners']],
                          normals=[d['normals'][ti][k] for ti, k in a['corners']],
                          triangle_materials=a['material'],
                          **({'canonical_normals': [d['canonical_normals'][ti][k] for ti, k in a['corners']]} if 'canonical_normals' in d else {})))
    remove = set(ops['remove'])
    keep = [i for i in range(len(tris)) if i not in remove]
    for key in ('triangles', 'triangle_materials', 'uv', 'normals', 'canonical_normals'):
        if key not in d:
            continue
        rows = [d[key][i] for i in keep]
        if key == 'triangles':
            rows = [[resolve(x) for x in f] for f in rows]
        out[key] = rows + [r[key] for r in added]
    return out


if __name__ == '__main__':
    from audit_mesh import audit
    master = json.loads((B / 'M4_original.json').read_text())
    centers = [p['center_vertex'] for p in json.loads((B / 'surface_repair.json').read_text())['patches']]
    ops = plan(master, centers)
    fixed = apply(master, ops)
    fixed['contract'] = 'V8 candidate: fold-free palm/thumb patches, micro-edge collapse; positions/weights/corner data retained'
    (O / 'M4_v8_candidate.json').write_text(json.dumps(fixed, separators=(',', ':')))
    (O / 'master_ops.json').write_text(json.dumps(ops, indent=1))
    r = audit(fixed)
    print('ops: removed %d, added %d, repointed %d' % (len(ops['remove']), len(ops['add']), len(ops['repoint'])))
    print(json.dumps({k: r[k] for k in ('triangles', 'degenerate_faces', 'boundary_edges', 'nonmanifold_edges',
                                         'inconsistent_winding_edges', 'faces_normal_against_winding')}))
    print('loops', [(l['side'], l['region'], l['perimeter_cm']) for l in r['boundary_loops']])
