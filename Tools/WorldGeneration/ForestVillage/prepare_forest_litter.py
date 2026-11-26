"""Bake independent road-side leaf drifts and deterministic deadwood points for the official PCG graph."""
import json
import math
import shutil
import sys
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.spatial import cKDTree
from generate_slope_grass import POINT,grid_at
from prepare_gate_road_surface import ORIGIN,STEP,smooth
from leaf_drift_edges import drift_alpha,broken_shoulder_edges
from forest_wood_retirement import active_points,retired_meshes

def leaf_atlas(src,out=None):
    out=src if out is None else out
    out.mkdir(parents=True,exist_ok=True)
    size=1024;pad=16
    color=Image.new('RGBA',(size*2,size*2));surface=Image.new('RGB',color.size)
    selected=[x for x in json.loads((src/'selection.json').read_text()) if x['role']=='leaves']
    if len(selected)!=4:raise RuntimeError('Four distinct leaf scans required')
    for i,item in enumerate(selected):
        root=src/'Fab'/item['uid']
        def read(ch,mode):
            with Image.open(next(root.glob('*_2K_'+ch+'.jpg'))) as f:return f.convert(mode)
        rgba=read('BaseColor','RGB')
        original_alpha=read('Opacity','L')
        alpha=original_alpha.resize((size-2*pad,size-2*pad),Image.Resampling.LANCZOS)
        # Downsample RGB with the original alpha before writing the final irregular silhouette.
        rgba.putalpha(original_alpha)
        rgba=rgba.resize(alpha.size,Image.Resampling.LANCZOS)
        rgba.putalpha(drift_alpha(alpha,item['uid']))
        normal=read('Normal','RGB')
        detail=Image.merge('RGB',(normal.getchannel('R'),normal.getchannel('G'),read('Roughness','L')))
        for canvas,tile in ((color,rgba),(surface,detail)):
            pixels=np.asarray(tile.resize((size-2*pad,size-2*pad),Image.Resampling.LANCZOS))
            pixels=np.pad(pixels,((pad,pad),(pad,pad),(0,0)),mode='edge')
            canvas.paste(Image.fromarray(pixels),(i%2*size,i//2*size))
    color.save(out/'T_ShoulderLeafColor.png');surface.save(out/'T_ShoulderLeafSurface.png')

def road_line(terrain,key):
    p=np.loadtxt(terrain/(key+'-road.csv'),delimiter=',',skiprows=1)[:,:2]
    good=np.r_[True,np.linalg.norm(np.diff(p,axis=0),axis=1)>1.e-5]
    p=p[good];dist=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))]
    axis=np.gradient(p,axis=0);axis/=np.maximum(np.linalg.norm(axis,axis=1,keepdims=True),.001)
    return p,dist,axis

