"""Compose small, supported dressing groups around the existing warehouse activity areas."""
from pathlib import Path
import json,gzip,math,random
ROOT=Path(__file__).resolve().parent
DATA=json.loads((ROOT/'inputs.json').read_text('utf8'))
ORIGIN=[3760.,-900.,0.]
TARGET=DATA['map'];TAG='FreightWarehouse.Weathering20261110'
MESHES={k.rsplit('/',1)[-1].split('.')[0]:dict(v,path=k) for k,v in DATA['meshes'].items() if '/UndergroundTunnel/' in k}
surfaces=[]
for path,row in DATA['meshes'].items():
    name=path.rsplit('/',1)[-1].split('.')[0]
    if name not in ('SM_CargoWarehouse_Paving','SM_CargoWarehouse_Floors','SM_CargoWarehouse_Dock'):continue
    if not row.get('geometry'):raise RuntimeError('Authoring needs the actual paving source surface')
    with gzip.open(ROOT/'Geometry'/row['geometry'],'rt',encoding='utf8') as f:g=json.load(f)
    v=g['vertices']
    for i in range(0,len(g['indices']),3):
        a,b,c=[v[j] for j in g['indices'][i:i+3]]
        determinant=(b[0]-a[0])*(c[1]-a[1])-(c[0]-a[0])*(b[1]-a[1])
        if abs(determinant)<1e-5 or max(a[2],b[2],c[2])-min(a[2],b[2],c[2])>.05:continue
        surfaces.append((a,b,c,determinant))

def ground(x,y):
    heights=[]
    for a,b,c,d in surfaces:
        u=((x-a[0])*(c[1]-a[1])-(c[0]-a[0])*(y-a[1]))/d
        v=((b[0]-a[0])*(y-a[1])-(x-a[0])*(b[1]-a[1]))/d
        if u>=-.0001 and v>=-.0001 and u+v<=1.0001:heights.append(a[2]+u*(b[2]-a[2])+v*(c[2]-a[2]))
    if not heights:raise RuntimeError('No authored support at '+str([x,y]))
    return max(heights)

def intersects(a,b):return a[0]<b[2] and a[2]>b[0] and a[1]<b[3] and a[3]>b[1]

reserved=[[-1720,720,180,1080],[-230,-680,230,1080],[-180,-680,1720,-320],
          [-1440,75,-1220,585],[-1440,-580,-1220,-55],[1220,75,1440,585],[350,1180,870,1400],
          [-1120,-925,-880,-600],[880,-925,1120,-600],[-115,-1130,115,-735]]
for a in DATA['actors']:
    c=a['bounds_center'];e=a['bounds_extent']
    x,y=c[0]-ORIGIN[0],c[1]-ORIGIN[1]
    if abs(x)>1600 or abs(y)>1500 or not a['components']:continue
    is_container=a['class_name']=='ColdSteelSceneContainer'
    is_prop=any('SM_Facility_' in comp['mesh'] or 'SM_CargoWarehouse_PalletJack' in comp['mesh'] for comp in a['components'])
    if not (is_container or is_prop) or c[2]-e[2]>145:continue
    pad=110 if is_container else 25
    reserved.append([x-e[0]-pad,y-e[1]-pad,x+e[0]+pad,y+e[1]+pad])

plan=dict(map=TARGET,baseline_map='/Game/GameMaps/Design/L_FreightTransit_BeforeWeathering',tag=TAG,origin=ORIGIN,
          parts=[],decals=[],bindings=[],groups={},omitted=[],preserve=dict(layout=True,gameplay=True,containers=True,lights=True),tests_run=False)
placed={}

def extent(row,scale,yaw):
    sx=(row['max'][0]-row['min'][0])*scale/2;sy=(row['max'][1]-row['min'][1])*scale/2
    c=abs(math.cos(math.radians(yaw)));s=abs(math.sin(math.radians(yaw)))
    return sx*c+sy*s,sx*s+sy*c

