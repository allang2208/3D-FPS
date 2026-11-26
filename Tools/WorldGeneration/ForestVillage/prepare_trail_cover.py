"""Synthesize the formal forest roadbed and meadow LOD from the measured study footprint."""
import json
import shutil
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter, gaussian_filter1d, label, map_coordinates
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra
from scipy.spatial import cKDTree
from skimage.morphology import skeletonize

from generate_reference_hill import smooth
from generate_slope_grass import grid_at
from continuous_meadow import bake as meadow

def measured_strip(ref, paint):
    # Follow the longest connected painted path. Both ends and lateral profiles come from the study.
    bones=skeletonize(paint>.46)
    ids,n=label(bones,np.ones((3,3)))
    y,x=np.where(ids==1+np.argmax(np.bincount(ids.ravel())[1:]))
    lookup={(j,i):k for k,(j,i) in enumerate(zip(y,x))}
    edges=[(k,lookup[(j+b,i+a)],np.hypot(a,b)) for k,(j,i) in enumerate(zip(y,x))
           for a,b in ((0,1),(1,-1),(1,0),(1,1)) if (j+b,i+a) in lookup]
    a,b,w=np.array(edges).T
    G=coo_matrix((w,(a.astype(int),b.astype(int))),shape=(len(y),len(y))).tocsr()
    start=dijkstra(G,directed=False,indices=0).argmax()
    dist,prev=dijkstra(G,directed=False,indices=start,return_predecessors=True)
    k=dist.argmax(); sequence=[k]
    while k!=start:
        k=prev[k];sequence.append(k)
    xy=gaussian_filter1d(np.column_stack((x[sequence],y[sequence])).astype(float)*2-252,1.8,axis=0,mode='nearest')
    station=np.r_[0,np.cumsum(np.hypot(*np.diff(xy,axis=0).T))]
    along=np.arange(0,station[-1],.5)
    center=np.array([np.interp(along,station,c) for c in xy.T]).T
    axis=np.gradient(center,axis=0)
    norm=np.stack([-axis[:,1],axis[:,0]],axis=1)/np.linalg.norm(axis,axis=1)[:,None]
    sx,sy=(center[:,None]+norm[:,None]*np.arange(-5,5.01,.5)[None,:,None]).transpose(2,0,1)
    heights=grid_at(ref,sx,sy,-252,-252)
    # Local affine grade removes the overall climb and crossfall, leaving crown, hollows and bumps.
    centerline=gaussian_filter1d(heights[:,10],17,mode='nearest')
    cross=gaussian_filter1d((heights[:,17]-heights[:,3])/7.,12,mode='nearest')
    residual=heights-centerline[:,None]-cross[:,None]*np.arange(-5,5.01,.5)
    return center,gaussian_filter(residual,(1.05,.75))

