"""Author deterministic reception layout and original sign/PBR artwork. No tests/renders."""
from pathlib import Path
import json,math,shutil
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageFilter
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[1]
refinement=ROOT/'Refine20261007'
if __name__=='__main__' and (refinement/'Receipts/install.json').exists() and json.loads((refinement/'Receipts/install.json').read_text('utf8')).get('stage')=='map_saved':
    import runpy
    runpy.run_path(str(refinement/'prepare.py'),run_name='__main__')
    raise SystemExit(0)
BASE='/Game/Dungeons/ReceptionHall20261006'
for p in ('Scripts','Config','Authored','Authored/Textures','Receipts'): (ROOT/p).mkdir(exist_ok=True,parents=True)
def write(p,x): (ROOT/p).write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf8')
shutil.copy2(PROJECT/'SourceAssets/DungeonPowerTheme20261004RefineV2/Scripts/geometry.py',ROOT/'Scripts/geometry.py')
roles=json.loads((PROJECT/'SourceAssets/DungeonPowerTheme20261004RefineV2/Config/materials.json').read_text('utf8'))
roles={k:v for k,v in roles.items() if k in ('Concrete','Paint','Steel','Rubber','Yellow','Enamel')}
def material(name,col,rough,metal=0,path=None,uv=1):
    roles[name]=dict(basecolor_linear=col,roughness=rough,metallic=metal,uv_meters=uv,existing_ue_path=path or BASE+'/Materials/M_Reception_'+name,new_authored=not bool(path))
material('Floor',[.35,.36,.33],.65,uv=1.2)
material('Stone',[.54,.51,.43],.64,uv=1.2)
material('Teal',[.032,.077,.070],.51,.12)
material('Brass',[.27,.20,.10],.42,.75)
material('Dark',[.02,.027,.027],.77,.12)
material('White',[.63,.62,.55],.6)
material('Glow',[.8,.88,.76],.4)
material('Red',[.26,.045,.032],.53)
material('Wood',[.23,.16,.085],.7,path='/Game/Dungeons/AtmosphereV2/RoomInteriors/WorkbenchKit/Materials/Abandoned/MI_WBK_WSBench_BenchWood_R3',uv=1.72)
material('Soil',[.055,.033,.02],.94,path='/Game/Dungeons/Ecology20261004/RefineV5/Materials/M_Eco_SoilBed',uv=.65)
material('Labels',[.6,.65,.57],.76)
write('Config/materials.json',roles)

# Original seamless terrazzo aggregate. Matched colour, normal and roughness.
rng=np.random.default_rng(61006);N=1024
low=np.asarray(Image.fromarray(rng.integers(95,165,(32,32),dtype=np.uint8)).resize((N,N),Image.Resampling.BICUBIC),dtype=float)
noise=rng.normal(0,1.4,(N,N));base=np.clip(low*.09+151+noise,0,255)
rgb=np.stack((base,base*.995,base*.946),axis=-1).astype('uint8')
im=Image.fromarray(rgb);d=ImageDraw.Draw(im)
height=Image.new('L',(N,N),128);hd=ImageDraw.Draw(height)
for i in range(11500):
    x,y=rng.integers(0,N,2);r=int(rng.integers(1,6));tone=int(rng.choice([102,128,151,176,194,213]))
    points=[(int(x+math.cos(a)*r),int(y+math.sin(a)*r*.72)) for a in np.linspace(0,math.tau,5,endpoint=False)]
    for dx in (-N,0,N):
        for dy in (-N,0,N):
            pp=[(a+dx,b+dy) for a,b in points];d.polygon(pp,fill=(tone,min(255,tone+1),max(0,tone-7)));hd.polygon(pp,fill=int(rng.integers(123,133)))
im.save(ROOT/'Authored/Textures/T_Reception_Terrazzo_BaseColor.png')
h=np.asarray(height.filter(ImageFilter.GaussianBlur(.65)),dtype=float)/255
dx=(np.roll(h,-1,1)-np.roll(h,1,1))*1.6;dy=(np.roll(h,-1,0)-np.roll(h,1,0))*1.6
normal=np.stack((-dx,dy,np.ones_like(dx)),axis=-1);normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
Image.fromarray(((normal*.5+.5)*255).astype('uint8')).save(ROOT/'Authored/Textures/T_Reception_Terrazzo_NormalDX.png')
Image.fromarray(np.clip(169+(low-128)*.14,0,255).astype('uint8')).save(ROOT/'Authored/Textures/T_Reception_Terrazzo_Roughness.png')

