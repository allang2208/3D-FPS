from pathlib import Path
import runpy
R=Path(__file__).resolve().parent;PROJECT=R.parents[2]
BASE='/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV15'
MAP='/Game/GameMaps/L_CyberpunkApartment'
# Reference cross-section: apartment frontage y=0, opposite central quay y=1230.
# Translate the district rigidly; do not flatten buildings or close street gaps.
AUTHOR_SHIFT_Y=-615.0
WORLD_SHIFT_Y=AUTHOR_SHIFT_Y*1.25
SHORE=[(-3600,1850),(-2600,1430),(-1800,1160),(-900,1090),(0,1230),(650,1490),(1120,1900),(1400,2500),(1470,3400)]
OLD=runpy.run_path(str(R.parent/'RefinementV10/design.py'))
BOARDS=OLD['BOARDS'];SEARCH=OLD['SEARCH']
def world_metres(p):
    x,y,z=OLD['world_metres'](p)
    return x,y+WORLD_SHIFT_Y,z
def moved_actor(label):
    return label.startswith(('BAY_City_','BAY_Quay_','AP7_BayLandmark_','AP8_','AP9_')) or label in ('BAY_Harbor','BAY_FarCity','BAY_FarHeadland','BAY_FarTerrain')
