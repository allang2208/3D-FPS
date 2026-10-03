"""Build M09 authored parts from retained source triangles; no renders or acceptance tests."""
import bpy, json, math
from pathlib import Path
import numpy as np
from mathutils import Vector

ROOT=Path("D:/FPS3D/FPSGAME/SourceAssets/HangingBellM09Meshy20261003")
a=np.load(ROOT/"Authoring/source_arrays.npz")
r=np.load(ROOT/"Authoring/semantic_parts_v02.npz")
recipe=json.loads((ROOT/"Records/parts_recipe_v02.json").read_text(encoding="utf8"))
manifest=json.loads((ROOT/"Records/source_manifest.json").read_text(encoding="utf8"))
p=a["positions"].astype(float);f=a["faces"].astype(np.int32);uv=a["uv"].astype(float);normal=a["normals"].astype(float);weld=a["weld_ids"]
labels=r["face_labels"];names=recipe["part_names"];scale=manifest["scale_to_280cm"];bottom=manifest["source_min_y"]
arm_ids={v:k for k,v in recipe["small_arm_ids"].items()}
digit_ids=recipe["digit_ids"];eye_ids=recipe["eye_ids"]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=manifest["archived_source"])
imported=[o for o in bpy.context.scene.objects if o.type=="MESH"]
base=imported[0].data.materials[0]
materials={}
for key in ["Body","Membrane","Eye","Closure"]:
 mat=base.copy();mat.name="M09_"+key+"_SourcePBR";materials[key]=mat
for obj in list(bpy.context.scene.objects):bpy.data.objects.remove(obj,do_unlink=True)
scene=bpy.context.scene
scene.unit_settings.system="METRIC";scene.unit_settings.scale_length=1.0
parts=bpy.data.collections.new("M09_Adjusted_Source_Parts_V02");scene.collection.children.link(parts)
guides=bpy.data.collections.new("M09_Editable_Anatomy_Guides");scene.collection.children.link(guides)
guides.hide_render=True;guides.hide_viewport=True
def smooth(t):
 t=np.clip(t,0,1);return t*t*(3-2*t)
def to_blender(points):
 q=np.asarray(points).copy()
 return np.stack([q[...,0]*scale,-q[...,2]*scale,(q[...,1]-bottom)*scale],axis=-1)
def normals_blender(nn):
 return np.stack([nn[...,0],-nn[...,2],nn[...,1]],axis=-1)
def guide(name,point,kind="PLAIN_AXES",size=.018):
 ob=bpy.data.objects.new(name,None);guides.objects.link(ob);ob.location=to_blender(np.asarray(point));ob.empty_display_type=kind;ob.empty_display_size=size
 ob["purpose"]="Anatomical authoring marker, not a bound bone";return ob
def attr(mesh,name,type,domain,values,field="value"):
 at=mesh.attributes.new(name=name,type=type,domain=domain)
 at.data.foreach_set(field,np.asarray(values).ravel())
def vg(ob,name,values):
 group=ob.vertex_groups.new(name=name)
 # Quantized authoring groups reduce per-vertex Python calls; these are editable masks, not final skinning.
 values=np.clip(values,0,1)
 bins=np.rint(values*64).astype(int)
 for b in np.unique(bins):
  if b>0:group.add(np.flatnonzero(bins==b).tolist(),float(b)/64,"REPLACE")
 return group
def boundary_loops(ids,lf):
 w=weld[ids]
 wf=w[lf]
 de=np.concatenate([wf[:,[0,1]],wf[:,[1,2]],wf[:,[2,0]]])
 le=np.concatenate([lf[:,[0,1]],lf[:,[1,2]],lf[:,[2,0]]])
 se=np.sort(de,axis=1)
 _,first,counts=np.unique(se,axis=0,return_index=True,return_counts=True)
 be=first[counts==1]; pairs=de[be];local=le[be]
 adj={}
 for j,(aa,bb) in enumerate(pairs):adj.setdefault(int(aa),[]).append(j)
 used=np.zeros(len(pairs),bool);loops=[]
 for seed in range(len(pairs)):
  if used[seed]:continue
  start=int(pairs[seed,0]);cur=seed;loop=[];closed=False
  while not used[cur]:
   used[cur]=True;loop.append(int(local[cur,0]));nxt=int(pairs[cur,1])
   if nxt==start:closed=True;break
   options=adj.get(nxt,[])
   left=[k for k in options if not used[k]]
   if not left:break
   cur=left[0]
  if len(loop)>=3 and closed:loops.append(loop)
 return loops,int(len(be))
