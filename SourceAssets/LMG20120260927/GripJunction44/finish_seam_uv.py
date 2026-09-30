"""Continue original UVs at the shared ring, then fade to valid neck unwrap."""
import bpy,json,os
from pathlib import Path
from mathutils.kdtree import KDTree
O=Path(os.environ.get('J44_OUTPUT',str(Path(__file__).parent)));model=json.loads((O/'model.json').read_text());bpy.ops.wm.open_mainfile(filepath=str(O/'LMG201_GripJunction44.blend'),use_scripts=False);bpy.context.preferences.filepaths.save_version=0
def select(obs):
 bpy.ops.object.select_all(action='DESELECT')
 for o in obs:o.hide_set(False);o.select_set(True)
 bpy.context.view_layer.objects.active=obs[-1]
for key,row in model['grips'].items():
 ob=bpy.data.objects['RearGrip_'+key+'_J44'];me=ob.data;mi=row['mask_uv_channel'];mask=me.uv_layers[mi];fresh=me.attributes['J44NewFace'];oldloops={};base=set()
 for p in me.polygons:
  if fresh.data[p.index].value==0:
   for li in p.loop_indices:oldloops.setdefault(me.loops[li].vertex_index,[]).append(li)
  else:
   for li in p.loop_indices:
    if abs(mask.data[li].uv.x)<1e-7:base.add(me.loops[li].vertex_index)
 base=[v for v in base if v in oldloops];tree=KDTree(len(base))
 for vi in base:tree.insert(me.vertices[vi].co,vi)
 tree.balance()
 for p in me.polygons:
  if fresh.data[p.index].value==0:continue
  for li in p.loop_indices:
   t=mask.data[li].uv.x
   if t>=.16:continue
   vi=me.loops[li].vertex_index;bi=vi if vi in oldloops else tree.find(me.vertices[vi].co)[1];source=max(oldloops[bi],key=lambda j:me.corner_normals[j].vector.dot(p.normal));a=min(1.,max(0.,t/.12));a=a*a*(3-2*a)
   for channel in range(mi):
    uv=me.uv_layers[channel];target=uv.data[li].uv.copy();origin=uv.data[source].uv.copy();uv.data[li].uv=origin.lerp(target,a) if channel==0 else origin
 row['source_uv_continued_at_shared_ring']=True
 if key=='factory':
  select([ob,bpy.data.objects['SK_M4_Infima']]);bpy.ops.export_scene.fbx(filepath=model['body_fbx'],use_selection=True,object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',colors_type='LINEAR')
 else:
  select([ob]);bpy.ops.export_scene.fbx(filepath=model['grip_fbx'][key],use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE');ob.hide_set(True)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'LMG201_GripJunction44.blend'));(O/'model.json').write_text(json.dumps(model,indent=2));print('J44_SEAM_UV_AUTHORED',flush=True)
