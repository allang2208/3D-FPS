"""Generate sparse talus fans at the downhill toes of the saved exposed rock faces (metres)."""
from pathlib import Path
import json
import sys

import numpy as np
from scipy.ndimage import distance_transform_edt, gaussian_filter
from scipy.spatial import cKDTree

from generate_slope_grass import POINT, WEST, SOUTH, grid_at

FINE = '07f4fdeb-3cd7-4043-bbc0-fbf040815a2d'
FRAGMENT = '6c32aa80-88bf-421e-8568-dd2e424980ef'
SITE = np.dtype([('x','<f4'),('y','<f4'),('yaw','<f4'),('scale','<f4'),('flags','<i4')])
ROAD_BAND_M = 13.3


def prepare(terrain, themes, rock_catalog, out, only=None):
    catalog = json.loads(rock_catalog.read_text(encoding='utf-8-sig'))
    by_id = {entry['listing']:entry for entry in catalog}
    meshes = [by_id[FINE],by_id[FRAGMENT]]
    widths = np.array([m['width_cm'] for m in meshes])*.01
    widths_by_path = {m['mesh']:m['width_cm']*.01 for m in catalog}
    height = np.fromfile(terrain/'region.i16','<i2').reshape(1025,1025)*.01
    exposure = np.fromfile(terrain/'cliff-mask.u8','u1').reshape(height.shape)/255.
    dy,dx = np.gradient(gaussian_filter(height,1.05))
    road_lines = [np.loadtxt(terrain/(name+'-road.csv'),delimiter=',',skiprows=1)[:,:2] for name in ('gate','quarry')]
    guide = cKDTree(np.vstack(road_lines))
    paint = np.fromfile(terrain/'paint.rg8','u1').reshape(1025,1025,2)[...,0]/255.
    grass = terrain/'Grass'
    original = np.fromfile(grass/'study_dirt_2m.u8','u1').reshape(253,253)/255.
    axis = np.arange(-252,253)
    paint[68:573,372:877] = grid_at(original,*np.meshgrid(axis,axis),-252,-252,2)
    water = np.fromfile(grass/'pond_wet.u8','u1').reshape(4097,4097)
    shore = np.fromfile(grass/'pond_shore.u8','u1').reshape(height.shape)
    quarry = np.fromfile(terrain/'quarry-clear.u8','u1').reshape(height.shape)
    protected = (quarry>10)|(shore>8)
    # Include every wet quarter-metre sample in its metre block.
    protected[:-1,:-1] |= water[:-1,:-1].reshape(1024,4,1024,4).max(axis=(1,3))>0
    vx,vy = json.loads((terrain/'hill.json').read_text())['site_min_m']
    x0,y0 = int(vx-WEST),int(vy-SOUTH)
    protected[y0:y0+146,x0:x0+119] = True
    clearance = distance_transform_edt(~protected)

    obstacles = [np.fromfile(grass/(key+'.f32'),'<f4').reshape(-1,3)
                 for key in ('study_obstacles','study_trees','study_pond_props')]
    stock=np.fromfile(grass/'harvest-trees.f32','<f4').reshape(-1,3)
    obstacles.append(np.c_[stock[:,:2]*.01,np.full(len(stock),.55)])
    for theme in ('HillsLandscape','RoadLandscape'):
        folder=themes/theme
        records=np.fromfile(folder/'planting.bin',POINT)
        palette=(folder/'reference-meshes.txt').read_text(encoding='utf-8-sig').splitlines()
        for slot in [0,1,4,5]+[16+i for i,path in enumerate(palette) if path in widths_by_path]:
            part=records[records['slot']==slot]
            if not len(part):continue
            radii=(np.full(len(part),.46) if slot<2 else
                   part['size']*(widths_by_path[palette[slot-16]]*.5 if slot>=16 else .62))
            obstacles.append(np.c_[part['x']*.01,part['y']*.01,radii])
    ledges=np.fromfile(terrain/'ledge-sites.bin',SITE)
    ledge_xy=np.c_[ledges['x'],ledges['y']]*.01
    obstacles.append(np.c_[ledge_xy,np.where(ledges['flags']&2,1.95,1.05)*ledges['scale']])
    blocks=np.vstack(obstacles)
    tree=cKDTree(blocks[:,:2]);search_radius=float(blocks[:,2].max())+.35

    def sample(grid,xy):
        return float(grid_at(grid,np.array([xy[0]]),np.array([xy[1]]))[0])

    def legal(xy,radius):
        if not (-622.<xy[0]<398. and -318.<xy[1]<702.):return False
        return (guide.query(xy)[0]>3.65+radius and sample(paint,xy)<.24 and
                sample(clearance,xy)>1.1+radius)

    def downhill(p):
        grad=np.array([sample(dx,p),sample(dy,p)])
        strength=np.linalg.norm(grad)
        return -grad/max(.0001,strength),strength

    rng=np.random.default_rng(237891)
    # Named ledges and irregularly spaced sections of larger exposed faces can shed material.
    seeds=list(ledge_xy[rng.permutation(len(ledge_xy))])
    iy,ix=np.indices((58,58))
    candidates=np.c_[WEST+(ix.ravel()+rng.uniform(.08,.92,ix.size))*18.,
                     SOUTH+(iy.ravel()+rng.uniform(.08,.92,iy.size))*18.]
    for p in candidates[rng.permutation(len(candidates))]:
        if sample(exposure,p)>.61:seeds.append(p)
    centres=[];placed=[];occupied={};fans=[]
    for source in seeds:
        p=source.copy();best=None;best_score=-np.inf
        for step in range(20):
            flow,grade=downhill(p)
            if grade<.04 or not legal(p,.18):break
            p=p+flow*.85
            if not legal(p,.18):break
            cover=sample(exposure,p)
            if 2<=step and grade<.75 and cover<.60 and sample(height,source)-sample(height,p)>.52:
                # Prefer the first shelf where the gradient relaxes at the edge of the rock.
                score=1.-abs(grade-.41)-.52*abs(cover-.18)-.016*step
                if score>best_score:best_score=score;best=(p.copy(),flow.copy())
            if step>3 and (grade<.21 or (cover<.07 and best is not None)):break
        if best is None:continue
        centre,flow=best
        if any(np.linalg.norm(centre-old)<5. for old in centres):continue
        sideways=np.array([-flow[1],flow[0]])
        fine_count=int(rng.integers(4,12));large_count=int(rng.integers(2,6));accepted=0
        for variant in [1]*large_count+[0]*fine_count:
            for _ in range(5):
                # A few larger fragments roll farther. Fine chips concentrate around the toe.
                along=np.clip(rng.normal(.40 if variant else -.14, .89),-1.8,2.5)
                off=np.clip(rng.normal(0,.42+.13*max(along,0.)),-1.4,1.4)
                at=centre+flow*along+sideways*off
                scale=rng.uniform(.63,1.38) if variant else rng.uniform(.45,1.05)
                radius=widths[variant]*scale*.52
                if not legal(at,radius) or downhill(at)[1]>.79 or sample(exposure,at)>.72:continue
                near=tree.query_ball_point(at,search_radius)
                if near and np.any(np.linalg.norm(blocks[near,:2]-at,axis=1)<blocks[near,2]+radius):continue
                ix,iy=np.floor(at).astype(int)
                neighbours=(pair for j in range(iy-1,iy+2) for i in range(ix-1,ix+2) for pair in occupied.get((i,j),()))
                if any(np.linalg.norm(at-old)<radius+r+.025 for old,r in neighbours):continue
                road=int(guide.query(at)[0]<=ROAD_BAND_M)
                placed.append((at[0]*100.,at[1]*100.,rng.uniform(-180.,180.),scale,2*variant+road))
                occupied.setdefault((ix,iy),[]).append((at,radius));accepted+=1
                break
        if accepted:
            centres.append(centre);fans.append([*map(float,centre),accepted])
    sites=np.asarray(placed,dtype=SITE)
    counts={owner:[int(np.count_nonzero(sites['flags']==v*2+t)) for v in (0,1)]
            for t,owner in enumerate(('HillsLandscape','RoadLandscape'))}
    if only is not None and only not in counts:raise ValueError('Unknown landscape theme '+only)
    out.mkdir(exist_ok=True,parents=True)
    for owner,tag in [('HillsLandscape',0),('RoadLandscape',1)]:
        if only is not None and owner!=only:continue
        folder=out/owner/'Rocks'
        folder.mkdir(parents=True,exist_ok=True)
        sites[(sites['flags']&1)==tag].tofile(folder/'talus-sites.bin')
        (folder/'theme.id').write_text(owner,encoding='ascii')
        (folder/'talus.json').write_text(json.dumps({'seed':237891,'terrain':terrain.name,'meshes':meshes,'counts':{owner:counts[owner]}},indent=2))
    report={'seed':237891,'terrain':terrain.name,'fans':len(fans),'sites':len(sites),'meshes':meshes,
            'counts':counts,'centres_m':fans}
    if only is None:
        sites.tofile(out/'talus-sites.bin')
        (out/'talus.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report

if __name__=='__main__':
    import argparse
    cli=argparse.ArgumentParser(description=__doc__)
    for name in ('terrain','themes','rock_catalog','out'):cli.add_argument(name,type=Path)
    cli.add_argument('--theme',choices=('HillsLandscape','RoadLandscape'))
    args=cli.parse_args()
    result=prepare(args.terrain,args.themes,args.rock_catalog,args.out,args.theme)
    print(result['counts'][args.theme] if args.theme else result['counts'])
