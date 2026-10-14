"""Apply the thermal clarity shader to its existing runtime material and save."""
import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path
import unreal as u

PROJECT = Path(__file__).resolve().parents[3]
SOURCE = Path(__file__).with_name('thermal_scene.hlsl')
PATH = '/Game/Weapons/ThermalScope20261006/Runtime/M_ThermalScene'
OUT = PROJECT / 'SourceAssets/ThermalScopeRuntime20261007/Clarity'
if Path(u.Paths.project_dir()).resolve() != PROJECT.resolve():
    raise RuntimeError('Unexpected project')
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('Exit the Play session before applying the thermal material')
if PATH in {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}:
    raise RuntimeError('Preserve unsaved edits to the thermal material')
if u.SystemLibrary.get_console_variable_int_value('r.CustomDepthTemporalAAJitter') != 0:
    raise RuntimeError('Thermal material expects the project custom-depth jitter setting of 0; no global setting changed')

stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
backup = OUT / ('BeforeMaterial-' + stamp)
backup.mkdir(parents=True, exist_ok=True)
asset_file = PROJECT / 'Content' / (PATH.removeprefix('/Game/') + '.uasset')
shutil.copy2(asset_file, backup / asset_file.name)
material = u.load_asset(PATH)
if not isinstance(material, u.Material):
    raise RuntimeError('Missing runtime thermal material')
library = u.MaterialEditingLibrary
effect = library.get_material_property_input_node(material, u.MaterialProperty.MP_EMISSIVE_COLOR)
if not isinstance(effect, u.MaterialExpressionCustom):
    raise RuntimeError('Preserve unexpected runtime thermal material graph')
code = SOURCE.read_text(encoding='utf-8')
effect.set_editor_property('code', code)
effect.set_editor_property('desc', 'Thermal clarity: aligned depth, filtered coverage and body relief')
errors = library.recompile_material(material)
if errors:
    raise RuntimeError('Thermal material compilation failed: ' + str(errors))
# Finishes the material's shader jobs without starting a game or capture.
library.get_statistics(material)
if not u.EditorLoadingAndSavingUtils.save_packages([material.get_outermost()], False):
    raise RuntimeError('Thermal material save failed')
receipt = {
    'saved': material.get_path_name(),
    'source_sha256': hashlib.sha256(code.encode('utf-8')).hexdigest(),
    'custom_depth_jitter': 0,
    'depth_tolerance_cm': [1.25, 3.0],
    'scene_capture_added': False,
    'native_code_changed': False,
    'game_tested': False,
    'rendered': False,
    'backup': str(backup),
}
receipt_path = OUT / ('material-save-' + stamp + '.json')
receipt_path.write_text(json.dumps(receipt, indent=2), encoding='utf-8')
print('THERMAL_CLARITY_SAVED ' + json.dumps(receipt))
