"""Build a nonperiodic hill from the measured woody slope, then site the village and reconnect its gate.
Run with the HillsForestPath source root and the new batch source directory.
"""
import heapq
import json
from pathlib import Path
import shutil
import sys

import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt, gaussian_filter, gaussian_filter1d, map_coordinates, maximum_filter
from scipy.spatial import cKDTree

import generate_slope_grass as grass
from generate_village_relief import generate as village_relief

WEST, SOUTH = -624, -320
SIDE = 1025
SEED = 473219


def smooth(a,b,v):
    u=np.clip((v-a)/(b-a),0,1)
    return u*u*(3-2*u)


def sample(a,x,y,left=WEST,bottom=SOUTH):
    return map_coordinates(a.astype(float,copy=False),[y-bottom,x-left],order=1,mode='nearest',prefilter=False)


def height_png(path,z):
    Image.fromarray(np.rint(32768+100*z).astype('uint16')).save(path)


def hill_profile(patch):
    # Sample the actual uphill profile perpendicular to the broad contour lines.
    broad=gaussian_filter(patch,5)
    gy,gx=np.gradient(broad)
    iy,ix=np.indices(broad.shape)
    along=ix*gx.mean()+iy*gy.mean()
    along=(along-along.min())/np.ptp(along)
    knots=np.linspace(.03,.97,19)
    levels=np.array([np.median(broad[np.abs(along-k)<.035]) for k in knots])
    levels=gaussian_filter1d(np.maximum.accumulate(levels),1)
    return (levels-levels[0])/(levels[-1]-levels[0])


def terrain_detail(patch,x,y):
    # Overlap irregularly oriented pieces of the measured bedding. The sample
    # interval stays metric and no edge of the reference is wrapped or tiled.
    rng=np.random.default_rng(SEED)
    result=np.zeros(x.shape); weights=np.zeros(x.shape)
    spacing=26
    for cy in range(int(y.min())-spacing,int(y.max())+spacing,spacing):
        for cx in range(int(x.min())-spacing,int(x.max())+spacing,spacing):
            ax,ay=rng.uniform(-5,5,2)
            dx,dy=x-cx-ax,y-cy-ay
            reach=29.
            use=(np.abs(dx)<reach)&(np.abs(dy)<reach)
            if not use.any(): continue
            angle=rng.uniform(-np.pi,np.pi)
            scale=rng.uniform(.80,.98)
            c,s=np.cos(angle)*scale,np.sin(angle)*scale
            sx=49+rng.uniform(-17,17)+dx[use]*c-dy[use]*s
            sy=61+rng.uniform(-28,28)+dx[use]*s+dy[use]*c
            w=(1-smooth(0,reach,np.abs(dx[use])))*(1-smooth(0,reach,np.abs(dy[use])))
            result[use]+=w*sample(patch,sx,sy,0,0)
            weights[use]+=w
    merged=result/weights
    # Feathering several signed patches suppresses their amplitude. Restore the
    # measured interdecile span (metres) about zero in each spatial band.
    span=np.diff(np.percentile(patch,[10,90]))[0]
    merged_span=np.diff(np.percentile(merged,[10,90]))[0]
    return (merged-np.median(merged))*span/max(.001,merged_span)


def wet_distance(pool):
    # Include any wet quarter-metre cell around a terrain node.
    wet=maximum_filter(pool,size=5)[::4,::4]>0
    return distance_transform_edt(~wet)


