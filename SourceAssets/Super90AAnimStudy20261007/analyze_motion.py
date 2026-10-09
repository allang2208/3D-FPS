"""Study RTM articulation and infer observable joint pivots; not a UE retarget.

A rigid joint pivot p obeys D_parent(t)*p = D_child(t)*p. Fit across keys,
report residual and rank, and use only well-constrained fits as research paths.
No source rest orientation, full source rig, prop contact or anatomy is assumed.
"""
from pathlib import Path
import ast,json,math,csv
import numpy as np
from scipy.spatial.transform import Rotation
from scipy.signal import find_peaks
O=Path(__file__).parent
data=json.loads((O/'rtm_frames.json').read_text());frames=data['frames'];bones=data['bones']
phases=np.array([f['phase'] for f in frames]);seconds=phases/.28
tree=ast.parse((O/'Sources/Arma3ObjectBuilder_data.py').read_text())
hierarchy=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='ofp2_manskeleton' for t in n.targets))
lookup={n.lower():n for n in bones}
parents={lookup[n.lower()]:lookup.get(p.lower()) for n,p in hierarchy.items() if n.lower() in lookup}
def mat(v):
    return np.array([[v[0],v[6],v[3],v[9]],[v[2],v[8],v[5],v[11]],[v[1],v[7],v[4],v[10]],[0,0,0,1.]])
D={n:np.array([mat(f['deformation'][n]) for f in frames]) for n in bones}
curves={}
report={'source':'m1014_Reload.rtm','phase_rate':.28,'duration_from_config':1/.28,
        'limitations':['Joint pivots are inferred, not the original bind skeleton.',
                      'Angles are parent-relative changes, not anatomical joint angles.',
                      'No prop contact, exact loader operation, or UE playback is established.'],
        'parents':parents,'local_excursions':{},'pivot_fit':{},'key_events':[]}
for n in bones:
    if not n.startswith(('Left','Right')) or any(t in n for t in ('Leg','Foot','Toe')):continue
    p=parents.get(n)
    if p not in D:continue
    local=np.linalg.inv(D[p])@D[n]
    rotations=Rotation.from_matrix(local[:,:3,:3]);angles=np.degrees((rotations*rotations[0].inv()).magnitude())
    changes=np.degrees((rotations[1:]*rotations[:-1].inv()).magnitude())
    curves[n]=angles
    i=int(np.argmax(angles))
    report['local_excursions'][n]={'parent':p,'peak_change_deg':float(angles[i]),'peak_phase':float(phases[i]),'max_key_step_deg':float(max(changes))}
    A=(D[p][:,:3,:3]-D[n][:,:3,:3]).reshape(-1,3);b=(D[n][:,:3,3]-D[p][:,:3,3]).reshape(-1)
    point,_,rank,sv=np.linalg.lstsq(A,b,rcond=1e-7)
    residual=(A@point-b).reshape(-1,3);dist=np.linalg.norm(residual,axis=1)
    condition=float(sv[0]/sv[-1]) if sv[-1]>1e-10 else None
    usable=rank==3 and condition is not None and condition<100 and max(dist)<.002
    report['pivot_fit'][n]={'parent':p,'rank':int(rank),'condition':condition,'rms_cm':float(np.sqrt(np.mean(dist**2))*100),'max_cm':float(max(dist)*100),'rest_point':point.tolist(),'usable':bool(usable)}
paths={}
for n,fit in report['pivot_fit'].items():
    if not fit['usable']:continue
    h=np.r_[fit['rest_point'],1.]
    paths[n]=np.einsum('nij,j->ni',D[n],h)[:,:3]
report['arm_lengths']={}
for side in ('Left','Right'):
    names=[side+'Arm',side+'ForeArm',side+'Hand']
    if all(n in paths for n in names):
        a,e,w=[paths[n] for n in names]
        lengths=np.stack([np.linalg.norm(e-a,axis=1),np.linalg.norm(w-e,axis=1)],axis=1)
        report['arm_lengths'][side]={'mean_cm':(lengths.mean(axis=0)*100).tolist(),'range_cm':((lengths.max(axis=0)-lengths.min(axis=0))*100).tolist()}
if 'LeftHand' in paths:
    hp=np.c_[paths['LeftHand'],np.ones(len(frames))]
    for gun in ('Weapon','weapon1'):
        gp=np.einsum('nij,nj->ni',np.linalg.inv(D[gun]),hp)[:,:3]
        travel=np.linalg.norm(gp-gp[0],axis=1);speed=np.linalg.norm(np.gradient(gp,seconds,axis=0),axis=1)
        peaks,_=find_peaks(travel,prominence=.025,distance=6)
        for i in peaks:report['key_events'].append({'space':gun,'kind':'left_wrist_excursion_peak','phase':float(phases[i]),'config_seconds':float(seconds[i]),'distance_from_first_cm':float(travel[i]*100)})
        report.setdefault('left_wrist_in_gun',{})[gun]={'positions':gp.tolist(),'distance_from_first_cm':(travel*100).tolist(),'speed_cm_s':(speed*100).tolist()}
        report.setdefault('gun_motion',{})[gun]={'relative_to_right_hand':float(max(np.degrees((Rotation.from_matrix(D[gun][:,:3,:3])*Rotation.from_matrix(D['RightHand'][:,:3,:3]).inv()* (Rotation.from_matrix(D[gun][0,:3,:3])*Rotation.from_matrix(D['RightHand'][0,:3,:3]).inv()).inv()).magnitude())))}
rows=[]
for i,p in enumerate(phases):
    rows.append({'phase':float(p),'seconds':float(seconds[i]),'joints':{n:v[i].tolist() for n,v in paths.items()}})
(O/'inferred_joint_paths.json').write_text(json.dumps({'method':'shared rigid pivot least squares','rows':rows},separators=(',',':')))
(O/'motion_study.json').write_text(json.dumps(report,indent=2))
with (O/'parent_relative_motion.csv').open('w',newline='',encoding='utf-8-sig') as file:
    fields=['phase','config_seconds']+list(curves)
    writer=csv.writer(file);writer.writerow(fields)
    for i,p in enumerate(phases):writer.writerow([p,seconds[i]]+[v[i] for v in curves.values()])
print('PIVOTS',json.dumps({n:f for n,f in report['pivot_fit'].items() if n in ('LeftArm','LeftForeArm','LeftHand','RightArm','RightForeArm','RightHand')}))
print('LOCAL_FINGERS',json.dumps({n:f for n,f in report['local_excursions'].items() if n.startswith('LeftHand')}))
print('KEY_EVENTS',json.dumps(report['key_events']))
print('LENGTHS',json.dumps(report['arm_lengths']))
