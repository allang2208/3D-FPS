import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;P='/Game/Weapons/AKMIntegration/SovietFab/GripErgonomic/angled';a=u.load_asset(P+'/A_AKM_angled_idle');u.AKMAnimationAuditLibrary.finish_animation_compression(a);opt=u.AnimPoseEvaluationOptions();opt.optional_skeletal_mesh=u.load_asset('/Game/Weapons/AKMIntegration/SovietFab/Attachments/SK_AKM_MannyNative');d={'properties':{k:str(a.get_editor_property(k)) for k in ['bone_compression_settings','retarget_source','retarget_source_asset','additive_anim_type','parent_asset']}}
for target in [True,False]:
 opt.should_retarget=target
 for mode in [u.AnimDataEvalType.SOURCE,u.AnimDataEvalType.RAW,u.AnimDataEvalType.COMPRESSED]:
  opt.evaluation_type=mode;p=u.AnimPoseExtensions.get_anim_pose_at_time(a,0,opt);d[str(target)+str(mode)]={n:str(u.AnimPoseExtensions.get_bone_pose(p,n,u.AnimPoseSpaces.LOCAL)) for n in ['index_metacarpal_l','index_01_l','index_02_l','ring_01_l']}
(O/'eval_modes.json').write_text(json.dumps(d,indent=2));u.log('EVAL_MODE_DIAG')
