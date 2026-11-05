import json,sys,numpy as np
from scipy.optimize import minimize
d=json.load(sys.stdin);x=np.array(d['x']);n=len(x);J=np.array(d['J']);r=np.array(d['r']);C=np.array(d['C']);b=np.array(d['need'])
if not len(b):C=np.zeros((1,n));b=np.array([-1.])
cons=[{'type':'ineq','fun':lambda y:C@y[:n]+y[n]-b},
 {'type':'ineq','fun':lambda y:110.**2-np.square(x[:3]+y[:3]).sum()},
 {'type':'ineq','fun':lambda y:40.**2-np.square(x[3:6]+y[3:6]).sum()}]
for a in d['arms']:
 v=np.array(a['v']);B=np.array(a['basis']);limit=a['limit']
 cons.append({'type':'ineq','fun':lambda y,v=v,B=B,limit=limit:limit**2-np.square(v+B@(x[:3]+y[:3])).sum()})
bounds=[(-3.,3.)]*3+[(-2.,2.)]*3
for k in range(6,n):
 lo,hi=((-55.,75.) if k%2==0 else (-65.,60.)) if k<14 else ((-20.,20.) if k<18 else (-35.,35.))
 bounds.append((max(-3.,lo-x[k]),min(3.,hi-x[k])))
bounds.append((0,None));start=np.zeros(n+1);start[n]=max(0,float(b.max()))+.001
res=minimize(lambda y:.001*np.square(J@y[:n]+r).sum()+80*y[n]**2,start,
 jac=lambda y:np.r_[.002*J.T@(J@y[:n]+r),160*y[n]],bounds=bounds,constraints=cons,method='SLSQP',options={'maxiter':180,'ftol':1e-8})
print(json.dumps({'step':res.x[:n].tolist(),'slack':float(res.x[n]),'success':bool(res.success)}))
