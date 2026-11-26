"""Complete the rolled sleeves, yoke and placket on the fitted blacksmith work shirt."""
import json
import math
from pathlib import Path
import numpy as np
from scipy.ndimage import gaussian_filter1d
from scipy.spatial import cKDTree

P=Path(__file__).resolve().parents[3]
OUT=P/'SourceAssets/VillageBlacksmithNPC20261118/BodyOutfit'
BASE=P/'SourceAssets/JasonStrong20261117'
def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))
def unit(q):
    return q/np.maximum(np.linalg.norm(q,axis=-1,keepdims=True),1e-9)
d=read(OUT/'outfit.json')
if 'Workshirt yoke' in d['parts']:
    raise SystemExit('Shirt revision already present')
p=d['positions']; f=d['triangles']; w=d['weights']; normals=d['normals']
rig=read(BASE/'R3_ArmsRefined/AnatomyReview/derived_saved_mesh.json')
skin=np.asarray(read(BASE/'R4_PoseRefined/Review/forms.json')['base'])
skin_tri=np.asarray(rig['triangles'])[np.isin(rig['triangle_materials'],[0,1,3,5])]
native=read(BASE/'R3_ArmsRefined/head_source.json')
neck=np.asarray(native['positions'])+[0,0,4.5]
nf=np.asarray(native['triangles'])
nf=nf[(np.max(neck[nf,2],axis=1)<160)&(np.asarray(native['triangle_materials'])==0)]
body_cloud=skin[skin_tri]
body_and_neck=np.concatenate([body_cloud,neck[nf]])
skin_tree=cKDTree(skin)
bones={b['name']:np.asarray(b['position']) for b in d['bones']}
shirt=d['parts']['shirt']; sh=np.asarray(p[shirt[0]:shirt[2]]);shtri=np.asarray(f[shirt[1]:shirt[3]])
shcloud=sh[shtri];slots=d['material_slots']
def weighted(q):
    dist,ids=skin_tree.query(q,k=5);influence=1/(dist+.08)**2;influence/=sum(influence);weight={}
    for i,fac in zip(ids,influence):
        for bone,value in rig['weights'][i]:weight[bone]=weight.get(bone,0)+fac*value
    row=sorted(weight.items(),key=lambda x:-x[1])[:8];total=sum(h[1] for h in row)
    return [[idx,round(fac/total,7)] for idx,fac in row]
def patch(name,coords,uv,slot='Linen',reverse=False,seam=False):
    xyz=np.asarray(coords);M,N=xyz.shape[:2];i0=len(p);j0=len(f)
    quads=[]
    end=N if seam else N-1
    for j in range(M-1):
        for i in range(end):
            k=(i+1)%N
            for a in [[(j,i),(j,k),(j+1,k)],[(j,i),(j+1,k),(j+1,i)]]:
                quads.append(a[::-1] if reverse else a)
    smooth=np.zeros_like(xyz)
    for tri in quads:
        aa,bb,cc=[xyz[j,i] for j,i in tri];n=np.cross(cc-aa,bb-aa)
        for j,i in tri:smooth[j,i]+=n
    smooth=unit(smooth)
    p.extend(np.round(xyz.reshape(-1,3),5).tolist());w.extend(weighted(q) for q in xyz.reshape(-1,3))
    for tri in quads:
        f.append([i0+j*N+i for j,i in tri]);d['normals'].append([smooth[j,i].round(5).tolist() for j,i in tri]);d['triangle_materials'].append(slots.index(slot))
        near_wrap=seam and max(i for j,i in tri)-min(i for j,i in tri)>N//2
        d['uv'].append([uv(j,N if near_wrap and i==0 else i) for j,i in tri])
    d['parts'][name]=[i0,j0,len(p),len(f)]
def cross_section(tris,center,axis,e1,e2,angles,default):
    dist=(tris-center)@axis
    hit=(dist.min(1)<=0)&(dist.max(1)>0)
    verts=tris[hit]-center;ds=dist[hit];a=[];b=[]
    # Each intersecting triangle yields one line segment in the slice.
    for axis_k in range(3):
        axis_j=(axis_k+1)%3;axis_i=(axis_k+2)%3
        sel=((ds[:,axis_k]>0)!=(ds[:,axis_j]>0))&((ds[:,axis_k]>0)!=(ds[:,axis_i]>0))
        vv=verts[sel];v=ds[sel]
        for to,coll in [(axis_j,a),(axis_i,b)]:
            t=v[:,axis_k]/(v[:,axis_k]-v[:,to])
            coll.extend((vv[:,axis_k]*(1-t[:,None])+vv[:,to]*t[:,None]).tolist())
    if not a:return np.array(default)
    aa=np.asarray(a);bb=np.asarray(b);aa=np.column_stack([aa@e1,aa@e2]);bb=np.column_stack([bb@e1,bb@e2]);delta=bb-aa
    out=[]
    for idx,ang in enumerate(angles):
        ray=np.array([math.cos(ang),math.sin(ang)]);perp=np.array([-ray[1],ray[0]])
        pa=aa@perp;pb=bb@perp;idxs=np.where((pa<0)!=(pb<0))[0]
        t=-pa[idxs]/(pb[idxs]-pa[idxs]);r=(aa[idxs]+t[:,None]*delta[idxs])@ray
        r=r[(r>1)&(r<24)]
        if len(r):
            # Shell inner and outer surfaces lie close together at the same crossing.
            r=r[r<=np.min(r)+1.3];out.append(r.max())
        else:out.append(default[idx])
    return np.array(out)
