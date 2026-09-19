import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;P='/Game/Weapons/AKMIntegration/SovietFab';report={};opt=u.AnimPoseEvaluationOptions();opt.optional_skeletal_mesh=u.load_asset(P+'/Attachments/SK_AKM_MannyNative')
for folder in ['Attachments','ArmSupport','ArmSupportFinalV2']:
 a=u.load_asset(P+'/'+folder+'/prism/A_AKM_prism_aim');r={}
 for mode in ['RAW','COMPRESSED']:
  opt.evaluation_type=getattr(u.AnimDataEvalType,mode);p=u.AnimPoseExtensions.get_anim_pose_at_time(a,0,opt);r[mode]={}
  for n in ['hand_l','pinky_metacarpal_l','pinky_01_l','pinky_02_l','pinky_03_l']:
   t=u.AnimPoseExtensions.get_bone_pose(p,n,u.AnimPoseSpaces.LOCAL);r[mode][n]={'p':str(t.translation),'q':str(t.rotation),'s':str(t.scale3d)}
 report[folder]=r
(O/'track_probe.json').write_text(json.dumps(report,indent=2));u.log('TRACK_PROBE_PASS')
