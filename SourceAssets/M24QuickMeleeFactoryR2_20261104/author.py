"""Carry the factory stock-led action into the actual advanced-stock assembly.

The original weapon roll, regrip rhythm and arm bend planes are the donor.
Only physical grip registration, native chain reach and boundary idle differ.
"""
from pathlib import Path
exec(compile((Path(__file__).parent/'common.py').read_text(),'common','exec'))
import numpy as np
geometry=setup_geometry();stock_points=geometry['stock'][0]
rear=min(v.y for v in stock_points);pad=[v for v in stock_points if v.y<rear+.006]
stock_local=rest['WPN_root'].inverted()@(sum(pad,Vector())/len(pad))
grip=json.loads((O/'stock_grip.json').read_text())
closed_hand=Matrix(grip['hand']);source_hand=Matrix(grip['source_hand'])
closed_delta=closed_hand@source_hand.inverted()
source_contact,_=compose(entry('base','quick_melee'),.25)
closed_q={n:Quaternion(q) for n,q in grip['rotations'].items()}
finger_delta={n:q@local(source_contact,n).to_quaternion().inverted() for n,q in closed_q.items()}
handbones=[n for n in names if under(n,'hand_r')];hi={n:i for i,n in enumerate(handbones)}
V=np.asarray([[p[0]*.01,-p[1]*.01,p[2]*.01,1.] for p in G['positions']])
weights=np.zeros((len(V),len(handbones)))
for i,ws in G['weights'].items():
    for n,w in ws.items():
        if n in hi:weights[int(i),hi[n]]=w
ids=np.where(weights.sum(1)>.985)[0][::9]
binding=np.einsum('vk,kij,vj->kvi',weights[ids],np.asarray([np.asarray(native[n].inverted()) for n in handbones]),V[ids],optimize=True)
rays=[Vector(v).normalized() for v in ((1,.073,.047),(.031,1,.051),(.047,.061,1))]
def arm_weight(t):return smooth(t/.14)*(1-smooth((t-.68)/.22))
def open_weight(t):return smooth((t-.005)/.025)*(1-smooth((t-.68)/.04))
def tree_for(kind):
    points=[];faces=[]
    for name in ('stock','front','grip_'+kind):
        p,f=geometry[name];offset=len(points);points.extend(p);faces.extend([tuple(offset+i for i in face) for face in f])
    return BVHTree.FromPolygons(points,faces,all_triangles=True)
def regrip_clearance(row,bv):
    unpose=rest['WPN_root']@row['WPN_root'].inverted()
    transforms=np.asarray([np.asarray(unpose@row[n]) for n in handbones])
    X=np.einsum('kij,kvj->vi',transforms,binding,optimize=True)[:,:3]
    penetrations=[]
    for x in X:
        p=Vector(x);_,_,_,d=bv.find_nearest(p);inside=0
        if d<.03:
            for direction in rays:
                hit,n,_,_=bv.ray_cast(p,direction);inside+=hit is not None and n.dot(direction)>0
        penetrations.append(max(0.,d*1000-.6) if inside>=2 else 0.)
    p=np.asarray(penetrations);return float(18*np.mean(p*p)+10*max(p)**2)