def part(group,name,xy,yaw=0,scale=1.,parent=None,flat=False):
    row=MESHES[name];ex,ey=extent(row,scale,yaw);selected=None
    shifts=[(0,0),(35,0),(-35,0),(0,35),(0,-35),(55,40),(-55,40),(55,-40),(-55,-40)] if not parent else [(0,0)]
    for dx,dy in shifts:
        x,y=xy[0]+dx,xy[1]+dy;box=[x-ex,y-ey,x+ex,y+ey]
        if box[0]<-1480 or box[2]>1480 or box[1]<-1380 or box[3]>1380:continue
        if any(intersects(box,r) for r in reserved):continue
        if not flat and not parent and any(intersects(box,p['box']) for p in placed.values() if not p['flat']):continue
        z=placed[parent]['top'] if parent else ground(x,y)
        if not parent:
            supports=[ground(x+dx2,y+dy2) for dx2,dy2 in ((-ex,-ey),(-ex,ey),(ex,-ey),(ex,ey))]
            if max(supports)-min(supports)>3.:continue
            z=max(z,*supports)
        selected=(x,y,z,box);break
    if selected is None:
        plan['omitted'].append(dict(group=group,mesh=name,requested=xy,reason='Preserve existing route, container access or support edge'));return None
    x,y,z,box=selected;mid=[(row['min'][i]+row['max'][i])/2 for i in range(2)]
    c=math.cos(math.radians(yaw));s=math.sin(math.radians(yaw))
    pos=[x-scale*(mid[0]*c-mid[1]*s)+ORIGIN[0],y-scale*(mid[0]*s+mid[1]*c)+ORIGIN[1],z-row['min'][2]*scale+.12]
    key=group+'_'+str(len(plan['parts'])+1).zfill(3)
    p=dict(id=key,group=group,mesh=row['path'],position=pos,yaw=yaw,scale=[scale]*3,collision=False,
           cast_shadow=not flat and (row['max'][2]-row['min'][2])*scale>8,max_draw_distance=3800 if flat else 5000,
           support_height=z,parent=parent)
    plan['parts'].append(p);plan['groups'][group]=plan['groups'].get(group,0)+1
    placed[key]=dict(box=box,flat=flat,top=z+(row['max'][2]-row['min'][2])*scale+.12,xy=[x,y])
    return key

def floor_decal(group,kind,xy,size,yaw=0):
    x,y=xy;z=ground(x,y)
    plan['decals'].append(dict(id=group+'_'+kind+'_'+str(len(plan['decals'])),group=group,material=kind,
        position=[x+ORIGIN[0],y+ORIGIN[1],z+.4],yaw=yaw,pitch=-90,roll=0,size=[2.,size[0]/2,size[1]/2]))

# Each group represents one use: broken packing, interrupted maintenance,
# unloading residue, or accumulation at a rack end. No layout RNG is consumed.
p=part('PackingBay','SM_WoodPallet01d',[-805,1235],-7)
if p:part('PackingBay','SM_WoodCrate01a',placed[p]['xy'],-7,parent=p)
part('PackingBay','SM_Dolly01a',[-1020,1310],-20)
part('PackingBay','SM_WoodBoard01a',[-960,1190],18,flat=True)
part('PackingBay','SM_WoodBoard01h',[-920,1340],-12,flat=True)
part('PackingBay','SM_DebrisPile01a',[-1010,1180],72,.7,flat=True)
part('PackingBay','SM_DebrisPile02b',[-650,1300],-24,.6,flat=True)

for name,xy,yaw in [('Sm_Toolbox01a',[-545,1225],-14),('SM_Bucket01b',[-605,1305],12),
                    ('SM_Bucket01b_lid',[-630,1275],-19),('SM_Paintcan01a',[-560,1302],15),
                    ('SM_GasCan01a',[-552,1140],-32),('SM_OilBottle01a',[-585,1160],7),
                    ('SM_WoodBoard01c',[-665,1155],64)]:part('RepairCabinet',name,xy,yaw,flat='Board' in name or 'lid' in name)

p=part('DockWest','SM_WoodPallet01e',[-1250,-1200],8)
if p:part('DockWest','SM_WoodCrate02a',placed[p]['xy'],8,parent=p)
part('DockWest','SM_WoodBoard01b',[-1210,-1350],-5,flat=True)
part('DockWest','SM_WoodBoard01i',[-1380,-1120],61,flat=True)
part('DockWest','SM_DebrisPile02a',[-1275,-1340],90,.62,flat=True)
part('DockWest','SM_Bucket01a',[-1380,-1285],12)

