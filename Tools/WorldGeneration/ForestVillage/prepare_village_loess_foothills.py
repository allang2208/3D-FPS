"""Regrade the official hill fringes and village wall aprons on the R28 physical height grids."""
from pathlib import Path
import json,math,re,shutil,sys
import numpy as np
from PIL import Image
from scipy.ndimage import map_coordinates,gaussian_filter,distance_transform_edt,maximum_filter
from scipy.spatial import cKDTree
from generate_reference_hill import smooth
from generate_village_relief import generate as site_masks
from layout_geometry import wall_segments

PROJECT=Path(__file__).resolve().parents[3]
WEST,SOUTH=-624,-320
def at(z,x,y):
    return map_coordinates(z,[y-SOUTH,x-WEST],order=1,mode='nearest',prefilter=False)
def u16(p,z_cm):
    Image.fromarray(np.rint(32768.+z_cm.astype(float)).clip(0,65535).astype('uint16')).save(p)
def flow(shape,rng,sigma):
    a=gaussian_filter(rng.standard_normal(shape),sigma,mode='reflect')
    return np.tanh((a-np.median(a))/max(a.std(),1.e-6))
def walls(layout,lx,ly):
    ex,ey=layout['surface_extent_m']
    corners=[(ex-6,ey),(-ex+6,ey),(-ex,ey-6),(-ex,-ey+6),(-ex+6,-ey),(ex-6,-ey),(ex,-ey+6),(ex,ey-6)]
    segs=[(a,b,.78) for a,b in zip(corners,corners[1:]+corners[:1])]
    segs.extend((piece[1:3],piece[3:5],width) for piece,width in wall_segments(layout))
    gap=np.full(lx.shape,np.inf)
    for a,b,width in segs:
        dx,dy=b[0]-a[0],b[1]-a[1]
        t=np.clip(((lx-a[0])*dx+(ly-a[1])*dy)/max(dx*dx+dy*dy,.0001),0.,1.)
        gap=np.minimum(gap,np.hypot(lx-a[0]-t*dx,ly-a[1]-t*dy)-width)
    return gap

def soil_textures(root,out):
    src=root/'GateRoadSurface-R25/Village';dest=out/'Loess';dest.mkdir(exist_ok=True)
    alpha=lambda name:Image.open(src/('ChapelEarth_'+name+'.tga'))
    color=np.asarray(alpha('B').convert('RGB').resize((1024,1024),Image.Resampling.LANCZOS),dtype=float)
    lum=color@np.array([.26,.60,.14]);contrast=np.clip((lum-np.median(lum))/max(24.,np.std(lum)*3),-1.1,1.1)
    # Warm buff silt retains the dry earth scan's grain and small mineral flecks.
    # Keep the mineral texture visible in direct sun. Preserve the scan's contrast while
    # pulling the brightest dust towards a neutral straw colour instead of saturated orange.
    col=np.array([139.,113.,83.])+contrast[...,None]*np.array([40.,36.,29.])+.24*(color-lum[...,None]-(color-lum[...,None]).mean(axis=(0,1)))
    Image.fromarray(col.clip(0,255).astype('u1')).save(dest/'T_VillageLoess_B.png')
    alpha('N').convert('RGB').resize((512,512),Image.Resampling.LANCZOS).save(dest/'T_VillageLoess_N.png')
    orm=alpha('ORM').convert('RGB').resize((512,512),Image.Resampling.LANCZOS)
    h=alpha('H').convert('L').resize((512,512),Image.Resampling.LANCZOS)
    Image.merge('RGB',(orm.getchannel('R'),orm.getchannel('G'),h)).save(dest/'T_VillageLoess_ARH.png')
    return np.asarray(h,dtype=float)/255.

