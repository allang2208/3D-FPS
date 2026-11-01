import unreal as u,json
from pathlib import Path
O=Path(__file__).resolve().parent
sub=u.get_editor_subsystem(u.UnrealEditorSubsystem)
world=sub.get_game_world() if sub else None
R={'game_world':world.get_path_name() if world else None,'dirty':[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()]}
(O/'publication_state.json').write_text(json.dumps(R,indent=2),encoding='utf-8')
print(json.dumps({'game_world':R['game_world'],'owned_dirty':[p for p in R['dirty'] if '/Weapons/M24/' in p]}),flush=True)
