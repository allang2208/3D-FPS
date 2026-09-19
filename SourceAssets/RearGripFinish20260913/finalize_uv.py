import bpy,json
from pathlib import Path
p=Path(r'D:\FPS3D\FPSGAME\SourceAssets\RearGripFinish20260913')
for k,i in json.loads((p/'authoring.json').read_text()).items():
 if i['family']=='QBZ191':continue
 f=Path(i['fbx']);bpy.ops.wm.open_mainfile(filepath=str(f.parent/'Editable.blend'));o=bpy.data.objects[i['mesh_name']]
 print('COATING_UVS',k,[u.name for u in o.data.uv_layers],flush=True)
 if len(o.data.uv_layers)>2:
  while len(o.data.uv_layers)>2:o.data.uv_layers.remove(o.data.uv_layers[1])
  bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
  bpy.ops.export_scene.fbx(filepath=str(f),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
  bpy.ops.wm.save_as_mainfile(filepath=str(f.parent/'Editable.blend'))
