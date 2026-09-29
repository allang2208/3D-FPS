"""Read compressed grip/reload motion as gauntlet authoring constraints.

Does not play, change, or save any UE asset or game state.
"""
import json
import math
from pathlib import Path
import unreal as u

P=Path('D:/FPS3D/FPSGAME')
R=P/'SourceAssets/MetalGauntlet20260927/SteelGauntletV1'
OUT=R/'ArticulationSolve20260928'
OUT.mkdir(exist_ok=True)
SPECS={
 'M4':{
  'idle':'/Game/Weapons/M4ContactImpactFinal/A_AKM_idle',
  'aim':'/Game/Weapons/M4ContactImpactFinal/A_AKM_aim',
  'reload':'/Game/Weapons/M4TacticalTossFinal/A_M4_HK416_reload',
  'reload_empty':'/Game/Weapons/M4SlapImpactFinal/A_M4_HK416_reload_empty',
  'drum_reload':'/Game/Weapons/M4DrumDrop/Contact/A_M4_DrumContact_reload'},
 'M1911':{
  'idle':'/Game/Weapons/M1911/Contact20260913/Animations/A_M1911_idle',
  'aim':'/Game/Weapons/M1911/Contact20260913/Animations/A_M1911_aim',
  'reload':'/Game/Weapons/M1911/ReloadReady20260913/Animations/A_M1911_reload',
  'reload_empty':'/Game/Weapons/M1911/ReloadReady20260913/Animations/A_M1911_reload_empty'},
 'DW715':{
  'idle':'/Game/Weapons/DanWesson715/Upgrade20260914/Animations/A_DW715_idle',
  'aim':'/Game/Weapons/DanWesson715/Upgrade20260914/Animations/A_DW715_aim',
  'reload_speed':'/Game/Weapons/DanWesson715/PalmClearance20260915/Animations/A_DW715_speed_0',
  'reload_single':'/Game/Weapons/DanWesson715/PalmClearance20260915/Animations/A_DW715_single_0_6'}
}
def xyz(v):return [v.x,v.y,v.z]
def bone(t):return dict(position=xyz(t.translation),axes=[xyz(t.transform_location(v)-t.translation) for v in (u.Vector(1,0,0),u.Vector(0,1,0),u.Vector(0,0,1))])
for profile,clips in SPECS.items():
 source=json.loads((R/'Sources'/f'{profile}.json').read_text(encoding='utf-8-sig'))
 names=sorted({b for ws in source['weights'] for b in ws})
 mesh=u.load_asset(source['binding_source'])
 if not mesh:raise RuntimeError('Missing native mesh '+source['binding_source'])
 options=u.AnimPoseEvaluationOptions();options.evaluation_type=u.AnimDataEvalType.COMPRESSED;options.optional_skeletal_mesh=mesh
 result=dict(profile=profile,mesh=mesh.get_path_name(),rate_hz=24,clips=[])
 for label,path in clips.items():
  asset=u.load_asset(path)
  if not asset:raise RuntimeError('Missing active animation '+path)
  duration=asset.get_play_length();count=math.ceil(duration*24)+1
  times=[min(i/24,duration) for i in range(count)] if label not in ('idle','aim') else [0.,duration*.5,duration]
  samples=[]
  for time in times:
   pose=u.AnimPoseExtensions.get_anim_pose_at_time(asset,time,options)
   samples.append(dict(time=time,bones={n:bone(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in names}))
  result['clips'].append(dict(label=label,asset=path,duration=duration,samples=samples))
  print('STEEL_MOTION_INPUT',profile,label,len(samples),flush=True)
 (OUT/f'{profile}_motion.json').write_text(json.dumps(result,separators=(',',':')),encoding='utf-8')
print('STEEL_MOTION_INPUTS_SAVED',flush=True)
