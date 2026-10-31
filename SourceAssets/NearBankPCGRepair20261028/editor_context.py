from pathlib import Path
import json,unreal as u
R=Path(__file__).resolve().parent
ed=u.get_editor_subsystem(u.UnrealEditorSubsystem)
w=ed.get_editor_world();g=ed.get_game_world()
d={'world':w.get_path_name() if w else None,'game':g.get_path_name() if g else None,'dirty_maps':[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()],'offline_pcg_helper_available':hasattr(u,'NearBankPCGAuthoringTools'),'pcg_primitives_exists':u.EditorAssetLibrary.does_asset_exist('/PCGPrimitives/Primitives/Assign/Assign_ShapeGrammarDefinition')}
(R/'editor_context.json').write_text(json.dumps(d,indent=2),encoding='utf8');print('PCG_EDITOR_CONTEXT',d)
