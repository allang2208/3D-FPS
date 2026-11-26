"""Bake a continuous triangular grass lattice. The close layer is packed by 16 m PCG cell."""
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import distance_transform_edt, gaussian_filter, map_coordinates, maximum_filter

POINT = np.dtype([('x','<f4'),('y','<f4'),('yaw','<f4'),('size','<f4'),('slot','<i4')])
WEST, SOUTH, SIDE = -624., -320., 1025
SEED, CELL, TILES, COLS, ROWS = 237855, 16, 64, 40, 46


def grid_at(field, x, y, west=WEST, south=SOUTH, step=1.):
    return map_coordinates(field, [(y-south)/step,(x-west)/step], order=1, mode='nearest')


def ground_maps(base, out, verge_source, verge_in_green=False):
    terrain = np.fromfile(base/'region.i16','<i2').reshape(SIDE,SIDE).astype('f4')/100.
    paint = np.fromfile(base/'paint.rg8','u1').reshape(SIDE,SIDE,2).astype('f4')/255.
    if verge_in_green:
        # The reference mesh stores Forest Floor road-verge coverage in G. This
        # generator's habitat field is the complementary Nordic Moss coverage.
        paint[...,1]=1.-paint[...,1]
    dirt = np.fromfile(out/'study_dirt_2m.u8','u1').reshape(253,253).astype('f4')/255.
    if dirt.max()<.5:
        raise ValueError('Study road paint unavailable')
    local = np.arange(-252.,253.)
    x,y = np.meshgrid(local, local)
    study = np.s_[68:573,372:877]
    paint[study][...,0] = grid_at(dirt,x,y,-252.,-252.,2.)
    spec = json.loads((verge_source/'placement.json').read_text())
    verge = np.asarray(Image.open(verge_source/'T_RoadsideMask.png').convert('L'),dtype='f4')/255.
    ox,oy = spec['mask_origin_cm']
    sx,sy = spec['mask_span_cm']
    paint[study][...,1] = 1.-map_coordinates(verge, [(y*100.-oy)/sy*verge.shape[0]-.5,
                                                        (x*100.-ox)/sx*verge.shape[1]-.5],
                                                order=1,mode='constant',cval=0.)
    return paint[...,0],paint[...,1],np.hypot(*np.gradient(terrain))


def decor_mask(xy, original, out, extra_circles):
    # A 25 cm occupancy grid avoids querying every tree and rock at every blade location.
    stamp = Image.new('L',(4097,4097),0)
    draw = ImageDraw.Draw(stamp)
    circles = [np.fromfile(out/'study_obstacles.f32','<f4').reshape(-1,3)]
    for slots,radius in (([2,3],.39),([4,5],.34),([6,7],.20),([8,9],.12),([12,13,14],.22)):
        points = xy[np.isin(original['slot'],slots)]
        circles.append(np.column_stack((points,np.full(len(points),radius))))
    for x,y,r in np.concatenate([*circles,*extra_circles]):
        x,y,r=(x-WEST)*4.,(y-SOUTH)*4.,r*4.
        draw.ellipse((round(x-r),round(y-r),round(x+r),round(y+r)),fill=1)
    return np.asarray(stamp)


def canopy_mask(xy, original, out, understory):
    tree_edges = np.full((4097,4097),255,dtype='u1')
    trees = xy[np.isin(original['slot'],[0,1])]
    for x,y,r in np.concatenate((np.column_stack((trees,np.full(len(trees),.56))),
                                  np.fromfile(out/'study_trees.f32','<f4').reshape(-1,3))):
        cx,cy=(x-WEST)*4.,(y-SOUTH)*4.
        core=max(.24,.52*r)*4.
        outer=(r+(2.4 if understory else .85))*4.
        x0,x1=max(0,int(np.floor(cx-outer))),min(4097,int(np.ceil(cx+outer))+1)
        y0,y1=max(0,int(np.floor(cy-outer))),min(4097,int(np.ceil(cy+outer))+1)
        if x1<=x0 or y1<=y0: continue
        yy,xx=np.ogrid[y0:y1,x0:x1]
        weight=np.clip((np.hypot(xx-cx,yy-cy)-core)/(outer-core),0.,1.)
        if understory:
            weight=.62+.38*weight*weight*(3.-2.*weight)
        dst=tree_edges[y0:y1,x0:x1]
        np.minimum(dst,np.rint(255.*weight).astype('u1'),out=dst)
    return tree_edges


