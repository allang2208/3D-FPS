"""Correspondence-free surface repair plan for any bare-skin mesh snapshot.

Works on the V7 JSON layout (master / Authored) and on UE snapshots (split
vertices). Three local operations, all on the mesh's own rest geometry:

1. micro-edge collapse: zero-area faces whose shortest edge is < 0.03 mm;
   faces using the dropped vertex are rewritten onto its partner.
2. fold repair: faces on edges traversed the same way by both neighbours, plus
   the 1-ring around them, are replaced by a fold-free ear-clipped
   triangulation of the region perimeter (oriented against the outside faces).
3. normal repair: corner normals that deviate > NORMAL_LIMIT from the mesh's
   own angle-weighted smooth normal are replaced by it (pre-deformed native
   reference poses carried canonical normals).

New faces copy every corner attribute from an existing corner of the same
vertex in a removed face. No vertex moves; weights are untouched.
"""
import json, sys
from collections import defaultdict, Counter
from pathlib import Path
import numpy as np

O = Path(__file__).parent
sys.path.insert(0, str(O.parent / 'BarePalmHoleRepair20261014'))
from triangulate_patch import triangulate

NORMAL_LIMIT = 35.0


def welded(d):
    v = np.asarray(d['positions'], float)
    key = np.round(v / 1e-4).astype(np.int64)
    _, wid = np.unique(key, axis=0, return_inverse=True)
    return v, wid.ravel()


def convention(v, t, n):
    cr = np.cross(v[t[:, 1]] - v[t[:, 0]], v[t[:, 2]] - v[t[:, 0]])
    sn = n.mean(1)
    return float(np.sign(np.median(np.einsum('ij,ij->i', cr, sn)))) or 1.0


def face_normals(v, faces):
    f = np.asarray(faces)
    cr = np.cross(v[f[:, 1]] - v[f[:, 0]], v[f[:, 2]] - v[f[:, 0]])
    return cr, .5 * np.linalg.norm(cr, axis=1)


