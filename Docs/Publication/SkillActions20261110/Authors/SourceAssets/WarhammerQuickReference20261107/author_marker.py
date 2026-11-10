import bpy,json
from pathlib import Path
from mathutils import Vector
p=Path('D:/FPS3D/FPSGAME/SourceAssets/WarhammerQuickReference20261107')
bpy.ops.wm.open_mainfile(filepath='D:/FPS3D/FPSGAME/SourceAssets/SteelWarhammer20261014/QuickCombatLeftWristV7/Warhammer_QuickCombat_LeftWristV7_Editable.blend')
r=bpy.data.objects['SK_RusticPickaxe_Rig'];o=bpy.data.objects['SM_SteelWarhammer'];inv=r.data.bones['WPN_root'].matrix_local.inverted();verts=[inv@(r.matrix_world.inverted()@o.matrix_world@v.co) for v in o.data.vertices]
low=min(v.z for v in verts);cap=[v for v in verts if v.z<low+.003];point=sum(cap,Vector())/len(cap)
(p/'strike-marker.json').write_text(json.dumps(dict(kind='shaft butt',native=[point.x,-point.y,point.z],surface_vertices=len(cap)),indent=2))
header='#pragma once\n#include "CoreMinimal.h"\n// V8 shaft-butt surface in native WPN_root metres (socket carries 100x).\nnamespace WarhammerQuickCombat { inline const FVector StrikeLocal(%.9f,%.9f,%.9f); }\n'%(point.x,-point.y,point.z)
Path('D:/FPS3D/FPSGAME/Source/FPSGAME/Production/WarhammerQuickCombatMarker.h').write_text(header)
print('BUTT_MARKER',list(point))
