"""Use the existing AKM-only importer with this revision's FBX and receipt path."""
from pathlib import Path
import json
import unreal as u

OUT = Path(__file__).resolve().parent
script = (OUT.parent / 'import_asset.py').read_text(encoding='utf-8')
exec(compile(script, str(OUT.parent / 'import_asset.py'), 'exec'), {'__file__': str(OUT / 'import_asset.py'), '__name__': '__main__'})

# This close-up mesh has much smaller bevels than the previous revision. Rebuild
# its tangent frame and retain full precision UVs instead of inherited import
# buffers that can collapse the fine channel and countersink coordinates.
mesh = u.load_asset('/Game/Weapons/AKMIntegration/SovietFab/GripErgonomic/SM_AKM_angled')
editor = u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
settings = editor.get_lod_build_settings(mesh, 0)
settings.set_editor_property('recompute_normals', False)
settings.set_editor_property('recompute_tangents', True)
settings.set_editor_property('use_mikk_t_space', True)
settings.set_editor_property('use_full_precision_u_vs', True)
settings.set_editor_property('use_high_precision_tangent_basis', True)
u.log('AKM_RESONANCE_POLISH_BUILD_PRECISION')
editor.set_lod_build_settings(mesh, 0, settings)
if not u.EditorAssetLibrary.save_loaded_asset(mesh, False):
    raise RuntimeError('Polished AKM mesh build settings could not be saved')
receipt = json.loads((OUT / 'import_receipt.json').read_text(encoding='utf-8'))
receipt['full_precision_uvs'] = True
receipt['high_precision_tangent_basis'] = True
receipt['recompute_tangents'] = True
(OUT / 'import_receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
u.log('AKM_RESONANCE_POLISH_IMPORTED ' + mesh.get_path_name())
