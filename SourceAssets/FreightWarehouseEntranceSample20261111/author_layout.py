"""A bounded packing / west rack / wall assembly. Coordinates are UE centimetres."""
from pathlib import Path
import json,gzip,math
import numpy as np
ROOT=Path(__file__).resolve().parent
OLD=ROOT.parent/'FreightWarehouseWeathering20261110'
ORIGIN=np.array([3760.,-900.,0.])
data=json.loads((OLD/'inputs.json').read_text('utf8'))
fresh=json.loads((ROOT/'authoring-inputs.json').read_text('utf8'))
meshes={p.split('/')[-1].split('.')[0]:dict(r,path=p) for p,r in {**data['meshes'],**fresh['meshes']}.items()}
cache={}
def geometry(name):
    if name not in cache:
        path=ROOT/'Geometry'/(name+'.json.gz')
        if not path.exists():path=OLD/'Geometry'/meshes[name]['geometry']
        with gzip.open(path,'rt',encoding='utf8') as f:g=json.load(f)
        cache[name]=np.array(g['vertices'])[np.array(g['indices']).reshape(-1,3)]
    return cache[name]
def hits(tris,xy):
    a=tris[:,0];b=tris[:,1]-a;c=tris[:,2]-a
    det=b[:,0]*c[:,1]-c[:,0]*b[:,1];valid=np.abs(det)>1.e-7
    det=np.where(valid,det,1.)
    u=((xy[0]-a[:,0])*c[:,1]-c[:,0]*(xy[1]-a[:,1]))/det
    v=(b[:,0]*(xy[1]-a[:,1])-(xy[0]-a[:,0])*b[:,1])/det
    return (a[:,2]+u*b[:,2]+v*c[:,2])[valid&(u>=-.0001)&(v>=-.0001)&(u+v<=1.0001)]
floor=np.concatenate([geometry(n) for n in ('SM_CargoWarehouse_Paving','SM_CargoWarehouse_Floors')])
def ground(x,y):return float(max(hits(floor,(x,y))))
def rot(yaw):
    c=math.cos(math.radians(yaw));s=math.sin(math.radians(yaw))
    return np.array([[c,-s,0],[s,c,0],[0,0,1]])
plan={'map':'/Game/GameMaps/Design/L_FreightTransit_Theme_Subject','tag':'FreightWarehouse.EntranceSample20261111',
      'origin':ORIGIN.tolist(),'parts':[],'decals':[],'remove_labels':[],
      'preserve':['original wall and floor material bindings','original actors and room layout','all containers and interaction logic','all lights and post process','main route and spawn'],
      'tests_run':False,'rendered':False}
oldplan=json.loads((OLD/'Config/layout.json').read_text('utf8'))
for r in oldplan['parts']+oldplan['decals']:
    if r['group'] in ('PackingBay','RepairCabinet','WestRackEnd') or r['id'] in ('Runoff_0','Runoff_6','SteelFoot_0','ColumnFoot_Damp_18'):
        plan['remove_labels'].append('WarehouseWeathering_'+r['id'])
