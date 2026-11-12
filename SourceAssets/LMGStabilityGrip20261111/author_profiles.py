"""Author bare-handguard and shared-grip poses through joint rotations only.

Source meshes, weights, local translations/scales and right-hand feed contacts
remain untouched. Free-hand mechanical actions retain their source trajectory.
"""
from pathlib import Path
import sys,json,gzip,pickle,copy
import numpy as np
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'M249Orpind20261107/Wrist36'))
import rig as G
from relax_reload import relax_reload
from pkm_cover_contact import cover_clearance
from scipy.spatial.transform import Rotation as R
from scipy.optimize import minimize
from scipy.ndimage import gaussian_filter1d
inputs=json.loads((HERE/'inputs.json').read_text());contacts=json.loads((HERE/'contacts.json').read_text());geometry=json.loads((HERE/'geometry.json').read_text())
report=json.loads((HERE/'authoring.json').read_text()) if (HERE/'authoring.json').exists() else {}
candidate=pickle.load(open(HERE/'authored_poses.pkl','rb')) if (HERE/'authored_poses.pkl').exists() else {}
def torso(key):
    d=inputs[key];G.names=d['names'];G.ix={n:i for i,n in enumerate(G.names)};G.parents=d['parents'];G.B=G.matrix(d['bind'])
    return d
