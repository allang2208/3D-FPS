"""Continue the user's requested detail check on saved FBX, using source idle poses."""
import bpy,json,math,numpy as np,hashlib
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion
O=Path(__file__).parent;F=Matrix.Diagonal((1,-1,1,1));poses=json.loads((O/'pose_inputs.json').read_text());report={'game_tested':False,'view_pose':'existing idle source frame 0','saved_assets':{}}
for path,row in json.loads((O/'delivery.json').read_text())['saved'].items():
 report['saved_assets'][path]=hashlib.sha256((O.parents[2]/'Content'/(path.removeprefix('/Game/')+'.uasset')).read_bytes()).hexdigest()==row['sha256']
def pm(t):
 q=t['q'];return F@Matrix.LocRotScale(Vector(t['p']),Quaternion((q[3],q[0],q[1],q[2])),Vector(t['s']))@F
deltas={n:pm(poses['clips']['idle']['bones'][n])@pm(t).inverted() for n,t in poses['reference'].items()}
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(O/'Exports/After_Body.fbx'),use_anim=False);old=list(bpy.data.objects);rig=next(o for o in old if o.type=='ARMATURE');root=rig.matrix_world@rig.data.bones['WPN_root'].matrix_local
bindings=json.loads((O/'bindings.json').read_text());slots=list(next(v for k,v in bindings.items() if 'Cover10' in k))
for ob in old:
 if ob.type!='MESH':continue
 me=ob.data;me.calc_loop_triangles()
 if len(me.materials)!=len(slots):raise RuntimeError('FBX slot order changed '+str((len(me.materials),len(slots))))
 ts=[t for t in me.loop_triangles if not slots[t.material_index].startswith(('M_LMG201_MannySkin_','M_LMG201_Feed__','M_LMG201_Cloth33__'))]
 ids=np.array([t.vertices[:] for t in ts]);vi,remap=np.unique(ids,return_inverse=True);xf=root.inverted()@ob.matrix_world;v=[];nxf={};bone_vertices={}
 for i in vi:
  vertex=me.vertices[int(i)];bone=ob.vertex_groups[max(vertex.groups,key=lambda g:g.weight).group].name if vertex.groups else 'WPN_root';matrix=deltas.get(bone,Matrix.Identity(4))@xf;point=matrix@vertex.co;v.append(point[:]);nxf[int(i)]=matrix.to_3x3().inverted().transposed();bone_vertices.setdefault(bone,[]).append(point[:])
 nm=bpy.data.meshes.new('SavedCurrent201Visible');nm.from_pydata(v,[],remap.reshape(-1,3).tolist());nm.update();normal=[]
 for p,t in zip(nm.polygons,ts):
  p.use_smooth=True
  for li in t.loops:normal.append((nxf[me.loops[li].vertex_index]@me.corner_normals[li].vector).normalized())
 nm.normals_split_custom_set(normal);visible=bpy.data.objects.new('SavedCurrent201Visible',nm);bpy.context.scene.collection.objects.link(visible)
 for bone in ['WPN_SOCKET_Magazine','WPN_Trigger']:
  values=np.array(bone_vertices.get(bone,[]));report[bone]={'vertices':len(values),'idle_bounds_m':[values.min(0).tolist(),values.max(0).tolist()]}
 report['visible_triangles']=len(ts)
for ob in old:bpy.data.objects.remove(ob,do_unlink=True)
old=set(bpy.data.objects);bpy.ops.import_scene.fbx(filepath=str(O/'Exports/After_RearSight.fbx'),use_anim=False);rear=next(o for o in set(bpy.data.objects)-old if o.type=='MESH');rear.location+=Vector((.0008,.04252,.0855));rear.data.calc_loop_triangles();v=np.array([(rear.matrix_world@p.co)[:] for p in rear.data.vertices]);f=np.array([t.vertices[:] for t in rear.data.loop_triangles]);w,ix=np.unique(np.round(v,6),axis=0,return_inverse=True);f=ix[f];edges=np.sort(np.concatenate([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]]),axis=1);ed,cnt=np.unique(edges,axis=0,return_counts=True)
report['rear_sight']={'triangles':len(f),'open_edges':int((cnt==1).sum()),'near_zero_area':int((np.linalg.norm(np.cross(w[f[:,1]]-w[f[:,0]],w[f[:,2]]-w[f[:,0]]),axis=1)<1e-12).sum())}
(O/'saved_details.json').write_text(json.dumps(report,indent=2));print('A40_SAVED_DETAILS',json.dumps(report),flush=True)
scene_part=(O/'preview.py').read_text().split('scene=bpy.context.scene;',1)[1]
exec(compile('scene=bpy.context.scene;'+scene_part.replace('_authored.png','_saved.png'),str(O/'read_saved.py'),'exec'),globals())
