"""Export the actual hammer-head station from the saved uppercut authoring rig."""
import bpy
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent;R=P.parents[2]
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'UppercutRightAnatomyV7/Warhammer_Uppercut_RightAnatomy_Editable.blend'))
rig=bpy.data.objects['SK_RusticPickaxe_Rig'];scene=bpy.context.scene
points=[]
for k in range(31):
    scene.frame_set(240+k)
    p=rig.pose.bones['WPN_root'].matrix@Vector((0,0,.972475657))
    points.append((p.y*100,p.x*100,p.z*100))
header='#pragma once\n#include "CoreMinimal.h"\n// Authored hammer-head arc, source seconds 1.0..1.125; no cosmetic camera offset.\nnamespace WarhammerUppercutArc\n{\n    inline const FVector Head[]={\n'
header+=''.join('        FVector(%.6f,%.6f,%.6f),\n'%p for p in points)
header+='    };\n    inline FVector Sample(float T)\n    {\n        const float F=FMath::Clamp((T-1.f)*240.f,0.f,30.f);\n        const int32 I=FMath::Min(29,FMath::FloorToInt(F));\n        return FMath::Lerp(Head[I],Head[I+1],F-I);\n    }\n}\n'
(R/'Source/FPSGAME/Production/WarhammerUppercutArc.h').write_text(header,encoding='utf-8')
print('UPPERCUT_CONTACT_ARC_WRITTEN')
