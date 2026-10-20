"""Measure the accepted SVD's contacts in WPN_root space at the idle pose.

That is the space the SVCh is authored in, so the seat becomes one rigid
translation: `svd_grip - svch_grip` in the same frame. Writes
Authoring/svd_root_space.json.
"""
import json
from pathlib import Path

import bpy
from mathutils import Vector

O = Path(__file__).parent
SRC = Path('D:/FPS3D/FPSGAME/SourceAssets/SVDCompletion20260923/SVD_Complete_Editable.blend')

bpy.ops.wm.open_mainfile(filepath=str(SRC))
rig = bpy.data.objects['SK_M4_Infima']
act = bpy.data.actions['A_SVD_idle']
rig.animation_data_create()
rig.animation_data.action = act
if getattr(act, 'slots', None):
    rig.animation_data.action_slot = act.slots[0]
bpy.context.scene.frame_set(0)
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()

root = rig.matrix_world @ rig.pose.bones['WPN_root'].matrix
inv = root.inverted()


def local_pts(name):
    ob = bpy.data.objects[name]
    ev = ob.evaluated_get(dg)
    me = ev.to_mesh()
    mw = ob.matrix_world
    pts = [inv @ (mw @ v.co) for v in me.vertices]
    ev.to_mesh_clear()
    return pts


def box(pts):
    mn = Vector((min(p[i] for p in pts) for i in range(3)))
    mx = Vector((max(p[i] for p in pts) for i in range(3)))
    return {'min': [round(v, 5) for v in mn], 'max': [round(v, 5) for v in mx],
            'centre': [round(v, 5) for v in ((mn + mx) / 2)], 'n': len(pts)}


out = {'source': str(SRC), 'space': 'WPN_root local, metres, idle frame 0'}
for name, key in (('SM_SVD_Body', 'Body'), ('SM_SVD_Trigger', 'Trigger'),
                  ('SM_SVD_Magazine', 'Magazine'),
                  ('SM_SVD_ChargingHandle', 'ChargingHandle')):
    if bpy.data.objects.get(name):
        out[key] = box(local_pts(name))

body = local_pts('SM_SVD_Body')
tc = Vector(out['Trigger']['centre'])
# Pistol grip panel: behind the trigger and below it. Muzzle is -Y.
for dx, dy, dzt, dzb, tag in ((0.030, 0.110, 0.150, 0.010, 'grip'),
                              (0.045, 0.150, 0.200, 0.005, 'grip_wide')):
    band = [p for p in body
            if abs(p.x - tc.x) < dx
            and tc.y + 0.015 < p.y < tc.y + dy
            and tc.z - dzt < p.z < tc.z - dzb]
    if len(band) >= 8:
        out[tag] = box(band)

# Hand bones in the same space.
for b in ('hand_r', 'hand_l', 'WPN_Trigger', 'WPN_SOCKET_Magazine', 'WPN_RearSight',
          'WPN_FrontSight', 'WPN_SOCKET_Muzzle', 'WPN_SOCKET_Eject'):
    pb = rig.pose.bones.get(b)
    if pb:
        m = rig.matrix_world @ pb.matrix
        loc = inv @ m.translation
        out.setdefault('bones', {})[b] = {'loc': [round(v, 5) for v in loc],
                                          'rot': [round(v, 5) for v in m.to_quaternion()]}

(O / 'Authoring' / 'svd_root_space.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
print('SVD_ROOT', json.dumps({k: v for k, v in out.items() if k != 'bones'}), flush=True)
print('SVD_ROOT_BONES', json.dumps(out.get('bones', {})), flush=True)
