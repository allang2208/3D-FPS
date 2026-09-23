import unreal as u,json,math
from pathlib import Path
O=Path(__file__).parent;P='/Game/Weapons/PKMLowpoly20260922';mesh=u.load_asset(P+'/SK_PKM_Manny');clip=u.load_asset(P+'/Animations/A_PKM_idle')
out={'mesh':mesh.get_path_name(),'idle_source':clip.get_editor_property('asset_import_data').get_first_filename(),'poses':{}}
def v(a):return [a.x,a.y,a.z]
for mode in [u.AnimDataEvalType.RAW,u.AnimDataEvalType.COMPRESSED]:
 opt=u.AnimPoseEvaluationOptions();opt.optional_skeletal_mesh=mesh;opt.evaluation_type=mode
 pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,0,opt)
 bones={n:u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD) for n in ['upperarm_l','lowerarm_l','hand_l','lowerarm_twist_01_l','lowerarm_twist_02_l']}
 ref={n:u.AnimPoseExtensions.get_ref_bone_pose(pose,n,u.AnimPoseSpaces.WORLD) for n in ['hand_l','lowerarm_l']}
 axis=(bones['hand_l'].translation-bones['lowerarm_l'].translation).normal()
 aligned=bones['hand_l'].transform_direction(ref['hand_l'].inverse_transform_direction((ref['hand_l'].translation-ref['lowerarm_l'].translation).normal())).normal()
 dot=max(-1,min(1,axis.dot(aligned)))
 out['poses'][str(mode)]={'wrist_axis_deg':math.degrees(math.acos(dot)),'bones':{n:{'cm':v(t.translation),'transform':str(t)} for n,t in bones.items()}}
(O/globals().get('REPORT_NAME','engine_before.json')).write_text(json.dumps(out,indent=2));print(json.dumps({'source':out['idle_source'],'angles':{k:v['wrist_axis_deg'] for k,v in out['poses'].items()}}))
