"""Bake the forest village's terrain coverage and rooted canopy on its final metre grid."""
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter
from scipy.spatial import cKDTree

from generate_reference_hill import smooth
from generate_slope_grass import POINT, WEST, SOUTH, grid_at

def surface(z,x,y):
    """Height in centimetres on the same triangles used by ForestVillageRegion::GroundHeight."""
    x=np.clip(x-WEST,0,1024)
    y=np.clip(y-SOUTH,0,1024)
    ix=np.minimum(x.astype(int),1023)
    iy=np.minimum(y.astype(int),1023)
    dx=np.where((ix>=372)&(ix<876),1,2)
    dy=np.where((iy>=68)&(iy<932),1,2)
    ix-=ix%dx
    iy-=iy%dy
    u=(x-ix)/dx; v=(y-iy)/dy
    a,b,c,d=z[iy,ix],z[iy,ix+dx],z[iy+dy,ix],z[iy+dy,ix+dx]
    return np.where(u>=v,a*(1-u)+b*(u-v)+d*v,a*(1-v)+c*(v-u)+d*u)

def macro(rng,shape,radius):
    field=gaussian_filter(rng.standard_normal(shape).astype('f4'),radius)
    return np.clip(.5+.19*field/max(field.std(),.00001),0,1)

def bake(base,out,z,paint,*,loess_perimeter=False):
    out.mkdir(parents=True,exist_ok=True)
    rng=np.random.default_rng(82493)
    grass=base/'Grass'
    y,x=np.mgrid[-320:705,-624:401]
    dirt=paint[...,0].astype('f4')/255.
    donor=np.fromfile(grass/'study_dirt_2m.u8','u1').reshape(253,253).astype('f4')/255.
    xy=np.arange(-252.,253.)
    dirt[68:573,372:877]=grid_at(donor,*np.meshgrid(xy,xy),-252,-252,2)
    quarry=np.fromfile(base/'quarry-clear.u8','u1').reshape(z.shape)/255.
    pond=np.fromfile(grass/'pond_wet.u8','u1').reshape(4097,4097)[::4,::4]/255.
    shore=np.fromfile(grass/'pond_shore.u8','u1').reshape(z.shape)/255.
    hill=json.loads((base/'hill.json').read_text());vx,vy=hill['site_min_m']
    loess_perimeter=loess_perimeter or hill.get('village_surface')=='loess'
    town_gap=np.hypot(np.maximum(np.maximum(vx-x,x-vx-118),0),np.maximum(np.maximum(vy-y,y-vy-145),0))
    grade=np.hypot(*np.gradient(z*.01))
    habitat=(1-smooth(.10,.70,dirt))*(1-pond)*(1-quarry)*(1-smooth(1.90,2.85,grade))*(1-.77*shore)
    soil=habitat*smooth(.25,3.3,town_gap)
    surface_soil=soil
    if loess_perimeter:
        cx,cy=hill['village_center_m'];a=np.abs(cy-y);b=np.abs(x-cx)
        inside=np.minimum(np.minimum(65.-a,50.-b),(109.-a-b)*.70710678)
        # Ground colour follows the chamfered walls. Solid grass instances still use the true exterior mesh.
        surface_soil=habitat*(1.-smooth(-4.5,.45,inside))
    lean=macro(rng,z.shape,4.8)
    shade=macro(rng,z.shape,11.)
    moss=smooth(.70,1.82,grade)
    # The sample at each pixel centre is the area-average of its four terrain knots.
    channels=np.stack((surface_soil,lean,shade,moss),axis=-1)
    pixels=(channels[:-1,:-1]+channels[1:,:-1]+channels[:-1,1:]+channels[1:,1:])*.25
    Image.fromarray(np.rint(255*pixels).clip(0,255).astype('u1')).save(out/'T_ContinuousMeadowField.png')
    color=Image.open(base/'Turf/T_VillageGrass_B.png').convert('RGB').resize((1024,1024),Image.Resampling.LANCZOS)
    pigment=np.asarray(color,dtype='f4')
    mean=np.asarray(color.resize((1,1),Image.Resampling.BOX),dtype='f4')[0,0]
    palette=np.asarray(Image.open(base.parent/'HillsGrassDistance-R15/T_HillsFarGrass.png').convert('RGBA'))
    leaves=palette[palette[...,3]>180,:3]
    target=np.median(leaves,axis=0)*np.array([.87,.91,.92])
    Image.fromarray(np.clip(target+(pigment-mean)*.84,0,255).astype('u1')).save(out/'T_ContinuousMeadowBlades.png')
    Image.open(base/'Turf/T_VillageGrass_N.png').convert('RGB').resize((512,512),Image.Resampling.LANCZOS).save(out/'T_ContinuousMeadowNormal.png')

    # Stratified triangular lattice: bounded gaps, independent stable roots and no crossing strips.
    # The continuous ground already fills every grassy patch. Use the existing fine low grass
    # only as supplementary relief, with a bounded number of draws per partition.
    spacing=6.4
    row_step=spacing*np.sqrt(3.)*.5
    ny=int(np.ceil(1024/row_step))
    iy,ix=np.indices((ny,int(np.ceil(1024/spacing))))
    px=WEST+(ix+.25+.5*(iy%2)+rng.uniform(-.20,.20,ix.shape))*spacing
    py=SOUTH+(iy+.5+rng.uniform(-.21,.21,iy.shape))*row_step
    chance=grid_at(soil*(1-smooth(1.48,2.45,grade)),px,py)
    # Leave full coverage in the surface mask; group upright blades along natural drifts and slopes.
    drift=grid_at(shade,px,py)
    extra=.44+.34*smooth(.24,.78,drift)+.20*smooth(.15,.68,grid_at(grade,px,py))
    inside=(px>=WEST)&(px<WEST+1024)&(py>=SOUTH)&(py<SOUTH+1024)
    use=inside&(rng.random(px.shape)<chance*extra)&(chance>.17)
    px,py=px[use],py[use]
    original=np.fromfile(grass/'planting.bin',POINT)
    standing=original[original['slot']<2]
    trees=np.concatenate((np.column_stack((standing['x'],standing['y']))*.01,
                          np.fromfile(grass/'study_trees.f32','<f4').reshape(-1,3)[:,:2],
                          np.fromfile(grass/'harvest-trees.f32','<f4').reshape(-1,3)[:,:2]*.01))
    trunk=cKDTree(trees).query(np.column_stack((px,py)))[0]
    canopy=.65+.35*smooth(.50,3.2,trunk)
    use=rng.random(len(px))<canopy
    px,py,canopy=px[use],py[use],canopy[use]
    center=surface(z,px,py)
    gx=(surface(z,px+.12,py)-surface(z,px-.12,py))/24.
    gy=(surface(z,px,py+.12)-surface(z,px,py-.12))/24.
    def root_delta(radius):
        heights=[]
        for angle in np.arange(8)*np.pi/4.:
            ox=radius*np.cos(angle);oy=radius*np.sin(angle)
            heights.append(surface(z,px+ox,py+oy)-center-100.*(gx*ox+gy*oy))
        return np.asarray(heights)
    spread=rng.uniform(.87,1.16,len(px))
    delta=root_delta(.34*spread)
    # Split the footprint visually at convex ribs: shorten the shared cluster there and seat its lowest foot.
    spread*=1.-.52*smooth(2.,10.,np.ptp(delta,axis=0))
    delta=root_delta(.34*spread)
    root=center+np.minimum(0.,np.min(delta,axis=0))-1.0
    yaw=rng.uniform(-180.,180.,len(px))
    height=rng.uniform(.68,1.18,len(px))*canopy*(1.-.40*smooth(.80,2.20,np.hypot(gx,gy)))
    poses=np.column_stack((px*100,py*100,root,yaw,gx,gy,spread,height))
    poses.astype('<f4').tofile(out/'meadow-fine.f32')
    (out/'meadow.json').write_text(json.dumps(dict(fine_instances=len(poses),mask_pixels=1024,spacing_m=spacing),indent=2))
    return len(poses)

if __name__=='__main__':
    base,terrain,out=map(Path,sys.argv[1:])
    heights=np.fromfile(terrain/'region.i16','<i2').reshape(1025,1025).astype('f4')
    paint=np.fromfile(terrain/'paint.rg8','u1').reshape(1025,1025,2)
    print('Fine grass sites:',bake(base,out,heights,paint))
