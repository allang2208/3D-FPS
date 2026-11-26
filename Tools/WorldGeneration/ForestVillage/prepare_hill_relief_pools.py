"""Refit the formal hill to measured forest relief and prepare eligibility for its closed pools."""
import json
import shutil
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import gaussian_filter, distance_transform_edt, maximum_filter, map_coordinates
from scipy.spatial import cKDTree

from generate_reference_hill import smooth
from generate_slope_grass import POINT
from generate_village_relief import generate as village_weights

WEST,SOUTH=-624,-320
SEED=473219

def write_pool_eligibility(out,cm,refroad,dtown,droad,dquarry):
    grass=out/"Grass"
    # Hydrology must use the actual current grade and both maintained road alignments.
    paint=np.fromfile(out/'paint.rg8','u1').reshape(1025,1025,2)[...,0]/255.
    paint[68:573,372:877]=refroad
    grade=np.hypot(*np.gradient(cm.astype(float)*.01))
    allowed=(maximum_filter(paint,7)<.25)&(grade<.45)&(dtown>5.)&(droad>5.)&(dquarry>3.)
    blocked=Image.new('L',(1025,1025),0);brush=ImageDraw.Draw(blocked)
    def exclude(points,buffer):
        for px,py,r in points:
            px,py,r=float(px)-WEST,float(py)-SOUTH,float(r)+buffer
            brush.ellipse((round(px-r),round(py-r),round(px+r),round(py+r)),fill=1)
    for key in ('study_trees','study_obstacles','study_pond_props'):
        exclude(np.fromfile(grass/(key+'.f32'),'<f4').reshape(-1,3),.65)
    trees=np.fromfile(grass/'harvest-trees.f32','<f4').reshape(-1,3)
    exclude(np.column_stack((trees[:,:2]*.01,np.full(len(trees),.60))),.65)
    (allowed&(np.asarray(blocked)==0)).astype('u1').tofile(grass/'pond_allowed.u8')

def scale_length(band):
    # Distance at which the mean covariance on both sample axes drops below half its initial value.
    centered=band-band.mean()
    reference=max(float(np.mean(centered**2)),1.e-8)
    for distance in range(1,33):
        cov=(np.mean(centered[:,distance:]*centered[:,:-distance])+np.mean(centered[distance:]*centered[:-distance]))*.5
        if cov<reference*.5:return distance
    return 32