placed={}
def part(key,name,xy,yaw=0,scale=1.,support='floor',flat=False,group='Packing'):
    m=meshes[name];s=np.array([scale]*3 if isinstance(scale,(int,float)) else scale);R=rot(yaw)
    mid=(np.array(m['min'])+m['max'])/2
    offset=np.array([xy[0],xy[1],0])-R@(mid*s*np.array([1,1,0]))
    ex=(np.abs(R)@((np.array(m['max'])-m['min'])*s/2))[:2]
    if support=='floor':z=max(ground(xy[0]+dx,xy[1]+dy) for dx,dy in ((0,0),(-ex[0],-ex[1]),(-ex[0],ex[1]),(ex[0],-ex[1]),(ex[0],ex[1])))
    elif support.startswith('rack:'):
        wanted=float(support.split(':')[1]);h=hits(geometry('SM_CargoWarehouse_RackDecks_V2'),xy)
        z=float(min(h,key=lambda a:abs(a-wanted)))
        if abs(z-wanted)>.2:raise RuntimeError('No requested deck at '+key)
    else:
        parent=placed[support];tris=geometry(parent['name'])*parent['scale']
        tris=tris@rot(parent['yaw']).T+parent['local_position']
        # Sample multiple actual top boards inside the receiving object's footprint.
        samples=[]
        child_path=ROOT/'Geometry'/(name+'.json.gz')
        child=(geometry(name)*s)@R.T+offset if child_path.exists() else None
        for dx in np.linspace(-.43,.43,13):
            for dy in np.linspace(-.43,.43,13):
                q=(xy[0]+dx*2*ex[0],xy[1]+dy*2*ex[1]);h=hits(tris,q)
                low=hits(child,q) if child is not None else [m['min'][2]*s[2]]
                if len(h) and len(low):samples.append(float(max(h)-min(low)+m['min'][2]*s[2]))
        if len(samples)<3:raise RuntimeError('Insufficient board support '+key)
        z=max(samples)
    offset[2]=z-m['min'][2]*s[2]+(.08 if flat else .03)
    row={'id':key,'group':group,'mesh':m['path'],'position':(offset+ORIGIN).tolist(),'rotation':[0,yaw,0],
         'scale':s.tolist(),'support':support,'support_z':z,'collision':'NoCollision' if flat else 'BlockAll',
         'shadow':not flat,'draw_distance':3800 if flat else 6000}
    # All blocking additions stay beyond the original entrance lane y=1080.
    if group=='Packing' and row['collision']=='BlockAll' and xy[1]-ex[1]<1090:raise RuntimeError('Packing object crosses entrance clearance '+key)
    if xy[0]-ex[0]<-1480 or xy[1]+ex[1]>1380:raise RuntimeError('Object exceeds room '+key)
    plan['parts'].append(row)
    placed[key]={'name':name,'scale':s,'yaw':yaw,'local_position':offset,'row':row}
    return key
def decal(key,material,xyz,wh,face='floor',angle=0,depth=1.2,group='Surface'):
    x,y,z=xyz
    if face=='floor':
        z=ground(x,y)+.25;rotation=[-90,angle,0]
    elif face=='deck':rotation=[-90,angle,0];z+=.15
    elif face=='south':y=1385.65;rotation=[0,90,angle]
    elif face=='west':x=-1485.65;rotation=[0,180,angle]
    else:rotation=[0,180,angle]
    plan['decals'].append({'id':key,'group':group,'material':material,'position':(np.array([x,y,z])+ORIGIN).tolist(),
                           'rotation':rotation,'size':[depth,wh[0]/2,wh[1]/2]})
# Packing remnant: two irregular pallets and one remaining packed crate.
# This retains the old packing-area footprint, with clear access to the metal loot case west of it.
p=part('Packing_LoadPallet','SM_WoodPallet01a',[-805,1238],-5)
part('Packing_RemainingCrate','SM_WoodCrate01a',[-808,1241],-5,support=p)
p=part('Packing_BrokenPallet','SM_WoodPallet01f',[-1000,1255],7)
part('Packing_EmptyReturnPallet','SM_WoodPallet01d',[-998,1254],3,support=p)
part('Packing_Dolly','SM_Dolly01a',[-665,1313],172)
part('Packing_Toolbox','Sm_Toolbox01a',[-810,1237],75,support='Packing_RemainingCrate')
for key,name,xy,yaw,s in [
 ('SplitBoardA','SM_WoodBoard01h',[-980,1120],-14,.85),
 ('SplitBoardB','SM_WoodBoard01i',[-933,1137],27,.58),
 ('LooseSlat','SM_WoodBoard01b',[-1103,1324],83,.70)]:
    part('Packing_'+key,name,xy,yaw,s,flat=True)
for i,(variant,xy,yaw,s) in enumerate([
 (1,[-944,1160],-23,1),(2,[-697,1188],32,.9),(3,[-920,1328],78,.8),
 (5,[-1034,1144],-56,.7),(6,[-1030,1093],20,.75),(7,[-870,1129],-5,1.2),
 (4,[-717,1089],63,.7),(3,[-888,1047],17,.72),(7,[-1050,983],-80,.75)]):
    part('Packing_Cardboard_'+str(i),'SM_Decal_Junk0'+str(variant)+'a',xy,yaw,s,flat=True)
for i,(xy,yaw) in enumerate([([-657,1160],-34),([-866,1083],15),([-1007,1012],81)]):
    part('Packing_DiscardedForm_'+str(i),'SM_IncidentDetail_Paper'+str(i),xy,yaw,flat=True)
