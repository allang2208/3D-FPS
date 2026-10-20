"""Apply the V8 surface repair to FBX export sources in place (binary-level, lossless elsewhere).

For every Mesh geometry, only bare-skin polygons are planned (material names
taken from the UE meshes imported from this FBX, else a name pattern). Control
points, deformers, bind poses, materials and every other node are untouched;
only PolygonVertexIndex, Edges and the per-polygon / per-corner layer arrays of
the repaired geometry are rewritten. The file is re-read and audited before the
original is replaced (backup in Before/).

Usage: python fbx_fix.py [--dry] <fbx or list.json> ...
"""
import json, re, sys, shutil, hashlib
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np
from fbx_bin import FBX
from generic_fix import plan_mesh, apply_json
from audit_mesh import audit

O = Path(__file__).parent; P = O.parents[1]
SKIN = re.compile(r'skin|bare', re.I)
NOT_SKIN = re.compile(r'glove|sleeve|cloth|leather|gauntlet|chain|mail|shirt|sweater|cuff|wrap|tape|handguard|handle|chrome', re.I)
MANNY_SLOT = re.compile(r'^MI_Manny_0[12]$')
V7_TIME = 1790272800  # 2026-09-25 02:00 local: V7 surfaces exist only after this; older Manny slots are the gloved original


def is_skin(name, file_time):
    if MANNY_SLOT.match(name): return file_time >= V7_TIME
    return bool(SKIN.search(name)) and not NOT_SKIN.search(name)


def ue_skin_names():
    """FBX path -> slot names that UE marked as skin for meshes imported from it."""
    out = defaultdict(set)
    snaps = {}
    for f in (O / 'Snapshots').glob('*.json'):
        pass
    index = json.loads((O / 'snap_index.json').read_text())
    by_path = {r['path']: k for k, r in index.items()}
    for row in json.loads((O / 'import_sources.json').read_text()):
        k = by_path.get(row['path'])
        if not k: continue
        snap = json.loads((O / 'Snapshots' / (k + '.json')).read_text())
        names = {s['slot'] for s in snap['slots'] if s['skin'] and 'PlayerBodySkin' not in s['base']}
        for s in row['sources']: out[s.replace('\\', '/').lower()] |= names
    return out


def sval(node, child):
    c = node.find(child)
    return c.props[0].get() if c and c.props else None


def name_of(node): return node.props[1].get().split(b'\x00\x01')[0].decode('utf-8', 'replace')


def polygons(pvi):
    polys, cur = [], []
    for x in pvi:
        if x < 0: cur.append(-x - 1); polys.append(cur); cur = []
        else: cur.append(x)
    return polys


