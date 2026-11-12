"""Route the right hand around the box through joint rotations only.

W37's stable pinch/lay/release and all left-arm poses are preserved.
"""
from pathlib import Path
import sys,copy
HERE38=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE38.parent/'Wrist37'))
from held import *
from scipy.ndimage import gaussian_filter1d

prior=pickle.load(open(HERE/'candidate.pkl','rb'))
c,u,e,h,arms,hands=indices('r');owned=list(dict.fromkeys([c]+arms+[h]))
result={};report={}
for path in [p for f,p in prior if f=='base' and p.endswith(('_reload','_reload_empty'))]:
    a=prior[('base',path)];old=a['after'];t=a['times'];offset=.9 if path.endswith('_empty') else 0.
    # X is the lateral side of the native receiver; Y runs along the barrel.
    # A Y-only detour cleared the box but crossed the receiver and was rejected.
    # Clear the outer edge first, then rise above the box/receiver before returning.
    side=ease((t-(4.16-offset))/.14)*(1-ease((t-(4.38-offset))/.12))
    rise=ease((t-(4.26-offset))/.13)*(1-ease((t-(4.43-offset))/.09))
    strength=np.maximum(side,rise)
    shifts=np.array([w[gun,:3,:3]@np.array([-.16*s,0.,.10*z]) for w,s,z in zip(old,side,rise)])
    params=[];last=np.zeros(4)
    for k,w in enumerate(old):
        if strength[k]<1e-9:params.append(np.zeros(4));last=np.zeros(4);continue
        length=np.linalg.norm(w[e,:3,3]-w[u,:3,3])+np.linalg.norm(w[h,:3,3]-w[e,:3,3])
        def posed(x):return solve(w,x,'r',shift=shifts[k])
        def cost(x):
            q=posed(x)
            return max(0,bend(q,'r')-24)**2*8+.02*np.sum(np.degrees(x)**2)+.02*np.sum(np.degrees(x-last)**2)
        def constraint(x):
            q=posed(x);return length*.98-np.linalg.norm(q[h,:3,3]-q[u,:3,3])
        fit=minimize(cost,last,method='SLSQP',bounds=[(-.9,.9)]*3+[(-1.4,1.4)],constraints=[dict(type='ineq',fun=constraint)],options=dict(maxiter=80,ftol=1e-6,eps=1e-5))
        if constraint(fit.x)<-.01:raise RuntimeError('Unreachable right hand arc')
        last=fit.x;params.append(last)
    params=gaussian_filter1d(params,1.2,axis=0,mode='nearest');new=old.copy()
    for k,w in enumerate(old):
        if strength[k]<1e-9:continue
        new[k]=solve(w,params[k],'r',shift=shifts[k])
    new=preserve_local(old,new,owned)
    result[path]=dict(times=t,old=old,new=new)
    print(path,'arc',np.linalg.norm(shifts,axis=1).max(),flush=True)

candidate=copy.deepcopy(prior)
for family in ['base','vertical','angled','canted','prism']:
    profile=json.load(gzip.open(HERE/(family+'.json.gz'),'rt'))
    for row in profile['clips']:
        path=row['base']
        if path not in result:continue
        a=candidate[(family,path)];t=a['times'];base=np.array(d['clips'][path]['frames'])
        before=layer(base,path,profile,names,t);desired=before.copy()
        wanted=encode(result[path]['new'],parents)
        desired[:,owned,3:7]=wanted[:,owned,3:7]
        for b in owned:
            delta=R.from_quat(desired[:,b,3:7])*R.from_quat(before[:,b,3:7]).inv()
            if delta.magnitude().max()<1e-7:continue
            track=next(x for x in row['tracks'] if x['bone']==names[b])
            ts=np.unique(np.r_[t,track['times']]);tmp=np.zeros((len(t),10));tmp[:,3:7]=delta.as_quat()
            turns=sample(tmp.ravel(),t,ts);values=sample(track['values'],track['times'],ts)
            values[:,3:7]=(R.from_quat(turns[:,3:7])*R.from_quat(values[:,3:7])).as_quat()
            for i in range(1,len(values)):
                if values[i-1,3:7]@values[i,3:7]<0:values[i,3:7]*=-1
            track.update(times=ts.tolist(),values=values.ravel().tolist())
        after=layer(base,path,profile,names,t);others=[i for i in range(len(names)) if i not in owned]
        translation_scale=float(np.max(abs(after[:,:,[0,1,2,7,8,9]]-before[:,:,[0,1,2,7,8,9]])))
        unrelated=float(np.max(abs(after[:,others]-before[:,others])))
        assert translation_scale<1e-8 and unrelated<1e-8
        final=compose(after,parents);a['after']=final
        report[family+'/'+path.split('.')[-1]]=dict(translation_scale_change=translation_scale,unrelated_change=unrelated,
            max_palm_step_cm=float(np.linalg.norm(np.diff(final[:,h,:3,3],axis=0),axis=1).max()),
            changed_bones=[names[i] for i in owned])
    with gzip.open(HERE38/(family+'.json.gz'),'wt') as stream:json.dump(profile,stream,separators=(',',':'))
pickle.dump(candidate,open(HERE38/'candidate.pkl','wb'))
(HERE38/'joint_only_report.json').write_text(json.dumps(report,indent=2))
print('Five candidate profiles written; no UE asset changed.')
