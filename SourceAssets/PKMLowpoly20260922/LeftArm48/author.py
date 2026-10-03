"""Rebuild coherent upper/lower arm skin segments at the installed PKM key times.

The forearm frame uses its axis and the palm-width direction, excluding wrist
flexion. All three forearm bones carry the same skin rotation. The upper-arm
helpers transport that frame across the elbow bend, keeping their pivots on the
upper-arm axis. No independently accumulated bone roll, angle branch or gate.
"""
import hashlib,json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R
from skin_weights import FOREARM,binding_parameters,rebind

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[2]
OUT=HERE/'AuthoredTracks'; OUT.mkdir(exist_ok=True)
BEFORE=HERE/'Before'; BEFORE.mkdir(exist_ok=True)
d=json.loads((HERE/'current_mesh.json').read_text())
parameters=binding_parameters(d['bones'])
ref={n:np.array(b['axes'],dtype=float).T for n,b in d['bones'].items()}
refrot={n:R.from_matrix(m/np.linalg.norm(m,axis=0)).as_matrix() for n,m in ref.items()}
elbow=np.array(parameters[0]); f0=np.array(parameters[1]); f0/=np.linalg.norm(f0)
shoulder=np.array(d['bones']['upperarm_l']['position']);u0=elbow-shoulder
width=np.array(d['bones']['index_metacarpal_l']['position'])-np.array(d['bones']['pinky_metacarpal_l']['position'])
stations=dict(zip(FOREARM,parameters[3]))
upper_helpers=('upperarm_twist_01_l','upperarm_twist_02_l')
changed=FOREARM+upper_helpers
parents={'lowerarm_l':'upperarm_l','lowerarm_twist_02_l':'lowerarm_l','lowerarm_twist_01_l':'lowerarm_l','hand_l':'lowerarm_l'}
parents.update({n:'upperarm_l' for n in upper_helpers})

def matrix(t):
    m=np.eye(4);m[:3,:3]=R.from_quat(t['q']).as_matrix()*np.array(t['s']);m[:3,3]=t['p'];return m

def swing(a,b):
    a=a/np.linalg.norm(a);b=b/np.linalg.norm(b)
    v=np.cross(a,b);c=float(np.clip(a@b,-1,1))
    if c < -0.999999:
        seed=np.array([1.,0.,0.]) if abs(a[0])<.8 else np.array([0.,1.,0.])
        axis=np.cross(a,seed);axis/=np.linalg.norm(axis)
        return R.from_rotvec(axis*np.pi).as_matrix()
    q=np.r_[v,1+c]
    return R.from_quat(q/np.linalg.norm(q)).as_matrix()

def unpack(m,previous):
    scales=np.linalg.norm(m[:3,:3],axis=0)
    quat=R.from_matrix(m[:3,:3]/scales).as_quat()
    if previous is not None and quat@previous<0:quat=-quat
    return {'p':m[:3,3].tolist(),'q':quat.tolist(),'s':scales.tolist()},quat

def limb_frame(axis,transverse):
    axis=axis/np.linalg.norm(axis)
    side=transverse-axis*(transverse@axis)
    if np.linalg.norm(side)<1.e-6:
        raise RuntimeError('Palm-width direction parallel to forearm; author a wrist transition here')
    side/=np.linalg.norm(side)
    return np.column_stack((axis,side,np.cross(axis,side)))

bind_frame=limb_frame(f0,width)
indices={b['index']:n for n,b in d['bones'].items()}
def in_left_arm(n):
    while n:
        if n=='clavicle_l':return True
        n=indices.get(d['bones'][n]['parent'])
    return False

receipt=[]
for file in sorted((HERE/'InputTracks').glob('*.json')):
    resolved=HERE/'RestoredContacts'/file.name
    src=json.loads((resolved if resolved.exists() else file).read_text())
    frames=src['frames']
    tracks={n:[] for n in changed}; previous={n:None for n in changed}
    for i,frame in enumerate(frames):
        world={n:matrix(t) for n,t in frame.items()}
        s=np.array(frame['upperarm_l']['p']);e=np.array(frame['lowerarm_l']['p']);w=np.array(frame['hand_l']['p'])
        hand=R.from_quat(frame['hand_l']['q']).as_matrix()@refrot['hand_l'].T
        forearm_skin=limb_frame(w-e,hand@width)@bind_frame.T
        upper_skin=swing(forearm_skin@u0,e-s)@forearm_skin
        for n in upper_helpers:
            station=float((np.array(d['bones'][n]['position'])-shoulder)@u0/(u0@u0))
            offset=np.array(d['bones'][n]['position'])-shoulder-station*u0
            m=np.eye(4)
            m[:3,:3]=(upper_skin@refrot[n])*np.array(frame['upperarm_twist_02_l']['s'])
            m[:3,3]=s+station*(e-s)+upper_skin@offset
            world[n]=m
        for n in FOREARM[:-1]:
            station=stations[n]
            # Bind-point offsets perpendicular to the axis are retained as well.
            offset=np.array(d['bones'][n]['position'])-elbow-station*np.array(parameters[1])
            world[n][:3,:3]=(forearm_skin@refrot[n])*np.array(frame[n]['s'])
            world[n][:3,3]=e+station*(w-e)+forearm_skin@offset
        for n in changed:
            local=np.linalg.inv(world[parents[n]])@world[n]
            key,previous[n]=unpack(local,previous[n]);tracks[n].append(key)
    restored={n:keys for n,keys in src.get('restored_contact_tracks',{}).items() if in_left_arm(n)}
    restored.update(tracks)
    payload={k:v for k,v in src.items() if k not in ('frames','restored_contact_tracks')}
    payload.update(version='PKM.LeftArm48',tracks=restored,stations=stations,
                   method='Coherent arm segments; palm-width roll; upper-arm elbow transport')
    (OUT/file.name).write_text(json.dumps(payload,separators=(',',':')),encoding='utf-8')
    receipt.append({'asset':src['asset'],'keys':src['keys'],'tracks':len(restored),
                    'contact_restored':bool(src.get('contact_source'))})
    print('AUTHORED',file.stem,src['keys'],len(restored),'tracks',flush=True)

source=PROJECT/'SourceAssets/ModularOutfit20260925/BarePalmV7/Authored/PKM.json'
raw=source.read_bytes(); before=BEFORE/'PKM_authored.json'
if not before.exists(): before.write_bytes(raw)
skin=json.loads(raw); count=0
for i,original in enumerate(skin['weights']):
    rebuilt=rebind(skin['positions'][i],original,parameters)
    if sum(abs(rebuilt.get(n,0)-original.get(n,0)) for n in set(rebuilt)|set(original))>1.e-8:count+=1
    skin['weights'][i]=rebuilt
skin['contract']+='; LeftArm48: continuous PKM left forearm weights at reference bone stations; right arm and finger influences preserved'
(HERE/'PKM_authored.json').write_text(json.dumps(skin,separators=(',',':')),encoding='utf-8')
(HERE/'authoring.json').write_text(json.dumps({'version':'PKM.LeftArm48','source_authored_sha256':hashlib.sha256(raw).hexdigest(),
    'vertices_changed':count,'stations':stations,'clips':receipt,'runtime_tested':False},indent=2),encoding='utf-8')
print('PKM_LEFT_ARM_AUTHORED',len(receipt),'clips;',count,'left arm vertices')