def plan_mesh(d, max_region=80):
    v, wid = welded(d)
    t = np.asarray(d['triangles'], int)
    n = np.asarray(d['normals'], float)
    mats = list(d['triangle_materials'])
    conv = convention(v, t, n)
    rep = {}
    for vi, w in enumerate(wid):
        rep.setdefault(int(w), vi)
    faces = [[int(wid[x]) for x in f] for f in t.tolist()]        # welded ids
    alive = [True] * len(faces)
    corner_of = {}                                                # welded vertex -> (face, k) attribute source
    for ti, f in enumerate(faces):
        for k, x in enumerate(f):
            corner_of.setdefault(x, (ti, k))
    ops = dict(remove=set(), add=[], normals={}, notes=Counter())
    # 1. micro-edge collapse
    cr, area = face_normals(v, t)
    repoint = {}
    for ti in np.where(area < 1e-6)[0]:
        f = faces[ti]
        if len(set(f)) < 3:
            ops['remove'].add(int(ti)); alive[ti] = False; ops['notes']['collapsed_input_face'] += 1; continue
        cand = sorted((np.linalg.norm(v[rep[f[i]]] - v[rep[f[(i + 1) % 3]]]), f[i], f[(i + 1) % 3]) for i in range(3))
        length, a, b = cand[0]
        if length >= .003:
            ops['notes']['needle_face_skipped'] += 1; continue
        keep, drop = min(a, b), max(a, b)
        while keep in repoint: keep = repoint[keep]
        if drop != keep and drop not in repoint: repoint[drop] = keep
    def res(x):
        while x in repoint: x = repoint[x]
        return x
    if repoint:
        for ti, f in enumerate(faces):
            if not alive[ti] or not any(x in repoint for x in f): continue
            g = [res(x) for x in f]
            ops['remove'].add(ti); alive[ti] = False
            if len(set(g)) < 3:
                ops['notes']['micro_face_removed'] += 1; continue
            # Same corner attributes; the dropped vertex takes its partner's position/weights.
            ops['add'].append(dict(face=g, corners=[(ti, k, res(x) if x in repoint else None) for k, x in enumerate(f)], material=mats[ti]))
            ops['notes']['micro_face_rewritten'] += 1
    # Current face set (welded), including rewritten faces.
    cur = {ti: faces[ti] for ti in range(len(faces)) if alive[ti]}
    added_key = {}
    for i, a in enumerate(ops['add']):
        key = ('a', i); cur[key] = a['face']; added_key[key] = a
    def edge_index(fs):
        e = defaultdict(list)
        for key, f in fs.items():
            for a, b in zip(f, f[1:] + f[:1]):
                e[(min(a, b), max(a, b))].append((key, a, b))
        return e
    # 1b. small openings (perimeter < 1 cm; designed openings are >= 9 cm):
    # ear-clip the loop, running each edge against the face that borders it.
    def src_of(key, x):
        f = cur[key]
        if isinstance(key, tuple):
            ti, k, ov = added_key[key]['corners'][f.index(x)]; return ti, k, ov
        return key, f.index(x), None
    e = edge_index(cur)
    bnd = {}
    for ek, rows in e.items():
        if len(rows) == 1:
            key, a, b = rows[0]; bnd[b] = (a, key)                   # fill runs b -> a
    seen = set()
    for start in list(bnd):
        if start in seen: continue
        loop, c = [], start
        while c in bnd and c not in loop:
            loop.append(c); c = bnd[c][0]
        seen.update(loop)
        if c != start or len(loop) < 3: continue
        perim = sum(np.linalg.norm(v[rep[loop[i]]] - v[rep[loop[(i + 1) % len(loop)]]]) for i in range(len(loop)))
        if perim >= 1.0: continue
        corners = {x: src_of(bnd[x][1], x) for x in loop}
        corners.update({bnd[x][0]: src_of(bnd[x][1], bnd[x][0]) for x in loop if bnd[x][0] not in corners})
        try:
            tri = triangulate([v[rep[x]].tolist() for x in loop], [(conv * n[corners[x][0]][corners[x][1]]).tolist() for x in loop])
        except RuntimeError:
            ops['notes']['opening_triangulation_failed'] += 1; continue
        new = [[loop[a], loop[b], loop[c2]] for a, b, c2 in tri]
        produced = {(f[i], f[(i + 1) % 3]) for f in new for i in range(3)}
        if not all((x, bnd[x][0]) in produced for x in loop):
            new = [f[::-1] for f in new]
        for f in new:
            i = len(ops['add'])
            ops['add'].append(dict(face=f, corners=[corners[x] for x in f], material=mats[corners[f[0]][0]]))
            cur[('a', i)] = f; added_key[('a', i)] = ops['add'][-1]
        ops['notes']['small_openings_filled'] += 1
    # 2. folds (and small openings whose two sides disagree in orientation)
    def small_open_edges(e):
        """Open edges belonging to undirected boundary components with perimeter < 1 cm."""
        adj = defaultdict(set); open_e = [ek for ek, rows in e.items() if len(rows) == 1]
        for a, b in open_e: adj[a].add(b); adj[b].add(a)
        small, seen_v = set(), set()
        for s in list(adj):
            if s in seen_v: continue
            comp, todo = {s}, [s]; seen_v.add(s)
            while todo:
                a = todo.pop()
                for b in adj[a] - seen_v: seen_v.add(b); comp.add(b); todo.append(b)
            edges = [ek for ek in open_e if ek[0] in comp]
            if sum(np.linalg.norm(v[rep[a]] - v[rep[b]]) for a, b in edges) < 1.0: small.update(edges)
        return small
    for attempt in range(4):
        e = edge_index(cur)
        holes = small_open_edges(e)
        seeds = {k for rows in e.values() if len(rows) == 2 and rows[0][1] == rows[1][1] for k, _, _ in rows}
        seeds |= {e[ek][0][0] for ek in holes}
        if not seeds: break
        vfaces = defaultdict(set)
        for key, f in cur.items():
            for x in f: vfaces[x].add(key)
        # Smallest region first: the seed faces plus the whole fan of any vertex
        # shared by three or more seeds (the old patch centre), and the 1-ring of
        # every small-opening vertex. Grow only on retry.
        region = set(seeds)
        shared = Counter(x for s in seeds for x in cur[s])
        for x, c in shared.items():
            if c >= 3: region |= vfaces[x]
        for ek in holes:
            for x in ek: region |= vfaces[x]
        for _ in range(attempt):
            region |= {k for r in list(region) for x in cur[r] for k in vfaces[x]}
        # Components of the region
        comps, left = [], set(region)
        while left:
            s = left.pop(); g = {s}; todo = [s]
            while todo:
                a = todo.pop()
                for x in cur[a]:
                    for b in vfaces[x] & left:
                        left.remove(b); g.add(b); todo.append(b)
            comps.append(g)
        progress = False
        for g in comps:
            if len(g) > max_region:
                ops['notes']['fold_region_too_large'] += 1; continue
            local = defaultdict(list)
            for key in g:
                f = cur[key]
                for a, b in zip(f, f[1:] + f[:1]): local[(min(a, b), max(a, b))].append((key, a, b))
            # Small-opening edges inside the region are filled, not kept as boundary.
            bnd = [(ek, rows[0]) for ek, rows in local.items() if len(rows) == 1 and ek not in holes]
            wanted = {}
            ok = True
            for ek, (key, a, b) in bnd:
                outside = [r for r in e[ek] if r[0] not in g]
                if len(outside) != 1: ok = False; break
                _, x, y = outside[0]; wanted[y] = x                    # new face must run y -> x
            if not ok or len(wanted) != len(bnd):
                ops['notes']['fold_boundary_not_simple'] += 1; continue
            loop, c0 = [], next(iter(wanted))
            c = c0
            while True:
                loop.append(c); c = wanted[c]
                if c == c0 or len(loop) > len(wanted): break
            if len(loop) != len(wanted):
                ops['notes']['fold_boundary_multi_loop'] += 1; continue
            def src_corner(x):
                for key in g:
                    f = cur[key]
                    if x in f:
                        if isinstance(key, tuple):
                            a = added_key[key]; ti, k, ov = a['corners'][f.index(x)]; return ti, k, ov
                        return key, f.index(x), None
                return corner_of[x] + (None,)
            corners = {x: src_corner(x) for x in loop}
            pts = [v[rep[x]].tolist() for x in loop]
            nrm = [(conv * n[corners[x][0]][corners[x][1]]).tolist() for x in loop]
            try:
                tri = triangulate(pts, nrm)
            except RuntimeError:
                ops['notes']['fold_triangulation_failed'] += 1; continue
            new = [[loop[a], loop[b], loop[c]] for a, b, c in tri]
            produced = {(f[i], f[(i + 1) % 3]) for f in new for i in range(3)}
            if not all((y, x) in produced for y, x in wanted.items()):
                new = [f[::-1] for f in new]
                produced = {(f[i], f[(i + 1) % 3]) for f in new for i in range(3)}
                if not all((y, x) in produced for y, x in wanted.items()):
                    ops['notes']['fold_orientation_failed'] += 1; continue
            for key in g:
                del cur[key]
                if isinstance(key, tuple): added_key[key]['dead'] = True
                else: ops['remove'].add(key)
            for f in new:
                i = len(ops['add'])
                ops['add'].append(dict(face=f, corners=[corners[x] for x in f], material=mats[corners[f[0]][0]]))
                cur[('a', i)] = f; added_key[('a', i)] = ops['add'][-1]
            ops['notes']['fold_regions_fixed'] += 1; progress = True
        if not progress: break
    ops['add'] = [a for a in ops['add'] if not a.get('dead')]
    # 3. normals: smooth angle-weighted normal per welded vertex over the final faces.
    final = [(key, f) for key, f in cur.items()]
    acc = np.zeros((len(rep), 3)) if False else defaultdict(lambda: np.zeros(3))
    for key, f in final:
        p = v[[rep[x] for x in f]]
        fn = conv * np.cross(p[1] - p[0], p[2] - p[0]); ln = np.linalg.norm(fn)
        if ln < 1e-12: continue
        fn /= ln
        for i, x in enumerate(f):
            e1, e2 = p[(i + 1) % 3] - p[i], p[(i + 2) % 3] - p[i]
            ang = np.arccos(np.clip(e1 @ e2 / max(np.linalg.norm(e1) * np.linalg.norm(e2), 1e-12), -1, 1))
            acc[x] += fn * ang
    smooth = {x: a / max(np.linalg.norm(a), 1e-12) for x, a in acc.items()}
    limit = np.cos(np.radians(NORMAL_LIMIT))
    for key, f in final:
        if isinstance(key, tuple):
            a = added_key[key]
            for k, x in enumerate(f):
                ti, kk, _ = a['corners'][k]; s = np.asarray(n[ti][kk]); s = s / max(np.linalg.norm(s), 1e-12)
                if s @ smooth[x] < limit: a.setdefault('normals', {})[k] = smooth[x].tolist()
            continue
        for k, x in enumerate(f):
            s = n[key][k]; s = s / max(np.linalg.norm(s), 1e-12)
            if s @ smooth[x] < limit:
                ops['normals'][(key, k)] = smooth[x].tolist()
    ops['notes']['normal_corners_replaced'] = len(ops['normals']) + sum(len(a.get('normals', {})) for a in ops['add'])
    ops['remove'] = sorted(ops['remove'])
    ops['rep'] = rep
    return ops


