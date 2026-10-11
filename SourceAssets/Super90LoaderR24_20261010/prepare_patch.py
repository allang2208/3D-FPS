"""Shorten only the extra bolt pull and carry the existing grasp with it."""
import json,sys
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R
O=Path(__file__).parent;S=O.parent;OLD=S/'Super90LoaderR23_20261010'
sys.path.insert(0,str(OLD))
from repair_core import rest,ri,parents,names,I,rack_time,phase,digits
fit=json.loads((O/'bolt_fit.json').read_text())
raw=json.loads((OLD/'contact_poses.json').read_text())
rows={b:[{n:np.array(m) for n,m in p.items()} for p in raw[b]] for b in ('empty','cycle')}
native=json.loads((S/'Super90Foregrips20261007/native.json').read_text())
C=np.diag([100.,-100.,100.,1.]);Ci=np.linalg.inv(C)
def mat(v):
    out=I.copy();out[:3,:3]=R.from_quat(v[3:7]).as_matrix()@np.diag(v[7:10]);out[:3,3]=v[:3];return out
K={n:np.linalg.inv(C@rest[n])@mat(native['rest'][n]) for n in names};Ki={n:np.linalg.inv(m) for n,m in K.items()}
WRITE=('WPN_bolt','hand_l')
ratio=fit['new_extra_travel_m']/fit['old_extra_travel_m']
max_offset=fit['old_extra_travel_m']-fit['new_extra_travel_m']

def adapt(p,clip,f):
    delta={t['bone']:t['values'][f*10:(f+1)*10] for t in clip['tracks']}
    ue={n:C@p[n]@K[n] for n in names};out={}
    for n in names:
        par=parents[n];local=np.linalg.inv(ue.get(par,I))@ue[n]
        if n in delta:
            v=delta[n];scale=np.linalg.norm(local[:3,:3],axis=0);rot=local[:3,:3]/scale
            local[:3,3]+=v[:3];local[:3,:3]=R.from_quat(v[3:7]).as_matrix()@rot@np.diag(scale+np.array(v[7:10]))
        out[n]=out.get(par,I)@local
    return {n:Ci@out[n]@Ki[n] for n in names}

def corrected(p,branch,f):
    out={n:m.copy() for n,m in p.items()};gun=p['WPN_root']@ri['WPN_root']
    mechanism=np.linalg.inv(gun)@p['WPN_bolt']@ri['WPN_bolt']
    travel=-mechanism[1,3]
    offset=max(0.,travel-fit['open_travel_m'])*(1-ratio)
    # Source opened position and closure stay exactly where they were. Only the
    # added overpull is shortened; the true handle is never hidden or scaled.
    out['WPN_bolt'][:3,3]+=gun[:3,:3]@np.array([0.,offset,0.])
    t=rack_time(branch,f)
    # Keep the hand at the shortened rear stop while it releases. Do not snap
    # the hand forward with the returning bolt; fade on the existing return arc.
    hand_offset=offset if t<44 else max_offset*(1-phase(t,48,63))
    step=gun[:3,:3]@np.array([0.,hand_offset,0.])
    for n in ('hand_l',*digits):out[n][:3,3]+=step
    return out

def local(p,n):
    par=parents[n];return Ki[par]@np.linalg.inv(p[par])@p[n]@K[n] if par else C@p[n]@K[n]
def offsets(old,new):
    return {n:[(local(b,n)[:3,3]-local(a,n)[:3,3]).tolist() for a,b in zip(old,new)] for n in WRITE}

new={b:[corrected(p,b,f) for f,p in enumerate(ps)] for b,ps in rows.items()}
base_offsets={b:offsets(rows[b],new[b]) for b in rows}
families={}
for fam in ('vertical','canted','prism','angled'):
    data=json.loads((OLD/(fam+'_profiles.json')).read_text());families[fam]={}
    for b in rows:
        name='A_Super90_loader_'+('cycle' if b=='cycle' else 'empty_7')
        clip=next(c for c in data['clips'] if c['base'].endswith(name))
        ps=[adapt(p,clip,f) for f,p in enumerate(rows[b])]
        target=[corrected(p,b,f) for f,p in enumerate(ps)]
        delta=offsets(ps,target)
        families[fam][b]={n:(np.array(delta[n])-np.array(base_offsets[b][n])).tolist() for n in WRITE}
manifest=json.loads((OLD/'authoring.json').read_text())
patch={'revision':'LoaderR24-BoltRearStop-20261010','write_bones':list(WRITE),
       'fit':fit,'base_offsets':base_offsets,'profile_offsets':families,
       'clips':[{'name':c['name'],'branch':'cycle' if c['name'].endswith('cycle') else 'empty',
                 'duration':c['duration']} for c in manifest['clips']],
       'runtime_tested':False}
(O/'translation_patch.json').write_text(json.dumps(patch,separators=(',',':')))
# Blender location keys use bind-relative parent space, unlike native UE keys.
blender={}
for b in rows:
    blender[b]={}
    for n in WRITE:
        par=parents[n];lr=np.linalg.inv(rest[par])@rest[n];values=[]
        for p in new[b]:values.append((np.linalg.inv(lr)@np.linalg.inv(p[par])@p[n])[:3,3].tolist())
        blender[b][n]=values
(O/'blender_locations.json').write_text(json.dumps(blender,separators=(',',':')))
print('SUPER90_R24_PATCH_READY',len(patch['clips']),'clips; extra pull 24 ->',fit['new_extra_travel_m']*1000,'mm',flush=True)
