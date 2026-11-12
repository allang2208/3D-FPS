"""Joint rotations only; preserve source local translations, scales and finger poses."""
from fit_hold import *
fit=json.loads((root/'fit.json').read_text());report=json.loads((root/'authoring.json').read_text()) if (root/'authoring.json').exists() else {};cache=pickle.load(open(root/'candidate.pkl','rb')) if (root/'candidate.pkl').exists() else {}
rotation_bones=[cl]+arm+[ha]
for family in (sys.argv[1:] or ['base','vertical','angled','canted','prism','bipod']):
    support='base' if family=='bipod' else family;P=profile(family);c=d['clips'][idlepath]
    home=compose(layer(np.array(c['frames']),idlepath,profile(support),names,c['times']),parents)[0]
    reference=np.linalg.inv(home[gun])@home[ha];f=fit[support];parameters=np.array(f['parameters']);pivot=np.r_[f['pivot'],1.];axis=np.array(f['axis'])
    for row in P['clips']:
        path=row['base'];c=d['clips'].get(path)
        if c is None:continue
        t=np.array(c['times']);base=np.array(c['frames']);effective=layer(base,path,P,names,t);old=compose(effective,parents);motion=old.copy();new=old.copy()
        if family=='prism' and path.endswith(('A_M249_reload','A_M249_reload_empty')):
            # The previous free-hand forward arc and this new grasp rotation
            # together exceeded reach. Replace that earlier joint arc, rather
            # than stacking it; retain the current translations and scales.
            earlier=json.load(gzip.open(src/'prism.json.gz','rt'));previous=layer(base,path,earlier,names,t)
            working=effective.copy();working[:,rotation_bones,3:7]=previous[:,rotation_bones,3:7];motion=compose(working,parents);new=motion.copy()
        weights=[]
        for k,w in enumerate(old):
            rel=np.linalg.inv(w[gun])@w[ha];distance=np.linalg.norm((rel[:3,3]-reference[:3,3])*np.linalg.norm(home[gun,:3,:3],axis=0));angle=np.degrees(R.from_matrix(rot(reference).T@rot(rel)).magnitude())
            weights.append((1-ease((distance-.4)/2.0))*(1-ease((angle-4)/16.)))
        weights=np.array(weights)
        if path.endswith(('A_M249_reload','A_M249_reload_empty')):
            returning=ease((t-(t[-1]-.80))/.80)
            if family=='prism':returning=np.maximum(returning,gaussian_filter1d(weights,2.,mode='nearest')*ease((t-(t[-1]-1.2))/.35))
            weights=np.maximum(1-ease(t/.55),returning)
        elif '/SideMagazine' in path:
            weights*=np.maximum(1-ease(t/.2),ease((t-(t[-1]-.3))/.3))
        elif len(t)>2 and not path.endswith('A_M249_idle'):
            filtered=gaussian_filter1d(weights,2.5,mode='nearest');first=ease(t/.12);last=ease((t-(t[-1]-.12))/.12)
            filtered=weights[0]*(1-first)+filtered*first;weights=filtered*(1-last)+weights[-1]*last
        for k,w in enumerate(motion):
            weight=weights[k]
            if weight<1e-8:continue
            transform=w[gun]@np.linalg.inv(home[gun]);basis=rot(w[gun])@rot(home[gun]).T
            x=parameters*weight;x[:3]=basis@x[:3]
            new[k]=solve(w,x,(transform@pivot)[:3],basis@axis,weight)
        local=encode(new,parents);before=encode(old,parents)
        # Reconstruct using ONLY rotations. In particular never write tiny
        # numeric scale/translation drift from the world-space solve.
        applied=effective.copy();applied[:,rotation_bones,3:7]=local[:,rotation_bones,3:7]
        final=compose(applied,parents);cache[family,path]=final
        for i in rotation_bones:
            change=R.from_quat(local[:,i,3:7])*R.from_quat(before[:,i,3:7]).inv()
            if np.max(change.magnitude())<1e-8:continue
            original=next((x for x in row['tracks'] if x['bone']==names[i]),None)
            ts=np.unique(np.r_[t,original['times'] if original else []]);corr=np.zeros((len(t),10));corr[:,3:7]=change.as_quat()
            add=sample(corr.ravel(),t,ts);v=sample(original['values'],original['times'],ts) if original else np.tile([0.,0.,0.,0.,0.,0.,1.,0.,0.,0.],(len(ts),1))
            v[:,3:7]=(R.from_quat(add[:,3:7])*R.from_quat(v[:,3:7])).as_quat()
            for k in range(1,len(v)):
                if v[k-1,3:7]@v[k,3:7]<0:v[k,3:7]*=-1
            if original:original.update(times=ts.tolist(),values=v.ravel().tolist())
            else:row['tracks'].append(dict(bone=names[i],times=ts.tolist(),values=v.ravel().tolist()))
        pt=final[:,:,:3,3][:,rotation_bones];beforept=old[:,:,:3,3][:,rotation_bones]
        report[family+'/'+path.split('.')[-1]]=dict(frames=len(t),max_source_frame_step_cm=float(np.linalg.norm(np.diff(pt,axis=0),axis=2).max()) if len(t)>1 else 0.,max_previous_source_frame_step_cm=float(np.linalg.norm(np.diff(beforept,axis=0),axis=2).max()) if len(t)>1 else 0.,local_translation_changed=False,local_scale_changed=False,finger_local_pose_changed=False,weighted_frames=int((weights>1e-8).sum()))
    with gzip.open(root/(family+'.json.gz'),'wt') as out:json.dump(P,out,separators=(',',':'))
    print('JOINT_ONLY_AUTHORED',family,flush=True)
pickle.dump(cache,open(root/'candidate.pkl','wb'));(root/'authoring.json').write_text(json.dumps(report,indent=2))
