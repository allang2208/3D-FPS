"""Wire the six saved pack variants through the shared per-field writer."""
import json,runpy
from pathlib import Path

P=Path('D:/FPS3D/FPSGAME')
R=P/'SourceAssets/BackpackHarnessRebuild20261020'
manifest=json.loads((R/'manifest.json').read_text())
saved=json.loads((R/'saved_assets.json').read_text())
path=P/'Content/ColdSteelData/player_body.json'
before=path.read_bytes();cfg=json.loads(before.decode('utf-8-sig'))
pack=cfg['outfits']['ue_mountain_backpack'];owned=[]
for row in manifest['variants']:
    receipt=saved[row['profile']]
    if not receipt['saved'] or receipt['revision']!=manifest['revision']:
        raise RuntimeError('Save the current variant first: '+row['profile'])
    if row['shirt']:
        pack['world_mesh_by_shirt'][row['shirt']]=row['asset']
        owned.append(('outfits','ue_mountain_backpack','world_mesh_by_shirt',row['shirt']))
    else:
        pack['world_mesh']=row['asset']
        owned.append(('outfits','ue_mountain_backpack','world_mesh'))
result=runpy.run_path(str(P/'Tools/PlayerBody/config_transaction.py'))['commit'](
    path,before,cfg,owned_paths=owned,producer=__file__)
result.update(revision=manifest['revision'],accepted_by_user=False)
(R/'published.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print('HARNESS_LOCAL_CONFIG',json.dumps(result))