def supported_arm(row,reference,idle,side):
    u,l,h=[n+'_'+side for n in ('upperarm','lowerarm','hand')]
    S0=reference[u].translation;E0=reference[l].translation;H0=reference[h].translation
    A=(idle[l].translation-idle[u].translation).length;B=(idle[h].translation-idle[l].translation).length
    H=row[h].translation;v=H-S0;direction=v.normalized()
    # Preserve the original bend range. Grip adaptation cannot force the elbow
    # into a much tighter fold or stretch either native segment.
    reference_distance=(H0-S0).length
    minimum=max(abs(A-B)+.005,reference_distance-.025)
    maximum=max(reference_distance,min(A+B-.001,(A+B)*.96))
    distance=max(minimum,min(maximum,v.length))
    S1=H-direction*distance;axis=direction
    along=(A*A-B*B+distance*distance)/(2*distance)
    radius=math.sqrt(max(1e-10,A*A-along*along));center=S1+axis*along
    pole=E0-center;pole-=axis*pole.dot(axis)
    if pole.length<1e-8:
        pole=idle[l].translation-idle[u].translation;pole-=axis*pole.dot(axis)
    E=center+pole.normalized()*radius
    upper=(E0-S0).normalized().rotation_difference((E-S1).normalized())
    lower=(H0-E0).normalized().rotation_difference((H-E).normalized())
    U=Matrix.LocRotScale(S1,upper@reference[u].to_quaternion(),idle[u].to_scale())
    L=Matrix.LocRotScale(E,lower@reference[l].to_quaternion(),idle[l].to_scale())
    row['clavicle_'+side]=reference['clavicle_'+side].copy();row['clavicle_'+side].translation+=S1-S0
    carried_hand=lower@reference[h].to_quaternion()
    extra=row[h].to_quaternion()@carried_hand.inverted()
    if extra.w<0:extra.negate()
    roll=2*math.atan2(Vector((extra.x,extra.y,extra.z)).dot((H-E).normalized()),extra.w)
    for n in names:
        if under(n,h):continue
        if under(n,l):row[n]=L@reference[l].inverted()@reference[n]
        elif under(n,u):row[n]=U@reference[u].inverted()@reference[n]
        if n.startswith('lowerarm_twist') and n.endswith('_'+side):
            share=1. if '_01_' in n else .5
            row[n]=Matrix.LocRotScale(row[n].translation,Quaternion((H-E).normalized(),roll*share)@row[n].to_quaternion(),idle[n].to_scale())
    row[u]=U;row[l]=L;row['ik_hand_'+side]=row[h].copy()
    return {'shoulder_shift_mm':(S1-S0).length*1000,'elbow_shift_mm':(E-E0).length*1000,'extra_pronation_deg':math.degrees(roll)}

