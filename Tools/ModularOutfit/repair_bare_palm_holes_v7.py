"""Close local V7 palm openings the same way as Bow ContactV9.

Work in the shared canonical mesh first, then replay the same face ops onto
each native-authored profile so gloves keep vertex correspondence.
"""
import json
from collections import defaultdict
from pathlib import Path
import numpy as np

PROJECT = Path(r'D:/FPS3D/FPSGAME')
ROOT = PROJECT / 'SourceAssets/ModularOutfit20260925/BarePalmV7'
MASTER = ROOT / 'M4_original.json'
BACKUP = ROOT / 'M4_original.before_holes.json'


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def save(path, data):
    Path(path).write_text(json.dumps(data, separators=(',', ':')), encoding='utf-8')


def weld_map(verts):
    mapping = {}
    weld = list(range(len(verts)))
    for i, v in enumerate(verts):
        if abs(v[0]) > 40:
            key = tuple(np.round(v, 4))
            weld[i] = mapping.setdefault(key, i)
    return weld


def collect_patches(data):
    verts = np.asarray(data['positions'], dtype=float)
    weld = weld_map(verts)
    triangles = [[weld[int(i)] for i in t] for t in data['triangles']]
    edges = defaultdict(list)
    for ti, t in enumerate(triangles):
        for a, b in zip(t, t[1:] + t[:1]):
            if a != b:
                edges[tuple(sorted((a, b)))].append((ti, a, b))
    boundary = [v[0] for v in edges.values()
                if len(v) == 1 and data['triangle_materials'][v[0][0]] == 2
                and min(abs(verts[i, 0]) for i in v[0][1:]) > 40]
    bad = {ti for ti, _a, _b in boundary}
    for ti, face in enumerate(triangles):
        if data['triangle_materials'][ti] != 2:
            continue
        a, b, c = verts[face]
        normal = np.mean(data['normals'][ti], axis=0)
        if np.dot(np.cross(b - a, c - a), normal) > 1e-8:
            bad.add(ti)
    seed = {v for ti in bad for v in triangles[ti]}
    patch = {ti for ti, face in enumerate(triangles)
             if data['triangle_materials'][ti] == 2 and any(v in seed for v in face)}
    vertex_faces = defaultdict(set)
    for ti in patch:
        for v in triangles[ti]:
            vertex_faces[v].add(ti)
    remaining = set(patch)
    components = []
    while remaining:
        todo = [remaining.pop()]
        group = set(todo)
        while todo:
            ti = todo.pop()
            for v in triangles[ti]:
                for tj in vertex_faces[v] & remaining:
                    remaining.remove(tj)
                    group.add(tj)
                    todo.append(tj)
        components.append(group)
    patches = []
    for group in components:
        local_edges = defaultdict(list)
        for ti in group:
            f = triangles[ti]
            for a, b in zip(f, f[1:] + f[:1]):
                local_edges[tuple(sorted((a, b)))].append((ti, a, b))
        boundary_edges = [v[0] for v in local_edges.values() if len(v) == 1]
        adjacent = defaultdict(list)
        for ti, a, b in boundary_edges:
            adjacent[a].append(b)
            adjacent[b].append(a)
        if any(len(v) != 2 for v in adjacent.values()):
            raise RuntimeError('Palm patch boundary branches')
        unseen = set(adjacent)
        loops = []
        while unseen:
            start = min(unseen)
            loop = []
            prev = None
            cur = start
            while cur in unseen:
                unseen.remove(cur)
                loop.append(cur)
                nxt = next(n for n in adjacent[cur] if n != prev)
                prev, cur = cur, nxt
            loops.append(loop)
        loop = max(loops, key=lambda v: sum(
            np.linalg.norm(verts[a] - verts[b]) for a, b in zip(v, v[1:] + v[:1])))
        if np.ptp(verts[loop], axis=0).max() > 2.0:
            raise RuntimeError('Palm repair exceeds local defect region')
        patches.append({
            'faces': sorted(group),
            'loop': loop,
            'inner_loops': len(loops) - 1,
            'side': 'r' if float(verts[loop].mean(0)[0]) > 0 else 'l',
        })
    return weld, triangles, patches


