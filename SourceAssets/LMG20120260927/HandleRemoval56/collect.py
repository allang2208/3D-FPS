"""Capture only the live asset state and native geometry needed for this edit."""
import unreal as u,json,gzip,hashlib
from pathlib import Path
O=Path(__file__).parent;P=O.parents[2];BODY='/Game/Weapons/LMG201/Cover10/SK_LMG201_Cover10'
a=u.load_asset(BODY);Q=u.GeometryScript_MeshQueries;B=u.GeometryScript_BoneWeights
dm,status=u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(a,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD());assert status==u.GeometryScriptOutcomePins.SUCCESS
slots=[{'name':str(s.material_slot_name),'material':s.material_interface.get_path_name() if s.material_interface else None} for s in a.materials]
_,bl=B.get_all_bones_info(dm)
def tr(t):return [*t.translation.to_tuple(),t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,*t.scale3d.to_tuple()]
idle=u.load_asset('/Game/Weapons/LMG201/BeltFeed08/Animations/A_LMG201_idle');pose=u.AnimPoseExtensions.get_anim_pose_at_time(idle,0,u.AnimPoseEvaluationOptions(optional_skeletal_mesh=a,evaluation_type=u.AnimDataEvalType.SOURCE))
s={'body':BODY,'sha256':hashlib.sha256((P/'Content/Weapons/LMG201/Cover10/SK_LMG201_Cover10.uasset').read_bytes()).hexdigest(),'slots':slots,'bones':[{'name':str(b.name),'index':b.index,'rest':tr(b.world_transform)} for b in bl],'idle':{str(b.name):tr(u.AnimPoseExtensions.get_bone_pose(pose,b.name,u.AnimPoseSpaces.WORLD)) for b in bl},'pie':bool(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()),'dirty':[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()]}
_,tl,_=Q.get_all_triangle_indices(dm,False);tri=u.GeometryScript_List.convert_triangle_list_to_array(tl);ts=[];ids=set()
for i,t in enumerate(tri):
 mid,valid=u.GeometryScript_Materials.get_triangle_material_id(dm,i)
 if not valid or slots[mid]['name'] not in ['M_LMG201_R30_Interior','M_LMG201_H39_Receiver','M_LMG201_H39_Handguard','M_LMG201_H54_CarryHandle_Polymer','M_LMG201_H54_CarryHandle_Coat']:continue
 ts.append([i,t.x,t.y,t.z,mid]);ids.update([t.x,t.y,t.z])
verts={}
for i in ids:
 p,valid=Q.get_vertex_position(dm,i);_,w,valid=B.get_vertex_bone_weights(dm,i)
 verts[i]={'p':list(p.to_tuple()),'w':[[b.bone_index,b.weight] for b in w if b.weight>0]}
with gzip.open(O/'native.json.gz','wt') as f:json.dump({'vertices':verts,'triangles':ts},f)
(O/'source.json').write_text(json.dumps(s,indent=2));print('H56_SOURCE',s['sha256'],'PIE',s['pie'],'dirty_body',BODY in s['dirty'],len(ts),'faces')
