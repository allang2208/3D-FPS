"""Seat the smith's neck facing, narrow placket and crossing straps on the dressed shell."""
import json, math, gzip
from pathlib import Path
import numpy as np
from scipy.ndimage import gaussian_filter1d
from scipy.spatial import cKDTree

root=Path(__file__).resolve().parents[3]/'SourceAssets'
out=root/'VillageBlacksmithNPC20261118/BodyOutfit'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
d=read(out/'outfit.json')
p=np.array(d['positions']);f=np.array(d['triangles']);w=d['weights']
rig=read(root/'JasonStrong20261117/R3_ArmsRefined/AnatomyReview/derived_saved_mesh.json')
r4=np.array(read(root/'JasonStrong20261117/R4_PoseRefined/Review/forms.json')['base'])
rt=np.array(rig['triangles'])[np.isin(rig['triangle_materials'],[0,1,3,5])]
head=json.loads(gzip.decompress((out.parent/'HeadHair/face.json.gz').read_bytes()))
hp=np.array(head['p']);ht=np.array(head['tri'])[np.array(head['m'])==1]
body_cloud=np.concatenate([r4[rt],hp[ht]])
rb=np.unique(rt);hb=np.unique(ht);bind_cloud=np.concatenate([r4[rb],hp[hb]])
tree=cKDTree(bind_cloud)
bind_rows=[rig['weights'][i] for i in rb]+[head['w'][i] for i in hb]
def weighted(pt):
    distances,indices=tree.query(pt,k=4);fac=1/np.maximum(distances,.05)**2;fac/=sum(fac)
    result={}
    for i,k in zip(indices,fac):
        for b,s in bind_rows[i]:result[b]=result.get(b,0)+s*k
    rows=sorted(result.items(),key=lambda row:-row[1])[:8];total=sum(x[1] for x in rows)
    return [[idx,round(a/total,7)] for idx,a in rows]
def section(cloud,axis,value):
    v=cloud[:,:,axis]-value
    ids=(v.min(1)<=0)&(v.max(1)>0);cloud=cloud[ids];v=v[ids]
    j=np.arange(len(v));cross=(v>0)!=(np.roll(v,-1,axis=1)>0)
    a,b=np.where(cross)
    k=(b+1)%3
    t=(-v[a,b]/(v[a,k]-v[a,b]))[:,None]
    hit=cloud[a,b]+t*(cloud[a,k]-cloud[a,b])
    return hit.reshape(-1,2,3) if len(hit) else np.empty((0,2,3))
def radii(seg,center,ray):
    perp=np.array([-ray[1],ray[0]])
    v=seg-center
    dist=v@perp
    hit=(dist[:,0]<0)!=(dist[:,1]<0)
    v=v[hit];dist=dist[hit]
    t=-dist[:,0]/(dist[:,1]-dist[:,0])
    rr=(v[:,0]+(v[:,1]-v[:,0])*t[:,None])@ray
    return rr[rr>0]
def part(name):
    a,i,b,j=d['parts'][name];return a,i,b,j
def grid(name,rows,cols):
    a,i,b,j=part(name);return p[a:b].reshape(rows,cols,3)
def update(name,coords):
    a,i,b,j=part(name);p[a:b]=coords.reshape(-1,3)
    for k in range(a,b): w[k]=weighted(p[k])
    ids=f[i:j];pts=p[ids]
    normals=np.cross(pts[:,2]-pts[:,0],pts[:,1]-pts[:,0])
    sn=np.zeros((b-a,3))
    for c in range(3):np.add.at(sn,ids[:,c]-a,normals)
    sn/=np.maximum(np.linalg.norm(sn,axis=1,keepdims=True),1e-9)
    d['normals'][i:j]=sn[ids-a].round(6).tolist()
def surface(names):
    return np.concatenate([p[f[part(n)[1]:part(n)[3]]] for n in names])
yoke=grid('Workshirt yoke',16,96).copy()
angles=np.arange(96)*math.tau/96;ray=np.stack([np.sin(angles),np.cos(angles)],axis=1);origin=np.array([0.,-.4])
outer=np.linalg.norm(yoke[0,:,:2]-origin,axis=1)
z0=gaussian_filter1d(yoke[0,:,2],1.2,mode='wrap')
notch=np.exp(-(np.minimum(angles,math.tau-angles)/.25)**2)
z1=152.65-.60*np.cos(angles)-1.55*notch
collar_skin=body_cloud[(body_cloud[:,:,2].max(1)>135)&(body_cloud[:,:,2].min(1)<156)]
levels=np.arange(135.,156.01,.25)
profile=[]
for z in levels:
    xy=section(collar_skin,2,z)[:,:,:2]
    row=[]
    for dr in ray:
        hits=radii(xy,origin,dr)
        near=hits[(hits>1.5)&(hits<27)]
        if len(near):
            closest=near.min()
            row.append(near[near<closest+.8].max())
        else:row.append(5.)
    profile.append(gaussian_filter1d(row,.8,mode='wrap'))
