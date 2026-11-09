"""Scoped anatomical axes, continuity and mechanical contact readback."""
from pathlib import Path
import sys,pickle,json,numpy as np
from scipy.spatial.transform import Rotation as R
r=Path(__file__).resolve().parent
exec(compile((r/'author.py').read_text().split("outdir=r/'Motion'")[0],str(r/'author.py'),'exec'))
label=sys.argv[1] if len(sys.argv)>1 else 'candidate'
original=d
if label=='saved':d=pickle.load(open(r/'saved_compressed.pkl','rb'))
cache=pickle.load(open(r/'candidate_world.pkl','rb')) if label=='candidate' else {}
report={}
for path,c in d['clips'].items():
    if path.split('.')[0].endswith('_idle'):continue
    key=('side_' if '/SideMagazine' in path else 'box_')+('reload_empty' if path.split('.')[0].endswith('_reload_empty') else 'reload')
    t=np.arange(len(c['frames']))/120;active=(t>=.25)&(t<=c['duration']-.35)
    for family in d['profiles']:
        k=key+'_'+family
        if label=='saved':cache[k]=dict(times=t,world=world(layer(np.array(c['frames']),path,family,t)))
        w=cache[k]['world'];row={}
        for side in ('l','r'):
            b,bn=binding(side);a,e,h=[w[:,ix[n],:3,3] for n in [bn[1],bn[4],bn[7]]];up=e-a;fore=h-e;axis=np.cross(up,fore);axis/=np.linalg.norm(axis,axis=1)[:,None]
            m=w[:,ix[bn[3]],:3,:3];m=m/np.linalg.norm(m,axis=1)[:,None,:];anatomy=m@b.R[3].T@b.H0;angle=np.degrees(np.arccos(np.clip((anatomy*axis).sum(1),-1,1)))
            hand=w[:,ix[bn[7]],:3,:3];hand=hand/np.linalg.norm(hand,axis=1)[:,None,:];wristaxis=hand@b.R[7].T@unit(b.F0);wrist=np.degrees(np.arccos(np.clip((wristaxis*fore).sum(1)/np.linalg.norm(fore,axis=1),-1,1)))
            steps={}
            for n in bn[1:]:
                pose=w[:,ix[n]];q=pose[:,:3,:3]/np.linalg.norm(pose[:,:3,:3],axis=1)[:,None,:];spin=np.degrees((R.from_matrix(q[:-1]).inv()*R.from_matrix(q[1:])).magnitude());dist=np.linalg.norm(np.diff(pose[:,:3,3],axis=0),axis=1);steps[n]=dict(degrees=float(spin.max()),at=float(t[spin.argmax()]),cm=float(dist.max()))
            row[side]=dict(hinge_active_max_degrees=float(angle[active].max()),wrist_max_degrees=float(wrist.max()),steps=steps)
        if key.startswith('side'):
            rel=np.linalg.inv(w[:,ix['WPN_SOCKET_Magazine']])@w[:,ix['hand_l']];lock=(t>=.70)&(t<=2.78);ref=rel[np.argmin(abs(t-.72))];dis=np.linalg.norm((rel[lock,:3,3]-ref[:3,3])*100,axis=1);rr=rel[lock,:3,:3]/np.linalg.norm(rel[lock,:3,:3],axis=1)[:,None,:];q=rot(ref);angle=np.degrees(R.from_matrix(rr@q.T).magnitude());row['magazine_contact']=dict(cm=float(dis.max()),degrees=float(angle.max()))
        report[k]=row
(r/(label+'_inspection.json')).write_text(json.dumps(report,indent=2))
if label=='saved':
    with (r/'saved_world.pkl').open('wb') as f:pickle.dump(cache,f)
print('M249_SCOPED_INSPECTION',label,'clips_and_grips',len(report),'max step',max((a['degrees'],k,n,a['at']) for k,v in report.items() for side in ['l','r'] for n,a in v[side]['steps'].items()),flush=True)
