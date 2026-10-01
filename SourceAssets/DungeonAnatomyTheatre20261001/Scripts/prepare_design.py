"""Author the accepted production theatre configuration; sample map is retired."""
import json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
base='/Game/Dungeons/AnatomyTheatre20261001'
outline=[[-14,-12],[14,-12],[14,-2]]+[[14*math.cos(math.pi*i/32),-2+14*math.sin(math.pi*i/32)] for i in range(1,33)]
morgue='/Game/Dungeons/IncineratorHall20260929/MorgueB1V1/Meshes/SM_Incinerator_'
c=dict(id='AbandonedAnatomyTheatre',revision='anatomy_accepted_blood_pool_20261001',phase='production_pool',
 ue_base=base,production_map='/Game/GameMaps/L_Dungeon_Randomized',sample_retired=True,
 pool_install_script='Pool20261001/Scripts/install_pool.py',
 hall=dict(outline=outline,height=8.,wall_thickness=.28),arc_center=[0,-2],
 tiers=dict(inner_radius=5.7,depth=1.2,count=4,rise=.54),gallery=dict(inner_radius=10.5,outer_radius=13.72,height=2.16),
 seating=dict(wood_material='/Game/Dungeons/AtmosphereV2/RoomInteriors/WorkbenchKit/Materials/Abandoned/MI_WBK_WSBench_BenchWood_R3',seat_bevel_m=.010,writing_ledge_bevel_m=.008,bevel_segments=5),
 side_stairs=dict(centres_x=[-11.35,11.35],width=4.,start_y=-7.4,end_y=-2.,steps=12,rise=.18,going=.45),
 radial_stairs=dict(angle_intervals_deg=[[43,77],[103,137]],width_at_inner_radius=3.33,steps=12,rise=.18,going=.4),
 clear_combat_rect_m=[-4,-6.4,4,1.6],
 ports=[dict(id=k,position=[x,-10,0],normal=[s,0,0],width=3.,height=2.8) for k,x,s in [('Entry',-16,-1),('Service',16,1)]],
 reused_parts=[dict(id='WashSink',mesh=morgue+'WashSink_MorgueB1',position=[-6,-11.35,0],yaw=180,collision=True),
 dict(id='PreparationTable',mesh=morgue+'PreparationTable_MorgueB1',position=[5.9,-11.05,0],yaw=180,collision=True),
 dict(id='MortuaryTrolley',mesh=morgue+'MortuaryTrolley_MorgueB1',position=[-7,-8.6,0],yaw=90,collision=True),
 dict(id='PowerCabinet',mesh='/Game/Dungeons/FacilityScenes20260927/Meshes/SM_Facility_PowerCabinet',position=[9,-11.25,0],yaw=180,collision=True)],
 lights=[],tests_run=False,environment_damage=False,random_pool_registered=True,
 blood=dict(material='/Game/Dungeons/IsolationWard20260929/BloodScan/M_WardBlood_Quixel',count=3,placement='tabletop only; captured runtime decals in Pool20261001/Config/module.json'),
 postprocess=dict(exposure_ev=.7,exposure_bias=-.15,indirect_intensity=.65,saturation=.85,contrast=1.05,vignette=.35,bloom=.35))
for name,p,intensity,radius,shadow,tint in [
 ('Entry',[-15,-10,3.04],240,330,False,[1,.76,.48]),('Service',[15,-10,3.04],220,330,False,[1,.76,.48]),
 ('TeachingFocus',[0,-8.8,3.02],700,550,True,[.72,.84,.88]),
 ('Centre',[-.4,-2,6.2],2400,1400,True,[.48,.61,.68]),
 ('WestStair',[-11.35,-4.6,5.15],230,480,False,[.57,.72,.77]),
 ('EastStair',[11.35,-4.6,5.15],195,480,False,[.57,.72,.77]),
 ('BackGallery',[0,10.1,6.3],270,620,False,[.54,.69,.75]),
 ('WestGallery',[-8.65,6.5,6.3],150,440,False,[.59,.72,.72]),
 ('EastGallery',[8.65,6.5,6.3],130,440,False,[.59,.72,.72])]:
 c['lights'].append(dict(id=name,position=p,lumens=intensity,radius_cm=radius,cast_shadows=shadow,tint=tint,
  role='path' if name!='TeachingFocus' and name!='Centre' else 'key',max_draw_distance_cm=3000,fade_range_cm=500,
  fixture=name!='TeachingFocus',indirect=.8 if name=='Centre' else .55))
(ROOT/'Config/room.json').write_text(json.dumps(c,ensure_ascii=False,indent=2),encoding='utf-8')
print('ANATOMY_THEATRE_DESIGN_AUTHORED')
