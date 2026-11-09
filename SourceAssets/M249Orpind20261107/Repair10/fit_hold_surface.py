"""Continuous hand-surface fit around the factory grip, retaining a closed grasp."""
from pathlib import Path
exec(compile((Path(__file__).parent/'fit_hold.py').read_text().split('best=[1.e9')[0],__file__,'exec'))
from scipy.optimize import least_squares
from scipy.spatial import ConvexHull
import ast
x0=np.array([-1.,0.,-2.,-.1,.8,.5,.8,0.,0.,0.])
# Use the closed outer envelope, including the grip's upper collar.
grip=obstacles['M249_Factory_Foregrip'][0];hull=ConvexHull(grip.vertices[np.unique(grip.faces)])
planes=hull.equations
sampleids=handids[::3]
original_posed=posed
def pose(x):
    q,w=original_posed(x[:7]);h=w['hand_l'][:3,3];turn=R.from_rotvec(x[7:10]).as_matrix()
    q[handids]=(q[handids]-h)@turn.T+h
    for name in hb:w[name][:3,3]=h+turn@(w[name][:3,3]-h);w[name][:3,:3]=turn@w[name][:3,:3]
    return q,w
def residual(x):
    q,w=pose(x);d=np.max(q[sampleids]@planes[:,:3].T+planes[:,3],axis=1)
    polygon=np.array([w[n][:2,3] for n in ('hand_l','middle_01_l','middle_02_l','middle_03_l')]);ep=ConvexHull(polygon).equations
    enclosure=np.max(ep[:,:2]@np.array([5.1,-28.9])+ep[:,2])
    a,e,h=[H[n][:3,3] for n in ('upperarm_l','lowerarm_l','hand_l')];at=w['hand_l'][:3,3];axis=unit(at-a);distance=np.linalg.norm(at-a);la=np.linalg.norm(e-a);lb=np.linalg.norm(h-e)
    along=(la*la-lb*lb+distance*distance)/(2*distance);pole=unit(e-a-axis*((e-a)@axis));elbow=a+axis*along+pole*np.sqrt(max(0,la*la-along*along))
    rest=unit(B['hand_l'][:3,3]-B['lowerarm_l'][:3,3]);wrist=np.arccos(np.clip(unit(at-elbow)@(rot(w['hand_l'])@rot(B['hand_l']).T@rest),-1,1))
    return np.r_[np.maximum(0,.10-d)*6.,max(0,enclosure+.25)*30.,(w['middle_02_l'][2,3]+21.0)*12.,x[:3]*.05,(x[3:7]-1)*.10,x[7:]*.5]
fit=least_squares(residual,x0,bounds=([-5.,-3.,-5.,-.6,-.4,-.2,-.2,-.5,-.5,-.5],[3.,5.,0.,1.15,1.15,1.15,1.15,.5,.5,.5]),diff_step=1.e-4,max_nfev=180,verbose=1)
q,w=pose(fit.x);hits=collisions(q);out=dict(parameters=fit.x.tolist(),hits=hits,hand_world={n:a.tolist() for n,a in w.items()})
(r/'hold_fit_surface.json').write_text(json.dumps(out,indent=2));print('HOLD_SURFACE_FIT',out['parameters'],hits,flush=True)
