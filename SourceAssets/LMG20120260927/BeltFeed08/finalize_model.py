"""Open the visible cover aperture and export the authoring assembly."""
import bpy,bmesh,json,sys,math
import numpy as np
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(O/'LMG201_BeltFeed_Animated.blend'),use_scripts=False)
sc=bpy.context.scene;r=bpy.data.objects['SK_M4_Infima'];rr=r.data.bones['WPN_root'].matrix_local.copy()
ob=bpy.data.objects['LMG201_Receiver'];src=ob.data;coords=[rr.inverted()@v.co for v in src.vertices];ns=[n.vector.copy() for n in src.corner_normals]
def cut(poly,axis,sign,limit):
 ins=[];outs=[]
 for p,q in zip(poly,poly[1:]+poly[:1]):
  dp=p[axis]*sign-limit;dq=q[axis]*sign-limit;pi=dp<=0;qi=dq<=0
  (ins if pi else outs).append(p)
  if pi!=qi:
   v=p+(q-p)*(dp/(dp-dq));ins.append(v);outs.append(v)
 return ins,outs
polys=[]
for face in src.polygons:
 part=[np.array([*coords[src.loops[i].vertex_index],*src.uv_layers.active.data[i].uv,*ns[i]]) for i in face.loop_indices]
 for axis,sign,limit in [(0,1,.031),(0,-1,.0294),(1,-1,.223),(1,1,-.111),(2,-1,-.047)]:
  part,out=cut(part,axis,sign,limit)
  if len(out)>2:polys.append((out,face.material_index,face.use_smooth))
  if len(part)<3:break
vs=[];fs=[];tex=[];norm=[];mis=[];smooth=[];lookup={}
for poly,mi,sm in polys:
 clean=[]
 for p in poly:
  if not clean or np.linalg.norm(p[:3]-clean[-1][:3])>1e-8:clean.append(p)
 if len(clean)>2 and np.linalg.norm(clean[0][:3]-clean[-1][:3])<1e-8:clean.pop()
 if len(clean)<3:continue
 ids=[]
 for p in clean:
  key=tuple(round(float(x),7) for x in p[:3])
  if key not in lookup:lookup[key]=len(vs);vs.append(rr@Vector(p[:3]))
  ids.append(lookup[key])
 if len(set(ids))<3:continue
 fs.append(ids);tex.append([p[3:5] for p in clean]);norm.extend(Vector(p[5:8]).normalized() for p in clean);mis.append(mi);smooth.append(sm)
me=bpy.data.meshes.new('201_VisibleFeedAperture');me.from_pydata(vs,[],fs);me.update()
for m in src.materials:me.materials.append(m)
uv=me.uv_layers.new(name='UVMap')
for f,t,mi,sm in zip(me.polygons,tex,mis,smooth):
 f.material_index=mi;f.use_smooth=sm
 for li,v in zip(f.loop_indices,t):uv.data[li].uv=v
me.normals_split_custom_set(norm);ob.data=me;ob.vertex_groups.clear();ob.vertex_groups.new(name='WPN_root').add(list(range(len(vs))),1,'REPLACE')
bpy.ops.wm.save_as_mainfile(filepath=str(O/'LMG201_BeltFeed_Animated.blend'))
r.data.pose_position='REST';copies=[]
for ob in list(sc.objects):
 if ob.type=='MESH' and ob.parent==r and ob.name.startswith('LMG201_') and 'BareArms' not in ob.name:
  cp=ob.copy();cp.data=ob.data.copy();sc.collection.objects.link(cp);copies.append(cp)
bpy.ops.object.select_all(action='DESELECT')
for ob in copies:ob.hide_set(False);ob.select_set(True)
bpy.context.view_layer.objects.active=copies[0];bpy.ops.object.join();joined=bpy.context.object;joined.name='LMG201_BeltFeed_Surface'
bpy.ops.object.select_all(action='DESELECT');joined.select_set(True);r.select_set(True);bpy.context.view_layer.objects.active=r
bpy.ops.export_scene.fbx(filepath=str(O/'Exports/SK_LMG201_BeltFeed.fbx'),use_selection=True,object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE')
print('201_BELTFEED_APERTURE_EXPORTED',flush=True)
