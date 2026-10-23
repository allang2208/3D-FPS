from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
P=Path(__file__).resolve().parent;ROOT=P.parents[2]
saved=json.loads((P/'import_receipt.json').read_text('utf-8-sig'))
built=json.loads((P/'build_receipt.json').read_text('utf-8-sig'))
if not saved.get('installed_to_main_project'):raise RuntimeError('Finish saving and installing the new HUD material first')
if not {'FPSGAME','FPSGAMEEditor'}<={r['target'] for r in built['targets'] if r['exit_code']==0}:raise RuntimeError('Finish native material-path builds first')
record={'complete':True,'saved_at_utc':datetime.now(timezone.utc).isoformat(),'weapon':'ue_runebound_warhammer',
 'scope':'left energy HUD upper cap completed as a vertical mirror of its retained lower cap',
 'material':saved['asset'],'installed_files':saved['installed_files'],'builds':built['targets'],
 'layout':json.loads((P/'cap_layout.json').read_text('utf-8')),
 'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [P/'RuneboundEnergyHud.hlsl',ROOT/'Source/FPSGAME/Production/RuneboundHammerTuning.h']},
 'gameplay_modified':False,'shared_azure_dragon_modified':False,'tests_run':False,'game_started':False,'editor_ui_started':False,'rendered_acceptance':False}
(P/'delivery_receipt.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
print('RUNEBOUND_SYMMETRIC_CAPS_DELIVERED',saved['asset'])
