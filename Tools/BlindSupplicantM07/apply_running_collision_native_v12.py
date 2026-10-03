"""Switch native defaults only after the matching V12 assets have saved."""
import json
from pathlib import Path

PROJECT = Path('D:/FPS3D/FPSGAME')
receipt = json.loads((PROJECT/'SourceAssets/BlindSupplicantM07Meshy20261001/RunningCollisionV12/ue_running_collision_delivery_v12.json').read_text(encoding='utf-8-sig'))
if not receipt.get('saved'):
    raise RuntimeError('Save V12 assets before switching native default references.')
path = PROJECT/'Source/FPSGAME/Monsters/BlindSupplicantMonster.cpp'
source = path.read_text(encoding='utf-8-sig')
source = source.replace('SK_M07_OriginalV11.SK_M07_OriginalV11', 'SK_M07_OriginalV12.SK_M07_OriginalV12')
source = source.replace('SlowWalkClip = FindClip(TEXT("A_M07_SlowWalk"));',
    'static ConstructorHelpers::FObjectFinder<UAnimSequence> LargerWalk(TEXT("/Game/Monsters/BlindSupplicantM07/AnimationsRunningV12/A_M07_SlowWalk.A_M07_SlowWalk"));\n    SlowWalkClip = LargerWalk.Object;')
source = source.replace('ChaseClip = FindClip(TEXT("A_M07_Chase"));',
    'static ConstructorHelpers::FObjectFinder<UAnimSequence> RunningChase(TEXT("/Game/Monsters/BlindSupplicantM07/AnimationsRunningV12/A_M07_Chase.A_M07_Chase"));\n    ChaseClip = RunningChase.Object;')
path.write_text(source, encoding='utf-8')
print('M07_V12_NATIVE_MODEL_AND_TWO_LOCOMOTION_DEFAULTS_UPDATED', flush=True)
