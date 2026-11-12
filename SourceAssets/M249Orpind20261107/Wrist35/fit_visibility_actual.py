import os
os.environ['OPENBLAS_NUM_THREADS']='1'
from pathlib import Path
import sys,json,gzip,pickle
import numpy as np
from scipy.optimize import minimize
from scipy.spatial.transform import Rotation as R
outdir=Path(__file__).resolve().parent
prior=outdir.parent/'Wrist34'
sys.path.insert(0,str(prior))
from fit_hold import d,g,names,ix,parents,B,vertices,tri,sections,compose,layer,matrix,elbow_pose,box_clearance,wrist,ease,encode,sample,rot,arm,ha,cl,ua,la,hand

upperfaces=tri[sections==g['slots'].index('Skin_UpperArm')]
upperids=np.unique(upperfaces)
upperids=np.array([i for i in upperids if sum(w for b,w in g['weights'][i] if names[b].endswith('_l'))>.9])
skinbind=np.c_[vertices[upperids],np.ones(len(upperids))]
weights={}
for k,i in enumerate(upperids):
    for b,w in g['weights'][i]:weights.setdefault(b,np.zeros(len(upperids)))[k]=w
inverse=np.linalg.inv(B)
def skin(w):
    xf=w@inverse;pts=np.zeros((len(upperids),3))
    for b,ws in weights.items():pts+=(skinbind@xf[b,:3,:].T)*ws[:,None]
    return pts

def camera(path,times):
    key='prism_'+('empty' if path.endswith('_empty') else 'normal')+'_60'
    a=np.fromfile(prior/'native_delivered'/(key+'.f32'),np.float32).reshape(-1,6+len(names)*7+14)
    a=a[a[:,1]==2];indices=[np.argmin(abs(a[:,3]-t)) for t in times];a=a[indices]
    rig=matrix(np.c_[a[:,-14:-7],np.ones((len(a),3))]);eye=matrix(np.c_[a[:,-7:],np.ones((len(a),3))])
    frames=json.loads((prior/'geometry_prism_final'/('box_empty_prism' if path.endswith('_empty') else 'box_normal_prism')/'review.json').read_text(encoding='utf-8-sig'))['frames']
    offset=sample(np.array([f['camera'] for f in frames]).ravel(),[f['source'] for f in frames],times)
    return np.linalg.inv(matrix(offset))@np.linalg.inv(eye)@rig

tanx=np.tan(np.radians(107.512367/2));tany=tanx*9/16
def clearance(w,xf):
    v=skin(w)@xf[:3,:3].T+xf[:3,3]
    return np.maximum.reduce([-v[:,2]-v[:,0]*tany,-v[:,1]-v[:,0]*tanx,v[:,1]-v[:,0]*tanx,-v[:,0]])

payload=json.load(gzip.open(outdir/'prism-before.json.gz','rt'));fits={}
for path,c in d['clips'].items():
    if not path.endswith(('A_M249_reload','A_M249_reload_empty')):continue
    times=np.array(c['times']);old=compose(layer(np.array(c['frames']),path,payload,names,times),parents)
    empty=path.endswith('_empty');start,full,back,end=(.85,1.7,4.85,5.25) if empty else (1.6,2.45,5.95,6.45)
    window=ease((times-start)/(full-start))*(1-ease((times-back)/(end-back)))
    active=np.flatnonzero((window>.999)&(np.arange(len(times))%15==0))
    xfs=camera(path,times[active]);baseline=np.array([clearance(old[k],xf).min() for k,xf in zip(active,xfs)])
    print(path,'baseline',baseline.tolist(),flush=True)
    def measures(x):
        margins=[];bends=[];reach=[];box=[]
        for k,xf in zip(active,xfs):
            w=elbow_pose(old[k],x)
            margins.append(clearance(w,xf).min())
            bends.append(np.degrees(wrist(w))-35)
            length=np.linalg.norm(old[k,la,:3,3]-old[k,ua,:3,3])+np.linalg.norm(old[k,ha,:3,3]-old[k,la,:3,3])
            reach.append(np.linalg.norm(w[ha,:3,3]-w[ua,:3,3])/length)
            box.append(box_clearance(w)-min(.15,box_clearance(old[k])))
        return np.array(margins),np.array(bends),np.array(reach),np.array(box)
    def score(x):
        margin,bend,reach,box=measures(x)
        return np.maximum(.6-margin,0).dot(np.maximum(.6-margin,0))*2000 + np.maximum(bend,0).dot(np.maximum(bend,0))*10 + np.maximum(reach-.975,0).dot(np.maximum(reach-.975,0))*1e6 + np.maximum(-box,0).dot(np.maximum(-box,0))*1e5 + np.degrees(x).dot(np.degrees(x))*.01
    best=None
    for seed in ([-.4,.4,0,.4],[-.3,.6,0,.7],[-.5,.5,-.2,.2]):
        fit=minimize(score,np.array(seed,dtype=float),method='SLSQP',bounds=[(-1.,1.)]*3+[(-1.5,1.5)],options=dict(maxiter=150,ftol=1e-5,eps=1e-5))
        if best is None or fit.fun<best.fun:best=fit
        print('candidate',best.fun,np.degrees(best.x).tolist(),[v.tolist() for v in measures(best.x)],flush=True)
    fits[path]=dict(parameters=best.x.tolist(),degrees=np.degrees(best.x).tolist(),score=float(best.fun),window=[start,full,back,end],baseline=baseline.tolist(),result=[v.tolist() for v in measures(best.x)])
(outdir/'visibility_fit.json').write_text(json.dumps(fits,indent=2),encoding='utf-8')
