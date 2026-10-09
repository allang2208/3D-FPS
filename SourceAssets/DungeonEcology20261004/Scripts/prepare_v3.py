"""User-directed ecology room revision; deterministic author placements in metres."""
from pathlib import Path
import json,random,math
ROOT=Path(__file__).resolve().parents[1]
cfg=json.loads((ROOT/'Revisions/v2/Config/room.json').read_text('utf8'))
n,h,b=cfg['rooms'];base=cfg['ue_base']
cfg.update(revision='ecology_subject_v3_20261004',layout_revision=3,geometry_revision=4,mesh_base=base+'/RefineV3',links=[[15,19],[63,67]])
h.update(size=[40,30,8],offset=[41,0,0],player_start=[-21,0,1.05]);b['offset']=[93,0,0]
for r in (h,b):
    half=r['size'][0]/2
    r['ports'][0]['position']=[-half-2,0,0];r['ports'][1]['position']=[half+2,0,0]

def move(r,key,p,yaw,wall=None):
    g=next(g for g in r['container_groups'] if g['id']==key);old=g['position_m'];delta=[p[i]-old[i] for i in range(3)]
    g.update(position_m=p,yaw_blender=yaw)
    for c in r['containers']:
        if c['container_id']==r['id']+'.'+key or c['container_id'].startswith(r['id']+'.'+key+'.'):
            c['position_m']=[c['position_m'][i]+delta[i] for i in range(3)];c['yaw_blender']=yaw
            if wall:c['wall_mount']=wall
    if g['prototype'] in ('SeedCabinet','RecordsCabinet'):
        for part in r['parts']:
            if part['mesh'].endswith('RecordsCarcass') and all(abs(part['position'][i]-old[i])<.002 for i in range(3)):
                part.update(position=p[:],yaw=yaw)
                if wall:part['wall_mount']=wall
                break

west=lambda v:dict(axis=0,plane=v,side=-1,gap_m=.055)
north=lambda v:dict(axis=1,plane=v,side=1,gap_m=.055)
south=lambda v:dict(axis=1,plane=v,side=-1,gap_m=.055)
for i in range(2):move(n,'PPE'+str(i),[-12.5,-4-i*1.15,0],-90,west(-12.78))
for i in range(3):move(n,'Tote'+str(i),[-12.4,-6.5-i*1.2,0],-90,west(-12.78))
move(n,'Sample',[-7.6,7.35,0],90,dict(axis=0,plane=-7.14,side=1,gap_m=.055));move(n,'Seeds',[-12.5,7.25,0],-90,west(-12.78))
for i,x in enumerate((-16,16)):move(h,'Tools'+str(i),[x,-14.5,0],0,south(-14.80))
for i,x in enumerate((-18,18)):move(h,'Box'+str(i),[x,-14.5,0],0,south(-14.80))
for i,x in enumerate((-6,-4.6)):move(h,'Filter'+str(i),[x,14.3,2.4],180,north(14.64))
move(h,'Spare',[7,14.3,2.4],180,north(14.64))
for i,x in enumerate((-20,-18.8)):move(b,'Records'+str(i),[x,16.0,0],180,north(16.30))
for i,y in enumerate((10,11.2)):move(b,'PPE'+str(i),[-23.4,y,0],-90,west(-23.78))
for key,p,wall in [('Sample0',[-13,-15.9,.07],south(-16.28)),('Tote0',[-10,-15.9,.07],south(-16.28)),('Sample1',[18,15.9,0],north(16.28)),('Tote1',[15,15.9,0],north(16.28)),('Sample2',[5,15.65,3],north(15.90)),('Tote2',[-4,15.65,3],north(15.90))]:
    move(b,key,p,0 if p[1]<0 else 180,wall)

