"""TS01 R4: independent torso blocks, continuous low crew yoke and cut raglan seams.
Run in background Blender. All units stored in centimetres, native UE bones retained.
"""
import sys,copy,math,os
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).parent))
from shirt_geometry import read,write,subset,unit
from combat3_cloth import normals,smooth
import combat3_cuff_solver as solver
P=Path('D:/FPS3D/FPSGAME');S=P/'SourceAssets/ModernTacticalSet20261113';B=S/'CombatShirtR3';R=S/'CombatShirtR4'
solver.C=R
(R/'Review').mkdir(exist_ok=True)

def weights_mix(rows,coeff):
    v={}
    for row,t in zip(rows,coeff):
        for bi,w in row:v[bi]=v.get(bi,0)+float(w*t)
    v=sorted(((int(i),w) for i,w in v.items() if w>1e-9),key=lambda x:-x[1])[:8];total=sum(w for _,w in v)
    return [[i,w/total] for i,w in v]

def boundary(f):
    es={}
    for face in f:
        for a,b in zip(face,np.roll(face,-1)):es.setdefault(tuple(sorted([int(a),int(b)])),[]).append((int(a),int(b)))
    return [x[0] for x in es.values() if len(x)==1]

def loops_from_edges(edges):
    adj={};todo=set()
    for a,b in edges:
        a,b=int(a),int(b);adj.setdefault(a,set()).add(b);adj.setdefault(b,set()).add(a);todo.add(tuple(sorted([a,b])))
    out=[]
    def walk(start,second):
        line=[start];previous,current=start,second;todo.discard(tuple(sorted([start,second])))
        while current!=start:
            line.append(current)
            if len(adj[current])!=2:break
            choices=[n for n in adj[current] if tuple(sorted([current,n])) in todo]
            if not choices:break
            following=min(choices);todo.remove(tuple(sorted([current,following])));previous,current=current,following
        return line
    # End a chain at a branch. Never walk through an already consumed circuit.
    for vertex in sorted(adj):
        if len(adj[vertex])==2:continue
        for neighbor in sorted(adj[vertex]):
            if tuple(sorted([vertex,neighbor])) in todo:out.append(walk(vertex,neighbor))
    while todo:
        a,b=min(todo);out.append(walk(a,b))
    return out

