import unreal as u,json,itertools,math
from pathlib import Path
O=Path(__file__).parent;data=json.loads((O/'pose_reference_cm.json').read_text());out={}
for key,reference in data.items():
 weapon,variant=key.split('/');prefix='/Game/Weapons/M4CantedErgonomic/A_M4_Canted_' if weapon=='m4' else '/Game/Weapons/AKMIntegration/SovietFab/GripErgonomic/'+variant+'/A_AKM_'+variant+'_';a=u.load_asset(prefix+'idle');u.AKMAnimationAuditLibrary.finish_animation_compression(a);opt=u.AnimPoseEvaluationOptions();opt.optional_skeletal_mesh=u.load_asset('/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416' if weapon=='m4' else '/Game/Weapons/AKMIntegration/SovietFab/Attachments/SK_AKM_MannyNative');result={}
 for retarget in [True,False]:
  opt.should_retarget=retarget
  for mode in [u.AnimDataEvalType.RAW,u.AnimDataEvalType.COMPRESSED]:
   opt.evaluation_type=mode;p=u.AnimPoseExtensions.get_anim_pose_at_time(a,0,opt);points={n:u.AnimPoseExtensions.get_bone_pose(p,n,u.AnimPoseSpaces.WORLD).translation for n in reference};errors={}
   for n,m in itertools.combinations(reference,2):errors[n+'-'+m]=abs(points[n].distance(points[m])-math.dist(reference[n],reference[m]))
   result[str(retarget)+str(mode)]={'maximum_pair_distance_error_cm':max(errors.values()),'worst':max(errors,key=errors.get),'wrist_to_index_error_cm':errors['hand_l-index_03_l']}
 out[key]=result
(O/'pose_reference_validation.json').write_text(json.dumps(out,indent=2));u.log('POSE_REFERENCE_READBACK')
