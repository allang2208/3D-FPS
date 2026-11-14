"""Translate the six design pins to actor edits, in UE centimetres."""
from pathlib import Path
import json,gzip
import math
import numpy as np

ROOT=Path(__file__).resolve().parent
SCENE=json.loads((ROOT/'scene-inputs.json').read_text('utf8'))
ACTORS=SCENE['actors']
NODES={p[0]:p[1] for p in json.loads((ROOT/'design-points.json').read_text('utf8'))}
EDIT=[]
old=ROOT.parent/'FreightWarehouseWeathering20261110/Geometry'
station=ROOT.parent/'FreightStationUnifiedPatina20261111/Geometry'
def geo(folder,pattern,origin):
    with gzip.open(next(folder.glob(pattern)),'rt') as f:g=json.load(f)
    return np.array(g['vertices'])[np.array(g['indices']).reshape(-1,3)]+origin
wh=geo(old,'SM_CargoWarehouse_Paving*',[3760,-900,0])
slab=geo(old,'SM_CargoWarehouse_Floors*',[3760,-900,0])
floor=np.concatenate([wh,slab])
link=geo(station,'SM_RS_Transit_Floors*',[0,0,0])
link=link[:,:,[1,0,2]]*[-1,1,1]+[5460,-1400,0]
platform=np.concatenate([geo(station,'SM_Station_Paving*',[7760,-1400,0]),geo(station,'SM_Station_Floors*',[7760,-1400,0])])
cart=geo(station,'SM_SW_RepairCart*',[7310,-550,0])
wall_booth=geo(station,'SM_SW_Walls*',[7310,-550,0])
bridge=geo(station,'SM_Station_Bridge*',[7760,-1400,0])
def hits(t,x,y):
    a=t[:,0];b=t[:,1]-a;c=t[:,2]-a
    den=b[:,0]*c[:,1]-b[:,1]*c[:,0];good=abs(den)>1e-7;den=np.where(good,den,1)
    q=((x-a[:,0])*c[:,1]-(y-a[:,1])*c[:,0])/den
    r=(b[:,0]*(y-a[:,1])-b[:,1]*(x-a[:,0]))/den
    return (a[:,2]+q*b[:,2]+r*c[:,2])[good&(q>=-1e-6)&(r>=-1e-6)&(q+r<=1.000001)]
def top(t,x,y,z):
    h=hits(t,x,y); near=h[abs(h-z)<3]
    if len(near)==0:raise ValueError(f'No support at {(x,y,z)}')
    return float(max(near))
def mat(yaw,pitch=0):
    c,s=np.cos(np.deg2rad([yaw,pitch])),np.sin(np.deg2rad([yaw,pitch]))
    return np.array([[c[0]*c[1],-s[0],-c[0]*s[1]],[s[0]*c[1],c[0],-s[0]*s[1]],[s[1],0,c[1]]])
def operation(pin,op,source,**extra):
    EDIT.append(dict(point=pin,op=op,source=source,**extra))
def mesh(pin,source,xy,yaw,scale,receiver,z=0,new=None,lift=.045):
    a=ACTORS[source];m=SCENE['source_meshes'][a['mesh']];mi,ma=np.array(m['min']),np.array(m['max'])
    middle=(mi+ma)*scale/2;middle[2]=0
    rotation=mat(yaw)
    rotated=rotation@middle
    corners=(np.array([[x,y,0.] for x in (mi[0],ma[0]) for y in (mi[1],ma[1])])*scale-middle)@rotation.T
    h=max(top(receiver,xy[0]+dx,xy[1]+dy,z) for dx,dy,_ in [[0,0,0],*corners])
    p=[xy[0]-rotated[0],xy[1]-rotated[1],h-mi[2]*scale+lift]
    operation(pin,'copy' if new else 'move',source,p=p,r=[0,yaw,0],s=[scale]*3,id=new,support=h)
    return EDIT[-1]
def decal(pin,source,xy,receiver,size,yaw=0,wanted=0,new=None):
    z=top(receiver,*xy,wanted)
    operation(pin,'copy' if new else 'move',source,p=[*xy,z+.16],r=[-90,yaw,0],size=size,id=new)
def remove(pin,*labels):
    for l in labels:operation(pin,'retire',l)
E='WarehouseEntrance_'; U='FreightStation_'; D='WarehouseDerelict_'
P=E+'Packing_'
# 01. Retain the accepted box-and-pallet hierarchy, and recompose the material in front of it.
mesh('01',P+'Cardboard_0',[2769,212],12,1.48,floor)
mesh('01',P+'Cardboard_1',[2840,219],-10,1.18,floor,lift=.11)
mesh('01',P+'DiscardedForm_0',[2822,167],-30,.93,floor)
remove('01',*[P+v for v in ('Cardboard_2','Cardboard_7','Cardboard_8','DiscardedForm_1','DiscardedForm_2')])
a=mesh('01',P+'SplitBoardA',[2788,210],20,.85,floor,lift=.15)
b=mesh('01',P+'SplitBoardB',[2806,190],-55,.63,floor,lift=.13)
# Rest the crossing board against the lower board and the floor. Minimise the height
# of its centre across feasible pitches using sampled upper/lower source triangles.
def board(name):
    with gzip.open(ROOT/(name+'.json.gz'),'rt') as f:g=json.load(f)
    return np.array(g['v'])[np.array(g['t'])]
