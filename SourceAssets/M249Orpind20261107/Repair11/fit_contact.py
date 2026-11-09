"""Fit the closer grasp to the narrow leg using native skin constraints."""
from pathlib import Path
import pickle,json,numpy as np
from scipy.optimize import least_squares
from scipy.spatial import ConvexHull
from motion import *
r=Path(__file__).resolve().parent
ns={'__file__':str(r/'author.py'),'__name__':'contact_fit'}
exec(compile((r/'author_proximal_study.py').read_text().split('contact=json.loads')[0],str(r/'author_proximal_study.py'),'exec'),ns)
globals().update({k:ns[k] for k in ('names','parents','B','home','local0','d','pivot','tip','closed','rod','edge_a','edge_b','surfaceP','surfaceW','surface_ids','handbones','digits','padP','padWeights')})
new=pickle.load(open(r/'contact_seed.pkl','rb'))
# The grasp occupies the straight central rod. Its measured convex cross section
# supplies continuous skin constraints while fitting the finger articulations.
# Final authoring retains the actual closed-mesh surface fit.
axis=unit(tip);ex=unit(np.cross(axis,[0.,1.,0.]));ey=unit(np.cross(axis,ex));cross=np.stack((ex,ey),axis=1)
da=(edge_a-axis*10.)@axis;db=(edge_b-axis*10.)@axis
cut=(da*db<=0)&(np.abs(da-db)>1.e-9)
section=edge_a[cut]+(edge_b[cut]-edge_a[cut])*(da[cut]/(da[cut]-db[cut]))[:,None]
hull=ConvexHull(section@cross);normals=hull.equations[:,:2];offsets=hull.equations[:,2]
chosen=np.arange(len(surface_ids))
native=np.stack([(surfaceP@np.linalg.inv(B[n]).T)*surfaceW.get(n,np.zeros(len(surface_ids)))[:,None] for n in handbones])
sampled=native[:,chosen]
padnative=np.stack([(padP@np.linalg.inv(B[n]).T)*padWeights.get(n,np.zeros(len(padP)))[:,None] for n in handbones])
jointnames=[f'{digit}_{j:02d}_l' for digit in ('thumb','index','middle','ring','pinky') for j in (1,2,3)]
rows=[];previous=np.zeros(20)
for t in np.arange(.12,.3001,.005):
    i=round(t*200);p={n:w for n,w in zip(names,new['world'][i])};rq=rot(p['WPN_root']);legq=blend(closed,np.eye(3),smooth((t-.12)/.18))
    local={n:np.linalg.inv(p[parents[n]])@p[n] for n in handbones if n!='hand_l'}
    forward=unit(p['middle_01_l'][:3,3]-p['hand_l'][:3,3]);lateral=unit(p['index_01_l'][:3,3]-p['pinky_01_l'][:3,3]);normal=unit(np.cross(forward,lateral))
    if normal@(p['middle_03_l'][:3,3]-p['middle_01_l'][:3,3])<0:normal=-normal
    rodaxis=rq@legq@axis;approach=-unit(normal-rodaxis*(normal@rodaxis))
    baseline=p['hand_l'].copy();baseline[:3,3]-=approach*4.
    desired=approach*.7
    def makepose(x):
        out={'hand_l':baseline.copy()};out['hand_l'][:3,3]+=x[:3]
        for n in handbones:
            if n=='hand_l':continue
            v=local[n].copy()
            if n in jointnames:
                j=jointnames.index(n);v[:3,:3]=turn([0,0,1],x[3+j])@v[:3,:3]
                if n=='thumb_01_l':v[:3,:3]=R.from_rotvec([x[18],x[19],0.]).as_matrix()@v[:3,:3]
            out[n]=out[parents[n]]@v
        return np.stack([out[n] for n in handbones])
    def distance(points):
        q=((points-p['WPN_root'][:3,3])@rq-pivot)@legq
        return ((q@cross)@normals.T+offsets).max(1)
    def residual(x):
        matrices=makepose(x)
        points=np.einsum('bni,bji->nj',sampled,matrices[:,:3,:])
        pads=np.einsum('bni,bji->nj',padnative,matrices[:,:3,:])
        return np.r_[np.maximum(0.,.16-distance(points))/.035,
            (distance(pads)-.18)/.24,(x[:3]-desired)/.65,
            x[3:]/.8,(x-previous)/np.r_[np.full(3,.65),np.full(17,.18)]]
    start=previous.copy()
    if not rows:start[:3]=desired
    fit=least_squares(residual,start,bounds=(np.r_[np.full(3,-4.),np.full(17,-.9)],np.r_[np.full(3,4.),np.full(17,.9)]),max_nfev=60,ftol=2.e-5,xtol=2.e-5)
    previous=fit.x
    rows.append(dict(time=round(float(t),5),parameters=fit.x.tolist()))
    if i%6==0:print('Grasp authored',round(float(t),3),'wrist correction cm',np.round(fit.x[:3],2).tolist(),flush=True)
(r/'contact_fit.json').write_text(json.dumps(dict(joints=jointnames,keys=rows),indent=2))
