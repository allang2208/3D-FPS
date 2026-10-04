"""Separate fused finger remnants from the abdomen and rebuild owner-local closures."""
import bpy,json,math
import numpy as np
from pathlib import Path
from mathutils import Vector,Quaternion
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/HangingBellM09Meshy20261003')
OUT=ROOT/'SkinDeathV13'
for d in ('Authoring','Exports','Records'):(OUT/d).mkdir(parents=True,exist_ok=True)
# Reuse the anatomical bone chains, not the old cross-part blending.
recipe=json.loads((ROOT/'RigV03/Authoring/rig_recipe_v03.json').read_text())
manifest=json.loads((ROOT/'Records/source_manifest.json').read_text())
namespace={'np':np,'bones':recipe['bones'],'B':len(recipe['bones']),
 'index':{b['name']:i for i,b in enumerate(recipe['bones'])},
 'chains':{k:{'points':np.array(v['points']),'names':v['names']} for k,v in recipe['chains'].items()},
 'S':manifest['scale_to_280cm'],'BOTTOM':manifest['source_min_y']}
text=(ROOT.parents[1]/'Tools/HangingBellM09/author_rig_weights_v03.py').read_text(encoding='utf8')
exec(compile(text[text.index('def src('):text.index('bones=[];')]+text[text.index('def empty('):text.index('weights={};stats=[];seam_reference={}')],'rig_functions','exec'),namespace)
bone_names=[b['name'] for b in namespace['bones']];index=namespace['index']
source_ids=np.load(ROOT/'RigV03/Work/rig_input.npz')
old_weights=np.load(ROOT/'RigV03/Authoring/skin_weights_v03.npz')
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'RigV03/Authoring/M09_Rigged_v03.blend'))
rig=bpy.data.objects['M09_Rig_V03'];scene=bpy.context.scene
parts={0:bpy.data.objects['M09_Body_RootBand'],8:bpy.data.objects['M09_SmallArm_L'],9:bpy.data.objects['M09_SmallArm_R']}
def smooth(t):
 t=np.clip(t,0,1);return t*t*(3-2*t)
def get_arrays(ob):
 me=ob.data;co=np.empty((len(me.vertices),3),np.float64);me.vertices.foreach_get('co',co.ravel())
 m=np.array(ob.matrix_world);co=co@m[:3,:3].T+m[:3,3]
 tri=np.empty((len(me.polygons),3),np.int32);me.loops.foreach_get('vertex_index',tri.ravel())
 uv=np.empty((len(me.loops),2),np.float32);me.uv_layers.active.data.foreach_get('uv',uv.ravel())
 sid=np.empty(len(me.polygons),np.int32);me.attributes['source_triangle_id'].data.foreach_get('value',sid)
 return co,tri,uv.reshape(-1,3,2),sid
arrays={p:get_arrays(o) for p,o in parts.items()}
co,tri,uv,sid=arrays[0]
bi=old_weights['p0_bones'];qw=old_weights['p0_weights']/1024.
side_weights=[]
for side in ('L','R'):
 selected=np.array([n.startswith('small_') and n.endswith('_'+side) or n.startswith('smallfinger_'+side+'_') for n in bone_names])
 side_weights.append((selected[bi]*qw).sum(1))
side_weights=np.array(side_weights).T
face_side=side_weights[tri].mean(1)
centres=co[tri].mean(1)
# Only distal hand/forearm contact tissue is freed. Shoulder roots remain attached.
transfer=(sid>=0)&(face_side.max(1)>.35)&(centres[:,2]<1.135)
owner=face_side.argmax(1)+8
report={'transferred_original_faces':{},'source':'RigV03 original visible triangles and UVs',
 'scope':'Body and small arms only; same rig, membranes, eyes, materials and other clips',
 'game_tested':False}

def weights_for(p,pid):
 if pid==0:
  w=namespace['body_weights'](p,include_small=False)
  # Keep just the biological shoulder junction; never attach abdomen to fingers.
  for side,sgn in [('L',1),('R',-1)]:
   blend=smooth((p[:,0]*sgn-.09)/.08)*smooth((p[:,2]-1.15)/.08)*(1-smooth((p[:,2]-1.28)/.07))
   blend*=smooth((-p[:,1]-.28)/.035)
   w*=1-blend[:,None];w[:,index['small_upperarm_'+side]]+=blend
  return w
 side='L' if pid==8 else 'R'
 w=namespace['small_weights'](p,side)[0]
 # A continuous shoulder blend, with no weights from the opposite hand.
 root=smooth((p[:,2]-1.155)/.095)
 anchor=namespace['body_weights'](p,include_small=False)
 w=w*(1-root[:,None])+anchor*root[:,None]
 return w

