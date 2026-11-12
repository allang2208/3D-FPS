"""Bake only local joint rotations into the existing shared pose profiles."""
from rig import *
from scipy.ndimage import gaussian_filter1d
left=pickle.load(open(ROOT/'left_final.pkl','rb'));right=pickle.load(open(ROOT/'right_final.pkl','rb'));report={};cache={}
lc,lu,ll,lh,larm,lhand=indices('l');rc,ru,rl,rh,rarm,rhand=indices('r');left_owned=[lc]+larm+[lh];right_owned=[rc]+rarm+rhand;gun=ix['WPN_root']
for family in ['base','vertical','angled','canted','prism']:
    P=payload(family);ip=next(p for p in d['clips'] if p.endswith('_idle'));oldhome=left[(family,ip)]['before'][0];home=left[(family,ip)]['after'][0];reference=np.linalg.inv(oldhome[gun])@oldhome[lh]
    for row in P['clips']:
        path=row['base'];c=d['clips'].get(path)
        if c is None or (family,path) not in left:continue
        t=np.array(c['times']);base=np.array(c['frames']);effective=layer(base,path,P,names,t);old=compose(effective,parents);local=effective.copy();owned=[]
        if (family,path) in left:
            newlocal=encode(left[(family,path)]['after'],parents);local[:,left_owned,3:7]=newlocal[:,left_owned,3:7];owned+=left_owned
        if path in right:
            rlcl=encode(right[path]['after'],parents);local[:,right_owned,3:7]=rlcl[:,right_owned,3:7];owned+=right_owned
        if not owned:continue
        final=compose(local,parents);cache[(family,path)]=dict(times=t,before=old,after=final)
        for b in set(owned):
            diff=(R.from_quat(local[:,b,3:7])*R.from_quat(effective[:,b,3:7]).inv())
            if diff.magnitude().max()<1e-7:continue
            prior=next((x for x in row['tracks'] if x['bone']==names[b]),None);ts=np.unique(np.r_[t,prior['times'] if prior else []]);corr=np.zeros((len(t),10));corr[:,3:7]=diff.as_quat();add=sample(corr.ravel(),t,ts)
            v=sample(prior['values'],prior['times'],ts) if prior else np.tile([0,0,0,0,0,0,1,0,0,0.],(len(ts),1));v[:,3:7]=(R.from_quat(add[:,3:7])*R.from_quat(v[:,3:7])).as_quat()
            for k in range(1,len(v)):
                if v[k-1,3:7]@v[k,3:7]<0:v[k,3:7]*=-1
            track=dict(bone=names[b],times=ts.tolist(),values=v.ravel().tolist())
            if prior:prior.update(track)
            else:row['tracks'].append(track)
        saved=layer(base,path,P,names,t);unowned=[i for i in range(len(names)) if i not in owned]
        offset=float(abs(saved[:,:,[0,1,2,7,8,9]]-effective[:,:,[0,1,2,7,8,9]]).max());unrelated=float(abs(saved[:,unowned]-effective[:,unowned]).max())
        if offset>1e-8 or unrelated>1e-7:raise RuntimeError('Joint-only invariant failed '+family+path)
        pts=final[:,:,:3,3][:,[lu,ll,lh,ru,rl,rh]];beforepts=old[:,:,:3,3][:,[lu,ll,lh,ru,rl,rh]]
        report[family+'/'+path.split('.')[-1]]=dict(local_translation_scale_change=offset,unrelated_change=unrelated,max_joint_frame_step_cm=float(np.linalg.norm(np.diff(pts,axis=0),axis=2).max()) if len(t)>1 else 0,previous_max_joint_frame_step_cm=float(np.linalg.norm(np.diff(beforepts,axis=0),axis=2).max()) if len(t)>1 else 0)
    with gzip.open(ROOT/(family+'.json.gz'),'wt') as f:json.dump(P,f,separators=(',',':'))
    print('AUTHORED',family,flush=True)
pickle.dump(cache,open(ROOT/'candidate.pkl','wb'));(ROOT/'joint_only_report.json').write_text(json.dumps(report,indent=2))
