import unreal,json
from pathlib import Path
dest='/Game/Weapons/M4DrumGripCandidate'
seq=unreal.load_asset(dest+'/LS_DrumGrip_FKCheck')
if not seq:seq=unreal.AssetToolsHelpers.get_asset_tools().create_asset('LS_DrumGrip_FKCheck',dest,unreal.LevelSequence,unreal.LevelSequenceFactoryNew())
seq.set_display_rate(unreal.FrameRate(60,1));seq.set_playback_start(0);seq.set_playback_end(163)
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem);world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
actor=actors.spawn_actor_from_class(unreal.SkeletalMeshActor,unreal.Vector(0,0,100));comp=actor.skeletal_mesh_component;comp.set_skeletal_mesh_asset(unreal.load_asset(dest+'/SK_M4_DrumGripPreview'))
b=seq.add_spawnable_from_instance(actor)
t=unreal.ControlRigSequencerLibrary.find_or_create_control_rig_track(world,seq,unreal.FKControlRig,b,False)
q=t.get_sections()[0];q.set_range(0,163)
ok=unreal.ControlRigSequencerLibrary.load_anim_sequence_into_control_rig_section_with_range(q,unreal.load_asset(dest+'/A_M4_DrumGrip_reload_empty'),comp,unreal.FrameNumber(0),False,unreal.FrameNumber(0),unreal.FrameNumber(162),key_reduce=False)
actors.destroy_actor(actor)
unreal.EditorAssetLibrary.save_loaded_asset(seq,False)
unreal.LevelSequenceEditorBlueprintLibrary.close_level_sequence();unreal.LevelSequenceEditorBlueprintLibrary.open_level_sequence(seq);unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(54)
print('NATIVE_FK_BAKED',ok)
