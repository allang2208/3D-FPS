"""Record the requested multiplier and copy change, with actual native build outcomes."""
import json
from pathlib import Path
P=Path(__file__).resolve().parent
builds={}
for target in ['FPSGAMEEditor','FPSGAME']:
    files=sorted(P.glob(f'build-{target}-*-receipt.json'))
    builds[target]=json.loads(files[-1].read_text(encoding='utf-8-sig')) if files else {'exit_code':None}
    if files:builds[target]['receipt']=files[-1].name
(P/'delivery.json').write_text(json.dumps({
    'revision':'ZhufengDamageBonusV1','source_saved':True,
    'catalog':json.loads((P/'publication.json').read_text(encoding='utf-8')),
    'native_build_complete':all(v.get('exit_code')==0 for v in builds.values()),
    'builds':builds,'game_tested':False,'editor_started':False},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('ZHUFENG_DAMAGE_BONUS_DELIVERY_RECORDED')