angles=np.arange(64)*math.tau/64
sleeve=read(OUT/'Inputs/shirt.json')
hem_ids=np.unique(np.asarray(sleeve['triangles'])[np.array(sleeve['triangle_materials'])==1])
for side,sign in [('l',1),('r',-1)]:
    hem=sh[hem_ids];hc=hem[hem[:,0]*sign>0].mean(0)
    elbow=bones['lowerarm_'+side];hand=bones['hand_'+side];shoulder=bones['upperarm_'+side]
    upper=unit(elbow-shoulder);lower=unit(hand-elbow)
    # The captured R4 cuff is in world bind space, so work from its actual centre.
    start=hc-2.8*upper;end=elbow+lower*6.4
    def center(t):return (1-t)**2*start+2*t*(1-t)*(elbow+1.9*upper)+t*t*end
    def frame(axis):
        b1=unit(np.cross(axis,[0,1,0]));b2=unit(np.cross(axis,b1));return b1,b2
    a1,a2=frame(upper)
    root=cross_section(shcloud,start,upper,a1,a2,angles,np.ones(len(angles))*6.0)
    root=gaussian_filter1d(root,.6,mode='wrap')
    coords=[];ts=list(np.linspace(0,.74,19))+[.765,.79,.81,.84,.87,.89,.912,.94,.968,.99,1.,1.005]
    rolls=[0,.12,.39,.64,.69,.44,.50,.76,.70,.55,.19,-.17]
    for j,t in enumerate(ts):
        c=center(t);axis=unit((1-t)*upper+t*lower)
        e1,e2=frame(axis);rays=np.cos(angles)[:,None]*e1+np.sin(angles)[:,None]*e2
        size=cross_section(body_cloud,c,axis,e1,e2,angles,root*.81)
        size=gaussian_filter1d(size,.70,mode='wrap')+.74+.26*np.cos(3*angles+2*t)**2
        blend=np.clip(t/.29,0,1);blend=blend*blend*(3-2*blend)
        rad=(1-blend)*(root-.04+.45*np.clip(t/.09,0,1))+blend*size
        if j>=19:rad+=rolls[j-19]
        else:rad+=.12*math.sin(t*14)*np.cos(2*angles+t*2)
        radial=rad[:,None]*rays
        coords.append(c+radial+axis*(np.sin(angles+sign)*.23*blend)[:,None])
    # Ring order and longitudinal sweep determine the outward clockwise winding.
    patch('Rolled work sleeve '+side,coords,lambda j,i:[i/33,j/21],seam=True,reverse=True)
# Fit the collar opening to the neck and outer yoke to the edge of the existing scoop.
angles=np.arange(96)*math.tau/96
origin=np.array([0,-.4,0.]);rays=np.stack([np.sin(angles),np.cos(angles)],axis=1)
rr=sh[:,:2]-origin[:2];rho=np.linalg.norm(rr,axis=1);theta=np.arctan2(rr[:,0],rr[:,1])
outer=[];zout=[]
for ang in angles:
    stride=abs(np.angle(np.exp(1j*(theta-ang))))
    idx=np.argmin(np.where((stride<.075)&(sh[:,2]>136),rho,1e6))
    outer.append(rho[idx]+1.0);zout.append(sh[idx,2])
outer=gaussian_filter1d(outer,1.05,mode='wrap');zout=gaussian_filter1d(zout,1.05,mode='wrap')
front=np.cos(angles);vnotch=np.exp(-np.abs(np.angle(np.exp(1j*angles)))/.13)
zin=152.9-.65*front-3.25*vnotch
inner=np.empty(len(angles))
for j,ang in enumerate(angles):
    inner[j]=cross_section(body_and_neck,np.array([0,-.4,zin[j]]),np.array([0,0,1]),np.array([0,1,0]),np.array([1,0,0]),[ang],[5.25])[0]+.45
