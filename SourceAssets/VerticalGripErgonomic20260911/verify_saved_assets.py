import unreal,json,math
from pathlib import Path
O=Path(__file__).parent;mesh=unreal.load_asset('/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416');report={}
for variant in ['Vertical','Prism']:
 for clip,info in json.loads((O/variant.lower()/'animation_build.json').read_text()).items():
  path=f'/Game/Weapons/M4VerticalGripErgonomic/{variant}/A_M4_{variant}_{clip}';a=unreal.load_asset(path);assert a and a.get_editor_property('skeleton')==mesh.skeleton
  options=unreal.AnimPoseEvaluationOptions();options.optional_skeletal_mesh=mesh;pos=ang=0
  for k in range(round(info['duration']*60)+1):
   options.evaluation_type=unreal.AnimDataEvalType.RAW;raw=unreal.AnimPoseExtensions.get_anim_pose_at_time(a,k/60,options);options.evaluation_type=unreal.AnimDataEvalType.COMPRESSED;comp=unreal.AnimPoseExtensions.get_anim_pose_at_time(a,k/60,options)
   for n in ['upperarm_l','lowerarm_l','lowerarm_twist_01_l','lowerarm_twist_02_l','hand_l','index_01_l','index_03_l','middle_03_l','ring_03_l','pinky_03_l','thumb_03_l']:
    x=unreal.AnimPoseExtensions.get_bone_pose(raw,n,unreal.AnimPoseSpaces.WORLD);y=unreal.AnimPoseExtensions.get_bone_pose(comp,n,unreal.AnimPoseSpaces.WORLD);pos=max(pos,x.translation.distance(y.translation));q=x.rotation;r=y.rotation;dot=abs(q.x*r.x+q.y*r.y+q.z*r.z+q.w*r.w)/math.sqrt((q.x*q.x+q.y*q.y+q.z*q.z+q.w*q.w)*(r.x*r.x+r.y*r.y+r.z*r.z+r.w*r.w));ang=max(ang,math.degrees(2*math.acos(min(1,dot))))
  assert pos<.01 and ang<.1,(path,pos,ang);assert abs(a.get_play_length()-info['duration'])<.0001
  report[path]={'position_error_cm':pos,'rotation_error_deg':ang,'duration':a.get_play_length()}
(O/'saved_asset_validation.json').write_text(json.dumps(report,indent=2));unreal.log('ERGONOMIC_SAVED_ASSETS_PASS 18')
