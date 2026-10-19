"""Record production outcomes; no gameplay or visual acceptance is run."""
import json
from pathlib import Path
P=Path(__file__).resolve().parent
builds={}
for target in ['FPSGAMEEditor','FPSGAME']:
    files=sorted(P.glob(f'build-{target}-*-receipt.json'))
    builds[target]=json.loads(files[-1].read_text(encoding='utf-8-sig')) if files else {'exit_code':None}
    if files:builds[target]['receipt']=files[-1].name
complete=all(b.get('exit_code')==0 for b in builds.values())
publication=json.loads((P/'publication.json').read_text(encoding='utf-8'))
(P/'delivery.json').write_text(json.dumps({
    'revision':'ZhufengCyanTrailV1','source_saved':True,'assets':publication,
    'native_build_complete':complete,'builds':builds,'game_tested':False,
    'visual_tested':False,'editor_started':False,
    'coverage':['first_person','third_person','remote_cosmetic_state'],
    'activation':'Zhufeng blade installed, during the spin phase of dash or manual whirlwind',
    'palette_priority':'Zhufeng whirlwind cyan; Chixiao heavy crimson; other Beiwei martial gold',
    'ribbon_budget':{'sample_limit':48,'lifetime_seconds':0.24}},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
if complete:
    for folder,filename in [('ZhufengWhirlwindMotionV2','delivery.json'),('ZhufengBladeV1','import_receipt.json')]:
        path=P.parent/folder/filename
        data=json.loads(path.read_text(encoding='utf-8-sig'))
        data.update(native_build_complete=True,native_build_pending=False,
                    editor_build_complete=True,game_build_complete=True,
                    superseding_build='../ZhufengCyanTrailV1/delivery.json')
        path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('ZHUFENG_CYAN_DELIVERY_RECORDED',complete)
