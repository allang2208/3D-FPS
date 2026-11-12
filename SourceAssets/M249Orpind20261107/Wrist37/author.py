"""Replace scoped local joint rotations; preserve every other channel and clip."""
from held import *
from scipy.interpolate import PchipInterpolator
from scipy.ndimage import gaussian_filter1d
import ast
tree=ast.parse((ROOT/'canonical_left.py').read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='regrip'],type_ignores=[]),'contact-regrip','exec'))
leftheld=pickle.load(open(HERE/'held.pkl','rb'))
cl,ua,la,ha,arm,hand=indices('l');left_owned=[cl]+arm+[ha]
rc,ru,rl,rh,rarm,rhand=indices('r');right_owned=[rc]+rarm+rhand
owned=left_owned+right_owned
basecurrent=pickle.load(open(ROOT/'current_poses.pkl','rb'))['base']
right36=pickle.load(open(ROOT/'right_final.pkl','rb'))
normal=next(p for p in right36 if p.endswith('_reload'));ref=right36[normal]['after'][np.argmin(abs(right36[normal]['times']-4.8))]
belt=ix['New_PKM_Belt_00'];ref_local=encode(ref[None],parents)[0]
def rigid(m):
    m=m.copy();m[:3,:3]=rot(m);return m
casefaces=faces[sections==g['slots'].index('FeedCase__NewBelt')]
caseids=np.unique(casefaces);caseids=caseids[dominant[caseids]==belt]
casecenter=(np.linalg.inv(ref[belt])@np.r_[skin(ref)[caseids].mean(0),1])
def cartridge_frame(w):
    # A round case does not force the palm to roll with the animated belt bone.
    # Preserve the case axis but keep the hand on the receiver's exposed side.
    axis=rot(w[belt])@rot(B[belt]).T@np.array([0.,1.,0.])
    up=rot(w[gun])@rot(B[gun]).T@np.array([0.,0.,1.])
    result=np.eye(4);result[:3,:3]=frame(axis,up);result[:3,3]=(w[belt]@casecenter)[:3]
    return result
contact=np.linalg.inv(cartridge_frame(ref))@rigid(ref[rh])

def apply_right(path):
    a=basecurrent[path];t=a['times'];old=a['world'];empty=path.endswith('_empty');offset=.9 if empty else 0
    weight=ease((t-(4.24-offset))/.28)*(1-ease((t-(5.10-offset))/.23))
    parameters=[];last=np.zeros(4)
    def posed(w,x,alpha):
        goal=cartridge_frame(w)@contact;turn=(R.from_matrix(rot(goal))*R.from_matrix(rot(w[rh])).inv()).as_rotvec()
        q=solve(w,x*alpha,'r',(goal[:3,3]-w[rh,:3,3])*alpha,R.from_rotvec(turn*alpha).as_matrix(),station_weight=alpha)
        return q
    for k,w in enumerate(old):
        alpha=weight[k]
        if alpha<1e-8:parameters.append(np.zeros(4));last=np.zeros(4);continue
        length=np.linalg.norm(w[rl,:3,3]-w[ru,:3,3])+np.linalg.norm(w[rh,:3,3]-w[rl,:3,3])
        def cost(x):
            q=posed(w,x,alpha)
            return max(0,bend(q,'r')-18)**2*8+.025*np.sum(np.degrees(x)**2)+.02*np.sum(np.degrees(x-last)**2)+max(0,np.linalg.norm(q[rh,:3,3]-q[ru,:3,3])-length*.97)**2*1e5
        fit=minimize(cost,last,method='SLSQP',bounds=[(-1.,1.)]*4,options=dict(maxiter=65,ftol=1e-6,eps=1e-5));last=fit.x;parameters.append(last)
    parameters=gaussian_filter1d(parameters,1.5,axis=0,mode='nearest');new=old.copy()
    for k,w in enumerate(old):
        alpha=weight[k]
        if alpha<1e-8:continue
        q=posed(w,parameters[k],alpha);local=encode(q[None],parents)[0]
        for b in rhand:
            if b==rh:continue
            turn=(R.from_quat(ref_local[b,3:7])*R.from_quat(local[b,3:7]).inv()).as_rotvec()
            local[b,3:7]=(R.from_rotvec(turn*alpha)*R.from_quat(local[b,3:7])).as_quat()
        new[k]=compose(local[None],parents)[0]
    return preserve_local(old,new,right_owned)