def leaf_field(terrain,out,rng=None):
    out.mkdir(exist_ok=True,parents=True)
    if rng is None:rng=np.random.default_rng(237855+29)
    grass=terrain/'Grass'
    x0,y0=ORIGIN
    gy,gx=np.indices((256,1024));fx=x0+(gx+.5)*STEP;fy=y0+(gy+.5)*STEP
    xy=np.column_stack((fx.ravel(),fy.ravel()))
    paths=[road_line(terrain,k) for k in ('gate','quarry')]
    route=cKDTree(np.vstack([p for p,_,_ in paths]))
    near=route.query(xy)[0].reshape(fx.shape)
    field=np.zeros(fx.shape,dtype=float)
    leaf_banks=[]
    for p,sta,axis in paths:
        for side in (-1,1):
            at=rng.uniform(.5,3.);n=0
            while at<sta[-1]:
                j=min(np.searchsorted(sta,at),len(p)-1);v=axis[j];cross=np.array([-v[1],v[0]])
                center=p[j]+side*cross*rng.uniform(2.3,4.1)
                length,width=rng.uniform(1.5,5.5),rng.uniform(.65,1.7)
                reach=2*max(length,width); cx,cy=center
                a=max(0,int((cx-x0-reach)/STEP));b=min(1024,int((cx-x0+reach)/STEP)+1)
                c=max(0,int((cy-y0-reach)/STEP));d=min(256,int((cy-y0+reach)/STEP)+1)
                if a<b and c<d:
                    dx=fx[c:d,a:b]-cx;dy=fy[c:d,a:b]-cy
                    radius=((dx*v[0]+dy*v[1])/length)**2+((dx*cross[0]+dy*cross[1])/width)**2
                    island=(1.-smooth(.05,2.0,radius))*rng.uniform(.58,1.)
                    field[c:d,a:b]=np.maximum(field[c:d,a:b],island)
                at+=rng.uniform(2.0,8.8);n+=1
            leaf_banks.append(n)
    town=json.loads((terrain/'hill.json').read_text())['site_min_m']
    def town_gap(x,y):
        return np.hypot(np.maximum(np.maximum(town[0]-x,x-town[0]-118.),0),np.maximum(np.maximum(town[1]-y,y-town[1]-145.),0))
    wet=np.fromfile(grass/'pond_wet.u8','u1').reshape(4097,4097)
    quarry=np.fromfile(terrain/'quarry-clear.u8','u1').reshape(1025,1025)
    field*=broken_shoulder_edges(near,fx,fy)*smooth(.1,2.4,town_gap(fx,fy))
    field*= (1.-grid_at(quarry,fx,fy)/255.)*(1.-grid_at(wet,fx,fy,step=.25)/255.)
    Image.fromarray(np.rint(255*field).clip(0,255).astype('u1')).save(out/'T_ShoulderLeafField.png')

    return paths,route,town_gap,wet,quarry,leaf_banks

