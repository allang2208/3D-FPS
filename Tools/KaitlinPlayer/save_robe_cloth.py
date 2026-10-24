"""Attach the retained robe simulation to female geometry and fitted colliders."""
import json
from pathlib import Path
import unreal as u

WORK = Path('D:/FPS3D/FPSGAME/SourceAssets/KaitlinPlayer20261023')
manifest = json.loads((WORK / 'WorldGarments/manifest.json').read_text())
saved = json.loads((WORK / 'WorldGarments/saved_assets.json').read_text())
receipt = []
for source, row in manifest.items():
    data = json.loads(Path(row['geometry']).read_text())
    if not any(material['slot'] == 'RobeSimulationProxy' for material in data['materials']):
        continue
    mesh = u.load_asset(saved[source])
    if not u.FPSModularOutfitComponent.build_mage_robe_drape_for_body(mesh, str(WORK / 'robe_collision.json')):
        raise RuntimeError('Female robe cloth authoring did not finish: ' + saved[source])
    if not u.EditorAssetLibrary.save_loaded_asset(mesh, False):
        raise RuntimeError('Female robe cloth was not saved: ' + saved[source])
    receipt.append(saved[source])
(WORK / 'robe_cloth_saved.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
(WORK / 'save_robe_cloth_status.json').write_text(json.dumps({'remaining': 0, 'complete': True}), encoding='utf-8')
print('KAITLIN_ROBE_CLOTH_SAVED', len(receipt), flush=True)
