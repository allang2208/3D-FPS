import unreal as u,json
from pathlib import Path
O=Path(__file__).parent
state={'content':[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()],'maps':[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()],'pie':bool(u.EditorLevelLibrary.get_game_world())}
(O/'build_state.json').write_text(json.dumps(state,indent=2));print(json.dumps(state))
