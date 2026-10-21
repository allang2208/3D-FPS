"""Publish only this revision's twenty hammer roles after save and build."""
import json
import re
import runpy
from pathlib import Path
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]
receipt=json.loads((OUT/'assets-saved.json').read_text())
if not receipt.get('complete'):
    raise RuntimeError('Save all ten anatomical animations before switching.')
build=OUT/'build-editor.log'
if not build.exists() or 'Editor modules built.' not in build.read_text(encoding='utf-8-sig',errors='replace'):
    raise RuntimeError('Compile section hiding and the native blend change first.')
clips={}
for key,value in receipt['clips'].items():
    label=key.removeprefix('Warhammer.FullBody.')
    if label.startswith('Whirlwind'):
        label='Whirlwind.'+label.removeprefix('Whirlwind')
    clips['Warhammer.FullBody.'+label]=value
for key,source in dict(Slash1Recover='Slash1',Slash2Recover='Slash2',Slash3Recover='Slash3',
    Charge='Slash3',Slam='Slash3',SprintLift='Slash3',SprintSlam='Slash3',Uppercut='Slash1',
    GuardExit='GuardEnter',GuardBreak='GuardHit').items():
    clips['Warhammer.FullBody.'+key]=clips['Warhammer.FullBody.'+source]
path=ROOT/'Content/ColdSteelData/player_body.json'
before_bytes=path.read_bytes();text=before_bytes.decode('utf-8-sig')
cfg=json.loads(text)
history=json.loads((OUT/'assets-published.json').read_text(encoding='utf-8-sig'))
for key,value in clips.items():
    if cfg['clips'].get(key) not in (history['previous_clips'].get(key),value):
        raise RuntimeError('A later revision owns this role; do not replay V7: '+key)
receipt['previous_clips']={key:cfg['clips'].get(key) for key in clips}
for key,value in clips.items():
    pattern=r'('+re.escape(json.dumps(key))+r'\s*:\s*)"[^"\r\n]*"'
    text,count=re.subn(pattern,lambda m:m[1]+json.dumps(value),text)
    if count!=1:
        raise RuntimeError('Expected exactly one existing hammer role: '+key)
config_write=runpy.run_path(str(ROOT/'Tools/PlayerBody/config_transaction.py'))['commit'](
    path,before_bytes,text,owned_paths=[('clips',key) for key in clips],producer=__file__)
receipt['config_write']=config_write
receipt.update(clips=clips,published=True,runtime_tested=False,
    supersedes=['DirectKwangV5','SecondaryDonorsV6'],
    revision='Joint-constrained haft fit; no camera-space action paths; duplicate FPS arm sections hidden')
(OUT/'assets-published.json').write_text(json.dumps(receipt,indent=2))
print('ANATOMICAL_GRIP_PUBLISHED '+str(len(clips))+' roles using 10 assets')
