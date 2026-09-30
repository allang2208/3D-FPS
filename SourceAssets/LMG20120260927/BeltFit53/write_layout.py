import json
from pathlib import Path
O=Path(__file__).parent;P=O.parents[2];d=json.loads((O/'layout.json').read_text())
def v(x):return 'FVector('+','.join('%.10g'%n for n in x)+')'
def q(x):return 'FQuat('+','.join('%.10g'%n for n in x)+')'
lines=['#pragma once','#include "CoreMinimal.h"','// BeltFit53: articulated chain with a pouch reservoir and receiver run.','namespace LMG201BeltLayout','{','inline constexpr int32 CellCount=14;','inline constexpr int32 LinkCount=14;','inline constexpr int32 ReloadContactCount=6;','inline constexpr double FirstSlot=-3.;','inline constexpr int32 SlotByCell[]={'+','.join(map(str,d['slot_by_cell']))+'};']
lines+=['inline constexpr int32 LinkA[]={'+','.join(str(a) for a,b in d['pairs'])+'};','inline constexpr int32 LinkB[]={'+','.join(str(b) for a,b in d['pairs'])+'};','inline constexpr double LinkLength[]={'+','.join('%.10g'%v for v in d['link_lengths_root'])+'};','inline const FQuat LinkFrame[]={'+','.join(map(q,d['link_frames_root']))+'};']
for name,values in [('Centers',d['centers_bone_local'][0]),('NewCenters',d['centers_bone_local'][1]),('Axis',d['axis_bone_local'][0]),('NewAxis',d['axis_bone_local'][1]),('LinkCenters',d['link_centers_bone_local'][0]),('NewLinkCenters',d['link_centers_bone_local'][1]),('Guide',d['guide_root_m'])]:lines.append('inline const FVector '+name+'[] = {'+','.join(map(v,values))+'};')
for key,names in [('idle_bone_local',['Idle','NewIdle']),('link_idle_bone_local',['LinkIdle','NewLinkIdle'])]:
 for side,name in enumerate(names):
  lines.append('inline const FTransform '+name+'[] = {')
  for t in d[key][side]:lines.append('FTransform('+q(t['q'])+','+v(t['p'])+','+v(t['s'])+'),')
  lines.append('};')
lines.append('}')
(P/'Source/FPSGAME/Weapons/LMG201BeltLayout.h').write_text('\n'.join(lines)+'\n')
