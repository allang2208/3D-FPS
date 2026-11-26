"""Reuse unchanged complete source captures for the new, isolated leg revision."""
import json, hashlib
from pathlib import Path

P=Path('D:/FPS3D/FPSGAME')
BASE=P/'SourceAssets/BlueMageRobe20261018/HemContinuity20261019'
OUT=P/'SourceAssets/BlueMageRobe20261018/TurnLegContinuity20261020'
OUT.mkdir(parents=True,exist_ok=True)
cfg=json.loads((P/'Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'))
mapping=cfg['items']['ue_blue_mage_robe']['underlayer_meshes']
old=json.loads((BASE/'inputs.json').read_text())
rows=[]
for row in old['rows']:
    if row['original'] not in mapping:raise RuntimeError('Source recipe changed: recapture current robe inputs')
    asset=P/'Content'/(row['source'].split('.')[0].removeprefix('/Game/')+'.uasset')
    if hashlib.sha256(asset.read_bytes()).hexdigest()!=row['asset_sha256']:
        raise RuntimeError('Source changed; run capture_hem_sources.py for '+row['source'])
    rows.append(row)
if len(rows)!=len(mapping):raise RuntimeError('New underlayer sources require capture_hem_sources.py')
(OUT/'inputs.json').write_text(json.dumps(dict(rows=rows,underlayer_meshes=mapping),indent=2),encoding='utf-8')
print('ROBE_TURN_SOURCE_INPUTS_READY',len(rows),flush=True)
