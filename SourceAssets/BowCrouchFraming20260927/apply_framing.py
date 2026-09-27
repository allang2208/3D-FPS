"""Adjust the catalog crouch pose; reuse runtime grip-pivot and ADS alignment.
No mesh reimport, DLL update, editor launch or save-game overwrite is needed.
"""
import json, shutil
from pathlib import Path
P=Path(__file__).parent;ROOT=P.parents[1]
path=ROOT/'Content/ColdSteelData/bows.json'
backup=ROOT/'Saved/BowCrouchFraming20260927/Before/Content/ColdSteelData/bows.json'
backup.parent.mkdir(parents=True,exist_ok=True)
if not backup.exists():shutil.copy2(path,backup)
data=json.loads(path.read_text(encoding='utf-8-sig'));bow=data['bow_dark']
changes={'bow_crouch_cant_deg':-12,'bow_crouch_offset_cm':'-1.5,-2,-3.5'}
before={k:bow.get(k) for k in changes}
changed=any(before[k]!=v for k,v in changes.items())
bow.update(changes)
bow['bow_presentation_revision']=max(34,int(bow.get('bow_presentation_revision',0))+int(changed))
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
(P/'install-receipt.json').write_text(json.dumps({'before':before,'after':changes,
    'presentation_revision':bow['bow_presentation_revision'],
    'activation':'Next game-instance initialization loads catalog and migrates existing bow presentation',
    'native_build_required':False,'runtime_tested':False},indent=2),encoding='utf8')
print('BOW_CROUCH_FRAMING_SAVED revision='+str(bow['bow_presentation_revision']))
