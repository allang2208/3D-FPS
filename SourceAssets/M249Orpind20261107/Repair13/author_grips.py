"""Author sparse M249 grip differences over current motions and bipod contacts."""
import json,pickle,gzip,sys
from pathlib import Path
import numpy as np
r=Path(__file__).resolve().parent;sys.path.insert(0,str(r.parent/'Repair10'))
from motion import *
d=pickle.load(open(r/'native.pkl','rb'));donor=pickle.load(open(r/'donor.pkl','rb'));recipe=json.loads((r/'parts_recipe.json').read_text())
names=d['names'];parents={n:(names[i] if i>=0 else None) for n,i in zip(names,d['parents'])};B={n:matrix(v) for n,v in zip(names,d['bind'])}
dn=donor['names'];dp={n:(dn[i] if i>=0 else None) for n,i in zip(dn,donor['parents'])};DB={n:matrix(v) for n,v in zip(dn,donor['bind'])}
selected=[n for n in names if n.endswith('_l') and n.startswith(('upperarm','lowerarm','hand','thumb','index','middle','ring','pinky','ik_hand'))]
digits=[n for n in selected if n.startswith(('thumb','index','middle','ring','pinky'))]
def apply_tracks(local,tracks,t):
    out={n:m.copy() for n,m in local.items()}
    for track in tracks:
        n=track['bone'];v=sample(np.asarray(track['values']).reshape(-1,10),track['times'],t)
        scale=np.linalg.norm(out[n][:3,:3],axis=0)+v[7:];out[n][:3,3]+=v[:3];out[n][:3,:3]=R.from_quat(v[3:7]).as_matrix()@rot(out[n])*scale
    return out
def effective(path,rows,t):
    local={n:matrix(v) for n,v in zip(names,rows)}
    source=d['bipod'] if '/Bipod/' in path else d['support']
    c=next((c for c in source if c['base']==path),None)
    return apply_tracks(local,c['tracks'],t) if c else local
idle_path=next(k for k in d['clips'] if k.split('.')[0].endswith('_idle'))
idle=compose(names,parents,effective(idle_path,d['clips'][idle_path]['frames'][0],0.))
reference=np.linalg.inv(idle['WPN_root'])@idle['hand_l'];reference[:3,3]*=100;reference[:3,:3]=rot(reference)
def solve(world,local,pos,rotation,amount,donor_local):
    out={n:m.copy() for n,m in world.items()};a,e,h=[world[n][:3,3] for n in ('upperarm_l','lowerarm_l','hand_l')]
    axis=unit(pos-a);dist=np.linalg.norm(pos-a);la=np.linalg.norm(e-a);lb=np.linalg.norm(h-e)
    if dist>la+lb-.01:raise RuntimeError('Grip seat exceeds native arm reach; adjust the authored seat')
    along=(la*la-lb*lb+dist*dist)/(2*dist);pole=unit(e-a-axis*((e-a)@axis));radius=np.sqrt(max(0,la*la-along*along));elbow=a+axis*along+pole*radius
    du=swing(e-a,elbow-a);dl=swing(h-e,pos-elbow)
    for prefix,origin,neworigin,delta in (('upperarm',a,a,du),('lowerarm',e,elbow,dl)):
        for suffix in ('','_twist_01','_twist_02'):
            n=prefix+suffix+'_l'
            if n not in out:continue
            out[n][:3,:3]=delta@world[n][:3,:3];out[n][:3,3]=neworigin+delta@(world[n][:3,3]-origin)
    # Roll is carried by the V9 forearm's full/half twist stations. The palm
    # keeps the accepted donor orientation without twisting the elbow hinge.
    axis=unit(pos-elbow);q=R.from_matrix(rotation@(dl@rot(world['hand_l'])).T).as_quat();q[:3]=axis*(q[:3]@axis);q/=max(np.linalg.norm(q),1e-12)
    rv=R.from_quat(q).as_rotvec()
    for suffix,w in (('_twist_01',1.),('_twist_02',.5)):
        n='lowerarm'+suffix+'_l'
        if n in out:
            t=R.from_rotvec(rv*w).as_matrix();out[n][:3,:3]=t@out[n][:3,:3];out[n][:3,3]=elbow+t@(out[n][:3,3]-elbow)
    out['hand_l'][:3,:3]=rotation*np.linalg.norm(world['hand_l'][:3,:3],axis=0);out['hand_l'][:3,3]=pos
    for n in names:
        if n not in digits:continue
        child=local[n].copy()
        if n in donor_local and n in DB and dp[n] in DB:
            bt=np.linalg.inv(B[parents[n]])@B[n];bd=np.linalg.inv(DB[dp[n]])@DB[n]
            target=rot(bt)@rot(bd).T@rot(donor_local[n])
            child[:3,:3]=blend(rot(child),target,amount)*np.linalg.norm(child[:3,:3],axis=0)
        out[n]=out[parents[n]]@child
    if 'ik_hand_l' in out:out['ik_hand_l']=out['hand_l']@np.linalg.inv(world['hand_l'])@world['ik_hand_l']
    return out
