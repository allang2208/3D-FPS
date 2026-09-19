import unreal,json
from pathlib import Path
O=Path('D:/FPS3D/FPSGAME/SourceAssets/M4DrumGrip20260910');DEST='/Game/Weapons/M4DrumGripCandidate'
mesh=unreal.load_asset(DEST+'/SK_M4_DrumGripPreview');rig=unreal.load_asset(DEST+'/CR_M4_DrumGrip_MAT');assert mesh and rig
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem);world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
report={}
for clip,end in [('reload',126),('reload_empty',162)]:
 seq=unreal.AssetToolsHelpers.get_asset_tools().create_asset('LS_M4_DrumGrip_'+clip,DEST,unreal.LevelSequence,unreal.LevelSequenceFactoryNew())
 if not seq:seq=unreal.load_asset(DEST+'/LS_M4_DrumGrip_'+clip)
 seq.set_display_rate(unreal.FrameRate(60,1));seq.set_playback_start(0);seq.set_playback_end(end+1)
 actor=actors.spawn_actor_from_class(unreal.SkeletalMeshActor,unreal.Vector(0,0,100));comp=actor.skeletal_mesh_component;comp.set_skeletal_mesh_asset(mesh);actor.set_actor_label('M4 Drum Grip '+clip)
 binding=seq.add_spawnable_from_instance(actor)
 track=unreal.ControlRigSequencerLibrary.find_or_create_control_rig_track(world,seq,rig.get_control_rig_class(),binding,False)
 sections=track.get_sections();section=sections[0] if sections else track.add_section();section.set_range(0,end+1)
 # Bake against the initialized Sequencer spawnable, not the temporary source actor.
 unreal.LevelSequenceEditorBlueprintLibrary.open_level_sequence(seq)
 unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(0)
 bid=unreal.MovieSceneObjectBindingID();bid.set_editor_property('Guid',binding.get_id())
 bound=unreal.LevelSequenceEditorBlueprintLibrary.get_bound_objects(bid)
 assert bound,'Sequencer spawnable must exist before baking'
 comp=bound[0].skeletal_mesh_component
 anim=unreal.load_asset(DEST+'/A_M4_DrumGrip_'+clip)
 ok=unreal.ControlRigSequencerLibrary.load_anim_sequence_into_control_rig_section_with_range(section,anim,comp,unreal.FrameNumber(0),False,unreal.FrameNumber(0),unreal.FrameNumber(end),key_reduce=False,interpolation=unreal.MovieSceneKeyInterpolation.LINEAR)
 assert ok
 section.set_range(0,end+1)
 unreal.EditorAssetLibrary.save_loaded_asset(seq,False);actors.destroy_actor(actor)
 rigs=unreal.ControlRigSequencerLibrary.get_control_rigs(seq)
 report[clip]={'sequence':seq.get_path_name(),'rig_count':len(rigs),'bake_success':ok,'frames':end+1}
(O/'sequence_report.json').write_text(json.dumps(report,indent=2));unreal.log('MAT_SEQUENCE_BUILD_PASS')