def sculpt(original,forest,pools):
    y,x=np.mgrid[252:602,-385:87]
    roi=np.s_[252-SOUTH:602-SOUTH,-385-WEST:87-WEST]
    old=original[roi]
    # Same reference footprint as R11, including its long-wave profile.
    patch=np.s_[189:312,63:162]
    source=forest[patch]
    profile=hill_profile(source)
    regional=gaussian_filter(forest,12)
    fine=(gaussian_filter(forest,.65)-gaussian_filter(forest,3.2))[patch]
    shoulder=(gaussian_filter(forest,3.2)-regional)[patch]
    micro=terrain_detail(fine,x,y)
    middle=terrain_detail(shoulder,x*.78,y*.78)
    def lobe(cx,cy,major,minor,angle):
        dx,dy=x-cx,y-cy
        c,s=np.cos(angle),np.sin(angle)
        u=(c*dx+s*dy)/major
        v=(-s*dx+c*dy)/minor
        return np.maximum(0.,1-np.sqrt(u*u+v*v))
    spine=lobe(-169,396,170,124,1.06)
    west=lobe(-208,371,127,77,.38)*.68
    northeast=lobe(-121,443,113,68,.90)*.77
    toe=lobe(-131,322,99,55,-.97)*.52
    # Smooth union gives a saddle and two shoulders at different elevations.
    stack=np.stack((spine,west,northeast,toe))
    mass=(stack**5).sum(axis=0)**.2
    summit=np.interp(np.clip(mass/np.max(mass),0,1),np.linspace(0,1,len(profile)),profile)
    # The reference's long profile controls the shoulder; rounding at the crest
    # retains the skyline while avoiding a cusp at the spine control point.
    summit=gaussian_filter(.55*smooth(0,1,mass/mass.max())+.45*summit,4.5)
    crest=71.*summit/summit.max()
    flanks=smooth(.035,.25,mass)*(1-smooth(.72,.98,mass))
    gully_a=x-(-239+.41*(y-327)+8*np.sin((y-304)/31))
    gully_b=x-(-107-.22*(y-370)+11*np.sin((y-306)/45))
    gullies=flanks*(5.4*np.exp(-(gully_a/13)**2)+4.1*np.exp(-(gully_b/11)**2))
    broad=sample(regional[patch],(x+385)*98/471,(y-252)*122/349,0,0)
    base=-5.7+.19*(broad-np.median(source))+crest-gullies
    base+=middle*(1.15+.35*flanks)+micro*(1.35+.40*flanks)
    fringe=(smooth(-383,-342,x)*(1-smooth(15,83,x))*(1-smooth(555,600,y)))
    influence=fringe*smooth(8,40,pools[roi])
    # Carry the measured elevation and derivative of the original forest for
    # the first metres; replace the former six-metre drop and rectangular pad.
    dy=y-252
    border=original[252-SOUTH,x-WEST]
    tangent=np.clip((border-original[249-SOUTH,x-WEST])/3.,-.60,.60)
    incoming=border+tangent*dy*np.exp(-dy/11.)
    base=incoming+(base-incoming)*smooth(0,46,dy)
    result=original.copy()
    result[roi]=old+(base-old)*influence
    mask=np.zeros_like(original)
    mask[roi]=influence
    structure=np.zeros_like(original)
    structure[roi]=micro+middle
    return result,mask,structure,profile


def choose_site(h,pools):
    # Score entire sites after the terrain is complete, including their natural
    # crossfall and the distance from the existing forest road. Keep ponds clear.
    best=None
    for cy in range(328,499,4):
        for cx in range(-20,142,4):
            x0,y0=cx-59,cy-71
            view=np.s_[y0-SOUTH:y0-SOUTH+146,x0-WEST:x0-WEST+119]
            if pools[view].min()<14: continue
            plot=h[view][7:-7:3,8:-8:3]
            datum=np.median(plot)
            cuts=np.abs(plot-datum)
            gate_distance=np.hypot(cx+5+108,cy-65-252)
            score=np.percentile(cuts,90)+.42*cuts.mean()+.011*gate_distance+.15*abs(datum-h[y0-SOUTH,cx+5-WEST])
            if best is None or score<best[0]:
                best=(score,cx,cy,float(datum))
    if best is None: raise ValueError('No dry foothill site fits the actual village footprint')
    return best[1:]


