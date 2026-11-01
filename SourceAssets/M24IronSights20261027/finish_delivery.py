import json,re
from pathlib import Path
O=Path(__file__).resolve().parent
assets=json.loads((O/'install_receipt.json').read_text())
registration=json.loads((O/'registration_receipt.json').read_text())
build=json.loads((O/'build_receipt.json').read_text())
if not assets['complete']:raise RuntimeError('Sight asset save remains incomplete')
console=(O/'build_console.log').read_text(encoding='utf-8-sig',errors='replace')
logs=re.findall(r'Log: (.+)',console)
install=(O/'install_console.log').read_text(encoding='utf-8-sig',errors='replace')
R={'assets_saved':True,'saved':assets['saved'],'no_optic_visual':registration['no_optic_visual'],
   'editor_build':build['editor_build'],'build_log':logs[-1].strip() if logs else None,
   'install_process_shutdown_error':'Critical error:' in install,
   'interactive_editor_started':False,'runtime_tested':False,
   'report':'Docs/Weapons/m24-mechanical-sights-20261027.md'}
(O/'delivery.json').write_text(json.dumps(R,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(R,ensure_ascii=False))
