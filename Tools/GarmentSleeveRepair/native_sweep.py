"""Continuous native-arm cross sections for the two strongly bent bind poses."""
import math
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

def unit(v):return v/max(np.linalg.norm(v),1e-12)
def side_of(w):return max(('l','r'),key=lambda s:sum(v for n,v in w.items() if n.endswith('_'+s)))
def bind(skin,tri,hit,p):
    a,b,c=p[tri];v0=b-a;v1=c-a;v2=np.asarray(hit)-a
    den=(v0@v0)*(v1@v1)-(v0@v1)**2
    if abs(den)<1e-12:return skin['weights'][tri[0]]
    b1=((v1@v1)*(v2@v0)-(v0@v1)*(v2@v1))/den;b2=((v0@v0)*(v2@v1)-(v0@v1)*(v2@v0))/den
    bary=np.maximum([1-b1-b2,b1,b2],0);bary/=bary.sum();out={}
    for i,k in enumerate(tri):
        for n,v in skin['weights'][k].items():out[n]=out.get(n,0)+float(bary[i]*v)
    pairs=sorted(out.items(),key=lambda kv:-kv[1])[:8];total=sum(v for n,v in pairs)
    return {n:v/total for n,v in pairs if v>1e-8}

def surface(skin,side,end_from_wrist,segments=80,rows=64):
    p=np.array(skin['positions']);fs=np.array([f for f,m in zip(skin['triangles'],skin['triangle_materials']) if m in (0,1,3) and all(side_of(skin['weights'][i])==side for i in f)])
    b=skin['bones'];a,e,w=[np.array(b[n+'_'+side]['position']) for n in ('upperarm','lowerarm','hand')]
    up=unit(e-a);low=unit(w-e);ul=np.linalg.norm(e-a);ll=np.linalg.norm(w-e)
    seed=unit(np.cross(up,low))
    if np.linalg.norm(seed)<.5:seed=unit(np.cross(up,[0,1,0]))
    blend=min(8.,ll-end_from_wrist-.5);stations=np.linspace(-ul+1,ll-end_from_wrist,rows)
    tree=BVHTree.FromPolygons([Vector(v) for v in p],fs.tolist(),all_triangles=True)
    radii=np.zeros((rows,segments));weights={};centers=[];directions=[]
    for j,t in enumerate(stations):
        if t<=-blend:center=e+up*t;axis=up
        elif t>=blend:center=e+low*t;axis=low
        else:
            q=(t+blend)/(2*blend);center=(1-q)**2*(e-up*blend)+2*q*(1-q)*e+q*q*(e+low*blend);axis=unit(up*(1-q)+low*q)
        cross=unit(np.cross(axis,seed));centers.append(center)
        dirs=[]
        for i in range(segments):
            direction=seed*math.cos(math.tau*i/segments)+cross*math.sin(math.tau*i/segments);dirs.append(direction)
            origin=center.copy();travel=0.;hits=[]
            for _ in range(8):
                hit,normal,fi,distance=tree.ray_cast(Vector(origin),Vector(direction),16-travel)
                if hit is None:break
                travel=float((np.array(hit)-center)@direction);tri=p[fs[fi]]
                if -np.cross(tri[1]-tri[0],tri[2]-tri[0])@direction>0:hits.append((travel,hit,fi))
                origin=np.array(hit)+direction*.002;travel+=.002
            if hits:
                rad,hit,fi=max(hits,key=lambda h:h[0]);radii[j,i]=rad;weights[j,i]=bind(skin,fs[fi],hit,p)
        directions.append(dirs)
    for j in range(rows):
        for i in range(segments):
            if radii[j,i]>0:continue
            choices=[k for k in range(rows) if radii[k,i]>0]
            if not choices:raise RuntimeError('Missing native section '+side)
            k=min(choices,key=lambda k:abs(k-j));radii[j,i]=radii[k,i];weights[j,i]=weights[k,i]
    # Soften the native elbow's tiny creases into cloth-scale folds.
    for _ in range(4):
        radial=(np.roll(radii,1,1)+2*radii+np.roll(radii,-1,1))/4
        radial[1:-1]=(radial[:-2]+2*radial[1:-1]+radial[2:])/4
        radii=.5*radii+.5*radial
    centers=np.array(centers);directions=np.array(directions)
    pp=(centers[:,None,:]+directions*radii[:,:,None]).reshape(-1,3)
    fs=[]
    for j in range(rows-1):
        for i in range(segments):
            ids=[j*segments+i,j*segments+(i+1)%segments,(j+1)*segments+(i+1)%segments,(j+1)*segments+i]
            for ci in ((0,1,2),(0,2,3)):
                face=[ids[k] for k in ci];pts=pp[face]
                if np.cross(pts[1]-pts[0],pts[2]-pts[0])@directions[j,i]>0:face=face[::-1]
                fs.append(face)
    fs=np.array(fs);edges={}
    for face in fs:
        for x,y in zip(face,np.roll(face,-1)):
            key=tuple(sorted((int(x),int(y))));edges.setdefault(key,[]).append((int(x),int(y)))
    boundary=[es[0] for es in edges.values() if len(es)==1]
    return pp,fs,[weights[j,i] for j in range(rows) for i in range(segments)],boundary,directions.reshape(-1,3)
