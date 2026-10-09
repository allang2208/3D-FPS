from pathlib import Path
import json,os
import unreal as u
ROOT=Path(__file__).resolve().parents[1]
if Path(u.Paths.project_dir()).resolve()!=ROOT.parents[1].resolve():raise RuntimeError('Wrong project')
ed=u.get_editor_subsystem(u.UnrealEditorSubsystem)
world=ed.get_editor_world() if ed else None;game=ed.get_game_world() if ed else None
data=dict(process=os.getpid(),project=u.Paths.project_dir(),world=world.get_path_name() if world else None,playing=bool(game),game_world=game.get_path_name() if game else None,
    dirty_maps=[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()],
    dirty_ecology=[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if p.get_path_name().startswith('/Game/Dungeons/Ecology20261004/')])
(ROOT/'Receipts/editor-context-v3.json').write_text(json.dumps(data,indent=2),encoding='utf8')
print('ECOLOGY_EDITOR_CONTEXT '+json.dumps(data))
