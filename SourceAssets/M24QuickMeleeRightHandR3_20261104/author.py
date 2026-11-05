"""Right-only stock grip, release and arm support over the saved R2 trajectory."""
from pathlib import Path
exec(compile((Path(__file__).parent/'surface.py').read_text(),'right skin and assembly','exec'))
import copy
grip=json.loads((O/'stock_grip.json').read_text())
r2_grip=json.loads((S/'M24QuickMeleeFactoryR2_20261104/stock_grip.json').read_text())
grip_delta=Matrix(grip['hand'])@Matrix(r2_grip['hand']).inverted()
finger_delta={n:Quaternion(q)@Quaternion(r2_grip['rotations'][n]).inverted() for n,q in grip['rotations'].items()}
OWNED=['clavicle_r',*[n for n in names if under(n,'upperarm_r')],'ik_hand_r']
# Include every 30 Hz base key so inverse-base delta interpolation never
# bridges a change in the base track's interpolation segment.
FPS=240
TIMES=[i/FPS for i in range(217)]
KEYS=(0.,.015,.03,.045,.06,.075,.09,.105,.12,.125,.13333333333333333,.14,.18,.25,.29,.325,.38,.45,.48,.51,.54,.57,.60,.63,.66,.69,.72,.78,.84,.9)
def support_weight(t):return smooth(t/.06)*(1-smooth((t-.70)/.14))
patch={};final={};report={'duration':.9,'contact':.25,'fps':FPS,'owned_bones':OWNED,'profiles':{},'runtime_tested':False,'rendered':False}
for family in D['profiles']:
    if not family.startswith('skeleton_'):continue
    own=entry(family,'quick_melee');idle,_=compose(entry(family,'idle'),0.)
    thumb_idle={n:local(idle,n).to_quaternion() for n in finger_delta if n.startswith('thumb_')}
    kind=next((k for k in ('balanced','phantom','stable') if family.endswith('_'+k)),'Default')
    bv=weapon_tree(kind,'mag10' if 'mag10' in family else 'mag5');cache={}
    def target(t,v):
        if t not in cache:cache[t]=compose(own,t)[0]
        original=cache[t];row=clone(original);w=grip_weight(t)
        held=smooth((t-.10)/.04)*(1-smooth((t-.45)/.06))
        root=original['WPN_root']@rest['WPN_root'].inverted()
        hand=lerp(Matrix.Identity(4),grip_delta,w)@(root.inverted()@original['hand_r'])
        hand=lerp(hand,Matrix(grip['hand']),held)
        rotation=Euler(tuple(math.radians(x) for x in v[3:]),'XYZ').to_quaternion()
        hand=Matrix.LocRotScale(hand.translation+Vector(v[:3])*.001,rotation@hand.to_quaternion(),hand.to_scale())
        row['hand_r']=root@hand
        for n in names:
            if n=='hand_r' or not under(n,'hand_r'):continue
            p,q,s=local(original,n).decompose()
            if n in thumb_idle:
                q=thumb_idle[n].slerp(Quaternion(grip['rotations'][n]),w)
            elif n in finger_delta:q=Quaternion().slerp(finger_delta[n],w)@q
            if n in grip['rotations']:q=q.slerp(Quaternion(grip['rotations'][n]),held)
            row[n]=row[parents[n]]@Matrix.LocRotScale(p,q,s)
        return row
    controls=[]
    for t in KEYS:
        w=grip_weight(t);a=support_weight(t)
        cap=smooth((t-.015)/.03)*(1-smooth((t-.10)/.04))+smooth((t-.45)/.03)*(1-smooth((t-.65)/.05))
        v=[0.]*6;previous=controls[-1]['pole'] if controls else 0.
        def solve(values):
            row=target(t,values);reference=cache[t]
            fitted,info=fit_arm(reference,row,previous,cap=45.*a)
            if fitted is None:return 1e12,info
            score=info['score']*.45+surface_penalty(fitted,bv,True)
            score+=.012*sum(x*x for x in values[:3])+.08*sum(x*x for x in values[3:])
            return score,info
        value,info=solve(v)
        if cap>.001 and 0.02<t<.70:
            for step in (10.,5.,2.,1.):
                for _ in range(2):
                    for axis in range(6):
                        for sign in (-1,1):
                            trial=v.copy();limit=(32. if axis<3 else 24.)*cap
                            trial[axis]=max(-limit,min(limit,trial[axis]+step*sign));cost,detail=solve(trial)
                            if cost<value:v,value,info=trial,cost,detail
        controls.append({'time':t,'v':v,'pole':info.get('pole_degrees',0.),'fit':info})
    print('RIGHT_CONTROLS_READY',family,flush=True)
    tracks={n:[] for n in OWNED};last={};rows=[]
    for t in TIMES:
        i=max(0,min(len(KEYS)-2,bisect.bisect_right(KEYS,t)-1));a,b=controls[i:i+2];mix=smooth((t-a['time'])/(b['time']-a['time']))
        v=[x*(1-mix)+y*mix for x,y in zip(a['v'],b['v'])];phi=a['pole']*(1-mix)+b['pole']*mix
        row=target(t,v);original=cache[t];fitted,info=arm(original,row,phi)
        if fitted is None:raise RuntimeError('Right hand left native reach: '+family+' '+str(t))
        influence=support_weight(t)
        # Ease orientation only. Keep the exact two-bone elbow position so the
        # transition cannot shorten either segment by blending elbow positions.
        for n in OWNED:
            if under(n,'hand_r') or n=='ik_hand_r':continue
            position=fitted[n].translation
            if n not in ('clavicle_r','upperarm_r','lowerarm_r'):
                position=fitted[parents[n]]@local(original,n).translation
            fitted[n]=Matrix.LocRotScale(position,original[n].to_quaternion().slerp(fitted[n].to_quaternion(),influence),original[n].to_scale())
        fitted['hand_r']=row['hand_r'];fitted['ik_hand_r']=row['hand_r'].copy()
        if t==0. or t>=.84:fitted=clone(original)
        rows.append(fitted)
        for n in OWNED:
            p,q,s=(K@local(fitted,n)@K).decompose();bp,bq,bs=raw(D['clips'][own['base']],t,n).decompose();dq=q@bq.inverted();dq.normalize()
            if n in last and dq.dot(last[n])<0:dq.negate()
            last[n]=dq.copy();tracks[n].extend([*(p-bp),dq.x,dq.y,dq.z,dq.w,*(s-bs)])
    replace={n:{'bone':n,'times':TIMES,'values':v} for n,v in tracks.items()}
    clip=copy.deepcopy(own);clip['tracks']=[replace.pop(tr['bone'],tr) for tr in clip['tracks']]+list(replace.values())
    patch[family]=clip;final[family]=rows;report['profiles'][family]={'controls':controls,'keys':len(TIMES)}
    print('RIGHT_HAND_AUTHORED',family,flush=True)
with gzip.open(O/'quick_melee_patch.json.gz','wt',compresslevel=1) as fp:json.dump(patch,fp,separators=(',',':'))
with gzip.open(O/'arm_path_patch.json.gz','wt',compresslevel=1) as fp:json.dump(patch,fp,separators=(',',':'))
code=(S/'M24QuickMeleeGrip20261104/author.py').read_text().split('# Native editable rig plus the current V9 skin and runtime-equivalent JC tracks.')[1]
code=code.replace('M24_QuickMelee_CurrentGrip_Editable.blend','M24_QuickMelee_RightHandR3_Editable.blend')
code=code.replace('s.render.fps = 200','s.render.fps = 240').replace('(len(rows) - 1) / 200','(len(rows) - 1) / 240').replace('s.frame_end=180','s.frame_end=216')
exec(compile(code,'native editable export','exec'))
