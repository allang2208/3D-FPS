"""Read the existing editor context needed to update the four shared material entries."""
import json
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[1];cfg=json.loads((ROOT/'Config/material-candidates.json').read_text())
ue=u.get_editor_subsystem(u.UnrealEditorSubsystem)
out={'world':str(ue.get_editor_world()),'game':str(ue.get_game_world()),
     'dirty_content':[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()],
     'dirty_maps':[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()],
     'assets':{},'api':{}}
for path in cfg['candidates']:
    m=u.load_asset(path)
    out['assets'][path]={'class':m.get_class().get_name(),'parent':m.get_base_material().get_path_name()}
for name in ['clear_all_material_instance_parameters','get_material_instance_scalar_parameter_value','get_material_instance_vector_parameter_value','get_material_instance_texture_parameter_value']:
    out['api'][name]=str(getattr(u.MaterialEditingLibrary,name).__doc__)
(ROOT/'Receipts/promotion-context.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print('WALL_PROMOTION_CONTEXT',out['world'],out['game'],'dirty',out['dirty_content'],out['dirty_maps'],flush=True)
