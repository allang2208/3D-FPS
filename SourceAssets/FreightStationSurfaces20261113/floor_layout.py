"""Bake registered surface deposits in station world centimetres. Each projection has its own support height."""
from pathlib import Path
import json,math
import numpy as np
from PIL import Image
from scipy.spatial import cKDTree
from scipy.interpolate import PchipInterpolator
R=Path(__file__).resolve().parent
out=R/'Textures';out.mkdir(exist_ok=True)
plan=[]
def clamp(a):return np.clip(a,0.,1.)
def ease(a,b,x):
    t=clamp((x-a)/(b-a));return t*t*(3.-2.*t)
def noise(x,y,scale,seed):
    a=x/scale;b=y/scale;i=np.floor(a);j=np.floor(b);u=ease(0,1,a-i);v=ease(0,1,b-j)
    def corner(i,j):return np.mod(np.sin(i*17.53017+j*71.021+seed*11.293)*39679.832,1.)
    return (corner(i,j)*(1-u)+corner(i+1,j)*u)*(1-v)+(corner(i,j+1)*(1-u)+corner(i+1,j+1)*u)*v
def gap(p,o,span):return abs((p-o+span/2)%span-span/2)
def lines(points):
    q=np.asarray(points);s=np.linspace(0,1,600)
    curve=PchipInterpolator(np.linspace(0,1,len(q)),q,axis=0)(s)
    t=np.gradient(curve,axis=0);t/=np.linalg.norm(t,axis=1)[:,None]
    normal=np.stack([-t[:,1],t[:,0]],axis=1)
    return [(cKDTree(curve+normal*d),curve.min(0)-56,curve.max(0)+56,s) for d in (-40.,40.)]
tracks=sum([lines(p) for p in (
 [(5745,-1405),(6005,-1409),(6235,-1376),(6432,-1297),(6658,-1278)],
 [(8509,-474),(8687,-555),(8953,-591),(9303,-574),(9465,-512)],
 [(6725,-2384),(6830,-2497),(7038,-2583),(7405,-2594),(7680,-2598)]
)],[])
# Physical wall edges and plinths, with gaps at active doors. Distances are in centimetres.
edges=[(6174,-3036,10946,-3036),(6174,236,10946,236),(6174,-3036,6174,-1560),(6174,-1240,6174,236),
 (5874,-1616,6174,-1616),(5874,-1184,6174,-1184),(7969,-3336,7969,-3050),(8401,-3336,8401,-3050),
 (5460,-1554,5860,-1554),(5460,-1246,5860,-1246),(7303,-557,8317,-557),(7303,157,8317,157),
 (7303,-557,7303,157),(8317,-557,8317,157),(10946,-3036,10946,-1925),(10946,-875,10946,236)]
# The north service port stays open through the main hall wall.
edges[0:1]=[(6174,-3036,8028,-3036),(8342,-3036,10946,-3036)]
def dist_to_edges(x,y,region):
    d=np.full(x.shape,999.,dtype='f')
    x0,y0,x1,y1=region
    for ax,ay,bx,by in edges:
        if max(ax,bx)+140<x0 or min(ax,bx)-140>x1 or max(ay,by)+140<y0 or min(ay,by)-140>y1:continue
        u=clamp(((x-ax)*(bx-ax)+(y-ay)*(by-ay))/((bx-ax)**2+(by-ay)**2))
        d=np.minimum(d,np.hypot(x-ax-u*(bx-ax),y-ay-u*(by-ay)))
    return d
def save(name,rgb,alpha,rough):
    rgb=np.where(rgb<=.0031308,12.92*rgb,1.055*np.maximum(rgb,0.)**(1/2.4)-.055)
    Image.fromarray(np.uint8(255*clamp(np.dstack((rgb,alpha)))+.5)).save(out/('T_'+name+'_Color.png'),compress_level=2)
    Image.fromarray(np.uint8(255*clamp(rough)+.5)).save(out/('T_'+name+'_Rough.png'),compress_level=2)