def reference_relief(forest,road,height,out):
    # Remove metre-scale DEM steps. Shoulder and short relief share the same source position and rotation.
    low=gaussian_filter(forest,14.)
    mid=gaussian_filter(forest,4.)-low
    fine=gaussian_filter(forest,1.15)-gaussian_filter(forest,4.)
    reach=np.s_[189:312,63:162]
    for name,band in (('Short',fine),('Shoulder',mid)):
        Image.fromarray(np.rint(32768+100*band[reach]).astype('uint16')).save(out/('H_Reference'+name+'.png'))
    lens=[scale_length(band[reach]) for band in (fine,mid)]
    radius=float(np.clip(2.8*lens[1]+2*lens[0],30.,45.))
    outside=distance_transform_edt(road<.30)
    margin=int(np.ceil(radius*1.18))+4
    ys,xs=np.mgrid[margin:505-margin:3,margin:505-margin:3]
    valid=outside[ys,xs]>12.
    xs,ys=xs[valid],ys[valid]
    gy,gx=np.gradient(low); grades=np.hypot(gy[ys,xs],gx[ys,xs])
    # Retain the approved road-free slope as the steep donor; use road-free glades for flat terrain.
    slope=(xs>=65)&(xs<160)&(ys>=191)&(ys<310)
    moderate=(grades>.055)&(~slope)
    flat=grades<=.075
    pools=[np.flatnonzero(flat),np.flatnonzero(moderate),np.flatnonzero(slope)]
    if any(not len(p) for p in pools):raise ValueError('Missing forest reference landform')
    macro=gaussian_filter(height,13.);ty,tx=np.gradient(macro)
    rng=np.random.default_rng(SEED+28)
    # The hash bins only accelerate the minimum-separation search. They do not place a lattice on the DEM.
    separation=radius*.55
    occupied={};centres=[]
    for cx,cy in rng.uniform(-radius,1024+radius,(24000,2)):
        key=(int(np.floor(cx/separation)),int(np.floor(cy/separation)))
        if any((cx-px)**2+(cy-py)**2<separation**2 for i in (-1,0,1) for j in (-1,0,1)
               for px,py in occupied.get((key[0]+i,key[1]+j),())):continue
        occupied.setdefault(key,[]).append((cx,cy));centres.append((cx,cy))
    bands=np.zeros((2,1025,1025),dtype='f8');weight=np.zeros_like(height,dtype='f8')
    for cx,cy in centres:
        i,j=np.clip(np.rint([cx,cy]),0,1024).astype(int)
        slope_here=np.hypot(tx[j,i],ty[j,i])
        # Probabilistic transition between donor habitats avoids contours at class boundaries.
        selector=rng.random()
        pool=pools[2] if selector<smooth(.12,.31,slope_here) else pools[1] if rng.random()<smooth(.025,.13,slope_here) else pools[0]
        k=rng.choice(pool);dx,dy=xs[k],ys[k]
        a=np.arctan2(gy[dy,dx],gx[dy,dx])-np.arctan2(ty[j,i],tx[j,i])+rng.uniform(-.4,.4)
        c,sa=np.cos(a),np.sin(a)
        rad=radius*rng.uniform(.88,1.13)
        x0,x1=max(0,int(cx-rad)),min(1025,int(cx+rad)+1)
        y0,y1=max(0,int(cy-rad)),min(1025,int(cy+rad)+1)
        if x0>=x1 or y0>=y1:continue
        y,x=np.mgrid[y0:y1,x0:x1];u=x-cx;v=y-cy
        dist=(u*u+v*v)/(rad*rad);w=np.maximum(0.,1.-dist)**3
        scale=rng.uniform(.88,1.03)
        coord=[dy+scale*(sa*u+c*v),dx+scale*(c*u-sa*v)]
        w*=smooth(2.,9.,map_coordinates(outside,coord,order=1,mode='nearest'))
        for n,band in enumerate((fine,mid)):
            bands[n,y0:y1,x0:x1]+=w*map_coordinates(band,coord,order=1,mode='nearest')
        weight[y0:y1,x0:x1]+=w
    bands/=np.maximum(weight,.0001)[None]
    slope_strength=smooth(.035,.23,np.hypot(tx,ty))
    # Use robust empirical spans; extreme hollows in the donor must not be amplified by a global gain.
    stats={'seed':SEED+28,'reference_xy_m':[[-189,-63],[-91,59]],'half_correlation_m':lens,'blend_radius_m':radius}
    for n,(name,source) in enumerate(zip(('short','shoulder'),(fine,mid))):
        lo,hi=np.percentile(source[reach],[10,90])
        stats[name+'_reference_p10_p90_m']=[float(lo),float(hi)]
        span=np.diff(np.percentile(bands[n][slope_strength>.6],[10,90]))[0]
        gain=np.clip((hi-lo)/max(.02,span),.65,1.65)
        bands[n]*=gain*(.43+.47*slope_strength)
    # Peripheral terrain has 2 m knots: suppress only detail too narrow for its triangles.
    y,x=np.mgrid[SOUTH:SOUTH+1025,WEST:WEST+1025]
    coarse=smooth(0.,8.,np.maximum.reduce([np.abs(x)-252.,-252.-y,y-612.,np.zeros_like(x)]))
    bands[0]=(1-coarse)*bands[0]+coarse*gaussian_filter(bands[0],1.45)
    return macro,bands,stats

