"""Adapt native finger curls to the thicker SVCh grip, using skinned surfaces."""
from contact_inputs import *
from scipy.optimize import least_squares
import trimesh
FIT=json.loads((O/'contact_fit.json').read_text())
TARGET=json.loads((O/'contact_meshes.json').read_text())
BASE_LOCAL=matrices(D['clips']['idle']['frames'][0])
import sys
order_only='--preserve-order' in sys.argv
OUT=json.loads((O/'finger_fit.json').read_text()) if order_only else {'bones':{},'source':'native SVD fingers; swing-only joint corrections; unchanged bone lengths'}
dominant=W.argmax(1)
for side in ('r','l'):
    if order_only and side!='r':continue
    f=FIT[side];mesh=TARGET[f['surface']];target=trimesh.Trimesh(mesh['positions'],mesh['triangles'],process=False)
    c=np.eye(4);c[:3,:3]=Rotation.from_rotvec(f['rotation_vector']).as_matrix()
    pivot=np.asarray(f['pivot_bind_cm']);c[:3,3]=pivot+f['translation_cm']-c[:3,:3]@pivot
    hi=N.index('hand_'+side);hand=IDLE[ROOT]@VRI[ROOT]@c@VR[ROOT]@np.linalg.inv(IDLE[ROOT])@IDLE[hi]
    local=BASE_LOCAL.copy();local[hi]=np.linalg.inv(IDLE[PI[hi]])@hand
    base=components(local)
    for digit in ('thumb','index','middle','ring','pinky'):
        if order_only and digit not in ('ring','pinky'):continue
        local=BASE_LOCAL.copy();local[hi]=np.linalg.inv(IDLE[PI[hi]])@hand
        if order_only:
            for name,fit in OUT['bones'].items():
                if name.endswith('_'+side) and not name.startswith(digit):
                    ni=N.index(name);local[ni,:3,:3]=Rotation.from_rotvec(fit['rotation_vector']).as_matrix()@local[ni,:3,:3]
        base=components(local)
        chain=[N.index(digit+'_%02d_'%j+side) for j in (1,2,3)]
        meta=digit+'_metacarpal_'+side
        if meta in N:chain.insert(0,N.index(meta))
        influenced=[i for i,n in enumerate(N) if n.startswith(digit) and n.endswith('_'+side)]
        ids=np.where(W[:,influenced].sum(1)>.1)[0]
        if not len(ids):continue
        start=skin(base,ids)
        # Contact fit uses the closest skin patch, excluding deep initial overlaps
        # from the target-selection step. Penetrations themselves stay in the loss.
        cp,ds,tr=trimesh.proximity.closest_point(target,start)
        pads=np.argsort(ds)[:24]
        terminal=np.where(W[ids,chain[-1]]>.7)[0]
        if side=='r' and digit=='index':
            pads=terminal[np.argsort(np.linalg.norm(start[terminal]-[6.07,-21.681,-7.068],axis=1))[:12]]
        axes=[]
        for j,bi in enumerate(chain):
            # Rotations perpendicular to the bone shaft; no arbitrary axial twist.
            shaft=BASE_LOCAL[chain[j+1],:3,3] if j<len(chain)-1 else BASE_LOCAL[bi,:3,:3].T@BASE_LOCAL[bi,:3,3]
            shaft=shaft/max(np.linalg.norm(shaft),1e-9)
            a=np.cross(shaft,[0,0,1])
            if np.linalg.norm(a)<.01:a=np.cross(shaft,[0,1,0])
            a/=np.linalg.norm(a);b=np.cross(shaft,a);axes.append(np.stack([a,b]))
        sample=np.arange(len(ids))
        original_tip=(TO_BIND@base[chain[-1]])[:3,3]
        def pose(x):
            ll=local.copy()
            for j,bi in enumerate(chain):ll[bi,:3,:3]=ll[bi,:3,:3]@Rotation.from_rotvec(x[j*2:j*2+2]@axes[j]).as_matrix()
            return components(ll)
        def residual(x):
            posed=pose(x);points=skin(posed,ids)
            cp,ds,tr=trimesh.proximity.closest_point(target,points[sample])
            signed=np.einsum('ij,ij->i',points[sample]-cp,target.face_normals[tr])
            penetration=np.minimum(signed+.045,0)*15
            if side=='r' and digit=='index':
                contact=(points[pads].mean(0)-[6.07,-21.681,-7.068])*8
            else:
                pp,dd,tt=trimesh.proximity.closest_point(target,points[pads])
                contact=((points[pads]-pp)-target.face_normals[tt]*.06).ravel()
            # A surface-only solve can exchange ring/pinky height by sliding
            # along the grip. Keep the native finger order along gun-up.
            order=[((TO_BIND@posed[chain[-1]])[2,3]-original_tip[2])*15] if order_only else []
            return np.r_[penetration,contact,x*(1.0 if side=='r' else 3.0),order]
        bounds=np.full(len(chain)*2,.65 if side=='r' else .16)
        if meta in N:bounds[:2]=.20 if side=='r' else .08
        sol=least_squares(residual,np.zeros(len(chain)*2),bounds=(-bounds,bounds),max_nfev=75,diff_step=.0005,ftol=1e-5)
        final=skin(pose(sol.x),ids)
        cp,ds,tr=trimesh.proximity.closest_point(target,final)
        signed=np.einsum('ij,ij->i',final-cp,target.face_normals[tr])
        for j,bi in enumerate(chain):
            # Persist in the parent frame consumed by FWeaponGripClip::ApplyLocal.
            rv=Rotation.from_matrix(BASE_LOCAL[bi,:3,:3]).apply(sol.x[j*2:j*2+2]@axes[j])
            OUT['bones'][N[bi]]={'rotation_vector':rv.tolist(),'side':side}
        print('SVCH_FINGER',side,digit,'max_swing_deg',round(np.degrees(max(np.linalg.norm(sol.x[j*2:j*2+2]@axes[j]) for j in range(len(chain)))),2),
              'inside_1.5mm',int(np.count_nonzero(signed<-.15)),'min_cm',round(float(signed.min()),3),flush=True)
(O/'finger_fit.json').write_text(json.dumps(OUT,indent=1))
