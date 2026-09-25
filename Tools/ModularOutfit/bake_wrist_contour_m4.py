"""Rebake the local wrist atlas and reuse the accepted V3 skin microdetail."""
import json
import runpy
import shutil
from pathlib import Path

PROJECT = Path('D:/FPS3D/FPSGAME')
BASE = PROJECT / 'SourceAssets/ModularOutfit20260924/OriginalShapeBareM4'
SOURCE, ROOT = BASE / 'RefinedSkinV3', BASE / 'WristContourV4'
for name in ('T_M4OriginalShape_SkinMicro.png', 'T_M4OriginalShape_SkinColourDetail.png',
             'micro_surface.json', 'skin_detail.hlsl'):
    shutil.copy2(SOURCE / name, ROOT / name)
config = json.loads((ROOT / 'micro_surface.json').read_text())
config['provenance'] = '../RefinedSkinV3/External/SkinHuman002/provenance.json'
config['wrist_v4_note'] = 'Accepted V3 microdetail scale and height retained; macro anatomy rebaked on locally tapered wrist'
(ROOT / 'micro_surface.json').write_text(json.dumps(config, indent=2))
runpy.run_path(str(PROJECT / 'Tools/ModularOutfit/bake_original_shape_skin.py'),
              init_globals={'AUTHOR_ROOT': str(ROOT), 'SMOOTH_SKIN': True})
