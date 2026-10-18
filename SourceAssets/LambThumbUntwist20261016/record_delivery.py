"""Record the saved source/data and actual background build results."""
import hashlib, json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = Path(__file__).resolve().parent
build = OUT/'20261016-202452'
result = json.loads((build/'result.json').read_text(encoding='utf-8-sig'))
paths = [
    'Source/FPSGAME/Items/PotionArmPose.cpp',
    'Source/FPSGAME/Items/PotionUseMotion.cpp',
    'Source/FPSGAME/Items/PotionUseMotion.h',
    'Content/ColdSteelData/potion_use_motion.json',
    'SourceAssets/FoodGrip20261003/large_lamb_natural_grasp.json',
    'SourceAssets/LargeLamb20261014/grip_profile.json',
]
def receipt(relative):
    path = ROOT/relative
    return {'path':relative, 'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'bytes':path.stat().st_size,
            'modified_utc':datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()}

data = {
    'scope':'roasted_large_lamb first-person left/right thumb roll correction',
    'created_utc':datetime.now(timezone.utc).isoformat(),
    'source_and_data':[receipt(p) for p in paths],
    'build':result,
    'build_logs':[str((build/(t+'.log')).relative_to(ROOT)) for t in result['targets']],
    'binaries':[receipt(p) for p in ['Binaries/Win64/UnrealEditor-FPSGAME.dll', 'Binaries/Win64/FPSGAME.exe']],
    'saved_uassets':'No uasset changes needed: runtime pose solver and JSON authoring recipe.',
    'diagnosis':'SourceAssets/LambThumbUntwist20261016/diagnosis.json',
    'preserved':['food mesh','four fingers','palm poses','grip axes','bone translations/scales/weights','food trajectory','6s duration','4.65s contact'],
    'editor_launched':False, 'game_or_pie_run':False, 'new_preview_rendered':False,
    'runtime_visual_acceptance':'Pending user test',
}
(OUT/'delivery.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'saved':'SourceAssets/LambThumbUntwist20261016/delivery.json','build':result},ensure_ascii=False))
