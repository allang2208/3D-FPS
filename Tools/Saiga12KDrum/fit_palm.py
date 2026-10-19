import json,gzip,sys,numpy as np
from scipy.optimize import differential_evolution,minimize
from pathlib import Path
sys.path.insert(0,'Tools/Saiga12KInspect');from pose_math import *
O=Path('SourceAssets/Saiga12KDrum20261018');d=json.loads(Path('SourceAssets/Saiga12KInspect20261018/Inputs/runtime-source.json').read_text());a=json.loads((O/'Authoring/drum.json').read_text());q=np.load(O/'Inputs/palm-source.npz')['points'];src=json.load(gzip.open(O/'Inputs/reload-source.json.gz','rt'));names=[b['name'] for b in d['bones']];pa={b['name']:names[b['parent']] if b['parent']>=0 else None for b in d['bones']};w=world({n:matrix(v) for n,v in src['clips']['drum_reload']['frames'][208]['local'].items()},pa);wrist=(np.linalg.inv(w['WPN_SOCKET_Magazine'])@w['hand_l'])[:3,3]*100;sm=np.array(a['socket_from_root_cm']);C=(sm@np.r_[.08,12.3,-12.6,1])[:3];print('c',C,'wrist',wrist)
# Closed exterior envelope: padding ring radius 9.68, front raised face 3.65.
def sdf(p):
 radial=np.linalg.norm(p[:,[0,2]]-C[[0,2]],axis=1)-9.68;axial=np.abs(p[:,1]-C[1])-3.65;d=np.stack([radial,axial],1);return np.minimum(np.maximum(radial,axial),0)+np.linalg.norm(np.maximum(d,0),axis=1)
palm=q[(q[:,0]>-2)&(q[:,0]<4)&(q[:,1]>-4.5)&(q[:,1]<-.5)&(q[:,2]<-11)]
def obj(v):
 r=Rot.from_rotvec(np.deg2rad(v[3:])).as_matrix();p=(q-wrist)@r.T+wrist+v[:3];s=sdf(p);pp=(palm-wrist)@r.T+wrist+v[:3];ps=sdf(pp);pen=np.minimum(s-.04,0);return 700*np.mean(pen*pen)+400*np.min(np.minimum(s,0))**2+.045*np.dot(v[:3],v[:3])+.001*np.dot(v[3:],v[3:])+2*np.mean(np.sort(np.abs(ps-.12))[:max(4,len(ps)//12)]**2)
r=differential_evolution(obj,[(-1.5,1.5),(-1,4),(-8,0),(-18,18),(-18,18),(-18,18)],popsize=8,maxiter=100,tol=1e-6,seed=12,polish=True);print('fit',r.x,'cost',r.fun);(O/'Inputs/palm-fit.json').write_text(json.dumps({'translation_mag_cm':r.x[:3].tolist(),'rotation_mag_deg':r.x[3:].tolist(),'pivot_mag_cm':wrist.tolist(),'source_frame':208,'support_envelope_center_cm':C.tolist(),'purpose':'authoring contact fit; no runtime acceptance'},indent=2))
