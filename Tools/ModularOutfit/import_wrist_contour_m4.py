"""Import/save a separate V4 wrist asset and publish the M4 bare-hand profile."""
import json
import runpy
from pathlib import Path

PROJECT = Path('D:/FPS3D/FPSGAME')
ROOT = PROJECT / 'SourceAssets/ModularOutfit20260924/OriginalShapeBareM4/WristContourV4'
runpy.run_path(str(PROJECT / 'Tools/ModularOutfit/import_original_shape_m4.py'), init_globals={
    'AUTHOR_ROOT': str(ROOT),
    'ASSET_DEST': '/Game/Characters/ModularOutfit20260924/OriginalShapeBareM4WristV4',
    'SMOOTH_SKIN': True, 'REFINED_SKIN': True})
receipt_path = ROOT / 'saved.json'
receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
receipt['wrist_reconstructed'] = False
receipt['wrist_contour_edited'] = True
receipt['new_wrist_weights'] = 'No new weights in V4; every V3 vertex binding retained'
receipt['preserved'] = ['corrected V3 connectivity and native winding', 'all V3 skin weights',
    'reference skeleton and bind transforms', 'palm/finger grip positions beyond wrist boundary',
    'V3 UV layout', 'animation assets', 'original glove restoration']
receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
