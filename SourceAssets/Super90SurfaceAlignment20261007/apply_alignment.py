"""Save the corrected atlas/normal inputs through the existing editor bridge."""
import json, shutil, runpy
from pathlib import Path
import unreal as u

O = Path(__file__).parent
P = O.parents[1]
W = O.parent/'Super90WS1Surface20261007'
if u.EditorLevelLibrary.get_game_world():
    raise RuntimeError('Exit PIE before importing the corrected Super90 UVs. No assets were modified.')
prior = json.loads((W/'import_receipt.json').read_text())
paths = prior['saved'] + ['/Game/Weapons/Super90/Cransh20261006/Textures/T_S90_TTI_Benelli_M4_Normal_brand_friendly']
for asset in paths:
    rel = 'Content/'+asset.split('.')[0].removeprefix('/Game/')+'.uasset'
    src = P/rel
    dst = O/'Before'/rel
    if src.exists() and not dst.exists():
        dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(src,dst)
config = 'Content/ColdSteelData/modular_outfits.json'
dst = O/'Before'/config
if not dst.exists():
    dst.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(P/config,dst)
runpy.run_path(str(W/'apply_surface.py'),run_name='__main__')
receipt = json.loads((W/'import_receipt.json').read_text())
receipt.update(atlas_mapping='SourcePNG-VFlip-20261007', gun_normal_format='DirectX; flip_green_channel=False', runtime_tested=False)
(O/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('SUPER90_ALIGNMENT_SAVED',len(receipt['saved']),flush=True)