profile=np.array(profile)
for j,t in enumerate(np.linspace(0,1,16)):
    z=z0*(1-t)+z1*t
    radial=np.array([np.interp(z[i],levels,profile[:,i]) for i in range(96)])
    # Seat the outer edge against the existing shirt, then follow skin to the neck opening.
    blend=(1-t)**4
    radial=(1-blend)*(radial+.47)+blend*outer
    yoke[j,:,:2]=origin+ray*radial[:,None];yoke[j,:,2]=z
update('Workshirt yoke',yoke)
facing=[yoke[-1]+np.column_stack((ray*wide,np.full(96,rise))) for wide,rise in ((.36,-.12),(.22,.08),(.03,.13),(-.08,.08),(-.09,-.12))]
update('Neck opening facing',np.array(facing))
cloth=surface(['shirt','Workshirt yoke'])
def face_y(cloud,x,z,back=False):
    seg=section(cloud,0,x)[:,:,[1,2]]
    rr=radii(seg,np.array([0,z]),np.array([-1.,0.]) if back else np.array([1.,0.]))
    rr=rr[rr<32]
    return (-1 if back else 1)*rr.max() if len(rr) else np.nan
for side in (-1,1):
    coords=grid('Short shirt placket '+str(side),20,5).copy()
    for j,t in enumerate(np.linspace(0,1,20)):
        z=140.2+t*10.0
        for k,s in enumerate(np.linspace(-.46,.46,5)):
            x=side*(.48+.42*t*t)+s
            coords[j,k]=[x,face_y(cloth,x,z)+.17,z]
    for k in range(5):
        row=coords[:,k,1];valid=np.isfinite(row);row[:]=gaussian_filter1d(np.interp(np.arange(20),np.flatnonzero(valid),row[valid]),.7)
    update('Short shirt placket '+str(side),coords)
outer_shell=surface(['shirt','Workshirt yoke','Apron bib and skirt'])
for sign in (-1,1):
    name='Bib strap '+str(sign)
    a,_,b,_=part(name);rows=(b-a)//5
    ribbon=np.zeros((rows,5,3))
    arc_count=36
    for col,dx in enumerate(np.linspace(-1.22,1.22,5)):
        x=sign*8.5+dx;seg=section(outer_shell,0,x)[:,:,[1,2]];center=np.array([0,131.])
        sweep=np.linspace(.18,2.56,arc_count);distances=[]
        for angle in sweep:
            dr=np.array([math.cos(angle),math.sin(angle)]);rr=radii(seg,center,dr)
            rr=rr[(rr>2)&(rr<43)]
            distances.append(rr.max() if len(rr) else np.nan)
        valid=np.isfinite(distances)
        if valid.sum()<arc_count*.7:raise ValueError('Shoulder strap missed garment')
        lengths=np.interp(sweep,sweep[valid],np.asarray(distances)[valid])
        for j,angle in enumerate(sweep):
            dr=np.array([math.cos(angle),math.sin(angle)])
            yz=center+dr*(lengths[j]+.37)
            ribbon[j,col]=[x,*yz]
        endz=ribbon[arc_count-1,col,2]
        for j,t in enumerate(np.linspace(0,1,rows-arc_count+1)[1:],arc_count):
            z=endz*(1-t)+103.5*t
            cx=sign*(8.5*(1-t)-11.8*t)+dx
            depth=face_y(cloth,cx,z,True)
            ribbon[j,col]=[cx,depth-.33-(.32 if sign==1 else 0)*math.sin(math.pi*t)**4,z]
        for ax in (1,2):
            v=ribbon[:,col,ax];valid=np.isfinite(v)
            v[:]=gaussian_filter1d(np.interp(np.arange(rows),np.flatnonzero(valid),v[valid]),.55)
    update(name,ribbon)
d['positions']=p.round(5).tolist()
d['shirt_finish']='Fitted neckline and continuous crossing apron straps'
(out/'outfit.json').write_text(json.dumps(d,separators=(',',':')))