def terrain(root,out):
    original=root/'TrailCover-R21';flora=root/'VillageFlora-R20';grass=out/'Grass'
    grass.mkdir(exist_ok=True,parents=True)
    for key in ('reference.f32','paint.rg8'):shutil.copy2(original/key,out/key)
    for key in ('hill.json','gate-road.csv','quarry-road.csv','quarry-clear.u8'):shutil.copy2(flora/key,out/key)
    for key in ('reference-meshes.txt','harvest-trees.f32','study-granite.i32','study_dirt_2m.u8',
                'study_trees.f32','study_obstacles.f32','study_pond_props.f32'):shutil.copy2(flora/'Grass'/key,grass/key)
    forest=np.fromfile(out/'reference.f32','<f4',count=505**2).reshape(505,505).astype('f8')*.01
    old=np.fromfile(original/'region.i16','<i2').reshape(1025,1025)*.01
    dirt=np.fromfile(grass/'study_dirt_2m.u8','u1').reshape(253,253)/255.
    i,j=np.indices(forest.shape)
    refroad=map_coordinates(dirt,[i*.5,j*.5],order=1,mode='nearest')
    macro,bands,stats=reference_relief(forest,refroad,old,out)
    y,x=np.mgrid[SOUTH:SOUTH+1025,WEST:WEST+1025]
    hill=json.loads((out/'hill.json').read_text());vx,vy=hill['site_min_m']
    sx,sy=hill['summit_xy_m']
    # Restore the authored summit datum over a broad area without retaining its old small folds.
    macro+=(old[sy-SOUTH,sx-WEST]-macro[sy-SOUTH,sx-WEST])*np.exp(-((x-sx)**2+(y-sy)**2)/(2.*38**2))
    dref=np.hypot(np.maximum(np.abs(x)-252.,0),np.maximum(np.abs(y)-252.,0))
    dtown=np.hypot(np.maximum.reduce([vx-x,x-vx-118,np.zeros_like(x)]),np.maximum.reduce([vy-y,y-vy-145,np.zeros_like(y)]))
    quarry=np.fromfile(out/'quarry-clear.u8','u1').reshape(x.shape)
    dquarry=distance_transform_edt(quarry<12)
    roads=np.vstack([np.loadtxt(out/(key+'-road.csv'),delimiter=',',skiprows=1)[:,:2] for key in ('gate','quarry')])
    droad=cKDTree(roads).query(np.column_stack((x.ravel(),y.ravel())))[0].reshape(x.shape)
    fade=smooth(1.,19.,dref)*smooth(2.,18.,dtown)*smooth(.5,17.,dquarry)*smooth(5.,17.,droad)
    raw=macro+bands[0]+bands[1]-old
    delta=np.rint(100.*fade*(6.*np.tanh(raw/6.))).astype('<i2')
    cm=np.rint(old*100.).astype('<i2')+delta;cm.tofile(out/'region.i16')
    Image.fromarray((cm.astype(np.int32)+32768).astype('uint16')).save(out/'H_Region_R28.png')
    # Junior-scale version of the same measured relief only on open village ground.
    setback,open_ground=village_weights(root/'VillageGroundRelief-R11',site_weights=True)
    off=np.fromfile(flora/'Turf/settlement.i16','<i2').reshape(146,119).astype(float)
    source=np.s_[vy-SOUTH:vy-SOUTH+146,vx-WEST:vx-WEST+119]
    oy,ox=np.indices(off.shape);rim=np.minimum.reduce([ox,118-ox,oy,145-oy])
    local=100*(.26*bands[0][source]+.13*bands[1][source])
    target=gaussian_filter(off,5.)+local
    adjust=np.rint(setback*open_ground*smooth(2.,8.,rim)*18.*np.tanh((target-off)/18.))
    (off+adjust).astype('<i2').tofile(out/'settlement.i16')
    write_pool_eligibility(out,cm,refroad,dtown,droad,dquarry)
    stats.update(changed_region_knots=int(np.count_nonzero(delta)),changed_village_knots=int(np.count_nonzero(adjust)),
                 delta_cm=[int(delta.min()),int(delta.max())])
    peak=np.unravel_index(np.argmax(cm),cm.shape)
    hill.update(summit_xy_m=[int(peak[1]+WEST),int(peak[0]+SOUTH)],summit_elevation_m=float(cm[peak])*.01,
                relief_recipe='HillReliefPools-R28',changed_area_m2=stats['changed_region_knots'])
    (out/'hill.json').write_text(json.dumps(hill,indent=2))
    (out/'relief.json').write_text(json.dumps(stats,indent=2))

if __name__=='__main__':terrain(Path(sys.argv[1]),Path(sys.argv[2]))
