"""Fit existing wardrobe shells to R4 and pattern the apron on their actual exterior."""
from pathlib import Path
import json,math
import runpy
import numpy as np
from scipy.spatial import cKDTree

P=Path('D:/FPS3D/FPSGAME')
BASE=P/'SourceAssets/JasonStrong20261117'
OUT=P/'SourceAssets/VillageBlacksmithNPC20261118/BodyOutfit'
def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
old=read(BASE/'R3_ArmsRefined/AnatomyReview/original_saved_mesh.json')
rig=read(BASE/'R3_ArmsRefined/AnatomyReview/derived_saved_mesh.json')
r4=read(BASE/'R4_PoseRefined/Review/forms.json')
a=np.array(old['positions']);b=np.array(r4['base'])
native={v['name']:i for i,v in enumerate(rig['bones'])}
oldtree=cKDTree(a);newtree=cKDTree(b)
slots=['Linen','Twill','Apron','Saddle','Boot','Sole','Brass','Thread']
ps=[];tris=[];uv=[];mids=[];ns=[];weights=[];parts={}
def newpart(name):parts[name]=[len(ps),len(tris)]
def closepart(name):parts[name] += [len(ps),len(tris)]
def smoothstep(lo,hi,x):
    t=np.clip((x-lo)/(hi-lo),0,1)
    return t*t*(3-2*t)
def mix_weights(pairs):
    dw={}
    for row,k in pairs:
        for i,w in row:dw[int(i)]=dw.get(int(i),0)+k*w
    v=sorted(dw.items(),key=lambda x:-x[1])[:8];s=sum(w for _,w in v)
    return [[i,round(w/s,7)] for i,w in v]
def body_bind(pos):
    ds,idx=newtree.query(pos,k=4)
    fac=1/(ds+.075)**2;fac/=fac.sum()
    return mix_weights([(rig['weights'][j],w) for j,w in zip(idx,fac)])
def vertex(pos,weight=None):
    ps.append(np.round(pos,5).tolist())
    weights.append(body_bind(pos) if weight is None else weight)
    return len(ps)-1
def face(ids,tex,slot,normal=None):
    # UE's front convention is clockwise when looking from the outside.
    for order in ([[0,1,2]] if len(ids)==3 else [[0,1,2],[0,2,3]]):
        v=[int(ids[i]) for i in order];tris.append(v);uv.append([tex[i] for i in order]);mids.append(slots.index(slot))
        if normal is None:
            aa,bb,cc=np.array([ps[i] for i in v]);n=np.cross(cc-aa,bb-aa);n/=max(np.linalg.norm(n),1e-9)
            ns.append([np.round(n,5).tolist()]*3)
        else:ns.append([normal[i] for i in order])
garments={}
for item in ('shirt','trousers','boots'):
    d=read(OUT/'Inputs'/f'{item}.json');src=np.array(d['positions'])
    ds,idx=oldtree.query(src,k=8);fac=1/(ds+.18)**2;fac/=fac.sum(axis=1)[:,None]
    pos=src+np.sum((b-a)[idx]*fac[:,:,None],axis=1)
    # Tuck only hem vertices below the belt, using the fitted trouser waist as cover.
    if item=='shirt':
        z=pos[:,2].copy()
        hem=z<109
        pos[hem,2]=np.interp(z[hem],[77,86,101,109],[99.5,100.3,102.6,109])
        tuck=1-smoothstep(101,109,z)
        pos[:,0]*=1-.105*tuck;pos[:,1]=2.0+(pos[:,1]-2.0)*(1-.10*tuck)
        # Ease at the shoulder and upper arm for the maximum R4 corrective.
        idxbody=oldtree.query(src,k=1)[1]
        n=pos-b[idxbody];lens=np.linalg.norm(n,axis=1);n/=np.maximum(lens,.01)[:,None]
        pos+=n*(.22+.55*smoothstep(14,23,abs(pos[:,0]))*smoothstep(110,128,pos[:,2]))[:,None]
    if item=='boots':
        # Maintain sole thickness and avoid individual toe drift.
        z=src[:,2];fac=smoothstep(8,20,z)
        pos[:,2]=src[:,2]+(pos[:,2]-src[:,2])*fac
    garments[item]=(pos,np.array(d['triangles']))
    newpart(item)
    first=len(ps);mapping={i:native[bone['name']] for i,bone in enumerate(d['bones']) if bone['name'] in native}
    for xyz,ww in zip(pos,d['weights']):
        vertex(xyz,mix_weights([([[mapping[i],w] for i,w in ww if i in mapping],1.)]))
    for tri,uvs,norm,mat in zip(d['triangles'],d['uv'],d['normals'],d['triangle_materials']):
        slot={'shirt':'Linen','trousers':'Twill','boots':'Boot'}[item]
        if item=='boots' and np.mean(pos[tri,2])<1.4:slot='Sole'
        if item=='shirt' and mat>2:continue
        face([first+i for i in tri],np.round(np.array(uvs)*({'shirt':3.5,'trousers':3.5,'boots':2}[item]),6).tolist(),slot,norm)
    closepart(item)