right=pickle.load(open(HERE/'right.pkl','rb')) if (HERE/'right.pkl').exists() else {p:apply_right(p) for p in right36}
pickle.dump(right,open(HERE/'right.pkl','wb'))
if (HERE/'right_smooth.pkl').exists():right=pickle.load(open(HERE/'right_smooth.pkl','rb'))
report={};candidate={}
for family in ['base','vertical','angled','canted','prism']:
    P=json.load(gzip.open(ROOT/(family+'.json.gz'),'rt'))
    ip=next(p for f,p in original if f==family and p.endswith('_idle'))
    home=original[(family,ip)]['after'][0];held=leftheld[family]
    for row in P['clips']:
        path=row['base'];key=(family,path)
        if key not in original:continue
        a=original[key];t=a['times'];old=a['after'];base=np.array(d['clips'][path]['frames']);priorlocal=layer(base,path,P,names,t);local=priorlocal.copy()
        if path==ip:
            goal=encode(held[None],parents)[0];local[:,left_owned,3:7]=goal[left_owned,3:7]
        else:
            offset=.9 if path.endswith('_empty') else 0
            cams=camera(family,path,t);ks=np.unique(np.r_[np.arange(0,len(t),4),len(t)-1]);params=[];last=np.zeros(4)
            for k in ks:
                w=old[k]
                if t[k]>=2.8-offset:params.append(last);continue
                length=np.linalg.norm(w[la,:3,3]-w[ua,:3,3])+np.linalg.norm(w[ha,:3,3]-w[la,:3,3]);minbox=min(.15,boxmargin(w));minvis=min(.2,margin(w,cams[k]))
                def pose(x):return anatomical(solve(w,x))
                def cost(x):
                    q=pose(x);roll=np.degrees(pronation(q))
                    return max(0,abs(roll)-55)**2*2+max(0,bend(q)-22)**2*8+.025*np.sum(np.degrees(x)**2)+.015*np.sum(np.degrees(x-last)**2)
                def constraints(x):
                    q=pose(x);return np.array([boxmargin(q)-minbox,margin(q,cams[k])-minvis,length*.98-np.linalg.norm(q[ha,:3,3]-q[ua,:3,3])])
                fit=minimize(cost,last,method='SLSQP',bounds=[(-.9,.9)]*3+[(-1.5,1.5)],constraints=[dict(type='ineq',fun=constraints)],options=dict(maxiter=65,ftol=1e-5,eps=1e-5))
                last=fit.x;params.append(last)
            curve=gaussian_filter1d(PchipInterpolator(t[ks],params,axis=0)(t),2,axis=0,mode='nearest')
            for k,w in enumerate(old):
                goal=w[gun]@np.linalg.inv(home[gun])@held
                incoming=1-ease((t[k]-.10)/.25);heldweight=ease((t[k]-(2.10-offset))/.70)
                q=anatomical(solve(w,curve[k]))
                amount=max(incoming,heldweight)
                if amount>0:q=anatomical(regrip(q,goal,amount,0.))
                newlocal=encode(q[None],parents)[0]
                local[k,left_owned,3:7]=newlocal[left_owned,3:7]
            rlocal=encode(right[path],parents);local[:,right_owned,3:7]=rlocal[:,right_owned,3:7]
        final=compose(local,parents);candidate[key]=dict(times=t,before=old,after=final)
        for b in owned:
            diff=R.from_quat(local[:,b,3:7])*R.from_quat(priorlocal[:,b,3:7]).inv()
            if diff.magnitude().max()<1e-7:continue
            track=next((x for x in row['tracks'] if x['bone']==names[b]),None)
            ts=np.unique(np.r_[t,track['times'] if track else []]);temp=np.zeros((len(t),10));temp[:,3:7]=diff.as_quat();delta=sample(temp.ravel(),t,ts)
            values=sample(track['values'],track['times'],ts) if track else np.tile([0,0,0,0,0,0,1,0,0,0.],(len(ts),1))
            values[:,3:7]=(R.from_quat(delta[:,3:7])*R.from_quat(values[:,3:7])).as_quat()
            for k in range(1,len(values)):
                if values[k-1,3:7]@values[k,3:7]<0:values[k,3:7]*=-1
            record=dict(bone=names[b],times=ts.tolist(),values=values.ravel().tolist())
            if track:track.update(record)
            else:row['tracks'].append(record)
        saved=layer(base,path,P,names,t);other=[i for i in range(len(names)) if i not in owned]
        translation_scale=float(abs(saved[:,:,[0,1,2,7,8,9]]-priorlocal[:,:,[0,1,2,7,8,9]]).max())
        unrelated=float(abs(saved[:,other]-priorlocal[:,other]).max())
        assert translation_scale<1e-8 and unrelated<1e-7
        points=final[:,:,:3,3][:,[ua,la,ha,ru,rl,rh]]
        report[family+'/'+path.split('.')[-1]]=dict(translation_scale_change=translation_scale,unrelated_change=unrelated,max_joint_step_cm=float(np.linalg.norm(np.diff(points,axis=0),axis=2).max()) if len(t)>1 else 0,left_palm_max_change_cm=float(np.linalg.norm(final[:,ha,:3,3]-old[:,ha,:3,3],axis=1).max()))
        print(family,path.split('.')[-1],report[family+'/'+path.split('.')[-1]],flush=True)
    with gzip.open(HERE/(family+'.json.gz'),'wt') as f:json.dump(P,f,separators=(',',':'))
pickle.dump(candidate,open(HERE/'candidate.pkl','wb'));(HERE/'joint_only_report.json').write_text(json.dumps(report,indent=2))
