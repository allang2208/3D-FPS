import unreal as u,json,os
from pathlib import Path
O=Path(__file__).parent;report={'pid':os.getpid()};opt=u.AnimPoseEvaluationOptions();opt.evaluation_type=u.AnimDataEvalType.COMPRESSED
paths={'m4_normal':'/Game/Weapons/ExtMagContact20260919/A_M4_ExtContact_reload','m4_empty':'/Game/Weapons/ExtMagContact20260919/A_M4_ExtContact_reload_empty','m16_idle':'/Game/Weapons/M16A2/Gameplay20260919/Animations/A_M16_idle','m16_normal':'/Game/Weapons/M16A2/Gameplay20260919/Animations/A_M16_reload','m16_empty':'/Game/Weapons/M16A2/Gameplay20260919/Animations/A_M16_reload_empty'}
for label,path in paths.items():
 a=u.load_asset(path);data=a.get_editor_property('asset_import_data');row={'asset':path,'duration':a.get_play_length(),'source':list(data.extract_filenames()),'frames':{}}
 for f in ([0] if label.endswith('idle') else [0,43,54,61,76,80,88,95,108,111,126]):
  p=u.AnimPoseExtensions.get_anim_pose_at_time(a,min(f/60,a.get_play_length()),opt);row['frames'][f]={}
  for name in ['WPN_root','WPN_SOCKET_Magazine','hand_l','hand_r','WPN_ChargingHandle']:
   t=u.AnimPoseExtensions.get_bone_pose(p,name,u.AnimPoseSpaces.WORLD);row['frames'][f][name]={'p':[t.translation.x,t.translation.y,t.translation.z],'q':[t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w],'s':[t.scale3d.x,t.scale3d.y,t.scale3d.z]}
 report[label]=row
(O/'runtime_sources.json').write_text(json.dumps(report,indent=2));print('M16_M4_INSERT_RUNTIME_READ')