for name,xy,yaw,scale in [('SM_Oildrum01b',[1300,-1240],14,1),('SM_Oildrum01a',[1215,-1300],-9,1),
                         ('SM_GasCan01a',[1345,-1325],-22,1),('SM_OilBottle01a',[1270,-1320],12,1),
                         ('SM_Paintcan01a',[1190,-1210],30,1),('SM_DebrisPile03a',[1260,-1135],18,.55)]:
    part('DockService',name,xy,yaw,scale,flat='Debris' in name)

part('WestRackEnd','SM_DebrisPile02b',[-1370,650],90,.85,flat=True)
part('WestRackEnd','Sm_Cinderblock01a',[-1410,692],16)
part('WestRackEnd','Sm_Cinderblock01a',[-1358,688],-21)
part('WestRackEnd','SM_WoodBoard01d',[-1260,650],-8,flat=True)
part('WestRackGap','SM_DebrisPile02a',[-1365,0],90,.85,flat=True)
part('WestRackGap','SM_Paintcan01a',[-1435,-8],-14)
part('WestRackGap','SM_Bucket01b_lid',[-1410,22],33,flat=True)
part('EastRackEnd','SM_DebrisPile01a',[1350,670],90,.75,flat=True)
part('EastRackEnd','SM_WoodBoard01b',[1260,690],-15,flat=True)
part('EastRackEnd','SM_WoodBoard01i',[1330,720],25,flat=True)
part('ElectricalCorner','SM_Bucket01a',[1335,1030],15)
part('ElectricalCorner','SM_GasCan01a',[1380,1075],-8)
part('ElectricalCorner','SM_DebrisPile02b',[1280,1045],65,.5,flat=True)
part('CargoWest','SM_DebrisPile03a',[-985,350],16,.57,flat=True)
part('CargoWest','SM_WoodBoard01h',[-1000,240],-33,flat=True)
part('CargoEast','SM_DebrisPile01a',[1005,90],-21,.65,flat=True)
part('CargoEast','SM_WoodBoard01a',[960,220],-17,flat=True)
part('PalletJackService','Sm_Toolbox01a',[-650,-265],24)
part('PalletJackService','SM_OilBottle01a',[-620,-220],-18)
part('PalletJackService','SM_GasCan01a',[-680,-270],-27)

rng=random.Random(20261110)
scatter=[('PackingBay',[-930,1230],['Junk01a','Junk03a','Junk06a'],7,155),
         ('RepairCabinet',[-590,1225],['MetalDebris01a','MetalDebris01b','Junk03a'],5,80),
         ('DockWest',[-1280,-1240],['Junk01a','Junk06a','ConcreteDebris01b'],5,100),
         ('DockService',[1280,-1200],['MetalDebris01a','MetalDebris01g','ConcreteDebris01c'],5,110),
         ('WestRackEnd',[-1360,660],['ConcreteDebris01a','ConcreteDebris01c','ConcreteDebris01g'],6,70),
         ('WestRackGap',[-1370,0],['MetalDebris01b','Junk03a','ConcreteDebris01d'],4,45),
         ('EastRackEnd',[1340,690],['Junk01a','Junk03a','ConcreteDebris01c'],6,80),
         ('CargoWest',[-985,350],['Junk01a','Junk03a','MetalDebris01b'],5,95),
         ('CargoEast',[1000,100],['Junk01a','Junk06a','ConcreteDebris01g'],5,95),
         ('ElectricalCorner',[1315,1040],['MetalDebris01g','Junk03a'],4,65)]
for group,center,names,count,radius in scatter:
    for i in range(count):
        angle=rng.uniform(0,math.tau);r=radius*math.sqrt(rng.random())
        part(group,'SM_Decal_'+names[i%len(names)],[center[0]+math.cos(angle)*r,center[1]+math.sin(angle)*r],rng.uniform(-180,180),rng.uniform(.85,1.3),flat=True)
    floor_decal(group,'Dust',center,[radius*2.7,radius*2.2],rng.uniform(-30,30))

for group,xy,size,yaw in [('DockService',[1280,-1250],[220,180],17),('RepairCabinet',[-570,1180],[100,130],-16),('PalletJackService',[-650,-260],[110,75],10)]:
    floor_decal(group,'Oil',xy,size,yaw)