def bake(name,kind,region,section,orient=0):
    x0,y0,x1,y1=section
    # Round to power of two for UE texture streaming, retaining the actual projection dimensions.
    def res(length):return 2**int(np.clip(math.ceil(math.log2(length*1.05)),6,10))
    W,H=res(x1-x0),res(y1-y0)
    x,y=np.meshgrid(x0+(np.arange(W)+.5)*(x1-x0)/W,y0+(np.arange(H)+.5)*(y1-y0)/H)
    ax,ay,bx,by=region;salt=17+orient
    a=noise(x,y,91,salt);b=noise(x,y,17,salt+5);c=noise(x,y,3.9,salt+13)
    grain=noise(x,y,1.75,68)
    grit=.30+.29*b+.22*c+.19*grain
    seam=np.zeros_like(x);rubber=np.zeros_like(x);film=np.zeros_like(x);dust=np.zeros_like(x)
    tile=kind in ('Slab','Link')
    if tile:
        px=(bx-ax)/math.ceil((bx-ax)/120.);py=(by-ay)/math.ceil((by-ay)/90.)
        if kind=='Link':px,py=100.,81.
        joint=np.minimum(gap(x,ax,px),gap(y,ay,py))
        seam=(1-ease(.27+.21*c,1.16,joint))*(.30+.29*b+.15*c)
        seam+=.095*np.exp(-joint/2.7)*ease(.32,.83,b)
        toe=dist_to_edges(x,y,section)
        dust=grit*(.032+.045*a+np.exp(-toe/(7+15*b))*.53+.17*np.exp(-joint/3.2))
        tx=np.floor((x-ax)/px);ty=np.floor((y-ay)/py)
        film=(.017+.053*noise(tx,ty,1,46)+.034*a)*(.56+.44*b)
        for tree,lo,hi,ss in tracks:
            if hi[0]<x0 or lo[0]>x1 or hi[1]<y0 or lo[1]>y1:continue
            inside=(x>=lo[0])&(x<=hi[0])&(y>=lo[1])&(y<=hi[1])
            if not np.any(inside):continue
            d,index=tree.query(np.column_stack([x[inside],y[inside]]),workers=3)
            travel=ss[index]; fade=ease(.0,.085,travel)*(1-ease(.86,1.,travel))
            f=(1-ease(1.1,2.55,d))*(.30+.61*b[inside])*(.47+.53*c[inside])
            f*=fade*(.24+.76*ease(-.60,.47,np.sin(travel*34)+.72*a[inside]))
            rubber[inside]=np.maximum(rubber[inside],f*.69)
        # Mask the approved cart sample and both platform safety strips in world space.
        sample=np.maximum.reduce([8317-x,x-8717,-600-y,y+200,np.zeros_like(x)])
        keep=ease(0.,9.,sample)
        track_gap=np.minimum(abs(y+1925),abs(y+875))
        keep*=np.maximum(1-ease(7205,7211,x),ease(51.,57.,track_gap))
    else:
        keep=1.
        if kind=='Bed':
            path=np.minimum(abs(y+1665),abs(y+1135))
            side=np.minimum(abs(y-ay),abs(by-y))
            dust=(.08+.28*np.exp(-side/38)+.10*ease(48,158,path))*grit
            film=(.045+.21*np.exp(-(path/49)**2))*(.31+.69*b)*(.48+.52*a)
        elif kind=='Bridge':
            edge=np.minimum.reduce([abs(x-ax),abs(x-bx),abs(y-ay),abs(y-by)])
            dust=(.029+.26*np.exp(-edge/23))*(.38+.62*b)*grit
            film=.017+.028*a
        elif kind in ('Tread','Recovery'):
            edge=np.minimum(y-ay,by-y)
            dust=(.036+.26*np.exp(-edge/26)+.08*np.exp(-(bx-x)/6))*grit
            film=.02+.050*a
            keep=ease(.8,3.3,x-ax)*ease(.0,1.7,bx-x)
        elif kind=='Coping':
            dust=(.045+.19*b)*grit;film=.052*a
    dust*=1-.70*rubber
    weights=(seam,rubber,dust,film)
    cols=((.025,.023,.020),(.045,.041,.037),(.28,.254,.214),(.054,.049,.043) if kind=='Bed' else (.225,.213,.195))
    total=np.maximum(1.e-8,sum(weights));rgb=sum(v[:,:,None]*np.array(col) for v,col in zip(weights,cols))/total[:,:,None]
    rough=sum(v*num for v,num in zip(weights,(.84,.50,.94,.71 if kind in ('Slab','Link') else .64)))/total
    alpha=(1.-np.prod([1.-v for v in weights],axis=0))*keep
    save(name,rgb,alpha,rough)
def decal(label,tex,rect,z,depth):
    ax,ay,bx,by=rect
    plan.append(dict(label=label,texture=tex,pos=[(ax+bx)/2,(ay+by)/2,z],size=[depth,(by-ay)/2,(bx-ax)/2],kind='floor'))
def zone(label,kind,region,z,depth):
    ax,ay,bx,by=region
    nx=math.ceil((bx-ax)/1000);ny=math.ceil((by-ay)/1000)
    for i in range(nx):
        for j in range(ny):
            rect=(ax+(bx-ax)*i/nx,ay+(by-ay)*j/ny,ax+(bx-ax)*(i+1)/nx,ay+(by-ay)*(j+1)/ny)
            name=f'{label}_{i}_{j}';bake(name,kind,region,rect);decal(name,name,rect,z,depth)
for label,kind,region,z,depth in [
 ('Concourse','Slab',(6160,-3050,7210,250),-.90,1.7),
 ('NorthPlatform','Slab',(7210,-3050,10960,-1925),-.90,1.7),
 ('SouthPlatform','Slab',(7210,-875,10960,250),-.90,1.7),
 ('WestVestibule','Slab',(5860,-1630,6160,-1170),-.90,1.7),
 ('SideVestibule','Slab',(7955,-3350,8415,-3050),-.90,1.7),
 ('Link','Link',(5460,-1562,5860,-1238),.02,.31),
 ('TrackBed','Bed',(7210,-1925,11560,-875),-180.,.28),
 ('Bridge','Bridge',(9985,-3020,10525,220),480.,.25)]:zone(label,kind,region,z,depth)
for kind,height,going,width,count in [('Tread',16.,30.,510.,30),('Recovery',-15.,30.,500.,12)]:
    for v in range(5):
        bake(f'{kind}_{v}',kind,(0,0,going,width),(0,0,going,width),v*27)
    for flight,cy in enumerate([-2765.,-35.] if kind=='Tread' else [-1400.]):
        start=9085. if kind=='Tread' else 7210.
        for step in range(count):
            ax=start+step*going;name=f'{kind}_{flight}_{step:02}';tex=f'{kind}_{(step*3+flight)%5}'
            decal(name,tex,(ax,cy-width/2,ax+going,cy+width/2),height*(step+1),.18)
for label,cy in [('CopingNorth',-1933.),('CopingSouth',-867.)]:
    zone(label,'Coping',(7210,cy-18.5,10960,cy+18.5),4.50,.21)
(R/'floor-plan.json').write_text(json.dumps(plan,indent=1),'utf8')
print('Floor projections',len(plan),'unique texture sets',len({a['texture'] for a in plan}))
