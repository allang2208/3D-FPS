"""Place retained hospital/office art at measured pivots; preserve circulation."""
import json,copy,math,runpy
from pathlib import Path
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[1]
read=lambda p:json.loads(p.read_text('utf-8-sig'))
ART=read(ROOT/'Config/reused-art.json')
CAT=read(PROJECT/'SourceAssets/DungeonFacilityFlow20261007/Config/catalog.json')
WARD=next(m for m in CAT['modules'] if m['id']=='AbandonedIsolationWard')
GEO=read(ROOT/'Config/geometry.json')
parts=[];actors=[];lights=[];clearances=[]
STAFF='/Game/Dungeons/StaffLiving20261002/Meshes/SM_Staff_'
HOSP='/Game/HospitalCorridor/Meshes/Objects/'
def place(identity,path,x,y,z=0,yaw=0,col=True,floor=True):
 b=ART[path];c=[(b['min'][i]+b['max'][i])/2 for i in range(3)]
 a=math.radians(yaw);co,si=math.cos(a),math.sin(a)
 p=[x-co*c[0]+si*c[1],y-si*c[0]-co*c[1],z-b['min'][2] if floor else z]
 spec=dict(id='MedicalOffice.'+identity,mesh=path,position=p,yaw=yaw,scale=[1,1,1],collision=col,
   affects_navigation=col,cast_shadow=col,fluid=False,materials=[])
 parts.append(spec);return spec
for item in GEO['meshes']:
 parts.append(dict(id='MedicalOffice.Shell.'+item['kind'],mesh=item['mesh'],position=[0,0,0],yaw=0,
   scale=[1,1,1],collision=item['collision'],affects_navigation=item['collision'],cast_shadow=item['cast_shadow'],fluid=False,materials=[]))
records='/Game/Dungeons/HospitalDoctorOffice20261003/Meshes/SM_Office_RecordsDesktop'
paper='/Game/Dungeons/StationWorkshop20261003/RefineV2/Meshes/SM_SW_DispatchPaper'
def desk(identity,x,y,yaw=0,visitors=True):
 place(identity+'.Desk',STAFF+'Desk',x,y,yaw=yaw)
 a=math.radians(yaw);co,si=math.cos(a),math.sin(a)
 def at(dx,dy):return x+co*dx-si*dy,y+si*dx+co*dy
 cx,cy=at(0,100);place(identity+'.DoctorChair',STAFF+'Chair',cx,cy,yaw=yaw+180)
 for k,dx in enumerate((-59,59) if visitors else ()):
  cx,cy=at(dx,-118);place(identity+'.Visitor'+str(k),STAFF+'Chair',cx,cy,yaw=yaw)
 place(identity+'.Records',records,x,y,78.35,yaw=yaw,col=False)
 clearances.append(dict(id=identity+'.DeskAccess',min=[x-180,y-175,0],max=[x+180,y+160,210]))
for i,y in enumerate((-300,-1110)):
 desk('Consult'+str(i+1),-600,y)
 place('Consult'+str(i+1)+'.Bed','/Game/Dungeons/IsolationWard20260929/Props/SM_Ward_HospitalBed',-610,y-370)
 place('Consult'+str(i+1)+'.Sink','/Game/Dungeons/StaffLiving20261002/ScenePolishV4/Meshes/SM_Staff_WashBasin_V4',-842,y+24,yaw=-90,floor=False)
 place('Consult'+str(i+1)+'.IV','/Game/Dungeons/IsolationWard20260929/Props/SM_Ward_IVDripCrutch',-808,y-400,col=False)
for i,(x,y) in enumerate(((560,-285),(1230,-285),(560,-650),(1230,-650))):desk('TeamWorkstation'+str(i+1),x,y,visitors=False)
desk('Chief',580,-2080,180)
place('Chief.CaseConferenceTable',STAFF+'DiningTable',580,-1705)
for i,(x,y,yaw) in enumerate(((460,-1610,180),(700,-1610,180),(460,-1800,0),(700,-1800,0))):
 place('Chief.ConferenceChair'+str(i),STAFF+'Chair',x,y,yaw=yaw)
