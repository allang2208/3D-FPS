"""Author two coordinated native-arm poses and skin them with V9 production data.

Candidate only. No Content, game code, installed assets, or source rigs change.
The JSON controls and full bone matrices remain available for later integration.
"""
import json, sys
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R

P = Path(__file__).resolve().parent
ROOT = P.parents[1]
V9 = ROOT/'SourceAssets/BareSkinV9Rollout_20261017'
sys.path.insert(0, str(V9))
from jc import Driver

def read(path): return json.loads(path.read_text(encoding='utf-8-sig'))
def unit(v): return np.asarray(v, float)/np.linalg.norm(v)
def matrix(q, p):
    m=np.eye(4);m[:3,:3]=q;m[:3,3]=p;return m
def frame(x,z):
    x=unit(x);z=unit(z-x*np.dot(x,z));return np.column_stack((x,np.cross(z,x),z))
def convert(m):
    m=np.array(m);s=np.diag([1,-1,1]);return matrix(s@m[:3,:3]@s,100*s@m[:3,3])
def rest_of(s): return {n:matrix(R.from_quat(b['q']).as_matrix(),b['t']) for n,b in s['bones'].items()}
def parents_of(s):
    names={b['index']:n for n,b in s['bones'].items()}
    return {n:names.get(b['parent']) for n,b in s['bones'].items()}
def chain(n, root, parents):
    while n:
        if n==root:return True
        n=parents[n]
    return False

controls=read(P/'pose_controls.json')
left=read(V9/'Snapshots/01e184ddd1b7.json')
right=read(V9/'Snapshots/8f309afe12dd.json')
LR,RR=rest_of(left),rest_of(right)
LP,RP=parents_of(left),parents_of(right)
src=read(P/'contact_source.json')
sr={n:convert(m) for n,m in src['rest'].items()}
raw=read(V9/'ClipsTrue/M1911.json')
grip=read(ROOT/'SourceAssets/SpellbookEvildeer20261009/GripPhotoV3/grip.json')
mount=np.array(grip['book_in_hand'])@np.diag([1,-1,-1,1])
carry={n:m.copy() for n,m in LR.items()}
for n,m in grip['poses'][0]['component'].items():carry[n]=np.array(m)

def solve_arm(rest, source, parents, side, shoulder, wrist, pole, hand_rotation, hand_roll=0.):
    """Coherent elbow hinge + native 100/50 forearm roll; grasp locals untouched."""
    C,U,E,H=[n+'_'+side for n in ('clavicle','upperarm','lowerarm','hand')]
    ru=rest[E][:3,3]-rest[U][:3,3];rl=rest[H][:3,3]-rest[E][:3,3]
    a,b=np.linalg.norm(ru),np.linalg.norm(rl)
    shoulder=np.asarray(shoulder,float);wrist=np.asarray(wrist,float);pole=np.asarray(pole,float)
    reach=wrist-shoulder;dist=np.linalg.norm(reach)
    # Move the arm root only when a fixed wrist exceeds the authored reach cap.
    if dist>(a+b)*.94:shoulder+=unit(reach)*(dist-(a+b)*.94)
    axis=unit(wrist-shoulder);dist=np.linalg.norm(wrist-shoulder)
    along=(a*a-b*b+dist*dist)/(2*dist);centre=shoulder+axis*along
    bend=unit(pole-centre-axis*np.dot(pole-centre,axis))
    elbow=centre+bend*np.sqrt(max(0,a*a-along*along))
    ud=unit(elbow-shoulder);ld=unit(wrist-elbow);normal=unit(np.cross(ud,ld))
    hand_rotation=R.from_rotvec(ld*np.radians(hand_roll)).as_matrix()@hand_rotation
    normal0=unit(np.cross(ru,rl))
    uq=frame(ud,normal)@frame(ru,normal0).T
    lq=frame(ld,normal)@frame(rl,normal0).T
    out={n:m.copy() for n,m in source.items()}
    out[U]=matrix(uq@rest[U][:3,:3],shoulder)
    out[E]=matrix(lq@rest[E][:3,:3],elbow)
    out[H]=matrix(hand_rotation,wrist)
    out[C][:3,3]+=shoulder-source[U][:3,3]
    delta=hand_rotation@rest[H][:3,:3].T@lq.T
    q=R.from_matrix(delta).as_quat()
    if q[3]<0:q=-q
    roll=2*np.arctan2(np.dot(q[:3],ld),q[3])
    for n in out:
        if not chain(n,C,parents) or n in (C,U,E,H):continue
        par=parents[n]
        # Twist helpers come from their native rest, fingers from the saved grip.
        donor=rest if 'twist_' in n else source
        out[n]=out[par]@np.linalg.inv(donor[par])@donor[n]
        if n in ('lowerarm_twist_01_'+side,'lowerarm_twist_02_'+side):
            factor=1. if '_01_' in n else .5
            out[n][:3,:3]=R.from_rotvec(ld*roll*factor).as_matrix()@out[n][:3,:3]
    return out

