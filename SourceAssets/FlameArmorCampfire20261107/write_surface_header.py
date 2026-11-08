"""Write the runtime table from a completed geometry extraction."""
import json
from pathlib import Path

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = Path(__file__).resolve().parent


def write(rows):
    lines = ['#pragma once', '#include "CoreMinimal.h"',
        '// Generated from installed blade triangles by FlameArmorCampfire20261107/build_surface_profiles.py.',
        'namespace FlameArmorSurfaces {',
        'struct FProfile {const TCHAR* Mesh;int32 Axis;float Start,End;FVector4 Sections[8];};',
        'inline const FProfile Profiles[]={']
    for row in rows:
        sections = ','.join('FVector4('+','.join(f'{n:.6f}' for n in s)+')' for s in row['sections'])
        lines.append('    {TEXT("%s"),%d,%.7ff,%.7ff,{%s}},' % (row['mesh'], row.get('axis', 2), row['start'], row['end'], sections))
    lines += ['};', '}']
    (ROOT/'Source/FPSGAME/Skills/FlameArmorSurfaceProfiles.h').write_text('\n'.join(lines)+'\n', encoding='utf-8')


if __name__ == '__main__':
    write(json.loads((OUT/'surface-profiles.json').read_text(encoding='utf-8'))['profiles'])
