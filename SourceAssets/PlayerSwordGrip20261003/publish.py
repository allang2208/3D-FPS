"""Publish only the saved sword finger clip, preserving other body configuration."""
import hashlib,json
from pathlib import Path

P=Path('D:/FPS3D/FPSGAME');R=Path(__file__).resolve().parent
saved=json.loads((R/'saved.json').read_text())
asset=P/'Content'/Path(saved['asset'].split('.')[0].removeprefix('/Game/')+'.uasset')
if not saved['saved'] or hashlib.sha256(asset.read_bytes()).hexdigest()!=saved['sha256']:
    raise RuntimeError('Missing saved grip asset')
path=P/'Content/ColdSteelData/player_body.json'
original=path.read_text(encoding='utf-8-sig');cfg=json.loads(original)
authored=json.loads((R/'grip.json').read_text())
if cfg['body_mesh']!=authored['body']:raise RuntimeError('Body rig changed during authoring')
if 'Melee.Grip' in cfg['clips']:raise RuntimeError('Keep existing grip configuration intact')
(R/'player_body_before_grip.json').write_text(original,encoding='utf-8')
cfg['clips']['Melee.Grip']=saved['asset']
path.write_text(json.dumps(cfg,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(R/'published.json').write_text(json.dumps(dict(asset=saved['asset'],key='clips.Melee.Grip',
    configuration=str(path),runtime_tested=False),indent=2))
print('JASON_SWORD_GRIP_PUBLISHED',saved['asset'])
