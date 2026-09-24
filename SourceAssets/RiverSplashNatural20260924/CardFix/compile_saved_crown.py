"""Compile the final saved graph in isolation, without intermediate authoring states."""
import json
from pathlib import Path
import unreal as u

root=Path(u.Paths.project_dir())/'SourceAssets/RiverSplashNatural20260924'
m=u.load_asset('/Game/Fluids/RiverPilot20260923/M_RiverCrown')
errors=list(u.MaterialEditingLibrary.recompile_material(m))
report={'material':m.get_path_name(),'errors':errors,'platform':'PCD3D_SM6','loaded_from_saved_asset':True}
(root/'CardFix/saved-material-compile.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
if errors:raise RuntimeError(str(errors))
if not u.EditorLoadingAndSavingUtils.save_packages([m.get_outermost()],False):raise RuntimeError('Save failed')
u.log('RIVER_SAVED_CROWN_COMPILED '+json.dumps(report))
