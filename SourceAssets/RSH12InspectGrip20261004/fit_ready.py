"""Trigger-finger and thumb contact over the common palm / three-finger grasp."""
import sys
sys.argv[1:4]=['ready','r','idle']
exec((__import__('pathlib').Path(__file__).parent/'fit_contact.py').read_text().split('params=')[0].replace("'grip_sdf.npz'","'full_sdf.npz'"))
active=[i for i in chain if names[i].startswith(('index','thumb'))]
limits=np.array([12. if 'metacarpal' in names[i] else 80. for i in active for a in (0,1,2)])
def pose(x):
    p=base.copy();rr=np.radians(x.reshape(-1,3));rs=Rotation.from_rotvec(rr).as_matrix()
    for k,i in enumerate(active):
        li=local[i].copy();li[:3,:3]=li[:3,:3]@rs[k];p[i]=p[parents[i]]@li
    return p
def points(x):return np.einsum('bij,bpj,pb->pi',pose(x)[used],bound,weights,optimize=True)[:,:3]
index=np.flatnonzero(labels=='index_03_r');thumb=np.flatnonzero(labels=='thumb_03_r');x=np.zeros(len(limits));source=points(x)
target_index=np.array((.009,.107,-.005));target_thumb=np.array((.033,.133,-.013))
pip=names.index('index_02_r');dip=names.index('index_03_r')
pip_target=np.array((-.026,.112,-.003));dip_target=np.array((-.005,.101,-.009))
def seed_residual(x):
    pp=points(x);p=pose(x)
    return np.r_[(pp[index].mean(0)-target_index)*1000*3.,(p[pip,:3,3]-pip_target)*1000*1.5,(p[dip,:3,3]-dip_target)*1000*1.5,(pp[thumb].mean(0)-target_thumb)*1000,x*.05]
seed=least_squares(seed_residual,x,bounds=(-limits,limits),max_nfev=100,diff_step=.002)
x=seed.x
def residual(x):
    pp=points(x);d=distance(pp);inside=np.minimum(d-.65,0)
    return np.concatenate((inside*3.,np.sort(inside)[:80]*8.,x*.09,(pp[index].mean(0)-target_index)*1000*2.5,(pp[thumb].mean(0)-target_thumb)*1000*.8))
result=least_squares(residual,x,bounds=(-limits,limits),diff_step=.002,max_nfev=160,ftol=1e-6,xtol=1e-6)
x=result.x;p=pose(x);ds=distance(points(x));rots={}
for i in active:
    lp=np.linalg.inv(p[parents[i]])@p[i];rots[names[i]]=Rotation.from_matrix(lp[:3,:3]@np.linalg.inv(local[i,:3,:3])).as_quat().tolist()
(O/'ready_index_thumb.json').write_text(json.dumps(dict(local_delta=rots,parameters=x.tolist(),sdf_max_mm=float(max(0,-ds.min())),inside_half_mm=int((ds<-.5).sum())),indent=2))
print('READY_FIT',round(max(0,-ds.min()),3),int((ds<-.5).sum()),'INDEX_PAD',points(x)[index].mean(0).tolist(),flush=True)
