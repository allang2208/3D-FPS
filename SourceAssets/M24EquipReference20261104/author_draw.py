"""Bake the short optical rise onto VM_Root, below the real 100x FBX armature."""
from pathlib import Path
import json,numpy as np
from scipy.spatial.transform import Rotation as R
from scipy.interpolate import PchipInterpolator
P=Path(__file__).resolve().parent
d=json.loads((P/'live_source.json').read_text());rig=json.loads((P/'armature_parent.json').read_text())
def mat(v):
    m=np.eye(4);m[:3,:3]=R.from_quat(v[3:7]).as_matrix()@np.diag(v[7:]);m[:3,3]=v[:3];return m
def dec(m):
    sc=np.linalg.norm(m[:3,:3],axis=0)
    return [*m[:3,3],*R.from_matrix(m[:3,:3]/sc).as_quat(),*sc]
def pose(data,layer,prefix):
    row={}
    for n,par in data['parent'].items():
        v=np.array(data['raw'][n]);delta=layer.get(n)
        if delta:
            a=np.array(delta);v[:3]+=a[:3];v[3:7]=(R.from_quat(a[3:7])*R.from_quat(v[3:7])).as_quat();v[7:]+=a[7:]
        row[n]=(row[par] if par is not None else prefix)@mat(v)
    return row
def basis(row,up):
    g=row['WPN_root'][:3,:3];g=g/np.linalg.norm(g,axis=0)
    x=row['WPN_FrontSight'][:3,3]-row['WPN_RearSight'][:3,3];x/=np.linalg.norm(x)
    z=g@up;z-=x*(z@x);z/=np.linalg.norm(z);return np.column_stack((x,np.cross(z,x),z))
ref=pose(d['reference'],{},np.eye(4))
idle=pose(d['idle'],d['profiles']['base'],mat(rig['idle']))
rz=R.from_euler('z',90,degrees=True).as_matrix()
hip=rz@basis(ref,[0.,0.,1.])@basis(idle,[0.,-1.,0.]).T
pivot=idle['WPN_root'][:3,3]
# Camera cm and angles: forward, right, up, nose-down, yaw-right, roll.
# The front appears before the eyepiece. Depth closes later than the lift.
controls=[
 (0,8.0,4.8,-54.,28.,4.5,7.0),
 (1,8.4,4.4,-37.,22.,4.1,6.3),
 (2,8.7,3.9,-25.,17.,3.5,5.7),
 (3,8.8,3.25,-17.,12.5,2.9,4.7),
 (4,8.7,2.7,-11.5,9.0,2.25,3.8),
 (6,8.0,1.75,-5.0,4.0,1.35,2.5),
 (8,6.6,.9,-1.10,1.1,.65,1.40),
 (10,4.6,.40,.36,-.40,.26,.68),
 (12,2.6,.16,.67,-.65,.09,.24),
 (14,1.05,.05,.28,-.24,.035,.06),
 (16,.17,.012,.045,-.034,.005,.009),
 (18,0.,0.,0.,0.,0.,0.)]
controls=np.array(controls);sample=PchipInterpolator(controls[:,0],controls[:,1:],axis=0)
output=[]
for k,raw in enumerate(d['root']):
    if k>=18:output.append(raw);continue
    forward,right,up,pitch,yaw,roll=sample(k);cam_rot=R.from_euler('ZYX',[yaw,pitch,roll],degrees=True).as_matrix()
    turn=hip.T@cam_rot@hip;delta=np.eye(4);delta[:3,:3]=turn
    delta[:3,3]=hip.T@[forward,right,up]+pivot-turn@pivot
    father=mat(rig['equip'][k]);m=np.linalg.inv(father)@delta@father@mat(raw)
    out=dec(m);out[7:]=raw[7:]
    if np.dot(out[3:7],raw[3:7])<0:out[3:7]=[-v for v in out[3:7]]
    output.append(out)
(P/'draw_keys.json').write_text(json.dumps({'asset':d['equip'],'bone':'VM_Root','source_sha256':d['sha256'],'frame_rate':d['fps'],
    'source_frames':len(output),'camera_controls':controls.tolist(),'armature_parent':rig['name'],'keys':output},indent=2))
print('M24_DRAW_KEYS',len(output), 'parent scale',rig['equip'][0][7:], 'camera basis',hip.tolist(),flush=True)
