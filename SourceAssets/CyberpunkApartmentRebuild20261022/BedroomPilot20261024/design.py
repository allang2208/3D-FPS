"""Bedroom production authoring: final-world metres, integrated into the existing apartment."""
from pathlib import Path
R=Path(__file__).resolve().parent
PROJECT=R.parents[2]
SOURCE_MAP='/Game/GameMaps/L_CyberpunkApartment'
MAP=SOURCE_MAP
BASE='/Game/Props/CyberpunkBedroomPilot20261024'
OWNER='Cyberpunk.BedroomPilot20261024'
SUB='/Game/SubstrateMaterials/Textures/'
SURFACES={
 'Graphite':dict(color=(.025,.032,.041),normal='01_Paints/T_OrangePeel_N',rough='03_Metals/T_Metal_Painted_R',period=.45,strength=.20,limits=(.36,.51),metal=.30),
 'EdgeSteel':dict(color=(.25,.29,.34),normal='03_Metals/T_Metal_Steel_Brushed_Horizontal_N',rough='03_Metals/T_Metal_Steel_Brushed_Horizontal_R',period=.35,strength=.25,limits=(.26,.40),metal=.96),
 'Copper':dict(color=(.31,.14,.065),normal='03_Metals/T_Metal_Steel_Brushed_Horizontal_N',rough='03_Metals/T_Metal_Steel_Brushed_Horizontal_R',period=.35,strength=.18,limits=(.31,.47),metal=.92),
 'Walnut':dict(color=(.055,.045,.035),normal='08_WoodVeneer/T_WoodVeneer_Oak_N',rough='08_WoodVeneer/T_WoodVeneer_Oak_R',base='08_WoodVeneer/T_WoodVeneer_Oak_BC',period=1.2,strength=.48,limits=(.39,.57),metal=0),
 'CharcoalWeave':dict(color=(.045,.062,.076),normal='02_Upholstery/Textiles/T_TextilePlain_N',rough='02_Upholstery/Textiles/T_TextilePlain_R',period=.24,strength=.65,limits=(.77,.93),metal=0),
 'FogLinen':dict(color=(.35,.36,.345),normal='02_Upholstery/Textiles/T_TextileStriped_N',rough='02_Upholstery/Textiles/T_TextileStriped_R',period=.28,strength=.55,limits=(.73,.91),metal=0),
 'OchreCloth':dict(color=(.22,.105,.043),normal='02_Upholstery/Textiles/T_TextilePlain_N',rough='02_Upholstery/Textiles/T_TextilePlain_R',period=.25,strength=.65,limits=(.78,.94),metal=0),
 'Rug':dict(color=(.075,.092,.099),normal='02_Upholstery/Textiles/T_Carpet_01_N',rough='02_Upholstery/Textiles/T_Carpet_01_R',period=.30,strength=.75,limits=(.80,.96),metal=0),
 'Rubber':dict(color=(.012,.016,.022),normal='07_Rubbers/T_Rubber_N',rough='07_Rubbers/T_Rubber_R_02',period=.25,strength=.25,limits=(.57,.78),metal=0),
 'Ceramic':dict(color=(.25,.285,.28),normal='01_Paints/T_Noise_N',rough=None,period=.5,strength=.025,limits=(.23,.31),metal=0),
 'Paper':dict(color=(.48,.46,.39),normal='01_Paints/T_Noise_N',rough=None,period=.5,strength=.06,limits=(.69,.82),metal=0),
 'Ink':dict(color=(.008,.014,.02),normal='01_Paints/T_Noise_N',rough=None,period=.5,strength=.025,limits=(.35,.48),metal=0),
 'WarmDiffuser':dict(color=(.62,.43,.22),normal='01_Paints/T_Noise_N',rough=None,period=.5,strength=.025,limits=(.34,.44),metal=0,emission=(2.4,1.55,.75)),
 'CoolIndicator':dict(color=(.025,.14,.18),normal='01_Paints/T_Noise_N',rough=None,period=.5,strength=.025,limits=(.30,.44),metal=0,emission=(.035,.38,.48)),
}
# Bed contact geometry/height and the existing terminal, door, cabinet identities remain.
BRIEF=dict(room='Bed2',style='graphite cyberpunk bedroom, quiet warm bedside light, sparse cyan technology',
           palette=['graphite','smoked walnut','fog linen','oxidised copper','muted petrol'],
           preserve=['room shell','bed transform and collision','rest animation contacts','door travel',
                     'storage IDs and contents','terminal power controls','other rooms','bay scenery'],
           dimensions_m=dict(minimum=[21.375,-10.125,0],maximum=[29.775,-.225,5.53125]),
           production='Blender precision geometry, existing PBR sources, scoped UE pilot map',
           renders_requested=False,tests_requested=False)