lower=(board('SM_WoodBoard01h')*a['s'])@mat(a['r'][1]).T+a['p']
upper=board('SM_WoodBoard01i')*b['s']
umin,umax=upper.min(axis=(0,1)),upper.max(axis=(0,1))
cloud=[]
for x in np.linspace(umin[0]+.2,umax[0]-.2,63):
    for y in np.linspace(umin[1]+.12,umax[1]-.12,9):
        h=hits(upper,x,y)
        if len(h):cloud.append([x,y,min(h)])
cloud=np.array(cloud)
world_xy=cloud@mat(b['r'][1]).T+b['p']
support=[]
for x,y,_ in world_xy:
    board_h=hits(lower,x,y)
    support.append(max(top(floor,x,y,0)+.11,max(board_h) if len(board_h) else -100))
best=None
for pitch in np.linspace(-10,10,161):
    v=cloud@mat(b['r'][1],pitch).T
    z=max(np.array(support)-v[:,2])+.045
    score=z+np.mean(v[:,2])
    if best is None or score<best[0]:best=(score,float(pitch),float(z))
b['p'][2]=best[2];b['r'][0]=best[1]
# 02. Source the fragments at the visible spall. Retire stray packing here.
remove('02',E+'RackEnd_Fragment_3')
decal('02',E+'Dust_RackEnd',[2325,-239],floor,[1.2,47,60],-7)
mesh('02',D+'ConcreteFragment_0',[2294,-239],16,1.62,floor,new='SpallHeel')
mesh('02',D+'ConcreteFragment_1',[2310,-224],-38,.78,floor,new='SpallChip')
mesh('02',D+'ConcreteFragment_1',[2334,-255],61,.52,floor,new='SpallFine')
# 03. Taper the transfer mark; remove the last loose carton in the narrow passage.
remove('03',U+'LinkSmallPacking')
decal('03',U+'LinkEdgeRub',[5620,-1520],link,[1.1,10,71],-3)
decal('03',U+'LinkEdgeRub',[5772,-1526],link,[1.1,5,31],1,new='FadingRub')
mesh('03',U+'LinkPaper',[5704,-1530],-28,.79,link)
# 04. Two runs beneath actual mullions. Each projector terminates below the sill.
for key,x,z,width,height in [('LongDrip',7731.7,62,32,80),('ShortDrip',7888.3,76,21,49)]:
    faces=hits(wall_booth[:,:,[0,2,1]],x,z);y=min(h for h in faces if -570<h<-550)
    operation('04','copy',U+'LinkShortLeak',id=key,p=[x,float(y)-.12,z],r=[0,90,0],size=[1.05,width/2,height/2])
mesh('04',U+'WorkshopExteriorPaperFold',[7728,-581],-62,.92,platform)
remove('04',U+'WorkshopExteriorPaper')
decal('04',U+'WorkshopWindowFoot',[7813,-574],platform,[1.5,13,128],1)
# 05. Recover the dropped shop fittings into the lower cart tray, and catch a folded cloth on its rail.
mesh('05',U+'WorkshopCartPacking',[8442,-310],-71,.86,cart,14.5,lift=.055)
mesh('05',U+'WorkshopCartJoint',[8427,-311],-15,.89,cart,14.5,lift=.15)
mesh('05',U+'WorkshopCartJoint',[8453,-309],55,.74,cart,14.5,new='LowerTrayCoupling',lift=.15)
operation('05','cloth',None,id='HandleCloth',p=[8380,-310,73],r=[0,0,0],s=[1,1,1])
decal('05',U+'WorkshopCartWheelLeft',[8387,-399],platform,[1,65,5],0)
decal('05',U+'WorkshopCartWheelRight',[8469,-384],platform,[1,50,4.5],0)
decal('05',U+'WorkshopCartResidue',[8422,-313],platform,[1.25,24,38],14)
# 06. Unequal deposits at railing feet keep the bridge landing and centre visually clear.
decal('06',U+'BridgeEdgeDust0',[10005,-2143],bridge,[.65,70,9],0,480)
decal('06',U+'BridgeEdgeDust2',[10504,-2452],bridge,[.65,42,8],0,480)
remove('06',U+'StairEdgeDust1')
(ROOT/'construction.json').write_text(json.dumps({'points':NODES,'operations':EDIT},ensure_ascii=False,indent=2),encoding='utf8')
print('DESIGN_POINTS_AUTHORED',len(EDIT))
