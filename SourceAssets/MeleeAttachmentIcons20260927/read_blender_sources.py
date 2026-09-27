import bpy,json
from pathlib import Path
P=Path(__file__).resolve().parent;SRC=P.parent
paths=[
 'RuneSwordModules20260919/RuneSword_Modular_Editable.blend',
 'FrostSwordModules20260915/FrostSword_Modular_Editable.blend',
 'HighlandClaymoreMeshy20260922/JunctionBlendV5_20260927/Highland_ContinuousJunctionV5_Editable.blend',
 'HighlandClaymoreMeshy20260922/ThornCrownPommel20260927/Highland_ThornCrown_BakeSource.blend',
 'SharedSwordPommels20260920/SharedPommels_FrostFit.blend',
 'SixSharedSwordPommels20260920/SixSharedPommels_RuneFit.blend',
 'RuneSwordPommels20260920/RuneSword_Pommels_PBR.blend',
 'FrostSwordGrips20260919/shock_wrap/SM_FrostGrip_shock_wrap_Editable.blend',
 'FrostSwordPommelsRepair20260915/ballast_hardened/FrostPommel_Editable.blend',
 'FrostSwordPommelsRepair20260915/ballast_rune/FrostPommel_Editable.blend',
 'FrostSwordPommelsRepair20260915/ballast_magic_orb/FrostPommel_Editable.blend',
 'ToolEnhance20260925/Icons/axe_upright.blend',
 'ToolEnhance20260925/Icons/pickaxe_upright.blend',
]
result={}
for file in paths:
 path=SRC/file
 with bpy.data.libraries.load(str(path),link=False) as (a,b):
  result[file]={'objects':list(a.objects),'materials':list(a.materials)}
(P/'blender_sources.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print('ICON_AUTHOR_SOURCES_READY',flush=True)
