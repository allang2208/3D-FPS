"""Record V7 saved asset/build output and close the preceding audio delivery."""
import json
from pathlib import Path
from datetime import datetime
p=Path(__file__).resolve().parent
imported=json.loads((p/'import_receipt.json').read_text(encoding='utf-8-sig'))
built=json.loads((p/'build_receipt.json').read_text(encoding='utf-8-sig'))
if not imported['complete'] or imported['revision']!='HeadThrustLeftWristV7_20261015':
    raise RuntimeError('V7 animation save is incomplete')
if not built['complete'] or any(x['exit_code'] for x in built['targets']):
    raise RuntimeError('Formal builds are incomplete')
for version in ('QuickCombatV1','QuickCombatImpactV2'):
    backup=p/'Before'/version;backup.mkdir(exist_ok=True)
    for name,target in (('author_quick_combat.py','author_left_wrist.py'),('import_assets.py','import_assets.py')):
        entry=p.parent/version/name
        if not (backup/name).exists():(backup/name).write_bytes(entry.read_bytes())
        entry.write_text('"""Current warhammer quick melee: left wrist repair V7."""\n'
            'from pathlib import Path\nimport runpy\n'
            'runpy.run_path(str(Path(__file__).resolve().parent.parent/'
            f'"QuickCombatLeftWristV7/{target}"),run_name="__main__")\n',encoding='utf-8')
receipt={'revision':imported['revision'],'saved_assets':imported['saved'],'builds':built['targets'],
    'runtime_seconds':.72,'contact_seconds':.28,'forward_stroke_m':.34,
    'left_hand_fingers_right_arm_weapon':'retained V6 component-space transforms',
    'repair':'left native hinge and continuous forearm roll, supported shoulder, original bone lengths',
    'source_diagnosis':True,'runtime_tested':False,'preview_rendered':False,'audio_auditioned':False,
    'finished':datetime.now().isoformat(timespec='seconds')}
(p/'delivery.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
audio=p.parent/'QuickCombatSwordAudioV1/delivery.json'
if audio.exists():
    previous=json.loads(audio.read_text(encoding='utf-8-sig'))
    previous.update(formal_build_complete=True,build=built,blocker=None,
        completed_with='QuickCombatLeftWristV7',recorded=receipt['finished'])
    audio.write_text(json.dumps(previous,indent=2),encoding='utf-8')
print(json.dumps(receipt))
