"""Finish each finger independently instead of forcing one curl on all digits."""
from pathlib import Path
exec(compile((Path(__file__).parent/'fit_hold_surface.py').read_text().split('fit=least_squares')[0],__file__,'exec'))
digitnames=sorted(n for n in hb if 'metacarpal' not in n and n!='hand_l')
forward=unit(B['middle_01_l'][:3,3]-B['hand_l'][:3,3]);across=unit(B['index_01_l'][:3,3]-B['pinky_01_l'][:3,3]);palmar=unit(np.cross(forward,across))
if palmar@(B['middle_03_l'][:3,3]-B['middle_01_l'][:3,3])<0:palmar=-palmar
pads=[]
for finger in ('index','middle','ring','pinky'):
    bone=finger+'_03_l';j=names.index(bone);ids=np.array([i for i,ws in enumerate(g['weights']) if sum(w for b,w in ws if b==j)>.70])
    points=v[ids]-B[bone][:3,3];axial=points@rot(B[bone])[:,0];lo,hi=np.quantile(axial,[.30,.75]);ids=ids[(axial>=lo)&(axial<=hi)];score=(v[ids]-B[bone][:3,3])@palmar;pads.append(ids[score>=np.quantile(score,.70)])
base_pose=pose
def pose(x):
    _,old=base_pose(x[:10]);w={'hand_l':old['hand_l']};q=p.copy();q[handids]=0.
    for name in hb:
        if name!='hand_l':
            local=np.linalg.inv(old[parents[name]])@old[name]
            if name in digitnames:local[:3,:3]=turn([0,0,1],x[10+digitnames.index(name)])@local[:3,:3]
            w[name]=w[parents[name]]@local
        if name in subset:
            sel,points=subset[name];q[handids[sel]]+=(points@(w[name]@np.linalg.inv(B[name])).T)[:,:3]
    return q,w
def residual(x):
    q,w=pose(x);surface=np.concatenate((q[handids],q[hf[::3]].mean(1)));d=np.max(surface@planes[:,:3].T+planes[:,3],axis=1)
    polygon=np.array([w[n][:2,3] for n in ('hand_l','middle_01_l','middle_02_l','middle_03_l')]);ep=ConvexHull(polygon).equations
    enclosure=np.max(ep[:,:2]@np.array([5.1,-28.9])+ep[:,2])
    pad_distance=np.array([np.max(q[ids].mean(0)@planes[:,:3].T+planes[:,3]) for ids in pads])
    return np.r_[np.maximum(0,.15-d)*12.,max(0,enclosure+.25)*30.,(w['middle_02_l'][2,3]+18.8)*10.,(pad_distance-.15)*12.,x[:3]*.02,(x[3:7]-1)*.3,x[7:]*.25]
x0=np.array(json.loads((r/'hold_fit_digits.json').read_text())['parameters']) if (r/'hold_fit_digits.json').exists() else np.r_[json.loads((r/'hold_fit_surface.json').read_text())['parameters'],np.zeros(len(digitnames))]
lower=[-5.,-3.,-6.,-.6,-.4,-.2,-.2,-.5,-.5,-.5]+[-.65]*len(digitnames)
upper=[3.,6.,0.,1.15,1.15,1.15,1.15,.5,.5,.5]+[.65]*len(digitnames)
fit=least_squares(residual,x0,bounds=(lower,upper),diff_step=1.e-5,max_nfev=80,verbose=1,xtol=1.e-10)
q,w=pose(fit.x);hits=collisions(q);out=dict(parameters=fit.x.tolist(),digit_names=digitnames,hits=hits,hand_world={n:a.tolist() for n,a in w.items()})
(r/'hold_fit_digits.json').write_text(json.dumps(out,indent=2));print('HOLD_DIGIT_FIT',out['parameters'],hits,flush=True)