def apply_json(d, ops):
    """Apply a plan to a V7-layout JSON dict (used for master / Authored and for checking)."""
    v, wid = welded(d)
    rep = {}
    for vi, w in enumerate(wid): rep.setdefault(int(w), vi)
    out = dict(d)
    keep = [i for i in range(len(d['triangles'])) if i not in set(ops['remove'])]
    keys = [k for k in ('triangles', 'triangle_materials', 'uv', 'normals', 'canonical_normals') if k in d]
    rows = {k: [d[k][i] for i in keep] for k in keys}
    if 'normals' in rows:
        idx = {old: new for new, old in enumerate(keep)}
        for (ti, k), nn in ops['normals'].items():
            if ti in idx:
                r = [list(c) for c in rows['normals'][idx[ti]]]; r[k] = nn; rows['normals'][idx[ti]] = r
    for a in ops['add']:
        tri = []
        for k, (ti, kk, ov) in enumerate(a['corners']):
            vi = d['triangles'][ti][kk]
            tri.append(rep[ov] if ov is not None else vi)
        rows['triangles'].append(tri)
        rows['triangle_materials'].append(a['material'])
        for k2 in ('uv', 'normals', 'canonical_normals'):
            if k2 in rows:
                rows[k2].append([d[k2][ti][kk] for ti, kk, _ in a['corners']])
        if a.get('normals'):
            r = [list(c) for c in rows['normals'][-1]]
            for k, nn in a['normals'].items(): r[int(k)] = nn
            rows['normals'][-1] = r
    out.update(rows)
    return out


