import unreal,json
from pathlib import Path
O=Path(__file__).resolve().parent;DEST='/Game/Weapons/M4HandMATRepair'
mesh=unreal.load_asset('/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416');assert mesh
skel=mesh.skeleton;report={}
for clip,end in [('reload',126),('reload_empty',162),('equip_charge',38),('drum_reload',126),('drum_reload_empty',162)]:
 name='A_M4_MAT_'+clip
 o=unreal.FbxImportUI();o.automated_import_should_detect_type=False;o.mesh_type_to_import=unreal.FBXImportType.FBXIT_ANIMATION;o.skeleton=skel;o.import_materials=False;o.import_textures=False;o.import_mesh=False;o.import_animations=True;o.create_physics_asset=False
 o.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False);o.anim_sequence_import_data.set_editor_property('custom_sample_rate',60)
 t=unreal.AssetImportTask();t.filename=str(O/(name+'.fbx'));t.destination_path=DEST;t.destination_name=name;t.automated=True;t.replace_existing=True;t.save=True;t.options=o
 unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t]);a=unreal.load_asset(DEST+'/'+name);assert a
 a.set_editor_property('bone_compression_settings',unreal.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel'));unreal.EditorAssetLibrary.save_loaded_asset(a,False)
 assert abs(a.get_play_length()-end/60)<1e-4
 opt=unreal.AnimPoseEvaluationOptions();opt.optional_skeletal_mesh=mesh;err=0
 for f in range(end*2+1):
  opt.evaluation_type=unreal.AnimDataEvalType.RAW;raw=unreal.AnimPoseExtensions.get_anim_pose_at_time(a,f/120,opt)
  opt.evaluation_type=unreal.AnimDataEvalType.COMPRESSED;packed=unreal.AnimPoseExtensions.get_anim_pose_at_time(a,f/120,opt)
  for n in ['hand_l','hand_r','index_03_l','middle_03_l','thumb_03_l','lowerarm_twist_01_l','WPN_ChargingHandle','WPN_SOCKET_Magazine']:
   a1=unreal.AnimPoseExtensions.get_bone_pose(raw,n,unreal.AnimPoseSpaces.WORLD);a2=unreal.AnimPoseExtensions.get_bone_pose(packed,n,unreal.AnimPoseSpaces.WORLD);err=max(err,a1.translation.distance(a2.translation))
 assert err<.05
 report[clip]={'asset':a.get_path_name(),'duration':a.get_play_length(),'compressed_position_error_cm':err}
rig=unreal.load_asset(DEST+'/CR_M4_Hand_MAT') or unreal.AssetToolsHelpers.get_asset_tools().duplicate_asset('CR_M4_Hand_MAT',DEST,unreal.load_asset('/Game/Weapons/M4DrumGripCandidate/CR_M4_DrumGrip_MAT'));assert rig
rig.set_preview_mesh(mesh);unreal.EditorAssetLibrary.save_loaded_asset(rig,False)
(O/'import_report.json').write_text(json.dumps(report,indent=2))
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem);world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
for clip,end in [('reload',126),('reload_empty',162),('equip_charge',38)]:
 seq=unreal.load_asset(DEST+'/LS_M4_Hand_'+clip) or unreal.AssetToolsHelpers.get_asset_tools().create_asset('LS_M4_Hand_'+clip,DEST,unreal.LevelSequence,unreal.LevelSequenceFactoryNew());assert seq
 for oldbinding in seq.get_bindings():oldbinding.remove()
 seq.set_display_rate(unreal.FrameRate(60,1));seq.set_playback_start(0);seq.set_playback_end(end+1)
 actor=actors.spawn_actor_from_class(unreal.SkeletalMeshActor,unreal.Vector(0,0,100));comp=actor.skeletal_mesh_component;comp.set_skeletal_mesh_asset(mesh);actor.set_actor_label('M4 Hand Repair '+clip)
 binding=seq.add_spawnable_from_instance(actor);track=unreal.ControlRigSequencerLibrary.find_or_create_control_rig_track(world,seq,rig.get_control_rig_class(),binding,False)
 spawn=binding.add_track(unreal.MovieSceneSpawnTrack);spawnsection=spawn.add_section();spawnsection.set_range(0,end+1)
 for channel in spawnsection.get_all_channels():channel.set_default(True)
 sections=track.get_sections();section=sections[0] if sections else track.add_section();section.set_range(0,end+1)
 ok=unreal.ControlRigSequencerLibrary.load_anim_sequence_into_control_rig_section_with_range(section,unreal.load_asset(DEST+'/A_M4_MAT_'+clip),comp,unreal.FrameNumber(0),False,unreal.FrameNumber(0),unreal.FrameNumber(end),key_reduce=False,interpolation=unreal.MovieSceneKeyInterpolation.LINEAR);assert ok
 unreal.EditorAssetLibrary.save_loaded_asset(seq,False);actors.destroy_actor(actor);report[clip]['sequence']=seq.get_path_name();report[clip]['bake_success']=ok
(O/'import_report.json').write_text(json.dumps(report,indent=2));unreal.log('M4_HAND_MAT_IMPORT_PASS')
unreal.EditorPythonScripting.set_keep_python_script_alive(True)
seq=unreal.load_asset(DEST+'/LS_M4_Hand_reload_empty');unreal.LevelSequenceEditorBlueprintLibrary.open_level_sequence(seq);unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(130)
widget=unreal.get_editor_subsystem(unreal.EditorUtilitySubsystem).spawn_and_register_tab(unreal.load_asset('/Game/Locodrome/MAT/Locodrome_MAT'))
(O/'mat_widget_api.json').write_text(json.dumps({'widget':widget.get_path_name(),'methods':[n for n in dir(widget) if any(w in n.lower() for w in ['rig','key','hand','finger','select','refresh','tween'])]},indent=2))
unreal.log('MAT_HAND_EDITOR_READY')
import traceback
state={'ticks':0,'last':''}
def tick(dt):
 try:
  state['ticks']+=1
  if state['ticks']==10:
   proxy=unreal.ControlRigSequencerLibrary.get_control_rigs(seq)[0];widget.set_editor_property('SelectedControlRig',proxy)
   from editor_toolset.toolsets.blueprint import BlueprintTools
   details={'widget':widget.get_path_name(),'rig':proxy.control_rig.get_path_name(),'type':str(widget.call_method('getControlRigType',(proxy.control_rig,))),'functions':str(BlueprintTools.list_functions(unreal.load_asset('/Game/Locodrome/MAT/Locodrome_MAT')))}
   details['button_functions']=str(BlueprintTools.list_functions(unreal.load_asset('/Game/Locodrome/MAT/Interface/WBP_CharPickerButtonBase')))
   (O/'mat_live.json').write_text(json.dumps(details,indent=2))
  queue=O/'editor_queue.py'
  if queue.exists():
   stamp=str(queue.stat().st_mtime_ns)
   if stamp!=state['last']:
    state['last']=stamp;exec(compile(queue.read_text(encoding='utf-8-sig'),str(queue),'exec'),globals());(O/'queue_done.txt').write_text(stamp)
 except Exception:
  (O/'editor_queue_error.txt').write_text(traceback.format_exc())
handle=unreal.register_slate_post_tick_callback(tick)
