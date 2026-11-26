"""Continue the measured road layers and rebuild the pool eligibility mask on the current hill."""
import json
import shutil
import sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from scipy.ndimage import map_coordinates,maximum_filter
from scipy.spatial import cKDTree
from generate_reference_hill import smooth

def prepare(out, *, root=None, hill=None):
    root=out.parent if root is None else root
    variant=hill is not None
    hill=root/'ReferenceHill-R12' if hill is None else hill
    hydro=root/'HillsWoodlandPools-R9'
    cover=out/'Grass'
    cover.mkdir(parents=True,exist_ok=True)
    for n in ('region.i16','hill.json','gate-road.csv'):
        shutil.copyfile(hill/n,out/n)
    shutil.copyfile(root/'VillageGroundRelief-R11/reference.f32',out/'reference.f32')
    for p in hydro.glob('study_*'):
        shutil.copyfile(p,cover/p.name)
    z=np.fromfile(out/'region.i16','<i2').reshape(1025,1025)*.01
    y,x=np.mgrid[-320:705,-624:401]
    xy=np.loadtxt(out/'gate-road.csv',delimiter=',',skiprows=1)[:,:2]
    dist,idx=cKDTree(xy).query(np.c_[x.ravel(),y.ravel()])
    d=dist.reshape(x.shape)
    station=np.r_[0,np.cumsum(np.hypot(*np.diff(xy,axis=0).T))][idx].reshape(x.shape)
    road=1-smooth(1.45,3.35+.14*np.sin(station*.075),d)
    if variant:
        from trail_variation import road_paint, stations
        road=road_paint(xy,stations(xy),idx.reshape(x.shape),x,y,d,6721)
    verge=1-smooth(5.3,13.3,d)
    verge_input=root/'WildGrass-oilox20'
    spec=json.loads((verge_input/'placement.json').read_text())
    mask=np.asarray(Image.open(verge_input/'T_RoadsideMask.png').convert('L'),dtype='f4')/255.
    ox,oy=spec['mask_origin_cm']; sx,sy=spec['mask_span_cm']
    ax,ay=x.clip(-252,252),y.clip(-252,252)
    native_verge=map_coordinates(mask,[(ay*100-oy)/sy*mask.shape[0]-.5,(ax*100-ox)/sx*mask.shape[1]-.5],order=1,mode='constant',cval=0.)
    dirt=np.fromfile(cover/'study_dirt_2m.u8','u1').reshape(253,253)/255.
    C=map_coordinates(dirt,[(ay+252)*.5,(ax+252)*.5],order=1,mode='nearest')
    edges=np.fromfile(root/'ForestVillage-R2/edge_dirt.u8','u1').reshape(4,505)/255.
    for boundary,values,at in [(ay==-252,edges[0],ax),(ay==252,edges[1],ax),(ax==-252,edges[2],ay),(ax==252,edges[3],ay)]:
        C[boundary]=values[at[boundary]+252]
    f=smooth(0,8,np.hypot(x-ax,y-ay))
    C=C*(1-f)+road*f
    G=native_verge*(1-f)+verge*f
    np.rint(255*np.stack([C,G],axis=-1).clip(0,1)).astype('u1').tofile(out/'paint.rg8')
    vx,vy=json.loads((out/'hill.json').read_text())['site_min_m']
    allowed=(maximum_filter(C,size=7)<.25)&(np.hypot(*np.gradient(z))<.45)
    allowed &= ~((x>=vx-5)&(x<=vx+123)&(y>=vy-5)&(y<=vy+150))
    stamp=Image.new('L',(1025,1025),0)
    draw=ImageDraw.Draw(stamp)
    for path in ('study_obstacles.f32','study_trees.f32','study_pond_props.f32'):
        for px,py,r in np.fromfile(cover/path,'<f4').reshape(-1,3):
            px+=624; py+=320;r+=.65
            draw.ellipse((round(px-r),round(py-r),round(px+r),round(py+r)),fill=1)
    (allowed&(np.asarray(stamp)==0)).astype('u1').tofile(cover/'pond_allowed.u8')

if __name__=='__main__': prepare(Path(sys.argv[1]))
