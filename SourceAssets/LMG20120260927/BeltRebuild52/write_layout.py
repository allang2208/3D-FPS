"""Generate the matching native feed layout from the authored model data."""
import json
from pathlib import Path
O=Path(__file__).parent;P=O.parents[2];d=json.loads((O/'layout.json').read_text())
def v(x):return 'FVector('+','.join('%.10g'%n for n in x)+')'
lines=['#pragma once','#include "CoreMinimal.h"','// BeltRebuild52: six reload contacts, two receiver cells and one hidden return.','namespace LMG201BeltLayout','{','inline constexpr int32 CellCount=9;','inline constexpr int32 ReloadContactCount=6;','inline constexpr double FirstSlot=-3.;','inline constexpr int32 SlotByCell[]={0,1,2,3,4,5,6,-1,-2};']
for name,values in [('Centers',d['centers_bone_local'][0]),('NewCenters',d['centers_bone_local'][1]),('Guide',d['guide_root_m'])]:lines.append('inline const FVector '+name+'[] = {'+','.join(map(v,values))+'};')
for side,name in enumerate(['Idle','NewIdle']):
 lines.append('inline const FTransform '+name+'[] = {')
 for t in d['idle_bone_local'][side]:lines.append('FTransform(FQuat('+','.join('%.10g'%n for n in t['q'])+'),'+v(t['p'])+','+v(t['s'])+'),')
 lines.append('};')
lines.append('}')
(P/'Source/FPSGAME/Weapons/LMG201BeltLayout.h').write_text('\n'.join(lines)+'\n')
