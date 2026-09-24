"""Extract archived Gallop in world space, keeping the original rig and timing."""
import bpy,json
from pathlib import Path
OUT=Path('D:/FPS3D/FPSGAME/SourceAssets/InfectedDogMeshy20260924/GodotRunFitV2/Source')
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.render.fps=30
bpy.ops.import_scene.gltf(filepath=str(OUT/'wolf_quaternius.gltf'))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
action=next(a for a in bpy.data.actions if 'Gallop' in a.name and 'Jump' not in a.name)
rig.animation_data.action=action
if hasattr(rig.animation_data,'action_slot'): rig.animation_data.action_slot=action.slots[0]
def matrix(m): return [list(row) for row in m]
data={'action':action.name,'frames':list(action.frame_range),'rig_matrix':matrix(rig.matrix_world),
      'rest':{b.name:{'matrix':matrix(rig.matrix_world@b.matrix_local),'head':list(rig.matrix_world@b.head_local),'tail':list(rig.matrix_world@b.tail_local),'parent':b.parent.name if b.parent else None} for b in rig.data.bones},'samples':[]}
start,end=action.frame_range
for i in range(35):
    f=start+(end-start)*i/34
    bpy.context.scene.frame_set(int(f),subframe=f-int(f))
    data['samples'].append({b.name:{'matrix':matrix(rig.matrix_world@b.matrix),'head':list(rig.matrix_world@b.head),'tail':list(rig.matrix_world@b.tail)} for b in rig.pose.bones})
(OUT/'godot_gallop_samples.json').write_text(json.dumps(data,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Gallop_Source.blend'))
print('GODOT_GALLOP_EXTRACTED',action.name,start,end)
