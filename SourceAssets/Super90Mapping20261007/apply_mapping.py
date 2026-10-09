"""Import/save the authored atlas correction without opening or running a game."""
import unreal as u,json,shutil,runpy
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];W=O.parent/'Super90WS1Surface20261007'
if u.EditorLevelLibrary.get_game_world():raise RuntimeError('Exit PIE before saving the corrected source mapping.')
prior=json.loads((W/'import_receipt.json').read_text())
for path in prior['saved']:
    rel=path.split('.')[0].removeprefix('/Game/')+'.uasset';src=P/'Content'/rel;dst=O/'Before'/rel
    if src.exists() and not dst.exists():dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
runpy.run_path(str(W/'apply_surface.py'),run_name='__main__')
receipt=json.loads((W/'import_receipt.json').read_text())
receipt['mapping']=json.loads((W/'authoring.json').read_text())['atlas_mapping']
(O/'import_receipt.json').write_text(json.dumps(receipt,indent=2))
print('SUPER90_MAPPING_SAVED',len(receipt['saved']),flush=True)
