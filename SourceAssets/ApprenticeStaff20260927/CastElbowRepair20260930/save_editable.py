"""Save the repaired casts on the existing V17 rig. No render or game launch."""
import json
from pathlib import Path
import bpy
from mathutils import Matrix, Vector

P = Path(__file__).resolve().parent
data = json.loads((P/'editable-takes.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'ChargeForwardV17/Staff_ChargeForward_V17.blend'))
bpy.context.preferences.filepaths.save_version = 0
rig = bpy.data.objects['Staff_ChargeForward_V17']
rig.name = 'Staff_CastElbow20260930'
scene = bpy.context.scene
scene.render.fps = data['fps']
mirror = Matrix.Diagonal((1, -1, 1))

def convert(value):
    m = Matrix(value)
    result = (mirror @ m.to_3x3() @ mirror).to_4x4()
    result.translation = mirror @ m.translation * .01
    return result

parents = dict(data['parent'], staff_grip='hand_r')
first = None
for take in data['takes']:
    action = bpy.data.actions.new(take['name'])
    action.use_fake_user = True
    action['source'] = 'CastElbowRepair20260930/full-pose.json'
    rig.animation_data.action = action
    previous = {}
    for frame in take['frames']:
        world = {n:convert(m) for n,m in frame['world'].items()}
        for bone in rig.pose.bones:
            n = bone.name
            if n not in world:
                continue
            parent = parents[n]
            relative = world[parent].inverted() @ world[n] if parent else world[n]
            rest = rig.data.bones[n].matrix_local
            if parent:
                rest = rig.data.bones[parent].matrix_local.inverted() @ rest
            bone.rotation_mode = 'QUATERNION'
            bone.matrix_basis = rest.inverted() @ relative
            if n in previous and bone.rotation_quaternion.dot(previous[n]) < 0:
                bone.rotation_quaternion.negate()
            previous[n] = bone.rotation_quaternion.copy()
            for field in ('location', 'rotation_quaternion', 'scale'):
                bone.keyframe_insert(field, frame=frame['frame'])
    if first is None:
        first = action
    print('SAVED_TAKE', take['name'], len(take['frames']), flush=True)
rig.animation_data.action = first
if len(first.slots):
    rig.animation_data.action_slot = first.slots[0]
scene.frame_start, scene.frame_end = 0, 114
scene.frame_set(0)
result = P/'Staff_CastElbow20260930.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(result))
(P/'editable-source.json').write_text(json.dumps(dict(file=str(result), takes=[t['name'] for t in data['takes']],
    fps=data['fps'], ue_import_required=False, rendered=False, runtime_tested=False), indent=2), encoding='utf-8')
print('STAFF_CAST_EDITABLE_SAVED', str(result), flush=True)
