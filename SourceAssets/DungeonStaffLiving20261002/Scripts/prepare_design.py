"""Author the three staff-living rooms and their connected preview, in metres.

This produces authoring inputs only; import_assets.py performs actual UE saving.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = '/Game/Dungeons/StaffLiving20261002'
if (ROOT/'Config/room.json').exists() and json.loads((ROOT/'Config/room.json').read_text('utf8')).get('production_revision',0)>=1:
    raise SystemExit('Staff samples retired: preserve current production author config')
for folder in ('Config', 'Authored', 'Receipts'):
    (ROOT / folder).mkdir(parents=True, exist_ok=True)

def port(key, x, y, direction):
    return dict(id=key, position=[x, y, 0], normal=[direction, 0, 0], width=3, height=2.8)

def light(key, p, lumens=450, radius=550, tint=(.91, .79, .62), shadow=False, role='path'):
    return dict(id=key, position=p, lumens=lumens, radius_cm=radius,
                tint=list(tint), cast_shadows=shadow, role=role,
                max_draw_distance_cm=2600, fade_range_cm=550, indirect=.65,
                fixture=True)

def prop(key, kind, x, y, z=0, yaw=0):
    return dict(id=key, prototype=kind, position=[x, y, z], yaw_blender_deg=yaw)

rooms = []
dorm = dict(id='StaffDormitory', name='生活宿舍区', prefix='Dormitory',
    outline=[[-14,-10],[14,-10],[14,10],[-14,10]], height=4.5,
    ports=[port('Entry',-16,0,-1),port('Changing',16,0,1)],
    player_start_m=[-15,0,1.0], clear_route_rects=[[-16,-1.55,16,1.55]],
    room_cells=[dict(min=[-14,-10,-.35],max=[14,10,4.8]),
                dict(min=[-16,-2,-.35],max=[-14,2,3.7]),
                dict(min=[14,-2,-.35],max=[16,2,3.7])],
    furniture=[],lights=[],encounter_anchors_m=[],walk_rects_m=[[-15.8,-1.6,15.8,1.6,0]])
for row, side in enumerate((-1,1)):
    for col, (x0,x1) in enumerate(((-14,-5),(-5,4),(4,14))):
        cx=(x0+x1)/2
        label=f'{101+row*3+col}'
        for bi, bx in enumerate((cx-2.45,cx+2.45)):
            dorm['furniture'].append(prop('Bed_'+label+'_'+str(bi),'BunkBed',bx,side*7.15))
        dorm['furniture'].append(prop('Desk_'+label,'Desk',cx,side*9.30,yaw=180 if side<0 else 0))
        dorm['furniture'].append(prop('Chair_'+label,'Chair',cx,side*8.45,yaw=0 if side<0 else 180))
        for li in range(2):
            dorm['furniture'].append(prop('Locker_'+label+'_'+str(li),'LockerOpen' if (col+row+li)%4==1 else 'Locker',
                                         x0+.47,side*(3.1+li*.75),yaw=90))
        dorm['furniture'].append(prop('PersonalBox_'+label,'PersonalBox',cx+2.45,side*7.15,z=.08))
        dorm['lights'].append(light('Room_'+label,[cx,side*5.5,3.17],650,650,
                                    (.93,.80,.61),shadow=col==1,role='key' if col==1 else 'path'))
        dorm['encounter_anchors_m'].append([cx,side*4.9,0])
        dorm['walk_rects_m'].append([x0+.3,min(side*2.3,side*9.5),x1-.3,max(side*2.3,side*9.5),0])
for x in (-10,0,10):
    dorm['lights'].append(light('Corridor_'+str(x),[x,0,4.10],850,620,tint=(.79,.85,.85)))
dorm['lights'] += [light('Entry',[-15,0,3.06],210,300), light('Exit',[15,0,3.06],210,300)]
dorm['furniture'] += [prop('Noticeboard','Noticeboard',-2.5,1.81,z=1.20),
                       prop('WaterDispenser','WaterDispenser',11.8,-1.65,yaw=180)]
rooms.append(dorm)

wash = dict(id='StaffChangingShowers', name='员工更衣淋浴区', prefix='ChangingShowers',
    outline=[[-12,-11],[12,-11],[12,11],[-12,11]],height=4.6,
    ports=[port('Dormitory',-14,0,-1),port('Recreation',14,0,1)],
    player_start_m=[-13,0,1.0],clear_route_rects=[[-14,-1.5,14,1.5]],
    room_cells=[dict(min=[-12,-11,-.35],max=[12,11,4.9]),
                dict(min=[-14,-2,-.35],max=[-12,2,3.7]),
                dict(min=[12,-2,-.35],max=[14,2,3.7])],
    furniture=[],lights=[],encounter_anchors_m=[],walk_rects_m=[[-13.8,-1.6,13.8,1.6,0],[-11.6,2.2,11.6,10.5,0],[-11.6,-10.5,11.6,-2.2,0]])
for i in range(24):
    x=-10.6+i*.88
    wash['furniture'].append(prop('ChangingLocker_'+str(i),'LockerOpen' if i in (3,10,17,21) else 'Locker',x,10.57))
for x in (-7.5,0,7.5):
    wash['furniture'].append(prop('Bench_'+str(x),'ChangingBench',x,5.8))
    wash['furniture'].append(prop('BenchBack_'+str(x),'ChangingBench',x,8.15))
    wash['encounter_anchors_m'].append([x,3.9,0])
for i,x in enumerate((-9.8,-5.9,-2.0,1.9,5.8,9.7)):
    wash['furniture'].append(prop('Shower_'+str(i),'ShowerFittings',x,-10.81,yaw=180))
    wash['furniture'].append(prop('Drain_'+str(i),'FloorDrain',x,-8.0))
    wash['encounter_anchors_m'].append([x,-5,0])
for i,x in enumerate((-8.5,-5.5,5.5,8.5)):
    wash['furniture'].append(prop('Sink_'+str(i),'WashBasin',x,-2.19))
    wash['furniture'].append(prop('Mirror_'+str(i),'Mirror',x,-1.97,z=1.42))
wash['furniture'] += [prop('LaundryBin','LaundryBasket',11,3.2),
                       prop('TowelRack','TowelRack',-11.68,6.5,z=.75,yaw=90),
                       prop('Noticeboard','Noticeboard',-2,1.63,z=1.15)]
for i,p in enumerate(([-8,0,4.20],[0,0,4.20],[8,0,4.20],[-7,6,4.20],[5,6,4.20],[-7,-5,4.20],[5,-5,4.20])):
    wash['lights'].append(light('WetLight_'+str(i),p,1050 if abs(p[1])>1 else 600,720,
                                (.65,.80,.83),shadow=i in (3,5),role='key' if i in (3,5) else 'path'))
wash['lights'] += [light('Entry',[-13,0,3.06],200,300),light('Exit',[13,0,3.06],200,300)]
rooms.append(wash)

rec = dict(id='StaffRecreation',name='员工活动区',prefix='Recreation',
    outline=[[-15,-12],[15,-12],[15,8],[9,8],[9,12],[-15,12]],height=5.5,
    ports=[port('Changing',-17,-6,-1),port('Onward',17,-6,1)],
    player_start_m=[-16,-6,1.0],clear_route_rects=[[-17,-7.5,17,-4.5]],
    room_cells=[dict(min=[-15,-12,-.35],max=[15,8,5.8]),
                dict(min=[-15,8,-.35],max=[9,12,5.8]),
                dict(min=[-17,-8,-.35],max=[-15,-4,3.7]),
                dict(min=[15,-8,-.35],max=[17,-4,3.7])],
    furniture=[],lights=[],encounter_anchors_m=[[0,-6,0],[-10,-2,0],[9,-1,0],[-1,6,0]],
    walk_rects_m=[[-16.8,-7.7,16.8,-4.3,0],[-14.4,-3.8,14.4,7.5,0],[-3,8,8.5,11.5,0],[-14,6,-4,11.5,.45]])
rec['furniture'] += [prop('TableTennis','TableTennis',2.7,0),prop('Billiard','BilliardTable',-6.6,0),
    prop('SofaA','Sofa',-10.7,8.9,z=.45,yaw=0),prop('SofaB','Sofa',-6.8,8.9,z=.45,yaw=0),
    prop('CoffeeTable','CoffeeTable',-8.7,7.45,z=.45),
    prop('Television','Television',-8.7,11.74,z=1.05),
    prop('BulletinBoard','Noticeboard',4.1,11.81,z=1.25),
    prop('KitchenCounter','KitchenCounter',10.6,-11.47,yaw=180),
    prop('Refrigerator','Refrigerator',13.85,-11.49,yaw=180),
    prop('WaterDispenser','WaterDispenser',14.64,5.3,yaw=-90),
    prop('CueRack','CueRack',-14.69,0,z=.25,yaw=90)]
for i,(x,y) in enumerate(((8,3),(12,3),(2,8),(6,8))):
    rec['furniture'].append(prop('DiningTable_'+str(i),'DiningTable',x,y))
    for j,dx in enumerate((-.55,.55)):
        for side in (-1,1):
            rec['furniture'].append(prop('DiningChair_'+str(i)+'_'+str(j)+'_'+str(side),'Chair',x+dx,y+side*.85,yaw=0 if side>0 else 180))
for i,p in enumerate(([-8,-6,5.10],[2,-6,5.10],[11,-6,5.10],[-6,0,5.10],[3,0,5.10],[11,4,5.10],[-9,8,3.7],[3,9,3.3])):
    rec['lights'].append(light('Activity_'+str(i),p,1050 if i not in (3,4) else 1650,850,
                               (.91,.79,.61) if i in (5,6,7) else (.72,.84,.85),
                               shadow=i in (3,5),role='key' if i in (3,5) else 'path'))
rec['lights'] += [light('Entry',[-16,-6,3.06],220,300),light('Exit',[16,-6,3.06],220,300)]
rooms.append(rec)

cfg=dict(id='StaffLivingTheme',name='地下员工生活区',revision='staff_living_subject_v1_20261002',layout_revision=2,
    phase='subject',wall_finish='intact',ue_base=BASE,sample_map='/Game/GameMaps/Design/L_StaffLiving_Theme_Subject',
    rooms=rooms,sequence=[r['id'] for r in rooms],
    preview_placements_m=[[0,0,0],[34,0,0],[69,6,0]],
    maps={r['id']:'/Game/GameMaps/Design/L_'+r['id']+'_Subject' for r in rooms},
    return_map='/Game/GameMaps/DayNight_Lighting',
    postprocess=dict(exposure_ev=1.0,exposure_bias=0.,indirect_intensity=.8,saturation=.90,contrast=1.04,bloom=.18,vignette=.16),
    tests_run=False,rendered=False,random_pool_registered=False,
    gameplay_scope='Authored static living spaces; no monsters or functional mini-games; no running water simulation.')
(ROOT/'Config/room.json').write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding='utf-8')
print('STAFF_LIVING_DESIGN_WRITTEN',len(rooms))
