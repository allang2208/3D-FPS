"""Apply the user's 8-second duration to this seal's active text and source recipe."""
import json,os
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[3]
build='SourceAssets/CommonHammerSeats20261024/AncientSealBuildV1/'
concept='SourceAssets/CommonHammerSeats20261024/AncientSealConceptV1/'
def wording(text):return text.replace('6秒','8秒').replace('6 秒','8 秒')
jobs=[('Content/ColdSteelData/common-hammer-seats.json','catalog'),
      ('Content/ColdSteelData/status_effects.json','status'),
      (build+'catalog_option.json','option'),(build+'published.json','published'),
      (concept+'design.json','design'),(build+'publish.py','text'),
      (build+'README.md','text'),(concept+'design_proposal.txt','text')]
changed=[]
for relative,kind in jobs:
    file=ROOT/relative;before=file.read_bytes();text=before.decode('utf-8-sig')
    if kind=='text':after=wording(text)
    else:
        data=json.loads(text)
        if kind=='catalog':
            entry=next(v for v in data['options'] if v['id']=='ancient_breaking_seal_seat')
            entry['special_effects']=[wording(v) for v in entry['special_effects']]
        elif kind=='status':
            entry=next(v for v in data['effects'] if v['type']=='breakingSeal');entry['description']=wording(entry['description'])
        elif kind in ('option','published'):
            entry=data if kind=='option' else data['option'];entry['special_effects']=[wording(v) for v in entry['special_effects']]
            if kind=='published':data['duration_revision']={'seconds':8,'date':'2026-10-25'}
        else:data['suggested_effect']['duration_seconds']=8
        after=json.dumps(data,ensure_ascii=False,indent=2)+'\n'
    backup=P/'Before'/relative;backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():backup.write_bytes(before)
    if file.read_bytes()!=before:raise RuntimeError('Concurrent change '+relative)
    tmp=file.with_suffix('.seal-duration.tmp');tmp.write_text(after,encoding='utf-8')
    if file.read_bytes()!=before:raise RuntimeError('Concurrent change before commit '+relative)
    os.replace(tmp,file);changed.append(relative)
(P/'update_receipt.json').write_text(json.dumps({'complete':True,'seconds':8,'physical_bonus':.15,'toughness_bonus':.25,'changed':changed,'game_tested':False},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('BREAKING_SEAL_DURATION_8S_PUBLISHED')
