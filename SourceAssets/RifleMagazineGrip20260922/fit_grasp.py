"""Fit the accepted VRE grouped grasp to each rifle's actual magazine shell.

Only the whole hand and shared joint closure amplitudes are fitted. Finger
translations, rest transforms, bone lengths and skin weights stay native.
"""
import json,sys
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from scipy.spatial import cKDTree
from scipy.spatial import ConvexHull
from scipy.optimize import minimize
import trimesh

O=Path(__file__).parent
D=json.loads((O/'fit_input.json').read_text())
names=D['names']; rest={n:np.array(m) for n,m in D['rest'].items()}
inverse={n:np.linalg.inv(m) for n,m in rest.items()}
local={n:inverse[D['parents'][n]]@rest[n] for n in names if n!='hand_l'}
donor={n:Rotation.from_matrix(np.array(m)[:3,:3]).as_rotvec() for n,m in D['donor_basis'].items() if n in names}
H0=np.array(D['hand_in_mag']); vertices=np.c_[np.array(D['vertices']),np.ones(len(D['vertices']))]
palm_forward=rest['middle_01_l'][:3,3]-rest['hand_l'][:3,3];palm_forward/=np.linalg.norm(palm_forward)
palm_across=rest['index_01_l'][:3,3]-rest['pinky_01_l'][:3,3];palm_across/=np.linalg.norm(palm_across)
palm_normal=np.cross(palm_across,palm_forward);palm_normal/=np.linalg.norm(palm_normal)
thumb_axes=rest['thumb_01_l'][:3,:3].T@np.c_[palm_normal,palm_across]
W=np.array([[w.get(n,0) for n in names] for w in D['weights']]);W/=W.sum(axis=1)[:,None]
bybone={n:vertices@inverse[n].T for n in names}
labels=np.array(D['labels']); sample=np.arange(0,len(vertices),4)
def pose(x):
    H=H0.copy();rot=Rotation.from_rotvec(np.radians(x[3:6])).as_matrix()
    H[:3,:3]=rot@H0[:3,:3];H[:3,3]+=np.array(x[:3])*.001
    p={'hand_l':H};basis={}
    for n in names[1:]:
        fields=n.split('_');k=fields[1]
        closure=x[9] if fields[0]=='thumb' else (.80 if not k.isdigit() else x[5+int(k)])
        q=Rotation.from_rotvec(donor[n]*closure)
        if n=='thumb_01_l':q=q*Rotation.from_rotvec(thumb_axes@np.radians(x[10:12]))
        b=np.eye(4);b[:3,:3]=q.as_matrix()
        p[n]=p[D['parents'][n]]@local[n]@b
        xyzw=q.as_quat();basis[n]=[float(xyzw[3]),*map(float,xyzw[:3])]
    skin=sum((bybone[n]@p[n].T)[:,:3]*W[:,i,None] for i,n in enumerate(names))
    return p,skin,basis