def apply_patches(data, weld, triangles, patches):
    verts = np.asarray(data['positions'], dtype=float)
    data['triangles'] = [list(t) for t in triangles]
    has_canon = 'canonical_positions' in data
    canon = np.asarray(data['canonical_positions'], dtype=float) if has_canon else verts
    removed = set()
    added = []
    info = []
    for patch in patches:
        loop = patch['loop']
        group = patch['faces']
        center = len(data['positions'])
        data['positions'].append(verts[loop].mean(0).tolist())
        if has_canon:
            data['canonical_positions'].append(canon[loop].mean(0).tolist())
        weights = defaultdict(float)
        for vi in loop:
            for name, weight in data['weights'][vi].items():
                weights[name] += weight / len(loop)
        weights = {k: v for k, v in sorted(weights.items(), key=lambda item: item[1], reverse=True)[:8]}
        total = sum(weights.values())
        data['weights'].append({k: v / total for k, v in weights.items()})

        def corner(vi, key):
            rows = [data[key][ti][data['triangles'][ti].index(vi)]
                    for ti in group if vi in data['triangles'][ti]]
            return np.mean(rows, axis=0)

        keys = [k for k in ('uv', 'normals', 'canonical_normals') if k in data]
        corner_values = {key: {vi: corner(vi, key) for vi in loop} for key in keys}
        center_values = {key: np.mean(list(vals.values()), axis=0) for key, vals in corner_values.items()}
        for a, b in zip(loop, loop[1:] + loop[:1]):
            face = [a, b, center]
            if 'normals' in center_values:
                normal = center_values['normals']
                if np.dot(np.cross(verts[b] - verts[a],
                                   np.array(data['positions'][center]) - verts[a]), normal) > 0:
                    face = [b, a, center]
            row = {'triangles': face, 'triangle_materials': 2}
            for key in keys:
                row[key] = [corner_values[key][vi].tolist() if vi != center
                            else center_values[key].tolist() for vi in face]
            added.append(row)
        removed.update(group)
        info.append({
            'side': patch['side'], 'removed_faces': group, 'boundary': loop,
            'center_vertex': center, 'filled_inner_loops': patch['inner_loops'],
        })
    keep = [i for i in range(len(data['triangles'])) if i not in removed]
    for key in ('triangles', 'triangle_materials', 'uv', 'normals', 'canonical_normals'):
        if key not in data:
            continue
        data[key] = [data[key][i] for i in keep] + [row[key] for row in added]
    return info, len(removed), len(added)


if not BACKUP.exists():
    BACKUP.write_bytes(MASTER.read_bytes())
master = load(MASTER)
weld, welded_tris, patches = collect_patches(master)
if len(patches) != 4:
    raise RuntimeError('Expected 4 local palm patches, got %d' % len(patches))
info, n_old, n_new = apply_patches(master, weld, welded_tris, patches)
master['contract'] = 'V7 palm openings capped; Bow ContactV9 local patch; corner data retained'
save(MASTER, master)
(ROOT / 'surface_repair.json').write_text(json.dumps({
    'source': 'Bow ContactV9 local topology patch applied to shared V7',
    'patches': info, 'replaced_faces': n_old, 'new_faces': n_new,
    'runtime_tested': False,
}, indent=2) + '\n', encoding='utf-8')
print('MASTER_PALM_REPAIR', len(info), 'patches;', n_old, 'old faces;', n_new, 'new faces', flush=True)

manifest = json.loads((ROOT / 'manifest.json').read_text(encoding='utf-8-sig'))
for entry in manifest:
    path = Path(entry['authored'])
    data = load(path)
    nvert = len(data['positions'])
    if nvert == len(weld):
        local_weld = weld
        local_tris = [[weld[int(i)] for i in t] for t in data['triangles']]
        local_patches = patches
    else:
        canon = np.asarray(data['canonical_positions'], dtype=float)
        side = -1 if canon[:, 0].mean() < 0 else 1
        master_canon = np.asarray(json.loads(BACKUP.read_text(encoding='utf-8-sig'))['positions'], dtype=float)
        keep = np.flatnonzero(master_canon[:, 0] * side > 0)
        if len(keep) != nvert:
            raise RuntimeError('Single-arm correspondence lost: ' + entry['profile'])
        inv = {int(src): i for i, src in enumerate(keep)}
        local_weld = [inv[weld[int(src)]] if weld[int(src)] in inv else i
                      for i, src in enumerate(keep)]
        # Rebuild weld inside the subset from this profile's own positions.
        local_weld = weld_map(np.asarray(data['positions'], dtype=float))
        local_tris = [[local_weld[int(i)] for i in t] for t in data['triangles']]
        _w, _t, local_patches = collect_patches(data)
        if any(np.ptp(np.asarray(data['positions'])[p['loop']], axis=0).max() > 2.0 for p in local_patches):
            raise RuntimeError('Single-arm patch too large: ' + entry['profile'])
    pinfo, old, new = apply_patches(data, local_weld, local_tris, local_patches)
    data['contract'] = 'Accepted V7 surface; local palm openings capped; native weights retained'
    save(path, data)
    entry['vertices'] = len(data['positions'])
    entry['triangles'] = len(data['triangles'])
    print('AUTHORED_PALM_REPAIR', entry['profile'], len(pinfo), old, new, flush=True)

(ROOT / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
print('V7_PALM_HOLES_REPAIRED', flush=True)
