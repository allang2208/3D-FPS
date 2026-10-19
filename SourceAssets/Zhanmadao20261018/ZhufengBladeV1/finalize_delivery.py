"""Record actual publication/build receipts; does not launch acceptance tests."""
import json,hashlib
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[2]
receipt=json.loads((P/'import_receipt.json').read_text(encoding='utf-8'))
builds={}
for target in ['FPSGAMEEditor','FPSGAME']:
    files=sorted(P.glob(f'build-{target}-receipt-zhufeng-*.json'))
    builds[target]=json.loads(files[-1].read_text(encoding='utf-8-sig')) if files else {'exit_code':None}
    if files:builds[target]['receipt']=files[-1].name
complete=receipt.get('assets_saved') and receipt.get('catalog_saved') and all(v.get('exit_code')==0 for v in builds.values())
receipt.update(native_build_pending=not complete,effects_applied=bool(complete),game_tested=False)
(P/'import_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
delivery={'id':'zhufeng','name':'逐风','weapon':'ue_zhanmadao','slot':'blade_1','tier':'legendary',
    'assets_saved':receipt.get('assets_saved',False),'asset_count':len(receipt['assets']),
    'catalog_saved':receipt.get('catalog_saved',False),'native_build_complete':bool(complete),'builds':builds,
    'game_tested':False,'multiplayer_tested':False,'editor_started':False,
    'animation':'existing standard/long-grip whirlwind; third-person upper-body layer over normal locomotion',
    'icon_generation':'built-in image_gen from actual mesh render and approved frame',
    'icon_prompt':'icon-prompt.txt','icon':'Export/Zhufeng_Icon_Framed.png',
    'source_blend':'Zhufeng_Blade_Editable.blend','production':'production.md'}
(P/'delivery.json').write_text(json.dumps(delivery,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
file=P.parent/'ZhufengBladeConceptV1/design.json';d=json.loads(file.read_text(encoding='utf-8'))
d['status']='assets_and_native_build_saved' if complete else 'assets_saved_native_build_pending'
d['game_tested']=False;file.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'assets_saved':delivery['assets_saved'],'asset_count':delivery['asset_count'],'native_build_complete':bool(complete),'game_tested':False}))