# Adjacent W1 rack: fill the previously empty upper front bay sparingly.
# Occupied cargo bays and all search containers are left in place.
part('Rack_UpperBrokenPallet','SM_WoodPallet01c',[-1330,217],90,.82,support='rack:346',group='Rack')
part('Rack_UpperSlat','SM_WoodBoard01c',[-1328,216],92,.73,support='Rack_UpperBrokenPallet',flat=True,group='Rack')
part('Rack_LowerEmptyPallet','SM_WoodPallet01e',[-1330,442],90,.84,support='rack:20',group='Rack')
part('Rack_LowerBox','SM_WoodCrate01a',[-1331,433],88,.78,support='Rack_LowerEmptyPallet',group='Rack')
for i,(variant,xy,level,yaw) in enumerate([(4,[-1336,119],346,-13),(6,[-1348,320],346,80),(3,[-1320,542],183,8),(7,[-1281,533],20,32)]):
    part('Rack_Cardboard_'+str(i),'SM_Decal_Junk0'+str(variant)+'a',xy,yaw,.7,support='rack:'+str(level),flat=True,group='Rack')
# End-of-rack fragments follow a single damaged wall patch, avoiding random rubble everywhere.
part('RackEnd_Splinter','SM_WoodBoard01d',[-1354,635],-12,.72,flat=True,group='RackEnd')
part('RackEnd_DustDebris','SM_DebrisPile02b',[-1451,674],-6,.38,flat=True,group='RackEnd')
for i,(n,xy,yaw,s) in enumerate([('SM_Decal_ConcreteDebris01a',[-1455,627],21,.7),('SM_Decal_ConcreteDebris01c',[-1424,657],-37,.8),('SM_Decal_ConcreteDebris01g',[-1412,695],68,1.2),('SM_Decal_Junk02a',[-1321,658],9,.68)]):
    part('RackEnd_Fragment_'+str(i),n,xy,yaw,s,flat=True,group='RackEnd')
# Texture-specific surface roles; these are shallow overlays, never replacement wall/floor bindings.
for key,xy,wh,angle in [('PalletHalo',[-958,1234],[340,185],-5),('PackingWallFoot',[-809,1344],[340,66],0),('RackFoot',[-1424,390],[90,395],5),('RackEnd',[-1394,650],[145,110],-19)]:
    decal('Dust_'+key,'Dust',xy+[0],wh,angle=angle)
for key,xy,wh,angle in [('DollyWheelLeft',[-682,1153],[19,153],-4),('DollyWheelRight',[-643,1155],[18,153],-4),('Handling',[-912,1081],[88,145],71)]:
    decal('Scuff_'+key,'Scuff',xy+[0],wh,angle=angle)
for key,xy,z,wh,angle in [('Lower',[-1378,439],20,[45,210],7),('MiddleEnd',[-1340,535],183,[110,32],-8),('UpperBack',[-1386,247],346,[36,245],-3)]:
    decal('Dust_Rack'+key,'Dust',xy+[z],wh,face='deck',angle=angle,depth=.7)
# A few vertical marks with different causes and heights, leaving broad original concrete visible.
decal('Wall_PackingLowWear','Dust',[-880,0,65],[340,110],face='south',angle=3)
decal('Wall_PackingRub','Scuff',[-1015,0,104],[115,85],face='south',angle=90)
decal('Wall_PackingPlasterLoss','Damage',[-681,0,87],[96,64],face='south',angle=-12)
decal('Wall_PackingHairline','Crack',[-1080,0,277],[78,235],face='south',angle=8)
decal('Wall_PackingOldDamp','Damp',[-875,0,412],[195,166],face='south',angle=7)
decal('Wall_RackEndLoss','Damage',[0,658,68],[89,105],face='west',angle=16)
decal('Wall_RackHairline','Crack',[0,365,427],[86,224],face='west',angle=-14)
decal('Wall_RackFootDamp','Damp',[0,312,94],[335,156],face='west',angle=-4)
# Rack beam front is x=-1241 cm; shallow depth only affects the beam face.
for i,(y,z) in enumerate([(521,338),(122,175),(505,12)]):
    decal('Rack_BeamWear_'+str(i),'Scuff',[-1240.65,y,z],[69,8],face='rackfront',angle=90,depth=.7)
(ROOT/'Config').mkdir(exist_ok=True)
(ROOT/'Config/layout.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf8')
print('ENTRANCE_LAYOUT_AUTHORED',len(plan['parts']),len(plan['decals']),len(plan['remove_labels']))