def woodland_lane(h,pools,cx,cy):
    # Endpoint directions follow the forest track and the gateway arch.
    start=(-108,259); end=(cx+5,cy-81)
    bounds=(-169,min(245,end[1]-8),max(cx+50,64),max(cy-70,300))
    left,bottom,right,top=bounds
    yy,xx=np.mgrid[bottom:top+1:2,left:right+1:2]
    z=sample(h,xx,yy); wet=sample(pools,xx,yy)
    def node(p):
        return int(round((p[1]-bottom)/2)),int(round((p[0]-left)/2))
    origin,goal=node(start),node(end)
    frontier=[(0.,0.,origin)]
    dist={origin:0.}; prev={}
    while frontier:
        _,cost,pos=heapq.heappop(frontier)
        if cost>dist[pos]: continue
        if pos==goal: break
        j,i=pos
        for dj,di in ((0,1),(1,0),(-1,0),(0,-1),(1,1),(-1,1),(1,-1),(-1,-1)):
            k,l=j+dj,i+di
            if not (0<=k<z.shape[0] and 0<=l<z.shape[1]) or yy[k,l]<258 or wet[k,l]<9:continue
            length=2*np.hypot(di,dj)
            grade=abs(z[k,l]-z[j,i])/length
            step=length*(1+14*grade**2+3*max(0.,grade-.16)+.5*(1-smooth(9,18,wet[k,l])))
            alt=cost+step
            if alt<dist.get((k,l),np.inf):
                dist[(k,l)]=alt;prev[(k,l)]=pos
                heapq.heappush(frontier,(alt+2*np.hypot(k-goal[0],l-goal[1]),alt,(k,l)))
    if goal not in dist: raise ValueError('No continuous dry grade to the gate')
    nodes=[goal]
    while nodes[-1]!=origin: nodes.append(prev[nodes[-1]])
    line=np.array([(-108.,252.),*[(xx[j,i],yy[j,i]) for j,i in reversed(nodes)],(cx+5.,cy-71.),(cx+5.,cy-65.)])
    along=np.r_[0,np.cumsum(np.hypot(*np.diff(line,axis=0).T))]
    stations=np.arange(0,along[-1],.5)
    stations=np.r_[stations,along[-1]]
    xy=np.stack([np.interp(stations,along,line[:,i]) for i in range(2)],axis=1)
    xy=gaussian_filter1d(xy,5,axis=0,mode='nearest')
    xy[stations<4]=np.c_[np.full((stations<4).sum(),-108.),252+stations[stations<4]]
    xy[-1]=line[-1]
    return xy,stations