for key in (sys.argv[1:] or ['M249','LMG201','PKM']):
    d=torso(key);names=G.names;ix=G.ix;parents=G.parents;gun=ix['WPN_root'];cl,ua,la,ha,arms,hands=G.indices('l');owned=[cl]+arms+[ha]
    family='base' if key=='M249' else 'vertical';profile=copy.deepcopy(d['profiles'][family]);profile['family']='handguard' if key=='M249' else 'stability';profile.pop('path',None)
    if key=='M249':motion=G.d['clips'];donor_key,donor_family='LMG201','base'
    else:motion=json.load(gzip.open(HERE/(key+'_motion.json.gz'),'rt'));donor_key,donor_family='M249','base'
    oldH=np.array(contacts[key][family]['hand_root']);target=np.array(contacts[donor_key][donor_family]['hand_root'])
    if key=='M249':
        # Fit the existing SVD support grasp to the actual handguard surfaces;
        # the previous bounding-box translation left fingers inside the guard.
        support=json.loads((HERE/'handguard_target.json').read_text())
        target=np.array(support['target'])
    else:target=np.array(geometry['parts'][key]['contact_transform'])@target
    delta=target@np.linalg.inv(oldH)
    donor=inputs[donor_key];donor_names=donor['names'];donor_ix={n:i for i,n in enumerate(donor_names)}
    dl=np.array(contacts[donor_key][donor_family]['local']);tl=np.array(contacts[key][family]['local'])
    digits=[i for i,n in enumerate(names) if n.endswith('_l') and n.startswith(('thumb_','index_','middle_','ring_','pinky_')) and n in donor_ix]
    turns={b:(R.from_quat(dl[donor_ix[names[b]],3:7])*R.from_quat(tl[b,3:7]).inv()).as_rotvec() for b in digits}
    if key=='M249':
        turns={b:(R.from_quat(support['digits'][names[b]])*R.from_quat(tl[b,3:7]).inv()).as_rotvec() for b in digits}
    for row in profile['clips']:
        path=row['base'];source=motion[path];times=np.array(source['times']);base=np.array(source['frames']);before=G.layer(base,path,profile,names,times);world=G.compose(before,parents)
        weights=[];shifts=[];rotations=[]
        for w in world:
            rel=np.linalg.inv(w[gun])@w[ha];rel[:3,3]*=100;rel[:3,:3]=G.rot(rel)
            distance=np.linalg.norm(rel[:3,3]-oldH[:3,3]);angle=np.degrees(R.from_matrix(rel[:3,:3]@oldH[:3,:3].T).magnitude())
            weight=float((1-G.ease((distance-1.2)/5.5))*(1-G.ease((angle-20)/50)))
            wanted=delta@rel;point=(w[gun]@np.r_[wanted[:3,3]*.01,1])[:3]
            rotation=G.rot(w[gun])@wanted[:3,:3]@G.rot(w[ha]).T
            weights.append(weight);shifts.append(point-w[ha,:3,3]);rotations.append(R.from_matrix(rotation).as_rotvec())
        weights=np.array(weights)
        # GripLayer56's 4/s contact ramp, evaluated offline in both directions
        # to anticipate release and preserve free mechanical contacts.
        for i in range(1,len(times)):
            weights[i]=min(weights[i],weights[i-1]+4*(times[i]-times[i-1]))
        for i in range(len(times)-2,-1,-1):
            weights[i]=min(weights[i],weights[i+1]+4*(times[i+1]-times[i]))
        weights=G.ease(weights)
        shifts=np.asarray(shifts)*weights[:,None]
        rotations=R.from_rotvec(np.asarray(rotations)*weights[:,None]).as_matrix()
        params=[];last=np.zeros(4)
        for w,weight,shift,turn in zip(world,weights,shifts,rotations):
            if weight<1e-8:params.append(np.zeros(4));last=np.zeros(4);continue
            length=np.linalg.norm(w[la,:3,3]-w[ua,:3,3])+np.linalg.norm(w[ha,:3,3]-w[la,:3,3])
            def posed(x):return G.solve(w,x,'l',shift=shift,hand_rotation=turn,station_weight=weight)
            def cost(x):
                q=posed(x)
                return max(0,G.bend(q,'l')-12)**2*8+.025*np.sum(np.degrees(x)**2)+.018*np.sum(np.degrees(x-last)**2)
            def reach(x):
                q=posed(x);return length*.985-np.linalg.norm(q[ha,:3,3]-q[ua,:3,3])
            fit=minimize(cost,last,method='SLSQP',bounds=[(-1.3,1.3)]*3+[(-2.,2.)],constraints=[dict(type='ineq',fun=reach)],options=dict(maxiter=80,ftol=1e-6,eps=1e-5))
            if reach(fit.x)<-.02:raise RuntimeError('Unreachable authored grip '+key+' '+path)
            last=fit.x;params.append(last*weight)
        params=np.array(params)
        if len(params)>3:params=gaussian_filter1d(params,1.,axis=0,mode='nearest')
        changed=world.copy()
        for k,w in enumerate(world):
            if weights[k]>1e-8:changed[k]=G.solve(w,params[k],'l',shift=shifts[k],hand_rotation=rotations[k],station_weight=weights[k])
        if key!='M249' and '_reload' in path:
            changed=relax_reload(changed,times,weights)
            if key=='PKM':
                changed=cover_clearance(changed,times,path.endswith('_empty'))
        local=before.copy();solved=G.encode(changed,parents);local[:,owned,3:7]=solved[:,owned,3:7]
        for b in digits:local[:,b,3:7]=(R.from_rotvec(weights[:,None]*turns[b])*R.from_quat(before[:,b,3:7])).as_quat()
        for b in owned+digits:
            correction=R.from_quat(local[:,b,3:7])*R.from_quat(before[:,b,3:7]).inv()
            if correction.magnitude().max()<1e-8:continue
            prior=next((t for t in row['tracks'] if t['bone']==names[b]),None);ts=np.unique(np.r_[times,prior['times'] if prior else []])
            tmp=np.zeros((len(times),10));tmp[:,3:7]=correction.as_quat();dq=G.sample(tmp.ravel(),times,ts)
            value=G.sample(prior['values'],prior['times'],ts) if prior else np.tile([0,0,0,0,0,0,1,0,0,0.],(len(ts),1))
            value[:,3:7]=(R.from_quat(dq[:,3:7])*R.from_quat(value[:,3:7])).as_quat()
            for i in range(1,len(value)):
                if value[i-1,3:7]@value[i,3:7]<0:value[i,3:7]*=-1
            track=dict(bone=names[b],times=ts.tolist(),values=value.ravel().tolist())
            if prior:prior.update(track)
            else:row['tracks'].append(track)
        row.pop('retained_idle',None)
        candidate[(key,path)]=dict(times=times,before=world,after=G.compose(local,parents),weights=weights)
        print('Authored',key,path.rsplit('.',1)[-1],flush=True)
    with gzip.open(HERE/(key+'_profile.json.gz'),'wt') as f:json.dump(profile,f,separators=(',',':'))
    report[key]=dict(family=profile['family'],clips=len(profile['clips']),target_hand_root=target.tolist(),joint_rotation_only=True,source_mesh_unchanged=True,runtime_tested=False)
pickle.dump(candidate,open(HERE/'authored_poses.pkl','wb'))
(HERE/'authoring.json').write_text(json.dumps(report,indent=2))
