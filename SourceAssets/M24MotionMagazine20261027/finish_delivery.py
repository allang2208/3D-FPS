"""Summarize production receipts; this does not run validation or gameplay."""
import json
from pathlib import Path
O=Path(__file__).resolve().parent
assets=json.loads((O/'install_receipt.json').read_text())
icons=json.loads((O/'icon_receipt.json').read_text())
catalog=json.loads((O/'registration_receipt.json').read_text())
build=json.loads((O/'build_receipt.json').read_text())
if not assets['complete'] or not icons['complete']:raise RuntimeError('An import remains incomplete')
result={'assets_saved':True,'saved_asset_count':len(assets['saved']),'icons_saved':True,'saved_ui_texture_count':len(icons['saved']),
 'default_capacity':catalog['default_capacity'],'extended_capacity':catalog['extended_capacity'],
 'extended_magazine_option':catalog['option'],'sprint_clips':['sprint_enter','sprint_loop','sprint_exit'],
 'extended_reload_profile':assets['magazine_profile'],'editor_build':build['editor_build'],
 'build_log':'Saved/BuildEditor/build-20261027-192125.log','interactive_editor_started':False,
 'runtime_tested':False,'report':'Docs/Weapons/m24-motion-magazine-20261027.md'}
(O/'delivery.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,ensure_ascii=False))
