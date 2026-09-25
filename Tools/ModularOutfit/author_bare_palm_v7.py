"""Fair residual glove grooves on the palm without changing grip bones/weights."""
import json,runpy
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree

PROJECT=Path('D:/FPS3D/FPSGAME')
BASE=PROJECT/'SourceAssets/ModularOutfit20260924/OriginalShapeBareM4'
ROOT=PROJECT/'SourceAssets/ModularOutfit20260925/BarePalmV7'
ROOT.mkdir(parents=True,exist_ok=True)
data=json.loads((BASE/'BareUpperArmsV6/M4_original.json').read_text())
shape=json.loads((BASE/'BareUpperArmsV6/M4_bare_shape.json').read_text())
P=np.asarray(data['positions']);T=np.asarray(data['triangles']);result=P.copy()
def unit(v):return v/np.maximum(np.linalg.norm(v,axis=-1,keepdims=True),1e-12)
def smooth(a,b,x):
    t=np.clip((x-a)/(b-a),0,1);return t*t*(3-2*t)
def normals(p):
    c=p[T];f=-unit(np.cross(c[:,1]-c[:,0],c[:,2]-c[:,0]));n=np.zeros_like(p)
    for k in range(3):
        a=unit(c[:,(k+1)%3]-c[:,k]);b=unit(c[:,(k+2)%3]-c[:,k])
        np.add.at(n,T[:,k],f*np.arccos(np.clip((a*b).sum(1),-1,1))[:,None])
    return unit(n)
N=normals(P)
hand=np.zeros(len(P),bool);hand[T[np.asarray(data['triangle_materials'])==2].ravel()]=True
digit=np.asarray([sum(v for n,v in w.items() if n.startswith(('index_0','middle_0','ring_0','pinky_0','thumb_02','thumb_03'))) for w in data['weights']])
palm_blend=np.zeros(len(P))
reports=[]
for side in ('l','r'):
    fr=shape['anatomy'][side];forward=unit(np.asarray(fr['forward']));dorsal=unit(np.asarray(fr['dorsal']))
    across=unit(np.cross(dorsal,forward));q=P-fr['wrist'];t=q@forward;y=q@across;z=q@dorsal
    facing=N@dorsal;belongs=P[:,0]<0 if side=='l' else P[:,0]>0
    # Finger surfaces and the accepted wrist taper remain fixed. Only the palm
    # skin envelope is faired, with a gradual boundary at the thenar web.
    blend=hand*belongs*smooth(1.9,3.1,t)*(1-smooth(8.2,9.4,t))
    blend*=smooth(-.05,.65,-facing)*(1-smooth(.06,.42,digit))
    palm_blend=np.maximum(palm_blend,blend)
    samples=np.flatnonzero(hand&belongs&(t>1.5)&(t<10)&(facing<-.38)&(digit<.5))
    cells=np.floor(np.column_stack((t[samples],y[samples]))/.22).astype(int)
    _,groups=np.unique(cells,axis=0,return_inverse=True);points=[]
    for g in np.unique(groups):
        ids=samples[groups==g]
        points.append([np.median(t[ids]),np.median(y[ids]),np.quantile(z[ids],.30)])
    points=np.asarray(points);tree=cKDTree(points[:,:2]);ids=np.flatnonzero(blend>0)
    delta=np.zeros(len(P))
    for vi in ids:
        dist,idx=tree.query([t[vi],y[vi]],k=min(48,len(points)))
        xy=points[idx,:2]-[t[vi],y[vi]];x0,x1=xy.T
        X=np.column_stack((x0*0+1,x0,x1,x0*x0,x0*x1,x1*x1))
        w=np.exp(-(dist/1.15)**2)
        fit=np.linalg.solve((X.T*w)@X+np.diag([1e-6,1e-4,1e-4,.003,.003,.003]),(X.T*w)@points[idx,2])
        # Remove narrow padding channels; retain the broad palm cup and pads.
        delta[vi]=np.clip(fit[0]-z[vi],-.23,.13)*blend[vi]*.92
    result+=delta[:,None]*dorsal
    reports.append({'side':side,'palm_vertices':int(np.count_nonzero(delta)),
                    'max_adjustment_cm':float(np.max(np.abs(delta)))})

after=normals(result);affected=np.linalg.norm(result-P,axis=1)>1e-10
adjacent=np.zeros(len(P),bool);adjacent[T[affected[T].any(axis=1)].ravel()]=True
old=np.asarray(data['normals']);axis=np.cross(N,after)[T];dot=(N*after).sum(1)[T]
rotated=old+np.cross(axis,old)+np.cross(axis,np.cross(axis,old))/np.maximum(1+dot[...,None],1e-8)
soft=smooth(0,.3,palm_blend)[T,None]
fair=unit(unit(rotated)*(1-soft)+after[T]*soft)
data['positions']=result.tolist();data['normals']=np.where(adjacent[T,None],fair,old).tolist()
(ROOT/'M4_original.json').write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
(ROOT/'palm_authoring.json').write_text(json.dumps({'changes':reports,'preserved':'Topology, UV0, wrist, fingers, bones and weights',
    'runtime_tested':False},indent=2)+'\n',encoding='utf-8')
runpy.run_path(str(PROJECT/'Tools/ModularOutfit/author_bare_arms_family.py'),init_globals={
    'AUTHOR_ROOT':str(ROOT),'NATIVE_SOURCE_ROOT':str(PROJECT/'SourceAssets/ModularOutfit20260925/BareArmsFamilyV6/Sources'),
    'ACCEPTED_SHAPE':str(ROOT/'M4_original.json'),'INCLUDE_M4':True})
print('BARE_PALM_V7_AUTHORED',reports,flush=True)
