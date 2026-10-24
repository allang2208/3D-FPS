"""Single mutually exclusive batch, retaining the user's current saved map."""
import unreal as u,json,runpy
from pathlib import Path
R=Path(__file__).resolve().parent
s=u.get_editor_subsystem(u.UnrealEditorSubsystem);world=s.get_editor_world();current=world.get_path_name().split('.')[0] if world else ''
state=dict(current_map=current,play_world=bool(s.get_game_world()),dirty_maps=[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()])
(R/'editor_state.json').write_text(json.dumps(state,indent=2),encoding='utf8')
if state['play_world']:raise RuntimeError('Preserve active play session; stop play before scene authoring.')
if state['dirty_maps']:raise RuntimeError('Preserve unsaved map edits: '+str(state['dirty_maps']))
try:
 runpy.run_path(str(R/'publish.py'),run_name='__main__')
finally:
 current_world=s.get_editor_world()
 if current.startswith('/Game/') and current_world and current_world.get_path_name().split('.')[0]!=current and not u.EditorLoadingAndSavingUtils.get_dirty_map_packages():u.EditorLoadingAndSavingUtils.load_map(current)
print('AP9_EDITOR_PUBLICATION_FINISHED')
