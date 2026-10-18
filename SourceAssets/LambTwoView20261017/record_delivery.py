import json,hashlib
from pathlib import Path
O=Path(__file__).parent;R=O.parents[1]
imports=json.loads((O/'import_receipt.json').read_text());build=sorted(O.glob('20*/result.json'))[-1]
def rec(p):
    f=R/p;return dict(path=p,bytes=f.stat().st_size,sha256=hashlib.sha256(f.read_bytes()).hexdigest())
paths=['Source/FPSGAME/Characters/FPSBodyConsumePose.inl','Source/FPSGAME/Characters/FPSPlayerBodyAnimInstance.cpp','Content/ColdSteelData/player_body.json','Content/ColdSteelData/potion_use_motion.json','SourceAssets/FoodGrip20261003/lamb_food_motion.py','SourceAssets/LargeLamb20261014/grip_profile.json','Binaries/Win64/UnrealEditor-FPSGAME.dll','Binaries/Win64/FPSGAME.exe']
report=dict(scope='Large lamb third-person complete dual arms and first-person downward exit',files=[rec(p) for p in paths],asset=imports,
    build=dict(path=str(build.relative_to(R)),result=json.loads(build.read_text(encoding='utf-8-sig'))),offline_reviews=['fps_exit_review.json','body_fit.json','body_surface_review.json'],
    game_or_pie_started=False,editor_ui_started=False,runtime_visual_acceptance='Pending user test')
report['saved_asset_file']=rec('Content/'+imports['asset'].split('.')[0].removeprefix('/Game/')+'.uasset')
(O/'delivery.json').write_text(json.dumps(report,indent=2));print('LAMB_TWO_VIEW_DELIVERED')