report={}
for family in ('vertical','canted','prism','angled'):
    dl={n:matrix(v) for n,v in zip(dn,donor['holds'][family]['local'])};dl=apply_tracks(dl,donor['holds'][family]['tracks'],0.);dw=compose(dn,dp,dl)
    rel=np.linalg.inv(dw['WPN_root'])@dw['hand_l'];rel[:3,3]*=100;rel[:3,:3]=rot(rel)
    target=np.array(recipe['foregrip_transforms'][family])@rel;target[:3,:3]=rot(target)
    shift=target[:3,3]-reference[:3,3];rotation_delta=rot(target)@rot(reference).T;clips=[]
    for path,clip in d['clips'].items():
        times=np.minimum(np.arange(len(clip['frames']))/clip['fps'],clip['duration']);tracks={n:[] for n in selected};count=0
        for time,rows in zip(times,clip['frames']):
            original={n:matrix(v) for n,v in zip(names,rows)};local=effective(path,rows,time);world=compose(names,parents,local)
            rel=np.linalg.inv(world['WPN_root'])@world['hand_l'];dist=np.linalg.norm(rel[:3,3]*100-reference[:3,3]);angle=np.degrees(R.from_matrix(rot(reference).T@rot(rel)).magnitude())
            w=float((1-ease((dist-.6)/5.5))*(1-ease((angle-14)/42)))
            if w>1.e-8:
                basis=rot(world['WPN_root']);pos=world['hand_l'][:3,3]+basis@shift*w
                rotation=basis@blend(np.eye(3),rotation_delta,w)@basis.T@rot(world['hand_l'])
                result=solve(world,local,pos,rotation,w,dl);count+=1
            else:result=world
            for n in selected:
                a=np.linalg.inv(result[parents[n]])@result[n];old=original[n];q=R.from_matrix(rot(a)@rot(old).T).as_quat()
                if q[3]<0:q=-q
                tracks[n].append([*(a[:3,3]-old[:3,3]),*q,*(np.linalg.norm(a[:3,:3],axis=0)-np.linalg.norm(old[:3,:3],axis=0))])
        encoded=[]
        for n,values in tracks.items():
            a=np.asarray(values);active=np.max(np.abs(a-[0,0,0,0,0,0,1,0,0,0]),axis=1)>1.e-6
            if not active.any():continue
            keep=active|np.r_[False,active[:-1]]|np.r_[active[1:],False];keep[0]=keep[-1]=True
            ids=np.array([0]) if np.max(np.abs(a-a[0]))<1.e-6 else np.nonzero(keep)[0]
            encoded.append(dict(bone=n,times=times[ids].tolist(),values=a[ids].ravel().tolist()))
        clips.append(dict(base=path,duration=clip['duration'],tracks=encoded))
        print('M249_GRIP_AUTHORED',family,path.split('.')[-1],count,flush=True)
    with gzip.open(r/(family+'.json.gz'),'wt') as f:json.dump(dict(family=family,clips=clips),f,separators=(',',':'))
    report[family]=dict(shift_root_cm=shift.tolist(),target_root_cm=target.tolist(),clips=len(clips),donor=donor['holds'][family]['clip'])
(r/'grip_recipe.json').write_text(json.dumps(report,indent=2))