cards=[('welcome','设施接待大厅','FACILITY RECEPTION  /  01'),('registration','访客登记','VISITOR REGISTRATION'),('security','安全检查','SECURITY CHECKPOINT'),
 ('waiting','访客等候区','PLEASE WAIT TO BE CALLED'),('upper','二层 · 接待办公','LEVEL 02  /  VISITOR SERVICES'),('exit','设施通道  →','AUTHORIZED ACCESS'),
 ('officeA','接待办公室','VISITOR SERVICES'),('officeB','值班协调室','DUTY COORDINATION'),('storage','访客物品寄存','PERSONAL BELONGINGS'),
 ('water','饮水 · 休息','WATER / REFRESHMENTS'),('accessible','无障碍登记位','ACCESSIBLE COUNTER'),('guide','来访流程','01 登记   02 安检   03 等候引导'),
 ('badge','请佩戴访客证','PLEASE WEAR YOUR VISITOR BADGE'),('staff','工作人员通道','STAFF ACCESS'),('notice','访客须知','请出示证件，随身物品配合检查。'),
 ('map','楼层导览','01 接待 / 安检     02 办公 / 会客'),('lane1','01  安检通道','SECURITY LANE 01'),('lane2','02  安检通道','SECURITY LANE 02'),
 ('desk1','登记 01','REGISTRATION'),('desk2','登记 02','REGISTRATION'),('files','访客记录','VISITOR RECORDS'),('meeting','会客与洽谈','MEETING LOUNGE'),
 ('restricted','仅限授权人员','AUTHORIZED PERSONNEL'),('return','入口 · 返回','ENTRANCE / RETURN')]