for xy,size,yaw in [([-850,1125],[85,240],10),([-750,1125],[50,210],8),([950,-1050],[70,200],-12),([-560,-210],[65,170],22),([830,100],[45,210],90)]:
    floor_decal('HandlingWear','Scuff',xy,size,yaw)
for x,y in [(-1455,600),(-1455,-100),(-1455,-1300),(1455,600),(1455,-100),(1455,-1300)]:
    floor_decal('ColumnFoot','Damp',[x-25 if x>0 else x+25,y],[90,125],0)

# Locate the real interior wall face from its source triangles, including its
# bevels and openings. A box center is not a decal projection datum.
wall=next(v for k,v in DATA['meshes'].items() if k.endswith('/SM_CargoWarehouse_Walls.SM_CargoWarehouse_Walls'))
with gzip.open(ROOT/'Geometry'/wall['geometry'],'rt',encoding='utf8') as f:wall_geometry=json.load(f)
def wall_contact(x,y,z,yaw):
    axis=0 if yaw in (0,180) else 1;other=1-axis;query=[x,y,z];hits=[]
    vertices=wall_geometry['vertices'];indices=wall_geometry['indices']
    for i in range(0,len(indices),3):
        a,b,c=[vertices[j] for j in indices[i:i+3]]
        d=(b[other]-a[other])*(c[2]-a[2])-(c[other]-a[other])*(b[2]-a[2])
        if abs(d)<1e-6:continue
        s=((query[other]-a[other])*(c[2]-a[2])-(c[other]-a[other])*(z-a[2]))/d
        t=((b[other]-a[other])*(z-a[2])-(query[other]-a[other])*(b[2]-a[2]))/d
        if s>=-.0001 and t>=-.0001 and s+t<=1.0001:
            pos=a[axis]+s*(b[axis]-a[axis])+t*(c[axis]-a[axis])
            if pos*query[axis]>0 and abs(pos)>1200:hits.append(pos)
    if not hits:raise RuntimeError('No solid wall behind runoff '+str(query))
    face=min(hits,key=abs);query[axis]=face-math.copysign(.35,face)
    return [query[0]+ORIGIN[0],query[1]+ORIGIN[1],z]

# Rust is associated with the existing steel bents and service corner; shallow
# projections stop before nearby racks and do not paint through the opposite wall.
for index,(x,y,z,w,h,yaw) in enumerate([
    (-1393,600,265,55,300,180),(-1393,-100,215,38,230,180),(1393,600,300,58,360,0),
    (1393,-100,200,42,210,0),(-1160,-1393,375,70,300,-90),(1270,-1393,380,82,350,-90),
    (-790,1393,270,60,300,90),(1050,1393,335,46,200,90)]):
    plan['decals'].append(dict(id='Runoff_'+str(index),group='WallRunoff',material='Rust',position=wall_contact(x,y,z,yaw),yaw=yaw,pitch=0,roll=0,size=[2.5,w/2,h/2]))
for index,(x,y,z,w,h,yaw) in enumerate([(-1455,600,35,50,65,180),(1455,600,40,50,70,0),(-1455,-100,40,50,70,180),(1455,-100,40,50,70,0)]):
    plan['decals'].append(dict(id='SteelFoot_'+str(index),group='ColumnFoot',material='Rust',position=[x+ORIGIN[0]+(20 if x<0 else -20),y+ORIGIN[1],z],yaw=yaw,pitch=0,roll=0,size=[3.,w/2,h/2]))

for actor in DATA['actors']:
    if 'AbandonedCargoWarehouse' not in actor['tags']:continue
    for component in actor['components']:
        name=component['mesh'].rsplit('/',1)[-1].split('.')[0]
        family='Wall' if name=='SM_CargoWarehouse_Walls' else 'Floor' if name in ('SM_CargoWarehouse_Floors','SM_CargoWarehouse_Paving','SM_CargoWarehouse_Dock','SM_CargoWarehouse_StairTreads') else None
        if family:
            plan['bindings'].append(dict(actor=actor['name'],component=component['name'],mesh=component['mesh'],slot=0,before=component['materials'][0],after=family))
(ROOT/'Config/layout.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(dict(parts=len(plan['parts']),decals=len(plan['decals']),groups=plan['groups'],bindings=len(plan['bindings']),omitted=len(plan['omitted']))))
