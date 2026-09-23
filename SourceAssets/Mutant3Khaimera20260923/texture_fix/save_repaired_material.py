"""Finish the known in-memory repair after an editor save was refused."""
import unreal as u,json
from pathlib import Path
ROOT=Path(__file__).parent
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_end_play()
    u.log('MUTANT3_MATERIAL_WAITING_FOR_PIE_END; repaired graph remains in memory')
else:
    asset='/Game/Monsters/Mutant3Meshy/Materials/M_Mutant3_Meshy'
    mat=u.load_asset(asset)
    front=u.MaterialEditingLibrary.get_material_property_input_node(mat,u.MaterialProperty.MP_FRONT_MATERIAL)
    if not isinstance(front,u.MaterialExpressionSubstrateShadingModels):raise RuntimeError('Known repair is not present')
    if not u.EditorAssetLibrary.save_loaded_asset(mat,False):raise RuntimeError('Material save still refused')
    state=json.loads((ROOT/'material_repair_state.json').read_text())
    state['state']='installed and saved in active production editor'
    state['game_started']=False
    (ROOT/'material_repair_state.json').write_text(json.dumps(state,indent=2),encoding='utf-8')
    u.log('MUTANT3_MATERIAL_INSTALLED 1 material; saved existing repaired graph')