initial=np.array([0.,0.,0.,0.,0.,0.,.63,.86,.80,.78,0.,0.])
bounds=[(-30,30),(-30,30),(-20,20),(-25,25),(-25,25),(-25,25),(.45,.84),(.64,1.0),(.55,.95),(.60,.95),(-22,22),(-22,22)]
results={}
prior_results=json.loads((O/'grasp_fit.json').read_text()) if (O/'grasp_fit.json').exists() else {}
for gun,mag in D['magazines'].items():
    if gun.endswith('_extended'):continue
    reference=initial.copy()
    if gun=='A762':
        mag=D['magazines']['A762_extended']
        reference=np.array(results['AKM']['parameters']);reference[1]+=10.;reference[2]-=5.
        bounds[1]=(-5,20);bounds[2]=(-5,15);bounds[6]=(.32,.70)
        for axis in range(3,6):bounds[axis]=(reference[axis]-4,reference[axis]+4)
    else:bounds[2]=(-20,20)
    tri=[]
    for f in mag['faces']:
        tri.extend([[f[0],f[j],f[j+1]] for j in range(1,len(f)-1)])
    mesh=trimesh.Trimesh(vertices=mag['vertices'],faces=tri,process=False)
    triangles=mesh.triangles; centers=triangles.mean(1);tree=cKDTree(centers); normals=mesh.face_normals
    # The hollow interior and stamped ribs are not free space for fingers.
    # Slice the actual curved shell; a convex cross section supplies a solid
    # inside/outside sign without mistaking its inner wall for an outer surface.
    zgrid=np.linspace(mesh.bounds[0,2]+.001,mesh.bounds[1,2]-.001,100);hulls=[]
    for z in zgrid:
        edge_start=triangles.reshape(-1,3);edge_end=np.roll(triangles,-1,axis=1).reshape(-1,3)
        select=(edge_start[:,2]-z)*(edge_end[:,2]-z)<0
        aa=edge_start[select];bb=edge_end[select];t=(z-aa[:,2])/(bb[:,2]-aa[:,2])
        cross=aa[:,:2]+t[:,None]*(bb-aa)[:,:2]
        hulls.append(ConvexHull(cross).equations if len(cross)>3 else None)
    def distances(points):
        _,ids=tree.query(points,k=12,workers=1)
        near=trimesh.triangles.closest_point(triangles[ids.reshape(-1)],np.repeat(points,12,axis=0)).reshape(len(points),12,3)
        ds=np.sum((near-points[:,None,:])**2,2);which=ds.argmin(1);i=np.arange(len(points))
        delta=points-near[i,which];normal=normals[ids[i,which]]
        inside=np.zeros(len(points),dtype=bool);iz=np.clip(np.searchsorted(zgrid,points[:,2]),0,len(zgrid)-1)
        for zindex in np.unique(iz):
            use=iz==zindex;eq=hulls[zindex]
            if eq is not None:inside[use]=np.max(points[use,:2]@eq[:,:2].T+eq[:,2],axis=1)<-.00015
        inside&=(points[:,2]>zgrid[0])&(points[:,2]<zgrid[-1])
        return np.sqrt(ds[i,which])*np.where(inside,-1,1)
    # Probe the palm and each distal pad independently. No fingertip target
    # or unconstrained joint rotations can sacrifice the authored hand shape.
    groups={}
    for digit in ('thumb','index','middle','ring','pinky'):
        groups[digit]=np.array([i for i in sample if labels[i] in (digit+'_02_l',digit+'_03_l')])
    groups['palm']=np.array([i for i in sample if labels[i]=='hand_l'])
    def objective(x):
        _,skin,_=pose(x);d=distances(skin[sample])*1000
        penetration=np.minimum(d+1.1,0)
        value=3.5*np.mean(penetration**2)+5*np.mean(np.sort(penetration**2)[-max(3,len(d)//40):])
        for label,ids in groups.items():
            vals=distances(skin[ids])*1000
            nearest=np.sort(vals)[max(0,len(vals)//25):max(3,len(vals)//8)]
            gap=nearest.mean()
            value+=(.75 if label=='palm' else 1.5)*(gap-.7)**2
        # Keep the reference wrist approach and tightly correlated donor curl.
        value+=.015*np.sum((x[:3]-reference[:3])**2)+.004*np.sum(x[3:6]**2)
        value+=9*np.sum((x[6:10]-initial[6:10])**2)+.012*np.sum(x[10:12]**2)
        return value
    if '--draft' in sys.argv:
        x=initial;value=None
    else:
        start=reference.copy()
        if gun in prior_results:
            old=prior_results[gun].get('parameters',[])
            start[:len(old)]=old
        if gun=='A762':start=reference.copy();start[6]=.44
        solved=minimize(objective,start,method='Powell',bounds=bounds,
                        options={'maxiter':32,'xtol':.003,'ftol':.001})
        x=solved.x;value=float(solved.fun)
    p,skin,basis=pose(x)
    results[gun]={'parameters':x.tolist(),'objective':value,'hand_in_mag':p['hand_l'].tolist(),
                  'finger_basis':basis,'skin':skin.tolist(),'joints':{n:m[:3,3].tolist() for n,m in p.items()},
                  'source':'MannyGraspDonor20260912/donor_fit.json',
                  'weights_changed':False,'game_tested':False}
    print('GROUPED_GRASP',gun,results[gun]['parameters'],'cost',value,flush=True)
    (O/('draft_fit.json' if '--draft' in sys.argv else 'grasp_fit.json')).write_text(json.dumps(results))
