import json
from pathlib import Path
from datetime import datetime
P=Path(__file__).resolve().parent
read=lambda file:json.loads((P/file).read_text('utf-8-sig'))
saved=read('install-receipt.json');checks=read('contact-check.json')
transport='isolated_commandlet' if (P/'asset-publication.json').exists() and read('asset-publication.json').get('published') else ('existing_editor' if (P/'editor-save-state.json').exists() and read('editor-save-state.json').get('state')=='saved' else 'commandlet')
if not saved.get('complete') or (transport=='commandlet' and read('commandlet-receipt.json')['exit_code']):raise RuntimeError('The animation save is not complete')
receipt={'revision':'ChixiaoGripV2','finished':datetime.now().astimezone().isoformat(),
 'assets_saved':True,'save_transport':transport,'animations':saved['animations'],'native_code_changed':False,'native_build_required':False,
 'requested_hand_inspection':True,'offline_visual_review':True,'runtime_play_tested':False,
 'damage_timing_blade_path_changed':False,'metrics':{v:{'before':d['V1']['peaks'],'after':d['V2']['peaks'],
 'weapon_max_delta_cm':d['weapon_max_delta_cm']} for v,d in checks.items()}}
(P/'delivery.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
previous=P.parent/'ChixiaoDoubleHeavyV1/production.md'
note='\n\n当前第一人称握持修订：`../ChixiaoGripV2/production.md`，以 V2 的作者源和导入入口维护手部；V1 双斩的刀路、时钟与伤害合同保留。\n'
text=previous.read_text('utf-8')
if '当前第一人称握持修订' not in text:previous.write_text(text+note,encoding='utf-8')
print('CHIXIAO_GRIP_V2_DELIVERED',flush=True)
