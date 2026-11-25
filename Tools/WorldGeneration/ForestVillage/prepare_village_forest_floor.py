"""Offline, seed-stable Forest Floor patches in village-local metres."""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt, gaussian_filter, label, map_coordinates

from generate_village_relief import ROOT
from prepare_village_street_relief import refitted_sites
from layout_geometry import house_paths, plot_geometry, wall_segments
from village_ground_relief import box, distance, mill_yard_gap
from village_tread import ramp


MASK = 'T_VillageForestFloorPatches'
DEFAULT_SEED = 251143
PIXELS = (2048,1024)


def lines(plan,kit):
    roads = [(v['points'],v['width']) for v in plan['roads']] + house_paths(plan,kit)
    lanes = [[(*p, width*.5) for p in points] for points,width in roads]
    lanes += [plan['tavern']['inn']['hall_road']['stations'], plan['tavern_forecourt']['trail']]
    cx,cy = plan['chapel']['center']
    lanes += [[(*plan['chapel']['trail'],1.05),(cx-26.50,cy,1.05),(cx-11.45,cy,1.2)],
              [(cx-18.5,cy,.67),(cx-16.7,cy+4.5,.70),(cx-12.9,cy+8.5,.67),(cx-9.75,cy+9.75,.65)]]
    wall = [(p[1:3],p[3:5],half) for p,half in wall_segments(plan)]
    f,b,s,g = plan['chapel']['yard']
    yard = [(cx+u,cy+v) for u,v in [(f,g),(f,s),(b,s),(b,-s),(f,-s),(f,-g)]]
    wall += [(a,b,.52) for a,b in zip(yard,yard[1:])]
    ex,ey = plan['surface_extent_m']
    corners = [(ex-6,ey),(-ex+6,ey),(-ex,ey-6),(-ex,-ey+6),(-ex+6,-ey),(ex-6,-ey),(ex,-ey+6),(ex,ey-6)]
    wall += [(a,b,.78) for a,b in zip(corners,corners[1:]+corners[:1])]
    return lanes, wall


def clearances(plan,kit,lanes,contacts):
    ex,ey=plan['surface_extent_m']
    ax=np.arange(-ex,ex+.125,.25)
    ay=np.arange(-ey,ey+.125,.25)
    x,y=np.meshgrid(ax,ay)
    hard=np.full(x.shape,1000.)
    def reserve(gap):
        np.minimum(hard,gap,out=hard)
    reserve(refitted_sites(x,y,plan))
    for h in plan['houses']:
        shape=plot_geometry(h,kit[h[2]],plan)
        reserve(box(x,y,shape['center'],shape['half'],shape['angle']))
        reserve(distance(x,y,[shape['entry'],shape['step']])-.78)
        if h[0]=='05':reserve(mill_yard_gap(x,y,shape))
    for yard in plan['service_clearings']:
        reserve(box(x,y,yard['center'],yard['half'],yard['yaw']))
    left,bottom,right,top=plan['blacksmith']['smelting_yard']['bounds_m']
    reserve(box(x,y,((left+right)/2,(top+bottom)/2),((right-left)/2,(top-bottom)/2)))
    cx,cy=plan['chapel']['center']
    front,back,side,_=plan['chapel']['yard']
    reserve(box(x,y,(cx,cy),(10.55,6.4)))
    reserve(box(x,y,(cx-16.3,cy-2.85),(4.7,6.65)))
    reserve(np.hypot(x-(cx+front-9.),y-cy)-3.25)
    for gx,gy in ((-5.70,9.07),(-3.77,9.50),(-1.99,8.86)):
        reserve(np.hypot(x-(cx+1.25*gx),y-(cy+1.25*gy))-1.12)
    for center,half in [((43.,38.),(15.,6.)),((51.5,24.),(6.5,8.)),((52.5,-5.45),(3.4,6.24)),
            ((58.73,-6.05),(5.,5.)),((65.,5.),(3.3,4.8)),((-65.,0.),(3.3,5.5))]:
        reserve(box(x,y,center,half))
    # Ground laid by a shop or its repair state retains its own composition.
    for a,b,c,d,name,_ in contacts:
        if not any(k in name for k in ('TroughRunoff','Paved','Threshold','Doorstep','ApronWear','YardPathStone',
                                        'StoneApron','PackedFloor','DeckWest','MillEarthShoulder','Stable_HayCrib')):
            continue
        reserve(box(x,y,((a+c)/2,(b+d)/2),((c-a)/2,(d-b)/2)))
    road=np.full(x.shape,1000.)
    for points in lanes:
        for a,b in zip(points,points[1:]):
            dx,dy=b[0]-a[0],b[1]-a[1]
            t=np.clip(((x-a[0])*dx+(y-a[1])*dy)/max(1e-7,dx*dx+dy*dy),0,1)
            gap=np.hypot(x-a[0]-t*dx,y-a[1]-t*dy)-a[2]-t*(b[2]-a[2])
            np.minimum(road,gap,out=road)
    sx,sy,rx,ry=plan['square']
    reserve((np.hypot((x-sx)/rx,(y-sy)/ry)-1.)*min(rx,ry))
    # Keep the stable's two approach ruts continuous up to its gate.
    for walk,half in [([(59,5),(56.9,5.3),(55,6.3),(53.7,8.1),(52.7,10.7),(52.5,13.1),(52.5,16)],2.),
            ([(51.4,5.05),(49.3,6.3),(47.7,8.2),(46.5,10.8),(46.25,13.5),(46.25,16)],1.1)]:
        reserve(distance(x,y,walk)-half)
    return hard,road


