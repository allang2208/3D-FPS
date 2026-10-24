"""Host tower in final UE world metres; playable apartment stays at Z=0."""
from pathlib import Path
ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parents[2]
BASE='/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV11'
MAP='/Game/GameMaps/L_CyberpunkApartment'
OWNER='CyberpunkApartment.RefinementV11'
# Near-bank surface is (3-90)*1.25 = -108.75 m. Foundations extend below it.
GROUND=-108.75
FLOOR=4.4
MAIN=(-6.,-30.,36.,1.2)
UPPER=(-2.5,-26.,32.5,-1.)
PLAYABLE_CLEARANCE=(-5.2,-25.3,30.35,5.4,-.03,5.90)
SECTIONS=[
 dict(key='LowerA',bounds=MAIN,z=-97.35,count=10,floor_start=0),
 dict(key='LowerB',bounds=MAIN,z=-53.35,count=12,floor_start=10),
 dict(key='UpperA',bounds=MAIN,z=6.2,count=10,floor_start=23),
 dict(key='UpperB',bounds=UPPER,z=50.2,count=6,floor_start=33),
]
SUB='/Game/SubstrateMaterials/Textures/'
PAINT='/Game/Dungeons/FacilityTransit20261007/RefineV2/Textures/T_FT2_Paint_'
SURFACES={
 'Graphite':dict(color=(.038,.047,.060),rough=(.42,.58),metal=.32,normal=PAINT+'NormalDX',rough_tex=PAINT+'Roughness',period=.6,strength=.32),
 'Pearl':dict(color=(.34,.37,.40),rough=(.46,.61),metal=.16,normal=SUB+'01_Paints/T_OrangePeel_N',rough_tex=SUB+'03_Metals/T_Metal_Painted_R',period=.7,strength=.12),
 'Frame':dict(color=(.10,.125,.15),rough=(.30,.44),metal=.78,normal=SUB+'03_Metals/T_Metal_Anodized_01_N',rough_tex=SUB+'03_Metals/T_Metal_Anodized_01_R',period=.45,strength=.32),
 'Concrete':dict(color=(.19,.21,.23),rough=(.67,.80),metal=0.,normal='/Game/HospitalCorridor/Textures/Environment/T_ConcreteRough_01_N',rough_tex=SUB+'03_Metals/T_Metal_Painted_R',period=1.4,strength=.30),
 'Steel':dict(color=(.38,.43,.48),rough=(.30,.43),metal=.94,normal=SUB+'03_Metals/T_Metal_Steel_Brushed_Horizontal_N',rough_tex=SUB+'03_Metals/T_Metal_Steel_Brushed_Horizontal_R',period=.45,strength=.28),
}
WINDOWS={'GlassDark':(.0,.0,.0),'GlassWarm':(.31,.21,.115),'GlassCool':(.085,.16,.21)}
ACCENTS={'GuideCyan':(.055,.35,.43),'GuideWarm':(.62,.40,.20)}
