from pathlib import Path
import runpy,copy
R=Path(__file__).resolve().parent;PROJECT=R.parents[2]
BASE='/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV16';MAP='/Game/GameMaps/L_CyberpunkApartment'
OLD=runpy.run_path(str(R.parent/'RefinementV15/design.py'))
BOARDS=OLD['BOARDS'];world_metres=OLD['world_metres'];SHORE=OLD['SHORE'];AUTHOR_SHIFT_Y=OLD['AUTHOR_SHIFT_Y']
SEARCH=copy.deepcopy(OLD['SEARCH'])
for i,b in enumerate(SEARCH):
 b.update(tilt=32+i%3*4,tilt_sweep=17+i%2*4,yaw_sweep=118+i%3*12,period=19+i*2.7)
TRAFFIC_SPEED=16.0
