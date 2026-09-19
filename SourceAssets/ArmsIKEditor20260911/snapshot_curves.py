"""Read every dense FK sample directly; avoid deferred Sequencer evaluation in a tick."""
import unreal,json
from pathlib import Path
O=Path(__file__).parent;E=unreal.LevelSequenceEditorBlueprintLibrary
seq=unreal.load_asset('/Game/Weapons/M4ArmsIKEditor/LS_Vertical_UserFK_Backup')
E.open_level_sequence(seq);E.set_current_time(0)
r=unreal.ControlRigSequencerLibrary.get_control_rigs(seq)[0].control_rig;h=r.get_hierarchy()
data=json.loads((O/'source_snapshot.json').read_text());data['poses']=[]
channels={}
for b in seq.get_bindings():
 for t in b.get_tracks():
  if isinstance(t,unreal.MovieSceneControlRigParameterTrack):
   for s in t.get_sections():
    channels.update({str(ch.channel_name):ch for ch in s.get_all_channels()})
samples={n:{k.get_time().frame_number.value:k.get_value() for k in ch.get_keys()} for n,ch in channels.items()}
controls=h.get_controls()
suffix=['Location.X','Location.Y','Location.Z','Rotation.X','Rotation.Y','Rotation.Z','Scale.X','Scale.Y','Scale.Z']
def tf(t):return {'p':list(t.translation.to_tuple()),'q':[t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w],'s':list(t.scale3d.to_tuple())}
for frame in range(data['start'],data['end']+1):
 for key in controls:
  values=[samples[str(key.name)+'.'+x][frame] for x in suffix]
  value=unreal.EulerTransform(location=unreal.Vector(*values[:3]),rotation=unreal.Rotator(pitch=values[4],yaw=values[5],roll=values[3]),scale=unreal.Vector(*values[6:]))
  h.set_control_value(key,h.make_control_value_from_euler_transform(value))
 assert r.execute('Forwards Solve')
 data['poses'].append({str(k.name):tf(h.get_global_transform(k)) for k in h.get_bones()})
data['snapshot_method']='Dense source channels evaluated explicitly through original FK Rig'
(O/'source_snapshot.json').write_text(json.dumps(data))
unreal.log('ARMS_IK_CURVE_SNAPSHOT '+str(len(data['poses'])))
