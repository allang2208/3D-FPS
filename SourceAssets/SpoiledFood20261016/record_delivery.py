"""Record actual source, saved asset and compile delivery, without running tests."""
import json,hashlib
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path('D:/FPS3D/FPSGAME');OUT=Path(__file__).resolve().parent
def read(name):return json.loads((OUT/name).read_text(encoding='utf-8-sig'))
builds=[json.loads(p.read_text(encoding='utf-8-sig')) for p in sorted(OUT.glob('2026*/result.json'))]
editor_succeeded=any('FPSGAMEEditor' in b['targets'] and b['builds']=='Succeeded' for b in builds)
files=[
    'Source/FPSGAME/UI/ColdSteelFoodPresentation.h','Source/FPSGAME/UI/ColdSteelInventoryPresentation.cpp',
    'Source/FPSGAME/UI/ColdSteelInventoryWidget.h','Source/FPSGAME/UI/ColdSteelItemTooltip.h',
    'Source/FPSGAME/UI/ColdSteelItemTooltip.cpp','Source/FPSGAME/UI/ColdSteelItemTooltipLayout.cpp',
    'Source/FPSGAME/UI/ColdSteelItemTooltipData.h','Source/FPSGAME/UI/ColdSteelItemTooltipData.cpp',
    'Source/FPSGAME/UI/ColdSteelInventoryRules.cpp','Source/FPSGAME/UI/ColdSteelPickupConsumable.cpp',
    'Source/FPSGAME/Items/SpoiledFoodVisuals.h','Source/FPSGAME/Items/FoodSpoilageAuditCommandlet.cpp',
    'Config/DefaultGame.ini','Content/ColdSteelData/items.json','Content/ColdSteelData/Icons/spoiled_food.png',
]
report={'created_utc':datetime.now(timezone.utc).isoformat(),'asset_preparation':read('preparation.json'),
    'ue_assets':read('ue-assets.json'),'catalog':read('catalog-published.json'),'builds':builds,
    'editor_build':{'status':'Succeeded' if editor_succeeded else 'Blocked by unrelated alchemy compilation errors',
        'previous_failed_attempt':'20261016-204918/FPSGAMEEditor.log'},
    'files':[{'path':p,'sha256':hashlib.sha256((ROOT/p).read_bytes()).hexdigest()} for p in files],
    'stages':[{'from':0,'until':.5,'color':'Success green'},{'from':.5,'until':.8,'color':'Warning yellow'},{'from':.8,'through':1,'color':'Danger red'}],
    'display':'progress bars only; countdown, lifetime text and percentage text removed',
    'user_revision':'compact chunks only; strips and strands removed; icon regenerated',
    'game_or_pie_started':False,'runtime_tests_run':False,'stage_color_scope':'Source routing and threshold inspection only',
    'model_preview_scope':'Requested inventory icon rendered from actual final model',
    'acceptance':'User gameplay/visual test pending'}
(OUT/'delivery.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'saved':'delivery.json','builds':builds,'packages':len(report['ue_assets']['saved_packages'])},ensure_ascii=False))