place('Chief.CaseNotes',records,580,-1705,78.5,col=False)
desk('RecordsWorkstation',-610,-1880,visitors=False)
place('ClinicalSupport.Bed','/Game/Dungeons/IsolationWard20260929/Props/SM_Ward_HospitalBed',1320,-1950,yaw=90)
place('ClinicalSupport.Sink','/Game/Dungeons/StaffLiving20261002/ScenePolishV4/Meshes/SM_Staff_WashBasin_V4',1640,-2220,yaw=90,floor=False)
place('ClinicalSupport.Desk',STAFF+'Desk',1270,-1660,yaw=180)
place('ClinicalSupport.Instructions',paper,1270,-1660,78.4,yaw=180,col=False)
# Bench backs face walls; a 2.6 m central line remains open through the waiting corridor.
for i,x in enumerate((420,680,1290,1540)):
 place('Waiting.Bench'+str(i),HOSP+'SM_HospitalBench_01',x,-940,yaw=180)
place('Waiting.Water','/Game/Dungeons/StaffLiving20261002/ScenePolishV4/Meshes/SM_Staff_WaterDispenser_V4',158,-1740,yaw=90)
place('Waiting.LeafletTable',STAFF+'CoffeeTable',164,-2090,yaw=90)
place('Waiting.Leaflets',paper,164,-2090,50.1,yaw=90,col=False)
place('Team.CoffeeTable',STAFF+'Desk',1510,-80,yaw=180)
place('Team.CoffeeMachine','/Game/Dungeons/StaffLiving20261002/RoomDetailsV5/Meshes/SM_Staff_CoffeeMachine_V5',1540,-80,78.4,yaw=180)
place('Team.Kettle','/Game/Dungeons/StaffLiving20261002/RoomDetailsV5/Meshes/SM_Staff_ElectricKettle_V5',1450,-80,78.4,yaw=180)
# Reuse the actual hospital noticeboard and poster artwork, mounted above protection rails.
for i,(x,y,yaw) in enumerate(((-197,-105,-90),(-197,-800,-90),(-197,-1660,-90),(223,-1970,-90),(1687,-1810,90))):
 path=HOSP+'SM_HospitalPosters_01_'+('A','C','D','F','G')[i]
 place('Wall.Poster'+str(i),path,x,y,214,yaw=yaw,col=False,floor=False)
place('Wall.Information',HOSP+'SM_InformationStand_01',1070,-1307,214,col=False,floor=False)

# Reuse existing working container mechanics and meshes; IDs are unique to this new module.
OFFICE=read(PROJECT/'SourceAssets/HospitalDoctorOffice20261003/Config/office.json')
book=OFFICE['group']['slots'][0]['variants'][0]['containers'][0]
shelf=OFFICE['group']['slots'][2]['variants'][0]['containers'][0]
def container(source,identity,caption,x,y,yaw=0,z=.1):
 s=copy.deepcopy(source);s.update(type='scene_container',container_id='MedicalOffice.'+identity,caption=caption,
   position=[x,y,z],yaw=yaw,initial_open_fraction=0,storage_pages=2)
 s.pop('layout_slot',None);actors.append(s)
 clearances.append(dict(id='MedicalOffice.'+identity,front_clearance_cm=110,includes_opening=True))
for i,x in enumerate((-750,-580,-410)):container(book,'RecordsCabinet'+str(i+1),'病历档案柜',x,-2230)
container(book,'ChiefMedicalLibrary','主任医学书柜',300,-2230)
container(shelf,'TeamReferenceShelf','医生参考资料',300,-65,180)
container(shelf,'TeamClinicalShelf','临床记录书架',930,-65,180)
def find_container(body):
 def visit(value):
  if isinstance(value,dict):
   if value.get('body','').endswith(body) and 'container_id' in value:yield value
   for v in value.values():yield from visit(v)
  elif isinstance(value,list):
   for v in value:yield from visit(v)
 return next(visit(WARD))
cart=find_container('SM_Hospital_MedicalCart_Body')
for i,(x,y) in enumerate(((-338,-760),(-338,-1580),(1610,-1530))):
 container(cart,'InstrumentCart'+str(i+1),'诊疗器械推车',x,y,90 if x>0 else -90)
firstaid=find_container('SM_Hospital_FirstAid_Body')
container(firstaid,'ClinicalFirstAid','诊室急救柜',1670,-2110,90,145)

