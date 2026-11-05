"""Adapt the factory power-grip contact to the actual skeleton stock surface."""
from pathlib import Path
exec(compile((Path(__file__).parent/'common.py').read_text(),'common','exec'))
import numpy as np
geometry=setup_geometry();vs,fs=geometry['stock'];bv=BVHTree.FromPolygons(vs,fs,all_triangles=True)
factory,_=compose(entry('base','quick_melee'),.25)
to_bind=rest['WPN_root']@factory['WPN_root'].inverted()
source={n:to_bind@m for n,m in factory.items()};H0=source['hand_r'].copy()
handbones=[n for n in names if under(n,'hand_r')];hand_index={n:i for i,n in enumerate(handbones)}
digits=[f'{d}_{i:02d}_r' for d in ('index','middle','ring','pinky','thumb') for i in (1,2,3)]
locals_={n:local(source,n) for n in handbones};qs={n:locals_[n].to_quaternion() for n in digits}
V=np.asarray([[p[0]*.01,-p[1]*.01,p[2]*.01,1.] for p in G['positions']])
weights=np.zeros((len(V),len(handbones)))
for v,ws in G['weights'].items():
    for n,w in ws.items():
        if n in hand_index:weights[int(v),hand_index[n]]=w
pure=weights.sum(1)>.985;dom=weights.argmax(1)
inverses=np.asarray([np.asarray(native[n].inverted()) for n in handbones])
def binding(ids):return np.einsum('vk,kij,vj->kvi',weights[ids],inverses,V[ids],optimize=True)
def handrow(H,rotations):
    out={'hand_r':H}
    for n in handbones:
        if n=='hand_r':continue
        p,q,s=locals_[n].decompose();out[n]=out[parents[n]]@Matrix.LocRotScale(p,rotations.get(n,q),s)
    return out
def points(H,rotations,W):
    row=handrow(H,rotations)
    return np.einsum('kij,kvj->vi',np.asarray([np.asarray(row[n]) for n in handbones]),W,optimize=True)[:,:3]
rays=[Vector(v).normalized() for v in ((1,.073,.047),(.031,1,.051),(.047,.061,1))]
def distances(X):
    out=[]
    for x in X:
        p=Vector(x);_,_,_,d=bv.find_nearest(p);inside=0
        if d<.025:
            for direction in rays:
                hit,n,_,_=bv.ray_cast(p,direction);inside+=hit is not None and n.dot(direction)>0
        out.append(d*1000*(-1 if inside>=2 else 1))
    return np.asarray(out)
palmbones=[hand_index[n] for n in handbones if n=='hand_r' or 'metacarpal' in n]
ids=np.where(pure&np.isin(dom,palmbones))[0][::4];palmW=binding(ids)
fingerW={}
for digit in ('index','middle','ring','pinky','thumb'):
    ids=np.where(pure&np.isin(dom,[hand_index[f'{digit}_{i:02d}_r'] for i in (2,3)]))[0][::7]
    fingerW[digit]=binding(ids)
allW=binding(np.where(pure)[0][::8])
def penalty(ds):
    p=np.maximum(-ds-.4,0.);return float(15*np.mean(p*p)+8*max(p)**2)
def grasp_cost(H,rotations):
    palm=distances(points(H,rotations,palmW));cost=penalty(distances(points(H,rotations,allW)))
    cost+=1.2*np.mean((np.sort(abs(palm))[:12]-1.2)**2)
    for digit,W in fingerW.items():
        d=distances(points(H,rotations,W));cost+=.7*np.mean((np.sort(abs(d))[:6]-1.)**2)
    return float(cost)
def moved(v):
    q=Euler(tuple(math.radians(x) for x in v[3:]),'XYZ').to_quaternion()
    pivot=H0@Vector((0.,.06,0.))
    return Matrix.LocRotScale(pivot+Vector(v[:3])*.001-q@(pivot-H0.translation),q@H0.to_quaternion(),H0.to_scale())
def cost(v):return grasp_cost(moved(v),qs)+.008*sum(x*x for x in v[:3])+.025*sum(x*x for x in v[3:])
best=[0.]*6;value=cost(best)
for y in (-45.,-25.,0.,25.,45.):
    for z in (-25.,0.,25.):
        trial=[0.,y,z,0.,0.,0.];v=cost(trial)
        if v<value:best,value=trial,v
for step in (12.,6.,3.,1.):
    for _ in range(2):
        for axis in range(6):
            for sign in (-1,1):
                trial=best.copy();trial[axis]+=step*sign;cap=50 if axis<3 else 18
                trial[axis]=max(-cap,min(cap,trial[axis]));v=cost(trial)
                if v<value:best,value=trial,v
H=moved(best);fit={'rigid_parameters_mm_degrees':best,'palm_cost':value,'digits':{}}
print('STOCK_PALM_FITTED',best,flush=True)
for digit in ('middle','ring','pinky','index','thumb'):
    ns=[f'{digit}_{i:02d}_r' for i in (1,2,3)];initial={n:qs[n].copy() for n in ns}
    ids=np.where(pure&np.isin(dom,[hand_index[n] for n in ns]))[0][::5];W=binding(ids)
    def rotations(v):
        out=dict(qs)
        for j,n in enumerate(ns):out[n]=initial[n]@Quaternion((0,0,1),math.radians(v[j]))
        if digit=='thumb':out[ns[0]]=initial[ns[0]]@Euler((math.radians(v[3]),math.radians(v[4]),math.radians(v[0])),'XYZ').to_quaternion()
        return out
    def finger_cost(v):
        d=distances(points(H,rotations(v),W));near=distances(points(H,rotations(v),fingerW[digit]))
        return penalty(d)+.8*np.mean((np.sort(abs(near))[:8]-1.)**2)+.06*sum(x*x for x in v)
    params=[0.]*(5 if digit=='thumb' else 3);value=finger_cost(params)
    for step in (10.,5.,2.,1.):
        for _ in range(2):
            for axis in range(len(params)):
                for sign in (-1,1):
                    trial=params.copy();trial[axis]=max(-22.,min(22.,trial[axis]+step*sign));v=finger_cost(trial)
                    if v<value:params,value=trial,v
    qs=rotations(params);fit['digits'][digit]={'offset_degrees':params,'fit_cost':float(value)}
    print('STOCK_DIGIT_FITTED',digit,params,flush=True)
data={'hand':[list(r) for r in H],'rotations':{n:list(q) for n,q in qs.items()},'source_hand':[list(r) for r in H0],'fit':fit,'meaning':'Factory power grip adapted to the real advanced stock; authoring fit, not visual acceptance.'}
(O/'stock_grip.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
print('M24_FACTORY_STOCK_GRIP_READY',flush=True)
