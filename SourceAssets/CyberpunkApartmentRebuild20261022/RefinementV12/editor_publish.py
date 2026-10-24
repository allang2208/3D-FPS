"""One existing-editor batch; keep play sessions and unrelated unsaved maps intact."""
from pathlib import Path
import unreal as u,json,runpy
R=Path(__file__).resolve().parent;s=u.get_editor_subsystem(u.UnrealEditorSubsystem)
playing=bool(s.get_game_world())
if playing:raise RuntimeError('AP12 pending: stop play and save before publication.')
world=s.get_editor_world();current=world.get_path_name().split('.')[0] if world else ''
dirty=[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
(R/'editor-publish-state.json').write_text(json.dumps(dict(current_map=current,dirty_maps=dirty,play_world=playing),indent=2),encoding='utf8')
if dirty:raise RuntimeError('AP12 preserves unsaved map edits: '+str(dirty))
try:runpy.run_path(str(R/'publish.py'),run_name='__main__')
finally:
 world=s.get_editor_world()
 if current.startswith('/Game/') and world and world.get_path_name().split('.')[0]!=current and not u.EditorLoadingAndSavingUtils.get_dirty_map_packages():u.EditorLoadingAndSavingUtils.load_map(current)
print('AP12_ASSETS_AND_MAP_SAVED')
