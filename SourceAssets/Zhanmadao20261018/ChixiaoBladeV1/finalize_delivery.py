"""Record production saves and required build receipts; no runtime checks."""
import json
from pathlib import Path
from datetime import datetime
P=Path(__file__).resolve().parent
def read(name):return json.loads((P/name).read_text(encoding='utf-8-sig'))
assets=read('import_receipt.json');publication=read('publication_receipt.json')
builds=[read('editor-build-receipt.json'),read('game-build-receipt.json')]
if not assets.get('complete') or publication['exit_code'] or any(b['result']!='Succeeded' for b in builds):raise RuntimeError('Save or build incomplete')
receipt={'name':'赤霄','definition':'ue_zhanmadao','slot':'blade_1','option':'chixiao','scope':'appearance_only',
    'completed_at':datetime.now().astimezone().isoformat(),'assets_saved':True,'catalog_saved':True,
    'asset_count':len(assets['assets']),'mesh':assets['mesh'],'lod_triangles':read('exports.json')['lod_triangles'],
    'native_builds':builds,'effects_applied':False,'game_tested':False,'visual_acceptance':False,
    'source':'Chixiao_Blade_Editable.blend','icon':'Export/Chixiao_Icon_Framed.png'}
(P/'delivery.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('CHIXIAO_DELIVERY_SAVED',receipt['asset_count'])
