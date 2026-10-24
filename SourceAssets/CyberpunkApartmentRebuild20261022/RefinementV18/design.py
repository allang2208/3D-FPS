from pathlib import Path
import runpy
R=Path(__file__).resolve().parent
PROJECT=R.parents[2]
BASE='/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV18'
MAP='/Game/GameMaps/L_CyberpunkApartment'
SHIFT=-615.
SHORE=runpy.run_path(str(R.parent/'RefinementV15/design.py'))['SHORE']
LOBBY_ROWS=[29,33,36,39,44,47,50,53,57,61,64]
PIERS=[(-760,1080),(-270,1160),(200,1280)]
# Linear RGB, roughness, metallic, night emission. Shared deterministic palette.
SURFACES={
 'Paving':((.23,.27,.28),.8,0,0),
 'Metal':((.065,.085,.105),.43,.65,0),
 'Glass':((.018,.065,.08),.24,.35,0),
 'Ivory':((.55,.61,.60),.38,.35,0),
 'Copper':((.28,.15,.075),.45,.65,0),
 'Rubber':((.018,.023,.027),.94,0,0),
 'Leaves':((.07,.15,.095),.9,0,0),
 'Warm':((1.,.63,.28),.48,.1,.8),
 'Teal':((.06,.48,.57),.45,.2,.65),
 'Red':((.8,.025,.015),.5,.1,.5),
}
