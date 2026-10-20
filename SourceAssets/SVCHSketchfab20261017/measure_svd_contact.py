"""Measure where the accepted SVD's right-hand contacts sit in the shared rig's idle pose.

Reads only the accepted author file. Writes Authoring/svd_contact.json so the SVCh
authoring step can seat the new weapon on exactly the same contact basis.
"""
import json
from pathlib import Path

import bpy
from mathutils import Vector

O = Path(__file__).parent
SRC = Path('D:/FPS3D/FPSGAME/SourceAssets/SVDCompletion20260923/SVD_Complete_Editable.blend')

bpy.ops.wm.open_mainfile(filepath=str(SRC))
rig = bpy.data.objects['SK_M4_Infima']
arm = bpy.data.objects['SK_Manny_Arms_Export']

act = bpy.data.actions['A_SVD_idle']
rig.animation_data_create()
rig.animation_data.action = act
if getattr(act, 'slots', None):
    rig.animation_data.action_slot = act.slots[0]
bpy.context.scene.frame_set(0)
bpy.context.view_layer.update()

dg = bpy.context.evaluated_depsgraph_get()


def deformed(obj):
    ev = obj.evaluated_get(dg)
    me = ev.to_mesh()
    mw = obj.matrix_world
    pts = [mw @ v.co for v in me.vertices]
    ev.to_mesh_clear()
    return pts


out = {'source': str(SRC), 'frame': 0, 'action': act.name, 'parts': {}, 'bones': {}}

for name in ('SM_SVD_Body', 'SM_SVD_Trigger', 'SM_SVD_Magazine', 'SM_SVD_ChargingHandle'):
    ob = bpy.data.objects.get(name)
    if not ob:
        continue
    pts = deformed(ob)
    mn = Vector((min(p[i] for p in pts) for i in range(3)))
    mx = Vector((max(p[i] for p in pts) for i in range(3)))
    out['parts'][name] = {'min': [round(v, 5) for v in mn],
                          'max': [round(v, 5) for v in mx],
                          'centre': [round(v, 5) for v in ((mn + mx) / 2)],
                          'verts': len(pts)}

# Grip panel: the body vertices around the pistol grip, which is behind and below
# the trigger. Take the body points inside a box centred on the trigger.
body = bpy.data.objects['SM_SVD_Body']
pts = deformed(body)
trig = out['parts']['SM_SVD_Trigger']['centre']
tc = Vector(trig)
band = [p for p in pts
        if abs(p.x - tc.x) < 0.030
        and tc.y + 0.010 < p.y < tc.y + 0.115
        and tc.z - 0.150 < p.z < tc.z - 0.010]
if band:
    mn = Vector((min(p[i] for p in band) for i in range(3)))
    mx = Vector((max(p[i] for p in band) for i in range(3)))
    out['grip'] = {'min': [round(v, 5) for v in mn], 'max': [round(v, 5) for v in mx],
                   'centre': [round(v, 5) for v in ((mn + mx) / 2)], 'n': len(band)}

# Bone markers in the same idle pose, rig space.
for b in ('WPN_root', 'WPN_Trigger', 'WPN_SOCKET_Magazine', 'WPN_RearSight',
          'WPN_FrontSight', 'WPN_SOCKET_Muzzle', 'WPN_SOCKET_Eject',
          'WPN_ChargingHandle', 'hand_r', 'hand_l'):
    pb = rig.pose.bones.get(b)
    if not pb:
        continue
    m = rig.matrix_world @ pb.matrix
    out['bones'][b] = {'head': [round(v, 5) for v in m.translation],
                       'rot': [round(v, 5) for v in m.to_quaternion()]}

(O / 'Authoring').mkdir(exist_ok=True)
(O / 'Authoring' / 'svd_contact.json').write_text(
    json.dumps(out, indent=1), encoding='utf-8')
print('SVD_CONTACT', json.dumps({k: v for k, v in out['parts'].items()}), flush=True)
print('SVD_CONTACT_GRIP', json.dumps(out.get('grip', {})), flush=True)
