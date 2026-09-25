"""Verify the refined M16 reloads: shell contact profile and receiver clearance,
against the previous clips and the accepted AKM wrap."""
import bpy, json, sys
from pathlib import Path
from mathutils.bvhtree import BVHTree

O = Path(__file__).parent; S = O.parent
sys.path.insert(0, str(O))
import grip_lib as G

DIGITS = G.DIGITS
PARTS = ['hand_l'] + [f'{d}_{k}_l' for d in DIGITS for k in ('01', '02', '03')]
FAMILIES = ['base', 'vertical', 'canted', 'prism', 'angled']
KINDS = {'reload': (126, [76, 88, 95]), 'reload_empty': (162, [80, 95, 100])}


def eval_world(obj, dg):
    e = obj.evaluated_get(dg); me = e.to_mesh(); M = e.matrix_world
    verts = [M @ v.co for v in me.vertices]
    polys = [list(p.vertices) for p in me.polygons]
    e.to_mesh_clear()
    return verts, polys


def run(path, action, frames):
    bpy.ops.wm.open_mainfile(filepath=str(path), use_scripts=False)
    r = bpy.data.objects['SK_M4_Infima']
    a = r.animation_data.action if action is None else bpy.data.actions[action]
    r.animation_data.action = a; r.animation_data.action_slot = a.slots[0]
    arms = bpy.data.objects['SK_Manny_Arms_Export']
    mag = next(o for o in bpy.context.scene.objects if o.type == 'MESH' and o.parent == r
               and 'agazine' in o.name and any(g.name == 'WPN_SOCKET_Magazine' for g in o.vertex_groups))
    body = next(o for o in bpy.context.scene.objects if o.type == 'MESH' and o.parent == r
                and ('Receiver' in o.name or 'Body' in o.name))
    groups = [g.name for g in arms.vertex_groups]
    out = {}
    for f in frames:
        bpy.context.scene.frame_set(f); bpy.context.view_layer.update()
        dg = bpy.context.evaluated_depsgraph_get()
        av, _ = eval_world(arms, dg)
        e = arms.evaluated_get(dg); me = e.to_mesh()
        owner = []
        for v in me.vertices:
            best, w = None, 0.0
            for g in v.groups:
                if g.weight > w:
                    best, w = groups[g.group], g.weight
            owner.append(best)
        e.to_mesh_clear()
        rec = {}
        for tname, tobj in (('mag', mag), ('body', body)):
            tv, tp = eval_world(tobj, dg)
            tree = BVHTree.FromPolygons(tv, tp, all_triangles=False)
            parts = {}
            for name in PARTS:
                idx = [i for i, o in enumerate(owner) if o == name]
                if not idx:
                    continue
                d = []; pen = 0.0
                for i in idx:
                    loc, nor, _, dist = tree.find_nearest(av[i])
                    if loc is None:
                        continue
                    inside = (av[i] - loc).dot(nor) < 0
                    d.append(-dist if inside else dist)
                    if inside and dist < 0.025:
                        pen = max(pen, min(30.0, dist * 1000))
                d.sort()
                parts[name] = {'med': round(d[len(d) // 2] * 1000, 2), 'pen_mm': round(pen, 2)}
            rec[tname] = parts
        out[f] = rec
    return out


AKM = {'hand_l': 45.14, 'thumb_01_l': 7.77, 'thumb_02_l': 1.28, 'thumb_03_l': 23.77,
       'index_01_l': 20.86, 'index_02_l': 22.82, 'index_03_l': 15.46,
       'middle_01_l': 10.12, 'middle_02_l': 7.09, 'middle_03_l': 0.07,
       'ring_01_l': -1.08, 'ring_02_l': 2.63, 'ring_03_l': -2.97,
       'pinky_01_l': -3.62, 'pinky_02_l': 14.91, 'pinky_03_l': 8.71}
res = {}
for family in FAMILIES:
    for kind, (end, frames) in KINDS.items():
        base = 'A_M16_' + ('' if family == 'base' else family + '_') + kind
        ref = frames[0]
        new = run(O / 'm16_cache' / family / (base + '.blend'), base + '_GripPrecise', frames)
        old = run(S / 'M16RemovalMelee20260920/Animations' / family / (base + '.blend'), None, frames)
        en = sum((new[ref]['mag'][k]['med'] - AKM[k]) ** 2 for k in AKM if k in new[ref]['mag'])
        eo = sum((old[ref]['mag'][k]['med'] - AKM[k]) ** 2 for k in AKM if k in old[ref]['mag'])
        pn = max(v['pen_mm'] for v in new[ref]['body'].values())
        po = max(v['pen_mm'] for v in old[ref]['body'].values())
        pn_all = max(max(v['pen_mm'] for v in new[f]['body'].values()) for f in frames)
        po_all = max(max(v['pen_mm'] for v in old[f]['body'].values()) for f in frames)
        res[family + '/' + kind] = {'err_before': round(eo, 1), 'err_after': round(en, 1),
                                    'body_pen_before_mm': round(po_all, 2), 'body_pen_after_mm': round(pn_all, 2)}
        print('%-16s profile err %8.1f -> %6.1f   receiver pen %5.2f -> %5.2f mm' % (
            family + '/' + kind, eo, en, po_all, pn_all), flush=True)
        if family == 'base' and kind == 'reload':
            print('   before %s' % json.dumps({k: v['med'] for k, v in old[ref]['mag'].items()}), flush=True)
            print('   after  %s' % json.dumps({k: v['med'] for k, v in new[ref]['mag'].items()}), flush=True)
            print('   AKM    %s' % json.dumps(AKM), flush=True)
(O / 'verify_m16.json').write_text(json.dumps(res, indent=1))
print('VERIFY_M16_OK', flush=True)
