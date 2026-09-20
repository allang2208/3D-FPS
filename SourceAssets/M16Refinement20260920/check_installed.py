"""Targeted readback of the reported finger/optic defects, no gameplay regression."""
import unreal as u,json,math
from pathlib import Path
O=Path(__file__).parent;result={};mesh=u.load_asset('/Game/Weapons/M16A2/Gameplay20260919/SK_M16_Manny');opt=u.AnimPoseEvaluationOptions();opt.optional_skeletal_mesh=mesh
for key,clip in json.loads((O/'reloads.json').read_text()).items():
 a=u.load_asset(clip['folder']+'/'+clip['name']);worstq=0.;worstp=0.;worstscale=0.
 for frame in [30,43,54,61,76,80,88,95,100,108,125]:
  poses={}
  for mode in ['RAW','COMPRESSED']:
   opt.evaluation_type=getattr(u.AnimDataEvalType,mode);poses[mode]=u.AnimPoseExtensions.get_anim_pose_at_time(a,frame/60,opt)
  for digit in ['thumb','index','middle','ring','pinky']:
   for segment in ['01','02','03']:
    name=digit+'_'+segment+'_l';r=u.AnimPoseExtensions.get_bone_pose(poses['RAW'],name,u.AnimPoseSpaces.LOCAL);c=u.AnimPoseExtensions.get_bone_pose(poses['COMPRESSED'],name,u.AnimPoseSpaces.LOCAL)
    q1=r.rotation;q2=c.rotation;dot=abs(q1.x*q2.x+q1.y*q2.y+q1.z*q2.z+q1.w*q2.w);worstq=max(worstq,math.degrees(2*math.acos(min(1,dot))))
    worstp=max(worstp,(r.translation-c.translation).length());worstscale=max(worstscale,max(abs(v-1) for v in [c.scale3d.x,c.scale3d.y,c.scale3d.z]))
 result[key]={'compressed_local_rotation_error_deg':worstq,'translation_error_cm':worstp,'scale_error':worstscale,'duration':a.get_play_length()}
m=u.load_asset('/Game/Weapons/M16A2/UniversalAttachments20260920/Meshes/SM_M16_holographic');result['glass']={str(s.material_slot_name):{'path':s.material_interface.get_path_name(),'blend':str(s.material_interface.get_base_material().get_editor_property('blend_mode'))} for s in m.static_materials}
result['sound']=u.load_asset('/Game/Weapons/M16A2/OriginalAudio20260920/S_M16_OriginalFire').get_path_name()
(O/'installed_inspection.json').write_text(json.dumps(result,indent=2));print('M16_TARGETED_READBACK_SAVED')
