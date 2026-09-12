import unreal as u,json,math
from pathlib import Path
O=Path(__file__).parent/'Final';build=json.loads((O/'build.json').read_text());report={}
def angle(q,r):
 dot=abs(q.x*r.x+q.y*r.y+q.z*r.z+q.w*r.w)/math.sqrt((q.x*q.x+q.y*q.y+q.z*q.z+q.w*q.w)*(r.x*r.x+r.y*r.y+r.z*r.z+r.w*r.w));return math.degrees(2*math.acos(min(1,dot)))
def bone(p,n):return u.AnimPoseExtensions.get_bone_pose(p,n,u.AnimPoseSpaces.WORLD)
for key,info in build.items():
 weapon,clip=key.split(':');name=f'A_{weapon.upper()}_{"Vertical" if weapon=="m4" else "vertical"}_{clip}'
 directory='/Game/Weapons/M4VerticalGripVRENatural/Vertical' if weapon=='m4' else '/Game/Weapons/AKMIntegration/SovietFab/GripVRENatural/vertical'
 a=u.load_asset(directory+'/'+name);base=u.load_asset(directory.replace('GripVRENatural','GripOpposed')+'/'+name);assert a and base
 mesh=u.load_asset('/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416' if weapon=='m4' else '/Game/Weapons/AKMIntegration/SovietFab/Attachments/SK_AKM_MannyNative')
 assert a.get_editor_property('skeleton')==mesh.skeleton and abs(a.get_play_length()-base.get_play_length())<.0001
 u.AKMAnimationAuditLibrary.finish_animation_compression(a);u.AKMAnimationAuditLibrary.finish_animation_compression(base)
 opt=u.AnimPoseEvaluationOptions();opt.optional_skeletal_mesh=mesh;hz=60 if weapon=='m4' else 120
 interval=([28 if clip.startswith('drum') else 16,info['frames']-24] if weapon=='m4' else [42,380 if 'empty' in clip else 270]) if 'reload' in clip else None
 pos=rot=nonleft=contact=0.
 for k in range(round(info['duration']*hz)+1):
  t=k/hz;opt.should_retarget=False;opt.evaluation_type=u.AnimDataEvalType.RAW;raw=u.AnimPoseExtensions.get_anim_pose_at_time(a,t,opt)
  opt.should_retarget=True;opt.evaluation_type=u.AnimDataEvalType.COMPRESSED;new=u.AnimPoseExtensions.get_anim_pose_at_time(a,t,opt);old=u.AnimPoseExtensions.get_anim_pose_at_time(base,t,opt)
  for n in ['upperarm_l','lowerarm_l','lowerarm_twist_01_l','lowerarm_twist_02_l','hand_l']+[f'{d}_{i:02}_l' for d in ['thumb','index','middle','ring','pinky'] for i in [1,2,3]]:
   x,y=bone(raw,n),bone(new,n);pos=max(pos,x.translation.distance(y.translation));rot=max(rot,angle(x.rotation,y.rotation))
  for n in ['hand_r','index_03_r','WPN_root','WPN_SOCKET_Magazine','WPN_bolt','WPN_Trigger','WPN_ChargingHandle','WPN_BoltCatch']:
   nonleft=max(nonleft,bone(new,n).translation.distance(bone(old,n).translation))
  if interval and interval[0]<=k<=interval[1]:
   for n in ['hand_l','thumb_03_l','index_03_l','middle_03_l','ring_03_l','pinky_03_l']:contact=max(contact,bone(new,n).translation.distance(bone(old,n).translation))
 ok=pos<.03 and rot<.15 and nonleft<.03 and contact<.03
 report[key]={'asset':a.get_path_name(),'duration':a.get_play_length(),'sample_rate':hz,'compression_position_cm':pos,'compression_rotation_deg':rot,'preserved_nonleft_cm':nonleft,'preserved_contact_cm':contact,'passed':ok}
 (O/'asset_validation.json').write_text(json.dumps(report,indent=2));u.log('VRE_ASSET_READBACK '+key+' '+str(ok))
assert len(report)==18 and all(v['passed'] for v in report.values()),report
u.log('VRE_READBACK_PASS 18')
