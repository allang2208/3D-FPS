"""Apply the saved release-plane correction to this revision's exact candidate."""
from held import *
candidate=pickle.load(open(HERE/'candidate.pkl','rb'));right=pickle.load(open(HERE/'right_smooth.pkl','rb'))
c,u,e,h,arms,hands=indices('r');owned=[c]+arms+hands
report=json.loads((HERE/'joint_only_report.json').read_text())
for family in ['base','vertical','angled','canted','prism']:
    profile=json.load(gzip.open(HERE/(family+'.json.gz'),'rt'))
    for row in profile['clips']:
        path=row['base']
        if path not in right:continue
        a=candidate[(family,path)];t=a['times'];base=np.array(d['clips'][path]['frames']);old=layer(base,path,profile,names,t);local=old.copy();desired=encode(right[path],parents)
        local[:,owned,3:7]=desired[:,owned,3:7]
        for b in owned:
            diff=R.from_quat(local[:,b,3:7])*R.from_quat(old[:,b,3:7]).inv()
            if diff.magnitude().max()<1e-7:continue
            track=next(x for x in row['tracks'] if x['bone']==names[b]);ts=np.unique(np.r_[t,track['times']]);temp=np.zeros((len(t),10));temp[:,3:7]=diff.as_quat();delta=sample(temp.ravel(),t,ts);values=sample(track['values'],track['times'],ts)
            values[:,3:7]=(R.from_quat(delta[:,3:7])*R.from_quat(values[:,3:7])).as_quat()
            for k in range(1,len(values)):
                if values[k-1,3:7]@values[k,3:7]<0:values[k,3:7]*=-1
            track.update(times=ts.tolist(),values=values.ravel().tolist())
        final=compose(local,parents);a['after']=final
        points=final[:,:,:3,3][:,[ua,la,ha,u,e,h]]
        report[family+'/'+path.split('.')[-1]]['max_joint_step_cm']=float(np.linalg.norm(np.diff(points,axis=0),axis=2).max())
    with gzip.open(HERE/(family+'.json.gz'),'wt') as f:json.dump(profile,f,separators=(',',':'))
pickle.dump(candidate,open(HERE/'candidate.pkl','wb'));(HERE/'joint_only_report.json').write_text(json.dumps(report,indent=2))
print('Release correction overlaid on five profiles')
