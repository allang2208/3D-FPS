"""Read the installed 201 mesh binding and compressed poses; no asset writes."""
import json,unreal as u
from pathlib import Path
O=Path('D:/FPS3D/FPSGAME/SourceAssets/LMG20120260927/Skin07');R='/Game/Weapons/LMG201/Production20260927'
mesh=u.load_asset(R+'/SK_LMG201_Manny');Q=u.GeometryScript_MeshQueries;B=u.GeometryScript_BoneWeights
dm,outcome=u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
if outcome!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('201 surface extraction failed')
_,bones=B.get_all_bones_info(dm);bn={b.index:str(b.name) for b in bones}
def xyz(v):return [v.x,v.y,v.z]
def transform(t):return {'position':xyz(t.translation),'axes':[xyz(t.transform_location(v)-t.translation) for v in (u.Vector(1,0,0),u.Vector(0,1,0),u.Vector(0,0,1))]}
_,vs,_=Q.get_all_vertex_positions(dm,False);vertices=u.GeometryScript_List.convert_vector_list_to_array(vs)
_,ts,_=Q.get_all_triangle_indices(dm,False);triangles=u.GeometryScript_List.convert_triangle_list_to_array(ts)
slots=[str(s.material_slot_name) for s in mesh.materials];ids=[i for i,s in enumerate(slots) if s.startswith('M_LMG201_MannySkin_')]
faces=[]
for i,t in enumerate(triangles):
 mat,valid=u.GeometryScript_Materials.get_triangle_material_id(dm,i)
 if valid and mat in ids:faces.append([int(v) for v in xyz(t)])
vids=sorted({v for t in faces for v in t});remap={v:i for i,v in enumerate(vids)};weights=[]
for i in vids:
 _,ws,valid=B.get_vertex_bone_weights(dm,i)
 if not valid:raise RuntimeError('Missing skin weights')
 weights.append({bn[w.bone_index]:w.weight for w in ws if w.weight>0})
data={'asset':mesh.get_path_name(),'skeleton':mesh.skeleton.get_path_name(),'bones':{str(b.name):dict(transform(b.world_transform),parent=bn.get(b.parent_index)) for b in bones},'positions':[xyz(vertices[i]) for i in vids],'weights':weights,'triangles':[[remap[i] for i in f] for f in faces],'poses':{}}
names=[n for n in data['bones'] if n.endswith('_l') and n.startswith(('clavicle','upperarm','lowerarm','hand_','thumb_','index_','middle_','ring_','pinky_'))]+['WPN_root']
opts=u.AnimPoseEvaluationOptions();opts.evaluation_type=u.AnimDataEvalType.COMPRESSED;opts.optional_skeletal_mesh=mesh
for key,times in {'idle':[0.0],'aim':[0.0],'sprint_enter':[0.,.10,.20,.30],'sprint_loop':[0.,.15],'reload_empty':[0.,2.1,4.29]}.items():
 a=u.load_asset(R+'/Animations/A_LMG201_'+key)
 for t in times:
  p=u.AnimPoseExtensions.get_anim_pose_at_time(a,min(t,a.get_play_length()),opts)
  data['poses'][key+':'+str(t)]={n:transform(u.AnimPoseExtensions.get_bone_pose(p,n,u.AnimPoseSpaces.WORLD)) for n in names}
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world();data['game_running']=bool(world);data['live_components']=[]
if world:
 for actor in u.GameplayStatics.get_all_actors_of_class(world,u.Character):
  for c in actor.get_components_by_class(u.SkeletalMeshComponent):
   m=c.get_skeletal_mesh_asset()
   if m and '/Weapons/LMG201/' in m.get_path_name():
    entry={'component':c.get_name(),'mesh':m.get_path_name(),'visible':c.is_visible(),'local_bones':{n:transform(c.get_socket_transform(n,u.RelativeTransformSpace.RTS_COMPONENT)) for n in names}}
    inst=c.get_anim_instance();entry['anim_instance']=inst.get_class().get_name() if inst else None
    data['live_components'].append(entry)
(O/'installed_skin_after.json').write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
print('201_INSTALLED_SKIN_READ',len(vids),len(faces),'game_running',data['game_running'],'live_components',len(data['live_components']))
