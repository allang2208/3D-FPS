"""Bake contact correction only; the runtime node owns support in every state."""
import copy,json
import numpy as np
from scipy.spatial.transform import Rotation as R
from repair_core import O,S,rest,parents,names,rows,correct,packed,I,digits
native=json.loads((S/'Super90Foregrips20261007/native.json').read_text())
C=np.diag([100.,-100.,100.,1.]);Ci=np.linalg.inv(C)
def mat(v):
    out=I.copy();out[:3,:3]=R.from_quat(v[3:7]).as_matrix()@np.diag(v[7:10]);out[:3,3]=v[:3];return out
K={n:np.linalg.inv(C@rest[n])@mat(native['rest'][n]) for n in names};Ki={n:np.linalg.inv(m) for n,m in K.items()}
def adapted(p,clip,f):
    delta={t['bone']:t['values'][f*10:(f+1)*10] for t in clip['tracks']};ue={n:C@p[n]@K[n] for n in names};out={}
    for n in names:
        par=parents[n];local=np.linalg.inv(ue.get(par,I))@ue[n]
        if n in delta:
            v=delta[n];scale=np.linalg.norm(local[:3,:3],axis=0);rot=local[:3,:3]/scale
            local[:3,3]+=v[:3];local[:3,:3]=R.from_quat(v[3:7]).as_matrix()@rot@np.diag(scale+np.array(v[7:10]))
        out[n]=out.get(par,I)@local
    return {n:Ci@out[n]@Ki[n] for n in names}
def local_ue(p,n):
    par=parents[n];return Ki[par]@np.linalg.inv(p[par])@p[n]@K[n] if par else C@p[n]@K[n]
changed=['hand_l',*digits];families=('vertical','canted','prism','angled')
inputs={f:json.loads((S/'Super90LoaderR21_20261010'/(f+'_profiles.json')).read_text()) for f in families}
profiles={f:dict(family=f,clips=[]) for f in families};authored={};rendered={};diagnostic={}
for branch in ('normal','empty','cycle'):
    authored[branch]=[correct(p,branch,f,support=False) for f,p in enumerate(rows[branch])]
    rendered[branch]=[correct(p,branch,f) for f,p in enumerate(rows[branch])]
for fam in families:
    diagnostic[fam]={}
    for branch in ('normal','empty','cycle'):
        name='A_Super90_loader_'+(branch if branch=='cycle' else branch+'_7')
        clip=next(c for c in inputs[fam]['clips'] if c['base'].endswith(name))
        adapted_rows=[adapted(p,clip,f) for f,p in enumerate(rows[branch])]
        targets=[correct(p,branch,f,support=False) for f,p in enumerate(adapted_rows)]
        diagnostic[fam][branch]=[packed(correct(p,branch,f)) for f,p in enumerate(adapted_rows)]
        if branch=='normal':continue
        for count in ([0] if branch=='cycle' else range(1,8)):
            target_name='A_Super90_loader_'+(branch if count==0 else branch+'_'+str(count))
            out=copy.deepcopy(next(c for c in inputs[fam]['clips'] if c['base'].endswith(target_name)));tracks={t['bone']:t for t in out['tracks']}
            for n in changed:
                values=[];last=None
                for base,target_pose in zip(authored[branch],targets):
                    a=local_ue(base,n);b=local_ue(target_pose,n);sa=np.linalg.norm(a[:3,:3],axis=0);sb=np.linalg.norm(b[:3,:3],axis=0)
                    q=R.from_matrix((b[:3,:3]/sb)@(a[:3,:3]/sa).T).as_quat()
                    if (last is not None and q@last<0) or (last is None and q[3]<0):q=-q
                    last=q;values.extend([*(b[:3,3]-a[:3,3]),*q,*(sb-sa)])
                track=dict(bone=n,times=[f/60 for f in range(len(targets))],values=values)
                if n in tracks:tracks[n].update(track)
                else:out['tracks'].append(track)
            profiles[fam]['clips'].append(out)
for f,data in profiles.items():(O/(f+'_profiles.json')).write_text(json.dumps(data,separators=(',',':')))
(O/'contact_poses.json').write_text(json.dumps({b:[packed(p) for p in ps] for b,ps in authored.items()},separators=(',',':')))
(O/'repaired_poses.json').write_text(json.dumps({b:[packed(p) for p in ps] for b,ps in rendered.items()},separators=(',',':')))
(O/'family_repaired_poses.json').write_text(json.dumps(diagnostic,separators=(',',':')))
print('R23_CONTACT_AND_FAMILY_POSES_READY',flush=True)
