"""Is the thumb opposing the fingers?  Distance from the thumb tip to the index /
middle pads, and the thumb tip's clearance to the magazine shell, for the shipped
AKM / A762 grip and the accepted SVD / M4 grips."""
import bpy, json, sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

O = Path(__file__).parent; S = O.parent
A762_LIB = S / 'A762Meshy20260920/Accessories05/A762_AccessoryReady_Editable.blend'


def tip(rig, pose, bone):
    return rig.matrix_world @ pose[bone] @ Vector((0, rig.data.bones[bone].length, 0))


def run(label, path, action, f):
    bpy.ops.wm.open_mainfile(filepath=str(path), use_scripts=False)
    r = bpy.data.objects['SK_M4_Infima']
    a = r.animation_data.action if action is None else bpy.data.actions[action]
    r.animation_data.action = a; r.animation_data.action_slot = a.slots[0]
    sc = bpy.context.scene
    sc.frame_set(f); bpy.context.view_layer.update()
    pose = {b.name: b.matrix.copy() for b in r.pose.bones}
    restb = r.data.bones['WPN_SOCKET_Magazine'].matrix_local
    D = r.matrix_world @ pose['WPN_SOCKET_Magazine'] @ restb.inverted() @ r.matrix_world.inverted()
    mags = [o for o in sc.objects if o.type == 'MESH'
            and any(g.name == 'WPN_SOCKET_Magazine' for g in o.vertex_groups)]
    if not mags:
        with bpy.data.libraries.load(str(A762_LIB), link=False) as (src, dst):
            dst.objects = [n for n in src.objects if n.startswith('A762_R02_Magazine_')]
        for o in dst.objects:
            if o is not None:
                sc.collection.objects.link(o); o.hide_set(False); o.hide_render = False
                mags.append(o)
    mv, mp = [], []
    for m in mags:
        off = len(mv)
        mv.extend(D @ (m.matrix_world @ v.co) for v in m.data.vertices)
        mp.extend([[off + i for i in p.vertices] for p in m.data.polygons])
    tree = BVHTree.FromPolygons(mv, mp, all_triangles=False)
    th = tip(r, pose, 'thumb_03_l')
    ix = tip(r, pose, 'index_03_l')
    md = tip(r, pose, 'middle_03_l')
    loc, _, dist, _ = tree.find_nearest(th)
    out = {'thumb_tip_to_index_tip_mm': round((th - ix).length * 1000, 1),
           'thumb_tip_to_middle_tip_mm': round((th - md).length * 1000, 1),
           'thumb_tip_to_shell_mm': round(dist * 1000, 1)}
    print('%-6s f%-4s %s' % (label, f, json.dumps(out)), flush=True)
    return out


V4 = S / 'RifleMagazineGrip20260922/IndexClearanceV4'
CASES = [
    ('AKM', V4 / 'AKM/standard/base/A_AKM_reload.blend', None, 148),
    ('A762', V4 / 'A762/standard/base/A_A762_reload.blend', None, 148),
    ('SVD', S / 'SVDThumbUp20260923/SVD_base_Editable.blend', 'A_SVD_reload', 148),
    ('M4', S / 'ExtMagContact20260919/A_M4_ExtContact_reload.blend', None, 76),
]
res = {}
for t, p, a, f in CASES:
    res[t] = run(t, p, a, f)
(O / 'thumb_opposition.json').write_text(json.dumps(res, indent=1))
print('OPP_OK', flush=True)