inner=gaussian_filter1d(inner,.75,mode='wrap')
# Upward and forward ray samples on the actual shoulders maintain cloth clearance.
allcloud=body_and_neck
def vertical_top(q,cloud,guess):
    tri=cloud[:,:,:2];bbox=(tri.min(1)<=q).all(axis=1)&(tri.max(1)>=q).all(axis=1)
    t=cloud[bbox];a=t[:,0,:2];e=t[:,1,:2]-a;g=t[:,2,:2]-a;u=q-a
    den=e[:,0]*g[:,1]-e[:,1]*g[:,0];ok=abs(den)>1e-9
    den[~ok]=1
    i=(u[:,0]*g[:,1]-u[:,1]*g[:,0])/den;j=(e[:,0]*u[:,1]-e[:,1]*u[:,0])/den
    ok &= (i>=0)&(j>=0)&(i+j<=1)
    z=t[:,0,2]+(t[:,1,2]-t[:,0,2])*i+(t[:,2,2]-t[:,0,2])*j
    z=z[ok&(z<guess+3.)]
    return max(z) if len(z) else guess-.5
# Per-column interpolation from the existing outer cloth to the upper neck.
coords=[];steps=np.linspace(0,1,16)
bbox_min=allcloud[:,:,:2].min(1);bbox_max=allcloud[:,:,:2].max(1)
for t in steps:
    radius=outer*(1-t)+inner*t
    xy=origin[:2]+rays*radius[:,None];z=zout*(1-t)+zin*t
    for i,q in enumerate(xy):
        local=allcloud[((bbox_min<=q)&(bbox_max>=q)).all(1)]
        z[i]=max(z[i],vertical_top(q,local,z[i])+.48)
    coords.append(np.column_stack([xy,z]))
coords=np.asarray(coords);coords[0,:,2]-=.24
patch('Workshirt yoke',coords,lambda j,i:[i/47,j/18],seam=True)
# Rolled bias facing turns under at the inner edge, with a slightly brighter ridge.
facing=[coords[-1]+np.column_stack((rays*width,np.full(len(angles),rise))) for width,rise in [(.55,.02),(.26,.16),(.02,.19),(-.10,.10),(-.10,-.18)]]
patch('Neck opening facing',facing,lambda j,i:[i/50,j/22],seam=True)
def front_depth(x,z):
    cloud=np.concatenate([shcloud,body_and_neck])
    t=cloud[((cloud[:,:,0].min(1)<=x)&(cloud[:,:,0].max(1)>=x)&(cloud[:,:,2].min(1)<=z)&(cloud[:,:,2].max(1)>=z))]
    t=t[:,:,[0,2,1]].copy();return vertical_top(np.array([x,z]),t,20)
for side in [-1,1]:
    rows=[]
    for t in np.linspace(0,1,20):
        z=139.5+t*9.6;cx=side*(.42+1.02*t*t)
        row=[]
        for k in np.linspace(-.44,.44,5):
            x=cx+k
            depth=front_depth(x,z)+.67
            yoke=np.asarray(coords).reshape(-1,3);dd=(yoke[:,0]-x)**2+(yoke[:,2]-z)**2
            closest=np.argmin(dd+np.where(yoke[:,1]>0,0,1e5))
            if dd[closest]<4:depth=max(depth,yoke[closest,1]+.23)
            row.append([x,depth+.10*math.cos(k*3),z])
        rows.append(row)
    patch('Short shirt placket '+str(side),rows,lambda j,i:[i/19,j/24])
# Push the original shoulder straps onto the new yoke where the two pieces cross.
yp=coords.reshape(-1,3)
for name in ['Bib strap -1','Bib strap 1']:
    lo,tf,hi,te=d['parts'][name]
    grid=np.asarray(p[lo:hi]).reshape(-1,5,3)
    for j,row in enumerate(grid):
        direction=1 if j<18 else -1
        for k,pt in enumerate(row):
            if 18<=j<31:
                dist=np.sum((yp[:,:2]-pt[:2])**2,axis=1)
                near=dist<1.9
                if near.any():pt[2]=max(pt[2],yp[near,2].max()+.5)
            elif pt[2]>138:
                dist=np.sum((yp[:,[0,2]]-pt[[0,2]])**2,axis=1)
                near=(dist<1.5)&(yp[:,1]*direction>1.0)
                if near.any():pt[1]=direction*max(direction*pt[1],(direction*yp[near,1]).max()+.48)
    p[lo:hi]=grid.reshape(-1,3).round(5).tolist()
(OUT/'outfit.json').write_text(json.dumps(d,separators=(',',':')))
print('SMITH_WORKSHIRT_FINISHED',len(p),len(f),flush=True)