def pool_mask(base,out,verge_source):
    soil,_,slope=ground_maps(base,out,verge_source)
    allowed=(maximum_filter(soil,size=9)<.25)&(slope<.45)
    y,x=np.ogrid[int(SOUTH):int(SOUTH)+SIDE,int(WEST):int(WEST)+SIDE]
    allowed &= ~((x>=-177)&(x<=-49)&(y>=247)&(y<=402))
    # The Landscape sublevel owns its own immutable props. Their footprints drain the flood.
    hard=Image.new('L',(SIDE,SIDE),0)
    draw=ImageDraw.Draw(hard)
    for name in ('study_trees.f32','study_obstacles.f32','study_pond_props.f32'):
        for x,y,r in np.fromfile(out/name,'<f4').reshape(-1,3):
            x,y,r=x-WEST,y-SOUTH,r+.65
            draw.ellipse((round(x-r),round(y-r),round(x+r),round(y+r)),fill=1)
    (allowed&(np.asarray(hard)==0)).astype('u1').tofile(out/'pond_allowed.u8')


def site_hash(indices):
    # Matches SiteHash in ForestVillageGrassCover.cpp. The byte mask encodes form and rest height.
    h = (indices+np.uint32(SEED))*np.uint32(0x9e3779b1)
    h = (h^(h>>16))*np.uint32(0x85ebca6b)
    return h^(h>>13)


def road_margin(soil):
    # Signed metres from the painted road edge, with subcell coverage on antialiased pixels.
    road=soil>=.5
    signed=np.where(road,.5-distance_transform_edt(road),distance_transform_edt(~road)-.5)
    partial=(soil>.04)&(soil<.96)
    signed[partial]=(.5-soil[partial])*2.
    return signed.astype('f4')


def shoulder_cover(margin,x,y):
    # Independent world-space fields on opposing verges. Keep the centre of narrow tracks open.
    tongues=.72*np.sin(.39*x+.25*y+.9*np.sin(.13*y))+.52*np.sin(.14*x-.51*y)+.22*np.sin(1.3*x+.96*y)
    t=np.clip((margin+.42+tongues)/(2.65+.48*np.sin(.22*x-.16*y)),0.,1.)
    return np.where(margin<=-1.18,0.,t*t*(3.-2.*t))


