"""Mirror the direct UE UV repair into the editable FBX convention (Y reflection, V flip)."""
import bpy,json,numpy as np
from pathlib import Path
O=Path(__file__).parent;C=json.loads((O/'production.json').read_text())
for key,row in C['assets'].items():
 count=row.get('repaired_native_uv_faces',0)
 if not count:continue
 bpy.ops.wm.open_mainfile(filepath=row['blend']);bpy.context.preferences.filepaths.save_version=0;ob=next(o for o in bpy.context.scene.objects if o.type=='MESH');me=ob.data;uv=me.uv_layers[0].data;changed=[]
 for f in me.polygons:
  if f.material_index==row['body_slot']:continue
  p=np.asarray([tuple(ob.matrix_world@me.vertices[i].co) for i in f.vertices]);n=np.cross(p[1]-p[0],p[2]-p[0]);axes=[i for i in range(3) if i!=np.argmax(abs(n))];previous=p[:,axes]/.04;current=np.asarray([tuple(uv[i].uv) for i in f.loop_indices])
  if np.max(abs(current-previous))>1e-5:continue
  q=p*np.array([1,-1,1]);result=q[:,axes]/.04;result[:,1]=1-result[:,1]
  changed.append((f.index,result))
 if len(changed)!=count:raise RuntimeError('Source projection face count changed '+key+' '+str((len(changed),count)))
 for fi,values in changed:
  for li,value in zip(me.polygons[fi].loop_indices,values):uv[li].uv=value
 bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob;bpy.ops.export_scene.fbx(filepath=row['fbx'],use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=False);bpy.ops.wm.save_as_mainfile(filepath=row['blend']);print('SOURCE_UV_CONVENTION_ALIGNED',key,count,flush=True)
