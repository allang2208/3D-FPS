"""Verify the refined M4 grip: shell contact profile and receiver clearance."""
import bpy, json, sys
from pathlib import Path
from mathutils.bvhtree import BVHTree

O = Path(__file__).parent; S = O.parent
sys.path.insert(0, str(O))
import grip_lib as G

DIGITS = G.DIGITS
PARTS = ['hand_l'] + [f'{d}_{k}_l' for d in DIGITS for k in ('01', '02', '03')]


def eval_world(obj, dg):
    e = obj.evaluated_get(dg); me = e.to_mesh(); M = e.matrix_world
    verts = [M @ v.co for v in me.vertices]
    polys = [list(p.vertices) for p in me.polygons]
    e.to_mesh_clear()
    return verts, polys


def run(label, path, action, mag_name, frames, body_name=None):
    bpy.ops.wm.open_mainfile(filepath=str(path), use_scripts=False)
    r = bpy.data.objects['SK_M4_Infima']
    a = bpy.data.actions[action]
    r.animation_data.action = a; r.animation_data.action_slot = a.slots[0]
    arms = bpy.data.objects['SK_Manny_Arms_Export']
    mag = bpy.data.objects[mag_name]
    body = bpy.data.objects[body_name] if body_name else None
    groups = [g.name for g in arms.vertex_groups]
    restb = r.data.bones['WPN_SOCKET_Magazine'].matrix_local
    out = {}
    for f in frames:
        bpy.context.scene.frame_set(int(f), subframe=f % 1)
        bpy.context.view_layer.update()
        dg = bpy.context.evaluated_depsgraph_get()
        pose = {b.name: b.matrix.copy() for b in r.pose.bones}
        local = r.matrix_world.inverted() @ (pose['WPN_SOCKET_Magazine'] @ restb.inverted())
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
        for tname, tobj in [('mag', mag), ('body', body)]:
            if tobj is None:
                continue
            tv, tp = eval_world(tobj, dg)
            if tname == 'mag':
                tree = BVHTree.FromPolygons([local @ p for p in tv], tp, all_triangles=False)
                q = [local @ v for v in av]
            else:
                tree = BVHTree.FromPolygons(tv, tp, all_triangles=False)
                q = av
            parts = {}
            for name in PARTS:
                idx = [i for i, o in enumerate(owner) if o == name]
                if not idx:
                    continue
                d = []
                for i in idx:
                    loc, nor, _, dist = tree.find_nearest(q[i])
                    if loc is None:
                        continue
                    d.append(-dist if (q[i] - loc).dot(nor) < 0 else dist)
                d.sort()
                parts[name] = {'med': round(d[len(d) // 2] * 1000, 2),
                               'min': round(d[0] * 1000, 2),
                               'touch': sum(1 for x in d if abs(x) * 1000 < 3.0),
                               'pen': sum(1 for x in d if -0.03 < x < -0.001)}
            rec[tname] = parts
        out[str(f)] = rec
    return out


res = {}
res['after'] = run('after', O / 'M4Animations/A_M4_ExtContact_reload.blend', 'A_M4_ExtContact_reload_GripPrecise',
                   'M4_Magazine Light.003_Export', [61, 76, 88, 95], 'M4_M4 Body_Export')
res['before'] = run('before', S / 'ExtMagContact20260919/A_M4_ExtContact_reload.blend', 'A_M4_ExtContact_reload',
                    'M4_Magazine Light.003_Export', [61, 76, 88, 95], 'M4_M4 Body_Export')
res['akm'] = run('akm', S / 'AKMReloadPolish20260911/base/A_AKM_reload.blend', 'A_AKM_reload_Polished',
                 'AKM_FactoryMagazine_Preview', [148])
for tag in ['akm', 'before', 'after']:
    for f, rec in res[tag].items():
        d = rec['mag']
        print('%-7s f%-4s mag %s' % (tag, f, ' '.join('%s %.1f' % (k.replace('_l', ''), v['med'])
                                                      for k, v in d.items())), flush=True)
        if 'body' in rec:
            pen = {k: v['pen'] for k, v in rec['body'].items() if v['pen'] > 0}
            mn = {k: v['min'] for k, v in rec['body'].items() if v['min'] < 2.0}
            print('        body pen=%s  near=%s' % (pen, mn), flush=True)
(O / 'verify_m4.json').write_text(json.dumps(res, indent=1))
print('VERIFY_M4_OK', flush=True)
