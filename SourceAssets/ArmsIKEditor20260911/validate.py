import unreal,json,math
from pathlib import Path
O=Path(__file__).parent;E=unreal.LevelSequenceEditorBlueprintLibrary;L=unreal.ControlRigSequencerLibrary
seq=E.get_current_level_sequence();assert seq.get_name()=='LS_M4_Vertical_Idle_IK_Edit', 'Open the IK edit sequence'
r=L.get_control_rigs(seq)[0].control_rig;h=r.get_hierarchy()
assert 'CR_M4_ArmsIK' in r.get_class().get_name()
source=json.loads((O/'source_snapshot.json').read_text())
def bone(n):return unreal.RigElementKey(type=unreal.RigElementType.BONE,name=n)
def control(n):return unreal.RigElementKey(type=unreal.RigElementType.CONTROL,name=n)
def angle(a,b):
 dot=abs(a.x*b.x+a.y*b.y+a.z*b.z+a.w*b.w)/math.sqrt((a.x*a.x+a.y*a.y+a.z*a.z+a.w*a.w)*(b.x*b.x+b.y*b.y+b.z*b.z+b.w*b.w))
 return math.degrees(2*math.acos(min(1,dot)))
report={'baseline':[],'ik':[]}
channels={}
for binding in seq.get_bindings():
 for track in binding.get_tracks():
  if isinstance(track,unreal.MovieSceneControlRigParameterTrack):
   for section in track.get_sections():
    channels.update({str(ch.channel_name):{k.get_time().frame_number.value:k.get_value() for k in ch.get_keys()} for ch in section.get_all_channels()})
suffix=['Location.X','Location.Y','Location.Z','Rotation.X','Rotation.Y','Rotation.Z','Scale.X','Scale.Y','Scale.Z']
def evaluate(frame):
 for key in h.get_controls():
  n=str(key.name)
  if n.endswith(('_ik_ctrl','_pole_ctrl')):v=[0,0,0,0,0,0,1,1,1]
  else:v=[channels[n+'.'+s][frame] for s in suffix]
  h.set_control_value(key,h.make_control_value_from_euler_transform(unreal.EulerTransform(location=unreal.Vector(*v[:3]),rotation=unreal.Rotator(pitch=v[4],yaw=v[5],roll=v[3]),scale=unreal.Vector(*v[6:]))))
 assert r.execute('Forwards Solve')
for frame in range(361):
 evaluate(frame)
 p=source['poses'][frame];maxp=maxq=0.;worst=''
 for n,v in p.items():
  t=h.get_global_transform(bone(n));err=(t.translation-unreal.Vector(*v['p'])).length()
  if err>maxp:maxp=err;worst=n
  maxq=max(maxq,angle(t.rotation,unreal.Quat(*v['q'])))
 report['baseline'].append({'frame':frame,'max_position_cm':maxp,'max_rotation_deg':maxq,'worst':worst})
evaluate(0)
for side in ['l','r']:
 names=['upperarm_'+side,'lowerarm_'+side,'hand_'+side]
 initial=[h.get_global_transform(bone(n)) for n in names]
 fingers={str(k.name):h.get_local_transform(k) for k in h.get_bones() if str(k.name).endswith('_'+side) and str(k.name).startswith(('thumb','index','middle','ring','pinky'))}
 lengths=[(initial[i+1].translation-initial[i].translation).length() for i in [0,1]]
 key=control('hand_'+side+'_ik_ctrl');original=h.get_global_transform(key)
 t=h.get_global_transform(key);t.translation+=unreal.Vector(2,0,1)
 h.set_global_transform(key,t);assert r.execute('Forwards Solve')
 actual=[h.get_global_transform(bone(n)) for n in names]
 report['ik'].append({'side':side,'target_error_cm':(actual[2].translation-t.translation).length(),'elbow_moved_cm':(actual[1].translation-initial[1].translation).length(),'length_error_cm':max(abs((actual[i+1].translation-actual[i].translation).length()-lengths[i]) for i in [0,1]),'finger_rotation_error_deg':max(angle(h.get_local_transform(bone(n)).rotation,v.rotation) for n,v in fingers.items())})
 h.set_global_transform(key,original);r.execute('Forwards Solve')
 polekey=control('elbow_'+side+'_pole_ctrl');pole=h.get_global_transform(polekey);shifted=h.get_global_transform(polekey);shifted.translation+=unreal.Vector(0,0,4)
 h.set_global_transform(polekey,shifted);r.execute('Forwards Solve')
 report['ik'][-1]['pole_elbow_moved_cm']=(h.get_global_transform(bone(names[1])).translation-initial[1].translation).length()
 report['ik'][-1]['pole_hand_error_cm']=(h.get_global_transform(bone(names[2])).translation-initial[2].translation).length()
 h.set_global_transform(polekey,pole);r.execute('Forwards Solve')
 far=h.get_global_transform(key);far.translation+=unreal.Vector(150,0,0)
 h.set_global_transform(key,far);r.execute('Forwards Solve')
 farbones=[h.get_global_transform(bone(n)) for n in names]
 report['ik'][-1]['unreachable_length_error_cm']=max(abs((farbones[i+1].translation-farbones[i].translation).length()-lengths[i]) for i in [0,1])
 h.set_global_transform(key,original);r.execute('Forwards Solve')
evaluate(0);E.set_current_time(0)
(O/'validation.json').write_text(json.dumps(report,indent=2))
summary={'frames':len(report['baseline']),'max_position_cm':max(x['max_position_cm'] for x in report['baseline']),'max_rotation_deg':max(x['max_rotation_deg'] for x in report['baseline']),'ik':report['ik']}
(O/'validation_summary.json').write_text(json.dumps(summary,indent=2))
# Euler channel roundtrip tolerance: 0.05 degrees; retain measured error in report.
assert summary['max_position_cm']<.001 and summary['max_rotation_deg']<.05,summary
assert all(x['target_error_cm']<.001 and x['length_error_cm']<.001 and x['finger_rotation_error_deg']<.01 and x['pole_hand_error_cm']<.001 and x['pole_elbow_moved_cm']>.01 and x['unreachable_length_error_cm']<.001 for x in report['ik']),report['ik']
unreal.log('ARMS_IK_VALIDATION_PASS '+json.dumps(summary))