def deposits(plan,lanes,wall,rng):
    groups=[]
    def pocket(kind,at,angle,length,width):
        groups.append((kind,*at,angle,length,width,rng.uniform(.78,.98)))
    for lane in lanes:
        line=np.array(lane)
        spans=np.diff(line[:,:2],axis=0)
        lens=np.linalg.norm(spans,axis=1)
        chain=np.r_[0,lens.cumsum()]
        for side in (-1,1):
            station=rng.uniform(1,6)
            while station<chain[-1]:
                seg=np.searchsorted(chain,station,side='right')-1
                t=(station-chain[seg])/lens[seg]
                a=line[seg]+t*(line[seg+1]-line[seg])
                tx,ty=spans[seg]/lens[seg]
                off=side*(a[2]+rng.uniform(.05,.95))
                pocket('road',(a[0]-ty*off,a[1]+tx*off),np.arctan2(ty,tx)+rng.uniform(-.55,.55),
                       rng.uniform(.60,2.40),rng.uniform(.30,.85))
                station+=rng.uniform(3.0,11.8)
    lengths=np.array([np.linalg.norm(np.subtract(b,a)) for a,b,_ in wall])
    for _ in range(round(lengths.sum()/3.7)):
        a,b,r=wall[rng.choice(len(wall),p=lengths/lengths.sum())]
        tangent=np.subtract(b,a);tangent=tangent/np.linalg.norm(tangent)
        at=np.array(a)+rng.random()*np.subtract(b,a)
        off=(r+rng.uniform(.08,1.25))*rng.choice([-1,1])
        at+=off*np.array([-tangent[1],tangent[0]])
        pocket('wall',at,np.arctan2(tangent[1],tangent[0])+rng.uniform(-.6,.6),
               rng.uniform(.52,2.2),rng.uniform(.30,.92))
    cx,cy=plan['chapel']['center']
    f,b,s,_=plan['chapel']['yard']
    for _ in range(100):
        at=cx+rng.uniform(f+1,b-1),cy+rng.uniform(-s+1,s-1)
        pocket('chapel',at,rng.uniform(-np.pi,np.pi),rng.uniform(.85,2.35),rng.uniform(.46,1.33))
    return groups