TIMES=[i/200 for i in range(181)]
TRAVEL=(0.,.005,.015,.03,.045,.06,.08,.10,.12,.14,.25,.325,.45,.48,.51,.54,.57,.60,.63,.66,.68,.70,.72,.80,.90)
patch={};final={};report={'duration':.9,'contact':.25,'fps':200,'reference':'Current factory base/mag10 stock-led club-regrip action', 'scope':'Eight advanced-stock profiles; factory donor assets unchanged','runtime_tested':False,'rendered':False,'profiles':{}}
for family in D['profiles']:
    if not family.startswith('skeleton_'):continue
    base='mag10' if 'mag10' in family else 'base'
    idle,_=compose(entry(family,'idle'),0.);donor_idle,_=compose(entry(base,'idle'),0.)
    original=entry(base,'quick_melee');own=entry(family,'quick_melee')
    kind=next((k for k in ('balanced','phantom','stable') if family.endswith('_'+k)),'Default');bv=tree_for(kind)
    idle_native=rest['WPN_root']@idle['WPN_root'].inverted()@idle['hand_r']
    donor_native=rest['WPN_root']@donor_idle['WPN_root'].inverted()@donor_idle['hand_r']
    idle_delta=idle_native@donor_native.inverted()
    idle_digits={n:local(idle,n).to_quaternion()@local(donor_idle,n).to_quaternion().inverted() for n in handbones if n!='hand_r'}
    cache={}
    def group(t,travel=Vector()):
        if t not in cache:cache[t]=compose(original,t)[0]
        donor=cache[t];row=clone(donor);w=grip_weight(t);a=arm_weight(t)
        root=donor['WPN_root']@donor_idle['WPN_root'].inverted()@idle['WPN_root']
        root.translation+=(donor['WPN_StockContact'].translation-root@stock_local)*w
        carry=root@donor['WPN_root'].inverted()
        for n in names:
            if under(n,'WPN_root'):row[n]=carry@donor[n]
        row['WPN_StockContact'].translation=root@stock_local
        # The left hand remains on its current actual forend through the swing.
        for n in names:
            if under(n,'hand_l'):row[n]=root@idle['WPN_root'].inverted()@idle[n]
        native_hand=rest['WPN_root']@donor['WPN_root'].inverted()@donor['hand_r']
        adapted=lerp(idle_delta,closed_delta,w)@native_hand
        adapted.translation+=travel
        row['hand_r']=root@rest['WPN_root'].inverted()@adapted
        release=open_weight(t)
        for n in handbones:
            if n=='hand_r':continue
            p,q,s=local(donor,n).decompose()
            q=Quaternion().slerp(idle_digits[n],1-release)@q
            if n in finger_delta:q=Quaternion().slerp(finger_delta[n],w)@q
            row[n]=row[parents[n]]@Matrix.LocRotScale(p,q,s)
        # Use the actual donor chain, including its roll and bend-plane history.
        reference={n:lerp(idle[n],donor[n],a) for n in names}
        return row,reference
    controls=[]
    for t in TRAVEL:
        best=Vector();w=grip_weight(t);release=open_weight(t)
        cap=.035*math.sin(math.pi*w)**2*release
        if cap>.001:
            previous=controls[-1]['offset'] if controls else Vector()
            def score(v):
                row,_=group(t,v)
                return regrip_clearance(row,bv)+.03*(v.length*1000)**2+.008*((v-previous).length*1000)**2
            value=score(best)
            for step in (.012,.006,.003,.0015):
                for _ in range(2):
                    for axis in range(3):
                        for sign in (-1,1):
                            trial=best.copy();trial[axis]=max(-cap,min(cap,trial[axis]+step*sign));cost=score(trial)
                            if cost<value:best,value=trial,cost
        controls.append({'time':t,'offset':best.copy()})
    print('M24_FACTORY_TRAVEL_FITTED',family,flush=True)
    rows=[];tracks={n:[] for n in names};last={};support=[]
    for t in TIMES:
        i=max(0,min(len(TRAVEL)-2,bisect.bisect_right(TRAVEL,t)-1));a,b=controls[i:i+2]
        w=smooth((t-a['time'])/(b['time']-a['time']));travel=a['offset'].lerp(b['offset'],w)
        row,reference=group(t,travel)
        info={side:supported_arm(row,reference,idle,side) for side in ('l','r')}
        if t==0. or t==.9:
            row=clone(idle);row['WPN_StockContact'].translation=row['WPN_root']@stock_local
        rows.append(row)
        if any(abs(t-k)<1e-8 for k in (0.,.05,.15,.25,.325,.46,.60,.72,.9)):support.append({'time':t,**info})
        for n in names:
            p,q,s=(K@local(row,n)@K).decompose();bp,bq,bs=raw(D['clips'][own['base']],t,n).decompose()
            dq=q@bq.inverted();dq.normalize()
            if n in last and dq.dot(last[n])<0:dq.negate()
            last[n]=dq.copy();tracks[n].extend([*(p-bp),dq.x,dq.y,dq.z,dq.w,*(s-bs)])
    compact=[]
    for n,values in tracks.items():
        seq=[values[i:i+10] for i in range(0,len(values),10)]
        constant=all(max(abs(x-y) for x,y in zip(v,seq[0]))<2e-7 for v in seq)
        compact.append({'bone':n,'times':[0.] if constant else TIMES,'values':seq[0] if constant else values})
    patch[family]={'base':own['base'],'duration':own['duration'],'tracks':compact};final[family]=rows
    report['profiles'][family]={'donor':base,'grip':kind,'travel_controls':[{'time':v['time'],'offset_m':list(v['offset'])} for v in controls],'support_controls':support,'keys':len(TIMES)}
    print('M24_FACTORY_REGRIP_AUTHORED',family,flush=True)
with gzip.open(O/'quick_melee_patch.json.gz','wt',compresslevel=1) as fp:json.dump(patch,fp,separators=(',',':'))

# Reuse only the native editable export, including current JC corrective keys.
FPS=200
code=(S/'M24QuickMeleeGrip20261104/author.py').read_text().split('# Native editable rig plus the current V9 skin and runtime-equivalent JC tracks.')[1]
code=code.replace('M24_QuickMelee_CurrentGrip_Editable.blend','M24_QuickMelee_FactoryR2_Editable.blend')
exec(compile(code,'native editable export','exec'))
