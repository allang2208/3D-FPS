import unreal,json
from pathlib import Path
O=Path(__file__).parent;D='/Game/Weapons/M4ArmsIKEditor'
data=json.loads((O/'source_snapshot.json').read_text());mapping=json.loads((O/'rig_build.json').read_text())['mapping']
E=unreal.LevelSequenceEditorBlueprintLibrary;L=unreal.ControlRigSequencerLibrary
mesh=unreal.load_asset('/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416')
bp=unreal.load_asset(D+'/CR_M4_ArmsIK');bp.recompile_vm()
def tf(v):
 t=unreal.Transform(location=unreal.Vector(*v['p']),scale=unreal.Vector(*v['s']));t.rotation=unreal.Quat(*v['q']);return t
name='LS_M4_Vertical_Idle_IK_Edit'
seq=unreal.load_asset(D+'/'+name) or unreal.AssetToolsHelpers.get_asset_tools().create_asset(name,D,unreal.LevelSequence,unreal.LevelSequenceFactoryNew())
seq.set_display_rate(unreal.FrameRate(data['fps'],1));seq.set_playback_start(data['start']);seq.set_playback_end(data['end'])
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
actor=actors.spawn_actor_from_class(unreal.SkeletalMeshActor,unreal.Vector(0,0,150),transient=True)
assert actor, 'Exit Play mode before building the IK editor sequence'
for old in seq.get_bindings():old.remove()
actor.set_actor_label('M4 Arms IK Editing');actor.skeletal_mesh_component.set_skeletal_mesh_asset(mesh)
binding=seq.add_spawnable_from_instance(actor)
E.open_level_sequence(seq)
track=L.find_or_create_control_rig_track(world,seq,bp.get_control_rig_class(),binding,False)
section=track.get_sections()[0];section.set_range(data['start'],data['end'])
spawn=binding.add_track(unreal.MovieSceneSpawnTrack);s=spawn.add_section();s.set_range(data['start'],data['end'])
for ch in s.get_all_channels():ch.set_default(True)
E.refresh_current_level_sequence();E.set_current_time(data['start'])
rig=L.get_control_rigs(seq)[0].control_rig
h=bp.hierarchy;frames=[unreal.FrameNumber(i) for i in range(data['start'],data['end']+1)]
poses=[{n:tf(t) for n,t in p.items()} for p in data['poses']]
channels={str(ch.channel_name):ch for ch in section.get_all_channels()}
suffixes=['Location.X','Location.Y','Location.Z','Rotation.X','Rotation.Y','Rotation.Z','Scale.X','Scale.Y','Scale.Z']
def write_values(control, times, values):
 for frame,value in zip(times,values):
  numbers=[value.location.x,value.location.y,value.location.z,value.rotation.roll,value.rotation.pitch,value.rotation.yaw,value.scale.x,value.scale.y,value.scale.z]
  for suffix,number in zip(suffixes,numbers):
   channels[control+'.'+suffix].add_key(frame,number,interpolation=unreal.MovieSceneKeyInterpolation.LINEAR)
for index,b in enumerate(h.get_bones()):
 n=str(b.name);parent=str(h.get_first_parent(b).name);control=mapping[n]
 offset=h.get_local_transform(b,True)
 values=[]
 for pose in poses:
  local=unreal.MathLibrary.make_relative_transform(pose[n],pose[parent]) if parent in pose else pose[n]
  value=unreal.MathLibrary.make_relative_transform(local,offset)
  values.append(unreal.EulerTransform(location=value.translation,rotation=value.rotation.rotator(),scale=value.scale3d))
 write_values(control,frames,values)
 if index%20==0:unreal.log('ARMS_IK_COPY '+str(index))
# Offset controls intentionally have only zero endpoints, so a correction can span the clip.
for ctrl in ['hand_l_ik_ctrl','hand_r_ik_ctrl','elbow_l_pole_ctrl','elbow_r_pole_ctrl']:
 write_values(ctrl,[frames[0],frames[-1]],[unreal.EulerTransform(scale=[1,1,1])]*2)
E.set_current_time(data['frame']);E.refresh_current_level_sequence()
assert unreal.EditorAssetLibrary.save_loaded_asset(seq,False)
actors.destroy_actor(actor)
(O/'sequence_build.json').write_text(json.dumps({'sequence':seq.get_path_name(),'frames':len(frames),'source':data['source']},indent=2))
unreal.log('ARMS_IK_EDIT_SEQUENCE_READY')
