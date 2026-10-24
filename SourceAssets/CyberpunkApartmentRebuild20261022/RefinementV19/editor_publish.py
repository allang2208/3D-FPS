from pathlib import Path
import unreal as u,runpy,json
R=Path(__file__).resolve().parent
sub=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if sub and sub.get_game_world():
 print(json.dumps(dict(stage='waiting_for_stop_and_save',reason='Active game world is preserved')))
elif u.EditorLoadingAndSavingUtils.get_dirty_map_packages():
 print(json.dumps(dict(stage='waiting_for_save',reason='Unsaved map packages are preserved')))
else:
 runpy.run_path(str(R/'publish.py'),run_name='__main__')
 print((R/'completed.json').read_text())