def generate(base,out, *, trail_variant=False):
    out.mkdir(parents=True,exist_ok=True)
    r11=base/'VillageGroundRelief-R11';r3=base/'ForestVillage-SurfaceGrass-R3';r9=base/'HillsWoodlandPools-R9'
    ref=np.fromfile(r11/'reference.f32','<f4').astype(float)/100
    forest=ref[:505**2].reshape(505,505)
    old_platform=ref[505**2:].reshape(146,119)
    old=np.fromfile(r3/'region.i16','<i2').reshape(SIDE,SIDE).astype(float)/100
    paint=np.fromfile(r3/'paint.rg8','u1').reshape(SIDE,SIDE,2).astype(float)/255
    pool=np.memmap(r9/'pond_wet.u8',mode='r',dtype='u1',shape=(4097,4097))
    pools=wet_distance(pool)
    h,mask,detail,profile=sculpt(old,forest,pools)
    summit_area=h[255-SOUTH:561-SOUTH,-319-WEST:-58-WEST]
    pj,pi=np.unravel_index(np.argmax(summit_area),summit_area.shape)
    peak=[int(pi-319),int(pj+255)]
    pre_site=h.copy()
    cx,cy,datum=choose_site(h,pools)
    minx,miny=cx-59,cy-71
    view=np.s_[miny-SOUTH:miny-SOUTH+146,minx-WEST:minx-WEST+119]
    y,x=np.mgrid[SOUTH:SOUTH+SIDE,WEST:WEST+SIDE]
    # Only the settling earth around the structures adopts the building datum.
    # Surrounding slopes rise continuously into the land behind the town.
    dx=np.maximum.reduce([minx-x,x-(minx+118),np.zeros_like(x)])
    dy=np.maximum.reduce([miny-y,y-(miny+145),np.zeros_like(y)])
    proximity=np.hypot(dx,dy)
    approach=(1-smooth(0,18,proximity))*smooth(5,14,pools)
    adjusted=h+(datum-h)*approach
    native=old_platform-old_platform[6,64]
    native[:6]=native[6]
    clearance,public=village_relief(r11,site_weights=True)
    signed=h[view]-datum
    # Limit building-adjacent earthwork slopes while retaining connected swells
    # in open land. Small road grade carries the lane through the gate.
    offset=clearance*((1-public)*.09*np.tanh(signed)+public*2.4*np.tanh(signed/2.4))
    rim=np.minimum.reduce([x[view]-minx,minx+118-x[view],y[view]-miny,miny+145-y[view]])
    offset*=smooth(0,6,rim)
    # Exterior and interior share a continuous collar without editing any courtyard.
    interior=datum+native+offset
    adjusted[view]=interior
    xy,st=woodland_lane(adjusted,pools,cx,cy)
    if trail_variant:
        from trail_variation import gate_curve, stations
        xy=gate_curve(xy,st)
        st=stations(xy)
    tree=cKDTree(xy)
    dist=np.full(h.shape,1e5); at=np.zeros(h.shape,dtype=int)
    near=(x>xy[:,0].min()-11)&(x<xy[:,0].max()+11)&(y>=252)&(y<xy[:,1].max()+11)
    dist[near],at[near]=tree.query(np.c_[x[near],y[near]])
    bed=gaussian_filter1d(sample(adjusted,*xy.T),9,mode='nearest')
    bed+= (bed[0]*-1+old[252-SOUTH,-108-WEST])*(1-smooth(0,12,st))
    bed+=(datum-bed[-1])*smooth(st[-1]-12,st[-1],st)
    in_village=(dx==0)&(dy==0)
    roadwork=(1-smooth(1.7,6.6,dist))*smooth(252,257,y)*~in_village
    h=adjusted+(bed[at]-adjusted)*roadwork
    if trail_variant:
        # The current village and authored hydrology stay in their existing source packages.
        np.rint(100*h).astype('<i2').tofile(out/'region.i16')
        np.savetxt(out/'gate-road.csv',np.c_[xy,bed],delimiter=',',header='x_m,y_m,z_m',comments='',fmt='%.3f')
        info=json.loads((base/'ReferenceHill-R12/hill.json').read_text())
        info['lane_length_m']=round(float(st[-1]),1)
        (out/'hill.json').write_text(json.dumps(info,indent=2))
        return
    grade=np.hypot(*np.gradient(h))
    grove=np.clip(.52+.19*np.tanh(detail)+.13*np.cos(x*.029+y*.011)-.22*smooth(.4,.85,grade),.10,.90)
    natural_soil=.06+.22*smooth(.35,.82,grade)+.08*(1-grove)
    natural_moss=.10+.68*grove+.10*(1-smooth(-1,.45,detail))
    # Use the original north Landscape boundary paint along the first metres.
    dirt=np.fromfile(r9/'study_dirt_2m.u8','u1').reshape(253,253)/255.
    edge=1-smooth(252,262,y)
    carried=np.interp(x[0],np.arange(-252,253,2),dirt[-1])
    natural_soil=natural_soil*(1-edge)+carried*edge
    natural_moss=natural_moss*(1-edge)+edge
    weights=mask.copy();weights[y<252]=0
    paint[...,0]+=(natural_soil-paint[...,0])*weights
    paint[...,1]+=(natural_moss-paint[...,1])*weights
    road=(1-smooth(1.45,3.35+.14*np.sin(st[at]*.075),dist))*smooth(252,256,y)
    paint[...,0]=np.maximum(paint[...,0],road)
    # Full scan settings for the hill; join to the earlier R3 sample and its materials.
    blend=np.maximum(np.fromfile(r3/'sample.r8','u1').reshape(SIDE,SIDE)/255.,np.maximum(weights,road))
    # Do not flag an original-Landscape-only source tile at the shared lower boundary.
    blend[y<252]=0
    np.rint(100*h).astype('<i2').tofile(out/'region.i16')
    np.rint(100*offset).astype('<i2').tofile(out/'settlement.i16')
    np.rint(255*np.clip(paint,0,1)).astype('u1').tofile(out/'paint.rg8')
    np.rint(255*blend).astype('u1').tofile(out/'sample.r8')
    np.rint(255*paint[view][:9]).astype('u1').tofile(out/'apron.rg8')
    height_png(out/'H_ReferenceHill_1m.png',h)
    height_png(out/'H_HillBeforeSettlement.png',pre_site[252-SOUTH:602-SOUTH,-385-WEST:87-WEST])
    rows=grass.POINT
    points=np.fromfile(r3/'planting.bin',rows)
    px,py=points['x']*.01,points['y']*.01
    corridor=sample(road,px,py)>.10
    onsite=(px>minx-2)&(px<minx+120)&(py>miny-2)&(py<miny+147)
    prev_apron=(px>=-172)&(px<=-54)&(py>=252)&(py<=258)&(points['slot']>=12)
    keep=~(onsite|corridor|prev_apron)&((sample(grade,px,py)<.85)|(sample(mask,px,py)<.01))
    # Reforest the former village and its formerly bare collar from the same project palette.
    rng=np.random.default_rng(SEED)
    fills=[]
    for spacing,slots,chance,lo,hi in [(5.8,[0,1],.75,.80,1.12),(8.5,[2,3],.41,140,275),
            (11,[4,5],.12,18,47),(12,[6,7],.10,42,91),(4.5,[8,9],.27,.60,.98),(27,[10,11],.10,.5,.96)]:
        fy,fx=np.mgrid[252+spacing/2:416:spacing,-193+spacing/2:-32:spacing]
        fx=fx.ravel()+rng.uniform(-.38,.38,fx.size)*spacing
        fy=fy.ravel()+rng.uniform(-.38,.38,fy.size)*spacing
        gap=np.hypot(np.maximum.reduce([-172-fx,fx+54,np.zeros_like(fx)]),np.maximum.reduce([252-fy,fy-397,np.zeros_like(fy)]))
        accept=(rng.random(fx.size)<chance*(1-smooth(0,16,gap)))&(fy>253)&(sample(grade,fx,fy)<.75)&(sample(paint[...,0],fx,fy)<.48)&(sample(pools,fx,fy)>5)
        fx,fy=fx[accept],fy[accept]
        group=np.empty(len(fx),rows)
        group['x'],group['y']=100*fx,100*fy
        group['yaw']=rng.uniform(0,360,len(fx));group['size']=rng.uniform(lo,hi,len(fx));group['slot']=rng.choice(slots,len(fx))
        fills.append(group)
    np.concatenate([points[keep],*fills]).tofile(out/'planting.bin')
    delta_cm=np.rint((h-old)*100)
    info=dict(site_min_m=[int(minx),int(miny)],village_center_m=[int(cx),int(cy)],village_datum_cm=float(datum*100),
              original_village_center_m=[-113,323],summit_xy_m=peak,summit_elevation_m=float(np.round(h[peak[1]-SOUTH,peak[0]-WEST],2)),
              trailhead_elevation_m=float(old[252-SOUTH,-108-WEST]),village_displacement_m=round(float(np.hypot(cx+113,cy-323)),1),
              summit_above_old_village_m=round(float(h[peak[1]-SOUTH,peak[0]-WEST]-old_platform[6,64]),2),
              lane_length_m=round(float(st[-1]),1),source_slope_world_m=[[-189,-63],[-91,59]],source_grid=[99,123],
              reference_profile=profile.round(4).tolist(),source_interval_m=1,seed=SEED,
              former_site_elevation_range_m=np.round([h[572:718,452:571].min(),h[572:718,452:571].max()],2).tolist(),
              changed_area_m2=int(np.count_nonzero(abs(delta_cm)>.5)),local_relief_p10_p90_m=np.percentile(detail[mask>.85],[10,90]).round(2).tolist())
    (out/'hill.json').write_text(json.dumps(info,indent=2),encoding='utf8')
    np.savetxt(out/'gate-road.csv',np.c_[xy,bed],delimiter=',',header='x_m,y_m,z_m',comments='',fmt='%.3f')
    print(json.dumps(info,indent=2),flush=True)
    cover=out/'Grass'
    cover.mkdir(exist_ok=True)
    for name in ('pond_wet.u8','study_dirt_2m.u8','study_obstacles.f32','study_trees.f32'):
        shutil.copy2(r9/name,cover/name)
    grass.generate(out,cover,base/'WildGrass-oilox20')


if __name__=='__main__':
    generate(Path(sys.argv[1]),Path(sys.argv[2]))
