"""Centimetre-space garment authoring; UE clockwise winding and native weights."""
import json,math,copy
from pathlib import Path
import numpy as np
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/BlueMageRobe20261018'
SLOTS=['RobeBody','RobeSleeves','RobeCuffs','SleeveLining','RobeSkirt','RobeHood','RobeEmbroidery','RobeBelt','RobeSilver','RobeSimulationProxy','TorsoLining','RobeGem']
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def write(p,d):p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,separators=(',',':')),encoding='utf-8')
def unit(v):return np.asarray(v)/max(float(np.linalg.norm(v)),1e-12)
def smooth(t):t=np.clip(t,0,1);return t*t*(3-2*t)
def norm_weights(w):
    pairs=sorted(((n,float(v)) for n,v in w.items() if v>1e-8),key=lambda kv:-kv[1])[:8];total=sum(v for _,v in pairs)
    return {n:v/total for n,v in pairs}
def blend_weights(a,b,t):return norm_weights({n:a.get(n,0)*(1-t)+b.get(n,0)*t for n in a.keys()|b.keys()})
def normals(p,f):
    p=np.asarray(p);f=np.asarray(f);n=np.zeros_like(p);cross=-np.cross(p[f[:,1]]-p[f[:,0]],p[f[:,2]]-p[f[:,0]])
    for k in range(3):np.add.at(n,f[:,k],cross)
    return n/np.maximum(np.linalg.norm(n,axis=1)[:,None],1e-12)
def new_mesh(profile,skin):return dict(profile=profile,binding_source=skin['source'],bones=skin['bones'],skeleton=skin.get('skeleton'),positions=[],weights=[],triangles=[],uv=[],triangle_materials=[],normals=[],material_slots=SLOTS,contract='Approved BlueMageRobe: native fitted closed collar/cuffs; continuous pelvis-supported skirt; shared Witch cloth capture; production render excludes proxy')
def vertex(d,p,w):i=len(d['positions']);d['positions'].append(np.asarray(p).tolist());d['weights'].append(copy.deepcopy(w));return i
def face(d,ids,mat,uv,out=None):
    if out is not None:
        p=np.array([d['positions'][i] for i in ids])
        if np.cross(p[1]-p[0],p[2]-p[0])@out>0:ids=ids[::-1];uv=uv[::-1]
    d['triangles'].append(list(map(int,ids)));d['triangle_materials'].append(int(mat));d['uv'].append(np.asarray(uv).tolist())
def finish(d):
    p=np.array(d['positions']);f=np.array(d['triangles']);d['normals']=normals(p,f)[f].tolist()
    if not np.isfinite(p).all() or not np.isfinite(d['normals']).all():raise RuntimeError('Nonfinite authored garment')
    if max(np.linalg.norm(p[f]-p[np.roll(f,1,axis=1)],axis=2).ravel())>30:raise RuntimeError('Unexpected long garment edge')
    return d
def boundary(f):
    ed={}
    for row in f:
        for a,b in zip(row,np.roll(row,-1)):ed.setdefault(tuple(sorted((int(a),int(b)))),[]).append((int(a),int(b)))
    return [v[0] for v in ed.values() if len(v)==1]
def paired(d,p,f,ws,clearance,thickness,materials,tex,inner_materials=None,directions=None):
    p=np.array(p);f=np.array(f);n=normals(p,f) if directions is None else directions
    c=np.broadcast_to(np.asarray(clearance),len(p));outer=[vertex(d,v,w) for v,w in zip(p+n*c[:,None],ws)];inside=[vertex(d,v,w) for v,w in zip(p+n*(c-thickness)[:,None],ws)]
    for fi,row in enumerate(f):
        uv=tex(row,False);face(d,[outer[i] for i in row],materials(fi,row),uv)
        face(d,[inside[i] for i in row[::-1]],inner_materials(fi,row) if inner_materials else 10,uv[::-1])
    for a,b in boundary(f):
        ids=[outer[b],outer[a],inside[a],inside[b]];length=np.linalg.norm(p[a]-p[b]);uv=[[0,0],[length/25,0],[length/25,thickness/25],[0,thickness/25]]
        for tri in ((0,1,2),(0,2,3)):face(d,[ids[k] for k in tri],inner_materials(0,[a,b,b]) if inner_materials else 10,[uv[k] for k in tri])
    return np.array(outer),np.array(inside)

def tube(d,path,radius,mat,weight,closed=False,sides=8):
    path=np.array(path);start=len(d['positions']);count=len(path)
    for i,p in enumerate(path):
        t=unit(path[(i+1)%count]-path[(i-1)%count]) if closed else unit(path[min(i+1,count-1)]-path[max(0,i-1)])
        a=unit(np.cross(t,[0,0,1] if abs(t[2])<.9 else [0,1,0]));b=np.cross(t,a)
        for angle in np.linspace(0,math.tau,sides,endpoint=False):vertex(d,p+radius*(a*math.cos(angle)+b*math.sin(angle)),weight(p) if callable(weight) else weight)
    for i in range(count if closed else count-1):
        for j in range(sides):
            ids=[start+i*sides+j,start+i*sides+(j+1)%sides,start+((i+1)%count)*sides+(j+1)%sides,start+((i+1)%count)*sides+j]
            for k in ((0,1,2),(0,2,3)):
                mid=np.mean([d['positions'][ids[x]] for x in k],axis=0);center=(path[i]+path[(i+1)%count])/2
                face(d,[ids[x] for x in k],mat,[[i/10,j/sides],[(i+1)/10,j/sides],[(i+1)/10,(j+1)/sides]],unit(mid-center))
    if not closed:
        for end in (0,count-1):
            center=vertex(d,path[end],weight(path[end]) if callable(weight) else weight);out=unit(path[end]-path[1 if end==0 else end-1])
            for j in range(sides):face(d,[center,start+end*sides+j,start+end*sides+(j+1)%sides],mat,[[.5,.5],[0,0],[1,0]],out)
