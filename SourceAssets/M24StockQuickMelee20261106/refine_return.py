"""Delay individual fingertip closure on the actual independent grip shell."""
from pathlib import Path
exec(compile((Path(__file__).parent/'clearance.py').read_text().split("if __name__=='__main__':")[0],'current surfaces','exec'))
import copy
import sys
patch=json.load(gzip.open(O/'quick_melee_patch.json.gz','rt'))
report={};digits=('index','middle','ring','pinky','thumb')
times=[i/120 for i in range(74,94)]
def influence(t):return smooth((t-.61)/.06)*(1-smooth((t-.73)/.06))
def edited(original,digit,angles,t):
    row=clone(original);w=influence(t)
    for n in names:
        if not n.startswith(digit+'_') or not n.endswith('_r') or 'metacarpal' in n:continue
        p,q,s=local(original,n).decompose();j=int(n.split('_')[1])-1
        if j in range(3):q=q@Quaternion((0,0,1),math.radians(angles[j]*w))
        if digit=='thumb' and j==0 and len(angles)>3:
            q=q@Quaternion((1,0,0),math.radians(angles[3]*w))@Quaternion((0,1,0),math.radians(angles[4]*w))
        row[n]=row[parents[n]]@Matrix.LocRotScale(p,q,s)
    return row
for family,clip in patch.items():
    if '--dense-default' in sys.argv and family not in ('skeleton_base','skeleton_mag10'):continue
    kind=next((k for k in ('balanced','phantom','stable') if family.endswith('_'+k)),'Default')
    stock_names=('stock','carbon','stock_native','carbon_native') if kind=='Default' else ('stock','carbon')
    trees=[assembly_tree(stock,kind,'mag10' if 'mag10' in family else 'mag5') for stock in stock_names]
    rows=[rest_row(compose(clip,t)[0]) for t in times]
    family_params={}
    for digit in digits:
        if '--thumb-spread' in sys.argv and digit!='thumb':continue
        ids=np.array([i for i in hand_ids if RIGHT[int(W[i].argmax())].startswith(digit+'_')],dtype=int)[::1 if '--dense-default' in sys.argv else 5]
        if not len(ids):continue
        cached=[]
        for row in rows:
            points=V[ids].copy();weights,_=corrective_weights(row,morph.files)
            for n,w in weights.items():
                if n not in morph_cache:morph_cache[n]=morph[n]
                points[:,:3]+=morph_cache[n][ids]*w
            cached.append(np.einsum('vk,kij,vj->kvi',W[ids],inverses,points,optimize=True))
        def score(angles,details=False):
            total=0.;worst=0.
            for t,row,pre in zip(times,rows,cached):
                modified=edited(row,digit,angles,t)
                # Finger flex changes the runtime JC grip/pose signature.
                # Re-evaluate the corrective skin on the candidate itself;
                # frozen corrective weights can hide a regrip penetration.
                pts=skin_points(modified,ids,True)
                for bv in trees:
                    d=signed_distance(bv,pts,True);p=np.maximum(.5-d,0)
                    total+=float(np.mean(p*p));worst=max(worst,float(p.max()))
            result=12*total+50*worst*worst+.02*sum(a*a for a in angles)
            return (result,worst) if details else result
        a=[0.]*(5 if digit=='thumb' else 3);baseline,worst=score(a,True);best=baseline
        if worst<1.25:continue
        for step in (8.,4.,2.,1.):
            for j in range(len(a)):
                for sign in (-1,1):
                    trial=a.copy();trial[j]=max(-20,min(20,trial[j]+sign*step));cost=score(trial)
                    if cost<best:a,best=trial,cost
        if best<baseline-.1 and any(a):
            family_params[digit]=a
            rows=[edited(row,digit,a,t) for t,row in zip(times,rows)]
        print('REGRIP_DIGIT',family,digit,round(baseline,3),round(best,3),a,flush=True)
    if not family_params:report[family]={};continue
    result=copy.deepcopy(clip);tracks={tr['bone']:tr for tr in result['tracks']};affected=[f'{d}_{j:02d}_r' for d in family_params for j in (1,2,3)]
    out={n:[] for n in affected};last={}
    for i in range(217):
        t=i/240;row,_=compose(clip,t)
        for digit,angles in family_params.items():row=edited(row,digit,angles,t)
        for n in affected:
            p,q,s=(K@local(row,n)@K).decompose();bp,bq,bs=raw(D['clips'][clip['base']],t,n).decompose();dq=q@bq.inverted();dq.normalize()
            if n in last and dq.dot(last[n])<0:dq.negate()
            last[n]=dq.copy();out[n].extend([*(p-bp),dq.x,dq.y,dq.z,dq.w,*(s-bs)])
    for n,values in out.items():tracks[n]['times']=[i/240 for i in range(217)];tracks[n]['values']=values
    patch[family]=result;report[family]=family_params
with gzip.open(O/'quick_melee_patch.json.gz','wt',compresslevel=1) as fp:json.dump(patch,fp,separators=(',',':'))
(O/('return_thumb_spread.json' if '--thumb-spread' in sys.argv else 'return_fingers_dense.json' if '--dense-default' in sys.argv else 'return_fingers.json')).write_text(json.dumps(report,indent=2))
print('FINGER_RETURN_REFINED',flush=True)
