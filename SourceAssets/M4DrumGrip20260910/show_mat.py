import unreal,json
from pathlib import Path
O=Path('D:/FPS3D/FPSGAME/SourceAssets/M4DrumGrip20260910')
unreal.EditorPythonScripting.set_keep_python_script_alive(True)
seq=unreal.load_asset('/Game/Weapons/M4DrumGripCandidate/LS_M4_DrumGrip_reload_empty')
unreal.LevelSequenceEditorBlueprintLibrary.open_level_sequence(seq)
unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(54)
widget=unreal.get_editor_subsystem(unreal.EditorUtilitySubsystem).spawn_and_register_tab(unreal.load_asset('/Game/Locodrome/MAT/Locodrome_MAT'))
rigs=unreal.ControlRigSequencerLibrary.get_control_rigs(seq)
report={'widget':widget.get_path_name(),'rigs':[p.control_rig.get_name() for p in rigs]}
for n in ['SelectedControlRig','ControlRigType']:
 try:report[n]=str(widget.get_editor_property(n))
 except Exception as e:report[n]=str(e)
(O/'mat_live_report.json').write_text(json.dumps(report,indent=2))
unreal.log('MAT_LIVE_PREVIEW_READY '+json.dumps(report))