# Existing WardGlassDoor supports double leaves, persistent open state and breakable glazing.
door=next(a for a in WARD['runtime_actors'] if a['type']=='glass_door')
for name,x,y,yaw in [('Consult01',-210,-500,0),('Consult02',-210,-1330,0),('Records',-210,-1990,0),
                     ('TeamHall',210,-450,0),('TeamWaiting',970,-880,90),('Chief',580,-1320,90),('Support',1350,-1320,90)]:
 a=math.radians(yaw)
 for side in (-1,1):
  s=copy.deepcopy(door);s.update(id='MedicalOffice.Door.'+name+str(side),position=[x-math.sin(a)*side*80.25,y+math.cos(a)*side*80.25,1.6],
      yaw=yaw,positive_hinge=side>0,auto_close_seconds=0.)
  # The shell contains one combined frame mesh. There is no independently
  # tagged WardFrame actor to attach to in the formal runtime assembler.
  s.pop('frame_id',None)
  actors.append(s)
# Measured floor and ceiling heights; reuse fixture emission with local, scheduled lights.
lamp_points=[(0,y) for y in (-210,-690,-1170,-1650,-2130)]
lamp_points += [(x,-1100) for x in (540,1050,1570,1850)]
lamp_points += [(-585,y) for y in (-300,-710,-1150,-1500,-1990)]
lamp_points += [(x,y) for x in (570,1250) for y in (-300,-690)]
lamp_points += [(580,-1640),(580,-2070),(1350,-1630),(1350,-2070)]
for i,(x,y) in enumerate(lamp_points):
 place('Ceiling.Lamp'+str(i),STAFF+'LampFixture',x,y,430,col=False,floor=False)
 lights.append(dict(id='MedicalOffice.Light'+str(i),position=[x,y,408],type='point',role='room',intensity=920 if x else 720,
    radius=440 if x else 340,optimized_radius_cm=440 if x else 340,color=[.80,.90,1.0] if x else [.89,.95,.9],
    cast_shadows=True,max_draw_distance_cm=3200,fade_range_cm=500,indirect_lighting_intensity=.3,source_radius=6,source_length=80))
actors.append(dict(type='post_process',position=[550,-1150,220],yaw=0,extent=[1464,1164,244],priority=15,
    blend_radius=80,exposure_ev=.95,exposure_bias=-.25,indirect_intensity=.8,saturation=.94,contrast=1.,vignette=.2,bloom=.08))
def paths(v):
 if isinstance(v,str) and v.startswith(('/Game/','/Script/')):yield v
 elif isinstance(v,dict):
  for x in v.values():yield from paths(x)
 elif isinstance(v,list):
  for x in v:yield from paths(x)
cells=[dict(min=[-914,-2314,-24],max=[1714,14,464]),dict(min=[1686,-1334,-24],max=[2014,-866,464])]
module=dict(id='MedicalDoctorOffice',family_id='MedicalDoctorOffice',display_name='医生办公室',role='room',
 encounter_role='medical_offices',revision='doctor_office_wing_20261010',min=[-914,-2314,-24],max=[2014,14,464],cells=cells,
 ports=[dict(id='entry',position=[0,0,0],normal=[0,1,0],width=300,height=280),
        dict(id='exit',position=[2000,-1100,0],normal=[1,0,0],width=300,height=280)],port_pairs=[[0,1]],
 parts=parts,lights=lights,runtime_actors=actors,anchors=[],props=[],
 walk_polyline=[[0,0,0],[0,-1100,0],[2000,-1100,0]],
 scene_keep_clear=[dict(min=[-130,-2300,0],max=[130,0,280]),dict(min=[0,-1225,0],max=[2000,-1010,280])],
 selection=dict(chance_per_run=1,max_per_run=1),authoring_only=False,runtime_assets=sorted(set(paths([parts,actors]))),
 authoring=dict(area_m2=611.2,program=['候诊走廊','全科诊室','复诊室','医生工作室','主任办公室','病历室','检查准备室'],
 reused_asset_count=len({p['mesh'] for p in parts if not p['id'].startswith('MedicalOffice.Shell.')}),furniture_clearances=clearances))
runpy.run_path(str(PROJECT/'SourceAssets/MedicalExecutiveOffice20261010/recipe.py'))['apply'](module)
runpy.run_path(str(PROJECT/'SourceAssets/MedicalOfficeWaitingFinish20261010/recipe.py'))['apply'](module)
runpy.run_path(str(PROJECT/'SourceAssets/MedicalOfficeLighting20261010/recipe.py'))['apply'](module)
(ROOT/'Config/module.json').write_text(json.dumps(module,ensure_ascii=False,indent=2),encoding='utf8')
print('MEDICAL_OFFICE_LAYOUT_AUTHORED',len(parts),'parts',len(actors),'actors',len(lights),'lights')