def terrain(root,out):
    old=root/'HillReliefPools-R28';out.mkdir(exist_ok=True,parents=True)
    for key in ('reference.f32','paint.rg8','quarry-clear.u8','gate-road.csv','quarry-road.csv','hill.json'):
        shutil.copy2(old/key,out/key)
    hill=json.loads((old/'hill.json').read_text());vx,vy=hill['site_min_m'];cx,cy=hill['village_center_m']
    base=np.fromfile(old/'region.i16','<i2').reshape(1025,1025).astype(float)*.01
    y,x=np.mgrid[SOUTH:SOUTH+1025,WEST:WEST+1025]
    rng=np.random.default_rng(473251)
    bend=flow(x.shape,rng,30.);spurs=flow(x.shape,rng,19.);reach=flow(x.shape,rng,49.)
    ax=np.clip(x,-252,252);ay=np.clip(y,-252,252);ox=x-ax;oy=y-ay;dist=np.hypot(ox,oy)
    nx=ox/np.maximum(dist,.001);ny=oy/np.maximum(dist,.001)
    broad=gaussian_filter(base,5.); low=gaussian_filter(base,2.)
    ridge=smooth(-3.,9.,at(broad,ax,ay))
    # Vary runout along the observed ridge edge. The normal derivative at the Landscape join stays one.
    scale=1.15+ridge*(1.95+1.10*spurs+.85*reach)
    inward=dist/scale+(1-1/scale)*4.*(-np.expm1(-dist/4.))
    sweep=(dist-inward)*(.37*bend+.16*spurs)
    sampled=at(low,ax+nx*inward-ny*sweep,ay+ny*inward+nx*sweep)
    skirt=np.maximum(0.,sampled-low)*ridge*smooth(.5,6.,dist)*(1-smooth(108.,180.,dist))
    # Secondary spurs around the summit and former quarry apron. Inner summits keep their characteristic shape.
    extra=np.zeros_like(base)
    for mx,my,rx,ry,limit in [(-172,386,153.,128.,24.),(-483,292,96.,92.,15.)]:
        dx,dy=x-mx,y-my
        eccentric=np.hypot(dx/rx,dy/ry)
        size=np.maximum(np.hypot(dx,dy),.001)
        ux,uy=dx/size,dy/size
        movement=limit*smooth(.28,.72,eccentric)*(1-smooth(1.25,1.92,eccentric))*(.85+.56*spurs+.34*bend)
        incoming=at(low,x-ux*movement-uy*movement*.23*bend,y-uy*movement+ux*movement*.23*bend)
        extra=np.maximum(extra,np.maximum(0.,incoming-low))
    road_points=np.vstack([np.loadtxt(out/(k+'-road.csv'),delimiter=',',skiprows=1)[:,:2] for k in ('gate','quarry')])
    rd=cKDTree(road_points).query(np.column_stack((x.ravel(),y.ravel())))[0].reshape(x.shape)
    qmask=np.fromfile(old/'quarry-clear.u8','u1').reshape(x.shape)
    wet=np.fromfile(old/'Grass/pond_wet.u8','u1').reshape(4097,4097)
    wet_knots=maximum_filter(wet,5)[::4,::4]>0
    wd=distance_transform_edt(~wet_knots);qd=distance_transform_edt(qmask<12)
    td=np.hypot(np.maximum(np.maximum(vx-x,x-vx-118.),0),np.maximum(np.maximum(vy-y,y-vy-145.),0))
    protected=smooth(5.5,34.,rd)*smooth(8.,40.,wd)*smooth(2.,24.,qd)*smooth(2.,20.,td)*smooth(.5,7.,dist)
    mass=17.*np.tanh(gaussian_filter(np.maximum(skirt,extra),3.8)/17.)
    # Retain the actual R28 microrelief, with a little local smoothing of the old straight apron.
    change=(mass+smooth(.06,1.5,mass)*.32*(low-base))*protected
    h=base+change

    source_h=soil_textures(root,out)
    geom=json.loads((PROJECT/'SourceAssets/TemperateHillsVillage/layout.json').read_text(encoding='utf-8-sig'))
    # Region collar on both sides of the foundation seam. External roads and pond shore are pinned.
    lx=cy-y;ly=x-cx
    ex,ey=geom['surface_extent_m']
    perimeter=np.minimum.reduce([ex-np.abs(lx),ey-np.abs(ly),(ex+ey-6-np.abs(lx)-np.abs(ly))*.70710678])
    w=(1-smooth(3.,19.,np.maximum(-perimeter,0)))*smooth(4.,12.,rd)*smooth(5.,16.,wd)*smooth(.5,5.,dist)
    # Existing sampled ground within the village is supplied by the dynamic foundation; its surrounding collar is graded once.
    relief=gaussian_filter(h,1.1)-gaussian_filter(h,4.8)
    level=hill['village_datum_cm']*.01+.15*np.tanh((gaussian_filter(h,12.)-hill['village_datum_cm']*.01)/1.4)+.075*np.tanh(relief/.23)
    h+=w*(level-h)
    cm=np.rint(h*100).astype('<i2');cm.tofile(out/'region.i16');u16(out/'H_Hills_R32.png',cm)

    oy,ox=np.indices((146,119));X=vx+ox;Y=vy+oy;lx=cy-Y;ly=X-cx
    off=np.fromfile(old/'settlement.i16','<i2').reshape(146,119).astype(float)
    inl=(PROJECT/'Source/FPSGAME/WorldGeneration/TemperateVillageGroundData.inl').read_text(encoding='utf-8-sig')
    table=inl.split('Relief[Rows][Columns]={',1)[1].split('};',1)[0]
    native=np.array([int(t) for t in re.findall(r'-?\d+',table)]).reshape(101,131)
    foot=np.zeros_like(off);inside=(np.abs(lx)<65)&(np.abs(ly)<50)
    foot[inside]=native[ly[inside]+50,lx[inside]+65]
    old_combined=foot+off
    solids,open_soil=site_masks(root/'VillageGroundRelief-R11',site_weights=True,wall_flanks=True)
    wall=walls(geom,lx,ly)
    duty=np.clip(1.-smooth(3.,9.,np.maximum(wall,0)),0,1)
    contact=wall<.40
    norm=gaussian_filter(contact.astype(float),4.)
    support=gaussian_filter(old_combined*contact,4.)/np.maximum(norm,.001)
    coarse=gaussian_filter(old_combined,6.)
    target=.20*coarse+.80*support*duty+.80*coarse*(1.-duty)
    # The saved 1 m geometry samples the low band of the same height scan as the material.
    grain=gaussian_filter(source_h,16.,mode='wrap')
    grain=(grain-grain.mean())/max(.00001,grain.std())
    u=2.25*ox+.59*oy+5.*np.sin(oy*.065);v=2.62*oy-.48*ox
    grain=map_coordinates(grain,[v,u],order=1,mode='grid-wrap')
    measured= np.asarray(Image.open(old/'H_ReferenceShort.png'),dtype=float)-32768
    detail=map_coordinates(measured,[5.+oy*.73,4.+ox*.71],order=1,mode='nearest')
    relief_cm=(.64*np.tanh(grain)+.36*np.tanh(detail/24.))*(8.-3.5*duty)
    target+=relief_cm
    rim=np.minimum.reduce([ox,118-ox,oy,145-oy])
    weight=solids*open_soil*smooth(1.42,2.75,wall)*smooth(1.,5.,rim)
    # Buildings, service yards, doorsteps, actual wall contacts and road centres remain at their seated elevations.
    offset=np.rint(off+weight*(target-old_combined)).astype('<i2')
    offset.tofile(out/'settlement.i16');u16(out/'H_VillageLoessOffsets.png',offset)
    wall_stats=(wall>1.5)&(wall<5.)&(weight>.45)
    def p90_slope(a):
        gy,gx=np.gradient(a*.01)
        return round(float(np.percentile(np.hypot(gy,gx)[wall_stats],90)),4)
    report=dict(site_m=[vx,vy],village_changed_knots=int(np.count_nonzero(offset-off)),
        wall_flank_open_knots=int(wall_stats.sum()),wall_p90_grade_before=p90_slope(old_combined),wall_p90_grade_after=p90_slope(foot+offset),
        changed_region_knots=int(np.count_nonzero(cm-np.rint(100*base))),max_foot_change_m=round(float(change.max()),2),
        physical_loess_relief_cm=[round(float(relief_cm.min()),2),round(float(relief_cm.max()),2)])
    # Water and road locations are shared immutable inputs to this regrade. No new pools or palette draws.
    grass=out/'Grass';grass.mkdir(exist_ok=True)
    for key in ('pond_wet.u8','pond_depth.u8','pond_shore.u8','ponds.csv','study_dirt_2m.u8','study_trees.f32',
                'study_obstacles.f32','study_pond_props.f32','planting.bin','near_grass.u8','reference-meshes.txt','harvest-trees.f32','study-granite.i32'):
        shutil.copy2(old/'Grass'/key,grass/key)
    from village_wall_grass import wall_grass
    report['wall_grass']=wall_grass(out,grass/'near_grass.u8',old/'Grass/near_grass.u8')
    (out/'wall-grass.json').write_text(json.dumps(report['wall_grass'],indent=2))
    from prepare_hill_relief_pools import write_pool_eligibility
    iy,ix=np.indices((505,505))
    dirt=np.fromfile(grass/'study_dirt_2m.u8','u1').reshape(253,253)/255.
    refroad=map_coordinates(dirt,[iy*.5,ix*.5],order=1,mode='nearest')
    write_pool_eligibility(out,cm,refroad,td,rd,qd)
    from continuous_meadow import bake
    report['fine_grass']=bake(old,out,cm.astype('f4'),np.fromfile(out/'paint.rg8','u1').reshape(1025,1025,2),loess_perimeter=True)
    hill.update(village_surface='loess',relief_recipe='VillageLoessFoothills-R32')
    (out/'hill.json').write_text(json.dumps(hill,indent=2))
    (out/'loess-foothills.json').write_text(json.dumps(report,indent=2))
    return report

if __name__=='__main__':print(terrain(Path(sys.argv[1]),Path(sys.argv[2])))
