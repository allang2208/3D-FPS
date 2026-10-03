"""Read QBZ191's authored ADS frame; no asset edits, rendering or runtime tests."""
import json
import math
from pathlib import Path

import bpy
from mathutils import Matrix, Quaternion, Vector

output = Path(__file__).parent
source = output.parent / 'QBZ191Refine20260913/QBZ191_base_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(source))
rig = bpy.data.objects['SK_M4_Infima']
scene = bpy.context.scene
reflection = Matrix.Diagonal((1.0, -1.0, 1.0))
base = Quaternion(Vector((0.0, 0.0, 1.0)), math.pi / 2)
rows = []
for family in ['base', 'angled', 'vertical', 'canted', 'prism']:
    action = bpy.data.actions['QBZ191_' + family + '_aim']
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    scene.frame_set(0)
    bpy.context.view_layer.update()
    matrices = {name: rig.matrix_world @ rig.pose.bones[name].matrix
                for name in ['WPN_root', 'WPN_RearSight', 'WPN_FrontSight']}
    rear = reflection @ matrices['WPN_RearSight'].translation
    front = reflection @ matrices['WPN_FrontSight'].translation
    axis = (front - rear).normalized()
    up = (reflection @ (matrices['WPN_root'].to_quaternion() @ Vector((0, 0, 1)))).normalized()
    old_rotation = (base @ axis).rotation_difference(Vector((1, 0, 0))) @ base
    old_up = old_rotation @ up
    rows.append({'family': family, 'action': action.name,
                 'rear_source_metres': list(rear), 'front_source_metres': list(front),
                 'axis_component': list(axis), 'up_component': list(up),
                 'up_after_old_single_axis_calibration': list(old_up),
                 'old_up_camera_yz_angle_degrees': math.degrees(math.atan2(old_up.y, old_up.z))})
report = {'source': str(source), 'frame': 0,
          'coordinate_mapping': 'Blender to UE component: (x, -y, z)',
          'runtime_tested': False, 'frames': rows}
(output / 'source_frame.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(rows, separators=(',', ':')), flush=True)
