"""Read the retained model and accepted idle as inputs; never save the source."""
import bpy
import json
from pathlib import Path

P = Path(__file__).parent
source = P.parent/'BackDrawEquipV23/AzureRunesword_Manny_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(source))
s = bpy.context.scene
r = bpy.data.objects['SK_RuneSword_Rig']
action = bpy.data.actions['A_RuneSword_Equip']
r.animation_data.action, r.animation_data.action_slot = action, action.slots[0]
s.frame_set(round(1.20*s.render.fps/s.render.fps_base))
bpy.context.view_layer.update()
rest = {b.name: b.matrix_local.copy() for b in r.data.bones}
pose = {b.name: b.matrix.copy() for b in r.pose.bones}
def mat(m):
    return [list(row) for row in m]
meshes = []
for ob in s.objects:
    if ob.type == 'MESH' and any(m.type == 'ARMATURE' and m.object == r for m in ob.modifiers):
        meshes.append({'name': ob.name, 'vertices': len(ob.data.vertices),
                       'transform': mat(ob.matrix_world),
                       'bounds': [list(v) for v in ob.bound_box]})
out = {'source': str(source), 'rig': r.name, 'rig_transform': mat(r.matrix_world),
       'source_fps': s.render.fps/s.render.fps_base,
       'bones': {b.name: {'parent': b.parent.name if b.parent else None,
                         'rest': mat(rest[b.name]), 'idle': mat(pose[b.name]),
                         'head': list(b.head_local), 'tail': list(b.tail_local)} for b in r.data.bones},
       'meshes': meshes,
       'actions': [{'name': a.name, 'range': list(a.frame_range)} for a in bpy.data.actions]}
(P/'authoring_inputs.json').write_text(json.dumps(out, indent=2), encoding='utf-8')
print('AUTHORING_INPUTS_READY', len(rest), [m['name'] for m in meshes], flush=True)