def part(r,key,p,yaw=0,collision=True):r['parts'].append(dict(mesh=key,position=p,yaw=yaw,collision=collision))
staff='/Game/Dungeons/StaffLiving20261002/Meshes/SM_Staff_'
part(n,staff+'Desk',[-11.5,4.75,0],180)
part(n,staff+'Chair',[-11.5,5.60,0],0)
part(n,staff+'Chair',[-9.95,5.25,0],-75)
part(n,'/Game/Dungeons/HospitalDoctorOffice20261003/Meshes/SM_Office_RecordsDesktop',[-11.5,4.75,.785],180,False)
n['bench_positions']=[[x,y,0 if y>0 else 180] for y in (-8.60,8.60) for x in (-4,1,6)]
rng=random.Random(1042603)
n['plants']=[];h['plants']=[]
plantbase='/Game/PN_tropicalGroundPlants/Meshes/'
for x,y,angle in n['bench_positions']:
    for j in range(10):
        px=x+(-1.21+(j%5)*.535);py=y+(-.43 if j<5 else .13)
        n['plants'].append(dict(mesh=plantbase+f'tropicalPlant_{1 if y<0 else 3:02d}_{rng.randint(1,4):02d}',position=[px,py,1.025],height_m=rng.uniform(.22,.54),yaw=rng.uniform(-180,180)))
for cx in (-7,7):
    for cy in (-3.8,3.8):
        for ix in range(8):
            for iy in range(3):
                h['plants'].append(dict(mesh=plantbase+f'tropicalPlant_{rng.choice((2,3,4)):02d}_{rng.randint(1,4):02d}',position=[cx+(ix-3.5)*.70,cy+(iy-1)*.42,.075],height_m=rng.uniform(.34,.85),yaw=rng.uniform(-180,180)))

def light(r,p,lm,radius,tint,shadow=True,**extra):
    r['lights'].append(dict(id='Light'+str(len(r['lights'])),position=p,lumens=lm,radius_cm=radius*100,tint=tint,cast_shadows=shadow,max_draw_distance_cm=3600,fade_range_cm=700,role='key' if shadow else 'fill',type='rect',source_width_cm=100,source_height_cm=28,**extra))
for r in (n,h):
    r['lights']=[];a,_,_=r['size']
    for x in (-a/2-1,a/2+1):light(r,[x,0,2.98],450,4,[1,.86,.67],True,fixture_ceiling_z=3.4)
for x in (-8,0,8):
    for y in (-3,3):light(n,[x,y,4.35],2400,10,[.87,.94,1],True)
for x,y,angle in n['bench_positions']:light(n,[x,y,3.0195],680,4,[.96,1,.87],False,grow_fixture=True)
light(n,[-10,6.7,3.08],1250,5,[1,.92,.79],True,fixture_ceiling_z=3.4)
for x in (-5,6):light(n,[x,0,3.65],440,8,[.82,.89,1],False,fill_only=True)
for x in (-15,-5,5,15):
    for y in (-7,7):light(h,[x,y,6.15],3100,12,[.86,.94,1],True)
for x in (-12,0,12):light(h,[x,12.5,5.8],1350,7,[1,.90,.73],False)
for x in (-14,0,14):light(h,[x,-11.5,4.8],1200,6,[.9,1,.90],False)
for x in (-9,9):light(h,[x,0,4.5],500,10,[.86,.93,1],False,fill_only=True)
# Existing biosphere fixture coordinates retained; move the emitter just under the actual diffuser.
for l in b['lights']:
    l.update(type='rect',source_width_cm=100,source_height_cm=28)
    if abs(l['position'][0])<24:l['position'][2]+=.043
    else:l['position'][2]+=.043
h['encounter_anchors_m']=[[-18,0,0],[0,-9,0],[0,0,0],[18,1,0],[-16,2,0],[16,2,0],[-6,12,2.4],[6,12,2.4]]
cfg['revision_notes']=['office sealed canopy and one unbroken front pane; side access','six wall benches and pipe overpass at doorway','hydroponics 40x30m; dry stair landings; two non-overlapping bridges','containers rear-face aligned to walls using source bounds','downward area emitters, shadow-free luminaire housings and bounded fills']
(ROOT/'Config/room.json').write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding='utf8')
print('ECOLOGY_V3_LAYOUT_AUTHORED')
