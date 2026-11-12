"""Reuse Wrist36 joint solver and accepted M249 grasp, fit to real handguard."""
from pathlib import Path
import sys,json,numpy as np
from scipy.spatial.transform import Rotation as R
from scipy.optimize import minimize
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
sys.path.insert(0,str(ROOT.parent/'M249Orpind20261107/Wrist36'));import rig as G
d=json.loads((ROOT/'inputs.json').read_text())['M249'];base=np.array(d['local'])[None,:,:]
local=G.layer(base,d['idle'],d['profiles']['base'],G.names,np.array([0.]));world=G.compose(local,G.parents)[0]
gun=G.ix['WPN_root'];ha=G.ix['hand_l'];ua=G.ix['upperarm_l'];la=G.ix['lowerarm_l']
old=np.linalg.inv(world[gun])@world[ha];old[:3,:3]=G.rot(old);old[:3,3]*=100
rest=G.encode(G.B[None,:,:],G.parents)[0];digits=[i for i,n in enumerate(G.names) if n.endswith('_l') and n.startswith(('thumb_','index_','middle_','ring_','pinky_'))]
owned=[G.indices('l')[0]]+G.indices('l')[4]+[ha]
donor=np.load(HERE/'svd_pose.npz');dni={n:i for i,n in enumerate(donor['names'])};dw=donor['world'];dr=np.linalg.inv(dw[dni['WPN_root']])@dw[dni['hand_l']];dr[:3,:3]=G.rot(dr);dr[:3,3]*=100
for name,angle,point,curl in [('svd0',0,[2.8265,23.,-3.72],1.),('svd1',0,[2.1265,23.,-4.22],1.)]:
    target=dr.copy();target[:3,3]=point
    wp=(world[gun]@np.r_[target[:3,3]*.01,1])[:3];turn=G.rot(world[gun])@target[:3,:3]@G.rot(world[ha]).T
    length=np.linalg.norm(world[la,:3,3]-world[ua,:3,3])+np.linalg.norm(world[ha,:3,3]-world[la,:3,3])
    def posed(x):return G.solve(world,x,'l',shift=wp-world[ha,:3,3],hand_rotation=turn)
    def reach(x):
        q=posed(x);return .98*length-np.linalg.norm(q[ha,:3,3]-q[ua,:3,3])
    def cost(x):return max(0,G.bend(posed(x))-12)**2*8+.025*np.sum(np.degrees(x)**2)
    fit=minimize(cost,np.zeros(4),method='SLSQP',bounds=[(-1.3,1.3)]*3+[(-2.,2.)],constraints=[dict(type='ineq',fun=reach)],options=dict(maxiter=150,ftol=1e-7,eps=1e-5))
    loc=local.copy();loc[:,owned,3:7]=G.encode(posed(fit.x)[None,:,:],G.parents)[:,owned,3:7]
    for b in digits:
        loc[0,b,3:7]=donor['local'][dni[G.names[b]],3:7]
    w=G.compose(loc,G.parents)[0];np.savez(HERE/(name+'.npz'),v=G.skin(w),f=G.faces,s=G.sections,dominant=G.dominant,names=np.array(G.names),w=w,local=loc[0],target=target)
    print(name,'bend',G.bend(w),'reach',reach(fit.x))
