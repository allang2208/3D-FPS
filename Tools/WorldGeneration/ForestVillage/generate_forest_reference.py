"""Extend measured forest PCG point patterns onto the R12 landform and bake its original ground varieties."""
import json
import re
import sys
from pathlib import Path
import numpy as np
from generate_slope_grass import POINT, grid_at, generate, site_hash

def sedge_points(shore,rng):
    yy,xx=np.nonzero(shore>.01)
    x=xx-624+rng.uniform(-.45,.45,xx.size); y=yy-320+rng.uniform(-.45,.45,yy.size)
    wet=grid_at(shore,x,y)
    clump=(1+np.sin(x*.32+y*.19)*np.cos(y*.17-x*.39))*.5
    select=rng.random(x.size)<((1-wet)*(.03+.06*clump)+wet*(.24+.42*clump))
    return x[select],y[select],rng.uniform(0,360,select.sum()),rng.uniform(.75,1.1,select.sum())

def planting(out, donor):
    grass=out/'Grass'
    report=json.loads((donor/'reference.json').read_text())
    paint=np.fromfile(out/'paint.rg8','u1').reshape(1025,1025,2)[...,0].astype('f4')/255.
    shore=np.fromfile(grass/'pond_shore.u8','u1').reshape(1025,1025).astype('f4')/255.
    depth=np.fromfile(grass/'pond_depth.u8','u1').reshape(4097,4097).astype('f4')
    vx,vy=json.loads((out/'hill.json').read_text())['site_min_m']
    clear_file=out/'quarry-clear.u8'
    quarry=np.fromfile(clear_file,'u1').reshape(1025,1025) if clear_file.exists() else None
    def outside_yard(x,y):
        if quarry is None: return True
        ids=np.floor((x+624)*4).astype('u4')*np.uint32(4099)+np.floor((y+320)*4).astype('u4')
        remaining=1.-grid_at(quarry,x,y)/255.
        return (site_hash(ids)&65535)/65536.<remaining
    rng=np.random.default_rng(237855)
    pieces=[]
    paths=[]
    counts={}
    def extra(path):
        paths.append(path)
        return 15+len(paths)
    def place(x,y,yaw,scale,slot,group,shore_only=False):
        x,y=np.asarray(x),np.asarray(y)
        rows=np.empty(x.size,POINT)
        rows['x'],rows['y'],rows['yaw'],rows['size'],rows['slot']=x*100.,y*100.,yaw,scale,slot
        outside=(x< -252)|(x>252)|(y< -252)|(y>252)
        allowed=(x>=-624)&(x<400)&(y>=-320)&(y<704)&~((x>vx-1)&(x<vx+119)&(y>vy-1)&(y<vy+146))
        allowed &= outside_yard(x,y)
        allowed &= grid_at(paint,x,y)<(.05 if slot<4 else .25)
        dep=grid_at(depth,x,y,step=.25)
        if shore_only:
            allowed &= (grid_at(shore,x,y)>.01)&((dep<=0)|((dep<=9)&(rng.random(x.size)<.20)))
        else:
            allowed &= outside & (dep<=0)
        pieces.append(rows[allowed])
        counts[group]=counts.get(group,0)+int(allowed.sum())

    for group,meshes in report['pcg'].items():
        canopy=group.endswith('Canopy')
        width,height,left,bottom=(504.,504.,-252.,-252.) if canopy else (195.,102.,-187.5,150.)
        for name,(_,path) in meshes.items():
            if canopy: slot=0 if name.endswith('04') else 1
            elif group.endswith('Hazel'): slot=2 if name.endswith('01') else 3
            else: slot=extra(path)
            a=np.fromfile(donor/(name+'.f32'),'<f4').reshape(-1,8)
            dx=a[:,0]*.01-left; dy=a[:,1]*.01-bottom
            for j in range(int(np.floor((-320-bottom)/height)),int(np.ceil((704-bottom)/height))):
                for i in range(int(np.floor((-624-left)/width)),int(np.ceil((400-left)/width))):
                    fx,fy=(-1 if i%2 else 1),(-1 if j%2 else 1)
                    x=left+i*width+(dx if fx==1 else width-dx)
                    y=bottom+j*height+(dy if fy==1 else height-dy)
                    rad=np.radians(a[:,3])
                    yaw=np.degrees(np.arctan2(fy*np.sin(rad),fx*np.cos(rad)))
                    place(x,y,yaw,a[:,4],slot,group)
    # LandscapeGrass uses a jittered lattice, random yaw and uniform scale for these varieties.
    sy,sx=np.gradient(shore)
    for path,density,_,uniform,_,_,align,cull in report['grass']:
        size_range=[float(v) for v in re.search(r'min: ([\d.]+), max: ([\d.]+)',uniform).groups()]
        slot=extra(path)
        step=np.sqrt(100./density)
        cy,cx=np.mgrid[0:int(np.ceil(1024/step)),0:int(np.ceil(1024/step))]
        x=-624+(cx.ravel()+rng.uniform(.05,.95,cx.size))*step
        y=-320+(cy.ravel()+rng.uniform(.05,.95,cx.size))*step
        yaw=rng.uniform(-180,180,x.size)
        if 'relu7' in path or 'rioqm' in path:
            dx,dy=grid_at(sx,x,y),grid_at(sy,x,y)
            strand=(dx*dx+dy*dy)>.008
            yaw[strand]=np.degrees(np.arctan2(dy[strand],dx[strand])+np.pi*.5+rng.uniform(-.57,.57,strand.sum()))
        place(x,y,yaw,rng.uniform(*size_range,x.size),slot,path.split('.')[-1])
    # Retain the established non-woodland road dressing and its decal footprint.
    prev=np.fromfile(out.parent/'ReferenceHill-R12/planting.bin',POINT)
    prev=prev[np.isin(prev['slot'],[10,11])]
    px,py=prev['x']*.01,prev['y']*.01
    pieces.append(prev[(grid_at(depth,px,py,step=.25)==0)&outside_yard(px,py)])
    np.concatenate(pieces).tofile(out/'planting.bin')
    # The forest floor shares habitat with rocks, twigs and shrubs. Thin only under trees.
    cover=generate(out,grass,out.parent/'WildGrass-oilox20',verge_in_green=True,understory=True)
    bank='/Game/WorldGeneration/TemperateHills/RiverEcologyDense/SM_RiverDense_grass_04_03_mesh.SM_RiverDense_grass_04_03_mesh'
    slot=extra(bank)
    x,y,yaw,scale=sedge_points(shore,rng)
    place(x,y,yaw,scale,slot,'Bank sedge',True)
    with (grass/'planting.bin').open('ab') as stream:
        pieces[-1].tofile(stream)
    (grass/'reference-meshes.txt').write_text('\n'.join(paths)+'\n',encoding='utf8')
    (out/'forest-density.json').write_text(json.dumps(dict(placed=counts,grass=cover,extra_meshes=paths),indent=2))

if __name__=='__main__': planting(Path(sys.argv[1]),Path(sys.argv[2]))
