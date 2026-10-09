"""Apply the ecology revision through the existing editor's mutually exclusive bridge."""
from pathlib import Path
import json
import unreal as u
ROOT=Path(__file__).resolve().parents[1]
if Path(u.Paths.project_dir()).resolve()!=ROOT.parents[1].resolve():raise RuntimeError('Wrong project')
ed=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if not ed:raise RuntimeError('Editor host required')
if ed.get_game_world():raise RuntimeError('PIE has not ended; keep map installation pending')
dirty_maps=[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
dirty_ecology=[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if p.get_path_name().startswith('/Game/Dungeons/Ecology20261004/')]
if dirty_maps or dirty_ecology:raise RuntimeError('Preserve unsaved editor content: '+str(dirty_maps+dirty_ecology))
world=ed.get_editor_world();previous=world.get_path_name().split('.')[0] if world else None
script=ROOT/'Scripts/install_v7_patch.py'
exec(compile(script.read_text('utf8'),str(script),'exec'),dict(__file__=str(script),__name__='__main__',ECOLOGY_EDITOR_BATCH=True))
receipt=ROOT/'Receipts/install-v7.json';data=json.loads(receipt.read_text('utf8'))
data.update(operation_host='existing_editor_bridge',editor_started_by_task=False,restored_editor_map=previous)
receipt.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
if previous:u.EditorLoadingAndSavingUtils.load_map(previous)
print('ECOLOGY_V7_EXISTING_EDITOR_SAVED')