def close_mesh(pos,faces,tex,source_faces,source_vertices,pid):
 # Welded topology is used only to locate boundary loops; UVs remain per corner.
 p=np.array(pos);_,weld=np.unique(np.rint(p*1e6).astype(np.int64),axis=0,return_inverse=True)
 f=np.array(faces,np.int32);directed=np.concatenate([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]])
 we=weld[directed];_,first,count=np.unique(np.sort(we,axis=1),axis=0,return_index=True,return_counts=True)
 border=directed[first[count==1]];wb=weld[border];by_start={}
 for i,(a,b) in enumerate(wb):by_start.setdefault(int(a),[]).append(i)
 used=set();closed=0;cap_weights=[]
 vertex_uv=np.zeros((len(p),2),np.float64);vertex_uv[np.array(faces).ravel()]=np.asarray(tex).reshape(-1,2)
 for seed in range(len(border)):
  if seed in used:continue
  chain=[];j=seed;start=int(wb[seed,0]);done=False
  while j not in used:
   used.add(j);chain.append(int(border[j,0]));end=int(wb[j,1])
   if end==start:done=True;break
   options=[k for k in by_start.get(end,[]) if k not in used]
   if not options:break
   j=options[0]
  if not done or len(chain)<3:continue
  q=p[chain];c=q.mean(0);n=-np.cross(q-c,np.roll(q,-1,axis=0)-c).sum(0)
  if np.linalg.norm(n)<1e-12:continue
  n/=np.linalg.norm(n);depth=min(.002,np.linalg.norm(np.ptp(q,axis=0))*.025)
  # The cap follows only this surface's owner field; no body-to-finger fans.
  center=len(pos);pos.append((c-n*depth).tolist());source_vertices.append(-1)
  cap_weights.append((center,chain))
  center_uv=vertex_uv[chain].mean(0).tolist()
  for k,a in enumerate(chain):
   b=chain[(k+1)%len(chain)];faces.append([b,a,center]);tex.append([vertex_uv[b].tolist(),vertex_uv[a].tolist(),center_uv]);source_faces.append(-1)
  closed+=1
 return closed,cap_weights

for pid,ob in parts.items():
 p,f,t,s=arrays[pid];keep=s>=0
 if pid==0:keep&=~transfer
 f=f[keep];t=t[keep];s=s[keep]
 used,inv=np.unique(f,return_inverse=True)
 pos=p[used].tolist();faces=inv.reshape(-1,3).tolist();tex=t.tolist();srcfaces=s.tolist()
 srcverts=source_ids[f'p{pid}_source_ids'][used].tolist()
 if pid in (8,9):
  select=transfer&(owner==pid);add=tri[select];extra,local=np.unique(add,return_inverse=True)
  offset=len(pos);points=co[extra].copy()
  # Match the existing V02 arm separation offset at the transferred seam.
  ps=namespace['src'](points);s0=1 if pid==8 else -1;w=smooth((-ps[:,1]-.135)/.22)
  points[:,0]+=s0*.012*w*namespace['S'];points[:,1]-=(.025 if pid==8 else .008)*w*namespace['S']
  pos.extend(points.tolist());faces.extend((local.reshape(-1,3)+offset).tolist());tex.extend(uv[select].tolist());srcfaces.extend(sid[select].tolist())
  srcverts.extend(source_ids['p0_source_ids'][extra].tolist())
  report['transferred_original_faces'][ob.name]=int(select.sum())
 caps,cap_weights=close_mesh(pos,faces,tex,srcfaces,srcverts,pid)
 me=bpy.data.meshes.new(ob.data.name+'_V13');matrix=np.array(ob.matrix_world.inverted());points=np.array(pos)
 local=points@matrix[:3,:3].T+matrix[:3,3];me.from_pydata(local.tolist(),[],faces);me.update()
 layer=me.uv_layers.new(name='UVMap');layer.data.foreach_set('uv',np.asarray(tex,np.float32).ravel())
 for mat in ob.data.materials:me.materials.append(mat)
 for poly in me.polygons:poly.use_smooth=True;poly.material_index=1 if srcfaces[poly.index]<0 and len(me.materials)>1 else 0
 for name,domain,values in [('source_vertex_id','POINT',srcverts),('source_triangle_id','FACE',srcfaces)]:
  attr=me.attributes.new(name,'INT',domain);attr.data.foreach_set('value',np.asarray(values,np.int32))
 old=ob.data;ob.data=me
 for vg in list(ob.vertex_groups):ob.vertex_groups.remove(vg)
 weights=weights_for(points,pid)
 for center,chain in cap_weights:weights[center]=weights[chain].mean(0)
 top=np.argpartition(weights,-4,axis=1)[:,-4:];values=np.take_along_axis(weights,top,axis=1)
 values/=values.sum(1,keepdims=True);quant=np.rint(values*1024).astype(np.int32);quant[np.arange(len(points)),values.argmax(1)]+=1024-quant.sum(1)
 for bone in np.unique(top[quant>0]):
  group=ob.vertex_groups.new(name=bone_names[bone]);rows,cols=np.where((top==bone)&(quant>0));amounts=quant[rows,cols]
  for amount in np.unique(amounts):group.add(rows[amounts==amount].tolist(),float(amount)/1024.,'REPLACE')
 ob['rig_revision']='V13 separated contact tissue and owner-local closures'
 report[ob.name]={'vertices':len(pos),'triangles':len(faces),'closed_loops':caps}
 print('M09_REBUILT',ob.name,report[ob.name],flush=True)

