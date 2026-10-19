import json
from pathlib import Path
from datetime import datetime
P=Path(__file__).resolve().parent
read=lambda file:json.loads((P/file).read_text('utf-8-sig'))
assets=read('publication.json')
builds=[read('build-'+target+'-receipt-double-heavy-01.json') for target in ('FPSGAMEEditor','FPSGAME')]
if not assets.get('published') or any(b['exit_code'] for b in builds):raise RuntimeError('Asset publication or required build unfinished')
receipt={'name':'赤霄','weapon':'ue_zhanmadao','slot':'blade_1','option':'chixiao','effect':'赤霄双斩',
 'completed_at':datetime.now().astimezone().isoformat(),'assets_saved':True,'catalog_saved':True,'effects_applied':True,
 'animations':assets['clips'],'native_builds':builds,'hits':2,'damage_per_hit':'full_heavy_strike',
 'category':'martial','charge_and_stamina':'one_original_charge_double_release_cost','release_stamina_multiplier':2,'runtime_tested':False,'visual_acceptance':False}
(P/'delivery.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('CHIXIAO_DOUBLE_HEAVY_DELIVERED',len(assets['assets']),flush=True)
