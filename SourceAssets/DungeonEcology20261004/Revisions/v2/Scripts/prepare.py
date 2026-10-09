"""Author ecology layouts, shared container descriptors and original signage.
No runtime, preview rendering or production-catalog mutation.
"""
from pathlib import Path
import json, copy, random, math
from PIL import Image, ImageDraw, ImageFont
ROOT=Path(__file__).resolve().parents[1]; PROJECT=ROOT.parents[1]
for d in ('Config','Authored','Receipts'): (ROOT/d).mkdir(parents=True,exist_ok=True)
BASE='/Game/Dungeons/Ecology20261004'
def write(path,data): path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
rooms=[]
for rid,title,size,offset in [('EcoNursery','育苗温室',[26,20,5.5],[0,0,0]),('EcoHydroponics','循环水培厅',[32,24,8],[37,0,0]),('EcoBiosphere','失控生态舱',[48,33,11.7],[85,0,0])]:
    a,b,h=size
    rooms.append(dict(id=rid,name=title,size=size,offset=offset,ports=[dict(id='Entry',position=[-a/2-2,0,0],normal=[-1,0,0],width=3,height=2.8),dict(id='Exit',position=[a/2+2,0,0],normal=[1,0,0],width=3,height=2.8)],
        player_start=[-a/2-1,0,1.05],map='/Game/GameMaps/Design/L_'+rid+'_Subject',parts=[],plants=[],lights=[],containers=[],container_groups=[],encounter_anchors_m=[]))
warehouse=json.loads((PROJECT/'SourceAssets/WarehouseContainers20261002/Authored/manifest.json').read_text('utf8'))
treatment=json.loads((PROJECT/'SourceAssets/IncineratorContainers20261003/Config/assemblies.json').read_text('utf8'))
protos=copy.deepcopy(treatment['prototypes'])
for key,value in warehouse['prototypes'].items():
    p=copy.deepcopy(value)
    for field in ('body','door'): p[field]='/Game/Dungeons/WarehouseContainers20261002/Meshes/'+p[field]
    if key in ('MetalCase','Tote'):
        p['body']='/Game/Dungeons/StationWorkshop20261003/RefineV2/Meshes/'+Path(p['body']).name+'_TextV2'
    if key=='ToolCabinet':
        p['door']='/Game/Dungeons/StationWorkshop20261003/RefineV2/Meshes/SM_Warehouse_ToolCabinet_Door_TextV2'
    if key=='ToolDrawer':
        p['door']='/Game/Dungeons/StationWorkshop20261003/RefineV2/Meshes/SM_Warehouse_ToolDrawer_Tray_TextV2'
    protos[key]=p

def container(room,key,p,yaw,caption,serial):
    spec=copy.deepcopy(protos[key]);spec.update(position_m=p,yaw_blender=yaw,caption=caption,container_id=room['id']+'.'+serial)
    room['containers'].append(spec);return spec
def group(room,key,p,yaw,caption,serial):
    room['container_groups'].append(dict(prototype=key,position_m=p,yaw_blender=yaw,caption=caption,id=serial))
    if key in ('SeedCabinet','RecordsCabinet'):
        room['parts'].append(dict(mesh=BASE+'/Meshes/SM_Eco_RecordsCarcass',position=p,yaw=yaw,collision=True))
        for i,z in enumerate((.11,.45,.79)):
            s=container(room,'RecordsDrawer',[p[0],p[1],p[2]+z],yaw,caption+' · '+str(i+1),serial+'.Drawer'+str(i))
            s['body']=BASE+'/Meshes/SM_Eco_RecordsFrame';s['door']=BASE+'/Meshes/SM_Eco_'+('SeedDrawer' if key=='SeedCabinet' else 'RecordsDrawer')
    elif key=='ToolCabinet':
        container(room,key,p,yaw,caption+' · 下柜',serial+'.Cabinet');container(room,'ToolDrawer',p,yaw,caption+' · 抽屉',serial+'.Drawer')
    else:container(room,key,p,yaw,caption,serial)

