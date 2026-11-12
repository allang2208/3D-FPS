"""Fit the PKM lid contact to the same edge, closer to its hinge."""
from pathlib import Path
import json
import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.optimize import minimize
import rig as G

ROOT=Path(__file__).resolve().parent

def cover_clearance(world,times,empty):
    camera=json.loads((ROOT/'Review02/pkm-eye.json').read_text())['7' if empty else '6']
    eye=np.array(camera['eye'])
    to_view=np.array(camera['camera_from_component'])
    geometry=json.loads((ROOT.parent/'PKMLowpoly20260922/ArmJoint49/Inputs/BarePalmV7.json').read_text())
    points=np.array(geometry['positions'])
    weights=geometry['weights']
    _,ua,la,ha,_,_=G.indices('l')
    v=G.B[la,:3,3]-G.B[ua,:3,3]
    u=((points-G.B[ua,:3,3])@v)/(v@v)
    ids=np.array([i for i,ws in enumerate(weights) if sum(w for n,w in ws.items() if n.endswith('_l'))>.96])[::18]
    cap=np.array([u[i]<.37 and max(weights[i],key=weights[i].get).startswith(('upperarm','clavicle')) for i in ids])
    groups={}
    for j,i in enumerate(ids):
        for n,weight in weights[i].items():
            if n not in G.ix:continue
            ids2,pts=groups.setdefault(G.ix[n],([],[]))
            ids2.append(j);pts.append(np.r_[points[i],1.]*weight)
    inv=np.linalg.inv(G.B)
    group=[(b,np.array(ii),np.array(pp)@inv[b].T) for b,(ii,pp) in groups.items()]
    tanx=np.tan(np.radians(107.512367/2));tany=tanx*9/16
    def clearance(frame):
        skin=np.zeros((len(ids),3))
        for b,ii,pp in group:skin[ii]+=pp@frame[b,:3].T
        view=(skin-eye)@to_view.T
        depth,side,height=view.T
        # Margin outside camera cone, expanded just beyond both edges.
        off=np.maximum.reduce([np.abs(side)-depth*tanx*1.05,np.abs(height)-depth*tany*1.05,-depth])
        distance=np.linalg.norm(view,axis=1)
        return float(np.min(np.maximum(distance-16,off))),float(off[cap].min())
    gun=G.ix['WPN_root'];lid=G.ix['PKM_Cover']
    # The authored closed lid and the barrel share their longitudinal axis.
    axis=G.rot(world[0,lid]).T@G.rot(world[0,gun])[:,1]
    blend=G.ease((times-.25)/.31)*G.ease((1.24-times)/.25)
    shifts=[G.rot(w[lid])@axis*(17*weight) for w,weight in zip(world,blend)]
    samples=np.flatnonzero((times>=.18)&(times<=1.30))
    keys=np.unique(np.r_[samples[::3],samples[-1]])
    values=[];last=np.zeros(4)
    for k in keys:
        w=world[k]
        if not blend[k]:
            last=np.zeros(4)
        else:
            length=np.linalg.norm(w[la,:3,3]-w[ua,:3,3])+np.linalg.norm(w[ha,:3,3]-w[la,:3,3])
            def solve(x):return G.solve(w,x,shift=shifts[k],station_weight=blend[k])
            def score(x):
                q=solve(x);near,cap_margin=clearance(q)
                short=max(0,np.linalg.norm(q[ha,:3,3]-q[ua,:3,3])-length*.987)
                return (200*min(0,near-1)**2+170*min(0,cap_margin-2)**2+
                        1.5*max(0,G.bend(q)-32)**2+350*short**2+
                        .022*np.sum(np.degrees(x)**2)+.018*np.sum(np.degrees(x-last)**2))
            seeds=[last,np.zeros(4)]
            best=None
            for seed in seeds:
                fit=minimize(score,seed,method='L-BFGS-B',bounds=[(-.70,.70)]*3+[(-1.30,1.30)],options=dict(maxiter=65,ftol=1e-9,eps=1e-5))
                if best is None or fit.fun<best.fun:best=fit
                near,cap_margin=clearance(solve(best.x))
                if near>.5 and cap_margin>0:break
            last=best.x
        values.append(last.copy())
    curve=PchipInterpolator(times[keys],values)(times[samples])
    result=world.copy()
    for k,x in zip(samples,curve):
        if blend[k]>0:result[k]=G.solve(world[k],x,shift=shifts[k],station_weight=blend[k])
    strength=[clearance(w) for w in result[samples]]
    print('PKM lid camera margins before/after',np.min([clearance(w) for w in world[samples]],axis=0),np.min(strength,axis=0),flush=True)
    return result
