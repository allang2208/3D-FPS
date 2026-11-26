"""Update the active hills ground's three rainforest scan samplers in place."""
import hashlib
import json
import runpy
import shutil
from pathlib import Path
import unreal as u

root = Path('D:/FPS3D/FPSGAME')
out = Path(globals().get('receipt_dir', root / 'Saved/HillsForestFloorRefinement'))
out.mkdir(parents=True, exist_ok=True)
asset_path = '/Game/WorldGeneration/TemperateHills/PebbleShore/M_PebbleShoreGround'
package = root / 'Content' / (asset_path.removeprefix('/Game/') + '.uasset')
original = package.read_bytes()
backup = out / ('before-' + hashlib.sha256(original).hexdigest()[:16] + '.uasset')
if not backup.exists():
    shutil.copy2(package, backup)
mat = u.load_asset(asset_path)
author = runpy.run_path(str(root / 'Tools/WorldGeneration/forest_wet_materials.py'))
nodes = {str(node.get_editor_property('desc')): node for node in u.MaterialEditingLibrary.get_material_expressions(mat)}
def existing(name):
    return nodes[author['TAG'] + name]

samples = [existing('MossSample' + channel) for channel in ('BaseColor', 'Normal', 'ARH')]
updated = author['rainforest_samples'](mat, *(existing(key) for key in (
    'MossUV', 'MossCoverage', 'CarpetWetHollow', 'HabitatUV', 'GroundVertex')))
if [n.get_path_name() for n in updated] != [n.get_path_name() for n in samples]:
    raise RuntimeError('The active ground must retain its connected sample expressions')
errors = u.MaterialEditingLibrary.recompile_material(mat)
if errors:
    raise RuntimeError(str(errors))
if package.read_bytes() != original:
    raise RuntimeError('The ground package changed during authoring')
if not u.EditorAssetLibrary.save_loaded_asset(mat, False):
    raise RuntimeError('Could not save the hills ground')
receipt = dict(asset=mat.get_path_name(), before=hashlib.sha256(original).hexdigest(),
               after=hashlib.sha256(package.read_bytes()).hexdigest(), samplers=len(samples))
(out / 'saved.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
u.log('HILLS_RAINFOREST_FLOOR_SAVED ' + receipt['after'])
