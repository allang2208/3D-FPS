"""Fit the released hand's travel to the actual stock, preserving grip endpoints."""
from pathlib import Path
exec(compile((Path(__file__).parent/'author_regrip.py').read_text().split('\nkeys=')[0],'author_setup','exec'))
import numpy as np
skin=bpy.data.objects['M24_V9_BareArms'];idx={n:i for i,n in enumerate(names)}
gn=[g.name for g in skin.vertex_groups]
V=np.array([(*v.co,1) for v in skin.data.vertices]);weights=np.zeros((len(V),len(names)))
for v in skin.data.vertices:
    for g in v.groups:
        if gn[g.group] in idx:weights[v.index,idx[gn[g.group]]]=g.weight
handbones=[n for n in names if under(n,'hand_r')];pure=weights[:,[idx[n] for n in handbones]].sum(1)>.96
selected=np.where(pure)[0][::4]
bind=np.einsum('vk,kij,vj->kvi',weights[selected],np.array([np.array(rest[n].inverted()) for n in names]),V[selected],optimize=True)
rays=[Vector((1,.073,.047)).normalized(),Vector((.031,1,.051)).normalized(),Vector((.047,.061,1)).normalized()]
def sdf(X):
    ds=[]
    for x in X:
        p=Vector(x);_,_,_,d=bv.find_nearest(p);inside=0
        if d<.04:
            for direction in rays:
                hit,n,_,_=bv.ray_cast(p,direction);inside+=hit is not None and n.dot(direction)>0
        ds.append(d*1000*(-1 if inside>=2 else 1))
    return np.array(ds)
def candidate(w,values):
    p,q,sc=native['hand_r'].decompose();pp,qq,ss=club['hand_r'].decompose()
    c1=Vector((.31,-.105,-.04));c2=Vector((.07,-.17,-.12))
    pos=p*(1-w)**3+c1*(3*(1-w)**2*w)+c2*(3*(1-w)*w*w)+pp*w**3
    pos.z-=.11*math.sin(math.pi*w)**2;pos+=Vector(values[:3])
    hand=Matrix.LocRotScale(pos,q.slerp(qq,ease((w-.25)/.65)),sc.lerp(ss,w))
    row=clone(rest);row['hand_r']=hand;rotations={}
    for n in names:
        if n=='hand_r' or not under(n,'hand_r'):continue
        lp,lq,ls=idle_local[n].decompose()
        if n in digits:lq=opened[n].slerp(closed[n],values[4 if n.startswith('thumb') else 3]);rotations[n]=lq
        row[n]=row[parents[n]]@Matrix.LocRotScale(lp,lq,ls)
    return row,rotations
steps=[i/50 for i in range(51)];out=[];last=[0.,0.,0.,0.,0.]
for w in steps:
    initial=ease((w-.55)/.45);v=[last[0],last[1],last[2],initial,initial] if 0<w<1 else [0.,0.,0.,initial,initial]
    def cost(values,detail=False):
        row,_=candidate(w,values)
        X=np.einsum('kij,kvj->vi',np.array([np.array(row[n]) for n in names]),bind,optimize=True)[:,:3]
        ds=sdf(X);pen=np.maximum(-ds-.65,0)
        val=float(30*np.mean(pen**2)+12*max(pen)**2+.012*sum((x*1000)**2 for x in values[:3])+4*sum((x-initial)**2 for x in values[3:])+.008*sum(((a-b)*1000)**2 for a,b in zip(values[:3],last[:3])))
        return {'score':val,'max_penetration_mm':float(max(pen)), 'parameters':values} if detail else val
    val=cost(v)
    if 0<w<1:
        for shift,turn in ((.02,.25),(.01,.15),(.005,.07),(.002,.03)):
            for _ in range(2):
                for axis in range(5):
                    for sign in (-1,1):
                        trial=list(v);trial[axis]+=sign*(shift if axis<3 else turn)
                        trial[axis]=max(-.08,min(.08,trial[axis])) if axis<3 else max(0,min(1,trial[axis]))
                        # Keep travel on one side of the stock between fitted poses.
                        if axis==0 and w<.20:trial[axis]=max(0,trial[axis])
                        if axis==0 and w>.80:trial[axis]=min(0,trial[axis])
                        value=cost(trial)
                        if value<val:v=trial;val=value
    row,rotations=candidate(w,v)
    out.append({'w':w,'hand':[list(r) for r in row['hand_r']],'rotations':{n:list(q) for n,q in rotations.items()},'fit':cost(v,True)})
    last=v;print('TRANSITION_FIT',w,out[-1]['fit'],flush=True)
(O/'transition_fit.json').write_text(json.dumps(out,indent=2));print('M24_TRANSITION_FIT_READY',flush=True)
