"""Sculpt the R2 meadow beside the village and append authored PCG grass sites.
Read the archived R2 inputs; write only the new sample batch. World XY in metres.
"""
import json
from pathlib import Path
import sys

import numpy as np
from scipy.ndimage import gaussian_filter, map_coordinates
from scipy.spatial import cKDTree
from PIL import Image

POINT = np.dtype([('x','<f4'), ('y','<f4'), ('yaw','<f4'), ('size','<f4'), ('slot','<i4')])
SIDE = 1025
SEED = 237146


def smooth(a, b, value):
    t = np.clip((value-a)/(b-a), 0., 1.)
    return t*t*(3.-2.*t)


def flow_noise(rng, size, sigma):
    field = gaussian_filter(rng.standard_normal(size), sigma, mode="reflect")
    return (field-field.mean()) / max(field.std(), .001)


def make_sample(base, out):
    out.mkdir(parents=True, exist_ok=True)
    terrain = np.fromfile(base/'region.i16','<i2').reshape(SIDE,SIDE)
    paint = np.fromfile(base/'paint.rg8','u1').reshape(SIDE,SIDE,2)
    north = np.fromfile(base/'edge_dirt.u8','u1').reshape(4,505)[1]/255.
    blend = np.zeros(terrain.shape, 'u1')
    # The south side touches the approved Landscape, the west side touches the
    # village foundation. Keep those exact elevations and slope into the sample.
    x0, y0, width, length = -54, 252, 80, 120
    roi = np.s_[y0+320:y0+320+length+1, x0+624:x0+624+width+1]
    iy, ix = np.mgrid[0:length+1, 0:width+1]
    x, y = ix+x0, iy+y0
    rim = np.minimum(width-ix,length-iy)
    influence = smooth(0.,9.,rim)
    # West borders R2's foundation, south borders the approved sample. The
    # visible surface must also fade at the west boundary where no apron exists.
    influence *= smooth(0.,6.,ix)
    blend[roi] = np.rint(255*influence)
    relief_mask = influence*smooth(0.,8.,iy)*smooth(0.,8.,ix)
    rng = np.random.default_rng(SEED+403)
    fields = [flow_noise(rng, ix.shape, sigma) for sigma in (12.,5.3,2.5)]
    broad, shoulder, humps = fields
    canopy = np.clip(.76*(1.-smooth(3.,53.,iy))+.23+.14*broad,0.,1.)
    hollow = np.exp(-.5*((x-(-26.+.11*iy+4.*np.sin(iy/22.)))/4.4)**2)
    bank = np.exp(-.5*((x-(-19.+.11*iy+4.*np.sin(iy/22.)))/5.8)**2)
    large = 68.*broad - 55.*hollow + 31.*bank
    middle = (13.+15.*canopy)*shoulder + (12.+18.*canopy)*humps
    terrain[roi] = np.rint(terrain[roi].astype(float)+relief_mask*(large+middle)).astype('<i2')
    moisture = np.clip(.24+.38*hollow+.16*broad-.09*shoulder,0.,1.)
    moss = smooth(.30,.82,.72*canopy+.34*moisture+.045*humps)
    soil = .37*smooth(.56,.94,.64*hollow+.18*moisture+.12*canopy)
    # The landscape boundary is painted in C and its complementary Auto layer.
    # The mesh master paints C over A/B, so the residual non-road surface there
    # is moss. Keep a conditional moss mask, not a second independent dirt share.
    forest_dirt = north[x+252]
    edge = 1.-smooth(0.,9.,iy)
    soil = (1.-edge)*soil+edge*forest_dirt
    moss = (1.-edge)*moss+edge
    target = np.stack([soil,moss],axis=-1)
    paint[roi] = np.rint((1.-influence[...,None])*paint[roi]+255.*influence[...,None]*target)
    # Gate strip inherits the actual northern Landscape paint, then follows
    # the centre of the existing through road. The last four rows fade into town.
    gy, gx = np.mgrid[0:9,-172:-53]
    road = 1.-smooth(1.55,3.2,np.abs(gx+108))
    carry = smooth(0.,5.,gy)
    gate_soil = north[gx+252]*(1.-carry)+road*carry
    gate_moss = 1.-carry*smooth(3.,12.,np.abs(gx+108))*.68
    apron = np.rint(255*np.stack((gate_soil,gate_moss),axis=-1)).astype('u1')
    terrain.tofile(out/'region.i16')
    paint.tofile(out/'paint.rg8')
    blend.tofile(out/'sample.r8')
    apron.tofile(out/'apron.rg8')
    Image.fromarray(np.rint(32768+terrain.astype(float)).astype('uint16')).save(out/'H_ForestVillage_SurfaceSample.png')
    # Constant roughness is linear data; the grass source has no roughness map.
    Image.fromarray(np.full((4,4),199,'u1')).convert('RGB').save(out/'T_ForestSample_GrassRoughness.png')

    old = np.fromfile(base/'planting.bin',POINT)
    xy = np.column_stack((old['x'],old['y'])) / 100.
    near = (xy[:,0]>x0-4)&(xy[:,0]<x0+width+4)&(xy[:,1]>y0-4)&(xy[:,1]<y0+length+4)
    def field_at(field, px, py):
        return map_coordinates(field, [py-y0,px-x0], order=1,mode='nearest')
    in_core = near & (xy[:,0]>=x0)&(xy[:,0]<=x0+width)&(xy[:,1]>=y0)&(xy[:,1]<=y0+length)
    # Do not seed woody props, herbs or decals on the inherited painted lane.
    painted_lane = in_core & (field_at(soil,*xy.T)>.52) & (field_at(influence,*xy.T)>.5)
    kept = old[~painted_lane]
    xy = xy[~painted_lane]
    obstacles = []
    for slots, radius in (([0,1],.85),([2,3],.55),([4,5],.48),([6,7],.28)):
        coords=xy[np.isin(kept['slot'],slots)]
        if len(coords): obstacles.append((cKDTree(coords),radius))
    # Jittered groups with several independent tuft candidates per cluster.
    # Tall blades occur mainly in openings. Keep the maintained gate apron low.
    grass_rng=np.random.default_rng(SEED+197)
    extra = []
    def scatter(left, right, bottom, top, gate):
        sx,sy=np.meshgrid(np.arange(left,right,1.65),np.arange(bottom,top,1.65))
        centers=np.column_stack((sx.ravel(),sy.ravel()))
        centers+=grass_rng.uniform(.12,1.53,centers.shape)
        centers=np.repeat(centers,grass_rng.integers(3,8,len(centers)),axis=0)
        pts=centers+grass_rng.normal(0.,.40,centers.shape)
        px,py=pts.T
        valid=(px>=left)&(px<right)&(py>=bottom)&(py<top)
        if gate:
            p=np.clip(np.rint(px+172).astype(int),0,118)
            q=np.clip(np.rint(py-252).astype(int),0,8)
            dirt=apron[q,p,0]/255.
            light=np.full(len(px),.45)
            density=.30*smooth(3.8,6.,np.abs(px+108))*(1.-smooth(2.8,4.4,py-252))
        else:
            dirt=field_at(soil,px,py)
            under=field_at(canopy,px,py)
            light=1.-under
            shade_moss=field_at(moss,px,py)
            patches=smooth(-.95,.85,field_at(shoulder*.40+humps*.60,px,py))
            density=field_at(influence,px,py)*(.16+.82*patches)*(.95-.65*shade_moss)*smooth(.2,2.,py-y0)
        slope_y,slope_x=np.gradient(terrain.astype(float)/100.)
        at=(np.clip(np.rint(py+320).astype(int),0,1024),np.clip(np.rint(px+624).astype(int),0,1024))
        valid &= (np.hypot(slope_x[at],slope_y[at])<.56)&(dirt<.48)
        valid &= grass_rng.random(len(px)) < density*(1.-smooth(.08,.48,dirt))
        for tree,radius in obstacles:
            valid &= tree.query(pts,k=1)[0]>radius
        light=light[valid]
        draw=grass_rng.random(len(light))
        slot=np.where(draw<(.58+.16*(1.-light)),12,13)
        if not gate: slot=np.where((light>.35)&(draw>1.-.11*light**2),14,slot)
        outpts=np.empty(len(slot),POINT)
        outpts['x'],outpts['y']=pts[valid].T*100.
        outpts['yaw']=grass_rng.uniform(0.,360.,len(slot))
        outpts['size']=np.choose(slot-12,[19.,32.,46.])*grass_rng.uniform(.76,1.18,len(slot))
        outpts['slot']=slot
        extra.append(outpts)
    scatter(x0,x0+width,y0,y0+length,False)
    # Only the open land outside the gate, up to 4.4 m from the forest edge.
    scatter(-126.,-90.,252.,256.4,True)
    points=np.concatenate([kept,*extra])
    points.tofile(out/'planting.bin')
    info=dict(seed=SEED,bounds_m=[[x0,y0],[x0+width,y0+length]],gate_apron_m=8,
              grass_by_slot={key:int((points['slot']==i).sum()) for i,key in enumerate(('low','spreading','tall'),12)},
              gate_grasses=len(extra[1]),protected_road_points_removed=int(painted_lane.sum()),
              baseline=str(base),sample_area_m2=width*length)
    (out/'generation.json').write_text(json.dumps(info,indent=2),encoding='utf8')


if __name__=='__main__':
    make_sample(Path(sys.argv[1]),Path(sys.argv[2]))
