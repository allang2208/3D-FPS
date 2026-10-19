"""Record the production save and required build receipts; does not run tests."""
import json
from pathlib import Path
from datetime import datetime
P=Path(__file__).resolve().parent
assets=json.loads((P/'import_receipt.json').read_text(encoding='utf-8'))
publication=json.loads((P/'publication_receipt.json').read_text(encoding='utf-8-sig'))
builds={target:json.loads((P.parent/('build-'+target+'-receipt-beiwei-01.json')).read_text(encoding='utf-8-sig'))
        for target in ['FPSGAMEEditor','FPSGAME']}
if not assets.get('complete') or publication['exit_code'] or any(b['exit_code'] for b in builds.values()):
    raise RuntimeError('Production save/build still incomplete')
delivery={'completed_at':datetime.now().astimezone().isoformat(),'assets_saved':True,'catalog_saved':True,
    'asset_count':len(assets['assets']),'native_materials':7,'temporal_materials':7,'sword_qi_materials':1,
    'mask_textures':1,'icon_textures':1,'icon_png_saved':True,'builds':builds,
    'scope':'ue_zhanmadao blade_2 beiwei_rune; martial damage x1.5, martial range x1.25',
    'restart':'Restart the game or stop PIE and begin again to reload the compiled module and catalog.',
    'game_tested':False,'multiplayer_tested':False,'visual_acceptance':False}
(P/'delivery.json').write_text(json.dumps(delivery,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
design=json.loads((P/'design.json').read_text(encoding='utf-8'))
design.update(status='integrated_saved',game_integrated=True,tests_run=False)
(P/'design.json').write_text(json.dumps(design,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('BEIWEI_DELIVERY_SAVED',delivery['asset_count'])
