"""Author the two approved room recipes; no editor or tests."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for folder in ('Config', 'Authored', 'Receipts', 'Sources'):
    (ROOT / folder).mkdir(exist_ok=True)
base = json.loads((ROOT.parent / 'DungeonRoomShells20260922/Config/rooms.json').read_text(encoding='utf-8'))
def light(x,y,z,warm,lumens,radius):
    return dict(at=[x,y,z],warm=warm,lumens=lumens,radius_cm=radius)

vent = dict(id='VentilationLoop',name='环廊通风机房',origin_m=[0,0,0],height_m=4.1,
    footprint=[[1.5,0],[16.5,0],[18,1.5],[18,14.5],[16.5,16],[1.5,16],[0,14.5],[0,1.5]],
    floors=[[0,0,18,16,0]],ceilings=[[0,0,18,16,4.1],[.12,2,1.0,14,3.2]],
    openings=[dict(edge=0,center=4.5,width=3,height=2.8,id='entry'),dict(edge=2,center=10.5,width=3,height=2.8,id='exit')],
    columns=[[.24,4],[.24,12],[17.76,4],[17.76,8]],
    beams=[[[.3,y,3.91],[17.7,y,3.91]] for y in (2,14)],
    pipes=[dict(points=[[.65,.8,2.86],[.65,14.8,2.86],[5,14.8,2.86]],radius=.062)],
    lights=[light(3,3,3.62,False,2450,575),light(15,5,3.62,False,2550,585),light(3,12.5,3.63,True,1650,490),light(14.8,13.1,3.66,True,1950,510)],
    anchors=[dict(role='encounter_west',at=[3,9,0]),dict(role='encounter_east',at=[15,8,0]),dict(role='filter_maintenance',at=[4.7,10,0]),dict(role='entry',at=[6,1.8,0]),dict(role='exit',at=[16,12,0])],
    core=dict(rect=[6,4,12,12],height=4.1),target_walkable_m2=[210,220])
freight = dict(id='FreightTransfer',name='错层货运中转间',origin_m=[26,0,0],height_m=4.3,
    footprint=[[4,0],[14,0],[14,8],[18,8],[18,18],[0,18],[0,8],[4,8]],
    floors=[[4,0,14,8,0],[0,8,18,14,0],[0,14,18,18,.6]],
    ceilings=[[4,0,14,3.6,3],[4,3.6,14,8,4.3],[0,8,18,18,4.3]],
    openings=[dict(edge=0,center=5,width=3,height=2.8,id='entry'),dict(edge=3,center=3,width=3,height=2.8,id='exit')],
    columns=[[4.18,7.82],[13.82,7.82],[.24,13.8],[17.76,13.8]],
    beams=[[[.3,y,4.12],[17.7,y,4.12]] for y in (9,16.5)],
    pipes=[dict(points=[[4.5,.4,2.68],[4.5,3.2,2.68],[4.5,3.2,3.55],[4.5,8.65,3.55],[.6,8.65,3.55],[.6,17.5,3.55]],radius=.045)],
    lights=[light(9,1.7,2.84,True,1200,430),light(8.5,6,3.8,False,2400,570),light(5.4,11.5,3.79,False,2550,580),light(14.5,11.8,3.79,False,1900,530),light(9,16.4,3.89,True,1900,520)],
    anchors=[dict(role='encounter_lower',at=[8,10.2,0]),dict(role='encounter_dock',at=[5.5,16,.6]),dict(role='freight_discovery',at=[1.7,11,0]),dict(role='entry',at=[9,1.8,0]),dict(role='exit',at=[16,11,0])],
    dock=dict(rect=[0,14,18,18],height=.6,stairs=[[2,12.8,5,14],[13,12.8,16,14]]),target_walkable_m2=[225,235])
cfg=dict(version=1,seed=92262,style=base['style'],rooms=[vent,freight],links=[],target_map='/Game/GameMaps/L_Dungeon_Randomized')
(ROOT/'Config/rooms.json').write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding='utf-8')
print('TWO_ROOM_RECIPES_WRITTEN')
