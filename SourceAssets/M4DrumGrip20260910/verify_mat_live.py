import unreal,json,traceback
from pathlib import Path
O=Path('D:/FPS3D/FPSGAME/SourceAssets/M4DrumGrip20260910')
unreal.EditorPythonScripting.set_keep_python_script_alive(True)
from editor_toolset.toolsets.blueprint import BlueprintTools
from editor_toolset.toolsets.blueprint_node import PinID
mat=unreal.load_asset('/Game/Locodrome/MAT/Locodrome_MAT')
node=unreal.find_object(None,mat.get_path_name()+':getControlRigType.K2Node_CallFunction_10')
pin=PinID();pin.node=node;pin.direction=unreal.EdGraphPinDirection.EGPD_INPUT;pin.index_id=2
if BlueprintTools.get_pin_value(pin).lower()!='true':
 BlueprintTools.set_pin_value(pin,'true');BlueprintTools.compile_blueprint(mat)
 # Toolset save_assets skips clean packages; graph pin edits did not dirty this asset.
 unreal.EditorAssetLibrary.save_loaded_asset(mat,False)
for clip in ['reload','reload_empty']:
 s=unreal.load_asset('/Game/Weapons/M4DrumGripCandidate/LS_M4_DrumGrip_'+clip)
 for b in s.get_bindings():
  if not any(isinstance(t,unreal.MovieSceneSpawnTrack) for t in b.get_tracks()):
   t=b.add_track(unreal.MovieSceneSpawnTrack);sec=t.add_section();sec.set_range(s.get_playback_start(),s.get_playback_end())
   for channel in sec.get_all_channels():channel.set_default(True)
 unreal.EditorAssetLibrary.save_loaded_asset(s,False)
seq=unreal.load_asset('/Game/Weapons/M4DrumGripCandidate/LS_M4_DrumGrip_reload_empty')
unreal.LevelSequenceEditorBlueprintLibrary.open_level_sequence(seq)
unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(54)
widget=unreal.get_editor_subsystem(unreal.EditorUtilitySubsystem).spawn_and_register_tab(unreal.load_asset('/Game/Locodrome/MAT/Locodrome_MAT'))
rig=unreal.ControlRigSequencerLibrary.get_control_rigs(seq)[0].control_rig
report={'rig':rig.get_path_name(),'widget':widget.get_path_name(),'controls':[str(k.name) for k in rig.get_hierarchy().get_controls()]}
try:report['body_type']=widget.call_method('getControlRigType',(rig,))
except Exception as e:report['detect_error']=str(e)
report['api']={n:str(getattr(unreal.ControlRigSequencerLibrary,n).__doc__) for n in ['get_local_control_rig_euler_transform','set_local_control_rig_euler_transform']}
state={'ticks':0}
def tick(dt):
 try:
  state['ticks']+=1
  if state['ticks']==10:
   report['poses']={}
   for f in [25,54,80]:
    report['poses'][f]={n:str(unreal.ControlRigSequencerLibrary.get_local_control_rig_euler_transform(seq,rig,n,unreal.FrameNumber(f))) for n in ['hand_l_fk_ctrl','index_01_l_ctrl','WPN_SOCKET_Magazine_ctrl']}
   actors=[]
   for b in seq.get_bindings():
    bid=unreal.MovieSceneObjectBindingID();bid.set_editor_property('Guid',b.get_id())
    actors.extend(unreal.LevelSequenceEditorBlueprintLibrary.get_bound_objects(bid))
   report['skeletal_actors']=[]
   for a in actors:
    if isinstance(a,unreal.SkeletalMeshActor):
     comp=a.skeletal_mesh_component
     center,extent=a.get_actor_bounds(False)
     report['skeletal_actors'].append({'path':a.get_path_name(),'mesh':str(comp.get_editor_property('skeletal_mesh_asset')),'center':str(center),'extent':str(extent),'hand':str(comp.get_socket_transform('hand_l'))})
     delta=unreal.Vector(-80,90,40)
     unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).set_level_viewport_camera_info(center+delta,unreal.MathLibrary.find_look_at_rotation(center+delta,center))
   # Remove only this task's unused MAT duplication; original MAT now has the scoped hierarchy fix.
   candidate='/Game/Weapons/M4DrumGripCandidate/MAT_M4_DrumGrip'
   if unreal.EditorAssetLibrary.does_asset_exist(candidate):report['unused_widget_removed']=unreal.EditorAssetLibrary.delete_asset(candidate)
   unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(54)
   (O/'mat_verified.json').write_text(json.dumps(report,indent=2,default=str))
   unreal.log('MAT_VERIFY_READY '+str(report.get('body_type',report.get('detect_error'))))
   unreal.unregister_slate_post_tick_callback(handle)
 except Exception:
  (O/'mat_verify_error.txt').write_text(traceback.format_exc())
  unreal.unregister_slate_post_tick_callback(handle)
handle=unreal.register_slate_post_tick_callback(tick)
