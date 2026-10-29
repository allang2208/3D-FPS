"""CC0 combo A/B and an authored single-hand thrust, on both native bodies.

The commercial video is a visual reference only. No commercial motion curves
are used. All final tracks are editable here and in the saved AnimSequences.
"""
import json
from pathlib import Path
import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.spatial.transform import Rotation as R

OUT = Path(__file__).resolve().parent
INPUT = json.loads((OUT/'inputs.json').read_text())
SOURCE = INPUT['source']
SI = {n.lower():i for i,n in enumerate(SOURCE['names'])}
SR = np.asarray(SOURCE['reference_world'])
RATE = 60
LENGTH = 38/30

def unit(v):
    return v/np.maximum(np.linalg.norm(v,axis=-1,keepdims=True),1e-10)

def frame(x,y):
    x=unit(x);y=unit(y-x*np.sum(x*y,axis=-1,keepdims=True))
    return R.from_matrix(np.stack([x,y,np.cross(x,y)],axis=-1))

def align(a,b):
    a=unit(a);b=unit(b)
    q=np.concatenate([np.cross(a,b),1+np.sum(a*b,axis=-1,keepdims=True)],axis=-1)
    opposite=np.linalg.norm(q,axis=-1)<1e-7
    if np.any(opposite):
        axis=np.cross(a[opposite],np.array([0.,0.,1.]))
        use=np.linalg.norm(axis,axis=-1)<1e-6
        axis[use]=np.cross(a[opposite][use],np.array([0.,1.,0.]))
        q[opposite]=np.c_[unit(axis),np.zeros(len(axis))]
    return R.from_quat(unit(q))

def slerp(a,b,t):
    b=np.where(np.sum(a*b,axis=-1,keepdims=True)<0,-b,b)
    angle=np.arccos(np.clip(np.sum(a*b,axis=-1,keepdims=True),-1,1))
    sine=np.sin(angle);safe=np.where(sine<1e-7,1,sine)
    q=np.where(sine<1e-7,a*(1-t)+b*t,(a*np.sin((1-t)*angle)+b*np.sin(t*angle))/safe)
    return unit(q)

def blend(a,b,t):
    f=a*(1-t)+b*t;f[...,3:7]=slerp(a[...,3:7],b[...,3:7],t)
    return f

def ease(x):
    x=np.clip(x,0,1);return x*x*(3-2*x)

def sample(a,t,rate=60):
    p=np.clip(t*rate,0,len(a)-1);i=int(p)
    return blend(a[i],a[min(i+1,len(a)-1)],p-i)