def hull(points):
    points=sorted(set(map(tuple,np.round(points,6))))
    def cross(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    lo=[];hi=[]
    for q in points:
        while len(lo)>1 and cross(lo[-2],lo[-1],q)<=0:lo.pop()
        lo.append(q)
    for q in reversed(points):
        while len(hi)>1 and cross(hi[-2],hi[-1],q)<=0:hi.pop()
        hi.append(q)
    return np.array(lo[:-1]+hi[:-1])

def torso_field(body,bones):
    p=np.array(body['positions']);f=np.array(body['triangles']);q=p[f];c=q.mean(1)
    q=q[(abs(c[:,0])<20)&(c[:,2]>88)&(c[:,2]<bones['neck_01']['position'][2]-2)]
    zs=np.arange(92.,146.1,.5);angles=np.arange(128)*2*np.pi/128;field=[];origin=np.array(bones['pelvis']['position'])[:2]
    for z in zs:
        points=[]
        for a,b in [(0,1),(1,2),(2,0)]:
            qa,qb=q[:,a],q[:,b];ok=(qa[:,2]-z)*(qb[:,2]-z)<0
            t=(z-qa[ok,2])/(qb[ok,2]-qa[ok,2]);points.extend(qa[ok,:2]+(qb[ok,:2]-qa[ok,:2])*t[:,None])
        if len(points)<3:field.append(field[-1] if field else np.full(128,10.));continue
        hh=hull(points)-origin;aa=hh;bb=np.roll(hh,-1,axis=0);edge=bb-aa;out=[]
        for theta in angles:
            direction=np.array([np.cos(theta),np.sin(theta)]);den=direction[0]*edge[:,1]-direction[1]*edge[:,0]
            radius=(aa[:,0]*edge[:,1]-aa[:,1]*edge[:,0])/np.where(abs(den)>1e-9,den,1e-9)
            t=(aa[:,0]*direction[1]-aa[:,1]*direction[0])/np.where(abs(den)>1e-9,den,1e-9)
            good=(radius>0)&(t>=0)&(t<=1)&(abs(den)>1e-9)
            out.append(float(radius[good].max()) if good.any() else 10.)
        field.append(out)
    raw=np.array(field);field=raw.copy()
    # A continuous chest panel bridges anatomy rather than reproducing each breast.
    for _ in range(18):field=(field*2+np.vstack([field[:1],field[:-1]])+np.vstack([field[1:],field[-1:]]))/4
    field=np.maximum(field,raw-.12)
    return zs,field,origin

def sample_field(q,zs,field,origin):
    v=q[:2]-origin;theta=np.arctan2(v[1],v[0])%(2*np.pi);tf=theta*field.shape[1]/(2*np.pi);it=int(tf);ft=tf-it
    zf=np.clip((q[2]-zs[0])/(zs[1]-zs[0]),0,len(zs)-1);iz=min(len(zs)-2,int(zf));fz=zf-iz
    return ((1-ft)*field[iz,it]+ft*field[iz,(it+1)%field.shape[1]])*(1-fz)+((1-ft)*field[iz+1,it]+ft*field[iz+1,(it+1)%field.shape[1]])*fz

def append_face(d,face,mat,uv=None):
    p=np.array([d['positions'][i] for i in face]);n=-unit(np.cross(p[1]-p[0],p[2]-p[0]))
    d['triangles'].append(list(map(int,face)));d['triangle_materials'].append(int(mat));d['normals'].append([n.tolist()]*3)
    if uv is None:
        axes=[i for i in range(3) if i!=np.argmax(abs(n))];uv=(p[:,axes]/8).tolist()
    d['uv'].append(uv)

def cut_raglan(d,bones):
    p=np.array(d['positions']);clav=np.mean([bones['clavicle_'+s]['position'][2] for s in ['l','r']]);top=clav+3.1
    g=abs(p[:,0])-(6.3+.56*(top-p[:,2]));g[p[:,2]<clav-21]=abs(p[p[:,2]<clav-21,0])-21
    old={k:d[k] for k in ['triangles','triangle_materials','uv','normals']}
    for k in old:d[k]=[]
    edge_cache={}
    for face,uv,mat in zip(old['triangles'],old['uv'],old['triangle_materials']):
        if mat==2 or min(g[face])>=0 or max(g[face])<=0:
            append_face(d,face,mat if mat==2 else int(np.mean(g[face])<0),uv);continue
        for positive in [False,True]:
            poly=[]
            for j in range(3):
                a,b=face[j],face[(j+1)%3];ua,ub=np.array(uv[j]),np.array(uv[(j+1)%3]);ga,gb=g[a],g[b]
                if (ga>=0)==positive:poly.append((a,ua))
                if (ga<0)!=(gb<0):
                    t=ga/(ga-gb);key=tuple(sorted([a,b]))
                    if key not in edge_cache:
                        edge_cache[key]=len(d['positions']);d['positions'].append((p[a]*(1-t)+p[b]*t).tolist());d['weights'].append(weights_mix([d['weights'][a],d['weights'][b]],[1-t,t]))
                    poly.append((edge_cache[key],ua*(1-t)+ub*t))
            for j in range(1,len(poly)-1):
                vs=[poly[i] for i in [0,j,j+1]];append_face(d,[x[0] for x in vs],0 if positive else 1,[x[1].tolist() for x in vs])
    return len(edge_cache)

def pattern(rig):
    raw=read(B/'Authored'/f'shirt_cloth_{rig}.json');count=len(raw['positions'])//2;f=np.array(raw['triangles']);d=subset(raw,(f<count).all(1));d.pop('cloth_production',None)
    p=np.array(d['positions']);bones={b['name']:b for b in d['bones']};body=read(B/'Inputs'/f'Body_{rig}.json');zs,field,origin=torso_field(body,bones)
    index={b['index']:b['name'] for b in d['bones']};cuff=np.zeros(len(p),bool)
    for side in ['l','r']:
        elbow=np.array(bones['lowerarm_'+side]['position']);wrist=np.array(bones['hand_'+side]['position']);along=(p-wrist)@unit(elbow-wrist);same=p[:,0]*np.sign(wrist[0])>0
        cuff|=same&(along<7.)
    for i,q in enumerate(p):
        if cuff[i]:continue
        torso=sum(w for bi,w in d['weights'][i] if index[bi].startswith(('spine','pelvis')))
        blend=smooth((torso-.15)/.7)*smooth((21-abs(q[0]))/3)*smooth((bones['clavicle_l']['position'][2]-q[2]+6)/9)
        if blend<=0:continue
        radius=np.linalg.norm(q[:2]-origin);target=sample_field(q,zs,field,origin)
        ease=.72+.58*math.exp(-((q[2]-111)/9)**2)
        # Waist anchor clears the native body; fabric above it has gathering room.
        ease*=.42+.58*float(smooth((q[2]-96)/5))
        if rig=='Kaitlin':ease+=.28*math.exp(-((q[2]-123)/8)**2)
        p[i,:2]+=(q[:2]-origin)/max(radius,1e-6)*(target+ease-radius)*blend
    d['positions']=p.tolist()
    edges=boundary(d['triangles']);loops=loops_from_edges(edges);rim=max(loops,key=lambda row:np.mean(p[row,2]));directed=set(edges)
    if (rim[0],rim[1]) not in directed:rim.reverse()
    neck=np.array(bones['neck_01']['position']);clav=np.mean([bones['clavicle_'+s]['position'][2] for s in ['l','r']]);ring0=p[rim];theta=np.unwrap(np.arctan2(ring0[:,1]-neck[1],ring0[:,0]-neck[0]));target=[]
    for t in theta:
        sn=math.sin(t);target.append([neck[0]+6.0*math.cos(t),neck[1]+(6.35 if sn>0 else 5.3)*sn,clav+3.15-1.35*sn])
    target=np.array(target);previous=rim;nr=12;last=[]
    for j in range(1,nr+1):
        t=j/nr;ring=ring0*(1-t)+target*t;ring[:,2]+=.65*np.sin(np.pi*t)
        new=[]
        for k,q in enumerate(ring):
            new.append(len(d['positions']));d['positions'].append(q.tolist());native=d['weights'][rim[k]];collar=[[bones['spine_05']['index'],.85],[bones['neck_01']['index'],.15]];d['weights'].append(weights_mix([native,collar],[1-t,t]))
        for k in range(len(rim)):
            h=(k+1)%len(rim);a,b,c,e=previous[k],previous[h],new[h],new[k]
            append_face(d,[b,a,e],2 if j>=nr-1 else 1);append_face(d,[b,e,c],2 if j>=nr-1 else 1)
        previous=new;last=new
    cuts=cut_raglan(d,bones);p=np.array(d['positions']);f=np.array(d['triangles']);n=normals(p,f);d['normals']=n[f].tolist()
    pins=np.zeros(len(p));pins[last]=1
    for side in ['l','r']:
        elbow=np.array(bones['lowerarm_'+side]['position']);wrist=np.array(bones['hand_'+side]['position']);distance=(p-wrist)@unit(elbow-wrist);same=p[:,0]*np.sign(wrist[0])>0
        pins=np.maximum(pins,np.where(same,1-smooth((distance-7)/3),0))
    pins=np.maximum(pins,1-smooth((p[:,2]-95)/2.5))
    # Shoulder supports carry the cloth; torso and elbows remain free to settle.
    for side in ['l','r']:
        a=np.array(bones['upperarm_'+side]['position']);pins=np.maximum(pins,.45*np.exp(-np.sum((p-a)**2,axis=1)/18))
    pins[last]=1;write(R/'Authored'/f'shirt_pattern_{rig}.json',d)
    head=read(S/'HelmetHairFitR1/Inputs'/f'{rig}_Head.json');collider=copy.deepcopy(body);offset=len(collider['positions']);collider['positions']+=head['positions'];collider['triangles']+=[[v+offset for v in tri] for tri in head['triangles']]
    # An allowance of 4.5% forms folds in free panels without relocating anchors.
    result=solver.settle('Pattern_'+rig,p,f,pins,collider,frames=42,allowance=.045)
    d['positions']=result.tolist();n=normals(result,f);d['normals']=n[f].tolist();d['r4_pattern']=dict(raglan_cut_vertices=cuts,neck_vertices=last,outer_vertices=len(p),frames=42,allowance=.045,body_clearance_cm=.3,torso_ease_cm=[.72,1.58],native_fixed_cuff_cm=7.)
    write(R/'Authored'/f'shirt_outer_{rig}.json',d);print('R4_PATTERN_COMPLETE',rig,len(result),len(f),flush=True)

if __name__=='__main__':
    for rig in (sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else ['Jason','Kaitlin']):pattern(rig)
