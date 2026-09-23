"""Author the terminal pump-hall recipe and its three-to-one approach contract."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for folder in ('Config','Authored','Receipts','Sources'):(ROOT/folder).mkdir(exist_ok=True)
base=json.loads((ROOT.parent/'DungeonRoomShells20260922/Config/rooms.json').read_text(encoding='utf-8'))
def lamp(x,y,z,warm,power,radius,role):
    return dict(at=[x,y,z],warm=warm,lumens=power,radius_cm=radius,role=role)
room=dict(id='BossPumpHall',name='终末主泵房',origin_m=[0,0,0],height_m=8.4,
    footprint=[[-15,0],[15,0],[15,26],[-15,26]],
    floors=[[-15,0,15,26,0]],ceilings=[[-15,0,15,26,8.4]],
    openings=[dict(id='entry',edge=0,center=15,width=3,height=2.8)],
    columns=[[x,y] for x in (-11.32,11.32) for y in (5.6,14.6,23)],
    beams=[],pipes=[],
    platform_height_m=3.6,
    platforms=[dict(id='WestGallery',rect=[-14.65,5.6,-11.15,25.5]),dict(id='EastGallery',rect=[11.15,5.6,14.65,25.5]),dict(id='RearGallery',rect=[-11.15,22,11.15,25.5]),dict(id='WestLanding',rect=[-11.15,11,-7.6,12.8]),dict(id='EastLanding',rect=[7.6,12.8,11.15,14.6])],
    stairs=[dict(id='West',x0=-10.6,x1=-7.6,y0=2,steps_per_flight=12,rise=.15,run=.30,landing=1.8),dict(id='East',x0=7.6,x1=10.6,y0=3.8,steps_per_flight=12,rise=.15,run=.30,landing=1.8)],
    machines=[dict(id='PumpWest',at=[-4.8,10.7,0],base=[4.6,5.0,.42],pipe_side=-1),dict(id='PumpEast',at=[4.8,14.3,0],base=[4.6,5.0,.42],pipe_side=1)],
    lights=[lamp(-4,5,7.55,False,4200,1050,'key'),lamp(4,14,7.55,False,4400,1050,'key'),lamp(-9,19.5,6.6,True,1800,720,'fill'),lamp(9.2,21,6.6,True,1800,720,'fill'),lamp(-13,9,6.4,True,1500,650,'fill'),lamp(13,16.5,6.4,False,1700,680,'fill'),lamp(-6,23.6,6.7,True,1700,650,'fill'),lamp(6,23.6,6.7,False,1800,680,'fill'),lamp(0,1,3.02,True,950,460,'fill'),lamp(-13,18,2.7,True,1000,470,'fill'),lamp(13,9,2.7,False,1100,480,'fill')],
    anchors=[dict(role='boss_spawn',at=[0,19,0]),dict(role='boss_arena_center',at=[0,13,0]),dict(role='boss_entry_trigger',at=[0,3,0]),dict(role='boss_reward',at=[0,24,0]),dict(role='upper_west',at=[-12.9,16,3.6]),dict(role='upper_east',at=[12.9,18,3.6]),dict(role='upper_rear',at=[0,23.8,3.6]),dict(role='cover_west',at=[-4.8,7.3,0]),dict(role='cover_east',at=[4.8,10.9,0])])
(ROOT/'Config/rooms.json').write_text(json.dumps(dict(version=1,seed=92291,style=base['style'],rooms=[room],links=[]),ensure_ascii=False,indent=2),encoding='utf-8')
contract=dict(version=1,phase='room_authoring',boss_count=1,room_pool_eligible=False,
    reference='DungeonConcept20260920/V1/02_pump-hall.png',
    reused_catalog='DungeonRoutes20260922/Config/catalog.json',
    assembly=[dict(module='BossConfluence',source='Junction',origin_m=[0,-16,0],yaw=0),dict(module='BossApproach',source='Transit',origin_m=[0,-4,0],yaw=0),dict(module='BossPumpHall',origin_m=[0,0,0],yaw=0)],
    connections=[dict(a=['BossConfluence','boss_out'],b=['BossApproach','entry']),dict(a=['BossApproach','exit'],b=['BossPumpHall','entry'])],
    branch_inputs=[dict(id='route_left',module='BossConfluence',source_port='left'),dict(id='route_middle',module='BossConfluence',source_port='entry'),dict(id='route_right',module='BossConfluence',source_port='right')],
    boss_output_port='forward',
    routing_requirement='Every upstream branch must reach one confluence input through existing authored connectors; place exactly one boss hall after confluence.',
    routing_status='contract_only_not_connected_to_runtime',
    connector_policy='Reuse existing Transit/Threshold pieces at their authored scale; door transitions belong to the current connector catalogue.',
    reserve_assembly_before_branch_routing=True)
(ROOT/'Config/terminal-assembly.json').write_text(json.dumps(contract,ensure_ascii=False,indent=2),encoding='utf-8')
print('BOSS_HALL_RECIPE_WRITTEN')