receipt=[];objects=[]
for label,name in enumerate(names):
 faceids=np.flatnonzero(labels==label)
 if not len(faceids):continue
 ids,inv=np.unique(f[faceids],return_inverse=True);lf=inv.reshape(-1,3)
 pp=p[ids].copy();nn=normal[ids].copy();uu=uv[ids].copy()
 ww=weld[ids];rootmask=np.zeros(len(ids))
 changes=np.zeros_like(pp)
 if 1<=label<=6:
  changes+=r["membrane_delta"][label,ww]
  rootmask=r["root_weight"][label,ww].copy()
 elif label in arm_ids:
  side=arm_ids[label];s=1 if side=="L" else -1
  w=smooth((-pp[:,1]-.135)/.22)
  changes[:,0]=s*.012*w
  changes[:,2]=(.025 if side=="L" else .008)*w
  rootmask=1-smooth((-pp[:,1]-.135)/.055)
 elif label in digit_ids:
  side="L" if "_L_" in name else "R";s=1 if side=="L" else -1
  k=int(name[-2:])-1;w=smooth((pp[:,1]-.805)/.08)
  changes[:,0]=s*(k-2)*.0028*w
  changes[:,2]=(.0015 if k%2 else -.0015)*w
  rootmask=1-smooth((pp[:,1]-.805)/.028)
 elif label==recipe["crown_id"]:
  rootmask=1-smooth((-.475-pp[:,1])/.035)
 pp+=changes
 # Retain original shading at unchanged source surfaces; adjusted patches receive geometric normals.
 moved=np.linalg.norm(changes,axis=1)>1e-8
 if moved.any():
  tri=pp[lf];fn=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);vn=np.zeros_like(pp)
  for corner in range(3):np.add.at(vn,lf[:,corner],fn)
  vn/=np.maximum(np.linalg.norm(vn,axis=1,keepdims=True),1e-12)
  nn[moved]=vn[moved]
 loops,boundary_edges=boundary_loops(ids,lf)
 pos=pp.tolist();norms=nn.tolist();tex=uu.tolist();triangles=lf.tolist();srcverts=ids.tolist();srcfaces=faceids.tolist();root_values=rootmask.tolist()
 # Closures extend inward from new cut loops, keeping original visible triangles and UVs intact.
 cap_start=len(pos);closure_faces=0
 for loop in loops:
  q=pp[loop];uvq=uu[loop];c=q.mean(0)
  area=np.sum(np.cross(q-c,np.roll(q,-1,axis=0)-c),axis=0)
  normlen=np.linalg.norm(area)
  if normlen<1e-12:continue
  outward=-area/normlen
  diameter=float(np.linalg.norm(np.ptp(q,axis=0)))
  if label in eye_ids:
   depth=min(.027,diameter*.30);steps=[(.87,.38),(.55,.78),(.20,.98)]
  else:
   depth=min(.003,diameter*.025);steps=[(.70,.65)]
  previous=list(loop)
  for shrink,deep in steps:
   ring=c+(q-c)*shrink-outward*depth*deep
   nextids=list(range(len(pos),len(pos)+len(loop)))
   pos.extend(ring.tolist());norms.extend(np.tile(outward,(len(loop),1)).tolist());tex.extend((uvq*shrink+uvq.mean(0)*(1-shrink)).tolist());srcverts.extend([-1]*len(loop));root_values.extend((rootmask[loop]*shrink+rootmask[loop].mean()*(1-shrink)).tolist())
   for k in range(len(loop)):
    j=(k+1)%len(loop)
    triangles.extend([[previous[j],previous[k],nextids[k]],[previous[j],nextids[k],nextids[j]]]);srcfaces.extend([-1,-1]);closure_faces+=2
   previous=nextids
  center_id=len(pos);pos.append((c-outward*depth).tolist());norms.append(outward.tolist());tex.append(uvq.mean(0).tolist());srcverts.append(-1);root_values.append(float(rootmask[loop].mean()))
  for k in range(len(loop)):
   j=(k+1)%len(loop);triangles.append([previous[j],previous[k],center_id]);srcfaces.append(-1);closure_faces+=1
 # Origins correspond to actual roots / intended articulation.
 if 1<=label<=6:
  rootids=np.flatnonzero(rootmask>.96);rootpoints=pp[rootids]
  if len(rootpoints):
   top=rootpoints[rootpoints[:,1]>=np.quantile(rootpoints[:,1],.8)];pivot=top.mean(0)
  else:pivot=pp[np.argmax(pp[:,1])]
 elif label in arm_ids:pivot=np.array(recipe["small_arm_guides_source"][arm_ids[label]][0])
 elif label in digit_ids:pivot=np.array(recipe["digit_guides_source"][str(label)][0])
 elif label==recipe["crown_id"]:pivot=np.array([0,-.475,.13])
 elif label in eye_ids:pivot=pp.mean(0)-np.array([0,0,.015])
 else:pivot=np.array([0,.682,.145])
 pivot_bl=to_blender(pivot)
 vertices=to_blender(np.array(pos))-pivot_bl
 tris=np.array(triangles,dtype=np.int32);tex=np.array(tex);cn=normals_blender(np.array(norms))
 mesh=bpy.data.meshes.new(name+"_Mesh")
 mesh.vertices.add(len(vertices));mesh.vertices.foreach_set("co",vertices.ravel())
 mesh.loops.add(len(tris)*3);mesh.loops.foreach_set("vertex_index",tris.ravel())
 mesh.polygons.add(len(tris));mesh.polygons.foreach_set("loop_start",np.arange(len(tris),dtype=np.int32)*3);mesh.polygons.foreach_set("loop_total",np.full(len(tris),3,np.int32))
 mesh.polygons.foreach_set("use_smooth",np.ones(len(tris),bool))
 mesh.update(calc_edges=True)
 uvl=mesh.uv_layers.new(name="UVMap");loopuv=tex[tris.ravel()].copy();loopuv[:,1]=1-loopuv[:,1];uvl.data.foreach_set("uv",loopuv.ravel())
 mesh.normals_split_custom_set_from_vertices(cn.tolist())
 source_v=np.asarray(srcverts,dtype=np.int32);source_f=np.asarray(srcfaces,dtype=np.int32)
 attr(mesh,"source_vertex_id","INT","POINT",source_v);attr(mesh,"source_triangle_id","INT","FACE",source_f)
 attr(mesh,"authored_closure","BOOLEAN","FACE",source_f<0)
 ob=bpy.data.objects.new(name,mesh);parts.objects.link(ob);ob.location=pivot_bl
 category="Membrane" if 1<=label<=6 else "Eye" if label in eye_ids else "Body"
 mesh.materials.append(materials[category]);mesh.materials.append(materials["Closure"])
 slots=np.zeros(len(tris),np.int32);slots[source_f<0]=1;mesh.polygons.foreach_set("material_index",slots)
 ob["part_id"]=int(label);ob["source_file"]=manifest["archived_source"];ob["source_faces_retained"]=int(len(faceids));ob["closure_faces_authored"]=int(closure_faces)
 ob["separation_method"]="Source-surface semantic partition with authored inward closures"
 ob["pivot_source"]=pivot.tolist();ob["not_animation_ready"]=True
 rw=np.asarray(root_values)
 if rootmask.any():vg(ob,"M09_FixedAttachment",rw)
 cv=np.zeros(len(pos));cv[cap_start:]=1;vg(ob,"M09_AuthoredClosure",cv)
 if 1<=label<=6:
  progress=smooth((pivot[1]-np.array(pos)[:,1])/.8)
  vg(ob,"M09_Open_Mid",4*progress*(1-progress)*(1-rw))
  vg(ob,"M09_Open_Tip",progress**2*(1-rw))
  guide(name+"_ROOT",pivot)
  free=pp[np.argsort(pp[:,1])[:max(5,len(pp)//50)]].mean(0)
  guide(name+"_MID",pivot*.5+free*.5);guide(name+"_TIP",free)
 elif label in arm_ids:
  for k,point in enumerate(recipe["small_arm_guides_source"][arm_ids[label]]):guide(name+"_Guide_"+str(k),point)
 elif label in digit_ids:
  for k,point in enumerate(recipe["digit_guides_source"][str(label)]):guide(name+"_Joint_"+str(k),point,size=.007)
 elif label in eye_ids:guide(name+"_Pivot",pivot,"SPHERE",.008)
 # An unapplied copy is not required: source IDs plus archived GLB retain every source triangle.
 objects.append(ob)
 receipt.append({"name":name,"source_faces":int(len(faceids)),"closure_faces":int(closure_faces),"vertices":len(pos),"boundary_loops_authored":len(loops),"source_boundary_edges":boundary_edges,"moved_source_vertices":int(moved.sum()),"maximum_authored_offset_cm":float(np.linalg.norm(changes,axis=1).max()*scale*100),"pivot_source":pivot.tolist()})
 print("M09_PART_SAVED_IN_SCENE",name,len(faceids),closure_faces,flush=True)
# Embed a readable production note in the Blender source.
note=bpy.data.texts.new("READ_ME_M09")
note.write("M09 source-preserving separated authoring model.\nSource GLB is archived under Source/.\n25 named parts; source triangle/vertex attributes distinguish retained geometry from closure patches.\nUnits: metres, authored overall height 2.8 m. Front: Blender -Y.\nRoot and closure groups are editing masks, not final skinning. Anatomy markers are not an armature.\nCuffs remain on original body to preserve wrist continuity. Five anterior eye caps are separate; eyelid animation and smaller eyes remain unrigged.\nNo UE import, new renders, acceptance checks or deformation tests were performed.\n")
scene["m09_status"]="Separated and locally adjusted authoring model; not rigged; not visually or runtime tested"
scene["source_manifest"]=str(ROOT/"Records/source_manifest.json")
scene["original_source_triangle_count"]=int(len(f))
# Pack imported images so the editable file is self-contained.
bpy.ops.file.pack_all()
for ob in bpy.context.selected_objects:ob.select_set(False)
for ob in objects:ob.select_set(True)
bpy.context.view_layer.objects.active=objects[0]
# Viewport opens in a practical material view; this does not render or open Blender UI.
for screen in bpy.data.screens:
 for area in screen.areas:
  if area.type=="VIEW_3D":area.spaces.active.shading.type="MATERIAL";area.spaces.active.clip_end=100
blend=ROOT/"Authoring/M09_Separated_Adjusted_v02.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(blend),compress=True)
glb=ROOT/"Exports/M09_Separated_Adjusted_v02.glb"
bpy.ops.export_scene.gltf(filepath=str(glb),export_format="GLB",use_selection=True,export_yup=True,export_normals=True,export_tangents=True,export_animations=False,export_extras=True)
fbx=ROOT/"Exports/M09_Separated_Adjusted_v02.fbx"
bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={"MESH"},apply_unit_scale=True,apply_scale_options="FBX_SCALE_UNITS",axis_forward="-Z",axis_up="Y",bake_anim=False,path_mode="COPY",embed_textures=True,mesh_smooth_type="FACE")
delivery={"version":"M09_SourceSeparation_V02","blend":str(blend),"glb":str(glb),"fbx":str(fbx),"parts":receipt,"part_count":len(objects),"source_triangle_count":int(len(f)),"retained_source_triangles":int(sum(x["source_faces"] for x in receipt)),"authored_closure_faces":int(sum(x["closure_faces"] for x in receipt)),"original_uv_retained_on_source_faces":True,"new_patch_uv":"interpolated from each retained boundary; authored interior surfaces","original_mesh_replaced":False,"source_body_rebuilt":False,"armature_created":False,"ue_imported":False,"rendered":False,"tested":False,"visually_accepted":False}
(ROOT/"Records/delivery_v02.json").write_text(json.dumps(delivery,indent=2),encoding="utf8")
print("M09_AUTHORING_AND_EXPORT_COMPLETE",json.dumps({"parts":len(objects),"retained_source_triangles":delivery["retained_source_triangles"],"closure_faces":delivery["authored_closure_faces"],"blend":str(blend),"glb":str(glb)}),flush=True)
