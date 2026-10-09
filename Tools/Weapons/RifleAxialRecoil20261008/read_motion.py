"""Requested read-only comparison of current rifle fire motion and routing."""
import json, math
from pathlib import Path
import unreal as u

O=Path(__file__).parent
P=Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir())).resolve()
if P!=Path('D:/FPS3D/FPSGAME').resolve():raise RuntimeError('Wrong project '+str(P))
S=u.AnimPoseSpaces.WORLD
def vec(v): return [v.x,v.y,v.z]
def sub(a,b): return [x-y for x,y in zip(a,b)]
def dot(a,b): return sum(x*y for x,y in zip(a,b))
def norm(a): return math.sqrt(dot(a,a))
def tf(t): return dict(p=vec(t.translation),q=[t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w],s=vec(t.scale3d))
specs={
 'm4':('/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416','/Game/Weapons/M4ContactImpactFinal/A_AKM_'),
 'hk416':('/Game/Weapons/HK416/Reworked20260930/SK_HK416_Manny','/Game/Weapons/HK416/Reworked20260930/Animations/base/A_HK416_base_'),
 'qbz191':('/Game/Weapons/QBZ191/RearGrip20260913/SK_QBZ191_Manny','/Game/Weapons/QBZ191/Refined20260913/Animations/base/A_QBZ191_'),
 'a762':('/Game/Weapons/A762/Integrated20260920/SK_A762_Manny','/Game/Weapons/A762/Integrated20260920/Animations/A_A762_')}
report=dict(project=str(P),weapons={},read_only=True,game_started=False,sample_hz=240)
for weapon,(mesh_path,prefix) in specs.items():
 mesh=u.load_asset(mesh_path)
 opts=u.AnimPoseEvaluationOptions();opts.evaluation_type=u.AnimDataEvalType.COMPRESSED
 opts.optional_skeletal_mesh=mesh;opts.should_retarget=True
 row=dict(mesh=mesh_path,clips={},profiles={})
 for role in ('fire','aim_fire'):
  clip=u.load_asset(prefix+role)
  if not clip:raise RuntimeError('Missing '+prefix+role)
  length=clip.get_play_length();samples=[]
  for i in range(math.ceil(length*240)+1):
   t=min(i/240,length);pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,t,opts)
   values={n:tf(u.AnimPoseExtensions.get_bone_pose(pose,n,S)) for n in
      ('WPN_root','WPN_RearSight','WPN_FrontSight','hand_r','hand_l','upperarm_r','lowerarm_r')}
   samples.append(dict(time=t,bones=values))
  initial=samples[0]['bones'];axis=sub(initial['WPN_FrontSight']['p'],initial['WPN_RearSight']['p']);axis=[x/norm(axis) for x in axis]
  for sample in samples:
   delta=sub(sample['bones']['WPN_root']['p'],initial['WPN_root']['p'])
   sample['rearward_cm']=-dot(delta,axis)
  peak=max(samples,key=lambda s:s['rearward_cm']);forward=min(samples,key=lambda s:s['rearward_cm'])
  row['clips'][role]=dict(asset=clip.get_path_name(),duration=length,rate_scale=clip.get_editor_property('rate_scale'),
      rearward_peak_cm=peak['rearward_cm'],peak_time=peak['time'],forward_peak_cm=forward['rearward_cm'],samples=samples)
 for family in ('base','drum','angled','vertical','canted','prism'):
  path='/Game/Weapons/AnimationProfiles20261001/ue_'+('m4a1' if weapon=='m4' else weapon)+'/DA_'+family
  if not (P/'Content'/(path.removeprefix('/Game/')+'.uasset')).exists():continue
  profile=u.load_asset(path)
  if not profile:raise RuntimeError('Cannot load saved grip profile '+path)
  entries=[]
  for layer in profile.get_editor_property('clips'):
   base=layer.get_editor_property('base')
   if not base or not base.get_name().lower().endswith(('_fire','_aim_fire')):continue
   retained=layer.get_editor_property('retained')
   tracks=[]
   for track in layer.get_editor_property('tracks'):
    if str(track.get_editor_property('bone')) in ('WPN_root','root','pelvis'):
     tracks.append(dict(bone=str(track.get_editor_property('bone')),times=list(track.get_editor_property('times')),values=list(track.get_editor_property('values'))))
   entries.append(dict(base=base.get_path_name(),retained=retained.get_path_name() if retained else None,duration=layer.get_editor_property('duration'),root_tracks=tracks))
  row['profiles'][family]=dict(path=path,entries=entries)
 report['weapons'][weapon]=row
 print('RIFLE_AXIAL_INPUT',weapon,json.dumps({k:{q:v[q] for q in ('duration','rearward_peak_cm','peak_time','forward_peak_cm')} for k,v in row['clips'].items()}),flush=True)
(O/'motion_before.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
