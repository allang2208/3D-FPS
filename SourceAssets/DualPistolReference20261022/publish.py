"""Register saved original-source takes using exact shared-config leaf ownership."""
import json
import runpy
from pathlib import Path

ROOT=Path('D:/FPS3D/FPSGAME')
OUT=ROOT/'SourceAssets/DualPistolReference20261022'
receipt=json.loads((OUT/'retarget-receipt.json').read_text(encoding='utf-8'))
roles={'Idle':'Idle','Walk':'Walk_Fwd','Jog':'Jog_Fwd','Sprint':'Sprint_Fwd',
       'FireRight':'DoubleShot_Fire_Rt','FireLeft':'DoubleShot_Fire_Lft'}
path=ROOT/'Content/ColdSteelData/player_body.json'
before=path.read_bytes()
cfg=json.loads(before.decode('utf-8-sig'))
source=json.loads((OUT/'source-poses.json').read_text(encoding='utf-8'))
if cfg['body_mesh']!=source['target']['mesh']:
    raise RuntimeError('Body mesh changed during retargeting; do not publish stale bones.')
keys={}
for role,name in roles.items():
    asset=receipt['clips'][name]
    package=ROOT/'Content'/(asset.split('.')[0].removeprefix('/Game/')+'.uasset')
    if not package.is_file():raise RuntimeError('Unsaved animation: '+asset)
    key='DualPistol.Source.'+role
    keys[key]=asset
    cfg['clips'][key]=asset
commit=runpy.run_path(str(ROOT/'Tools/PlayerBody/config_transaction.py'))['commit']
written=commit(path,before,cfg,owned_paths=[('clips',k) for k in keys],producer=__file__)
(OUT/'published.json').write_text(json.dumps(dict(clips=keys,config_write=written,
    assets_saved=True,runtime_tested=False,git_commit=None,git_push=None),indent=2),encoding='utf-8')
print('TWINBLAST_ROUTES_SAVED',len(keys))