# Sample front skin of the actual dressed silhouette in XZ for the conforming upper apron and patch.
gp=np.concatenate([garments[k][0][garments[k][1]] for k in ('shirt','trousers')])
gproj=gp[:,:,[0,2]];mid=gproj.mean(axis=1);tree=cKDTree(mid)
def contact(x,z,mode='front'):
    ids=tree.query([x,z],k=240)[1]
    t=gproj[ids];e=t[:,1]-t[:,0];f=t[:,2]-t[:,0];q=np.array((x,z))-t[:,0]
    den=e[:,0]*f[:,1]-e[:,1]*f[:,0];den[np.abs(den)<1e-8]=np.nan
    u=(q[:,0]*f[:,1]-q[:,1]*f[:,0])/den;v=(e[:,0]*q[:,1]-e[:,1]*q[:,0])/den
    ok=(u>=-.001)&(v>=-.001)&(u+v<=1.001)
    if not ok.any():return None
    y=gp[ids,0,1]+u*(gp[ids,1,1]-gp[ids,0,1])+v*(gp[ids,2,1]-gp[ids,0,1])
    return float(y[ok].max() if mode=='front' else y[ok].min())
def at(x,z,mode='front',fallback=10):
    h=contact(x,z,mode)
    return h if h is not None else fallback
# Belt hugs each actual horizontal section, taking the outermost fitted torso intersection.
def belt_point(angle,z,dilation=0):
    origin=np.array([0,1.5]);ray=np.array([math.sin(angle),math.cos(angle)])
    ds=(gp[:,:,2]-z);cut=(ds.min(axis=1)<=0)&(ds.max(axis=1)>=0)
    ts=gp[cut];vs=ds[cut];pts=[]
    for i,j in [(0,1),(1,2),(2,0)]:
        k=(vs[:,i]<0)!=(vs[:,j]<0)
        s=ts[k,i,:2];f=ts[k,j,:2]
        q=vs[k,i]/(vs[k,i]-vs[k,j]);pts.extend((s+q[:,None]*(f-s)).tolist())
    xy=np.array(pts)-origin
    ang=np.arctan2(xy[:,0],xy[:,1]);da=np.abs(np.angle(np.exp(1j*(ang-angle))))
    radius=np.max(np.linalg.norm(xy[da<.135],axis=1)) if np.any(da<.135) else np.linalg.norm(xy[np.argmin(da)])
    return np.r_[origin+ray*(radius+dilation),z]
def grid(name,coords,mat,uvs,flip=False,binder=None):
    newpart(name);vp=np.array([[vertex(p,None if binder is None else binder(p)) for p in row] for row in coords]);M,N=vp.shape
    for j in range(M-1):
        for i in range(N-1):
            idx=[(j,i),(j,i+1),(j+1,i+1),(j+1,i)]
            if flip:idx=idx[::-1]
            face([vp[r,c] for r,c in idx],[uvs(r,c,M,N) for r,c in idx],mat)
    closepart(name)
def cloth_uv(row,col,M,N):return [3*col/(N-1),4*row/(M-1)]
def apron(u,t):
    # u goes across the pattern; t follows the hem upwards to the bib.
    z=55+81*t
    width=np.interp(z,[55,73,92,102,116,128,136],[18.0,17.8,17.0,15.4,12.7,10.9,9.8])
    x=u*width; z+=.55*(1-t)*(1-u*u)-1.15*t**8*u*u
    # A continuous sheet bridges the gap between the legs.
    if z<98:
        sample=min(max(abs(x),6.),13.5)
        center=max(at(sample,z,fallback=8),at(-sample,z,fallback=8))
        side=at(x,z,fallback=center*.58)
        y=max(side+.95,center*(1-.39*abs(u)**3)+1.6)+.35*math.sin(u*10+t*3)*(1-t)
    else:y=at(x,z,fallback=9.5)+.88
    return np.array([x,y,z])
def apron_bind(p):
    base=body_bind(p)
    a=1-smoothstep(67,94,p[2])
    if not a:return base
    # Keep center between the legs instead of switching abruptly at the inseam.
    left=float(smoothstep(-8,8,p[0]))
    row=[[native['thigh_l'],left*.92],[native['thigh_r'],(1-left)*.92],[native['pelvis'],.08]]
    return mix_weights([(base,1-a),(row,a)])
