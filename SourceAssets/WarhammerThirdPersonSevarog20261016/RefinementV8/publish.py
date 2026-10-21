"""Switch only the twelve roles backed by this revision's four saved takes."""
import json
import re
import runpy
from pathlib import Path
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]
receipt=json.loads((OUT/'assets-saved.json').read_text())
if not receipt.get('complete'):raise RuntimeError('Save all four refined takes before switching.')
build=(OUT/'build-editor.log').read_text(encoding='utf-8-sig',errors='replace')
if 'Editor modules built.' not in build:raise RuntimeError('Compile the charge/phase clock first.')
clips=dict(receipt['clips'])
for key,source in dict(Slash1Recover='Slash1',Slash2Recover='Slash2',Slash3Recover='Slash3',
    Charge='Slash3',Slam='Slash3',SprintLift='Slash3',SprintSlam='Slash3',Uppercut='Slash1').items():
    clips['Warhammer.FullBody.'+key]=clips['Warhammer.FullBody.'+source]
path=ROOT/'Content/ColdSteelData/player_body.json'
before_bytes=path.read_bytes();text=before_bytes.decode('utf-8-sig');cfg=json.loads(text)
history=json.loads((OUT/'assets-published.json').read_text(encoding='utf-8-sig'))
for key,value in clips.items():
    if cfg['clips'].get(key) not in (history['previous_clips'].get(key),value):
        raise RuntimeError('A later revision owns this role; do not replay V8: '+key)
receipt['previous_clips']={key:cfg['clips'].get(key) for key in clips}
for key,value in clips.items():
    pattern=r'('+re.escape(json.dumps(key))+r'\s*:\s*)"[^"\r\n]*"'
    text,count=re.subn(pattern,lambda m:m[1]+json.dumps(value),text)
    if count!=1:raise RuntimeError('Expected one existing hammer role: '+key)
config_write=runpy.run_path(str(ROOT/'Tools/PlayerBody/config_transaction.py'))['commit'](
    path,before_bytes,text,owned_paths=[('clips',key) for key in clips],producer=__file__)
receipt['config_write']=config_write
receipt.update(clips=clips,published=True,runtime_tested=False,
    revision='V8 arm continuity, quick-melee shoulder clearance and moving heavy charge')
(OUT/'assets-published.json').write_text(json.dumps(receipt,indent=2))
print('HAMMER_REFINEMENT_PUBLISHED '+str(len(clips))+' roles using 4 assets')
