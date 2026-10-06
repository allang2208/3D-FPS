"""Correct only the three wrapping fingers; retain the established thumb/index gesture."""
exec((__import__('pathlib').Path(__file__).parent/'fit_natural.py').read_text().split('parameters=[];limits=[]')[0])
parameters=[];limits=[];lower_limits=[]
for i in chain:
    name=names[i]
    if not name.startswith(('middle','ring','pinky')) or 'metacarpal' in name:continue
    axis=np.cross(base[parent[i],:3,1],base[i,:3,1]);axis=base[i,:3,:3].T@axis
    if np.linalg.norm(axis)<.1:axis=np.array((0.,0.,1.))
    axis/=np.linalg.norm(axis)
    parameters.append((i,axis));lower_limits.append(-70. if '_03_' in name else -35. if '_02_' in name else -20.);limits.append(10. if '_03_' in name else 25. if '_02_' in name else 20.)
    if '_01_' in name:
        splay=np.cross(axis,np.array((0.,1.,0.)));splay/=np.linalg.norm(splay)
        parameters.append((i,splay));lower_limits.append(-10.);limits.append(10.)
def pose(x):
    p=base.copy();deltas={i:np.eye(3) for i in chain}
    for (i,axis),v in zip(parameters,x):deltas[i]=deltas[i]@R.from_rotvec(axis*np.radians(v)).as_matrix()
    for i in chain:
        li=local[i].copy();li[:3,:3]=li[:3,:3]@deltas[i];p[i]=p[parent[i]]@li
    return p
def pts(x):return np.einsum('bij,bpj,pb->pi',pose(x)[used],bound,weights,optimize=True)[:,:3]
ids=np.flatnonzero(np.array([n.startswith(('middle','ring','pinky')) and 'metacarpal' not in n for n in labels]))
x=np.zeros(len(limits));original=pts(x)
tips={f:np.flatnonzero(labels==f+'_03_'+side) for f in ('middle','ring','pinky')}
def residual(x):
    points=pts(x);d=distances(points[ids]);inside=np.minimum(d-.25,0)
    r=[inside*.7,np.sort(inside)[:60]*2.,x*.09]
    for f in tips:
        g=tips[f];r.append(np.array([max(0,distances(points[g]).min()-1.)*2.]))
        r.append((points[g].mean(0)-original[g].mean(0))*1000*.05)
    return np.concatenate(r)
result=least_squares(residual,x,bounds=(lower_limits,limits),max_nfev=180,diff_step=.001,ftol=1e-6,xtol=1e-6)
x=result.x;p=pose(x);ds=distances(pts(x)[ids]);deltas={}
for i in chain:
    lp=np.linalg.inv(p[parent[i]])@p[i];deltas[names[i]]=R.from_matrix(lp[:3,:3]@np.linalg.inv(local[i,:3,:3])).as_quat().tolist()
print('WRAP_FIT',family,side,kind,round(result.cost,2),round(max(0,-ds.min()),3),int((ds<-.5).sum()),[(names[i],round(v,2)) for (i,a),v in zip(parameters,x)],flush=True)
(O/f'wrap_{family}_{side}_{kind}.json').write_text(json.dumps(dict(family=family,side=side,kind=kind,parameters=x.tolist(),offset_grip_m=[0,0,0],wrist_local_quat=[0,0,0,1],finger_local_delta=deltas,sdf_penetration_max_mm=float(max(0,-ds.min())),sdf_inside_half_mm=int((ds<-.5).sum()),cost=float(result.cost)),indent=2))