def surface_change_mm(d, fixed):
    """Distance from every welded vertex that left the surface to the new faces (mm)."""
    v, wid = welded(d)
    used_before = {int(wid[x]) for f in d['triangles'] for x in f}
    v2, wid2 = welded(fixed)
    used_after = {int(wid2[x]) for f in fixed['triangles'] for x in f}
    pos = {}
    for vi, w in enumerate(wid): pos.setdefault(int(w), v[vi])
    key2 = {tuple(np.round(v2[vi] / 1e-4).astype(np.int64)): int(wid2[vi]) for vi in range(len(v2))}
    dropped = [w for w in used_before if key2.get(tuple(np.round(pos[w] / 1e-4).astype(np.int64))) not in used_after]
    if not dropped: return 0.0, 0
    tris = np.asarray(fixed['triangles'])
    new = tris[len(tris) - 200:] if len(tris) > 200 else tris
    best = 0.0
    for w in dropped:
        p = pos[w]; dmin = 1e9
        for f in tris[np.linalg.norm(v2[tris[:, 0]] - p, axis=1) < 3]:
            a, b, c = v2[f]
            # point-triangle distance (closest point on triangle)
            ab, ac, ap = b - a, c - a, p - a
            nrm = np.cross(ab, ac); ln = np.linalg.norm(nrm)
            if ln < 1e-12: continue
            nrm /= ln; q = p - nrm * (ap @ nrm)
            m = np.array([ab, ac]).T; uvw = np.linalg.lstsq(m, q - a, rcond=None)[0]
            if uvw.min() >= 0 and uvw.sum() <= 1: dist = abs(ap @ nrm)
            else: dist = min(np.linalg.norm(p - x) for x in (a, b, c))
            dmin = min(dmin, dist)
        best = max(best, dmin)
    return round(float(best) * 10, 3), len(dropped)


def jsonable(ops):
    """Plan in snapshot-local indices: corner = [source face, corner, override local vertex or None]."""
    rep = ops['rep']
    def corner(c):
        ti, k, ov = c
        return [int(ti), int(k), None if ov is None else int(rep[ov])]
    return dict(remove=[int(x) for x in ops['remove']],
                add=[dict(corners=[corner(c) for c in a['corners']], material=int(a['material']),
                          normals={str(k): v for k, v in a.get('normals', {}).items()}) for a in ops['add']],
                normals=[[int(ti), int(k), nn] for (ti, k), nn in ops['normals'].items()], notes=dict(ops['notes']))


if __name__ == '__main__':
    from audit_mesh import audit
    d = json.loads(Path(sys.argv[1]).read_text())
    ops = plan_mesh(d)
    fixed = apply_json(d, ops)
    before, after = audit(d), audit(fixed)
    pick = ('triangles', 'degenerate_faces', 'boundary_edges', 'nonmanifold_edges', 'inconsistent_winding_edges')
    print('notes', dict(ops['notes']), 'removed', len(ops['remove']), 'added', len(ops['add']))
    print('before', {k: before[k] for k in pick}, 'openings', len(before['boundary_loops']))
    print('after ', {k: after[k] for k in pick}, 'openings', len(after['boundary_loops']))
    print('vertices leaving the surface: %d, max distance to new surface %.3f mm' % surface_change_mm(d, fixed)[::-1])
