"""Save the mesh already reimported by import_mesh.py; do not reimport again."""
from pathlib import Path
import json
import unreal as u
mesh = u.load_asset('/Game/Weapons/SpellbookEvildeer20261009/PagesV1/Meshes/SK_Spellbook_Alchemy_16Pages')
if not u.EditorAssetLibrary.save_loaded_asset(mesh, only_if_is_dirty=False):
    raise RuntimeError('The UV-corrected mesh has not been saved')
receipt = dict(saved=True, mesh=mesh.get_path_name(), rotated_degrees=180,
    skeleton=mesh.skeleton.get_path_name(), material_assets_modified=False,
    texture_assets_modified=False, animation_assets_modified=False, runtime_tested=False)
Path('D:/FPS3D/FPSGAME/SourceAssets/SpellbookEvildeer20261009/PagesV1/OrientationV2/import-receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('SPELLBOOK_PAGE_ORIENTATION_SAVED '+json.dumps(receipt))
