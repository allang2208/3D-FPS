"""Author compatible bay layouts; no room shell duplication or random placement on the critical route."""
import json, math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE='/Game/Dungeons/FacilityScenes20260927/Meshes/'
SIZE={'PumpSkid':(220,95,130),'FilterRack':(180,65,180),'PowerCabinet':(160,68,192),
      'RepairBench':(180,75,150),'CargoStack':(190,112,149),'DuctCradle':(180,94,94),
      'ServiceSpares':(80,50,30),'AbandonedPanels':(90,65,22),'IsolationStand':(78,52,85)}
SMALL={'ServiceSpares','AbandonedPanels','IsolationStand'}

def part(key,at,yaw=0):
    return dict(mesh=BASE+'SM_Facility_'+key,position=list(at),yaw=yaw,scale=[1,1,1],materials=[],
                collision=key not in SMALL,fluid=False,affects_navigation=key not in SMALL,
                cast_shadow=key not in SMALL,assembly_role='FacilityScene')

def reservation(key,at,yaw):
    x,y,z=SIZE[key];a=math.radians(yaw)
    ex=(abs(math.cos(a))*x+abs(math.sin(a))*y)/2+18
    ey=(abs(math.sin(a))*x+abs(math.cos(a))*y)/2+18
    return dict(min=[at[0]-ex,at[1]-ey,at[2]-5],max=[at[0]+ex,at[1]+ey,at[2]+z+15])

# All positions use existing room-local UE centimetres. Bays avoid BOTH primary
# and optional side doors. Drainage sites fit the near, centre and far bridge shells;
# ventilation sites fit either core offset and all declared main-door combinations.
BAYS={
 'Drainage': {'A':((430,-190,0),0),'B':((-260,-1770,0),0),'C':((840,-820,0),90),'state':((-465,-1630,0),0)},
 'VentilationLoop': {'A':((180,-1370,0),90),'B':((1600,-270,0),0),'C':((1630,-750,0),90),'state':((400,-1400,0),0)},
 'FreightTransfer': {'A':((490,-360,0),90),'B':((1320,-520,0),90),'C':((400,-1630,60),0),'state':((1400,-1710,60),0)},
}
LAYOUTS={
 'Drainage':[
  ('pump_service','排水泵组检修',[('PumpSkid','A'),('RepairBench','B')]),
  ('filter_exchange','过滤回收作业',[('FilterRack','B'),('PumpSkid','C')]),
  ('emergency_power','排水应急供电',[('PowerCabinet','C'),('CargoStack','B')])],
 'VentilationLoop':[
  ('filter_service','风道滤芯更换',[('FilterRack','A'),('RepairBench','B')]),
  ('duct_overhaul','风道拆换工位',[('DuctCradle','B'),('RepairBench','C')]),
  ('fan_power','风机供电维护',[('PowerCabinet','C'),('FilterRack','A')])],
 'FreightTransfer':[
  ('cargo_staging','待运货物堆场',[('CargoStack','C'),('PowerCabinet','B')]),
  ('dock_repair','装卸维修工位',[('RepairBench','A'),('DuctCradle','C')]),
  ('spare_dispatch','设备备件周转',[('PumpSkid','C'),('FilterRack','B')])],
}
STATES=[('maintenance','中断的检修','ServiceSpares',1.0),
        ('abandoned','撤离后的废弃','AbandonedPanels',.90),
        ('isolated','应急封存','IsolationStand',.85)]
library={}
for family,layouts in LAYOUTS.items():
    recipes=[]
    for rid,label,placements in layouts:
        parts=[];clear=[]
        for key,site in placements:
            at,yaw=BAYS[family][site];parts.append(part(key,at,yaw));clear.append(reservation(key,at,yaw))
        states=[]
        at,yaw=BAYS[family]['state']
        for sid,slabel,key,intensity in STATES:
            states.append(dict(id=sid,label=slabel,parts=[part(key,at,yaw)],
                               scene_keep_clear=[reservation(key,at,yaw)],light_intensity_scale=intensity))
        recipes.append(dict(id=rid,label=label,parts=parts,scene_keep_clear=clear,states=states))
    library[family]=recipes
config=dict(version=1,families=library,bays=BAYS,policy=dict(selection='after_route_plan_independent_seed_streams',
    large_equipment='authored_UCX_boxes',small_clutter='no_collision_no_tick',maximum_added_mesh_parts_per_room=3,
    added_lights_per_room=0,loose_floor_prop_limit=8,loose_cluster_limit=2))
(ROOT/'Config').mkdir(exist_ok=True)
(ROOT/'Config/scene-recipes.json').write_text(json.dumps(config,ensure_ascii=False,indent=2),encoding='utf-8')
print('FACILITY_RECIPES_AUTHORED',len(library),sum(len(v) for v in library.values()))