# Export the corrected mesh on the unchanged skeleton. Keep the editable base pose.
scene.frame_set(1);rig.animation_data_clear()
for p in rig.pose.bones:
 for c in list(p.constraints):p.constraints.remove(c)
 p.rotation_mode='QUATERNION';p.location=(0,0,0);p.rotation_quaternion=(1,0,0,0);p.scale=(1,1,1)
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
for ob in bpy.data.objects:
 if ob.type=='MESH' and ob.parent==rig:ob.select_set(True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Authoring/M09_Rigged_V13.blend'),compress=True)
bpy.ops.export_scene.fbx(filepath=str(OUT/'Exports/M09_Rigged_V13.fbx'),use_selection=True,object_types={'ARMATURE','MESH'},
 apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',axis_forward='-Z',axis_up='Y',bake_anim=False,
 path_mode='AUTO',embed_textures=False,mesh_smooth_type='FACE',add_leaf_bones=False,use_armature_deform_only=True,
 armature_nodetype='NULL',use_mesh_modifiers=False)

# An authored release lead, with arms relaxed inside the physical joint range.
# Keep the existing 0.60s handoff and staggered left/right grip release.
rig.animation_data_create();action=bpy.data.actions.new('A_M09_Death_V13');rig.animation_data.action=action
scene.render.fps=60;scene.frame_start=1;scene.frame_end=61
def rot(name,axis,angle):
 p=rig.pose.bones[name];local=rig.data.bones[name].matrix_local.to_3x3().inverted()@Vector(axis)
 p.rotation_quaternion=Quaternion(local.normalized(),math.radians(angle))@p.rotation_quaternion
for frame in range(61):
 t=frame/60.
 for p in rig.pose.bones:p.location=(0,0,0);p.rotation_quaternion=(1,0,0,0);p.scale=(1,1,1)
 drop=float(smooth(t/.6));rot('spine_01',(1,0,0),6*drop);rot('eye_crown',(0,1,0),5*drop)
 for side,delay,sign in [('L',.18,1),('R',.34,-1)]:
  release=float(smooth((t-delay)/.26))
  rot('big_upperarm_'+side,(0,1,0),-sign*24*release)
  rot('big_forearm_'+side,(1,0,0),18*release)
  for digit in range(1,6):
   for joint in range(1,4):rot(f'hook_{side}_{digit:02d}_{joint:02d}',(1,0,0),-8*release)
  for layer in range(1,4):
   for joint,factor in enumerate((.44,.27,.18,.11),1):rot(f'membrane_{side}{layer}_{joint:02d}',(0,1,0),sign*6*drop*factor)
 for bone in rig.data.bones:
  if bone.use_deform:
   for channel in ('location','rotation_quaternion','scale'):rig.pose.bones[bone.name].keyframe_insert(channel,frame=frame+1,group=bone.name)
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True)
bpy.ops.export_scene.fbx(filepath=str(OUT/'Exports/A_M09_Death_V13.fbx'),use_selection=True,object_types={'ARMATURE'},
 apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',axis_forward='-Z',axis_up='Y',bake_anim=True,
 bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0,add_leaf_bones=False,use_armature_deform_only=True)
scene.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Authoring/M09_Death_V13.blend'),compress=True)
(OUT/'Records/authoring_saved.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('M09_SKIN_DEATH_V13_EXPORTED',flush=True)