class Body:
    def __init__(self,data):
        self.data=data;self.names=data['names'];self.parents=data['parents']
        self.ix={n:i for i,n in enumerate(self.names)}
        self.ref=np.asarray(data['reference']);self.bind=np.asarray(data['reference_world'])
        self.idle=np.asarray(data['idle']);self.hip=self.ix['pelvis']
        self.tp=self.bind[:,:3];self.tq=self.bind[:,3:7]
        self.scale=np.mean([sum(np.linalg.norm(self.tp[self.ix[b+'_'+s]]-self.tp[self.ix[a+'_'+s]]) for a,b in [('thigh','calf'),('calf','foot')]) /
            sum(np.linalg.norm(SR[SI[b+'_'+s],:3]-SR[SI[a+'_'+s],:3]) for a,b in [('thigh','calf'),('calf','foot')]) for s in 'lr'])
        self.ground_offset=np.mean([self.tp[self.ix['ball_'+s],2]-SR[SI['ball_'+s],2]*self.scale for s in 'lr'])
        self.source_forward=unit(np.mean([SR[SI['ball_'+s],:3]-SR[SI['foot_'+s],:3] for s in 'lr'],axis=0)*[1,1,0])
        self.target_forward=unit(np.mean([self.tp[self.ix['ball_'+s]]-self.tp[self.ix['foot_'+s]] for s in 'lr'],axis=0)*[1,1,0])
        self.corrections={}
        for i,n in enumerate(self.names):
            if n.lower() not in SI or n=='root':continue
            j=SI[n.lower()]
            # Use anatomical axes, not the old rig's different A/T-pose offsets.
            # Source bind faces -Y; its animated take and our bodies face +Y.
            child=self.axis_child(n)
            if n.startswith('hand_'):
                side=n[-1]
                a=frame(SR[SI['middle_01_'+side],:3]-SR[j,:3],SR[SI['index_01_'+side],:3]-SR[SI['pinky_01_'+side],:3])
                b=frame(self.tp[self.ix['middle_01_'+side]]-self.tp[i],self.tp[self.ix['index_01_'+side]]-self.tp[self.ix['pinky_01_'+side]])
            elif child and child in self.ix and child.lower() in SI:
                av=SR[SI[child.lower()],:3]-SR[j,:3];bv=self.tp[self.ix[child]]-self.tp[i]
                sa=self.source_forward;tb=self.target_forward
                if abs(float(unit(av)@sa))>.92:sa=np.array([0.,0.,1.])
                if abs(float(unit(bv)@tb))>.92:tb=np.array([0.,0.,1.])
                a=frame(av,sa);b=frame(bv,tb)
            else:
                a=frame(np.array([0.,0.,1.]),self.source_forward)
                b=frame(np.array([0.,0.,1.]),self.target_forward)
            self.corrections[i]=R.from_quat(SR[j,3:7]).inv()*a*b.inv()*R.from_quat(self.tq[i])
        self.blade_local=self.mount_rotation()

    def axis_child(self,n):
        pairs={'pelvis':'spine_01','spine_01':'spine_02','spine_02':'spine_03','spine_03':'neck_01','neck_01':'head'}
        if n in pairs:return pairs[n]
        for a,b in [('clavicle','upperarm'),('upperarm','lowerarm'),('lowerarm','hand'),('thigh','calf'),('calf','foot'),('foot','ball')]:
            if n in [a+'_l',a+'_r']:return b+n[-2:]
        for a,b in [('_01_','_02_'),('_02_','_03_')]:
            if a in n:return n.replace(a,b)
        if '_03_' in n:return n.replace('_03_','_02_')
        if n in ('ball_l','ball_r'):return 'foot'+n[-2:]
        return None

    def world(self,f):
        one=f.ndim==2
        if one:f=f[None]
        p=f[:,:,:3].copy();q=f[:,:,3:7].copy();s=f[:,:,7:].copy()
        for i,par in enumerate(self.parents):
            if par<0:continue
            p[:,i]=p[:,par]+R.from_quat(q[:,par]).apply(f[:,i,:3]*s[:,par])
            q[:,i]=(R.from_quat(q[:,par])*R.from_quat(q[:,i])).as_quat();s[:,i]*=s[:,par]
        return (p[0],q[0]) if one else (p,q)

    def set_world_rotations(self,f,desired):
        q=[]
        for i,par in enumerate(self.parents):
            parent=R.from_quat(q[par]) if par>=0 else R.identity(len(f))
            local=parent.inv()*desired[i] if i in desired else R.from_quat(f[:,i,3:7])
            f[:,i,3:7]=local.as_quat();q.append((parent*local).as_quat())

    def solve(self,f,chain,goal,pole,end_rotation):
        hidx,kidx,aidx=[self.ix[n] for n in chain]
        p,q=self.world(f);h,k,a=[p[:,j] for j in (hidx,kidx,aidx)]
        l1=np.linalg.norm(k-h,axis=1);l2=np.linalg.norm(a-k,axis=1)
        axis=unit(goal-h);dist=np.clip(np.linalg.norm(goal-h,axis=1),abs(l1-l2)+.02,(l1+l2)*.995)
        bend=pole-h; bend-=axis*np.sum(bend*axis,axis=1)[:,None]
        fallback=np.linalg.norm(bend,axis=1)<1e-6
        bend[fallback]=np.cross(axis[fallback],np.array([1.,0.,0.]))
        bend=unit(bend)
        along=(l1*l1-l2*l2+dist*dist)/(2*dist)
        joint=h+axis*along[:,None]+bend*np.sqrt(np.maximum(0,l1*l1-along*along))[:,None]
        hq=align(k-h,joint-h)*R.from_quat(q[:,hidx])
        kq=align(a-k,h+axis*dist[:,None]-joint)*R.from_quat(q[:,kidx])
        f[:,hidx,3:7]=(R.from_quat(q[:,self.parents[hidx]]).inv()*hq).as_quat()
        f[:,kidx,3:7]=(hq.inv()*kq).as_quat()
        f[:,aidx,3:7]=(kq.inv()*end_rotation).as_quat()

    def retarget(self,world):
        f=np.repeat(self.ref[None],len(world),axis=0)
        desired={i:R.from_quat(world[:,SI[self.names[i].lower()],3:7])*c for i,c in self.corrections.items()}
        self.set_world_rotations(f,desired)
        f[:,self.hip,:3]=world[:,SI['pelvis'],:3]*self.scale
        f[:,self.hip,2]+=self.ground_offset
        targets={s:world[:,SI['foot_'+s],:3]*self.scale+[0,0,self.ground_offset] for s in 'lr'}
        p,q=self.world(f)
        drop=np.zeros(len(f))
        for side in 'lr':
            h,k,a=[p[:,self.ix[n+'_'+side]] for n in ('thigh','calf','foot')]
            reach=(np.linalg.norm(k-h,axis=1)+np.linalg.norm(a-k,axis=1))*.994
            max_z=targets[side][:,2]+np.sqrt(np.maximum(1,reach*reach-np.sum((targets[side][:,:2]-h[:,:2])**2,axis=1)))
            drop=np.maximum(drop,h[:,2]-max_z)
        f[:,self.hip,2]-=drop
        for side in 'lr':
            self.solve(f,[n+'_'+side for n in ('thigh','calf','foot')],targets[side],
                world[:,SI['calf_'+side],:3]*self.scale+[0,0,self.ground_offset],desired[self.ix['foot_'+side]])
        return f

    def mount_rotation(self):
        native=INPUT['native'];ni={n:i for i,n in enumerate(native['names'])};nr=np.asarray(native['reference_world'])
        points=[]
        for refs,idx in [(nr,ni),(self.bind,self.ix)]:
            h=refs[idx['hand_r']]
            points.append([R.from_quat(h[3:7]).inv().apply(refs[idx[d+'_01_r'],:3]-h[:3]) for d in ('index','middle','pinky')])
        a,b=points
        mount=frame(b[1],b[0]-b[2])*frame(a[1],a[0]-a[2]).inv()
        grip=native['grip']
        return mount*R.from_quat(grip['hand_r'][3:7]).inv()*R.from_quat(grip['WPN_root'][3:7])

    def twists(self,f):
        for side in 'lr':
            hand=self.ix['hand_'+side]
            delta=(R.from_quat(f[:,hand,3:7])*R.from_quat(self.ref[hand,3:7]).inv()).as_quat()
            axis=unit(self.ref[hand,:3]);projected=np.sum(delta[:,:3]*axis,axis=1)[:,None]*axis
            twist=unit(np.c_[projected,delta[:,3]])
            twist=np.where(twist[:,3:]<0,-twist,twist)
            for suffix in ('01','02'):
                key='lowerarm_twist_'+suffix+'_'+side
                if key not in self.ix:continue
                i=self.ix[key];weight=np.clip(np.linalg.norm(self.ref[i,:3])/np.linalg.norm(self.ref[hand,:3]),0,1)
                part=slerp(np.tile([0,0,0,1.],(len(f),1)),twist,weight)
                f[:,i,3:7]=(R.from_quat(part)*R.from_quat(self.ref[i,3:7])).as_quat()
        return f

    def thrust(self,start):
        # Author-space +Y is forward, -X is the right side. Root stays fixed.
        # The rear foot gathers, then its heel rises as the hips drive forward.
        times=np.array([0.,.16,.27,.367,.43,.52,.72,.96,LENGTH])
        p0,q0=self.world(start);pi,qi=self.world(self.idle)
        hip0=p0[self.hip];size=self.scale/94.
        hip_loaded=hip0+np.array([0,5,8])*size
        hips=np.array([hip0,hip_loaded,hip_loaded,hip_loaded+[0,9,2],hip_loaded+[0,10,1.5],hip_loaded+[0,7,2],hip_loaded+[0,2,4],pi[self.hip]*.65+hip_loaded*.35,pi[self.hip]])
        loaded_hand=hip_loaded+np.array([-17,16,35])*size
        hit_hand=hip_loaded+np.array([-10,65,47])*size
        right=np.array([p0[self.ix['hand_r']],loaded_hand,loaded_hand+np.array([0,-2,0]),hit_hand,hit_hand+np.array([0,1,-1]),hit_hand+np.array([0,-8,-1]),loaded_hand+np.array([0,5,3]),pi[self.ix['hand_r']]*.65+loaded_hand*.35,pi[self.ix['hand_r']]])
        guard=hip_loaded+np.array([23,27,54])*size
        left=np.array([p0[self.ix['hand_l']],guard,guard,guard+[0,3,0],guard+[0,3,0],guard+[0,1,0],guard+[0,0,1],pi[self.ix['hand_l']]*.65+guard*.35,pi[self.ix['hand_l']]])
        # A true forward blade direction is authored from the real palm mount.
        blade_hit=frame(np.array([0.,0.,-1.]),np.array([-1.,0.,0.]))
        blade_load=R.from_euler('x',-12,degrees=True)*blade_hit
        hand_hit=(blade_hit*self.blade_local.inv()).as_quat();hand_load=(blade_load*self.blade_local.inv()).as_quat()
        keys=[]
        for k,t in enumerate(times):
            f=start.copy() if k<7 else blend(start,self.idle,.65 if k==7 else 1.)
            if k in range(1,7):
                desired={}
                yaw=[0,14,16,-4,-5,-2,9][k]
                for n,pitch in [('pelvis',-6),('spine_01',-9),('spine_02',-12),('spine_03',-14),('neck_01',-7),('head',-3)]:
                    j=self.ix[n]
                    desired[j]=R.from_euler('xyz',[pitch,0,yaw if n not in ('head','neck_01') else 0],degrees=True)*R.from_quat(self.tq[j])
                one=f[None].copy();self.set_world_rotations(one,{i:R.from_quat(v.as_quat()[None]) for i,v in desired.items()});f=one[0]
            keys.append(f)
        keys=np.asarray(keys)
        feet={};footq={}
        for side in 'lr':
            j=self.ix['foot_'+side];base=p0[j].copy()
            if side=='l':
                gather=base+np.array([0,17,0])*size
                feet[side]=np.array([base,(base+gather)/2+[0,0,6],gather,gather+[0,0,5],gather+[0,0,5],gather+[0,0,2],gather,(gather+pi[j])/2+[0,0,7],pi[j]])
                lifted=(R.from_euler('x',-13,degrees=True)*R.from_quat(q0[j])).as_quat()
                footq[side]=np.array([q0[j],q0[j],q0[j],lifted,lifted,q0[j],q0[j],qi[j],qi[j]])
            else:
                feet[side]=np.array([base,base,base,base,base,base,base,(base+pi[j])/2+[0,0,5],pi[j]])
                footq[side]=np.array([q0[j]]*7+[qi[j],qi[j]])
        ts=np.arange(round(LENGTH*RATE)+1)/RATE
        frames=[];qright=[];qleft=[];qfeet={s:[] for s in 'lr'}
        for t in ts:
            k=min(np.searchsorted(times,t,side='right')-1,len(times)-2);k=max(0,k)
            x=ease((t-times[k])/(times[k+1]-times[k]))
            frames.append(blend(keys[k],keys[k+1],x))
            rq=np.array([q0[self.ix['hand_r']],hand_load,hand_load,hand_hit,hand_hit,hand_hit,hand_load,qi[self.ix['hand_r']],qi[self.ix['hand_r']]])
            qright.append(slerp(rq[k],rq[k+1],x))
            # The support hand is free; the existing native idle supplies its guard rotation.
            lq=np.array([q0[self.ix['hand_l']]]+[qi[self.ix['hand_l']]]*8)
            qleft.append(slerp(lq[k],lq[k+1],x))
            for side in 'lr':qfeet[side].append(slerp(footq[side][k],footq[side][k+1],x))
        f=np.asarray(frames);f[:,self.hip,:3]=PchipInterpolator(times,hips)(ts)
        for side in 'lr':
            goals=PchipInterpolator(times,feet[side])(ts)
            pole_keys=hips+np.array([-23 if side=='r' else 23,45,-30])*size
            pole_keys[0]=p0[self.ix['calf_'+side]];pole_keys[-1]=pi[self.ix['calf_'+side]]
            pole_keys[-2]=pole_keys[-2]*.35+pole_keys[-1]*.65
            poles=PchipInterpolator(times,pole_keys)(ts)
            self.solve(f,[n+'_'+side for n in ('thigh','calf','foot')],goals,poles,R.from_quat(qfeet[side]))
        for side,goals,rot in [('r',right,qright),('l',left,qleft)]:
            goal=PchipInterpolator(times,goals)(ts)
            pole_keys=hips+np.array([-40 if side=='r' else 40,10,25])*size
            pole_keys[0]=p0[self.ix['lowerarm_'+side]];pole_keys[-1]=pi[self.ix['lowerarm_'+side]]
            pole_keys[-2]=pole_keys[-2]*.35+pole_keys[-1]*.65
            poles=PchipInterpolator(times,pole_keys)(ts)
            self.solve(f,[n+'_'+side for n in ('upperarm','lowerarm','hand')],goal,poles,R.from_quat(rot))
        # Boundary frames are exact; transition/recovery does not introduce an idle reset.
        f[0]=start;f[-1]=self.idle
        return f

