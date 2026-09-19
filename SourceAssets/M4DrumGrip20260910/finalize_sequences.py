import unreal,json,traceback
from pathlib import Path
O=Path('D:/FPS3D/FPSGAME/SourceAssets/M4DrumGrip20260910')
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
unreal.SystemLibrary.execute_console_command(world,'ControlRig.EnableAnimNodePerformanceOptimizations 1')
state={'clip':0,'tick':0};report={};clips=[('reload',126,76),('reload_empty',162,54)]
def open_clip():
 clip,end,frame=clips[state['clip']]
 state['seq']=unreal.load_asset('/Game/Weapons/M4DrumGripCandidate/LS_M4_DrumGrip_'+clip)
 unreal.LevelSequenceEditorBlueprintLibrary.close_level_sequence()
 unreal.LevelSequenceEditorBlueprintLibrary.open_level_sequence(state['seq'])
 unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(0)
 state['tick']=0
def tick(dt):
 try:
  state['tick']+=1;s=state['seq'];clip,end,frame=clips[state['clip']]
  if state['tick']==3:
   b=s.get_bindings()[0];bid=unreal.MovieSceneObjectBindingID();bid.set_editor_property('Guid',b.get_id())
   a=unreal.LevelSequenceEditorBlueprintLibrary.get_bound_objects(bid)[0];state['actor']=a
   p=unreal.ControlRigSequencerLibrary.get_control_rigs(s)[0];state['rig']=p.control_rig
   q=p.track.get_sections()[0]
   ok=unreal.ControlRigSequencerLibrary.load_anim_sequence_into_control_rig_section_with_range(q,unreal.load_asset('/Game/Weapons/M4DrumGripCandidate/A_M4_DrumGrip_'+clip),a.skeletal_mesh_component,unreal.FrameNumber(0),False,unreal.FrameNumber(0),unreal.FrameNumber(end),key_reduce=False,interpolation=unreal.MovieSceneKeyInterpolation.LINEAR)
   assert ok
   q.set_range(0,end+1);unreal.EditorAssetLibrary.save_loaded_asset(s,False)
   unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(frame)
  if state['tick']==8:
   h=state['rig'].get_hierarchy();a=state['actor'];c=a.skeletal_mesh_component
   bone=h.get_global_transform(unreal.RigElementKey(name='hand_l',type=unreal.RigElementType.BONE))
   ctrl=h.get_global_transform(unreal.RigElementKey(name='hand_l_fk_ctrl',type=unreal.RigElementType.CONTROL))
   initial=h.get_global_transform(unreal.RigElementKey(name='hand_l',type=unreal.RigElementType.BONE),True)
   err=(bone.translation-ctrl.translation).length();motion=(bone.translation-initial.translation).length()
   assert err<.01 and motion>1,(err,motion)
   meshhand=c.get_socket_transform('hand_l',unreal.RelativeTransformSpace.RTS_COMPONENT)
   mesherr=(meshhand.translation-bone.translation).length();assert mesherr<.01,mesherr
   report[clip]={'bake_success':True,'frame':frame,'hand_control_bone_error_cm':err,'mesh_rig_error_cm':mesherr,'hand_motion_from_reference_cm':motion,'optimized_anim_node':unreal.SystemLibrary.get_console_variable_int_value('ControlRig.EnableAnimNodePerformanceOptimizations')}
   if state['clip']==0:state['clip']=1;open_clip()
   else:
    center,extent=a.get_actor_bounds(False);delta=unreal.Vector(-95,55,20)
    unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).set_level_viewport_camera_info(center+delta,unreal.MathLibrary.find_look_at_rotation(center+delta,center))
    (O/'sequence_runtime_verified.json').write_text(json.dumps(report,indent=2));unreal.log('DRUM_MAT_SEQUENCE_PASS '+json.dumps(report))
    unreal.unregister_slate_post_tick_callback(handle)
 except Exception:
  (O/'sequence_runtime_error.txt').write_text(traceback.format_exc());unreal.unregister_slate_post_tick_callback(handle)
open_clip();handle=unreal.register_slate_post_tick_callback(tick)