class Layer:
    """Per-item view of one LayerElement* node."""
    def __init__(self, node, n_corners, n_polys):
        self.node = node
        self.mit = sval(node, 'MappingInformationType') or b''
        self.rit = sval(node, 'ReferenceInformationType') or b''
        self.items = {b'ByPolygonVertex': n_corners, b'ByPolygon': n_polys}.get(self.mit)
        self.arrays = [c for c in node.children if c.props and c.props[0].code in 'dfil' and len(c.props) == 1]

    def per_item(self):
        """Arrays that hold one entry (or one stride) per item."""
        if not self.items: return []
        rows = []
        for c in self.arrays:
            n = len(c.props[0].get())
            if self.rit in (b'IndexToDirect', b'Index'):
                if c.props[0].code == 'i' and n == self.items and (c.name.endswith('Index') or c.name in ('Materials',)): rows.append((c, 1))
            elif n and n % self.items == 0 and 1 <= n // self.items <= 4:
                rows.append((c, n // self.items))
        return rows


def corner_normals(geom, polys, starts):
    lay = next((c for c in geom.children if c.name == 'LayerElementNormal'), None)
    if lay is None: return None
    L = Layer(lay, starts[-1] + len(polys[-1]), len(polys))
    vals = np.asarray(lay.find('Normals').props[0].get()).reshape(-1, 3 if len(lay.find('Normals').props[0].get()) % 3 == 0 else 4)[:, :3]
    idx = lay.find('NormalsIndex')
    def get(p, k):
        c = starts[p] + k
        if L.mit == b'ByPolygonVertex': i = c
        elif L.mit == b'ByPolygon': i = p
        else: i = polys[p][k]
        if L.rit in (b'IndexToDirect', b'Index') and idx is not None: i = idx.props[0].get()[i]
        return vals[i].tolist()
    return get


def plan_geometry(geom, skin_names, mats_of_model, file_time):
    verts = np.asarray(geom.find('Vertices').props[0].get()).reshape(-1, 3)
    pvi = geom.find('PolygonVertexIndex').props[0].get()
    polys = polygons(pvi); starts = np.cumsum([0] + [len(p) for p in polys[:-1]]).tolist()
    mlay = next((c for c in geom.children if c.name == 'LayerElementMaterial'), None)
    if mlay is not None and sval(mlay, 'MappingInformationType') == b'ByPolygon':
        pm = list(mlay.find('Materials').props[0].get())
    else:
        first = mlay.find('Materials').props[0].get()[0] if mlay is not None and mlay.find('Materials') else 0
        pm = [first] * len(polys)
    names = mats_of_model
    skin = {i for i, n in enumerate(names) if is_skin(n, file_time) or (n in skin_names and not MANNY_SLOT.match(n))}
    sel = [i for i, m in enumerate(pm) if m in skin]
    if not sel: return None, 'no skin polygons'
    if any(len(polys[i]) != 3 for i in sel): return None, 'skin polygons are not triangles'
    getn = corner_normals(geom, polys, starts)
    if getn is None: return None, 'no normals layer'
    used = verts[sorted({x for i in sel for x in polys[i]})]
    diag = np.linalg.norm(np.ptp(used, axis=0))
    scale = min((0.01, 0.1, 1.0, 10.0, 100.0, 1000.0), key=lambda s: abs(np.log(diag * s / 110.0)))
    d = dict(positions=(verts * scale).tolist(), triangles=[polys[i] for i in sel],
             normals=[[getn(i, k) for k in range(3)] for i in sel], uv=[[[0, 0]] * 3 for _ in sel],
             triangle_materials=[pm[i] for i in sel], weights=[{} for _ in range(len(verts))])
    ops = plan_mesh(d)
    return dict(d=d, ops=ops, sel=sel, polys=polys, starts=starts, scale=scale), None


def apply_geometry(geom, pl):
    ops, sel, polys, starts = pl['ops'], pl['sel'], pl['polys'], pl['starts']
    rep = ops['rep']
    removed = {sel[i] for i in ops['remove']}
    kept = [p for p in range(len(polys)) if p not in removed]
    new_polys = [polys[p] for p in kept]
    corner_src = [starts[p] + k for p in kept for k in range(len(polys[p]))]
    poly_src = list(kept)
    over = {}
    for (ti, k), nn in ops['normals'].items():
        p = sel[ti]
        if p in removed: continue
        over[starts[p] + k] = nn
    new_over = {}
    for a in ops['add']:
        face = []
        for k, (ti, kk, ov) in enumerate(a['corners']):
            p = sel[ti]; face.append(rep[ov] if ov is not None else polys[p][kk])
            nn = a.get('normals', {}).get(k) or a.get('normals', {}).get(str(k))
            if nn is not None: new_over[len(corner_src)] = nn
            corner_src.append(starts[p] + kk)
        poly_src.append(sel[a['corners'][0][0]]); new_polys.append(face)
    n_c_old = starts[-1] + len(polys[-1]); n_p_old = len(polys)
    # Corner overrides are addressed in the new corner order.
    pos_of_old = {}
    for i, c in enumerate(corner_src):
        if c in over and c not in pos_of_old: pos_of_old[c] = i
    overrides = {pos_of_old[c]: nn for c, nn in over.items() if c in pos_of_old}
    overrides.update(new_over)
    pvi = []
    for f in new_polys: pvi += list(f[:-1]) + [-f[-1] - 1]
    geom.find('PolygonVertexIndex').props[0].set(pvi)
    for lay in [c for c in geom.children if c.name.startswith('LayerElement')]:
        L = Layer(lay, n_c_old, n_p_old)
        src = corner_src if L.mit == b'ByPolygonVertex' else poly_src if L.mit == b'ByPolygon' else None
        if src is not None:
            for node, stride in L.per_item():
                a = node.props[0].get()
                node.props[0].set([a[i * stride + s] for i in src for s in range(stride)])
        if lay.name == 'LayerElementNormal' and overrides:
            normals = lay.find('Normals'); idx = lay.find('NormalsIndex')
            vals = list(normals.props[0].get()); stride = 4 if len(vals) % 3 else 3
            if L.mit == b'ByPolygonVertex' and L.rit == b'Direct':
                for c, nn in overrides.items(): vals[c * stride:c * stride + 3] = nn
            elif L.mit == b'ByPolygonVertex' and idx is not None:
                ix = list(idx.props[0].get())
                for c, nn in overrides.items():
                    ix[c] = len(vals) // stride; vals += list(nn) + ([1.0] if stride == 4 else [])
                idx.props[0].set(ix)
            else:
                raise RuntimeError('normal override unsupported for mapping %s' % L.mit)
            normals.props[0].set(vals)
    edges = geom.find('Edges')
    if edges is not None:
        old_e = edges.props[0].get(); oldpvi = []
        for f in polys: oldpvi += f
        old_key = {}
        for i, c in enumerate(old_e):
            p = max(j for j in range(len(starts)) if starts[j] <= c) if False else None
        # Rebuild edge list in first-appearance order: value = corner index of the edge start.
        flat = [x for f in new_polys for x in f]; nstarts = np.cumsum([0] + [len(f) for f in new_polys[:-1]]).tolist()
        seen, ne = set(), []
        for pi, f in enumerate(new_polys):
            for k in range(len(f)):
                key = (min(f[k], f[(k + 1) % len(f)]), max(f[k], f[(k + 1) % len(f)]))
                if key not in seen: seen.add(key); ne.append(nstarts[pi] + k)
        byedge = [lay for lay in geom.children if lay.name.startswith('LayerElement') and sval(lay, 'MappingInformationType') == b'ByEdge']
        if byedge:
            ostarts = starts
            def edge_key(c, plist, st):
                pi = int(np.searchsorted(st, c, side='right') - 1); f = plist[pi]; k = c - st[pi]
                return (min(f[k], f[(k + 1) % len(f)]), max(f[k], f[(k + 1) % len(f)]))
            okeys = [edge_key(c, polys, ostarts) for c in old_e]
            nkeys = [edge_key(c, new_polys, nstarts) for c in ne]
            for lay in byedge:
                for node, stride in [(c, 1) for c in lay.children if c.props and c.props[0].code in 'il' and len(c.props[0].get()) == len(old_e)]:
                    a = node.props[0].get(); m = dict(zip(okeys, a)); common = Counter(a).most_common(1)[0][0] if len(a) else 0
                    node.props[0].set([m.get(k, common) for k in nkeys])
        edges.props[0].set(ne)
    return len(removed), len(ops['add']), len(overrides)


def model_materials(fbx):
    objs = next(n for n in fbx.roots if n.name == 'Objects')
    mats = {c.props[0].get(): name_of(c) for c in objs.children if c.name == 'Material'}
    conns = [c for c in next(n for n in fbx.roots if n.name == 'Connections').children if c.name == 'C']
    parent = {}; order = defaultdict(list)
    for c in conns:
        kind, child, par = c.props[0].get(), c.props[1].get(), c.props[2].get()
        if kind != b'OO': continue
        if child in mats: order[par].append(mats[child])
        else: parent.setdefault(child, par)
    return objs, parent, order


def skin_tris(fbx, skin_names, file_time):
    """Re-read check: audit the skin polygons of every geometry."""
    objs, parent, order = model_materials(fbx)
    rows = []
    for g in [c for c in objs.children if c.name == 'Geometry' and len(c.props) > 2 and c.props[2].get() == b'Mesh']:
        pl, why = plan_geometry(g, skin_names, order.get(parent.get(g.props[0].get()), []), file_time)
        if pl: rows.append(audit(dict(pl['d'], triangles=pl['d']['triangles'])))
    return rows


def fix_file(path, dry=False):
    path = Path(path); key = str(path).replace('\\', '/').lower()
    names = UE.get(key, set())
    file_time = path.stat().st_mtime
    fbx = FBX(path)
    objs, parent, order = model_materials(fbx)
    report = []
    for g in [c for c in objs.children if c.name == 'Geometry' and len(c.props) > 2 and c.props[2].get() == b'Mesh']:
        gname = name_of(g)
        pl, why = plan_geometry(g, names, order.get(parent.get(g.props[0].get()), []), file_time)
        if pl is None: report.append(dict(geometry=gname, skipped=why)); continue
        ops = pl['ops']
        if not (ops['remove'] or ops['add'] or ops['normals']): report.append(dict(geometry=gname, clean=True)); continue
        check = audit(apply_json(pl['d'], ops)); before = audit(pl['d'])
        if check['degenerate_faces'] or check['inconsistent_winding_edges'] or check['nonmanifold_edges'] > before['nonmanifold_edges'] \
                or len(check['boundary_loops']) > len(before['boundary_loops']):
            report.append(dict(geometry=gname, rejected=dict(ops['notes']))); continue
        removed, added, normals = apply_geometry(g, pl)
        report.append(dict(geometry=gname, removed=removed, added=added, normal_corners=normals, notes=dict(ops['notes']),
                           scale_to_cm=pl['scale'], openings=(len(before['boundary_loops']), len(check['boundary_loops']))))
    changed = any('removed' in r for r in report)
    if changed and not dry:
        tmp = path.with_suffix('.v8tmp')
        fbx.save(tmp)
        again = FBX(tmp)
        expected = sorted(r['openings'][1] for r in report if 'removed' in r)
        audits = skin_tris(again, names, file_time)
        if any(a['degenerate_faces'] or a['inconsistent_winding_edges'] for a in audits):
            tmp.unlink(); raise RuntimeError('re-read audit failed for %s' % path)
        # Every node except the rewritten geometry arrays must be byte-identical;
        # control points (Vertices) of the rewritten geometry too.
        old, new = FBX(path), again
        def blob(f, n):
            b = bytearray(); f._write(n, b); return bytes(b)
        for ro, rn in zip(old.roots, new.roots):
            if ro.name != 'Objects':
                if blob(old, ro) != blob(new, rn): tmp.unlink(); raise RuntimeError('node changed: %s' % ro.name)
                continue
            for co, cn in zip(ro.children, rn.children):
                if co.name == 'Geometry' and blob(old, co) != blob(new, cn):
                    if blob(old, co.find('Vertices')) != blob(new, cn.find('Vertices')):
                        tmp.unlink(); raise RuntimeError('control points changed in %s' % name_of(co))
                elif blob(old, co) != blob(new, cn):
                    tmp.unlink(); raise RuntimeError('object changed: %s %s' % (co.name, name_of(co)))
        backup = O / 'Before' / path.relative_to(P); backup.parent.mkdir(parents=True, exist_ok=True)
        if not backup.exists(): shutil.copy2(path, backup)
        shutil.move(str(tmp), str(path))
    return dict(path=str(path), changed=changed, skin_names=sorted(names), geometries=report,
                sha256=hashlib.sha256(path.read_bytes()).hexdigest() if changed and not dry else None)


if __name__ == '__main__':
    args = sys.argv[1:]; dry = '--dry' in args; args = [a for a in args if a != '--dry']
    files = []
    for a in args: files += json.load(open(a)) if a.endswith('.json') else [a]
    UE = ue_skin_names()
    out = O / ('fbx_dryrun.json' if dry else 'fbx_receipt.json')
    rows = json.loads(out.read_text()) if out.exists() and not dry else []
    done = {r['path'] for r in rows}
    for f in files:
        if str(Path(f)) in done: continue
        try: r = fix_file(f, dry)
        except Exception as exc: r = dict(path=str(Path(f)), error=repr(exc))
        rows.append(r); out.write_text(json.dumps(rows, indent=1))
        print('BARE_V8_FBX', 'DRY' if dry else '', Path(f).name, json.dumps(r['geometries'] if 'geometries' in r else r)[:400], flush=True)
