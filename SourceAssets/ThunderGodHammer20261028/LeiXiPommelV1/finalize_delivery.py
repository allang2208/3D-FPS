"""Record completed production from the build and import receipts; no gameplay tests."""
from pathlib import Path
import json
P=Path(__file__).resolve().parent
receipt=json.loads((P/'import_receipt.json').read_text(encoding='utf-8-sig'))
build_path=max(P.glob('build-*-receipt.json'),key=lambda p:p.stat().st_mtime)
build=json.loads(build_path.read_text(encoding='utf-8-sig'))
if not receipt['complete'] or build['exit_code']!=0:raise RuntimeError('Production has not finished')
data={'id':'lei_xi_pommel','name':'雷息配重','weapon':'ue_thunder_god_hammer','slot':'pommel','tier':'special',
 'stage':'implemented_not_gameplay_tested','model_created':True,'assets_saved':True,'native_build_succeeded':True,
 'build_receipt':build_path.name,'import_receipt':'import_receipt.json','saved_asset_count':len(receipt['saved_assets']),
 'mesh':receipt['mesh'],'icon':receipt['icon'],'passives':{'attack_speed_mult':1.15,'stamina_mult':.85},
 'buff':{'id':'magicInspiration','duration_seconds':10,'attack_speed_mult':1.25,'refresh_not_stack':True},
 'concept':'../LeiXiPommelConceptV1/lei_xi_pommel_concept_v1.png','editable':'LeiXiPommelV1_Editable.blend',
 'icon_method':'Actual current mesh render plus built-in imagegen standard grayscale frame',
 'background_only':True,'runtime_tested':False,'multiplayer_tested':False}
(P/'delivery.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
concept=P.parent/'LeiXiPommelConceptV1/concept.json';c=json.loads(concept.read_text(encoding='utf-8-sig'));c.update(stage='implemented_not_gameplay_tested',runtime_implemented=True,model_created=True,production='../LeiXiPommelV1/delivery.json');concept.write_text(json.dumps(c,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'production':'saved','asset_count':data['saved_asset_count'],'build':build['exit_code'],'tested':False},ensure_ascii=False))
