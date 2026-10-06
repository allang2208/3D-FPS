"""Fit a complete grasp with index on the frame exterior and three separate contact pads."""
exec((__import__('pathlib').Path(__file__).parent/'fit_contact.py').read_text().split('params=')[0].replace("'grip_sdf.npz'","'full_sdf.npz'"))
params=[('move',a) for a in range(3)]+[('wrist',a) for a in range(3)]+[(names[i],a) for i in chain for a in (0,2)]
limits=np.array([25.,8.,8.]+[6.]*3+[5. if 'metacarpal' in n else 22. if n.startswith(('index','thumb')) else 65. for n,a in params[6:]])
lower_limits=-limits.copy();limits[0]=2. if side=='r' else 25.;lower_limits[0]=-25. if side=='r' else -2.
def pose(x):
    p=base.copy();p[hand,:3,3]+=x[:3]*.001;p[hand,:3,:3]=base[hand,:3,:3]@Rotation.from_rotvec(np.radians(x[3:6])).as_matrix()
    rr=np.zeros((len(chain),3));rr[:,(0,2)]=np.radians(x[6:].reshape(-1,2));rotations=Rotation.from_rotvec(rr).as_matrix()
    for k,i in enumerate(chain):
        li=local[i].copy();li[:3,:3]=li[:3,:3]@rotations[k];p[i]=p[parents[i]]@li
    return p
def points(x):return np.einsum('bij,bpj,pb->pi',pose(x)[used],bound,weights,optimize=True)[:,:3]
x=np.zeros(len(params));original=points(x);x[0]=-18. if side=='r' else 18.
tips={f:np.flatnonzero(labels==f+'_03_'+side) for f in ('thumb','index','middle','ring','pinky')}
means={f:original[g].mean(0) for f,g in tips.items()}
ids=np.arange(0,len(labels),2)
def residual(x):
    pp=points(x);p=pose(x);d=distance(pp[ids]);inside=np.minimum(d-.35,0.)
    r=[inside*.65,np.sort(inside)[:100]*2.,x[:3]*np.array((.05,.2,.2)),x[3:6]*.25,x[6:]*.09]
    for f in tips:
        target=means[f].copy()
        if f=='index':target[0]=-.028 if side=='r' else .028
        elif f=='thumb':target[0]=.032 if side=='r' else -.032
        else:target[0]=.023 if side=='r' else -.023
        r.append((pp[tips[f]].mean(0)-target)*1000*np.array((2.,1.,1.2)))
    for f in ('middle','ring','pinky'):
        r.append(np.array([max(0,distance(pp[tips[f]]).min()-1.)*3.]))
        for segment in ('01','02','03'):
            i=names.index(f+'_'+segment+'_'+side)
            r.append(np.array([(p[i,2,3]-base[i,2,3])*1000*.4]))
    return np.concatenate(r)
path=O/f'production_{family}_{side}_{kind}.json'
if path.exists():x=np.array(json.loads(path.read_text())['parameters'])
refine=len(sys.argv)>4 and sys.argv[4]=='refine'
if refine:
    anchor=x.copy();source_residual=residual
    lower_limits=np.maximum(lower_limits,x-np.array([2.]*3+[2.]*3+[12.]*(len(x)-6)))
    limits=np.minimum(limits,x+np.array([2.]*3+[2.]*3+[12.]*(len(x)-6)))
    def residual(x):
        d=distance(points(x)[ids]);inside=np.minimum(d-1.0,0.)
        return np.concatenate((inside*5.,np.sort(inside)[:100]*12.,source_residual(x)*.2,(x-anchor)*.2))
for stage in range(2):
    if stage:ids=np.arange(len(labels))
    result=least_squares(residual,x,bounds=(lower_limits,limits),diff_step=.002,max_nfev=180,ftol=1e-6,xtol=1e-6,gtol=1e-4)
    x=result.x;d=distance(points(x));print('PRODUCTION_FIT',family,side,kind,stage,round(result.cost,2),round(max(0,-d.min()),3),int((d<-.5).sum()),x[:6].round(2).tolist(),flush=True)
p=pose(x);rots={}
for i in chain:
    lp=np.linalg.inv(p[parents[i]])@p[i];rots[names[i]]=Rotation.from_matrix(lp[:3,:3]@np.linalg.inv(local[i,:3,:3])).as_quat().tolist()
path.write_text(json.dumps(dict(family=family,side=side,kind=kind,parameters=x.tolist(),offset_grip_m=(x[:3]*.001).tolist(),wrist_local_quat=Rotation.from_rotvec(np.radians(x[3:6])).as_quat().tolist(),finger_local_delta=rots,sdf_penetration_max_mm=float(max(0,-d.min())),sdf_inside_half_mm=int((d<-.5).sum()),cost=float(result.cost)),indent=2))
