import bpy,json
from pathlib import Path
from mathutils import Matrix
R=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(R.parent/'modern-zombie-v01-20260906/modern-zombie-v01.blend'))
a=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
a.animation_data.action=None
for tr in a.animation_data.nla_tracks:tr.mute=True
for b in a.pose.bones:b.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update()
report={'bones':{b.name:list(b.head_local) for b in a.data.bones},'meshes':{o.name:{'matrix': [list(r) for r in o.matrix_world], 'bounds':[[min(v.co[i] for v in o.data.vertices),max(v.co[i] for v in o.data.vertices)] for i in range(3)]} for o in bpy.context.scene.objects if o.type=='MESH'}}
(R/'rest.json').write_text(json.dumps(report,indent=2))
