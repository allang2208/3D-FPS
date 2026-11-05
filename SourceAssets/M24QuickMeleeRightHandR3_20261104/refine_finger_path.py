"""Bounded digit clearance over the authored right-arm route, including JC skin."""
from pathlib import Path
exec(compile((Path(__file__).parent/'surface.py').read_text(),'skin and geometry','exec'))
import copy
patch=json.load(gzip.open(O/'arm_path_patch.json.gz','rt'))
for family,clip in patch.items():
    D['profiles'][family]['clips']=[clip if c['base']==clip['base'] else c for c in D['profiles'][family]['clips']]
digits=('thumb','index','middle','ring','pinky')
fingerbones=[n for n in handbones if n!='hand_r']
times=sorted(set([i/60 for i in range(55)]+[.015,.03,.045,.08,.105,.12,.125,.14,.45,.48,.51,.55,.65,.70,.72,.84]))
result={};report={'scope':'Bounded local digit clearance only; actual assembled geometry and native JC skin','profiles':{}}
final={};FPS=240
for family,clip in patch.items():
    kind=next((k for k in ('balanced','phantom','stable') if family.endswith('_'+k)),'Default')
    bv=weapon_tree(kind,'mag10' if 'mag10' in family else 'mag5')
    controls=[];previous={d:[0.]*5 if d=='thumb' else [0.]*3 for d in digits}
    paired=family.replace('skeleton_mag10','skeleton_base')
    # Magazine variants have the same right-side animation. Only reuse a fit
    # when all digit and arm inputs are exactly the same as the fitted variant.
    own=[tr for tr in clip['tracks'] if tr['bone'] in RIGHT]
    paired_clip=patch.get(paired,clip)
    same=family!=paired and own==[tr for tr in paired_clip['tracks'] if tr['bone'] in RIGHT]
    if same:controls=copy.deepcopy(report['profiles'][paired]['controls'])
    else:
        for t in times:
            reference,_=compose(clip,t);row=clone(reference);params={}
            active=smooth(t/.03)*(1-smooth((t-.76)/.08))
            inv=rest['WPN_root']@row['WPN_root'].inverted()
            for digit in digits:
                ns=[f'{digit}_{i:02d}_r' for i in (1,2,3)]
                locals0={n:local(reference,n) for n in ns}
                ids=hand_ids[np.sum(W[hand_ids][:,[ri[n] for n in ns]],axis=1)>.5][::2]
                def changed(v):
                    candidate=clone(row)
                    for j,n in enumerate(ns):
                        p,q,s=locals0[n].decompose()
                        delta=Euler(tuple(math.radians(x) for x in v[:3]),'XYZ').to_quaternion() if digit=='thumb' and j==0 else Quaternion((0,0,1),math.radians(v[j+2] if digit=='thumb' else v[j]))
                        candidate[n]=candidate[parents[n]]@Matrix.LocRotScale(p,q@delta,s)
                    return candidate
                def cost(v,details=False):
                    candidate=changed(v);X=skin_points(candidate,ids,True)
                    X=(np.c_[X,np.ones(len(X))]@np.asarray(inv).T)[:,:3]
                    ds=signed_distance(bv,X,True);p=np.maximum(-ds-.2,0.)
                    value=250*np.mean(p*p)+160*max(p)**2+.08*sum(x*x for x in v)+.12*sum((a-b)**2 for a,b in zip(v,previous[digit]))
                    return (value,float(max(p))) if details else value
                v=[0.]*len(previous[digit]);value,depth=cost(v,True)
                if active>.001 and (depth>.25 or max(abs(x) for x in previous[digit])>.2):
                    seed=[x*.8 for x in previous[digit]];seed_cost=cost(seed)
                    if seed_cost<value:v,value=seed,seed_cost
                    for step in (6.,3.,1.):
                        for _ in range(2):
                            for axis in range(len(v)):
                                for sign in (-1,1):
                                    trial=v.copy();limit=(20. if digit=='thumb' else 14.)*active
                                    trial[axis]=max(-limit,min(limit,trial[axis]+step*sign));c=cost(trial)
                                    if c<value:v,value=trial,c
                params[digit]=v;previous[digit]=v;row=changed(v)
            controls.append({'time':t,'digits':params})
        print('DIGIT_CLEARANCE_FIT',family,flush=True)
    tracks={n:[] for n in fingerbones};last={};rows=[];bake_times=[i/FPS for i in range(217)]
    for t in bake_times:
        row,_=compose(clip,t);original=clone(row)
        i=max(0,min(len(times)-2,bisect.bisect_right(times,t)-1));a,b=controls[i:i+2];w=smooth((t-a['time'])/(b['time']-a['time']))
        offsets={}
        for digit in digits:
            v=[x*(1-w)+y*w for x,y in zip(a['digits'][digit],b['digits'][digit])]
            for j in range(3):
                n=f'{digit}_{j+1:02d}_r'
                offsets[n]=Euler(tuple(math.radians(x) for x in v[:3]),'XYZ').to_quaternion() if digit=='thumb' and j==0 else Quaternion((0,0,1),math.radians(v[j+2] if digit=='thumb' else v[j]))
        for n in fingerbones:
            p,q,s=local(original,n).decompose();row[n]=row[parents[n]]@Matrix.LocRotScale(p,q@offsets.get(n,Quaternion()),s)
            p,q,s=(K@local(row,n)@K).decompose();bp,bq,bs=raw(D['clips'][clip['base']],t,n).decompose();dq=q@bq.inverted();dq.normalize()
            if n in last and dq.dot(last[n])<0:dq.negate()
            last[n]=dq.copy();tracks[n].extend([*(p-bp),dq.x,dq.y,dq.z,dq.w,*(s-bs)])
        rows.append(row)
    replacement={n:{'bone':n,'times':bake_times,'values':v} for n,v in tracks.items()}
    current=copy.deepcopy(clip);current['tracks']=[replacement.pop(tr['bone'],tr) for tr in current['tracks']]+list(replacement.values())
    result[family]=current;final[family]=rows;report['profiles'][family]={'controls':controls,'reused_from':paired if same else None}
with gzip.open(O/'quick_melee_patch.json.gz','wt',compresslevel=1) as fp:json.dump(result,fp,separators=(',',':'))
with gzip.open(O/'digit_path_patch.json.gz','wt',compresslevel=1) as fp:json.dump(result,fp,separators=(',',':'))
(O/'finger_path.json').write_text(json.dumps(report,indent=2))
code=(S/'M24QuickMeleeGrip20261104/author.py').read_text().split('# Native editable rig plus the current V9 skin and runtime-equivalent JC tracks.')[1]
code=code.replace('M24_QuickMelee_CurrentGrip_Editable.blend','M24_QuickMelee_RightHandR3_Editable.blend').replace('s.render.fps = 200','s.render.fps = 240').replace('(len(rows) - 1) / 200','(len(rows) - 1) / 240').replace('s.frame_end=180','s.frame_end=216').replace("O/'authoring.json'","O/'finger_path_export.json'")
exec(compile(code,'native editable export','exec'))
print('M24_RIGHT_DIGIT_CLEARANCE_COMPLETE',flush=True)
