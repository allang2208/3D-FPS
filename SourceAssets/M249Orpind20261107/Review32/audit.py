"""Read-only review of the installed Feedback31 animation graph output."""
from pathlib import Path
import json, hashlib, numpy as np
from scipy.spatial.transform import Rotation as R

r=Path(__file__).resolve().parent
prev=r.parent/'Feedback31'
meta=json.loads((prev/'saved/30_empty_base/geometry.json').read_text())
ix={name:i for i,name in enumerate(meta['bones'])}; n=len(ix)
report={}

def pose(folder):
    a=np.fromfile(folder/'poses.f32',np.float32).reshape(-1,4+n*7)
    return a,a[:,4:].reshape(-1,n,7)

def relative(p,bone):
    gun=p[:,ix['WPN_root']]; child=p[:,ix[bone]]; q=R.from_quat(gun[:,3:])
    return q.inv().apply(child[:,:3]-gun[:,:3]),q.inv()*R.from_quat(child[:,3:])

def matrix(v):
    m=np.eye(4);m[:3,:3]=R.from_quat(v[3:7]).as_matrix()*np.array(v[7:10]);m[:3,3]=v[:3];return m

for folder in sorted((r/'full').iterdir()):
    if not(folder/'review.json').exists():continue
    j=json.loads((folder/'review.json').read_text());a,p=pose(folder)
    assert j['complete'] and np.isfinite(a).all()
    active=a[:,0]<j['duration'];handoff=np.flatnonzero(np.diff(active.astype(int))==-1)[0]
    gun=p[:,ix['WPN_root']];g=R.from_quat(gun[:,3:]);step=np.linalg.norm(np.diff(gun[:,:3],axis=0),axis=1)
    rotation=np.degrees((g[:-1].inv()*g[1:]).magnitude())
    result=dict(frames=len(a),images=len(j['frames']),duration=j['duration'],finite=True,
        max_receiver_frame_cm=float(step.max()),max_receiver_frame_deg=float(rotation.max()),
        idle_handoff_cm=float(step[handoff]),idle_handoff_deg=float(rotation[handoff]))
    assert result['idle_handoff_cm']<.01 and result['idle_handoff_deg']<.01
    assert step.max()<.5 and rotation.max()<.7
    old=prev.parent/'Insert30/saved'/folder.name
    if (old/'poses.f32').exists():
        b,q=pose(old);assert np.array_equal(a[:,:4],b[:,:4])
        result['previous_clock_identical']=True;contacts={}
        for bone in ['hand_l','hand_r','lowerarm_l','lowerarm_r','PKM_Charge','WPN_SOCKET_Magazine']:
            u,uq=relative(p,bone);v,vq=relative(q,bone)
            contacts[bone]=dict(cm=float(np.linalg.norm(u-v,axis=1).max()),degrees=float(np.degrees((uq.inv()*vq).magnitude()).max()))
        assert all(x['cm']<.015 and x['degrees']<.015 for x in contacts.values())
        result['relative_contacts']=contacts
    if (folder/'dominant.bin').exists():
        dominant=np.fromfile(folder/'dominant.bin',np.uint32)
        arm=np.array([name.endswith(('_l','_r')) and name.startswith(('upperarm','lowerarm')) for name in meta['bones']])[dominant]
        surfaces=[]
        for frame in j['frames']:
            v=np.fromfile(folder/Path(frame['file']).with_suffix('.vertices'),np.float32).reshape(-1,3)
            xf=np.linalg.inv(matrix(frame['camera']))@matrix(frame['component']);v=v[arm]@xf[:3,:3].T+xf[:3,3]
            depth=v[:,0];half=np.tan(np.radians(107.5/2));inside=(depth>1)&(abs(v[:,1])<=depth*half)&(abs(v[:,2])<=depth*half*540/960)
            surfaces.append(dict(source=frame['source'],near_arm_vertices=int((inside&(depth<10)).sum()),min_visible_depth_cm=float(depth[inside].min()) if inside.any() else None))
        result['surface_samples']=surfaces
    report[folder.name]=result

assert len(report)==20
hashes=json.loads((r/'input_hashes.json').read_text())
for asset,item in hashes.items():
    disk=r.parents[2]/'Content'/(asset.removeprefix('/Game/')+'.uasset')
    assert hashlib.sha256(disk.read_bytes()).hexdigest()==item['actual'],asset
result=dict(complete=True,asset_writes=False,gameplay_test=False,cases=report)
(r/'audit.json').write_text(json.dumps(result,indent=2))
print('REVIEW32_PASS',len(report),'cases;',sum(v['frames'] for v in report.values()),'pose frames;',sum(v['images'] for v in report.values()),'images')
for name,v in report.items():
    if 'surface_samples' in v:print(name,'near-camera arm vertices',max(s['near_arm_vertices'] for s in v['surface_samples']))