r=rooms[0]
for i,p in enumerate(([-12,-4,0],[-12,-5.1,0])):group(r,'PPELocker',p,-90,'温室防护用品柜','PPE'+str(i))
for i,p in enumerate(([-4,-8.3,0],[2,-8.3,0],[8,-8.3,0])):group(r,'Tote',p,0,'培育耗材周转箱','Tote'+str(i))
group(r,'MetalCase',[-9,8.5,0],0,'密封样本箱','Sample')
group(r,'SeedCabinet',[-12,7.5,0],-90,'种子样本柜','Seeds')
r=rooms[1]
for i,p in enumerate(([-14,9.6,0],[14,9.6,0])):group(r,'ToolCabinet',p,0,'水培维护工具柜','Tools'+str(i))
for i,p in enumerate(([-13,-8.5,0],[13,-8.5,0])):group(r,'ToolBox',p,0,'泵组检修工具箱','Box'+str(i))
for i,p in enumerate(([-6,10.4,2.4],[-4.6,10.4,2.4])):group(r,'FilterCase',p,0,'备用滤芯箱','Filter'+str(i))
group(r,'MetalCase',[7,10.3,2.4],0,'水质检测备件箱','Spare')
r=rooms[2]
for i,p in enumerate(([-20,13.5,0],[-18.8,13.5,0])):group(r,'RecordsCabinet',p,0,'生态实验记录柜','Records'+str(i))
for i,p in enumerate(([-13,-12.8,0],[18,12.8,0],[5,14.4,3])):group(r,'MetalCase',p,0,'封存样本运输箱','Sample'+str(i))
for i,p in enumerate(([-10,-12.8,0],[15,12.8,0],[-4,14.4,3])):group(r,'Tote',p,0,'生态耗材周转箱','Tote'+str(i))
for i,p in enumerate(([-22,10,0],[-22,11.2,0])):group(r,'PPELocker',p,-90,'应急防护用品柜','PPE'+str(i))

def light(room,p,lumens,radius,tint,shadow=False):
    room['lights'].append(dict(id='Light'+str(len(room['lights'])),position=p,lumens=lumens,radius_cm=radius*100,tint=tint,cast_shadows=shadow,max_draw_distance_cm=3200,fade_range_cm=600,role='key' if shadow else 'path'))
for r in rooms:
    a,b,h=r['size']
    for x in (-a/2-1,a/2+1):light(r,[x,0,2.95],340,4,[1,.82,.55])
if True:
    r=rooms[0]
    for x in (-9,-1,7):light(r,[x,0,4.6],2000,9,[.82,.92,1],x==-1)
    for x in (-4,2,8):
        for y in (-5.6,5.4):light(r,[x,y,2.95],650,4,[.92,1,.84])
    light(r,[-10,6,3.0],750,5,[1,.87,.68])
    r=rooms[1]
    for x in (-12,0,12):light(r,[x,0,6.5],3000,12,[.75,.89,1],x==0)
    for x in (-8,8):
        for y in (-8.5,8.5):light(r,[x,y,5.6],1300,8,[.92,1,.86],x==8 and y==8.5)
    light(r,[0,10,6],1000,8,[1,.85,.65])
    r=rooms[2]
    for x in (-18,-5,9,20):light(r,[x,-8,8.5],4000,15,[1,.84,.6],x in (-5,20))
    for x in (-16,0,17):light(r,[x,10,8.6],3000,12,[.79,.90,.81],x==0)
    light(r,[-19,10,3.4],900,6,[.9,.95,1]);light(r,[18,12,3.7],950,6,[1,.78,.5])
    light(r,[0,14,5.3],900,8,[1,.88,.63])

# Plants use original installed materials. Target heights are authored separately from source bounds.
plantbase='/Game/PN_tropicalGroundPlants/Meshes/'
rng=random.Random(10042026)
def plant(r,p,h,species=1):
    r['plants'].append(dict(mesh=plantbase+f'tropicalPlant_{species:02d}_{rng.randint(1,4):02d}',position=p,height_m=h,yaw=rng.uniform(-180,180)))
for x in (-4,2,8):
    for y in (-5.6,5.4):
        for j in range(6):plant(rooms[0],[x+rng.uniform(-1.1,1.1),y+rng.uniform(-.48,.48),.89],rng.uniform(.22,.7),1 if y<0 else 3)
for x in (-6.5,6.5):
    for y in (-4,4):
        for j in range(7):plant(rooms[1],[x+rng.uniform(-2.7,2.7),y+rng.uniform(-.55,.55),.12],rng.uniform(.6,1.5),rng.choice((2,3,4)))
