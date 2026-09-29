"""One authored ward layout; metre coordinates, UE = (100x, -100y, 100z)."""
import json,runpy
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
for folder in ('Config','Authored','Receipts'): (ROOT/folder).mkdir(parents=True,exist_ok=True)
def write(name,value):
    (ROOT/'Config'/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')

rooms=[
 {'id':'N01','x':[-10,-2],'y':[4.5,12.5],'door_x':-6.9,'window_x':-3.4,'rear_door_x':-6},
 {'id':'N02','x':[-2,6],'y':[4.5,12.5],'door_x':1.1,'window_x':4.6},
 {'id':'N03','x':[6,15],'y':[4.5,12.5],'door_x':9.5,'window_x':13,'rear_door_x':10.5},
 {'id':'S01','x':[-15,-5],'y':[-12.5,-4.5],'door_x':-11.7,'window_x':-7.3},
 {'id':'S02','x':[-5,5],'y':[-12.5,-4.5],'door_x':-1.7,'window_x':2.7},
]
for room in rooms:
 room['x']=[x*2 for x in room['x']]
 for key in ('door_x','window_x','rear_door_x'):
  if key in room:room[key]*=2
lights=[]
def lamp(id,p,role='fill',warm=False,shadow=False,radius=640,lumens=2300):
 lights.append(dict(id=id,position=p,role=role,warm=warm,cast_shadows=shadow,radius_cm=radius,
                    lumens=lumens,max_draw_distance_cm=3200,fade_range_cm=650))
for i,x in enumerate((-26,-19.5,-13,-6.5,0,6.5,13,19.5,26)):
 lamp('Hall'+str(i),[x,0,5.32],'main',i in (0,5),i in (0,2,4,6,8),670,1050)
for room in rooms:
 for side in (-1,1):lamp(room['id']+('A' if side<0 else 'B'),[sum(room['x'])/2+side*3.2,sum(room['y'])/2,4.16],'fill',False,False,490,480)
for i,x in enumerate((-25,-12.5,0,12.5,25)):lamp('Service'+str(i),[x,14.75,4.16],'path',True,i==3,520,620)
lamp('WestLoop',[-25,8.5,4.16],'path',False,False,600,780)
lamp('Decon',[23.5,-7.5,4.16],'path',False,True,550,700)
lamp('Entry',[23.5,-12,3.13],'path',True,False,330,450)
lamp('Exit',[31.5,1,3.13],'path',True,False,330,450)
for light in lights:
 light['fault']='flicker' if light['id'] in ('Hall2','Hall6','Service3') else 'dead' if light['id'] in ('Hall7','N02B') else 'steady'
 light['phase']={'Hall2':0.,'Hall6':4.3,'Service3':9.1}.get(light['id'],0.)
 if light['fault']=='dead':light['lumens']=0
rects=[[-30,-4.5,30,4.5],[-30,4.5,30,17],[-30,-12.5,10,-4.5],[17,-10.5,30,-4.5],
       [21.2,-13.5,25.8,-10.5],[30,-1.3,33,3.3]]
cfg=dict(id='AbandonedIsolationWard',revision='isolation_ward_window_reveals_v8_20260929',phase='standalone_architecture',
 ue_base='/Game/Dungeons/IsolationWard20260929',sample_map='/Game/GameMaps/Design/L_AbandonedIsolationWard_Subject',
 coordinate_system='Blender metres; UE centimetres (x,-y,z)',hall=dict(x=[-30,30],y=[-4.5,4.5],height=5.8),
 ward_height=4.5,rooms=rooms,floor_rectangles_m=rects,
 cells_m=[dict(min=[r[0]-.18,r[1]-.18,-.28],max=[r[2]+.18,r[3]+.18,6.1 if i==0 else 4.8]) for i,r in enumerate(rects)],
 ports=[dict(id='DecontaminationEntry',position=[23.5,-13.5,0],normal=[0,-1,0],width=3,height=2.8),
        dict(id='EastExit',position=[33,1,0],normal=[1,0,0],width=3,height=2.8)],
 sample_player_start=[23.5,-8.9,1],sample_player_yaw=-90,
 sample_return_portal=dict(position=[23.5,-12.45,0],yaw=-90,tag='ScenePortal.IsolationWardReturn'),
 lights=lights,reused_parts=[],
 clear_areas_m=[dict(name='Main nursing hall',min=[-29.7,-4.2,0],max=[29.7,4.2,5.8]),
                dict(name='Rear service gallery',min=[-29.7,12.7,0],max=[29.7,16.7,4.5]),
                dict(name='West loop',min=[-29.7,4.5,0],max=[-20.3,12.5,4.5])],
 furniture_reservations=[dict(room=r['id'],items=['hospital bed','IV stand','monitor'],
                             center=[sum(r['x'])/2,9.8 if r['id'].startswith('N') else -10,0],
                             footprint_m=[3.2,2.4]) for r in rooms],
 future_pool=dict(status='not_registered_pending_user_structure_approval',family_id='AbandonedIsolationWard',
                  remove_sample_parts=['SamplePortCaps'],remove_tags=['ScenePortal.IsolationWardReturn'],
                  main_route_width_m=8.4,rear_route_width_m=4.0,interior_door_width_m=3.2))
cfg['atmosphere']=dict(exposure_min_ev=1.,exposure_max_ev=1.,exposure_bias=-.25,
                       broken_lights=['Hall2','Hall6','Service3'],dead_lights=['Hall7','N02B'],
                       glass_material='/Game/Dungeons/IsolationWard20260929/Materials/M_WardGlassV2')
# Author receiver regions, never individual stain positions. Runtime chooses fresh
# positions and continuous silhouettes from a seed each time the room is entered.
surfaces=[]
def floor_region(x0,y0,x1,y1):
 surfaces.append(dict(center_m=[(x0+x1)/2,(y0+y1)/2,.042],normal=[0,0,1],axis_u=[1,0,0],
                      half_size_m=[(x1-x0)/2,(y1-y0)/2],wall=False))
floor_region(-29.6,-4.1,29.6,4.1)
floor_region(-29.6,12.9,29.6,16.6)
floor_region(-29.6,4.9,-20.4,12.1)
floor_region(17.4,-10.1,29.6,-4.9)
for room in rooms:
 x0,x1=room['x'];y0,y1=room['y']
 floor_region(x0+.4,y0+.4,x1-.4,y1-.4)

def wall_region(x0,x1,y,normal_y):
 if x1-x0<.65:return
 surfaces.append(dict(center_m=[(x0+x1)/2,y,1.4],normal=[0,normal_y,0],axis_u=[0,0,1],
                      half_size_m=[1.1,(x1-x0)/2],wall=True))
for room in rooms:
 x0,x1=room['x'];north=room['id'].startswith('N')
 spans=[(x0+.4,x1-.4)]
 for center,width in ((room['door_x'],3.2),(room['window_x'],3.4)):
  lo,hi=center-width/2-.3,center+width/2+.3
  spans=[p for a,b in spans for p in ((a,min(b,lo)),(max(a,hi),b)) if p[1]>p[0]]
 for a,b in spans:wall_region(a,b,4.29 if north else -4.29,-1 if north else 1)
 if not north:wall_region(x0+.4,x1-.4,-12.29,1)
wall_region(-29.5,29.5,16.79,-1)
cfg['blood_scatter']=dict(actor_class='/Script/FPSGAME.DungeonBloodScatter',
 material=cfg['ue_base']+'/BloodScan/M_WardBlood_Quixel',
 floor_count=44,wall_count=16,randomize_on_begin_play=True,seed=19429,
 receiver_tag='BloodScatter.Surface',surfaces=surfaces,
 shape_families=['quixel_blood_stain_sgfjdepc'],source_kind='quixel_scan',
 scanned_size_range_cm=[25.,60.],
 source_url='https://www.fab.com/listings/765d43e1-45ef-42f2-80a5-43d6214aa1d3',
 material_author='Scripts/author_scanned_blood.py')
runpy.run_path(str(ROOT/'Scripts/room_blood_design.py'))['apply_room_blood_design'](cfg)
cfg['glass_doors']=[dict(id=r['id'],position=[r['door_x'],4.5 if r['id'].startswith('N') else -4.5,-.038],
                        yaw=-90 if r['id'].startswith('N') else 90) for r in rooms]
cfg['glass_doors'].append(dict(id='Decon',position=[23.5,-4.5,-.038],yaw=90))
for d in cfg['glass_doors']:
 d.update(actor_class='/Script/FPSGAME.WardGlassDoor',independent_leaves=True,open_seconds=.6,auto_close_seconds=6.,
          frame=cfg['ue_base']+'/Meshes/SM_Ward_GlassDoorFrame',leaf=cfg['ue_base']+'/Meshes/SM_Ward_GlassDoorMetalV5')
cfg['glass_breakage']=dict(fracture_material=cfg['ue_base']+'/Materials/M_WardGlassFragmentsV5',
 impact_particles='/Game/NiagaraExamples/FX_Weapons/Impacts/NS_Impact_Glass',
 sound='/Game/Weapons/GunplayFX/Impacts/S_Impact_Glass_0',
 door=dict(pane=cfg['ue_base']+'/Meshes/SM_Ward_DoorPaneV5',fracture=cfg['ue_base']+'/Meshes/SM_Ward_DoorFractureV5',dimensions_cm=[142,250,1.2]),
 window=dict(pane=cfg['ue_base']+'/Meshes/SM_Ward_WindowPaneV5',fracture=cfg['ue_base']+'/Meshes/SM_Ward_WindowFractureV5',dimensions_cm=[165.5,128,1.6]),
 windows=[dict(id=r['id']+side,position=[r['window_x']+offset,4.5 if r['id'].startswith('N') else -4.5,2.215],yaw=90)
          for r in rooms for side,offset in (('L',-.8475),('R',.8475))],
 max_active_bursts=6,lifetime_seconds=4.1,fragment_query_collision=False)
cfg['bed_scatter']=dict(mesh='/Game/Dungeons/IsolationWard20260929/Props/SM_Ward_HospitalBed',
 asset_scale=1.5,min_beds_per_room=3,max_beds_per_room=5,wall_clearance=65.,bed_clearance=110.,
 randomize_on_begin_play=True,seed=29481,recipe='BedScatter/bed-manifest.json')
cfg['room_props']=runpy.run_path(str(ROOT/'MedicalProps20260929/prop_design.py'))['build_props']()
cfg['bench_layout']=runpy.run_path(str(ROOT/'BenchLayout20260929/Scripts/bench_design.py'))['build_layout'](cfg)
for area in cfg['clear_areas_m']:
 if area['name']=='Main nursing hall':
  area['min'][1]=-cfg['bench_layout']['center_aisle_half_width_m']
  area['max'][1]=cfg['bench_layout']['center_aisle_half_width_m']
cfg=runpy.run_path(str(ROOT/'Scripts/pool_design.py'))['apply'](cfg)
write('room.json',cfg)
write('asset-schedule.json',dict(
 reuse=['Approved fractured ceramic walls and UVs','Existing concrete, exposed mortar, steel and paint PBR materials',
        'IndustrialV1 warm/cool ceiling fixtures','ColdSteelDoor independent leaf interaction and collision',
        'Authored pipe/flange/hanger geometry','Hospital Bed by loxfear (CC-BY-4.0); fitted collision derivative for runtime scatter',
        'Hospital Waiting Bench - AshenCut (CC-BY-4.0); 13 fixed waiting benches beside ward doors and hall walls'],
 authored_now=['Stepped asymmetric shell','Five isolation suites','Observation windows and recessed frames',
               'Decontamination vestibule','Rear service loop','Ceiling beams and vent grilles',
               'Wall protection rails and fixed medical service trunks','Embossed room identifiers',
               'Six glazed double doors, fitted frames and convex collision','Ward-local aged clear glass',
               'Bounded scan blood placement and independent per-floor/wall scale',
               'Bounded per-room hospital bed scatter with four resting poses and traversal collision',
               'Waiting bench layout with doorway, window and central-aisle clearance',
               'Medical cart and IV drip derivatives with shared occupied-space placement',
               'Soviet Hospital poster pools and unique room-number placement'],
 missing=[dict(asset='Bedside monitor / medical wall terminal',count=5,priority='next furnishing phase'),
          dict(asset='Nurse station furniture',count=1,priority='after structure approval')],
 excluded=['Random low-detail repair tables','New monsters','New damage systems'],
 provenance='Original precision Blender architecture; existing local project materials/fixtures reused. No new external downloads.',
 tests_run=False))
print('WARD_DESIGN_SAVED',cfg['id'],len(rooms),len(lights))
