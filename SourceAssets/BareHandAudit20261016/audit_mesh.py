"""Read-only topology / surface audit of a bare-arm mesh snapshot (V7 JSON layout).

Input layout (M4_original.json, Authored/<Profile>.json, BarePalmHoleRepair snapshots):
positions[V], triangles[T][3], normals[T][3][3], uv[T][3][2], triangle_materials[T], weights[V].
Units are UE centimetres. Nothing is written except the report.
"""
import json, sys
from collections import defaultdict, Counter
from pathlib import Path
import numpy as np

O = Path(__file__).parent


def side_and_region(ws):
    if not ws:
        return '?', '?'
    side = 'l' if sum(w for n, w in ws.items() if n.endswith('_l')) >= sum(w for n, w in ws.items() if n.endswith('_r')) else 'r'
    top = max(ws.items(), key=lambda kv: kv[1])[0]
    for key, name in (('thumb', 'thumb'), ('index', 'index'), ('middle', 'middle'), ('ring', 'ring'), ('pinky', 'pinky'),
                      ('hand', 'palm'), ('lowerarm', 'forearm'), ('upperarm', 'upperarm'), ('clavicle', 'shoulder')):
        if key in top:
            return side, name
    return side, top


def audit(d, skin=None, weld=1e-4, crack=0.05):
    v = np.asarray(d['positions'], float)
    t = np.asarray(d['triangles'], int)
    mats = np.asarray(d['triangle_materials'], int)
    nrm = np.asarray(d['normals'], float)
    uv = np.asarray(d['uv'], float)
    if skin is not None:
        keep = np.isin(mats, list(skin))
        t, mats, nrm, uv = t[keep], mats[keep], nrm[keep], uv[keep]
    W = d['weights']
    # Weld coincident positions (split UV / normal vertices) to study the surface itself.
    key = np.round(v / weld).astype(np.int64)
    _, weld_id, counts = np.unique(key, axis=0, return_inverse=True, return_counts=True)
    weld_id = weld_id.ravel()
    tw = weld_id[t]
    report = dict(vertices=len(v), triangles=len(t), welded_vertices=int(weld_id.max() + 1) if len(v) else 0,
                  split_vertex_groups=int((counts > 1).sum()))
    # Degenerate and duplicate faces.
    e1, e2 = v[t[:, 1]] - v[t[:, 0]], v[t[:, 2]] - v[t[:, 0]]
    cross = np.cross(e1, e2)
    area = .5 * np.linalg.norm(cross, axis=1)
    collapsed = (tw[:, 0] == tw[:, 1]) | (tw[:, 1] == tw[:, 2]) | (tw[:, 0] == tw[:, 2])
    report['degenerate_faces'] = int(((area < 1e-6) | collapsed).sum())
    faces = Counter(tuple(sorted(f)) for f in tw.tolist())
    report['duplicate_faces'] = int(sum(c - 1 for c in faces.values() if c > 1))
    # Edge use and orientation.
    edges = defaultdict(list)
    for ti, (a, b, c) in enumerate(tw.tolist()):
        for x, y in ((a, b), (b, c), (c, a)):
            if x != y:
                edges[(min(x, y), max(x, y))].append((ti, x, y))
    boundary = [(k, r[0]) for k, r in edges.items() if len(r) == 1]
    nonmanifold = [k for k, r in edges.items() if len(r) > 2]
    flipped_edges = [k for k, r in edges.items() if len(r) == 2 and r[0][1] == r[1][1]]
    report.update(boundary_edges=len(boundary), nonmanifold_edges=len(nonmanifold), inconsistent_winding_edges=len(flipped_edges))
    # Boundary loops with location.
    adj = defaultdict(set)
    for (a, b), _ in boundary:
        adj[a].add(b); adj[b].add(a)
    rep_vertex = {}
    for vi, w in enumerate(weld_id):
        rep_vertex.setdefault(int(w), vi)
    loops, seen = [], set()
    for s in list(adj):
        if s in seen:
            continue
        group, todo = {s}, [s]
        seen.add(s)
        while todo:
            a = todo.pop()
            for b in adj[a] - seen:
                seen.add(b); group.add(b); todo.append(b)
        ps = v[[rep_vertex[g] for g in group]]
        ws = Counter()
        for g in group:
            ws.update(W[rep_vertex[g]])
        side, region = side_and_region(dict(ws))
        length = sum(np.linalg.norm(v[rep_vertex[a]] - v[rep_vertex[b]]) for (a, b), _ in boundary if a in group)
        loops.append(dict(vertices=len(group), side=side, region=region, span_cm=np.ptp(ps, axis=0).round(3).tolist(),
                          perimeter_cm=round(float(length), 3), center=ps.mean(0).round(3).tolist(),
                          branched=any(len(adj[a]) != 2 for a in group)))
    loops.sort(key=lambda x: -x['perimeter_cm'])
    report['boundary_loops'] = loops
    # Stored normal versus geometric face normal (inverted shading / see-through faces).
    gn = cross / np.maximum(np.linalg.norm(cross, axis=1, keepdims=True), 1e-12)
    dots = np.einsum('ij,ij->i', gn, nrm.mean(1) / np.maximum(np.linalg.norm(nrm.mean(1), axis=1, keepdims=True), 1e-12))
    report['faces_normal_against_winding'] = int((dots < 0).sum())
    report['faces_normal_grazing'] = int(((dots >= 0) & (dots < .2)).sum())
    # Cracks: distinct welded vertices closer than `crack` cm that are on boundaries.
    bverts = np.array(sorted(adj))
    cracks = []
    if len(bverts):
        from scipy.spatial import cKDTree
        bp = v[[rep_vertex[b] for b in bverts]]
        tree = cKDTree(bp)
        for i, j in tree.query_pairs(crack):
            if bverts[j] not in adj[bverts[i]]:
                cracks.append(dict(a=int(bverts[i]), b=int(bverts[j]), gap_mm=round(float(np.linalg.norm(bp[i] - bp[j]) * 10), 3),
                                   region='/'.join(side_and_region(W[rep_vertex[bverts[i]]]))))
    report['boundary_cracks'] = cracks
    # Normal splits at welded vertices (hard shading lines) and UV seams.
    corner_normals = defaultdict(list); corner_uv = defaultdict(set)
    for ti in range(len(t)):
        for c in range(3):
            corner_normals[int(tw[ti, c])].append(nrm[ti, c])
            corner_uv[int(tw[ti, c])].add(tuple(np.round(uv[ti, c], 5)))
    hard = []
    for w, ns in corner_normals.items():
        ns = np.asarray(ns)
        if len(ns) < 2:
            continue
        nn = ns / np.maximum(np.linalg.norm(ns, axis=1, keepdims=True), 1e-12)
        ang = np.degrees(np.arccos(np.clip(nn @ nn.T, -1, 1))).max()
        if ang > 20:
            hard.append((w, float(ang)))
    report['hard_normal_vertices_over_20deg'] = len(hard)
    hard_regions = Counter('/'.join(side_and_region(W[rep_vertex[w]])) for w, _ in hard)
    report['hard_normal_regions'] = hard_regions.most_common(12)
    report['uv_seam_vertices'] = int(sum(len(s) > 1 for s in corner_uv.values()))
    # UV triangles: flipped (mirrored) and zero area, relative to the majority per material.
    uvc = (uv[:, 1, 0] - uv[:, 0, 0]) * (uv[:, 2, 1] - uv[:, 0, 1]) - (uv[:, 2, 0] - uv[:, 0, 0]) * (uv[:, 1, 1] - uv[:, 0, 1])
    flips = 0
    for m in np.unique(mats):
        s = np.sign(uvc[mats == m]); major = np.sign(np.median(s)) or 1.
        flips += int((s * major < 0).sum())
    report['uv_flipped_faces'] = flips
    report['uv_zero_area_faces'] = int((np.abs(uvc) < 1e-10).sum())
    # Texel density spread (stretch): 3D area per UV area, per material.
    dens = {}
    for m in np.unique(mats):
        sel = (mats == m) & (np.abs(uvc) > 1e-10) & (area > 1e-6)
        r = np.sqrt(area[sel] / (.5 * np.abs(uvc[sel])))
        if len(r):
            dens[int(m)] = dict(faces=int(sel.sum()), p5=round(float(np.percentile(r, 5)), 2), median=round(float(np.median(r)), 2),
                                p95=round(float(np.percentile(r, 95)), 2), outliers_over_3x=int(((r > 3 * np.median(r)) | (r < np.median(r) / 3)).sum()))
    report['texel_scale_cm_per_uv'] = dens
    report['material_faces'] = dict(Counter(int(m) for m in mats))
    return report


if __name__ == '__main__':
    path = Path(sys.argv[1])
    d = json.loads(path.read_text())
    skin = set(json.loads(sys.argv[2])) if len(sys.argv) > 2 else None
    r = audit(d, skin)
    out = O / ('audit_' + path.stem + '.json')
    out.write_text(json.dumps(r, indent=1))
    brief = {k: v for k, v in r.items() if k not in ('boundary_loops', 'boundary_cracks')}
    print(json.dumps(brief, indent=1))
    print('LOOPS')
    for l in r['boundary_loops'][:40]:
        print('  ', l)
    print('CRACKS', len(r['boundary_cracks']), r['boundary_cracks'][:15])
