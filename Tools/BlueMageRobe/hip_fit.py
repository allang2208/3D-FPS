"""Native waist/hip yoke and gradual A-line fall; identical render/proxy transform."""
import json
from pathlib import Path
import numpy as np
from geometry import finish,read,write,smooth
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/BlueMageRobe20261018';OUT=R/'HipFit20261019'
def hull(points):
    pts=sorted(set(map(tuple,points)))
    def cross(o,a,b):return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
    lower=[];upper=[]
    for seq,target in ((pts,lower),(pts[::-1],upper)):
        for point in seq:
            while len(target)>=2 and cross(target[-2],target[-1],point)<=0:target.pop()
            target.append(point)
    return np.array(lower[:-1]+upper[:-1])
def radial(h,angles):
    edge=np.roll(h,-1,axis=0)-h;normal=np.c_[edge[:,1],-edge[:,0]];direction=np.c_[np.sin(angles),-np.cos(angles)];limit=((h-[0,1])*normal).sum(1);den=direction@normal.T
    return np.min(np.where(den>1e-9,limit[None,:]/np.maximum(den,1e-9),1e6),axis=1)
def apply(d,skin):
    if d.get('hip_fit_revision')=='20261019-v1':return d
    points=np.array(d['positions']);faces=np.array(d['triangles']);mats=np.array(d['triangle_materials']);uv=np.array(d['uv']);dims=d['cloth_dimensions'];waist,height,scale=dims['waist_cm'],dims['length_cm'],dims['scale'];native=np.array(skin['positions']);hip_end=24.*scale;angles=np.arange(128)*2*np.pi/128
    drops=np.linspace(0,hip_end,49);radii=[]
    for drop in drops:
        z=waist-drop;section=native[(np.abs(native[:,2]-z)<1.)&(np.abs(native[:,0])<27.)][:,:2]
        if len(section)<8:raise RuntimeError('Missing native hip cross-section')
        radii.append(radial(hull(section),angles))
    radii=np.array(radii)
    for _ in range(2):radii[1:-1]=.25*radii[:-2]+.5*radii[1:-1]+.25*radii[2:]
    selected=np.flatnonzero(np.isin(mats,[4,9]));theta={}
    for fi in selected:
        for ci,vi in enumerate(faces[fi]):theta[int(vi)]=(float(uv[fi,ci,0])%1)*2*np.pi
    outer=np.unique(faces[mats==4]);base=outer[:128*66];old_grid=points[base].reshape(66,128,3);old_drop=waist-old_grid[:,0,2]
    top=old_grid[0,:,:2];hem=old_grid[-1,:,:2];center=np.array([0.,1.]);dirs=np.c_[np.sin(angles),-np.cos(angles)]
    new_upper=[]
    for j,drop in enumerate(drops):
        ease=(.8+.5*float(smooth(drop/(8*scale))))*scale;target=center+dirs*(radii[j]+ease)[:,None];blend=float(smooth(drop/(5*scale)));new_upper.append(top*(1-blend)+target*blend)
    new_upper=np.array(new_upper);before=points.copy()
    for vi,a in theta.items():
        drop=float(np.clip(waist-points[vi,2],0,height));k=int(round(a*128/(2*np.pi)))%128
        if drop<=hip_end:new=np.array([np.interp(drop,drops,new_upper[:,k,axis]) for axis in range(2)])
        else:
            t=(drop-hip_end)/(height-hip_end);s=.75*t+.25*t*t;new=new_upper[-1,k]*(1-s)+hem[k]*s
        old=np.array([np.interp(drop,old_drop,old_grid[:,k,axis]) for axis in range(2)])
        points[vi,:2]+=new-old
    d['positions']=points.tolist();d['hip_fit_revision']='20261019-v1';d['hip_fit_contract']='Native convex hip envelope plus 0.8-1.3 cm ease; root seam fixed; gradually flared lower skirt; unchanged hem/turnback; render and physics proxy share the transform';finish(d)
    return d
if __name__=='__main__':
    rows=read(R/'input_inventory.json')['rows'];report={}
    for profile in ('Body','Body_Owner','Jason','Jason_Owner'):
        path=R/'Authored/Body'/(profile+'.json');d=read(path);skin=read(next(r['file'] for r in rows if r['profile']==profile.split('_')[0]));apply(d,skin);write(path,d);report[profile]=dict(revision=d['hip_fit_revision'],triangles=len(d['triangles']),source=d['binding_source']);print('ROBE_HIP_CONTOUR_AUTHORED',profile,flush=True)
    write(OUT/'authored.json',report)
