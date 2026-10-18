import hashlib,json
from pathlib import Path
O=Path(__file__).parent;R=O.parents[1]
builds={}
for target in ['Game','Editor']:
    receipts=sorted(O.glob(f'Build-*-{target}/result.json'))
    if not receipts:raise RuntimeError('Build still pending: '+target)
    p=receipts[-1];builds[target]={'receipt':str(p.relative_to(R)),**json.loads(p.read_text(encoding='utf-8-sig'))}
sources=['Source/FPSGAME/Weapons/TacticalDeviceComponent.cpp','Source/FPSGAME/Characters/FPSPlayerBodyLaser.cpp']
report={'scope':'Suppress independent tactical effects and cached/remote laser samples during the complete two-hand large-lamb use, retaining configured toggle state.',
 'builds':builds,'source_sha256':{p:hashlib.sha256((R/p).read_bytes()).hexdigest() for p in sources},
 'assets_changed':False,'live_coding_used':False,'game_or_pie_started':False,'tested':False,'acceptance':'user testing pending'}
(O/'delivery.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('CONSUMABLE_LASER_DELIVERED',list(builds))
