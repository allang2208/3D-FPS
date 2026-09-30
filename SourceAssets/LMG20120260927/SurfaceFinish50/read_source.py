import bpy,json,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).parent;d=json.loads((O/'Inputs/assets.json').read_text());slots=d['meshes']['/Game/Weapons/LMG201/Cover10/SK_LMG201_Cover10']['slots'];bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(O/'Inputs/Body.fbx'),use_anim=False);rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');root=rig.matrix_world@rig.data.bones['WPN_root'].matrix_local
out={}
for ob in bpy.data.objects:
 if ob.type!='MESH':continue
 me=ob.data;me.calc_loop_triangles();xf=root.inverted()@ob.matrix_world
 for i in [14,16,34,58,67,69]:
  faces=[t.vertices[:] for t in me.loop_triangles if t.material_index==i];ids=np.unique(np.array(faces));v=np.array([(xf@me.vertices[int(j)].co)[:] for j in ids]);weights={}
  for j in ids:
   for g in me.vertices[int(j)].groups:weights[ob.vertex_groups[g.group].name]=weights.get(ob.vertex_groups[g.group].name,0)+g.weight
  out[str(i)]={'slot':slots[i]['name'],'bounds':[v.min(0).tolist(),v.max(0).tolist()],'bones':weights}
  if i in [14,34,58]:
   out[str(i)]['z_sections']=[{'z':float(z),'low':np.quantile(v[abs(v[:,2]-z)<.003],.03,axis=0).tolist(),'high':np.quantile(v[abs(v[:,2]-z)<.003],.97,axis=0).tolist()} for z in np.linspace(v[:,2].min()+.004,v[:,2].max()-.004,12) if np.sum(abs(v[:,2]-z)<.003)>5]
(O/'Inputs/source_regions.json').write_text(json.dumps(out,indent=2));print(json.dumps(out),flush=True)
print('CDT_HELP',bpy.app.version_string,flush=True)
from mathutils.geometry import delaunay_2d_cdt
print(delaunay_2d_cdt.__doc__,flush=True)
