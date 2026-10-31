from pathlib import Path
import runpy,json,unreal as u
R=Path(__file__).resolve().parent
ed=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if ed and ed.get_game_world():raise RuntimeError('Wait for the requested end of play before reflection authoring')
if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved map')
runpy.run_path(str(R.parents[2]/'SourceAssets/CyberpunkNearBank20261028/publish_reflection.py'),run_name='__main__')
native=json.loads((R.parent/'installed.json').read_text());reflection=json.loads((R.parents[2]/'SourceAssets/CyberpunkNearBank20261028/installed.json').read_text())
native.update(repair='20261028-v1',reflection=reflection['reflection'],reflection_texture=reflection['reflection_texture'],repair_backup=json.loads((R/'repair_backup.json').read_text())['backup'])
(R/'published.json').write_text(json.dumps(native,indent=2));(R.parent/'installed.json').write_text(json.dumps(native,indent=2))
