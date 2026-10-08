"""Rebuild and save the V3 garment mapping without reimporting motion/corpse."""
from pathlib import Path
import json
import unreal as u

out = Path('D:/FPS3D/FPSGAME/SourceAssets/BoundCongregateMeshy20261006/RigRepairV3')
u.SystemLibrary.execute_console_command(None, 'Editor.AsyncSkinnedAssetCompilation 0')
mesh = u.load_asset('/Game/Monsters/BoundCongregate/RigV3/SK_BoundCongregate_RigV3')
if not mesh or not u.BoundCongregate.build_garment_simulation(mesh):
    raise RuntimeError('V3 garment mapping rebuild failed')
u.SystemLibrary.execute_console_command(None, 'Editor.AsyncSkinnedAssetCompilationFinishAll')
u.EditorAssetLibrary.set_metadata_tag(mesh, 'GarmentBindingVersion', 'V3-linear-backstop')
if not u.EditorAssetLibrary.save_loaded_asset(mesh, False):
    raise RuntimeError('V3 garment mapping save failed')
(out / 'cloth_mapping_save.json').write_text(json.dumps({
    'saved': True, 'mesh': mesh.get_path_name(),
    'change': 'four scoped mappings, linear vertex-color travel, skin-relative backstop contacts'
}, indent=2), encoding='utf-8')
print('BOUND_CONGREGATE_CLOTH_MAPPING_SAVED', flush=True)
