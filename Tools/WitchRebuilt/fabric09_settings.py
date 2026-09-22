"""Shared artist settings; original 4 cm weave textures, no new raster assets."""
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/WitchRebuilt20260921')
OUT=ROOT/'Revision09'
DEST='/Game/Monsters/WitchRebuilt'
COLOR=(.072,.063,.046)
NORMAL_STRENGTH=.36
ROUGHNESS=.86
ROUGHNESS_DETAIL=.22
COLOR_DETAIL=.65
SPECULAR=.20
ROLES=('Master','Idle','Walk','CastPoison','Hit','TurnLeft','TurnRight','ThrowPoisonBottle','DeathBackward')
PARTS={
 'UpperRobe':('Witch_UpperRobe','MI_WitchRebuilt_UpperFabric09',1.),
 'LowerRobe':('Witch_OriginalRobe_Render','MI_WitchRebuilt_LowerFabric09',1.),
 'Lining':('WitchRebuilt_Lining','MI_WitchRebuilt_Lining09',.82),
}

def parameters(part,source):
 obj,_,shade=PARTS[part];groups=source[obj]['groups']
 regular=groups['original']['tile_repeat_4cm']
 repair=groups.get('repair',{}).get('tile_repeat_4cm',regular)
 return {'ClothColor':[c*shade for c in COLOR],'WeaveTiling':regular,'RepairWeaveTiling':repair,
  'NormalStrength':NORMAL_STRENGTH,'Roughness':ROUGHNESS,'RoughnessDetail':ROUGHNESS_DETAIL,
  'ColorDetail':COLOR_DETAIL,'Specular':SPECULAR}
