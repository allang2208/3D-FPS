"""Layer only arm/contact tracks on the saved five-round-loader profile."""
import sys,json,copy
from pathlib import Path
O=Path(__file__).parent;sys.path.insert(0,str(O))
from grip_scene import *
from held_grip import HeldGrip
rig,D,profile,meta=load();solver=HeldGrip(rig,D,profile,meta)
S=Matrix.Diagonal((1,-1,1,1));to_native=rig.matrix_world.inverted()@S@Matrix.Diagonal((.01,.01,.01,1));to_ue=to_native.inverted()
result=copy.deepcopy(profile);summary={}
for entry in result['clips']:
    kind=entry['kind'];values={};times=[]
    for sample in D['clips'][kind]['samples']:
        t=sample['time'];times.append(t);p=pose(rig,D,profile,kind,sample);changed=solver.authored(p,kind)
        # Keep every existing mechanical and reload-support key; only update changed arm locals.
        world={n:to_ue@m@S for n,m in p.items()}
        original=applied({n:matrix(v) for n,v in sample['local'].items()},entry,t)
        frame={}
        for n in changed:
            parent=D['parents'][n];lp=world[parent].inverted()@world[n]
            # Rotations carry the hand. Local translations/scales remain exactly the native lengths.
            nt,nq,ns=lp.decompose();bt,bq,bs=matrix(sample['local'][n]).decompose()
            if not n.startswith('clavicle_'):nt=original[n].translation
            ns=original[n].to_scale()
            q=nq@bq.inverted()
            if q.w<0:q.negate()
            frame[n]=[*(nt-bt),q.x,q.y,q.z,q.w,*(ns-bs)]
            if n not in values:values[n]=[None]*(len(times)-1)
        for n in values:values[n].append(frame.get(n))
    existing={tr['bone']:tr for tr in entry['tracks']}
    for n,vv in values.items():
        for i,v in enumerate(vv):
            if v is None:vv[i]=track_at(existing[n],times[i]) if n in existing else [0,0,0,0,0,0,1,0,0,0]
        constant=all(max(abs(a-b) for a,b in zip(vv[0],v))<.00001 for v in vv[1:])
        existing[n]=dict(bone=n,times=[0.] if constant else times,values=vv[0] if constant else [x for v in vv for x in v])
    entry['tracks']=list(existing.values());summary[kind]=len(values)
    print('RSH_GRIP_PROFILE_AUTHORED',kind,len(values),flush=True)
out=O/'Single';out.mkdir(exist_ok=True)
(out/'profile.json').write_text(json.dumps(result,separators=(',',':')),encoding='utf8')
(O/'authoring_receipt.json').write_text(json.dumps(dict(source='RSH12Speedloader20261003',profile='/Game/Weapons/RSH12/Native71520261003/Profiles/DA_RSH12_base',changed_arm_tracks=summary,mesh_unchanged=True,source_animation_sequences_unchanged=True,runtime_tested=False),indent=2))