def generate(base, out, verge_source, *, verge_in_green=False, extra_circles=(), understory=False):
    original = np.fromfile(base/'planting.bin',POINT)
    layout=base/'hill.json'
    vx,vy=(json.loads(layout.read_text())['site_min_m'] if layout.exists() else (-172,252))
    soil,moss,slope = ground_maps(base,out,verge_source,verge_in_green)
    margin=road_margin(soil)
    clear_file=base/'quarry-clear.u8'
    quarry=np.fromfile(clear_file,'u1').reshape(SIDE,SIDE) if clear_file.exists() else None
    pond=np.fromfile(out/'pond_wet.u8','u1').reshape((SIDE-1)*4+1,-1)
    shore=gaussian_filter(pond,sigma=2.)
    dry=grid_at(pond,original['x']*.01,original['y']*.01,step=.25)<32
    original=original[dry]
    xy = np.column_stack((original['x'],original['y']))*.01
    blocked = None if understory else decor_mask(xy,original,out,extra_circles)
    tree_edges = canopy_mask(xy,original,out,understory)
    col = np.tile(np.arange(COLS),ROWS*TILES)
    row = np.tile(np.repeat(np.arange(ROWS),COLS),TILES)
    cell_x = np.repeat(np.arange(TILES),ROWS*COLS)
    points_per_strip = len(col)
    middle_count = np.zeros(3,dtype='i8')
    near_count = np.zeros(3,dtype='i8')
    study_count = flat_count = 0

    with (out/'near_grass.u8').open('wb') as packed, (out/'planting.bin').open('wb') as stream:
        original.tofile(stream)
        for cell_y in range(TILES):
            ids = np.arange(cell_y*points_per_strip,(cell_y+1)*points_per_strip,dtype='u4')
            h = site_hash(ids)
            jx = ((h&255)/255.-.5)*.20
            jy = (((h>>8)&255)/255.-.5)*.20
            x = WEST+cell_x*CELL+(col+.25+.5*(row%2)+jx)*(CELL/COLS)
            y = SOUTH+cell_y*CELL+(row+.5+jy)*(CELL/ROWS)
            wet = grid_at(moss,x,y)
            grade = grid_at(slope,x,y)
            village = (x>vx)&(x<vx+118)&(y>vy)&(y<vy+145)
            iy,ix=np.rint((y-SOUTH)*4).astype(int),np.rint((x-WEST)*4).astype(int)
            edge=tree_edges[iy,ix].astype('f4')/255.
            bank=grid_at(pond,x,y,step=.25)
            shore_weight=grid_at(shore,x,y,step=.25).astype('f4')/128.
            edge=np.minimum(edge,1.-.72*np.minimum(shore_weight,1.))
            shoulder=shoulder_cover(grid_at(margin,x,y),x,y)
            valid = (~village)&(grade<.90)
            if blocked is not None: valid &= blocked[iy,ix]==0
            valid &= (site_hash(ids+np.uint32(19609))&65535)/65536.<shoulder
            if quarry is not None: edge*=1.-grid_at(quarry,x,y)/255.
            edge=np.minimum(edge,.42+.58*shoulder)
            # The maintained gate apron crosses from the village onto the original Landscape.
            valid &= ~((np.abs(x-(vx+64.))<2.2)&(y>vy-2.)&(y<vy+8.))
            rnd = site_hash(ids+np.uint32(76543))
            valid &= (bank<32)&((site_hash(ids+np.uint32(3341))&65535)/65536.<edge)
            choice = (rnd&65535)/65536.
            form = np.where(choice < .47+.15*wet,0,1)
            form[choice>1.-(.055-.035*wet)] = 2
            form[(edge<.82)&(choice>edge*.55)] = 0
            # About one in nine sites is present through the middle distance. Its neighbours stream locally.
            gx,gy = cell_x*COLS+col,cell_y*ROWS+row
            middle = valid&(gy%3==0)&(gx%3==((gy//3)%2))
            if understory:
                # With the old prop holes filled, keep the outer forest's permanent
                # instance budget by streaming some middle sites with the close layer.
                distance=np.hypot(np.maximum(np.abs(x)-252.,0.),np.maximum(np.abs(y)-252.,0.))
                t=np.clip(distance/12.,0.,1.)
                keep=1.-.19*t*t*(3.-2.*t)
                middle &= (site_hash(ids+np.uint32(41387))&65535)/65536.<keep
            close = valid&~middle
            variation = ((rnd>>16)/65535.-.5)*.16
            patch=.045*np.sin(.32*x+.19*y)+.035*np.sin(.17*x-.39*y)
            height=np.rint(np.choose(form,[28.,39.,50.])*(1.-.06*wet+variation+patch)*
                           (.42+.58*edge)*np.where(middle,1.17,1.)).clip(1,63).astype('u1')
            np.where(close,(height<<2)|(form+1),0).astype('u1').tofile(packed)
            records = np.empty(middle.sum(),POINT)
            records['x'], records['y'] = x[middle]*100.,y[middle]*100.
            records['size'] = height[middle]
            records['slot'] = form[middle]+12
            records['yaw'] = (h[middle]>>16)*(360./65536.)
            records.tofile(stream)
            near_count += np.bincount(form[close],minlength=3)
            middle_count += np.bincount(form[middle],minlength=3)
            study_count += int(np.count_nonzero(valid&(np.abs(x)<=252.)&(np.abs(y)<=252.)))
            flat_count += int(np.count_nonzero(valid&(grade<.035)))
    names = ('low','spreading','tall')
    total = int(near_count.sum()+middle_count.sum())
    info = {'format':1,'seed':SEED,'kept_points':len(original),'eligible_sites':total,
            'study_sites':study_count,'surrounding_sites':total-study_count,'flat_sites':flat_count,
            'near_sites':int(near_count.sum()),'baked_middle_sites':int(middle_count.sum()),
            'near_by_form':dict(zip(names,near_count.tolist())),'middle_by_form':dict(zip(names,middle_count.tolist())),
            'cell_size_m':CELL,'sites_per_cell':COLS*ROWS,'nominal_sites_per_m2':COLS*ROWS/CELL**2,
            'packed_mask_bytes':(out/'near_grass.u8').stat().st_size}
    (out/'generation.json').write_text(json.dumps(info,indent=2))
    return info


if __name__=='__main__':
    step=pool_mask if sys.argv[4:]==['--pool-mask'] else generate
    step(Path(sys.argv[1]),Path(sys.argv[2]),Path(sys.argv[3]))
