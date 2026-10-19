import json
from datetime import datetime
from pathlib import Path

P=Path(__file__).resolve().parent
read=lambda file:json.loads((P/file).read_text('utf-8-sig'))
saved=read('install-receipt.json')
if not saved.get('complete'):
    raise RuntimeError('Both shoulder animation saves must finish')
review=read('shoulder-review.json')
receipt={
    'revision':'ChixiaoShoulderV3','finished':datetime.now().astimezone().isoformat(),
    'assets_saved':True,'animations':saved['animations'],
    'requested_shoulder_inspection':True,'offline_visual_review':True,
    'runtime_play_tested':False,'native_code_changed':False,'native_build_required':False,
    'damage_timing_blade_path_changed':False,'metrics':review}
(P/'delivery.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('CHIXIAO_SHOULDER_V3_DELIVERED',flush=True)
