"""Fit only Jason's weighted elbow helpers, preserving main arm/finger transforms and contact timing."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
import json,itertools
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as Q
O=Path(__file__).parent;D=json.loads((O/'saved_clips_before.json').read_text());G=json.loads((O/'body_geometry.json').read_text());A=json.loads((O/'graph_source.json').read_text())
names=D['names'];parents=A['parents'];ix={n:i for i,n in enumerate(names)};ref=np.array(D['reference'])
def mat(f):
    m=np.zeros((len(f),4,4));m[:,3,3]=1;m[:,:3,:3]=Q.from_quat(f[:,3:7]).as_matrix()*f[:,None,7:];m[:,:3,3]=f[:,:3];return m
def fk(f):
    m=mat(f)
    for i,p in enumerate(parents):
        if p>=0:m[i]=m[p]@m[i]
    return m
bind=fk(ref);inv=np.linalg.inv(bind);verts=np.array(G['positions']);faces=np.array(G['triangles']);points=np.column_stack((verts,np.ones(len(verts))))
weights=np.zeros((len(verts),len(names)))
for j,ws in enumerate(G['weights']):
    for n,w in ws.items():weights[j,ix[n]]=w
def under(i,a):
    while i>=0:
        if i==a:return True
        i=parents[i]
    return False
def modify(world,side,param):
    u,l,h=[ix[n+'_'+side] for n in ['upperarm','lowerarm','hand']];du=world[u,:3,:3]@inv[u,:3,:3];dl=world[l,:3,:3]@inv[l,:3,:3];uq=Q.from_matrix(du);delta=(uq.inv()*Q.from_matrix(dl)).as_rotvec();out=world.copy()
    for stem,share in zip(['upperarm_twistCor_02','lowerarm_correctiveRoot','lowerarm_twist_02'],param):
        b=ix[stem+'_'+side];rot=(uq*Q.from_rotvec(delta*share)).as_matrix();target=np.eye(4);target[:3,:3]=rot@bind[b,:3,:3];target[:3,3]=world[l,:3,3]+rot@(bind[b,:3,3]-bind[l,:3,3]);change=target@np.linalg.inv(world[b])
        for j in range(len(names)):
            if under(j,b):out[j]=change@world[j]
    return out
def dataset(side):
    b=ix['lowerarm_'+side];near=np.linalg.norm(verts-bind[b,:3,3],axis=1)<16
    bones=np.array([under(j,ix['upperarm_'+side]) and not under(j,ix['hand_'+side]) for j in range(len(names))])
    fs=faces[np.all(near[faces],axis=1)&(weights[faces][:,:,bones].sum(2).mean(1)>.7)]
    ids=np.unique(fs);reverse=np.full(len(verts),-1);reverse[ids]=np.arange(len(ids));fs=reverse[fs]
    wp=weights[ids];active=np.where(wp.max(0)>0)[0];wp=wp[:,active];wf=wp[fs].mean(1)
    vv=verts[ids];nn=np.cross(vv[fs[:,1]]-vv[fs[:,0]],vv[fs[:,2]]-vv[fs[:,0]]);nn/=np.maximum(np.linalg.norm(nn,axis=1,keepdims=True),1e-12)
    return ids,fs,active,wp,wf,nn
datasets={s:dataset(s) for s in ['l','r']}
def skin_metrics(world,side):
    ids,fs,active,wp,wf,nn=datasets[side];mm=world@inv;v=np.zeros((len(ids),3));expected=np.zeros_like(nn)
    for j,b in enumerate(active):
        v+=(points[ids]@mm[b].T)[:,:3]*wp[:,j,None];expected+=(nn@mm[b,:3,:3].T)*wf[:,j,None]
    normal=np.cross(v[fs[:,1]]-v[fs[:,0]],v[fs[:,2]]-v[fs[:,0]]);area=np.linalg.norm(normal,axis=1);den=area*np.linalg.norm(expected,axis=1);cos=(normal*expected).sum(1)/np.maximum(den,1e-12)
    folds=int(np.sum(cos<-.001));penalty=np.mean(np.maximum(0,.1-cos)**2)
    return folds,penalty,v
frames=D['clips']['Consume.EatLargeLamb']['frames'];selected=[fk(np.array(frames[round(t*60)])) for t in [1.,2.75,4.65,5.,5.3]]
results={}
for side in ['l','r']:
    original=[skin_metrics(w,side) for w in selected];candidates=[]
    for param in itertools.product([0.,.1,.2,.3,.4],[.35,.5,.65,.8],[.75,.875,1.]):
        counts=[];score=0.;maxmove=0.
        for w,old in zip(selected,original):
            metrics=skin_metrics(modify(w,side,param),side);move=np.linalg.norm(metrics[2]-old[2],axis=1);maxmove=max(maxmove,float(move.max()));counts.append(metrics[0]);score+=metrics[1]+.000025*np.mean(move**2)
        candidates.append({'params':param,'folds':counts,'score':score,'max_vertex_move_cm':maxmove})
    candidates.sort(key=lambda c:c['score']);results[side]={'before':[x[0] for x in original],'candidates':candidates[:12]};print(side,results[side],flush=True)
(O/'elbow_fit.json').write_text(json.dumps(results,indent=2))