for j in range(38):
    angle=rng.random()*math.tau;radius=rng.uniform(3.6,7.6)
    plant(rooms[2],[3+math.cos(angle)*radius,math.sin(angle)*radius,.2],rng.uniform(.65,2.2),rng.choice((2,3,4,5)))
for j in range(22):plant(rooms[2],[rng.uniform(-15,17),rng.choice((-1,1))*rng.uniform(13,15.3),0],rng.uniform(.65,1.6),rng.choice((2,3,5)))
rooms[0]['encounter_anchors_m']=[[-8,0,0],[0,0,0],[9,0,0],[-5,-3,0],[3,3,0]]
rooms[1]['encounter_anchors_m']=[[-14,-3,0],[0,-8,0],[0,0,0],[14,4,0],[5,10,2.4],[-5,10,2.4]]
rooms[2]['encounter_anchors_m']=[[-17,0,0],[-9,-8,0],[0,-10,0],[15,-6,0],[18,6,0],[3,11,0],[-4,14,3]]
cfg=dict(id='EcologyTheme',revision='ecology_subject_v1_20261004',layout_revision=1,geometry_revision=2,phase='subject',ue_base=BASE,rooms=rooms,
    sequence=[r['id'] for r in rooms],sample_map='/Game/GameMaps/Design/L_Ecology_Theme_Subject',return_map='/Game/GameMaps/DayNight_Lighting',
    postprocess=dict(exposure_ev=2,exposure_bias=0,bloom=.17,vignette=.18),container_outline='/Game/Dungeons/StaffLiving20261002/ScenePolishV4/Materials/M_Staff_ContainerOutline_V4',
    links=[[15,19],[55,59]],container_physical_groups=24,container_search_entries=32,random_pool_registered=False)
write(ROOT/'Config/room.json',cfg)
# Each atlas cell has an explicit physical aspect ratio; text is never stretched.
entries=[('Nursery','育苗温室','01  /  PROPAGATION'),('Hydro','循环水培厅','02  /  WATER RECLAMATION'),('Biosphere','生态实验舱','03  /  BIOSPHERE'),('Exit','出口  →','EXIT'),('Seed','种子样本','SEED BANK'),('Records','实验记录','RESEARCH RECORDS'),('PPE','防护用品','PERSONAL PROTECTION'),('Filter','循环过滤','RETURN / FILTER'),('Supply','营养液供给','NUTRIENT SUPPLY'),('Warning','注意湿滑','CAUTION / WET FLOOR'),('Specimen','样本 B-07','SPECIMEN / BIO-07'),('Control','环境监测','ENVIRONMENT CONTROL'),('Tray','培育批次 014','GERMINATION / 014'),('Shutdown','系统停机检修','SERVICE ISOLATION'),('Pump','循环泵 P-02','RECIRCULATION P-02'),('Quarantine','禁止触碰样本','DO NOT TOUCH')]
im=Image.new('RGB',(2048,2048),(22,29,26));d=ImageDraw.Draw(im);font='C:/Windows/Fonts/msyh.ttc'
rects={}
for i,(key,zh,en) in enumerate(entries):
    x=(i%2)*1024;y=(i//2)*256;rects[key]=[x,y,x+1024,y+256]
    d.rounded_rectangle((x+6,y+6,x+1017,y+249),radius=13,fill=(42,57,50),outline=(166,178,161),width=4)
    d.rectangle((x+26,y+22,x+38,y+234),fill=(199,175,94))
    d.text((x+65,y+40),zh,font=ImageFont.truetype(font,72),fill=(230,230,213))
    d.text((x+68,y+150),en,font=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',36),fill=(173,190,174))
im.save(ROOT/'Authored/T_Eco_Labels_BaseColor.png');write(ROOT/'Authored/atlas.json',dict(size=[2048,2048],rects=rects))
write(ROOT/'Config/provenance.json',dict(original=['Architecture, horticulture equipment, pipes, root paths and labels by this author','Seed and records inserts derived from project-original treatment cabinet'],reused=[dict(source='PN_tropicalGroundPlants',use='Existing installed meshes and their materials; retained locally'),dict(source='UnrealNormandy',use='Installed scanned bark textures'),dict(source='Existing FPSGAME dungeon assets',use='Concrete, industrial metal, ceramic surface authors and interactive containers')],distribution='Third-party binaries remain local; no new download or license acquisition.'))
print('ECOLOGY_DESIGN_SAVED',len(rooms),sum(len(r['containers']) for r in rooms))