grid('Apron bib and skirt',[[apron(u,t) for u in np.linspace(-1,1,47)] for t in np.linspace(0,1,66)],'Apron',cloth_uv,False,apron_bind)
def strip(name,side):
    z0,z1=134.5,104
    x=side*8.5
    # Come over each shoulder between the bib and the back waist.
    f=[(x,at(x,z)+1.1,z) for z in np.linspace(z0,144.0,18)]
    back=[(side*(8.5+(144-z)*.13),at(side*(8.5+(144-z)*.13),z,'back',-7)-.90,z) for z in np.linspace(144,z1,33)]
    ya,yb=f[-1][1],back[0][1]
    # Sample the upper surface at each strap column for the short over-shoulder section.
    pts=garments['shirt'][0]
    arc=[]
    for yy in np.linspace(ya,yb,15)[1:-1]:
        dist=(pts[:,0]-x)**2+(pts[:,1]-yy)**2
        jj=np.argpartition(dist,22)[:22];zz=max(144.0,pts[jj,2].max())+.58
        arc.append((x,yy,zz))
    spine=f+arc+back;coords=[]
    for j,(cx,yy,zz) in enumerate(spine):
        coords.append([[cx+q,yy,zz] for q in (-1.25,-.65,0,.65,1.25)])
    grid(name,coords,'Saddle',lambda r,c,M,N:[c*.07,r*.07],False)
for s in (-1,1):strip('Bib strap '+str(s),s)
angles=np.linspace(-math.pi,math.pi,97)
grid('Apron waist belt',[[belt_point(u,z,1.68+.12*math.sin(math.pi*(z-99.8)/5.5)) for u in angles] for z in np.linspace(99.8,105.3,7)],'Saddle',lambda r,c,M,N:[c/15,r/16])
def tube(name,path,radius,mat):
    path=np.array(path);newpart(name);ids=[]
    for j,q in enumerate(path):
        axis=path[min(j+1,len(path)-1)]-path[max(j-1,0)];axis/=max(np.linalg.norm(axis),1e-8)
        v=np.cross(axis,[0,1,0]);v/=max(np.linalg.norm(v),1e-8);w=np.cross(axis,v)
        ids.append([vertex(q+radius*(v*math.cos(a)+w*math.sin(a)),apron_bind(q) if q[2]<94 else None) for a in np.linspace(0,math.tau,8,endpoint=False)])
    for j in range(len(ids)-1):
        for i in range(8):
            k=(i+1)%8
            face([ids[j][i],ids[j+1][i],ids[j+1][k],ids[j][k]],[[0,0],[.2,0],[.2,.1],[0,.1]],mat)
    closepart(name)
def worn_edge(u,t):
    q=apron(u,t).copy();q[1]+=.08;return q
for side in (-1,1):tube('Apron turned edge '+str(side),[worn_edge(side,t) for t in np.linspace(0,1,68)],.18,'Saddle')
for t,lab in [(0,'Hem'),(1,'Bib')]:tube(lab+' turned edge',[worn_edge(u,t) for u in np.linspace(-1,1,49)],.18,'Saddle')
# Single oblique repair patch, hand whip-stitched in waxed thread.
def repair(l,h):
    u=.30+(l*6.2-h*.80)/17.6
    t=(75+l*3.1+h*1.7-55)/81
    q=apron(u,t);q[1]+=.34
    return q
grid('Old oblique leather repair',[[repair(l,h) for l in np.linspace(-1,1,19)] for h in np.linspace(-1,1,7)],'Saddle',lambda r,c,M,N:[c/22,r/24],False,apron_bind)
for j,l in enumerate(np.linspace(-.92,.92,13)):
    for s in (-1,1):
        qa,qb=repair(l-.033,s*.84),repair(l+.033,s*1.17)
        qa[1]+=.18;qb[1]+=.15
        tube('Whip stitch %d %d'%(j,s),[qa,qb],.075,'Thread')
# Rounded brass frame and prong; every point follows the same waist weights.
center=belt_point(.02,102.5,2.35);cx,cy,cz=center
frame=[]
for rx,rz,start in [(2.9,-2.0,-90),(2.9,2.,0),(-2.9,2.,90),(-2.9,-2.,180)]:
    for ang in np.linspace(start,start+90,7):
        theta=math.radians(ang);frame.append([cx+rx+.44*math.cos(theta),cy,cz+rz+.44*math.sin(theta)])
frame.append(frame[0]);tube('Cast buckle frame',frame,.31,'Brass')
tube('Buckle tongue',[[cx-1.2,cy+.18,cz-2.1],[cx-.92,cy+.28,cz],[cx-.5,cy+.35,cz+2.14]],.22,'Brass')
out={'material_slots':slots,'positions':ps,'triangles':tris,'uv':uv,'normals':ns,'triangle_materials':mids,'weights':weights,'parts':parts,'bones':rig['bones']}
(OUT/'outfit.json').write_text(json.dumps(out,separators=(',',':')))
print('SMITH_WORKWEAR_AUTHORED',len(ps),len(tris))
runpy.run_path(str(Path(__file__).with_name('finish_shirt.py')),run_name='__main__')
