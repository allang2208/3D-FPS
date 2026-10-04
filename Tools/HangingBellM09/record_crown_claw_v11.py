"""Record actual V11 animation save and native build results, without gameplay testing."""
import json
from datetime import datetime
from pathlib import Path
p=Path('D:/FPS3D/FPSGAME');r=p/'SourceAssets/HangingBellM09Meshy20261003/CrownClawV11/Records'
assets=json.loads((r/'import_saved.json').read_text(encoding='utf8'))
builds={}
for target in ('FPSGAMEEditor','FPSGAME'):
 log=r/f'build_{target}_stdout.log'
 text=log.read_text(encoding='utf-8-sig',errors='replace') if log.exists() else ''
 builds[target]={'succeeded':'Result: Succeeded' in text,'log':str(log),'kind':'regular native build' if log.exists() else 'pending'}
data={'production':'M09 CrownClaw V11','recorded_at':datetime.now().isoformat(timespec='seconds'),
 'complete':assets['complete'] and all(b['succeeded'] for b in builds.values()),'assets':assets,'builds':builds,
 'tested':False,'editor_started':False,'game_started':False,
 'preserved':['V10 Gaze convergence FX','V08 Gaze attack timing/range/damage','V09 staged membrane opening at 1.5x','V07 Resonance contract','V05 spawn/movement']}
(r/'delivery.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'complete':data['complete'],'assets_saved':len(assets['saved']),'builds':builds,'tested':False},ensure_ascii=False))
