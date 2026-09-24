"""Offline, clustered ceramic loss. Retain the approved glaze UVs and bonded fracture style."""
import ast
import json
import math
import random
from pathlib import Path
from collections import defaultdict
import numpy as np
from mathutils import Vector
from mathutils.geometry import tessellate_polygon

BASE=Path(__file__).resolve().parents[2]
FRACTURE=BASE/'DungeonTileFracture20260922'
CFG=json.loads((FRACTURE/'Config/fracture.json').read_text())
BEDCFG=json.loads((BASE/'DungeonWallRelief20260922/Config/surface.json').read_text())
TW=CFG['tile_width_m'];TH=CFG['tile_height_m']
# Reuse the accepted fracture profile and ceramic thickness, without executing its producer.
tree=ast.parse((FRACTURE/'Scripts/author_fractures.py').read_text(encoding='utf-8'))
nodes=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and
       n.name in ('inset','remnant_outline','Build')]
exec(compile(ast.Module(body=nodes,type_ignores=[]),str(FRACTURE/'Scripts/author_fractures.py'),'exec'))

def donor_tiles(panels):
    cells=defaultdict(list)
    for panel,(width,records,name,lo) in enumerate(panels):
        for points,material,smooth in records:
            if 'Ceramic' not in material:continue
            t=sum(p[0] for p in points)/len(points);z=sum(p[2] for p in points)/len(points)
            col=math.floor(t/TW);row=round((z-.24)/TH)
            if not 0<=row<=8:continue
            # Never transplant a wall-wide grout strip or a cut edge as a tile.
            if min(p[0] for p in points)<col*TW+.001 or max(p[0] for p in points)>(col+1)*TW-.001:continue
            if min(p[2] for p in points)<.24+row*TH-.077 or max(p[2] for p in points)>.24+row*TH+.077:continue
            cells[(panel,col,row)].append((points,material,smooth))
    donors=[]
    for (_,col,row),records in sorted(cells.items()):
        area=0;front=[];glaze=None
        for points,material,smooth in records:
            if 'Atlas' not in material:continue
            a=abs(sum(points[i][0]*points[(i+1)%len(points)][2]-points[(i+1)%len(points)][0]*points[i][2] for i in range(len(points))))*.5
            area+=a
            if a>.0001:front.extend(points);glaze=material
        if area<.044 or not front:continue
        matrix=np.array([[p[0]-col*TW,p[2]-row*TH,1] for p in front])
        values=np.array([[p[3],p[4]] for p in front])
        coefficients=np.linalg.lstsq(matrix,values,rcond=None)[0]
        normalized=[([(t-col*TW,d,z-row*TH,u,v) for t,d,z,u,v in points],mat,smooth) for points,mat,smooth in records]
        donors.append((normalized,coefficients,glaze))
        if len(donors)>=48:break
    if not donors:raise RuntimeError('No intact approved ceramic donor tiles')
    return donors

def hash_noise(x,y,seed):
    def value(ix,iy):
        n=(ix*374761393+iy*668265263+seed*69069)&0xffffffff
        n=((n^(n>>13))*1274126177)&0xffffffff
        return ((n^(n>>16))&0xffff)/32767.5-1
    ix=math.floor(x);iy=math.floor(y);fx=x-ix;fy=y-iy
    fx=fx*fx*(3-2*fx);fy=fy*fy*(3-2*fy)
    return (value(ix,iy)*(1-fx)+value(ix+1,iy)*fx)*(1-fy)+(value(ix,iy+1)*(1-fx)+value(ix+1,iy+1)*fx)*fy

def clustered_cells(length,seed):
    rng=random.Random(seed);lobes=[];groups=[]
    # Exponential gaps and optional intact walls avoid an evenly spaced row of stamps.
    if rng.random()>.16:
        t=rng.uniform(.15,2.1)
        while t<length:
            kind=rng.choices(('impact','damp','small'),(.50,.28,.22))[0]
            z=rng.uniform(.42,1.37) if kind!='damp' else rng.uniform(.17,.48)
            rx=rng.uniform(.40,1.12) if kind!='small' else rng.uniform(.12,.35)
            rz=rng.uniform(.22,.55) if kind!='small' else rng.uniform(.10,.22)
            if kind=='damp':rx*=1.4;rz*=.7
            groups.append((t,z,rx,rz,kind))
            for j in range(rng.randint(2,5)):
                lobes.append((t+rng.uniform(-.45,.45)*rx,z+rng.uniform(-.5,.5)*rz,
                              rx*rng.uniform(.5,1),rz*rng.uniform(.5,1),rng.uniform(-.65,.65)))
            t+=max(.8,rng.expovariate(1/3.8))
    def damaged(t,z):
        warp=.08*hash_noise(t*3.1,z*3.1,seed)+.035*hash_noise(t*10,z*10,seed+7)
        for x,y,rx,rz,angle in lobes:
            dx=t-x;dy=z-y;c=math.cos(angle);s=math.sin(angle)
            q=((dx*c+dy*s)/rx)**2+((-dx*s+dy*c)/rz)**2
            if q<1+warp*3:return True
        return False
    coverage={}
    for col in range(math.ceil(length/TW)):
        for row in range(9):
            count=sum(damaged(col*TW+.003+(sx+.5)*.304/6,.164+row*TH+(sy+.5)*.152/4)
                      for sx in range(6) for sy in range(4))
            coverage[col,row]=1-count/24
    return coverage,groups

