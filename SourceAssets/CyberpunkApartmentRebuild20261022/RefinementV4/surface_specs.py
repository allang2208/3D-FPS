"""Shared PBR sources, linear colour, physical repeats and restrained relief."""
from pathlib import Path
ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parents[2]
BASE='/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV4'
SUB='/Game/SubstrateMaterials/Textures/'
FT='/Game/Dungeons/FacilityTransit20261007/RefineV2/Textures/T_FT2_'
MARBLE='/Game/ColdSteelUI/Warehouse20260909/ZiaratWhiteMarble/Textures/T_Ziarat_'
def sub(path):return SUB+path
def spec(color,normal,rough=None,base=None,period=.45,strength=.6,limits=(.35,.65),metal=0.,uv_m=1.2):
 return dict(color=color,normal=normal,rough=rough,base=base,period_m=period,strength=strength,
             rough_range=limits,metal=metal,uv_m=uv_m)
SPECS={
 'Teal':spec((.027,.034,.043),FT+'Paint_NormalDX',FT+'Paint_Roughness',period=.40,strength=.70,limits=(.36,.56)),
 'Dark':spec((.022,.026,.033),sub('03_Metals/T_Metal_Anodized_01_N'),sub('03_Metals/T_Metal_Anodized_01_R'),period=.45,strength=.48,limits=(.28,.47),metal=.72),
 'Wall':spec((.23,.245,.26),sub('01_Paints/T_OrangePeel_N'),sub('03_Metals/T_Metal_Painted_R'),period=.60,strength=.20,limits=(.65,.80)),
 'Ceiling':spec((.31,.325,.34),sub('01_Paints/T_Noise_N'),period=.60,strength=.12,limits=(.75,.88)),
 'Oak':spec((.15,.17,.19),sub('08_WoodVeneer/T_WoodVeneer_Oak_N'),sub('08_WoodVeneer/T_WoodVeneer_Oak_R'),sub('08_WoodVeneer/T_WoodVeneer_Oak_BC'),period=1.20,strength=.65,limits=(.40,.60)),
 'Steel':spec((.46,.50,.55),sub('03_Metals/T_Metal_Steel_Brushed_Horizontal_N'),sub('03_Metals/T_Metal_Steel_Brushed_Horizontal_R'),period=.40,strength=.42,limits=(.23,.43),metal=.97),
 'Brass':spec((.38,.42,.47),sub('03_Metals/T_Metal_Steel_SandBlasted_N'),sub('03_Metals/T_Metal_Steel_SandBlasted_R'),period=.35,strength=.42,limits=(.34,.53),metal=.94),
 'Fabric':spec((.075,.090,.105),sub('02_Upholstery/Textiles/T_TextilePlain_N'),sub('02_Upholstery/Textiles/T_TextilePlain_R'),sub('02_Upholstery/Textiles/T_TextilePlain_BC'),period=.25,strength=.75,limits=(.70,.93),uv_m=.30),
 'Linen':spec((.39,.42,.44),sub('02_Upholstery/Textiles/T_TextileStriped_N'),sub('02_Upholstery/Textiles/T_TextileStriped_R'),sub('02_Upholstery/Textiles/T_TextileStriped_BC'),period=.30,strength=.65,limits=(.68,.88),uv_m=.30),
 'Carpet':spec((.08,.09,.105),sub('02_Upholstery/Textiles/T_Carpet_01_N'),sub('02_Upholstery/Textiles/T_Carpet_01_R'),sub('02_Upholstery/Textiles/T_Carpet_01_BC'),period=.35,strength=.8,limits=(.78,.96),uv_m=.30),
 'Rubber':spec((.017,.021,.026),sub('07_Rubbers/T_Rubber_N'),sub('07_Rubbers/T_Rubber_R_02'),period=.30,strength=.6,limits=(.58,.83)),
 'CabinetInside':spec((.043,.052,.065),FT+'Paint_NormalDX',FT+'Paint_Roughness',period=.35,strength=.45,limits=(.56,.73)),
 'Stone':spec((.20,.23,.26),MARBLE+'Normal_4K',MARBLE+'Roughness_4K',MARBLE+'BaseColor_4K',period=1.4,strength=.28,limits=(.29,.48)),
 'Floor':spec((.18,.20,.22),'/Game/HospitalCorridor/Textures/Environment/T_ConcreteFloor_01_N',base='/Game/HospitalCorridor/Textures/Environment/T_ConcreteFloor_01_BC',period=1.8,strength=.35,limits=(.55,.74)),
 'Ceramic':spec((.42,.45,.48),FT+'Ceramic_NormalDX',FT+'Ceramic_Roughness',period=.50,strength=.28,limits=(.19,.33)),
 'Grout':spec((.025,.031,.039),'/Game/HospitalCorridor/Textures/Environment/T_ConcreteRough_01_N',period=.70,strength=.5,limits=(.78,.96)),
 'Paper':spec((.47,.48,.45),sub('01_Paints/T_Noise_N'),period=.50,strength=.08,limits=(.65,.80)),
 'Soil':spec((.030,.021,.015),'/Game/HospitalCorridor/Textures/Environment/T_ConcreteRough_01_N',period=.12,strength=.7,limits=(.88,.98)),
 'Armor':spec((.057,.069,.088),sub('03_Metals/T_Metal_Anodized_02_N'),sub('03_Metals/T_Metal_Anodized_02_R'),period=.48,strength=.48,limits=(.28,.46),metal=.82),
 'EdgeSteel':spec((.34,.39,.45),sub('03_Metals/T_Metal_Steel_Brushed_N'),sub('03_Metals/T_Metal_Steel_Brushed_R'),period=.34,strength=.32,limits=(.25,.42),metal=.97),
 'ReaderGlass':spec((.006,.017,.023),sub('01_Paints/T_Noise_N'),period=.50,strength=.018,limits=(.13,.17)),
 'CabinetLining':spec((.04,.05,.065),sub('07_Rubbers/T_Rubber_N'),sub('07_Rubbers/T_Rubber_R_01'),period=.30,strength=.35,limits=(.60,.79)),
 'Plastic':spec((.032,.041,.053),sub('01_Paints/T_OrangePeel_N'),sub('03_Metals/T_Metal_Painted_R'),period=.40,strength=.25,limits=(.36,.56)),
}
ALIASES={'SmokedWood':'Oak','BareSteel':'Steel','Stainless':'Steel','PaintedSteel':'Teal','OlivePaint':'Teal','Paint':'Teal','Wood':'Oak','Leather':'Fabric','Seam':'Fabric','Hem':'Linen','Terry':'Linen'}
