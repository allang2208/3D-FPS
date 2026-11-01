import json,re
from pathlib import Path
O=Path(__file__).resolve().parent
assets=json.loads((O/'install_receipt.json').read_text());build=json.loads((O/'build_receipt.json').read_text())
if not assets['complete']:raise RuntimeError('Import remains incomplete')
logs=re.findall(r'Log: (.+)',(O/'build_console.log').read_text(encoding='utf-8-sig',errors='replace'))
R={'saved_profiles':assets['saved'],'assets_saved':True,'editor_build':build['editor_build'],'build_log':logs[-1].strip() if logs else None,
 'fix':'native-axis left support fingers; shared hold and transitions; exact existing mag10 arm layer',
 'mesh_replaced':False,'animations_replaced':False,'interactive_editor_started':False,'runtime_tested':False,
 'asset_process_exit':'failed after assets were saved; UColdSteelSkillPage::ReleaseSlateResources shutdown access violation',
 'asset_process_log':'SourceAssets/M24SupportGrip20261027/install.log',
 'report':'Docs/Weapons/m24-support-grip-20261027.md'}
(O/'delivery.json').write_text(json.dumps(R,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(R,ensure_ascii=False))
