"""Fixed final-world dimensions; replay never compounds earlier apartment scaling."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parents[2]
BASE='/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV12'
MAP='/Game/GameMaps/L_CyberpunkApartment'
OWNER='CyberpunkApartment.RefinementV12'
SOURCE=json.loads((ROOT/'source-bindings.json').read_text())
SUB='/Game/SubstrateMaterials/Textures/'
SURFACES={
 'Graphite':dict(color=(.027,.034,.044),rough=(.36,.48),metal=.42,normal=SUB+'01_Paints/T_OrangePeel_N',rough_tex=SUB+'03_Metals/T_Metal_Painted_R',period=.45,strength=.16),
 'Steel':dict(color=(.24,.30,.35),rough=(.28,.40),metal=.86,normal=SUB+'03_Metals/T_Metal_Steel_Brushed_Horizontal_N',rough_tex=SUB+'03_Metals/T_Metal_Steel_Brushed_Horizontal_R',period=.35,strength=.22),
}
# Temperature and range follow the individual rooms, not a global exposure change.
ROOM_TUNING={
 'Landing':(3800,2025,600), 'Master':(4100,4950,830),
 'Living':(3700,10125,1040), 'Bed2':(3500,4950,880), 'Bed3':(3500,4950,880),
 'Kitchen':(4200,6300,780), 'Foyer':(3900,2350,760),
 'Corridor':(4000,2200,700), 'Bath2':(4200,2700,700),
 'Laundry':(4200,1912.5,650), 'Service':(4200,1912.5,620),
 'Balcony':(4800,1350,640),
}
LIGHTS=[]
for old in SOURCE['lights']:
 if not old['actor'].startswith('AP_Light_'):continue
 key=old['actor'].removeprefix('AP_Light_');dining=key.startswith('Dining_')
 temp,power,radius=ROOM_TUNING.get(key,(4100,old['intensity'],650))
 if dining:temp,power,radius=3500,450,300
 if key.startswith('Gym_'):temp,power,radius=4400,2475,650
 if key.startswith('BathV5_'):temp,power,radius=4200,2475,650
 loc=[v/100 for v in old['location']]
 row=dict(actor=old['actor'],key=key,old=old,center=loc,fixture='AP12_Fixture_'+key.replace('.','p').replace('-','m'),
          old_width=old['source_width']/100,old_depth=old['source_height']/100,
          temperature=temp,power=power,radius=radius,cover=not dining,new=False)
 if dining:
  # A square source inscribed in the existing 45.6 cm round pendant diffuser.
  row.update(width=.31,depth=.31,source=loc,diffuser_bottom=loc[2]+.009)
 else:
  width=row['old_width'];depth=row['old_depth']
  row.update(width=width-.04,depth=depth-.02,source=[loc[0],loc[1],loc[2]-.070],diffuser_bottom=loc[2]-.064)
 row['day']=.58 if any(k in key for k in ('Corridor','Foyer','Laundry','Service','Bath')) else .30
 row['night']=.86 if key=='Living' else .95
 if key=='Balcony':row['day']=.10
 LIGHTS.append(row)
for side,x in [('West',3.70),('East',17.68)]:
 z=5.27625
 LIGHTS.append(dict(actor='AP_Light_Corridor_'+side,key='Corridor_'+side,old=None,center=[x,-11.475,z],fixture='AP12_Fixture_Corridor_'+side,
                   old_width=3.51,old_depth=.1725,width=3.47,depth=.1525,source=[x,-11.475,z-.070],diffuser_bottom=z-.064,
                   temperature=4000,power=2200,radius=700,cover=True,new=True,day=.58,night=.95))
TV=dict(actor='AP_Living_TV',location=[2101.100000953674,-408.,88.14],scale=[1.816,.8,2.08],yaw=90.,
        outer_width_cm=617.44,outer_height_cm=397.8,body_bottom_cm=91.0,body_top_cm=488.8,
        lower_soundbar_cm=60.58,console_top_cm=58.,wall_back_cm=2113.20,
        reference='user red rectangle: width about 2.27x and height about 2.60x; retain original screen and body materials')
