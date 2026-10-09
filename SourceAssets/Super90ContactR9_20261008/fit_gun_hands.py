import os
os.environ['OPENBLAS_NUM_THREADS']='1'
import numpy as np,json
from pathlib import Path
from scipy.ndimage import map_coordinates
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
O=Path(__file__).parent;D=np.load(O/'fit_inputs.npz');names=D['names'].tolist();ix={n:i for i,n in enumerate(names)}
rest=D['rest'];ri=np.linalg.inv(rest);parents=D['parents'];vs=D['vertices'];ws=D['weights'];idle=D['idle']
out=json.loads((O/'hand_fit.json').read_text(encoding='utf-8-sig'))
for side in ('r','l'):
    hand_name='hand_'+side;digits=[n for n in names if n.endswith('_'+side) and n.startswith(('thumb','index','middle','ring','pinky'))]
    selected=[hand_name]+digits;indices=[ix[n] for n in selected]
    ids=np.flatnonzero(ws[:,indices].sum(axis=1)>.995);v=vs[ids];w=ws[ids];dominant=np.argmax(w,axis=1)
    weighted={n:np.flatnonzero(w[:,ix[n]]>1e-6) for n in selected};pre={n:v[weighted[n]]@ri[ix[n]].T for n in selected}
    hand=np.array(out['right_hand_in_idle']) if side=='r' else idle[ix[hand_name]].copy()
    local={n:np.array(out['right_finger_local'][n]) if side=='r' else np.linalg.inv(idle[parents[ix[n]]])@idle[ix[n]] for n in digits}
    field=np.load(O/('gun_sdf_'+side+'.npz'));grid=field['values'].astype(np.float64);origin=field['origin'];step=float(field['step'])
    def sdf(points):return map_coordinates(grid,((points-origin)/step).T,order=1,mode='nearest')
    def matrices(h,loc):
        p={hand_name:h}
        for n in digits:p[n]=p[names[parents[ix[n]]]]@loc[n]
        return p
    def skin(p):
        result=np.zeros((len(ids),3))
        for n in selected:
            j=ix[n];vi=weighted[n];result[vi]+=(pre[n]@p[n].T)[:,:3]*w[vi,j,None]
        return result
    initial=matrices(hand,local);joints=[n for n in digits if 'metacarpal' not in n]
    axes={}
    for digit in ('thumb','index','middle','ring','pinky'):
        a,b,c=[initial[f'{digit}_0{i}_{side}'][:3,3] for i in (1,2,3)]
        axis=np.cross(b-a,c-b);axis/=np.linalg.norm(axis)
        for n in joints:
            if n.startswith(digit):axes[n]=initial[n][:3,:3].T@axis
    near={n:np.flatnonzero(dominant==ix[n]) for n in selected}
    def pose(x):
        h=hand.copy();h[:3,3]+=x[:3];h[:3,:3]=Rotation.from_rotvec(x[3:6]).as_matrix()@h[:3,:3]
        loc={n:m.copy() for n,m in local.items()}
        for n,a in zip(joints,x[6:]):loc[n][:3,:3]=loc[n][:3,:3]@Rotation.from_rotvec(axes[n]*a).as_matrix()
        return h,loc,matrices(h,loc)
    active=np.arange(len(ids))[::3]
    contacts=[hand_name]+[f'{digit}_03_{side}' for digit in ('thumb','middle','ring','pinky')]
    def residual(x):
        d=sdf(skin(pose(x)[2]));pen=np.minimum(d[active]-.0015,0)*1000*80/np.sqrt(len(active))
        contact=np.concatenate([np.maximum(np.partition(d[near[n]],5)[:5]-.0035,0)*1000*.3 for n in contacts if len(near[n])>5])
        return np.r_[pen,contact,x[:3]*1000*.02,x[3:6]*.2,x[6:]*.15]
    limits=np.r_[[.025]*3,[np.deg2rad(22)]*3,[np.deg2rad(30)]*len(joints)];x=np.full(len(limits),.0001)
    for stride in (3,1):
        active=np.arange(len(ids))[::stride]
        fit=least_squares(residual,x,bounds=(-limits,limits),max_nfev=150,ftol=1e-7,xtol=1e-7,gtol=1e-5,diff_step=.002);x=fit.x
        h,loc,p=pose(x);d=sdf(skin(p));print('GUN_GRIP',side,stride,fit.nfev,'inside',int(sum(d<0)),'min_mm',float(min(d)*1000),flush=True)
    key='right' if side=='r' else 'idle_left'
    out[key+'_hand_in_idle']=h.tolist();out[key+'_finger_local']={n:m.tolist() for n,m in loc.items()}
    out[key+'_surface_fit']={'inside_vertices':int(sum(d<0)),'min_clearance_mm':float(min(d)*1000),'parameters':x.tolist()}
    (O/'hand_fit_gun_candidate.json').write_text(json.dumps(out,indent=2))
