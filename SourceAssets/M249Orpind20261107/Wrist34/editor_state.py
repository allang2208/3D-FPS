import unreal as u,json
from pathlib import Path
paths=set(json.loads((Path(__file__).resolve().parent.parent/'Wrist33/Followup/state.json').read_text())['saved_hashes'])
result=dict(pie=u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor(),dirty_task_assets=[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if p.get_path_name() in paths])
print('M249_EDITOR_STATE',json.dumps(result))
(Path(__file__).resolve().parent/'editor_state.json').write_text(json.dumps(result,indent=2))
