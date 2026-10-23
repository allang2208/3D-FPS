"""Save the rune HUD's soft floating lights as one UI material, without changing shared HUDs."""
import json
from pathlib import Path
import unreal as u

P = Path(__file__).resolve().parent
ROOT = P.parents[2]
DEST = '/Game/Weapons/RuneboundWarhammer20261022/HudMotesV2'
DONOR = '/Game/Weapons/RuneboundWarhammer20261022/PassiveV1/M_RuneboundEnergyHud'
TAG, OWNER = 'RuneboundHudMotesOwner', 'RuneboundHudMotesV2_20261023'
E, L, A = u.EditorAssetLibrary, u.MaterialEditingLibrary, u.AssetToolsHelpers.get_asset_tools()
if Path(u.Paths.project_dir()).resolve() not in (ROOT, P/'AuthorHost'):
    raise RuntimeError('Wrong HUD authoring project')
path = DEST+'/M_RuneboundEnergyHud'
if any(str(pkg.get_name()) == path for pkg in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    raise RuntimeError('Preserve dirty material '+path)
mat = u.load_asset(path) if E.does_asset_exist(path) else None
if mat and E.get_metadata_tag(mat, TAG) != OWNER:
    raise RuntimeError('Preserve unowned material '+path)
if not mat:
    source = u.load_asset(DONOR)
    if not source:
        raise RuntimeError('Missing rune HUD donor')
    mat = A.duplicate_asset('M_RuneboundEnergyHud', DEST, source)
if not mat:
    raise RuntimeError('HUD material creation failed')
custom = next(n for n in L.get_material_expressions(mat) if isinstance(n, u.MaterialExpressionCustom))
shader = P.parent/'PassiveV1/RuneboundEnergyHud.hlsl'
custom.set_editor_property('code', shader.read_text(encoding='utf-8'))
custom.set_editor_property('description', 'Blue glass and rune ribbon; gathering fireflies and rising soft motes; no floating crystals or centre gem')
if L.recompile_material(mat):
    raise RuntimeError('Rune HUD material compile failed')
E.set_metadata_tag(mat, TAG, OWNER)
E.set_metadata_tag(mat, 'SourceAuthoring', 'RuneboundWarhammer20261022/HudMotesV2')
if not E.save_loaded_asset(mat, False):
    raise RuntimeError('Rune HUD material save failed')
receipt = {
    'complete': True, 'asset': mat.get_path_name(), 'source': str(shader.relative_to(ROOT)),
    'author_project': u.Paths.project_dir(), 'material_domain': 'UI',
    'analytic_motes': 32, 'gathering_motes': 10, 'rising_motes': 22,
    'floating_crystal_shapes': 0, 'centre_gem': False,
    'tests_run': False, 'rendered_acceptance': False, 'game_started': False,
}
(P/'import_receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
print('RUNEBOUND_HUD_MOTES_SAVED '+json.dumps(receipt))
