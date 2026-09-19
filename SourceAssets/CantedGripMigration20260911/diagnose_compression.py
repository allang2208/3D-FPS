import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;report={};opt=u.AnimPoseEvaluationOptions();opt.optional_skeletal_mesh=u.load_asset('/Game/Weapons/AKMIntegration/SovietFab/Attachments/SK_AKM_MannyNative')
for variant in ['vertical','angled']:
 a=u.load_asset('/Game/Weapons/AKMIntegration/SovietFab/GripErgonomic/'+variant+'/A_AKM_'+variant+'_idle');u.AKMAnimationAuditLibrary.finish_animation_compression(a);compression=a.get_editor_property('bone_compression_settings');data={'codec':str(compression),'codecs':[str(c) for c in compression.get_editor_property('codecs')]};opt.evaluation_type=u.AnimDataEvalType.RAW;raw=u.AnimPoseExtensions.get_anim_pose_at_time(a,0,opt);opt.evaluation_type=u.AnimDataEvalType.COMPRESSED;comp=u.AnimPoseExtensions.get_anim_pose_at_time(a,0,opt);data['bones']={}
 for n in ['clavicle_l','upperarm_l','lowerarm_l','hand_l','index_metacarpal_l','index_01_l','index_02_l','index_03_l','middle_03_l','ring_03_l','pinky_03_l','thumb_03_l']:
  a1=u.AnimPoseExtensions.get_bone_pose(raw,n,u.AnimPoseSpaces.WORLD);b=u.AnimPoseExtensions.get_bone_pose(comp,n,u.AnimPoseSpaces.WORLD);data['bones'][n]={'raw':str(a1),'compressed':str(b),'distance':a1.translation.distance(b.translation)}
 report[variant]=data
(O/'compression_diagnosis.json').write_text(json.dumps(report,indent=2));u.log('COMPRESSION_DIAG_DONE')
