"""Settle the PKM viewmodel's left/right axis and camera frame from the rig."""
import json
from pathlib import Path

import bpy
import numpy as np

ROOT = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922')
HERE = ROOT / 'ChargeDirection40'
BLEND = ROOT / 'Charge34' / 'PKM_base_ChargePush_Editable.blend'

bpy.ops.wm.open_mainfile(filepath=str(BLEND))
scene = bpy.context.scene
rig = bpy.data.objects['PKM_Manny_Rig']
action = bpy.data.actions['PKM34_base_reload_empty']
rig.animation_data.action = action
rig.animation_data.action_slot = action.slots[0]
scene.render.fps = 120
scene.frame_set(0)
bpy.context.view_layer.update()

print('rig matrix_world:\n', np.round(np.array(rig.matrix_world), 4))
pb = rig.pose.bones
for n in ('VM_Root', 'root', 'WPN_root', 'clavicle_l', 'clavicle_r',
          'upperarm_l', 'upperarm_r', 'hand_l', 'hand_r',
          'WPN_ChargingHandle', 'PKM_Charge', 'WPN_SOCKET_Eject',
          'WPN_SOCKET_Muzzle'):
    if n in pb:
        print('%-22s head %s' % (n, np.round(np.array(pb[n].head), 4)))

# armature-level and object-level extra transforms
print('\nobject scale', tuple(rig.scale), 'loc', tuple(rig.location))
if rig.parent:
    print('parent', rig.parent.name, tuple(rig.parent.location))
print('armature unit scale', rig.data.unit_settings.scale_length if hasattr(rig.data, 'unit_settings') else 'n/a')

# any bone whose name suggests a camera / eye
print('\ncamera-ish bones', [b.name for b in rig.data.bones
                             if any(k in b.name.lower() for k in ('cam', 'eye', 'head', 'view'))])

# where does the arms mesh sit relative to the rig?
for ob in bpy.data.objects:
    if ob.type == 'MESH' and 'Arms' in ob.name:
        print('mesh %-28s parent=%s matrix_world diag %s' % (
            ob.name, ob.parent.name if ob.parent else None,
            np.round(np.diag(np.array(ob.matrix_world)), 4)))
print('AXIS_PROBE_DONE')