import unreal,json
from pathlib import Path
O=Path('D:/FPS3D/FPSGAME/SourceAssets/M4WrapGrip20260910');DEST='/Game/Weapons/M4WrapGripFinal'
mesh=unreal.load_asset('/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416');rig=unreal.load_asset('/Game/Weapons/M4ContactImpactFinal/CR_M4_ContactImpact');assert rig
rig.recompile_vm()
unreal.log('AUDIT_RIG_RECOMPILED')
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem);world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world();report={}
for clip,end in [('reload',1008),('reload_empty',1296),('equip_charge',304)]:
 seq=unreal.load_asset(DEST+'/LS_M4_WrapGrip_'+clip) or unreal.AssetToolsHelpers.get_asset_tools().create_asset('LS_M4_WrapGrip_'+clip,DEST,unreal.LevelSequence,unreal.LevelSequenceFactoryNew());assert seq
 for old_binding in seq.get_bindings():old_binding.remove()
 seq.set_display_rate(unreal.FrameRate(480,1));seq.set_playback_start(0);seq.set_playback_end(end+1);assert unreal.EditorAssetLibrary.save_loaded_asset(seq,False);assert unreal.LevelSequenceEditorBlueprintLibrary.open_level_sequence(seq)
 actor=actors.spawn_actor_from_class(unreal.SkeletalMeshActor,unreal.Vector(0,0,100));comp=actor.skeletal_mesh_component;comp.set_skeletal_mesh_asset(mesh);actor.set_actor_label('M4 Reload Polish '+clip)
 binding=seq.add_spawnable_from_instance(actor);track=unreal.ControlRigSequencerLibrary.find_or_create_control_rig_track(world,seq,rig.get_control_rig_class(),binding,False)
 spawn=binding.add_track(unreal.MovieSceneSpawnTrack);section=spawn.add_section();section.set_range(0,end+1)
 for channel in section.get_all_channels():channel.set_default(True)
 sections=track.get_sections();section=sections[0] if sections else track.add_section();section.set_range(0,end+1)
 unreal.log('AUDIT_SECTION_CHANNELS '+str(len(section.get_all_channels())))
 anim=unreal.load_asset('/Game/Weapons/M4WrapGripFinal/A_M4_HK416_'+clip);assert anim.get_editor_property("number_of_sampled_keys")==end+1
 ok=unreal.ControlRigSequencerLibrary.load_anim_sequence_into_control_rig_section_with_range(section,anim,comp,unreal.FrameNumber(0),False,unreal.FrameNumber(0),unreal.FrameNumber(end),key_reduce=False,interpolation=unreal.MovieSceneKeyInterpolation.LINEAR);assert ok
 unreal.EditorAssetLibrary.save_loaded_asset(seq,False);unreal.LevelSequenceEditorBlueprintLibrary.close_level_sequence();actors.destroy_actor(actor);report[clip]={'sequence':seq.get_path_name(),'baked':ok,'fps':480,'source_duration':end/480,'runtime_duration':.72 if clip=='equip_charge' else end/480}
unreal.LevelSequenceEditorBlueprintLibrary.close_level_sequence()
(O/'mat_sequences.json').write_text(json.dumps(report,indent=2));unreal.log('M4_POLISH_MAT_SEQUENCES_PASS')

unreal.SystemLibrary.quit_editor()