def records_for_wall(panels,length,seed,donors=None):
    rng=random.Random(seed);donors=donors or donor_tiles(panels)
    coverage,groups=clustered_cells(length,seed);records=[]
    bed='V2_WallReliefBed';finish='V2_WallReliefFinish';core='V2_CeramicFractureCore'
    # One continuous mineral bed, never floating decal planes or per-cluster raised sheets.
    def height(t,z):
        return .1255+.0016*hash_noise(t*4,z*4,seed)+.0006*hash_noise(t*11,z*11,seed+1)
    nx=max(1,math.ceil(length/.05));nz=29
    for ix in range(nx):
        a=length*ix/nx;b=length*(ix+1)/nx
        for iz in range(nz):
            z0=.155+1.435*iz/nz;z1=.155+1.435*(iz+1)/nz
            points=[(t,height(t,z),z,t/1.28,z/1.28) for t,z in ((a,z0),(a,z1),(b,z1),(b,z0))]
            records.append((points,bed,True))
    kept=0;missing=0;broken=0
    offsets={'left':(-1,0),'right':(1,0),'bottom':(0,-1),'top':(0,1)}
    for (col,row),fraction in coverage.items():
        donor,coeff,glaze=rng.choice(donors)
        if fraction>.92:
            records.extend(([(t+col*TW,d,z+row*TH,u,v) for t,d,z,u,v in points],mat,smooth) for points,mat,smooth in donor)
            a=col*TW+.006;b=(col+1)*TW-.006;z0=.167+row*TH;z1=.313+row*TH
            corners=[(a,z0),(b,z0),(b,z1),(a,z1)]
            for j in range(4):
                x,z=corners[j];xx,zz=corners[(j+1)%4]
                q=[(xx,.13515,zz),(x,.13515,z),(x,height(x,z)-.002,z),(xx,height(xx,zz)-.002,zz)]
                records.append(([(t,d,h,t/1.28,h/1.28) for t,d,h in q],finish,False))
            kept+=1;continue
        eligible=[side for side,(dx,dy) in offsets.items() if coverage.get((col+dx,row+dy),0)>.92]
        if fraction<.13 or not eligible:
            missing+=1;continue
        side=rng.choice(eligible);rect=(col*TW+.003,.164+row*TH,(col+1)*TW-.003,.316+row*TH)
        outline=remnant_outline(rect,side,fraction,rng.choice((-1,0,1)),rng)
        top=inset(outline,.0004);mid=inset(outline,-.0002);bottom=inset(outline,.00035)
        front=.144;rdepth=rng.uniform(*CFG['core_thickness_m']);back=front-rdepth
        uv=lambda x,z:tuple(np.array([x-col*TW,z-row*TH,1])@coeff)
        flat=lambda x,z:(x/CFG['core_texture_size_m'],z/CFG['core_texture_size_m'])
        b=Build(('x',0,length,0,1))
        ft=lambda x,z:front;lip=lambda x,z:front-CFG['glaze_lip_m'];half=lambda x,z:front-rdepth*.48;bk=lambda x,z:back
        b.cap(top,ft,glaze,uv);b.sides(top,outline,ft,lip,glaze,uv)
        b.sides(outline,mid,lip,half,core);b.sides(mid,bottom,half,bk,core)
        b.cap(bottom,bk,core,flat,back=True)
        base=inset(bottom,-.0004);glue=lambda x,z:back+.00015;below=lambda x,z:height(x,z)-.003
        mortar=lambda x,z:(x/1.28,z/1.28)
        b.cap(bottom,glue,finish,mortar);b.sides(bottom,base,glue,below,finish,mortar)
        for face,mat,uvs in zip(b.f,b.mi,b.uv):
            records.append(([(b.v[i][0],b.v[i][1],b.v[i][2],*uvp) for i,uvp in zip(face,uvs)],mat,False))
        broken+=1
    return records,dict(seed=seed,clusters=groups,intact=kept,missing=missing,bonded_remnants=broken)
