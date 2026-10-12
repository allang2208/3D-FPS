from arm_core import *
from scipy.optimize import minimize
cm=camera();rows={fam:posed('empty_7',fam) for fam in ('base',*D['profiles'])}
frames=list(range(126,160))
# Fit only actual shoulder/upper-arm vertices; no preview or game run.
ids=np.unique(np.r_[cap,upper[::8]])
subset={n:(i[np.isin(i,ids)],w[np.isin(i,ids)],local[np.isin(i,ids)]) for n,(i,w,local) in groups.items() if np.isin(i,ids).any()}
cap_set=np.isin(ids,cap);upper_set=np.isin(ids,upper)
index={v:i for i,v in enumerate(ids)}
g={n:(np.array([index[v] for v in i]),w,local) for n,(i,w,local) in subset.items()}
def sampled(w):
 out=np.zeros((len(ids),3))
 for n,(i,v,local) in g.items():out[i]+=((cm@w[n])@local.T).T[:,:3]*v[:,None]
 return out
def errors(w):
 p=sampled(w);c=p[cap_set];x,y,z=c.T
 edge=np.minimum.reduce((z+TV*x,y+TH*x,-y+TH*x,-z+TV*x))
 exposed=np.where(x>0,np.maximum(0,edge+1.5),0)
 v=p[upper_set];x,y,z=v.T;inside=(x>0)&(abs(y)<TH*x)&(abs(z)<TV*x)
 close=np.where(inside,np.maximum(0,15-np.linalg.norm(v,axis=1)),0)
 return float(np.max(exposed)),float(np.max(close))
# A single smooth shoulder offset prevents frame-to-frame solver flicker.
# Optimize the same offset for the default and all four grip families.
poses=[(r[f],envelope(f)) for r in rows.values() for f in frames[::2]]
def cost(v):
 maximum=0.;total=0.
 for w,weight in poses:
  try:q=support_pose(w,v[:3],v[3],weight,cm)
  except ValueError:return 1e6+float(np.dot(v,v))
  edge,near=errors(q);e=4*edge*edge+near*near;maximum=max(maximum,e);total+=e
 return 500*maximum+20*total/len(poses)+float(np.dot(v[:3],v[:3]))+.015*v[3]*v[3]
best=None
for start in ([2,-2,-8,0],[3,-3,-12,0]):
 res=minimize(cost,start,method='Powell',bounds=[(-1,8),(-9,0),(-18,0),(-20,20)],options={'maxiter':45,'xtol':.03,'ftol':.001})
 print('SUPPORT_FIT',res.x.tolist(),res.fun,flush=True)
 if best is None or res.fun<best.fun:best=res
value=best.x;result=dict(offset_camera_cm=value[:3].tolist(),bend_degrees=float(value[3]),cost=float(best.fun),window=[125,137,145,160],frames={},runtime_tested=False)
for fam,r in rows.items():
 result['frames'][fam]={}
 for frame in (125,132,138,144,150,156,160):
  result['frames'][fam][frame]=dict(before=measure(r[frame],cm),authored=measure(support_pose(r[frame],value[:3],value[3],envelope(frame),cm),cm))
(O/'support_fit.json').write_text(json.dumps(result,indent=2))
print('LEFT_ARM_ROOT_FIT_SAVED',result['offset_camera_cm'],result['bend_degrees'],flush=True)
