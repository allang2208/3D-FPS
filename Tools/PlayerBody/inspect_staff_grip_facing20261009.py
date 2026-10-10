"""Requested grip check: actual production skin, face samples and action wrists."""
import json,sys,importlib.util
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'SourceAssets/ThirdPersonStaffGripFacing20261009'
scope={'__file__':str(ROOT/'Tools/PlayerBody/author_staff_grip_facing20261009.py')}
exec((ROOT/'Tools/PlayerBody/author_staff_grip_facing20261009.py').read_text().split('result=dict')[0],scope)
names,children,local,native=[scope[n] for n in ('names','children','local','native')]
parents,rest,dist,surface=[scope[n] for n in ('parents','rest','distance','surface')]
current=json.loads((OUT/'authored-grip.json').read_text())
old=json.loads((ROOT/'SourceAssets/ThirdPersonStaffGripVRE20261009/authored-grip.json').read_text())
geo=json.loads((OUT/'production-steel.json').read_text())
points=np.array(geo['positions']);tri=np.array(geo['triangles'],int)
mask=np.array([sum(v for b,v in ws if names[b] in native)>.95 for ws in geo['weights']])
tri=tri[np.all(mask[tri],axis=1)]
influences={}
for i,ws in enumerate(geo['weights']):
    for b,weight in ws:
        n=names[b]
        if n in native:influences.setdefault(n,[]).append((i,weight))
def fk(g):
    w={'hand_r':np.array(g['hand_in_grip'])}
    for n in children:
        q=R.from_quat(g['rotations'][n]).as_matrix() if n in g['rotations'] else local[n][:3,:3]
        if '_half_' in n and parents[n] in g['rotations']:
            delta=local[parents[n]][:3,:3].T@R.from_quat(g['rotations'][parents[n]]).as_matrix()
            q=R.from_rotvec(-R.from_matrix(delta).as_rotvec()*.5).as_matrix()@local[n][:3,:3]
        w[n]=w[parents[n]]@scope['matrix'](q,local[n][:3,3])
    return w
def skin(w):
    missing=np.array([1-sum(v for b,v in ws if names[b] in native) for ws in geo['weights']])
    base=w['hand_r']@np.linalg.inv(rest['hand_r'])
    p=(points@base[:3,:3].T+base[:3,3])*missing[:,None]
    for n,rows in influences.items():
        rows=np.array(rows);ids=rows[:,0].astype(int);weight=rows[:,1,None]
        m=w[n]@np.linalg.inv(rest[n]);p[ids]+=(points[ids]@m[:3,:3].T+m[:3,3])*weight
    return p
report={'production_asset':geo['source'],'variants':{},'rejected':{},'clips':{}}
for label,grips in [('rejected',old),('variants',current)]:
    for key,g in grips['variants'].items():
        w=fk(g);p=skin(w)
        v=p[tri];samples=np.concatenate((p[mask],v.mean(1),(v[:,0]+v[:,1])*.5,(v[:,1]+v[:,2])*.5,(v[:,2]+v[:,0])*.5))
        sd=dist(samples,np.array(surface['variants'][key]['radii']))
        hand=np.array(g['hand_in_grip']);hi=np.linalg.inv(hand)
        normal=scope['palm'](native)[:,2]
        curls={d:float(np.dot((hi@w[d+'_03_r'])[:3,3]-native[d+'_01_r'][:3,3],normal)) for d in ['index','middle','ring','pinky']}
        report[label][key]=dict(sample_count=len(samples),minimum_clearance_cm=float(sd.min()),penetrating_samples=int((sd<0).sum()),volar_curl_cm=curls)
        print(label,key,report[label][key],flush=True)
        if label=='variants':
            assert min(curls.values())>0,'Finger curled dorsally'
            assert sd.min()>0,'Surface sample penetrates shaft'
spec=importlib.util.spec_from_file_location('body_math',ROOT/'SourceAssets/ThirdPersonSwordDonorRepair20261006/adapt_donor.py')
rig=importlib.util.module_from_spec(spec);spec.loader.exec_module(rig)
donor=json.loads((ROOT/'SourceAssets/ThirdPersonStaffCast20261009/donors.json').read_text())
rig.names=donor['names'];rig.ix={n:i for i,n in enumerate(rig.names)};rig.parents=donor['parents'];rig.ref=np.array(donor['reference'])
poses={}
for folder in ['ThirdPersonStaffCast20261009','ThirdPersonStaffCombat20261009']:
    data=json.loads((ROOT/'SourceAssets'/folder/'authored.json').read_text())
    for key,c in data['clips'].items():
        if not key.startswith('Staff.'):continue
        f=np.array(c['frames']);i=rig.ix['hand_r'];restq=R.from_quat(rig.ref[i,3:7])
        angles=np.degrees((restq.inv()*R.from_quat(f[:,i,3:7])).magnitude())
        report['clips'][key]={'frames':len(f),'maximum_wrist_angle_degrees':float(angles.max())}
        assert angles.max()<25.001,key+' wrist folded'
        for name,frame in [('start',f[0]),('contact',f[round(c['contact']*(len(f)-1))])]:
            # These are the same local rotations installed by the live finger layer.
            g=current['variants']['false']
            frame=frame.copy()
            for n in children:
                j=rig.ix[n]
                frame[j]=rig.ref[j]
                if n in g['rotations']:frame[j,3:7]=g['rotations'][n]
                elif '_half_' in n and parents[n] in g['rotations']:
                    delta=local[parents[n]][:3,:3].T@R.from_quat(g['rotations'][parents[n]]).as_matrix()
                    frame[j,3:7]=R.from_matrix(R.from_rotvec(-R.from_matrix(delta).as_rotvec()*.5).as_matrix()@local[n][:3,:3]).as_quat()
            poses[key+'.'+name]={'bones':{n:t.tolist() for n,t in zip(rig.names,rig.fk(frame))},'hand_in_grip':g['hand_in_grip']}
(OUT/'inspection.json').write_text(json.dumps(report,indent=2))
(OUT/'inspection-poses.json').write_text(json.dumps(poses,separators=(',',':')))
print(json.dumps(report,indent=2))
