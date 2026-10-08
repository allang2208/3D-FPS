"""Resume our interrupted particle compilation; retain the saved materials."""
from pathlib import Path
import json
import runpy
import unreal as u

ROOT = Path(__file__).resolve().parent
recipe = runpy.run_path(str(ROOT.parent / 'RisingMotes/author_rising_motes.py'))
material = u.load_asset(recipe['DEST'] + '/M_ZhenmoGoldMote')
if not material:
    raise RuntimeError('The material from the interrupted batch is missing')
recipe['particles'](material)
receipt = {'complete': True, 'saved_assets': recipe['SAVED'],
           'revision': 'SoftGroundV3', 'edge_fade_radius_fraction': [.72, .985],
           'runtime_tested': False}
(ROOT / 'motes_receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
print('ZHENMO_MOTES_EDGE_SAVED ' + json.dumps(receipt), flush=True)
