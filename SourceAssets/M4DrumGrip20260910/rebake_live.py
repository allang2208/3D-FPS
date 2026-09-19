import unreal
s=unreal.LevelSequenceEditorBlueprintLibrary.get_current_level_sequence()
b=s.get_bindings()[0];bid=unreal.MovieSceneObjectBindingID();bid.set_editor_property('Guid',b.get_id())
a=unreal.LevelSequenceEditorBlueprintLibrary.get_bound_objects(bid)[0];c=a.skeletal_mesh_component
p=unreal.ControlRigSequencerLibrary.get_control_rigs(s)[0]
print('RIG',p.control_rig.get_supported_events(),len(p.control_rig.get_hierarchy().get_controls()))
ok=unreal.ControlRigSequencerLibrary.load_anim_sequence_into_control_rig_section_with_range(p.track.get_sections()[0],unreal.load_asset('/Game/Weapons/M4DrumGripCandidate/A_M4_DrumGrip_reload_empty'),c,unreal.FrameNumber(0),False,unreal.FrameNumber(0),unreal.FrameNumber(162),key_reduce=False)
print('REBAKE',ok)
unreal.EditorAssetLibrary.save_loaded_asset(s,False)
unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(55)