def bake(out,contacts,seed):
    folder=ROOT/'SourceAssets/TemperateHillsVillage'
    plan=json.loads((folder/'layout.json').read_text(encoding='utf8'))
    kit=json.loads((folder/'house-pieces.json').read_text(encoding='utf8'))
    lanes,wall=lines(plan,kit)
    hard,road=clearances(plan,kit,lanes,json.loads(contacts.read_text(encoding='utf8')))
    ex,ey=plan['surface_extent_m']
    w,h=PIXELS
    X=((np.arange(w)+.5)/w-.5)*(2*ex)
    Y=((np.arange(h)+.5)/h-.5)*(2*ey)
    dx,dy=2*ex/w,2*ey/h
    rng=np.random.default_rng(seed)
    def noise(metres):
        v=gaussian_filter(rng.standard_normal((h,w),dtype='f'),(metres/dy,metres/dx))
        return np.tanh(v/max(v.std(),1e-5))
    long=noise(.78)
    bend=noise(.38)
    mid=noise(.23)
    grain=noise(.085)
    cover=np.zeros((h,w),dtype='f')
    owner=np.zeros((h,w),'u1')
    cx,cy=plan['chapel']['center']
    front,back,side,_=plan['chapel']['yard']
    types=['chapel','road','wall']
    for kind,a,b,angle,length,width,opacity in deposits(plan,lanes,wall,rng):
        reach=max(length,width)*1.65+.7
        i,j=X.searchsorted([a-reach,a+reach]);k,l=Y.searchsorted([b-reach,b+reach])
        if i==j or k==l:continue
        cut=np.s_[k:l,i:j]
        x=X[None,i:j]-a+.29*long[cut]+.11*mid[cut]
        y=Y[k:l,None]-b+.22*bend[cut]-.08*grain[cut]
        cos,sin=np.cos(angle),np.sin(angle)
        u=(x*cos+y*sin)/length
        v=(y*cos-x*sin)/width
        # Break the flank into lobes, with small soil windows inside the fringe.
        rim=1.-np.hypot(u,v+.21*np.sin(3.2*u+.68*bend[cut]))
        rim+=.28*mid[cut]+.15*grain[cut]+.14*long[cut]
        patch=opacity*ramp((rim+.02)/.40)*ramp((mid[cut]+.52*grain[cut]+1.13)/.50)
        if kind=='chapel':
            gap=np.minimum(np.minimum(X[None,i:j]-cx-front,cx+back-X[None,i:j]),side-abs(Y[k:l,None]-cy))
            patch*=ramp((gap-.20-.12*mid[cut])/.54)
        replace=patch>cover[cut]
        owner[cut][replace]=types.index(kind)+1
        np.maximum(cover[cut],patch,out=cover[cut])
    coords=np.meshgrid((Y+ey)*4,(X+ex)*4,indexing='ij')
    hard=map_coordinates(hard,coords,order=1,mode='nearest')
    road=map_coordinates(road,coords,order=1,mode='nearest')
    border=np.minimum(np.minimum(ex-abs(X[None,:]),ey-abs(Y[:,None])),
                      (ex+ey-6-abs(X[None,:])-abs(Y[:,None]))/np.sqrt(2.))
    cover*=ramp((hard-.04-.15*(1+mid))/.35)*ramp((border-.40-.15*mid)/.62)
    cover*=ramp((road+.16+.18*bend+.09*grain)/.58)
    # One crop per connected patch. Extend crop coordinates through transparent
    # texels so bilinear filtering and distant mips cannot shear the outer leaves.
    weights=np.rint(cover*255).astype('u1')
    islands,n=label(weights>0,structure=np.ones((3,3)))
    nearest=distance_transform_edt(islands==0,return_distances=False,return_indices=True)
    crop=rng.integers(0,256,(n+1,3),dtype='u1')
    rgb=crop[islands[tuple(nearest)]]
    out.mkdir(parents=True,exist_ok=True)
    Image.fromarray(np.dstack((weights,rgb))).save(out/(MASK+'.png'))
    result=dict(seed=seed,grid_xy=[w,h],village_half_extent_m=[ex,ey],islands_with_visible_core=int(len(np.unique(islands[weights>=64]))),
                equivalent_cover_m2={key:round(float(cover[owner==i].sum()*dx*dy),1) for i,key in enumerate(types,1)},
                equivalent_cover_percent=round(100*float(cover.sum()*dx*dy)/(4*ex*ey-72),2))
    (out/'generation.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    print(json.dumps(result))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('output',type=Path);p.add_argument('contacts',type=Path)
    p.add_argument('--seed',type=int,default=DEFAULT_SEED)
    args=p.parse_args()
    bake(args.output,args.contacts,args.seed)
