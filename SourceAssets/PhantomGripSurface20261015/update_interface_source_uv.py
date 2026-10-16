import bpy,json,numpy as np
from pathlib import Path
O=Path(__file__).parent;C=json.loads((O/'production.json').read_text());review=json.loads((O/'saved_asset_review.json').read_text())
for key,result in review['assets'].items():
 if not result['collapsed_uv0']['interface']:continue
 row=C['assets'][key];bpy.ops.wm.open_mainfile(filepath=row['blend']);bpy.context.preferences.filepaths.save_version=0;ob=next(o for o in bpy.context.scene.objects if o.type=='MESH');me=ob.data;uv=me.uv_layers[0].data;fixed=0
 for f in me.polygons:
  if f.material_index==row['body_slot']:continue
  a,b,c=[uv[i].uv.copy() for i in f.loop_indices]
  if abs((b-a).cross(c-a))>=2e-14:continue
  p=[ob.matrix_world@me.vertices[i].co for i in f.vertices];n=(p[1]-p[0]).cross(p[2]-p[0])
  if n.length_squared<=4e-24:continue
  axis=max(range(3),key=lambda i:abs(n[i]));axes=[i for i in range(3) if i!=axis]
  for li,v in zip(f.loop_indices,p):uv[li].uv=(v[axes[0]]/.04,v[axes[1]]/.04)
  fixed+=1
 bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob;bpy.ops.export_scene.fbx(filepath=row['fbx'],use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=False);bpy.ops.wm.save_as_mainfile(filepath=row['blend']);row['repaired_native_uv_faces']=fixed;(O/'production.json').write_text(json.dumps(C,indent=2));print('INTERFACE_SOURCE_UV_UPDATED',key,fixed,flush=True)
