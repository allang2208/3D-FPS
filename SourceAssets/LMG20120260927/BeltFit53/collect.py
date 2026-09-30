"""Read current feed geometry and exact reload samples; do not alter assets."""
import unreal as u,json,gzip,hashlib,collections
from pathlib import Path
O=Path(__file__).parent;P=O.parents[2]
BODY='/Game/Weapons/LMG201/Cover10/SK_LMG201_Cover10'
asset=u.load_asset(BODY)
G=u.GeometryScript_AssetUtils;Q=u.GeometryScript_MeshQueries;B=u.GeometryScript_BoneWeights
dm,status=G.copy_mesh_from_skeletal_mesh(asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
assert status==u.GeometryScriptOutcomePins.SUCCESS
_,bones=B.get_all_bones_info(dm)
def tr(t):return [*t.translation.to_tuple(),t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,*t.scale3d.to_tuple()]
def sha(path):return hashlib.sha256((P/'Content'/(path.removeprefix('/Game/')+'.uasset')).read_bytes()).hexdigest()
slots=[{'name':str(s.material_slot_name),'material':s.material_interface.get_path_name() if s.material_interface else None} for s in asset.materials]
out={'body':BODY,'sha256':sha(BODY),'slots':slots,'bones':[{'name':str(b.name),'index':b.index,'rest':tr(b.world_transform)} for b in bones]}
_,tl,_=Q.get_all_triangle_indices(dm,False);tris=u.GeometryScript_List.convert_triangle_list_to_array(tl)
selected=set();faces=[];counts=collections.Counter()
for ti,t in enumerate(tris):
 m,valid=u.GeometryScript_Materials.get_triangle_material_id(dm,ti)
 if not valid:continue
 n=slots[m]['name'];counts[n]+=1
 if not n.startswith('M_LMG201_Cloth33__'):continue
 faces.append([t.x,t.y,t.z,m]);selected.update([t.x,t.y,t.z])
vertices={}
for vi in sorted(selected):
 p,valid=Q.get_vertex_position(dm,vi);_,ws,valid=B.get_vertex_bone_weights(dm,vi)
 vertices[vi]={'p':list(p.to_tuple()),'w':[[w.bone_index,w.weight] for w in ws if w.weight>0]}
with gzip.open(O/'feed.json.gz','wt') as f:json.dump({'vertices':vertices,'triangles':faces},f)
out['counts']=dict(counts)
motion=json.loads((O.parent/'ClothReload44/motion.json').read_text())
out['clips']={}
for key,spec in motion['clips'].items():
 path=spec['destination'];a=u.load_asset(path);out['clips'][key]={'path':path,'sha256':sha(path),'revision':u.EditorAssetLibrary.get_metadata_tag(a,'201ReloadRevision')}
 if key not in ['base_reload','base_reload_empty']:continue
 samples={}
 for t in [0.,1.60,1.74,2.10,2.40,2.80,3.35,3.82,4.05,4.38,4.78,5.22,6.2]:
  pose=u.AnimPoseExtensions.get_anim_pose_at_time(a,t,u.AnimPoseEvaluationOptions(optional_skeletal_mesh=asset,evaluation_type=u.AnimDataEvalType.SOURCE))
  samples[str(t)]={str(b.name):tr(u.AnimPoseExtensions.get_bone_pose(pose,b.name,u.AnimPoseSpaces.WORLD)) for b in bones if str(b.name).startswith(('LMG201_','New_LMG201_')) or str(b.name) in ['WPN_root','hand_l','index_03_l','thumb_03_l']}
 out['clips'][key]['samples']=samples
idle=u.load_asset('/Game/Weapons/LMG201/BeltFeed08/Animations/A_LMG201_idle')
pose=u.AnimPoseExtensions.get_anim_pose_at_time(idle,0,u.AnimPoseEvaluationOptions(optional_skeletal_mesh=asset,evaluation_type=u.AnimDataEvalType.SOURCE))
out['idle']={str(b.name):tr(u.AnimPoseExtensions.get_bone_pose(pose,b.name,u.AnimPoseSpaces.WORLD)) for b in bones}
out['pie']=bool(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world())
(O/'source.json').write_text(json.dumps(out,indent=2))
print('BELT53_CAPTURED',out['sha256'],len(vertices),len(faces),'PIE',out['pie'],flush=True)
