import unreal,json,traceback
from pathlib import Path
O=Path('D:/FPS3D/FPSGAME/SourceAssets/M4DrumGrip20260910');D='/Game/Weapons/M4DrumGripCandidate'
unreal.EditorPythonScripting.set_keep_python_script_alive(True)
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
unreal.SystemLibrary.execute_console_command(world,'ControlRig.EnableAnimNodePerformanceOptimizations 0')
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
mesh=unreal.load_asset(D+'/SK_M4_DrumGripPreview')
state={'i':0,'tick':0};report={};clips=[('reload',126,76),('reload_empty',162,54)]
def begin():
 clip,end,frame=clips[state['i']];name='LS_M4_DrumGrip_FK_'+clip
 s=unreal.load_asset(D+'/'+name)
 if not s:s=unreal.AssetToolsHelpers.get_asset_tools().create_asset(name,D,unreal.LevelSequence,unreal.LevelSequenceFactoryNew())
 s.set_display_rate(unreal.FrameRate(60,1));s.set_playback_start(0);s.set_playback_end(end+1)
 if not s.get_bindings():
  a=actors.spawn_actor_from_class(unreal.SkeletalMeshActor,unreal.Vector(0,0,100));a.skeletal_mesh_component.set_skeletal_mesh_asset(mesh)
  b=s.add_spawnable_from_instance(a)
  unreal.ControlRigSequencerLibrary.find_or_create_control_rig_track(world,s,unreal.FKControlRig,b,False)
  actors.destroy_actor(a)
 unreal.LevelSequenceEditorBlueprintLibrary.close_level_sequence();unreal.LevelSequenceEditorBlueprintLibrary.open_level_sequence(s);unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(0)
 state.update(seq=s,tick=0)
def tick(dt):
 try:
  state['tick']+=1;s=state['seq'];clip,end,frame=clips[state['i']]
  if state['tick']==3:
   b=s.get_bindings()[0];bid=unreal.MovieSceneObjectBindingID();bid.set_editor_property('Guid',b.get_id())
   a=unreal.LevelSequenceEditorBlueprintLibrary.get_bound_objects(bid)[0];p=unreal.ControlRigSequencerLibrary.get_control_rigs(s)[0]
   state.update(actor=a,proxy=p)
   q=p.track.get_sections()[0]
   ok=unreal.ControlRigSequencerLibrary.load_anim_sequence_into_control_rig_section_with_range(q,unreal.load_asset(D+'/A_M4_DrumGrip_'+clip),a.skeletal_mesh_component,unreal.FrameNumber(0),False,unreal.FrameNumber(0),unreal.FrameNumber(end),key_reduce=False,interpolation=unreal.MovieSceneKeyInterpolation.LINEAR)
   assert ok
   q.set_range(0,end+1);unreal.EditorAssetLibrary.save_loaded_asset(s,False)
   unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(frame)
  if state['tick']==10:
   a=state['actor'];c=a.skeletal_mesh_component
   opt=unreal.AnimPoseEvaluationOptions();opt.optional_skeletal_mesh=mesh;opt.evaluation_type=unreal.AnimDataEvalType.RAW
   source=unreal.AnimPoseExtensions.get_anim_pose_at_time(unreal.load_asset(D+'/A_M4_DrumGrip_'+clip),frame/60,opt)
   errors={}
   for n in ['hand_l','hand_r','WPN_SOCKET_Magazine','index_03_l','thumb_03_l']:
    x=unreal.AnimPoseExtensions.get_bone_pose(source,n,unreal.AnimPoseSpaces.WORLD);y=c.get_socket_transform(n,unreal.RelativeTransformSpace.RTS_COMPONENT)
    errors[n]=x.translation.distance(y.translation)
   report[clip]={'sequence':s.get_path_name(),'frame':frame,'bone_error_cm':errors,'pass':max(errors.values())<.1}
   report[clip]['optimized_anim_node']=unreal.SystemLibrary.get_console_variable_int_value('ControlRig.EnableAnimNodePerformanceOptimizations')
   (O/'native_editable_verified.json').write_text(json.dumps(report,indent=2))
   assert report[clip]['pass'],errors
   if state['i']==0:state['i']=1;begin()
   else:
    center,extent=a.get_actor_bounds(False);delta=unreal.Vector(-80,50,20)
    unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).set_level_viewport_camera_info(center+delta,unreal.MathLibrary.find_look_at_rotation(center+delta,center))
    widget=unreal.get_editor_subsystem(unreal.EditorUtilitySubsystem).spawn_and_register_tab(unreal.load_asset('/Game/Locodrome/MAT/Locodrome_MAT'))
    widget.set_editor_property('SelectedControlRig',state['proxy']);state['widget']=widget
    report['widget']=widget.get_path_name();report['rig']=state['proxy'].control_rig.get_path_name()
    (O/'native_editable_verified.json').write_text(json.dumps(report,indent=2))
  if state['i']==1 and state['tick']==15:
   w=state['widget'];p=state['proxy']
   # MAT finger names already match the native FK rig. Adapt only wrist/arm buttons in this live editor tab.
   w.get_editor_property('btn_Hand_L').set_editor_property('ControlsToSelect',['hand_l_ctrl'])
   w.get_editor_property('btn_Hand_R').set_editor_property('ControlsToSelect',['hand_r_ctrl'])
   w.get_editor_property('index_02_l_ctrl').get_editor_property('btnSelect').on_clicked.broadcast()
   report['mat_selected_controls']=[str(n) for n in p.control_rig.current_control_selection()]
   report['body_type']=w.call_method('getControlRigType',(p.control_rig,))
   (O/'native_editable_verified.json').write_text(json.dumps(report,indent=2))
   unreal.log('DRUM_NATIVE_EDITABLE_PASS '+json.dumps(report));unreal.unregister_slate_post_tick_callback(handle)
 except Exception:
  (O/'native_editable_error.txt').write_text(traceback.format_exc());unreal.log_error(traceback.format_exc());unreal.unregister_slate_post_tick_callback(handle)
begin();handle=unreal.register_slate_post_tick_callback(tick)
