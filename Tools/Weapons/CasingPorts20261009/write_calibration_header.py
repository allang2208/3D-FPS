"""Emit measured runtime ports without reimporting shared weapon skeletons."""
import json
from pathlib import Path
O=Path(__file__).parent
D=json.loads((O/'calibration.json').read_text())
MATCH={
 'm4':'SK_M4_FoldingSights_HK416', 'hk416':'/Weapons/HK416/',
 'qbz191':'/Weapons/QBZ191/', 'a762':'/Weapons/A762/',
 'akm':'/Weapons/AKMIntegration/', 'ash12':'/Weapons/ASH12/',
 'm16a2':'/Weapons/M16A2/', 'svd':'/Weapons/SVDDragunov20260922/',
 'pkm_lowpoly':'/Weapons/PKMLowpoly20260922/', 'lmg201':'/Weapons/LMG201/',
 'm1911':'/M1911/', 'g18':'/Weapons/G18/',
 'pit_viper2011':'/Weapons/PitViper2011/', 'super90':'/Weapons/Super90/',
}
lines=['// Measured from the active meshes and compressed fire poses, 2026-10-09.',
 '// Source: Tools/Weapons/CasingPorts20261009/calibration.json',
 '#pragma once', '#include "CoreMinimal.h"', '', 'namespace CasingPortCalibration', '{',
 'struct FPort', '{', '    const TCHAR* MeshPathFragment;',
 '    FVector RootCentimetres;', '    const TCHAR* Anchor;', '    float OutwardSide;', '};',
 '// The native rig carries a 100x weapon root. Positions below are physical cm.',
 '// Left-hand pistols retain the unmirrored gun, including its ejection side.',
 'inline const FPort Ports[] =', '{']
for key,row in D.items():
 xyz=', '.join(f'{v:.6f}' for v in row['root_cm'])
 lines.append(f'    {{TEXT("{MATCH[key]}"), FVector({xyz}), TEXT("{row["anchor"]}"), {row["outward_side"]:.1f}f}}, // {key}')
lines += ['};', '', 'inline const FPort* Find(const FString& MeshPath)', '{',
 '    for (const FPort& Port : Ports)',
 '        if (MeshPath.Contains(Port.MeshPathFragment)) return &Port;',
 '    return nullptr;', '}', '}', '']
(O.parents[2]/'Source/FPSGAME/Weapons/CasingPortCalibration.h').write_text('\n'.join(lines),encoding='utf-8')
