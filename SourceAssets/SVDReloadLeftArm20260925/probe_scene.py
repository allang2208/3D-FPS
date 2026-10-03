"""Probe the authoring scene's camera/anchor relationship for the SVD blend."""
import bpy, math, sys, json
from pathlib import Path

ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
blend = ARGS[0]
action = ARGS[1]
bpy.ops.wm.open_mainfile(filepath=blend, use_scripts=False)
rig = bpy.data.objects['SK_M4_Infima']
act = bpy.data.actions[action]
rig.animation_data.action = act
rig.animation_data.action_slot = act.slots[0]
bpy.context.scene.frame_set(0)
bpy.context.view_layer.update()
print('RIG matrix_world', [round(v, 4) for row in rig.matrix_world for v in row])
for name in ['root', 'pelvis', 'spine_01', 'clavicle_l', 'hand_l', 'hand_r', 'WPN_root', 'WPN_SOCKET_Muzzle', 'WPN_FrontSight', 'WPN_RearSight']:
    b = rig.pose.bones.get(name)
    if not b:
        print(f'  bone {name}: absent')
        continue
    w = rig.matrix_world @ b.matrix
    print(f'  bone {name:20s} world pos cm {[round(v*100,2) for v in w.translation]} '
          f'axes {[round(v,3) for v in (w.to_3x3() @ b.vector.normalized())]}')
print('cam(0,-.10,.05) -> hand_l distance cm',
      round(((rig.matrix_world @ rig.pose.bones['hand_l'].matrix.translation) - bpy.app.driver_namespace.get('x', __import__('mathutils').Vector((0, -0.10, 0.05)))).length * 100, 2))
print('mesh objects', [o.name for o in bpy.data.objects if o.type == 'MESH'][:20])
