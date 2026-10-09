"""Author a V7 grasp against the actual rounded rectangular game prop surface.

Only wrist rigid fit and digit flexion are solved. Native translations, scales,
axial finger roll and the mesh bind remain unchanged. This is an authoring step,
not a rendered or runtime acceptance test.
"""
import json
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation

O=Path(__file__).parent
D=json.loads((O/'grasp_skin_inputs.json').read_text())
names=D['names']; parents=D['parents']; index={n:i for i,n in enumerate(names)}
rest={n:np.array(v) for n,v in D['rest'].items()}
world={n:np.array(v) for n,v in D['grasp'].items()}
frame=np.array(D['frame']); invframe=np.linalg.inv(frame)
base={n:np.linalg.inv(world[parents[n]])@world[n] for n in names if n!='hand_l'}
hand=invframe@world['hand_l']
vertices=D['vertices']; count=len(vertices)
weighted=[]
for n in names:
    ids=np.array([i for i,v in enumerate(vertices) if n in v['weights']],dtype=int)
    weights=np.array([vertices[i]['weights'][n] for i in ids])
    p=np.array([vertices[i]['p']+[1.] for i in ids])@np.linalg.inv(rest[n]).T
    weighted.append((ids,weights,p))

def skin(matrices):
    out=np.zeros((count,3))
    for n,(ids,weights,p) in zip(names,weighted):
        out[ids]+=(p@matrices[n].T)[:,:3]*weights[:,None]
    return out

donor={n:invframe@world[n] for n in names}
surface0=skin(donor)
dominant=[max(v['weights'],key=v['weights'].get) for v in vertices]
joints=[n for n in names if n!='hand_l' and 'metacarpal' not in n]
# Digits encircle the handle along its long Z axis; rotation around this
# anatomical flexion plane preserves the donor's accepted axial bone roll.
axes={n:donor[n][:3,:3].T@np.array([0.,0.,1.]) for n in joints}
# The thumb opposes the four fingers and bends in its own anatomical plane.
t1,t2,t3=(donor['thumb_0%d_l'%i][:3,3] for i in (1,2,3))
thumb_axis=np.cross(t2-t1,t3-t2);thumb_axis/=np.linalg.norm(thumb_axis)
for n in joints:
    if n.startswith('thumb'):axes[n]=donor[n][:3,:3].T@thumb_axis

def rounded_box(points,center,half,radius):
    q=np.abs(points-np.array(center))-(np.array(half)-radius)
    return np.linalg.norm(np.maximum(q,0),axis=1)+np.minimum(np.max(q,axis=1),0)-radius

def sdf(p):
    d=rounded_box(p,[0,0,0],[.016,.015,.047],.006)
    d=np.minimum(d,rounded_box(p,[0,0,.012],[.0195,.006,.014],.002))
    for z in (-.036,-.025,-.014,.014,.025,.036):
        d=np.minimum(d,rounded_box(p,[0,-.015,z],[.0155,.002,.0015],.001))
    return d

# Fit inward-facing skin patches, not the wrist or dummy Blender bone tails.
# Each phalanx keeps a small patch on the side facing the actual handle.
contacts={}
for n in joints+['hand_l']:
    ids=np.array([i for i,b in enumerate(dominant) if b==n],dtype=int)
    if n=='hand_l':
        ids=ids[(surface0[ids,2]>-.035)&(surface0[ids,2]<.035)&(surface0[ids,0]>-.04)]
    distance=sdf(surface0[ids])
    contacts[n]=ids[np.argsort(distance)[:min(10,len(ids))]]

def pose(x):
    h=hand.copy()
    h[:3,:3]=Rotation.from_rotvec(x[3:6]).as_matrix()@h[:3,:3]
    h[:3,3]+=x[:3]
    local={n:m.copy() for n,m in base.items()}
    for n,angle in zip(joints,x[6:]):
        local[n][:3,:3]=local[n][:3,:3]@Rotation.from_rotvec(axes[n]*angle).as_matrix()
    posed={'hand_l':h}
    for n in names[1:]:posed[n]=posed[parents[n]]@local[n]
    return posed,local

def residual(x):
    posed,_=pose(x);points=skin(posed);distance=sdf(points)
    penetration=np.minimum(distance-.0005,0)*1000/np.sqrt(count)
    patches=np.concatenate([(distance[ids]-.0007)*1000/np.sqrt(len(ids))*.8 for ids in contacts.values() if len(ids)])
    regularization=np.r_[x[:3]*1000*.06,x[3:6]*2.,x[6:]*.35]
    return np.r_[penetration*5.,patches,regularization]

bounds=np.r_[[.025,.030,.008],[np.deg2rad(12)]*3,[np.deg2rad(38)]*len(joints)]
result=least_squares(residual,np.zeros(6+len(joints)),bounds=(-bounds,bounds),max_nfev=140,
                     ftol=1e-7,xtol=1e-7,gtol=1e-6,diff_step=.002)
posed,local=pose(result.x)
output={'method':'Native V7 skin patches fitted to the authored palm bar, yoke and ribs; fixed native bone offsets and roll',
        'hand_in_handle':posed['hand_l'].tolist(), 'finger_local':{n:m.tolist() for n,m in local.items()},
        'fit_parameters':{'wrist_translation_m':result.x[:3].tolist(),'wrist_rotation_degrees':np.rad2deg(result.x[3:6]).tolist(),
                          'finger_flex_degrees':dict(zip(joints,np.rad2deg(result.x[6:]).tolist()))},
        'contact_vertex_ids':{n:[vertices[i]['id'] for i in ids] for n,ids in contacts.items()},
        'runtime_tested':False}
(O/'handle_grasp.json').write_text(json.dumps(output,indent=2),encoding='utf-8')
print('HANDLE_GRASP_AUTHORED',result.nfev,'iterations; native lengths retained',flush=True)
