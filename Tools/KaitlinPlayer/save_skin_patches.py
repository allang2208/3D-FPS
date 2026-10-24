"""Keep robe inner-skin visibility while replacing its male skin graph."""
import importlib.util
import json
from pathlib import Path
import unreal as u

PROJECT = Path('D:/FPS3D/FPSGAME')
WORK = PROJECT / 'SourceAssets/KaitlinPlayer20261023'
manifest = json.loads((WORK / 'WorldGarments/manifest.json').read_text())
saved = json.loads((WORK / 'WorldGarments/saved_assets.json').read_text())
body = json.loads((WORK / 'NativeGeometry/MHC_Kaitlin_Body.json').read_text())
spec = importlib.util.spec_from_file_location('kaitlin_hem_materials', str(PROJECT / 'Tools/BlueMageRobe/hem_materials.py'))
hem = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hem)
hem.DEST = '/Game/Characters/ModularOutfit20260924/KaitlinPlayer20261023/Materials/Hem'
skin = u.load_asset(body['materials'][0]['asset'])
masked_skin = None
modified = []
for source, row in manifest.items():
    data = json.loads(Path(row['geometry']).read_text())
    # Only the two source skin variants have these section identities.
    if not any(material['slot'] == 'SkinTorso' for material in data['materials']):
        continue
    if masked_skin is None:
        masked_skin = hem.make(skin)
    asset = u.load_asset(saved[source])
    slots = list(asset.materials)
    for index, slot in enumerate(slots):
        name = str(slot.material_slot_name)
        if name.startswith('RobeStairHidden_') or name == 'NeckSeam':
            replacement = slot.copy()
            replacement.material_interface = masked_skin if name.startswith('RobeStairHidden_') else skin
            slots[index] = replacement
    asset.set_editor_property('materials', slots)
    if not u.EditorAssetLibrary.save_loaded_asset(asset, False):
        raise RuntimeError('Female inner skin was not saved: ' + saved[source])
    modified.append(saved[source])
(WORK / 'skin_patches_saved.json').write_text(json.dumps({'meshes': modified,
    'masked_skin': masked_skin.get_path_name() if masked_skin else None}, indent=2), encoding='utf-8')
(WORK / 'save_skin_patches_status.json').write_text(json.dumps({'remaining': 0, 'complete': True}), encoding='utf-8')
print('KAITLIN_INNER_SKIN_SAVED', len(modified), flush=True)