def prepare(terrain,src,out):
    out.mkdir(exist_ok=True,parents=True)
    rng=np.random.default_rng(237855+29)
    retired=retired_meshes()
    woods=[row for row in json.loads((src/'wood-palette.json').read_text()) if row['mesh'] not in retired]
    grass=terrain/'Grass';palette=(grass/'reference-meshes.txt').read_text(encoding='utf-8-sig').splitlines()
    original,palette=active_points(np.fromfile(grass/'planting.bin',POINT),palette)
    prior_wood={16+i for i,path in enumerate(palette) if '/WoodlandDressing/Wood/' in path}
    slots=[]
    for row in woods:
        if row['mesh'] not in palette:palette.append(row['mesh'])
        slots.append(16+palette.index(row['mesh']))
    paths,route,town_gap,wet,quarry,leaf_banks=leaf_field(terrain,out,rng)

    height=np.fromfile(terrain/'region.i16','<i2').reshape(1025,1025)*.01
    grade=np.hypot(*np.gradient(height));shore=np.fromfile(grass/'pond_shore.u8','u1').reshape(height.shape)/255.
    if prior_wood:original=original[~np.isin(original['slot'],list(prior_wood))]
    canopy=np.vstack([np.c_[original['x'],original['y']][original['slot']<2]*.01,
                      np.fromfile(grass/'harvest-trees.f32','<f4').reshape(-1,3)[:,:2]*.01,
                      np.fromfile(grass/'study_trees.f32','<f4').reshape(-1,3)[:,:2]])
    trees=cKDTree(canopy)
    granites={16+i for i,path in enumerate(palette) if '/Granite/' in path}
    stone=original[np.isin(original['slot'],list(granites))]
    rocks=cKDTree(np.column_stack((stone['x'],stone['y']))*.01)
    chosen=[];taken={};roles={}
    for i,wood in enumerate(woods):roles.setdefault(wood['role'],[]).append((i,wood))
    # Sample a conservative oriented footprint. Long objects cannot cross a bend, a pond or the town perimeter.
    def place(x,y,yaw,role):
        if role not in roles or not (-618<x<394 and -314<y<698):return False
        i,wood=roles[role][rng.integers(len(roles[role]))]
        sx,sy,_=wood['size_cm'];scale=rng.uniform(.80,1.12)
        half=np.hypot(sx,sy)*scale*.005
        width=min(sx,sy)*scale*.005
        if role=='stump':half=width=max(sx,sy)*scale*.005
        ang=math.radians(yaw);cs,sn=math.cos(ang),math.sin(ang)
        u,v=np.meshgrid(np.linspace(-half,half,max(3,int(2*half/1.3)+1)),[-width,0.,width])
        xx=x+u.ravel()*cs-v.ravel()*sn; yy=y+u.ravel()*sn+v.ravel()*cs
        if xx.min()<-624 or xx.max()>400 or yy.min()<-320 or yy.max()>704:return False
        probe=np.c_[xx,yy]
        if town_gap(xx,yy).min()<1.8 or grid_at(quarry,xx,yy).max()>20 or grid_at(wet,xx,yy,step=.25).max()>10:return False
        if route.query(probe)[0].min()<(2.55 if role=='branch' else 3.8):return False
        if trees.query(probe)[0].min()<(.38 if role=='branch' else .72) or rocks.query(probe)[0].min()<.85:return False
        if grid_at(grade,xx,yy).max()>(.81 if role=='branch' else .58):return False
        radius=max(1.,half)
        bx,by=math.floor(x/16),math.floor(y/16)
        reach=int(math.ceil((radius+35.)/16))
        for tx in range(bx-reach,bx+reach+1):
            for ty in range(by-reach,by+reach+1):
                if any(math.hypot(x-ox,y-oy)<radius+old+1. for ox,oy,old in taken.get((tx,ty),())):return False
        taken.setdefault((bx,by),[]).append((x,y,radius))
        chosen.append((x*100.,y*100.,yaw,scale,slots[i]))
        return True
    # Reserve the rarer large silhouettes first. Advance along the route in irregular lengths on either side.
    for p,sta,axis in paths:
        for lo,hi,variants,offset in [(26.,48.,['large','fallen','pine'],(8.,19.)),(4.,12.,['branch','branch','log','stump'],(4.2,10.))]:
            at=rng.uniform(1.,lo)
            while at<sta[-1]:
                j=min(np.searchsorted(sta,at),len(p)-1);v=axis[j]
                side=rng.choice([-1.,1.]);kind=rng.choice(variants)
                for trial in range(5):
                    pt=p[j]+side*np.array([-v[1],v[0]])*rng.uniform(*offset)
                    yaw=np.rad2deg(np.arctan2(v[1],v[0]))+rng.uniform(-32,32)+rng.choice([0,180])
                    if place(*pt,yaw,kind):break
                at+=rng.uniform(lo,hi)
    road_count=len(chosen)
    for role,spacing,rate in [('large',79.,.60),('pine',61.,.66),('fallen',61.,.66),('log',43.,.87),('stump',41.,.86),('branch',47.,.75)]:
        for y0 in np.arange(-320,704,spacing):
            for x0 in np.arange(-624,400,spacing):
                x,y=np.array([x0,y0])+rng.uniform(.03,.97,2)*spacing
                if x>=400 or y>=704:continue
                gap=trees.query([x,y])[0]
                shade=1.-smooth(5.,32.,gap)
                damp=float(shore[min(1024,round(y+320)),min(1024,round(x+624))])
                chance=rate*(.13+.87*shade)*(min(1.,.72+.50*damp) if role in ('log','stump') else 1.)
                if rng.random()<chance:place(x,y,rng.uniform(-180.,180.),role)
    records=np.array(chosen,dtype=POINT)
    with (out/'planting.bin').open('wb') as stream:original.tofile(stream);records.tofile(stream)
    (out/'reference-meshes.txt').write_text('\n'.join(palette)+'\n',encoding='utf-8')
    for k in ('harvest-trees.f32','study-granite.i32'):shutil.copy2(grass/k,out/k)
    summary=dict(leaf_drift_candidates=leaf_banks,wood_candidates=len(chosen),roadside_candidates=road_count,
                 by_mesh={v['mesh']:int(np.count_nonzero(records['slot']==slots[i])) for i,v in enumerate(woods)})
    (out/'distribution.json').write_text(json.dumps(summary,indent=2))
    from landscape_theme_points import store
    store(out,terrain,out/'Themes',road_count,len(chosen))
    return summary

if __name__=='__main__':
    src,terrain,out=map(Path,sys.argv[1:4])
    if '--leaves-only' in sys.argv[4:]:
        leaf_atlas(src,out)
        leaf_field(terrain,out/'Dressing')
    else:
        if '--points-only' not in sys.argv[4:]:leaf_atlas(src)
        prepare(terrain,src,out)
