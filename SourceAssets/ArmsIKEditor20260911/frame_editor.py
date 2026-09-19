import unreal,json
from pathlib import Path
E=unreal.LevelSequenceEditorBlueprintLibrary;seq=E.get_current_level_sequence()
assert seq.get_name()=='LS_M4_Vertical_Idle_IK_Edit'
arm=next(b for b in seq.get_bindings() if any(isinstance(t,unreal.MovieSceneControlRigParameterTrack) for t in b.get_tracks()))
section=arm.add_track(unreal.MovieScene3DTransformTrack).add_section();section.set_range(0,360)
for ch,v in zip(section.get_all_channels(),[2000,0,150,0,0,0,1,1,1]):ch.set_default(v)
E.refresh_current_level_sequence();E.set_current_time(0)
unreal.EditorAssetLibrary.save_loaded_asset(seq,False)
rig=unreal.ControlRigSequencerLibrary.get_control_rigs(seq)[0].control_rig
rig.select_control('hand_l_ik_ctrl',True)
center=unreal.Vector(2000,-30,135);cam=center+unreal.Vector(65,-65,25)
unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).set_level_viewport_camera_info(cam,unreal.MathLibrary.find_look_at_rotation(cam,center))
