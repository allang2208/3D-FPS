"""Read the retained rig and ready grasp for the new photo-directed guard."""
import bpy, json
from pathlib import Path
from mathutils import Vector

P = Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(P.parent / 'GuardPoseV19/AzureRunesword_Manny_Editable.blend'))
rig = bpy.data.objects['SK_RuneSword_Rig']
scene = bpy.context.scene
action = bpy.data.actions['A_RuneSword_Slash1']
rig.animation_data.action = action
rig.animation_data.action_slot = action.slots[0]
scene.frame_set(0)
bpy.context.view_layer.update()
rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
pose = {b.name: b.matrix.copy() for b in rig.pose.bones}
names = [n for n in rest if n.endswith(('_l', '_r')) or n in ('WPN_root', 'Blade_Base', 'Blade_Tip')]
record = {'fps': scene.render.fps, 'rig_matrix': [list(v) for v in rig.matrix_world],
          'actions': {a.name: list(a.frame_range) for a in bpy.data.actions},
          'bones': {n: {'parent': rig.data.bones[n].parent.name if rig.data.bones[n].parent else None,
                        'rest': [list(v) for v in rest[n]], 'ready': [list(v) for v in pose[n]],
                        'tail': list(rig.data.bones[n].tail_local)} for n in names}}
blade = bpy.data.objects['RuneSword_Blade']
local = [rest['WPN_root'].inverted() @ v.co for v in blade.data.vertices]
record['blade_cross_sections'] = {}
for height in (.16, .22, .28, .34):
    points = [p for p in local if abs(p.z-height) < .008]
    record['blade_cross_sections'][str(height)] = {
        'min': [min(p[i] for p in points) for i in range(3)],
        'max': [max(p[i] for p in points) for i in range(3)]}
(P / 'authoring_inputs.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
print('FIST_BRACE_INPUTS_READY', flush=True)
