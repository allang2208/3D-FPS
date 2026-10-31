"""Apartment-side spatial inputs for the native Epic PCG pipeline, in cm."""
from pathlib import Path
import json,math,runpy
R=Path(__file__).resolve().parent
old=runpy.run_path(str(R.parent/'CyberpunkNearBank20261028/design.py'))
shore=old['shore_y'];z=(old['GROUND']+.18)*100
inputs=[]
def add(name,tag,pts,closed=False):
    inputs.append(dict(name=name,tag=tag,closed=closed,points=[[x*100,y*100,z] for x,y in pts]))
def waterfront_y(x):
    natural=shore(x)-53
    influence=math.exp(-((x-15)/145)**4)
    return min(natural, natural+(min(-80,natural)-natural)*influence)
top=[(x,shore(x)-28) for x in range(-520,521,20)]
add('DistrictBoundary','NBPCG_Boundary',top+[(520,-550),(-520,-550)],True)
add('ApartmentReserve','NBPCG_Exclusion',[(-32,-57),(62,-57),(62,32),(-32,32)],True)
# A connected perimeter collector and a central avenue. Local streets terminate
# on the collector, not in green space or water. Junctions are solved by PCG.
front=[(x,waterfront_y(x)) for x in range(-480,481,20)]
add('PerimeterCollector','NBPCG_Collector',front+[(480,-505),(-480,-505)],True)
add('CentralAvenue','NBPCG_Artery',[(-480,-265),(480,-265)])
for i,x in enumerate((-300,-140,140,300)):
    add('NorthSouth_'+str(i),'NBPCG_Local',[(x,waterfront_y(x)),(x,-505)])
for i,y in enumerate((-145,-385)):
    add('EastWest_'+str(i),'NBPCG_Local',[(-480,y),(480,y)])
d=dict(seed=281028,map='/Game/GameMaps/L_CyberpunkApartment',scope='near bank only',inputs=inputs,road_width_cm=dict(local=1400,collector=2200,artery=2600),sidewalk_target_cm=400,building_setback_cm=300,park_ratio=.22,building_styles=['NYAB','NYAC','CHF','CHH','CHI','QBA','SFC','SFD','SFE'],protected=['apartment','shoreline','promenade','opposite bank'],retire_legacy_labels=['NB28_Neighborhood_Streets']+['NB28_N1_'+str(i).zfill(2) for i in range(1,7)],generation_backend='native UE 5.8 PCG and Epic CitySamplePCG primitives',source_city_generated=False)
(R/'native_inputs.json').write_text(json.dumps(d,indent=2),encoding='utf8')
print('NATIVE_CITY_INPUTS_AUTHORED',len(inputs))
if __name__=='__main__':pass