atlas=Image.new('RGB',(4096,4096),(27,44,40));draw=ImageDraw.Draw(atlas);rects={}
fontpath='C:/Windows/Fonts/msyh.ttc';enpath='C:/Windows/Fonts/consola.ttf'
for i,(key,cn,en) in enumerate(cards):
    x=16+(i%4)*1024;y=16+(i//4)*512;w=984;hh=304
    rects[key]=[x,y,x+w,y+hh]
    draw.rectangle((x,y,x+w-1,y+hh-1),fill=(30,48,44),outline=(161,153,122),width=3)
    draw.rectangle((x+24,y+31,x+33,y+hh-31),fill=(185,151,88))
    size=70
    while draw.textbbox((0,0),cn,font=ImageFont.truetype(fontpath,size))[2]>w-108:size-=1
    draw.text((x+60,y+43),cn,font=ImageFont.truetype(fontpath,size),fill=(222,220,199))
    sz=28
    while draw.textbbox((0,0),en,font=ImageFont.truetype(fontpath,sz))[2]>w-108:sz-=1
    draw.text((x+63,y+183),en,font=ImageFont.truetype(fontpath,sz),fill=(167,189,174))
    draw.line((x+60,y+hh-35,x+w-40,y+hh-35),fill=(74,96,84),width=2)
atlas.save(ROOT/'Authored/Textures/T_Reception_Signs.png');write('Config/atlas.json',dict(size=[4096,4096],rects=rects))

parts=[];lights=[];containers=[];glazing=[];doors=[]
def part(id,mesh,pos,yaw=0,anchor=(0,0,0),scale=1,collision=True,**kw):
    a=math.radians(yaw);ax,ay,az=anchor
    p=[pos[0]-(ax*math.cos(a)-ay*math.sin(a))*scale,pos[1]-(ax*math.sin(a)+ay*math.cos(a))*scale,pos[2]-az*scale]
    parts.append(dict(id=id,mesh=mesh,position_m=p,yaw_deg=yaw,scale=[scale]*3,collision=collision,cast_shadow=True,**kw))
staff='/Game/Dungeons/StaffLiving20261002/Meshes/SM_Staff_'
sw='/Game/Dungeons/StationWorkshop20261003';anchor=[6.1,-.72,0]
# Waiting lounges: free of stair approaches, with coffee tables and circulation.
for side in (-1,1):
    for j,x in enumerate((-20.7,-16.9)):
        y=side*15.3;yaw=0 if side==1 else 180
        part(f'Lounge_{side}_{j}',staff+'Sofa',[x,y,0],yaw)
        part(f'Table_{side}_{j}',staff+'CoffeeTable',[x,side*13.55,0],yaw)
for j,x in enumerate((-17,-11,-5,1,7)):
    for side in (-1,1):
        part(f'UpperBench_{side}_{j}',staff+'ChangingBench',[x,side*15.75,4.5])
for id,pos,yaw in [('SouthWater',[-12,-15.9,0],180),('NorthWater',[0,15.9,0],0),('UpperWater',[23.4,0,4.5],-90)]:
    part(id,'/Game/Dungeons/StaffLiving20261002/RoomDetailsV5/Meshes/SM_Staff_WaterDispenser_V5',pos,yaw)
for x in (-10.1,-6.7):
    # Existing complete workstation is at 77.5cm desk height, grounded through its real source anchor.
    part('ReceptionMonitor_'+str(x),sw+'/RefineV2/Meshes/SM_SW_DispatchElectronics',[x,12.975,0],180,anchor,collision=False)
    part('ReceptionChair_'+str(x),staff+'Chair',[x,14.25,0],0)
    part('ReceptionPaper_'+str(x),sw+'/RefineV2/Meshes/SM_SW_DispatchPaper',[x,13.0,0],180,anchor,collision=False)
for side in (-1,1):
    for j,y in enumerate((side*4.4,side*11.8)):
        # Existing 2.1x0.8m workstations against east wall, facing into office.
        part(f'OfficeDesk_{side}_{j}',sw+'/Meshes/SM_SW_DispatchDesk',[23.1,y,4.5],-90,anchor)
        part(f'OfficePC_{side}_{j}',sw+'/RefineV2/Meshes/SM_SW_DispatchElectronics',[23.17,y,4.5],-90,anchor,collision=False)
        part(f'OfficePaper_{side}_{j}',sw+'/RefineV2/Meshes/SM_SW_DispatchPaper',[23.1,y,4.5],-90,anchor,collision=False)
        part(f'OfficeChair_{side}_{j}',staff+'Chair',[21.85,y,4.5],90)
    part(f'OfficeGuestBench_{side}',staff+'ChangingBench',[20.8,side*13.8,4.5])
for side in (-1,1):
    part(f'SecurityDesk_{side}',sw+'/Meshes/SM_SW_DispatchDesk',[23.1,side*9.3,0],-90,anchor)
    part(f'SecurityPC_{side}',sw+'/RefineV2/Meshes/SM_SW_DispatchElectronics',[23.17,side*9.3,0],-90,anchor,collision=False)
    part(f'SecurityChair_{side}',staff+'Chair',[21.85,side*9.3,0],90)

proto=json.loads((PROJECT/'SourceAssets/IncineratorContainers20261003/Config/assemblies.json').read_text('utf8'))
for j in range(6):
    spec=dict(proto['prototypes']['PPELocker']);spec.update(id=f'VisitorLocker{j+1}',position_m=[23.4,-10.8-j*.82,0],yaw_deg=90,caption=f'访客寄存柜 {j+1:02d}');containers.append(spec)
for id,pos,yaw in [('ReceptionRecords',[-3.8,15.8,0],180),('UpperRecordsSouth',[23.4,-2.3,4.5],90),('UpperRecordsNorth',[23.4,2.3,4.5],90)]:
    part(id,proto['assemblies']['RecordsCabinet']['static_parts'][0]['mesh'],pos,yaw)
    for j,z in enumerate((.11,.45,.79)):
        spec=dict(proto['prototypes']['RecordsDrawer']);spec.update(id=id+str(j),position_m=[pos[0],pos[1],pos[2]+z],yaw_deg=yaw,caption='访客记录 · '+('登记资料','通行凭证','接待档案')[j]);containers.append(spec)

# Two office fronts; doors interrupt glazing at actual openings. 3m clear balcony.
for side in (-1,1):
    y0,y1=(-14.8,-1.2) if side==-1 else (1.2,14.8);door_y=side*8
    for lo,hi in [(y0,door_y-.615),(door_y+.615,y1)]:
        n=math.ceil((hi-lo)/2.8)
        for i in range(n):
            a=lo+(hi-lo)*i/n;b=lo+(hi-lo)*(i+1)/n
            glazing.append(dict(id=f'OfficeGlass_{side}_{len(glazing)}',position_m=[19,(a+b)/2,6.45],yaw_deg=0,width_m=b-a-.07,height_m=1.95))
    doors.append(dict(id=f'OfficeDoor_{side}',position_m=[19,door_y,4.5],yaw_deg=0,positive_hinge=side>0,leaf_mesh=sw+'/RefineV2/Meshes/SM_SW_PersonnelLeaf'))

# Root-anchored reused ecology plants, with pots large enough for their foliage.
eco=json.loads((PROJECT/'SourceAssets/DungeonEcology20261004/Config/room.json').read_text('utf8'));sources={}
def plant_sources(value):
    if isinstance(value,dict):
        if value.get('root_anchor_blender_m') and '/PN_tropicalGroundPlants/' in value.get('mesh',''):sources.setdefault(value['mesh'],value)
        for child in value.values():plant_sources(child)
    elif isinstance(value,list):
        for child in value:plant_sources(child)
plant_sources(eco)
plants=list(sources.values());pots=[]
for i,(x,y,z) in enumerate([(-21,-8,0),(-21,8,0),(-3,15.25,0),(2,15.25,0),(8,-14.7,0),(12,-14.7,0),(-20,-12,4.5),(-20,12,4.5),(11,-14.8,4.5),(11,14.8,4.5)]):
    pots.append([x,y,z]);p=plants[i%len(plants)];height=1.2 if z else 1.5;scale=height/p['source_height_m']
    part('PlanterPlant'+str(i),p['mesh'],[x,y,z+.575],i*71,p['root_anchor_blender_m'],scale,False)

for x in (-14,0,14):
    for y in (-6,6):
        lights.append(dict(id=f'Atrium_{x}_{y}',position_m=[x,y,8.5],radius=17,intensity=14000,cast_shadows=(x in (-14,14)),type='spot',outer_cone_degrees=74,inner_cone_degrees=52,role='main'))
for x in (-20,-8,4,20):
    for y in (-13.25,13.25):
        lights.append(dict(id=f'Ground_{x}_{y}',position_m=[x,y,3.08 if x==-8 and y>0 else 3.65],radius=8,intensity=2600,cast_shadows=False,type='point',role='local'))
for x,y in [(-21,0),(-8,-13.2),(-8,13.2),(7,-13.2),(7,13.2),(21.4,-7.6),(21.4,7.6)]:
    lights.append(dict(id=f'Upper_{x}_{y}',position_m=[x,y,8.1],radius=8,intensity=3200,cast_shadows=False,type='point',role='local'))
for x in (-25.5,25.5):lights.append(dict(id=f'Vestibule_{x}',position_m=[x,0,2.55],radius=5,intensity=1300,cast_shadows=False,type='point',role='local'))
widths=sorted(set(round(p['width_m'],5) for p in glazing))
for p in glazing:p['glass_kind']='Office'+str(widths.index(round(p['width_m'],5)))
cfg=dict(id='FacilityReceptionHall',revision='20261006-v1',phase='independent_subject',base=BASE,map='/Game/GameMaps/Design/L_ReceptionHall_Subject',dimensions_m=[48,33,10],upper_floor_m=4.5,
    station_reference_m=[48,33,11.7],player_start_m=[-25.6,0,1.05],parts=parts,lights=lights,containers=containers,glass=glazing,doors=doors,pots=pots,
    ports=[dict(id='arrival',position=[-27,0,0],normal=[-1,0,0],width=4,height=3.4),dict(id='facility',position=[27,0,0],normal=[1,0,0],width=3,height=3)],
    reception_counter=dict(x=[-12,-3],y=[12.0,13.7]),lighting_budget=dict(total=len(lights),shadowed=sum(p['cast_shadows'] for p in lights)),
    production_registered=False,tests_run=False,rendered=False,route_intent='Future dungeon first room; independent subject pending user acceptance')
import runpy
cfg=runpy.run_path(str(PROJECT/'SourceAssets/HallLighting20261007/profile.py'))['revise_layout'](cfg,'Reception')
upper_props=ROOT/'UpperProps20261007/layout.py'
if upper_props.exists():cfg=runpy.run_path(str(upper_props))['preserve_source_if_installed'](cfg)
write('Config/layout.json',cfg)
write('Config/provenance.json',dict(new_geometry='Original dimensioned reception hall architecture and furniture, produced locally',new_artwork='Original Chinese typography atlas and seeded terrazzo PBR',
    reuse='Existing approved project assets and materials remain unchanged',source_modules=['DungeonStaffLiving20261002','StationWorkshop20261003','IncineratorContainers20261003','DungeonEcology20261004'],
    imported_foliage='Existing PN_tropicalGroundPlants project assets; no new external download',geometry_library='Private snapshot of PowerTheme precision primitives',tests_run=False))
print('RECEPTION_LAYOUT_AUTHORED',len(parts),'reused placements',len(lights),'lights',len(containers),'containers')
