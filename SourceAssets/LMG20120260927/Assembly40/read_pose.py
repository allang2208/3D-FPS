import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;mesh=u.load_asset('/Game/Weapons/LMG201/Cover10/SK_LMG201_Cover10')
names=['WPN_root','WPN_SOCKET_Magazine','WPN_Trigger','WPN_ChargingHandle','WPN_BoltCatch','LMG201_Cover']
def tr(t):return {'p':list(t.translation.to_tuple()),'q':[t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w],'s':list(t.scale3d.to_tuple())}
dm,status=u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD());_,rows=u.GeometryScript_BoneWeights.get_all_bones_info(dm);bones={str(b.name):b.world_transform for b in rows};root=bones['WPN_root']
out={'reference':{n:tr(u.MathLibrary.make_relative_transform(bones[n],root)) for n in names},'clips':{}}
for key in ['idle','reload']:
 path='/Game/Weapons/LMG201/'+('BeltFeed08/Animations/A_LMG201_idle' if key=='idle' else 'Magazine24/Animations/base/A_LMG201_base_reload')
 clip=u.load_asset(path);opts=u.AnimPoseEvaluationOptions(optional_skeletal_mesh=mesh,evaluation_type=u.AnimDataEvalType.SOURCE);pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,0,opts);root=u.AnimPoseExtensions.get_bone_pose(pose,'WPN_root',u.AnimPoseSpaces.WORLD)
 out['clips'][key]={'asset':path,'bones':{n:tr(u.MathLibrary.make_relative_transform(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD),root)) for n in names}}
(O/'pose_inputs.json').write_text(json.dumps(out,indent=2));print('A40_AUTHORING_POSES',json.dumps(out),flush=True)
