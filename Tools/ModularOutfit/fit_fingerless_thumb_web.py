"""Keep the exposed A762 thumb web following its own metacarpal during abduction."""
import json
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ModularOutfit20260926/FingerlessHuntV2';path=R/'SkinCoverage/A762_review.json';before=R/'ClearanceReview/A762_skin_before_thumb_web.json'
if not before.exists():before.write_bytes(path.read_bytes())
d=json.loads(before.read_text());touched=0
for w in d['weights']:
    thumb=w.get('thumb_02_l',0)+w.get('thumb_03_l',0)
    f=max(0,min(1,(thumb-.15)/.15));f=f*f*(3-2*f)
    if f<=0:continue
    tail=max(0,min(1,(thumb-.65)/.30));tail=tail*tail*(3-2*tail)
    donation=w.get('thumb_02_l',0)*f*(1-tail)*.85
    if donation:w['thumb_02_l']-=donation
    if donation<=0:continue
    w['thumb_01_l']=w.get('thumb_01_l',0)+donation;touched+=1
path.write_text(json.dumps(d,separators=(',',':')))
print('EXPOSED_THUMB_WEB_WEIGHTS',touched)
# Failed large thumb rotations were only candidates, never saved to UE.
for p in (R/'FingerClearance').glob('A762__vertical*.json'):
    c=json.loads(p.read_text())
    if 'corrections' not in c:continue
    c['corrections'].pop('thumb_01_l',None);c['corrections'].pop('thumb_02_l',None)
    p.write_text(json.dumps(c,indent=2))