def make_body(label,data):
    body=Body(data)
    combo=body.retarget(np.asarray(SOURCE['clips']['Sword_Regular_Combo']['frames']))
    times=np.arange(round(LENGTH*RATE)+1)/RATE
    # Preserve A -> B boundary from one continuous take. First two hit moments
    # remain on the existing gameplay clock; recovery retains the loaded stance.
    maps={
        'Slash1':([0,.14,.26,.357,.45,.72,LENGTH],[0,.10,.19,.265,.32,.40,28/60]),
        'Slash2':([0,.16,.29,.380,.47,.74,LENGTH],[28/60,.55,.63,.695,.75,.90,1.0])}
    clips={}
    for role,(clock,source) in maps.items():
        remap=PchipInterpolator(clock,source)
        f=np.array([sample(combo,float(remap(t))) for t in times])
        if role=='Slash1':
            for i,t in enumerate(times):
                if t<.14:f[i]=blend(body.idle,f[i],ease(t/.14))
        hit=.357 if role=='Slash1' else .380
        release=.45 if role=='Slash1' else .47
        clips[role]=dict(frames=f,contact=hit/LENGTH,release=release/LENGTH,
            source=SOURCE['clips']['Sword_Regular_Combo']['asset'],source_range=[source[0],source[-1]],
            adaptation='Original CC0 full-body take; anatomical axes and planted ankle fit; continuous loaded endpoint; existing hit clock.')
    clips['Thrust']=dict(frames=body.thrust(clips['Slash2']['frames'][-1]),contact=.367/LENGTH,release=.47/LENGTH,
        source='Authored in ComboV3/author.py; public Front_Thrust_Middle video is visual reference only',source_range=[0,LENGTH],
        adaptation='Single-hand middle thrust from Combo B low stance; rear-foot gather, heel lift, hip drive, free left guard; no commercial curves.')
    for role,donor,start in [('Recover1','Sword_Regular_A_Rec',clips['Slash1']['frames'][-1]),('Recover2','Sword_Regular_B_Rec',clips['Slash2']['frames'][-1])]:
        raw=body.retarget(np.asarray(SOURCE['clips'][donor]['frames']))
        duration=.5
        frames=[]
        for t in np.linspace(0,1,31):
            f=sample(raw,t*(len(raw)-1)/RATE)
            f=blend(start,f,ease(t/.22))
            f=blend(f,body.idle,ease((t-.62)/.38))
            frames.append(f)
        clips[role]=dict(frames=np.asarray(frames),contact=.4,release=.7,source=SOURCE['clips'][donor]['asset'],source_range=[0,SOURCE['clips'][donor]['duration']],
            adaptation='Only played when the chain stops; source recovery into the current native idle.')
    for c in clips.values():
        c['frames']=body.twists(c['frames']).tolist();c['rate']=RATE;c['source_group']='CC0 Quaternius UAL2 + original authored thrust';c['loop']=False
    result=dict(mesh=data['mesh'],names=data['names'],parents=data['parents'],clips=clips)
    (OUT/(label+'-actions.json')).write_text(json.dumps(result,separators=(',',':')))
    return dict(mesh=data['mesh'],skeleton=data['skeleton'],scale_cm_per_source_unit=float(body.scale),clips={k:dict(frames=len(c['frames']),seconds=(len(c['frames'])-1)/RATE,source=c['source'],source_range=c['source_range']) for k,c in clips.items()})

if __name__=='__main__':
    receipt={'runtime_tested':False,'rendered':False,'commercial_asset_used':False,'bodies':{}}
    for label,data in INPUT['targets'].items():
        receipt['bodies'][label]=make_body(label,data)
        print('KUKRI_COMBO_AUTHORED '+label,flush=True)
    (OUT/'authoring.json').write_text(json.dumps(receipt,indent=2))
