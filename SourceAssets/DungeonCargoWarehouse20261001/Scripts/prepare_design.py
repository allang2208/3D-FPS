"""Original warehouse layout, metres, deterministic dressing and open transport lanes."""
import json,random,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for folder in ('Config','Authored','Receipts'):(ROOT/folder).mkdir(exist_ok=True)
base='/Game/Dungeons/CargoWarehouse20261001'
c=dict(id='AbandonedCargoWarehouse',name='废弃货运仓库',revision='cargo_warehouse_refine_v2_20261001',phase='production',
    ue_base=base,sample_map=None,sample_retired=True,production_module='SourceAssets/DungeonThemedRoutes20261001/Config/warehouse-module.json',
    active_refinement='RefineV2',refinement_author='RefineV2/Scripts/author_revision.py',refinement_installer='RefineV2/Scripts/import_assets.py',
    hall=dict(width=30,length=28,height=8.5),platform=dict(height=1.2,rect=[-14.7,9,14.7,13.7]),
    ports=[dict(id='FreightGate',position=[-17,-9,0],normal=[-1,0,0],width=3,height=2.8),
        dict(id='Onward',position=[17,5,0],normal=[1,0,0],width=3,height=2.8)],
    player_start_m=[-15.9,-9,1.05],player_yaw=0,return_portal_m=[-16.4,-9,0],return_portal_yaw=0,
    reused_parts=[],lights=[],racks=[],
    postprocess=dict(exposure_ev=.7,exposure_bias=-.05,indirect_intensity=.75,vignette=.28,bloom=.25),
    route_intent=dict(predecessor='FreightTransfer cleared internal gate',single_entry=True,old_transfer_exit='physically_closed_in_FreightTransfer_WarehouseLink',
        successor='route onward via warehouse exit',registration='fixed_freight_sequence'),tests_run=False,rendered=False)
props='/Game/Dungeons/FacilityScenes20260927/Meshes/SM_Facility_'
def part(name,mesh,p,yaw=0):c['reused_parts'].append(dict(id=name,mesh=mesh,position=p,yaw=yaw,collision=True))
r=random.Random(100121)
for side in (-1,1):
    for index,y in enumerate((-3.3,3.1)):
        x=side*13.3;angle=0
        if side>0 and index==1:x,y,angle=6.1,-12.95,-90
        rack_id=('W' if side<0 else 'E')+str(index+1)
        c['racks'].append(dict(id=rack_id,position=[x,y,0],width=4.8,depth=1.7,height=4.7,yaw_blender=angle))
        for layer,z in enumerate((.20,1.83,3.46)):
            for slot in (-1,1):
                if r.random()<.32:continue
                t=math.radians(angle);offset=slot*1.17
                part('RackCargo_'+str(len(c['reused_parts'])),props+'CargoStack',[x-math.sin(t)*offset,y+math.cos(t)*offset,z],(-90 if side<0 else 90)-angle)
                c['reused_parts'][-1]['rack_id']=rack_id
# Large cover clusters are kept away from entry cross-lane, main spine and exit lane.
for index,(x,y,yaw) in enumerate([(-7,-2,0),(-7,0,180),(6.7,-3,0),(7.0,-1,180),(-7.5,5.2,90),(7,7.6,0),(-5,11.5,0),(4.7,11.3,180)]):
    part('FloorCargo_'+str(index),props+'CargoStack',[x,y,1.2 if y>9 else 0],yaw)
part('PowerCabinet',props+'PowerCabinet',[10.3,-13.35,0],180)
part('ServiceSpares',props+'ServiceSpares',[-9,12.9,1.2],0)
part('PalletJack',base+'/Reused/Meshes/SM_Freight_PalletJack',[-5.1,3.7,.002],180)
for name,p,lm,radius,shadow,tint in [
 ('Entry',[-16,-9,3.05],420,420,False,[1,.76,.49]),
 ('EntryLane',[-7,-9,5.6],1800,1100,True,[.72,.79,.80]),
 ('Front',[3,-8,6.0],1900,1200,False,[.73,.79,.8]),
 ('Centre',[0,0,6.1],2600,1450,True,[.68,.77,.79]),
 ('WestRack',[-11,1,5.5],900,740,False,[.64,.75,.78]),
 ('EastRack',[11,-1,5.5],1000,750,False,[.70,.78,.78]),
 ('Dock',[0,11,6.6],1800,1200,True,[.86,.76,.57]),
 ('ExitLane',[10,5,5.1],850,780,False,[.75,.78,.69]),
 ('Exit',[16,5,3.05],450,430,False,[.8,.86,.66])]:
    c['lights'].append(dict(id=name,position=p,lumens=lm,radius_cm=radius,cast_shadows=shadow,tint=tint,
        role='key' if shadow else 'path',indirect=.7,max_draw_distance_cm=3400,fade_range_cm=500))
(ROOT/'Config/room.json').write_text(json.dumps(c,ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/'Config/sources.json').write_text(json.dumps(dict(new_geometry='Original Blender warehouse shell, pallet racks, dock, stairs, safety rails, roller bed and suspended hoist',
    reused=['FacilityScenes20260927 polished cargo stack, power cabinet and service spares','WallUpgrade20260924 concrete',
        'SeamMetal20260923 steel/enamel materials','IndustrialV1 ceiling lamp meshes'],
    new_textures='Original bilingual warehouse signs drawn with Pillow',external_downloads=[],
    license_note='Shared dependencies keep existing provenance; no new third-party assets downloaded.'),ensure_ascii=False,indent=2),encoding='utf-8')
print('CARGO_WAREHOUSE_LAYOUT_WRITTEN')
