"""Maintain the approved station architecture and its reuse/missing-asset schedule."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
for name in ('Config','Authored','Receipts'):(ROOT/name).mkdir(parents=True,exist_ok=True)
cfg={
 'id':'AbandonedTransitStation','revision':'station_expansion_20260929','phase':'random_room_module',
 'ue_base':'/Game/Dungeons/TransitStation20260928',
 'production_map':'/Game/GameMaps/L_Dungeon_Randomized',
 'coordinate_system':'Blender metres, +X along tracks, +Z up; UE = (100x,-100y,100z)',
 'enlargement':{'linear_scale':1.5,'baseline_hall_m':[32,22,7.8],
                'anchor':'west entry remains fixed; architectural dimensions grow, human-scale details stay unchanged'},
 'hall':{'x':[-16,32],'y':[-16.5,16.5],'spring':7.35,'rise':4.35,'vault_rx':16.62,'wall':.28},
 'track':{'x':[-5.5,38],'y':[-5.25,5.25],'floor':-1.80,'rail_start':-.25,'centres_y':[-2.65,2.65],'gauge':1.435,
          'recovery_steps':12,'recovery_going':.30,'recovery_width':5.0,'tunnel_radius':2.42,'tunnel_rise':2.07,'tunnel_spring':2.175},
 'bridge':{'x':[22.25,27.65],'y':[-16.2,16.2],'top':4.8,'thickness':.24},
 'stairs':{'x':[13.25,22.25],'centres_y':[-13.65,13.65],'width':5.1,'steps':30,'rise':.16,'going':.30},
 'structure':{'rib_candidates_x':[-15.4,-5.5,3.5,12.5,30.2],'pier_width':.60,'pier_base_width':.90,
              'door_frame_width':.07,'door_clearance':.60},
 'pool_policy':'Config/pool.json',
 'ports':[{'id':'concourse','position':[-19,0,0],'normal':[-1,0,0],'width':3,'height':2.8},
          {'id':'side_access','position':[4.25,19.5,0],'normal':[0,1,0],'width':3,'height':2.8}],
 'cells_m':[{'min':[-16.28,-16.78,-2.08],'max':[32.28,16.78,12.08]},
            {'min':[-19.15,-2.44,-.3],'max':[-16,2.44,3.7]},
            {'min':[1.81,16.5,-.3],'max':[6.69,19.65,3.7]},
            {'min':[32,-5.33,-2.08],'max':[38.28,5.33,4.65]}],
 'clear_areas_m':[{'role':'concourse','rect':[-15.6,-12,-5.7,12]},
                  {'role':'south_platform','rect':[-5.2,-10.8,31.6,-5.6]},
                  {'role':'north_platform','rect':[-5.2,5.6,31.6,10.8]}],
 'furniture_reservations':[{'type':'seating','rect':[-3.25,13.2,1.0,15.9]},
                           {'type':'seating','rect':[-3.25,-15.9,1.0,-13.2]},
                           {'type':'ticket_machines','rect':[-15.1,-14.9,-12.3,-11.9]},
                           {'type':'station_map','at':[-7.75,16.34,2.1]}],
 'reused_parts':[{'id':'power_cabinet','mesh':'/Game/Dungeons/FacilityScenes20260927/Meshes/SM_Facility_PowerCabinet',
                  'position':[-12.7,15.75,0],'yaw':0,'collision':True}],
 'lights':[], 'tests_run':False
}
for sign in (-1,1):
 for i,x in enumerate((-10,.5,11,20,30.2)):
  cfg['lights'].append({'id':f'platform_{sign}_{i}','position':[x,sign*8.55,7.05],
      'warm':sign<0,'lumens':4050,'radius_cm':1035,'role':'key' if i in (0,2,4) else 'fill',
      'cast_shadows':i in (0,2,4),'max_draw_distance_cm':4200,'fade_range_cm':900})
cfg['lights'].append({'id':'concourse_centre','position':[-10.75,0,7.5],'warm':True,'lumens':3375,
    'radius_cm':1005,'role':'fill','cast_shadows':False,'max_draw_distance_cm':4200,'fade_range_cm':900})
# Resolve complete arch ribs (including their piers) around the north door opening.
# Clearance is from the widest pier base to the outside of the metal door frame.
st=cfg['structure'];door=cfg['ports'][1];cx=door['position'][0]
keepout=door['width']/2+st['door_frame_width']+st['pier_base_width']/2+st['door_clearance']
st['rib_positions_x']=[round(cx-keepout if x<cx else cx+keepout,3) if abs(x-cx)<keepout else x
                       for x in st['rib_candidates_x']]
(ROOT/'Config/room.json').write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding='utf-8')
inventory={
 'reuse':['Existing corridor ceramic fracture geometry and material UVs','Existing concrete / exposed mortar / steel / rail metal / paint materials',
          'Existing IndustrialV1 ceiling lamp meshes','Existing authored pipe/flange/hanger geometry functions',
          'Polished FacilityScenes power cabinet'],
 'new_architecture_this_stage':['Barrel-vault station envelope and portal collars','Platforms and coping / tactile strip',
   'Twin recessed track beds, profiled rails, sleepers and fixed buffer stops','Suspended cross-track bridge and two stair flights',
   'Blocked railway tunnel stubs and two compatible 3 x 2.8 m access portals'],
 'missing_furnishings':[{'item':'Abandoned train carriage','priority':'optional later','action':'report only; no placeholder train'},
  {'item':'Ticket gates and ticket vending machines','priority':'later furnishings','action':'reserve ticket zone'},
  {'item':'Station-specific seating','priority':'later furnishings','action':'reserve two seating bays; military benches not used'},
  {'item':'Station name signs / line map / timetable / directional graphics','priority':'next visual identity pass','action':'report only; avoid blank yellow plates'},
  {'item':'Platform PA / CCTV / emergency intercom','priority':'optional later','action':'report only'}],
 'discovery_scope':'Local Content package names and existing dungeon author sources; no external downloads or purchases',
 'stage':'architecture authored separately; missing furnishing assets have been reported to the user'
}
(ROOT/'Config/asset-schedule.json').write_text(json.dumps(inventory,ensure_ascii=False,indent=2),encoding='utf-8')
print('STATION_DESIGN_PREPARED',cfg['production_map'])
