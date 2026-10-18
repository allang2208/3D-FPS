import json,hashlib
from pathlib import Path
from datetime import datetime,timezone
O=Path(__file__).parent;R=O.parents[1]
builds=sorted(O.glob('20*/result.json'))
if not builds:raise RuntimeError('No successful build receipt yet')
build=builds[-1];result=json.loads(build.read_text(encoding='utf-8-sig'))
def record(relative):
    p=R/relative
    return dict(path=relative,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),modified_utc=datetime.fromtimestamp(p.stat().st_mtime,timezone.utc).isoformat())
receipt=dict(scope='roasted_large_lamb two-hand V8 native-joint thumb grip',completed_utc=datetime.now(timezone.utc).isoformat(),
    mesh_identity=json.loads((O/'diagnosis_before.json').read_text()),
    source=[record(p) for p in ['Source/FPSGAME/Items/PotionArmPose.cpp','Source/FPSGAME/Items/PotionUseMotion.cpp','Source/FPSGAME/Items/PotionUseMotion.h','Content/ColdSteelData/potion_use_motion.json','SourceAssets/FoodGrip20261003/large_lamb_natural_grasp.json','SourceAssets/LargeLamb20261014/grip_profile.json']],
    build=dict(receipt=str(build.relative_to(R)),result=result),
    binaries=[record(p) for p in ['Binaries/Win64/UnrealEditor-FPSGAME.dll','Binaries/Win64/FPSGAME.exe']],
    saved_uassets='No mesh or texture changes. Current Traversal package already equals saved V8; grip is runtime C++ and JSON.',
    scoped_offline_review='SourceAssets/LambGripV8_20261017/saved_pose_review.json',
    editor_ui_started=False,game_or_pie_started=False,runtime_visual_acceptance='Pending user test')
(O/'delivery.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('LAMB_V8_GRIP_DELIVERED',result)
