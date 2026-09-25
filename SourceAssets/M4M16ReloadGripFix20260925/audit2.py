"""Same part-vs-shell audit as audit.py, but also covering the accepted AKM wrap
so the current M4/M16 numbers have a target to match."""
import bpy, json
from pathlib import Path
from mathutils.bvhtree import BVHTree

O = Path(__file__).parent; S = O.parent
DIGITS = ['thumb', 'index', 'middle', 'ring', 'pinky']
PARTS = ['hand_l'] + [f'{d}_{k}_l' for d in DIGITS for k in ('01', '02', '03')]


def eval_world(obj, dg):
    e = obj.evaluated_get(dg); me = e.to_mesh(); M = e.matrix_world
    verts = [M @ v.co for v in me.vertices]
    polys = [list(p.vertices) for p in me.polygons]
    e.to_mesh_clear()
    return verts, polys


def audit(label, path, mag_name, frames, action=None):
    bpy.ops.wm.open_mainfile(filepath=str(path), use_scripts=False)
    r = bpy.data.objects['SK_M4_Infima']
    a = bpy.data.actions[action] if action else r.animation_data.action
    r.animation_data.action = a; r.animation_data.action_slot = a.slots[0]
    arms = bpy.data.objects['SK_Manny_Arms_Export']
    mag = bpy.data.objects[mag_name]
    groups = [g.name for g in arms.vertex_groups]
    restb = r.data.bones['WPN_SOCKET_Magazine'].matrix_local
    res = {'file': str(path), 'action': a.name, 'mag': mag_name, 'frames': {}}
    for f in frames:
        bpy.context.scene.frame_set(int(f), subframe=f % 1)
        bpy.context.view_layer.update()
        dg = bpy.context.evaluated_depsgraph_get()
        pose = {b.name: b.matrix.copy() for b in r.pose.bones}
        local = r.matrix_world.inverted() @ (pose['WPN_SOCKET_Magazine'] @ restb.inverted())
        mv, mp = eval_world(mag, dg)
        av, _ = eval_world(arms, dg)
        tree = BVHTree.FromPolygons([local @ p for p in mv], mp, all_triangles=False)
        e = arms.evaluated_get(dg); me = e.to_mesh()
        owner = []
        for v in me.vertices:
            best, w = None, 0.0
            for g in v.groups:
                if g.weight > w:
                    best, w = groups[g.group], g.weight
            owner.append(best)
        e.to_mesh_clear()
        parts = {}
        for name in PARTS:
            idx = [i for i, o in enumerate(owner) if o == name]
            if not idx:
                continue
            d = []
            for i in idx:
                q = local @ av[i]
                loc, nor, _, dist = tree.find_nearest(q)
                if loc is None:
                    continue
                d.append(-dist if (q - loc).dot(nor) < 0 else dist)
            d.sort()
            parts[name] = {'min': round(d[0] * 1000, 2), 'p05': round(d[len(d) // 20] * 1000, 2),
                           'med': round(d[len(d) // 2] * 1000, 2),
                           'touch': sum(1 for x in d if abs(x) * 1000 < 3.0),
                           'pen': sum(1 for x in d if x * 1000 < -1.0),
                           'deep': round(min(d) * 1000, 2)}
        res['frames'][str(f)] = parts
    return res


JOBS = [
    ('AKM_acc_n', S / 'AKMReloadPolish20260911/base/A_AKM_reload.blend', 'AKM_FactoryMagazine_Preview', [148]),
    ('AKM_acc_e', S / 'AKMReloadPolish20260911/base/A_AKM_reload_empty.blend', 'AKM_FactoryMagazine_Preview', [240]),
    ('M4_n', S / 'ExtMagContact20260919/A_M4_ExtContact_reload.blend', 'M4_Magazine Light.003_Export', [54, 61, 76, 95]),
    ('M4_e', S / 'ExtMagContact20260919/A_M4_ExtContact_reload_empty.blend', 'M4_Magazine Light.003_Export', [43, 54, 80, 100]),
    ('M16_n', S / 'M16RemovalMelee20260920/Animations/base/A_M16_reload.blend', 'M16A2_Magazine', [54, 61, 76, 95]),
    ('M16_e', S / 'M16RemovalMelee20260920/Animations/base/A_M16_reload_empty.blend', 'M16A2_Magazine', [43, 54, 80, 100]),
]
report = {}
for label, path, mag_name, frames in JOBS:
    report[label] = audit(label, path, mag_name, frames)
(O / 'audit2.json').write_text(json.dumps(report, indent=2))
for label, v in report.items():
    for f, parts in v['frames'].items():
        row = ' '.join('%s med=%6.2f pen=%-4d' % (k.replace('_l', ''), parts[k]['med'], parts[k]['pen'])
                       for k in ['hand_l', 'thumb_02_l', 'thumb_03_l', 'index_01_l', 'index_02_l', 'index_03_l',
                                 'middle_02_l', 'middle_03_l', 'ring_02_l', 'ring_03_l', 'pinky_02_l', 'pinky_03_l'] if k in parts)
        print('%-10s f%-4s %s' % (label, f, row), flush=True)
print('AUDIT2_OK', flush=True)
