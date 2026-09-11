import unreal as u,json,math,os
from pathlib import Path
O=Path(__file__).parent;P='/Game/Weapons/AKMIntegration/SovietFab';report=json.loads((O/'asset_validation.json').read_text()) if (O/'asset_validation.json').exists() else {};failures=[]
def angle(q,r):
 dot=abs(q.x*r.x+q.y*r.y+q.z*r.z+q.w*r.w)/math.sqrt((q.x*q.x+q.y*q.y+q.z*q.z+q.w*q.w)*(r.x*r.x+r.y*r.y+r.z*r.z+r.w*r.w));return math.degrees(2*math.acos(min(1,dot)))
def bone(p,n):return u.AnimPoseExtensions.get_bone_pose(p,n,u.AnimPoseSpaces.WORLD)
for weapon,variant in [('m4','canted')]+[('akm',v) for v in ['canted','vertical','prism','angled']]:
 if os.environ.get('FPS_GRIP_IMPORT_FILTER') and weapon+':'+variant not in os.environ['FPS_GRIP_IMPORT_FILTER'].split(','):continue
 d=O/weapon/variant;build=json.loads((d/('animation_build.json' if weapon=='m4' else 'build.json')).read_text());mesh=u.load_asset('/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416' if weapon=='m4' else P+'/Attachments/SK_AKM_MannyNative');opt=u.AnimPoseEvaluationOptions();opt.optional_skeletal_mesh=mesh
 for clip,info in build.items():
  name=f'A_{weapon.upper()}_{"Canted" if weapon=="m4" else variant}_{clip}';path=('/Game/Weapons/M4CantedErgonomic' if weapon=='m4' else P+'/GripErgonomic/'+variant)+'/'+name;a=u.load_asset(path);assert a
  if weapon=='m4':base=u.load_asset('/Game/Weapons/M4CantedThumbClose/'+name)
  else:base=u.load_asset((P+'/ReloadPolish/base' if 'reload' in clip else '/Game/Weapons/AKMIntegration/EquipCharge' if clip=='equip' else '/Game/Weapons/AKMIntegration/SourceMatched')+'/A_AKM_'+clip)
  assert base and a.get_editor_property('skeleton')==mesh.skeleton and abs(a.get_play_length()-base.get_play_length())<.0001
  u.AKMAnimationAuditLibrary.finish_animation_compression(a);u.AKMAnimationAuditLibrary.finish_animation_compression(base);hz=120 if weapon=='akm' else 60;pos=rot=preserved=nonleft=tail=0
  for k in range(round(info['duration']*hz)+1):
   t=k/hz;opt.should_retarget=False;opt.evaluation_type=u.AnimDataEvalType.RAW;raw=u.AnimPoseExtensions.get_anim_pose_at_time(a,t,opt);opt.should_retarget=True;opt.evaluation_type=u.AnimDataEvalType.COMPRESSED;new=u.AnimPoseExtensions.get_anim_pose_at_time(a,t,opt);old=u.AnimPoseExtensions.get_anim_pose_at_time(base,t,opt)
   for n in ['upperarm_l','lowerarm_l','lowerarm_twist_01_l','lowerarm_twist_02_l','hand_l','index_01_l','index_03_l','middle_03_l','ring_03_l','pinky_03_l','thumb_03_l']:
    x,y=bone(raw,n),bone(new,n);pos=max(pos,x.translation.distance(y.translation));rot=max(rot,angle(x.rotation,y.rotation))
   for n in ['hand_r','index_03_r','WPN_root','WPN_SOCKET_Magazine','WPN_bolt','WPN_Trigger','WPN_ChargingHandle','WPN_BoltCatch']:
    nonleft=max(nonleft,bone(new,n).translation.distance(bone(old,n).translation))
   interval=([42,380 if 'empty' in clip else 270] if weapon=='akm' else [28 if clip.startswith('drum') else 16,info['frames']-24]) if 'reload' in clip else None
   if interval and interval[0]<=k<=interval[1]:
    for n in ['hand_l','index_03_l','middle_03_l','ring_03_l','pinky_03_l','thumb_03_l']:preserved=max(preserved,bone(new,n).translation.distance(bone(old,n).translation))
  ok=pos<.03 and rot<.15 and nonleft<.03 and preserved<.03
  report[path]={'duration':a.get_play_length(),'samples_hz':hz,'compression_position_cm':pos,'compression_rotation_deg':rot,'preserved_nonleft_cm':nonleft,'preserved_reload_contact_cm':preserved,'passed':ok}
  if not ok:failures.append(path)
  (O/'asset_validation.json').write_text(json.dumps(report,indent=2));u.log('GRIP_ASSET_READBACK '+name+' '+str(ok))
assert not failures,failures
u.log('GRIP_MIGRATION_READBACK_PASS '+str(len(report)))
