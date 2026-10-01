"""Record actual production receipts, without launching tests or loading UE assets."""
import json
from pathlib import Path
O=Path(__file__).parent
assets=json.loads((O/'import_receipt.json').read_text())
icons=json.loads((O/'icon_import_receipt.json').read_text())
out={'weapon_id':'ue_hk416','weapon_name':'HK416',
 'asset_status':assets.get('status','incomplete'),'icon_status':icons.get('status','incomplete'),
 'source_components':61,'original_source_triangles':1505464,
 'saved_mesh':assets.get('mesh'),'saved_animation_count':len(assets.get('animations',{})),
 'saved_static_part_count':len(assets.get('static',{})),'saved_icon_count':len(icons.get('icons',{})),
 'native_build':{'status':'Succeeded','log':'Saved/BuildEditor/build-20260930-131148.log','kind':'Full editor module DLL, not a live patch'},
 'receipts':['import_receipt.json','icon_import_receipt.json','catalog_publication.json','material_build_receipt.json'],
 'notes':'Game, PIE, visual acceptance, performance and save/load testing were not run, per user instructions. User performs gameplay testing.',
 'interactive_editor_started':False,'game_started':False,'runtime_tested':False,
 'documentation':'Docs/Weapons/hk416-reworked-20260930.md'}
(O/'delivery.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(out,ensure_ascii=False,indent=2))
