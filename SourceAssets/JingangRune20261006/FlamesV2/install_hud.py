"""Update and save only the existing Jingang scripture HUD custom shader."""
from pathlib import Path
import hashlib
import json
import shutil
import unreal as u

P = Path(__file__).resolve().parent
ROOT = P.parents[2]
ASSET = '/Game/Weapons/XuanChiZhenYue20261004/JingangRune20261006/Materials/M_JingangSutraHud'
E, L = u.MaterialEditingLibrary, u.EditorAssetLibrary
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
        raise RuntimeError('Exit PIE before saving the scripture material.')
mat = u.load_asset(ASSET)
if not mat:
    raise RuntimeError('Existing scripture material is missing: ' + ASSET)
nodes = [n for n in E.get_material_expressions(mat)
         if isinstance(n, u.MaterialExpressionCustom)
         and 'SutraSampler' in n.get_editor_property('code')
         and 'PreviousState' in n.get_editor_property('code')]
if len(nodes) != 1:
    raise RuntimeError('Expected the existing single scripture custom expression.')

before = P / 'Before'
before.mkdir(exist_ok=True)
package = ROOT / 'Content' / (ASSET.removeprefix('/Game/') + '.uasset')
if not (before / package.name).exists():
    shutil.copy2(package, before / package.name)
    (before / 'asset-custom-code.hlsl').write_text(nodes[0].get_editor_property('code'), encoding='utf-8')
source = P.parent / 'sutra_hud.hlsl'
nodes[0].set_editor_property('code', source.read_text(encoding='utf-8'))
nodes[0].set_editor_property('desc', 'JingangSutra_GoldenFlamesV2')
errors = E.recompile_material(mat)
if errors:
    raise RuntimeError('Scripture material compilation failed: ' + str(errors))
L.set_metadata_tag(mat, 'JingangHudRevision', 'GoldenFlamesV2-20261006')
if not u.EditorLoadingAndSavingUtils.save_packages([mat.get_outermost()], False):
    raise RuntimeError('Could not save scripture flames material.')
receipt = {
    'complete': True,
    'saved_assets': [mat.get_path_name()],
    'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
    'revision': 'GoldenFlamesV2-20261006',
    'runtime_tested': False,
    'render_previewed': False,
    'native_changes': False,
}
(P / 'install-receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print('JINGANG_GOLDEN_FLAMES_SAVED ' + mat.get_path_name(), flush=True)
