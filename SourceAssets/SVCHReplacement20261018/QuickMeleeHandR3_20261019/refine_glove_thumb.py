"""Unfold the small glove thumb patch with minimum local displacement."""
from pathlib import Path
import sys,json,numpy as np
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from check_surfaces import *
from scipy.optimize import minimize
O=HERE;cached=np.load(O/'glove-correctives.npz');fields={k:cached[k].copy() for k in cached.files}
blue.extra=fields;grip='JC_Grip_R_0_51_48_48';start=fields[grip].copy();T=blue.T;history=[]
poses=np.load(O/'poses.npz')['base']
for round_ in range(3):
    for fi in [0,3,7,20,52,68,82,90,100,108]:
        p=poses[fi];v=blue.evaluate(p);x=np.zeros((len(blue.first),3));np.add.at(x,blue.weld,v);x/=blue.counts[:,None]
        fn=np.cross(x[T[:,1]]-x[T[:,0]],x[T[:,2]]-x[T[:,0]]);vn=np.zeros_like(x)
        for k in range(3):np.add.at(vn,T[:,k],fn)
        vn/=np.maximum(np.linalg.norm(vn,axis=1)[:,None],1e-10)
        dots=np.einsum('ij,ij->i',fn,vn[T].mean(1));bad=np.flatnonzero((dots<0)&blue.mask)
        if not len(bad):continue
        moving=np.unique(T[bad]);affected=np.any(np.isin(T,moving),axis=1);tris=T[affected]
        normal=vn[tris].mean(1);normal/=np.maximum(np.linalg.norm(normal,axis=1)[:,None],1e-10)
        # The original garment remains fixed outside these few welded vertices.
        base=x.copy();margin=np.minimum(np.linalg.norm(fn[affected],axis=1)*.03,.0005)
        def constraints(delta):
            y=base.copy();y[moving]+=delta.reshape(-1,3)
            a=np.cross(y[tris[:,1]]-y[tris[:,0]],y[tris[:,2]]-y[tris[:,0]])
            return np.einsum('ij,ij->i',a,normal)-margin
        result=minimize(lambda d:float(d@d),np.zeros(len(moving)*3),jac=lambda d:2*d,
            method='SLSQP',bounds=[(-.15,.15)]*(len(moving)*3),constraints=[{'type':'ineq','fun':constraints}],
            options={'ftol':1e-12,'maxiter':200})
        if not result.success:raise RuntimeError(result.message)
        change=np.zeros_like(x);change[moving]=result.x.reshape(-1,3)
        A=np.zeros((len(v),3,3))
        for j in blue.used:A+=(p[j]@blue.inv[j])[:3,:3]*blue.weights[:,j,None,None]
        weight=driver.weights(matrix_pose(p))[grip]
        rest=np.linalg.solve(A,change[blue.weld,...,None])[...,0]/weight
        if np.linalg.norm(rest,axis=1).max()>.2:raise RuntimeError('Unexpected glove patch displacement')
        fields[grip]+=rest
        history.append({'round':round_,'frame':fi,'folds_before':len(bad),'folds_after':blue.folds(blue.evaluate(p)),
                        'maximum_rest_change_cm':float(np.linalg.norm(rest,axis=1).max()),'welded_vertices':len(moving)})
        print(history[-1],flush=True)
np.savez_compressed(O/'glove-correctives.npz',**fields)
report={'base_glove_changed':False,'V9_changed':False,'history':history,
        'maximum_additional_rest_change_cm':float(np.linalg.norm(fields[grip]-start,axis=1).max())}
(O/'glove-thumb-refinement.json').write_text(json.dumps(report,indent=2))
