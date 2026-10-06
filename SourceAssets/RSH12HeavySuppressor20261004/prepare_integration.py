"""Prepare WS material channels and the measured native RSH mount constant."""
import json
from pathlib import Path
import numpy as np
from PIL import Image

O=Path(__file__).resolve().parent; P=O.parents[1]
auth=json.loads((O/'authoring.json').read_text(encoding='utf8'))
align=np.array(json.loads((O.parent/'RSH12Speedloader20261003/Single/authoring.json').read_text(encoding='utf8'))['alignment'])
reflect=np.diag([1.,-1.,1.,1.])
canonical=np.array(auth['interface']['accessory_to_canonical_m'])
root=reflect@align@canonical
point=root[:3,3]; forward=root[:3,0]; up=root[:3,2]
def vec(v): return 'FVector('+','.join(f'{x:.10f}f' for x in v)+')'
header='''#pragma once
#include "CoreMinimal.h"

// Generated from the original RSH muzzle annulus and current native gun registration.
namespace RSH12MuzzleAssets
{
inline constexpr const TCHAR* Part = TEXT("rsh12_heavy_suppressor");
inline constexpr const TCHAR* MeshPath = TEXT("/Game/Weapons/RSH12/HeavySuppressor20261004/SM_RSH12_HeavySuppressor");
inline constexpr float LengthCM = 18.f;
inline FTransform Mount()
{
    return FTransform(FRotationMatrix::MakeFromXZ(FORWARD, UP).ToQuat(), POINT, FVector(.01f));
}
}
'''.replace('FORWARD',vec(forward)).replace('UP',vec(up)).replace('POINT',vec(point))
cube=O.parent/'RSH12CubeSuppressor20261004'
if (cube/'catalog_receipt.json').exists():
    import runpy
    runpy.run_path(str(cube/'publish_runtime.py'),run_name='__main__')
else:
    (P/'Source/FPSGAME/Weapons/RSH12MuzzleAssets.h').write_text(header,encoding='utf8')
for part, spec in auth['textures'].items():
    orm=np.array(Image.open(O/spec['orm']).convert('RGB'))
    rough=O/'Textures'/f'T_RSH12_Heavy_{part}_Roughness.png'
    mask=O/'Textures'/f'T_RSH12_Heavy_{part}_SurfaceMask.png'
    Image.fromarray(orm[:,:,1]).save(rough)
    channels=np.zeros((*orm.shape[:2],4),dtype=np.uint8);channels[:,:,2]=orm[:,:,0];channels[:,:,3]=255
    Image.fromarray(channels).save(mask)
    spec['roughness_texture']=str(rough.relative_to(O));spec['surface_mask']=str(mask.relative_to(O))
(O/'integration_inputs.json').write_text(json.dumps(dict(textures=auth['textures'],mount_point_root_m=point.tolist(),forward_root=forward.tolist(),up_root=up.tolist(),source_alignment=align.tolist(),runtime_tested=False),indent=2),encoding='utf8')
print('RSH_SUPPRESSOR_INTEGRATION_INPUTS_WRITTEN')
