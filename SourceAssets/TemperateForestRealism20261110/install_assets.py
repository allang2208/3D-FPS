"""Author only the current hills ground and its local foliage settings."""
import json
import runpy
import shutil
from datetime import datetime
from pathlib import Path
import unreal as u

PROJECT = Path('D:/FPS3D/FPSGAME')
ROOT = PROJECT / 'SourceAssets/TemperateForestRealism20261110'
BASE = '/Game/WorldGeneration/TemperateHills'
DA_PATH = BASE + '/DA_TemperateHillsStreaming'
owned = {BASE + '/M_TemperateGround', BASE + '/PebbleShore/M_PebbleShoreGround', DA_PATH}
if Path(u.Paths.project_dir()).resolve() != PROJECT.resolve():
    raise RuntimeError('Wrong project')
dirty = u.EditorLoadingAndSavingUtils.get_dirty_content_packages()
conflicts = [p.get_name() for p in dirty if p.get_name() in owned]
if conflicts:
    raise RuntimeError('Keep unsaved user changes before authoring: ' + repr(conflicts))
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('Stop PIE before changing the biome')

inputs = json.loads((ROOT / 'inputs.json').read_text())
da = u.load_asset(DA_PATH)
current = da.get_editor_property('ground_material').get_path_name()
if current != inputs['fields']['ground_material']:
    raise RuntimeError('The ground material was changed independently; preserve its binding: ' + current)
ground = u.load_asset(current)
for key, expected in inputs['ground_parameters'].items():
    actual = u.MaterialEditingLibrary.get_material_default_scalar_parameter_value(ground, key)
    if abs(actual - expected) > .00001:
        raise RuntimeError('Ground parameter changed independently: ' + key)

result = runpy.run_path(str(PROJECT / 'Tools/WorldGeneration/build_hills_ground_v2.py'), run_name='__main__')
report = result['REPORT']
# Keep flowers as small meadow pockets rather than an even multi-colour carpet.
before = da.get_editor_property('meadow_flower_coverage')
if abs(before - inputs['scalars']['meadow_flower_coverage']) > .00001 and abs(before-.18) > .00001:
    raise RuntimeError('Meadow density was changed independently; materials saved, density left intact')
backup = ROOT / 'Backups' / ('Assets-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
source = PROJECT / 'Content/WorldGeneration/TemperateHills/DA_TemperateHillsStreaming.uasset'
backup.mkdir(parents=True, exist_ok=True)
shutil.copy2(source, backup / source.name)
da.set_editor_property('meadow_flower_coverage', .18)
if not u.EditorAssetLibrary.save_loaded_asset(da, False):
    raise RuntimeError('Could not save the biome')
receipt = {'stage':'assets_saved', 'ground_material':current,
           'saved':report['saved'] + [DA_PATH], 'flower_coverage_before':before,
           'flower_coverage_after':.18, 'source_textures_modified':False,
           'map_modified':False, 'game_run':False, 'visual_tested':False}
(ROOT / 'Receipts/assets.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
u.log('FOREST_ASSETS_SAVED ' + json.dumps(receipt))
