"""Record actual asset-save/build results; no runtime tests or verification run."""
import json
from pathlib import Path
from datetime import datetime
p=Path('D:/FPS3D/FPSGAME');r=p/'SourceAssets/HangingBellM09Meshy20261003/GazeV08/Records'
a=r/'import_saved.json'
assets=json.loads(a.read_text(encoding='utf8')) if a.exists() else {'complete':False,'saved':[]}
builds={}
for target in ('FPSGAMEEditor','FPSGAME'):
 log=r/f'build_{target}_stdout.log'
 content=log.read_text(encoding='utf-8-sig',errors='replace') if log.exists() else ''
 builds[target]={'succeeded':'Result: Succeeded' in content,'log':str(log),'kind':'regular native build' if log.exists() else 'pending'}
receipt={'production':'M09 Gaze V08','recorded_at':datetime.now().isoformat(timespec='seconds'),
 'assets':assets,'builds':builds,'complete':assets['complete'] and all(b['succeeded'] for b in builds.values()),
 'contract':{'duration':3.,'lock':.9,'fire':[1.25,1.85],'pulses':[1.25,1.45,1.65],
 'range_cm':1400,'radius_cm':10,'magic_multiplier_per_hit':.35,'cooldown':7,
 'sanity_rule':'Existing generic magic attack handling; V07 fixed -2 remains exclusive to Resonance',
 'main_eyes':5,'decorative_segments':20,'gameplay_beams':1},
 'preserved':['RigV03 skin and original geometry','V04 body and skeleton','V05 ceiling spawn/movement','V07 Resonance'],
 'tested':False,'interactive_editor_launched_by_this_task':False,'game_launched_by_this_task':False}
(r/'delivery.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'complete':receipt['complete'],'assets_saved':len(assets['saved']),'builds':builds,'tested':False},ensure_ascii=False))