def roadbed(base,out):
    original=np.fromfile(base/'region.i16','<i2').reshape(1025,1025)
    paint=np.fromfile(base/'paint.rg8','u1').reshape(1025,1025,2)
    ref=np.fromfile(base/'reference.f32','<f4',count=505**2).reshape(505,505)
    donor=np.fromfile(base/'Grass/study_dirt_2m.u8','u1').reshape(253,253)/255.
    center,strip=measured_strip(ref,donor)
    np.savez_compressed(out/'measured-road.npz',center_m=center,relief_cm=strip)
    # Signed millimetres about 32768, 0.5 m between samples along and across the road.
    Image.fromarray(np.rint(32768+10*strip).clip(0,65535).astype('uint16')).save(out/'H_StudyRoadResidual.png')
    extent=np.percentile(abs(strip[:,5:16]),90)
    # The clipping is a soft limit in centimetres, not a change to the overall road gradient.
    detail=24*np.tanh((strip-np.median(strip[:,5:16]))*(15/max(2,extent))/24.)
    y,x=np.mgrid[-320:705,-624:401]
    sites=np.c_[x.ravel(),y.ravel()]
    quarry=np.fromfile(base/'quarry-clear.u8','u1').reshape(x.shape)/255.
    shore=np.fromfile(base/'Grass/pond_shore.u8','u1').reshape(x.shape)/255.
    h=json.loads((base/'hill.json').read_text())
    vx,vy=h['site_min_m']
    town=np.hypot(np.maximum.reduce((vx-x,x-vx-118,np.zeros_like(x))),np.maximum.reduce((vy-y,y-vy-145,np.zeros_like(y))))
    refedge=np.hypot(np.maximum(abs(x)-252,0),np.maximum(abs(y)-252,0))
    total=np.zeros_like(x,dtype=float);weight=np.zeros_like(total)
    for name,seed in [('gate-road',3491),('quarry-road',2077)]:
        road=np.loadtxt(base/(name+'.csv'),delimiter=',',skiprows=1)[:,:2]
        sta=np.r_[0,np.cumsum(np.hypot(*np.diff(road,axis=0).T))]
        dist,idx=cKDTree(road).query(sites)
        d=dist.reshape(x.shape);i=idx.reshape(x.shape);u=sta[i]
        tangent=np.gradient(road,axis=0)
        tangent/=np.maximum(np.linalg.norm(tangent,axis=1)[:,None],1.e-6)
        v=-(x-road[i,0])*tangent[i,1]+(y-road[i,1])*tangent[i,0]
        rng=np.random.default_rng(seed)
        # Overlap irregular lengths of the measured strip. No periodic repetitions at segment boundaries.
        accum=np.zeros_like(total);count=accum.copy()
        at=-10.
        while at<sta[-1]+25:
            length=rng.uniform(18,34);rate=rng.uniform(.8,1.18)*rng.choice([-1,1])
            origin=rng.uniform(75,len(strip)-75); flip=rng.choice([-1,1])
            hit=(abs(u-at)<length)&(d<5.5)
            t=(u[hit]-at)/length
            f=(1-t*t)**2
            data=map_coordinates(detail,[origin+2*(u[hit]-at)*rate,10+2*v[hit]*flip],order=1,mode='nearest')
            accum[hit]+=f*data;count[hit]+=f
            at+=length*.70
        w=(1-smooth(2.4,5.4,d))*smooth(0,5,np.minimum(u,sta[-1]-u))
        total+=accum/np.maximum(count,.0001)*w
        weight+=w
    fade=smooth(0,6,refedge)*smooth(.5,5,town)*(1-quarry)*(1-shore)
    delta=np.rint(total/np.maximum(1,weight)*fade).astype('i2')
    new=original+delta
    new.astype('<i2').tofile(out/'region.i16')
    for key in ('paint.rg8','reference.f32'):
        shutil.copy2(base/key,out/key)
    tiles=[f'SM_ForestGround_{i:02d}_{j:02d}' for j in range(8) for i in range(8)
           if delta[max(0,128*j-1):128*j+130,max(0,128*i-1):128*i+130].any()]
    count=meadow(base,out,new,paint)
    report=dict(reference_length_m=len(strip)*.5,reference_abs_p90_cm=float(extent),changed_vertices=int(np.count_nonzero(delta)),
                min_cm=int(delta.min()),max_cm=int(delta.max()),tiles=tiles,grass_patches=count)
    (out/'generation.json').write_text(json.dumps(report,indent=2))
    print(report)

if __name__=='__main__':
    if sys.argv[1]=='--meadow':
        base,terrain,out=map(Path,sys.argv[2:])
        heights=np.fromfile(terrain/'region.i16','<i2').reshape(1025,1025)
        paint=np.fromfile(terrain/'paint.rg8','u1').reshape(1025,1025,2)
        print('Meadow patches:',meadow(base,out,heights,paint))
    else:
        base,out=map(Path,sys.argv[1:])
        roadbed(base,out)



