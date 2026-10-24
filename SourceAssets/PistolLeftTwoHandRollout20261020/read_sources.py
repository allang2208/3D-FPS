"""Saved native animation/profile inputs; no gameplay or asset writes."""
import json,hashlib
from pathlib import Path
import unreal as u
O=Path('D:/FPS3D/FPSGAME/SourceAssets/PistolLeftTwoHandRollout20261020')
(O/'Source').mkdir(parents=True,exist_ok=True)
hier=json.loads(Path('D:/FPS3D/FPSGAME/SourceAssets/BareSkinV9Rollout_20261017/Work/mesh_hierarchy.json').read_text())
weapons={
 'M1911':dict(definition='ue_m1911',mesh='/Game/Weapons/M1911/RearFinish20260913/SK_M1911_Manny',capacity=0),
 'G18':dict(definition='ue_g18',mesh='/Game/Weapons/G18/Integrated20260929/Single/SK_G18_Manny',capacity=0),
 'DW715':dict(definition='ue_dan_wesson715',mesh='/Game/Weapons/DanWesson715/Chrome20260914/SK_DW715_Manny',capacity=6),
 'RSH12':dict(definition='ue_rsh12',mesh='/Game/Weapons/RSH12/Native71520261003/single/SK_RSH12_Manny',capacity=5),
}
def package(a):return a.get_path_name().split('.')[0] if a else None
def pack(t):
 p,q,s=t.translation,t.rotation,t.scale3d
 return [p.x,p.y,p.z,q.x,q.y,q.z,q.w,s.x,s.y,s.z]
def sources(key,cap):
 roles={}
 if not cap:
  for role in ['idle','idle_empty','aim','aim_empty','fire','fire_last','aim_fire','aim_fire_last','equip','equip_empty','reload','reload_empty','sprint','sprint_empty','quickcombat']:
   kind={'equip':'equip_charge','equip_empty':'equip_charge_empty'}.get(role,role)
   if key=='G18':path='/Game/Weapons/G18/Integrated20260929/Single/Animations/A_G18_'+kind
   elif role.startswith('sprint'):path='/Game/Weapons/PistolLocomotion20260914/M1911/Animations/A_M1911_'+kind
   elif role=='quickcombat':path='/Game/Weapons/M1911/QuickCombat20260919/Animations/A_M1911_quickcombat'
   else:path='/Game/Weapons/M1911/'+('ReloadReady20260913' if role.startswith('reload') else 'Contact20260913')+'/Animations/A_M1911_'+kind
   roles[role]=path
 else:
  for role in ['idle','aim','fire','aim_fire','equip']:
   roles[role]='/Game/Weapons/DanWesson715/Upgrade20260914/Animations/A_DW715_'+('equip_charge' if role=='equip' else role)
  roles['sprint']='/Game/Weapons/PistolLocomotion20260914/DW715/Animations/A_DW715_sprint'
  roles['quickcombat']='/Game/Weapons/DanWesson715/QuickCombat20260918/Animations/A_DW715_quickcombat'
  roles['speed_0']='/Game/Weapons/DanWesson715/PalmClearance20260915/Animations/A_DW715_speed_0'
  for start in range(cap):
   for count in range(1,cap-start+1):
    role=f'single_{start}_{count}'
    roles[role]='/Game/Weapons/DanWesson715/'+('PalmClearance20260915' if start==0 else 'LeftRecovery20260914')+'/Animations/A_DW715_'+role
 return roles
def read_profile(path):
 asset=u.load_asset(path)
 if not asset:raise RuntimeError('Required grip profile '+path)
 rows={}
 for c in asset.get_editor_property('clips'):
  rows[package(c.get_editor_property('base'))]=dict(
   retained=package(c.get_editor_property('retained')),duration=c.get_editor_property('duration'),
   tracks=[dict(bone=str(t.get_editor_property('bone')),times=list(t.get_editor_property('times')),values=list(t.get_editor_property('values'))) for t in c.get_editor_property('tracks')])
 return dict(asset=path,clips=rows)
for key,row in weapons.items():
 mesh=u.load_asset(row['mesh'])
 if not mesh:raise RuntimeError('Missing '+row['mesh'])
 h=dict(hier[row['mesh']]);ref=u.AnimPoseExtensions.get_reference_pose(mesh.skeleton)
 h['reference']=[pack(u.AnimPoseExtensions.get_bone_pose(ref,n,u.AnimPoseSpaces.LOCAL)) for n in h['names']]
 h['skeleton']=mesh.skeleton.get_path_name();row['hierarchy']=h
 row['roles']=sources(key,row['capacity']);row['profiles']={}
 if key=='G18':row['profiles']['drum']=read_profile('/Game/Weapons/G18/Drum50_20261003/Reload/DA_G18_Drum50')
 if key=='RSH12':
  row['profiles']['base']=read_profile('/Game/Weapons/RSH12/Native71520261003/Profiles/DA_RSH12_base')
  for family in ['vertical','canted','prism','angled']:
   row['profiles'][family]=read_profile('/Game/Weapons/RSH12/Foregrips20261004/Profiles/DA_RSH12_'+family)
 paths=set(row['roles'].values())
 for profile in row['profiles'].values():
  for source in row['roles'].values():
   data=profile['clips'].get(source)
   if data and data['retained']:paths.add(data['retained'])
 row['raw']={}
 for path in sorted(paths):
  name=hashlib.sha256((row['mesh']+path).encode()).hexdigest()[:16]+'.json'
  row['raw'][path]='Source/'+name;file=O/'Source'/name
  if file.exists():continue
  clip=u.load_asset(path)
  if not clip:raise RuntimeError('Required clip '+path)
  model=clip.get_editor_property('data_model_interface');rate=model.get_frame_rate();fps=rate.numerator/rate.denominator
  frames=[[pack(t) for t in u.AnimationLibrary.get_bone_poses_for_time(clip,h['names'],i/fps,False,mesh)] for i in range(model.get_number_of_keys())]
  file.write_text(json.dumps(dict(source=path,mesh=row['mesh'],rate=[rate.numerator,rate.denominator],fps=fps,length=model.get_play_length(),frames=frames),separators=(',',':')),encoding='utf-8')
  print('LONE_ROLLOUT_SOURCE',key,path,len(frames),flush=True)
 (O/'inputs.json').write_text(json.dumps(weapons,separators=(',',':')),encoding='utf-8')
 print('LONE_ROLLOUT_WEAPON_READY',key,flush=True)
print('LONE_ROLLOUT_SOURCES_COMPLETE',flush=True)