def pistol_pose(kind):
    # Bone basis differences introduced by FBX are transported through each
    # bone's own rest frame. Saved raw UE contact fingers supersede source hands.
    pose={n:(convert(src['poses'][kind][n])@np.linalg.inv(sr[n])@RR[n] if n in sr else RR[n].copy()) for n in RR}
    clip=raw['clips']['/Game/Weapons/M1911/Contact20260913/Animations/A_M1911_'+kind]
    for n,row in zip(raw['bones'],clip['frames'][0]):pose[n]=matrix(R.from_quat(row[3:7]).as_matrix(),row[:3])
    if kind=='idle':
        xf=matrix(R.from_euler('z',-90,degrees=True).as_matrix(),controls['hip']['view_translation'])
    else:
        rear=pose['WPN_RearSight'][:3,3];front=pose['WPN_FrontSight'][:3,3]
        q=frame(front-rear,pose['WPN_root'][:3,2]).T
        xf=matrix(q,np.array([controls['aim']['rear_sight_distance'],0,0])-q@rear)
    geo=np.load(P/('gun_'+kind+'.npz'))
    xyz=100*geo['X']*np.array([1,-1,1])
    np.savez_compressed(P/('gun_camera_'+kind+'.npz'),X=xyz@xf[:3,:3].T+xf[:3,3],T=geo['T'][:,::-1],UV=geo['UV'][:,::-1],slots=geo['slots'])
    return {n:xf@m for n,m in pose.items()}

def skin(snapshot,key,batch,pose,side,include_gun=False):
    payload=read(V9/f'Work/{batch}/{key}.json')
    x=np.array(payload['positions']);ids=payload['vertex_ids'];idmap={v:i for i,v in enumerate(ids)}
    weights=[payload['weights'].get(str(v),w) for v,w in zip(ids,snapshot['weights'])]
    shapes=dict(payload['morphs'])
    # The most recent published pose4 payload replaces earlier JC_Pose examples.
    extra=read(V9/f'Work/{batch}_pose4/{key}.json')
    shapes.update(extra['morphs'])
    driver=Driver(snapshot['bones'],shapes)
    signature={n:(m[:3,3],R.from_matrix(m[:3,:3]).as_quat()) for n,m in pose.items()}
    amounts=driver.weights(signature)
    original=x.copy()
    for name,amount in amounts.items():
        if amount<.001 or name not in shapes:continue
        for row in shapes[name]:
            i=idmap[row[0]];x[i]+=amount*(np.array(row[1:4])-original[i])
    rest=rest_of(snapshot);posed=np.zeros_like(x)
    for n in rest:
        ix=[];wt=[]
        for i,w in enumerate(weights):
            if n in w:ix.append(i);wt.append(w[n])
        if not ix:continue
        xf=pose[n]@np.linalg.inv(rest[n]);posed[ix]+=(x[ix]@xf[:3,:3].T+xf[:3,3])*np.array(wt)[:,None]
    tri=np.array(snapshot['triangles']);slot=np.array(snapshot['triangle_materials'])
    valid=np.array([sum(v for n,v in w.items() if n.endswith('_'+side))>.5 for w in weights])
    mask=np.all(valid[tri],axis=1)
    if include_gun:mask|=np.array([not snapshot['slots'][i]['skin'] for i in slot])
    return {'X':posed,'T':tri[mask],'UV':np.array(payload['uv0'])[mask],
            'slots':slot[mask], 'skin_slots':np.array(payload['skin_slots']),
            'active_correctives': {n:float(a) for n,a in amounts.items() if a>.001 and n in shapes}}

poses={};books={}
for label,kind in [('hip','idle'),('aim','aim')]:
    c=controls[label];gun=pistol_pose(kind)
    r=solve_arm(RR,gun,RP,'r',c['right_shoulder'],gun['hand_r'][:3,3],c['right_pole'],gun['hand_r'][:3,:3])
    wrist=np.array(c['left_wrist']) if label=='hip' else r['hand_r'][:3,3]+c['left_wrist_from_right']
    pole=np.array(c['left_pole']) if label=='hip' else wrist+c['left_pole_from_wrist']
    forward=LR['middle_01_l'][:3,3]-LR['hand_l'][:3,3]
    dorsal=-np.cross(LR['index_01_l'][:3,3]-LR['hand_l'][:3,3],LR['pinky_01_l'][:3,3]-LR['hand_l'][:3,3])
    hq=frame(c['left_finger_direction'],c['left_dorsal_direction'])@frame(forward,dorsal).T@LR['hand_l'][:3,:3]
    l=solve_arm(LR,carry,LP,'l',c['left_shoulder'],wrist,pole,hq,c.get('left_hand_roll_degrees',0.))
    books[label]=(l['hand_l']@mount).tolist()
    poses[label]={'left':{n:m.tolist() for n,m in l.items()},'right':{n:m.tolist() for n,m in r.items()}}
    for side,s,key,batch,p,inc in [('left',left,'01e184ddd1b7','batch1',l,False),('right',right,'8f309afe12dd','batch2',r,True)]:
        result=skin(s,key,batch,p,side[0],inc)
        corrective=result.pop('active_correctives')
        np.savez_compressed(P/f'{label}_{side}.npz',**result)
        poses[label][side+'_correctives']=corrective
    print(label, 'right wrist',r['hand_r'][:3,3].round(2),'right elbow',r['lowerarm_r'][:3,3].round(2),
          'left wrist',l['hand_l'][:3,3].round(2),'left elbow',l['lowerarm_l'][:3,3].round(2),flush=True)
(P/'candidate.json').write_text(json.dumps({'candidate_only':True,'runtime_integrated':False,'controls':controls,
    'poses':poses,'book_frames':books,'grasp':'saved M1911 contact and closed-book fingers retained',
    'surface':'native V9 production payloads with joint and pose4 corrective shapes'},indent=2),encoding='utf-8')
