import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;m=u.load_asset('/Game/Weapons/AKMIntegration/SovietFab/SK_AKM_MannyNative');a=u.load_asset('/Game/Weapons/AKMIntegration/SourceMatched/A_AKM_aim');opt=u.AnimPoseEvaluationOptions();opt.evaluation_type=u.AnimDataEvalType.RAW;opt.optional_skeletal_mesh=m;p=u.AnimPoseExtensions.get_anim_pose_at_time(a,0,opt)
r=u.AnimPoseExtensions.get_bone_pose(p,'WPN_root',u.AnimPoseSpaces.WORLD);out={}
for n in ['WPN_root','WPN_RearSight','WPN_FrontSight','WPN_SOCKET_Muzzle']:
 t=u.AnimPoseExtensions.get_bone_pose(p,n,u.AnimPoseSpaces.WORLD);v=r.inverse_transform_location(t.translation);out[n]={'world':str(t),'local':[v.x,v.y,v.z]}
(O/'ue_sights.json').write_text(json.dumps(out,indent=2));u.log('SIGHT_PROBE_PASS')
