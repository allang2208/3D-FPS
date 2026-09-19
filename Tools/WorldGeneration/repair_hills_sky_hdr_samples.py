"""Update only the hills sky blend expression, without opening a game world."""
import ast
import json
import shutil
from datetime import datetime
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = ROOT / 'Saved/HillsSkyMarkers20260915'
SOURCE = ROOT / 'Tools/WorldGeneration/build_hills_daynight_sky.py'
ASSET = '/Game/WorldGeneration/TemperateHills/Sky/M_HillsDayNightSky'

# Use the authoring script's exact expression so regenerating this material
# retains the repair instead of reintroducing the original weighted sum.
tree = ast.parse(SOURCE.read_text(encoding='utf-8'))
blend = next(node for node in tree.body if isinstance(node, ast.Assign)
             and any(isinstance(target, ast.Name) and target.id == 'color'
                     for target in node.targets))
code = ast.literal_eval(blend.value.args[1])
material = u.load_asset(ASSET)
if material is None:
    raise RuntimeError('Missing hills sky material')
expressions = [obj for obj in u.MaterialEditingLibrary.get_material_expressions(material)
               if isinstance(obj, u.MaterialExpressionCustom)
               and 'float nightWeight' in obj.get_editor_property('code')]
if len(expressions) != 1:
    raise RuntimeError('Expected one hills sky blend expression')

asset_file = ROOT / 'Content/WorldGeneration/TemperateHills/Sky/M_HillsDayNightSky.uasset'
backup_dir = OUT / ('BeforeHDRSampleRepair-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
backup_dir.mkdir(parents=True, exist_ok=True)
shutil.copy2(asset_file, backup_dir / asset_file.name)
expression = expressions[0]
old_code = expression.get_editor_property('code')
expression.set_editor_property('code', code)
u.MaterialEditingLibrary.recompile_material(material)
if not u.EditorAssetLibrary.save_loaded_asset(material, False):
    raise RuntimeError('Unable to save hills sky material')
(OUT / 'hdr-sample-repair.json').write_text(json.dumps({
    'material': material.get_path_name(), 'expression': expression.get_path_name(),
    'backup': str(backup_dir / asset_file.name), 'old_code': old_code, 'code': code,
    'scope': 'Material authoring only; user will test the repaired sky.'
}, indent=2), encoding='utf-8')
u.log('HILLS_HDR_SAMPLE_REPAIR_SAVED: ' + material.get_path_name())
