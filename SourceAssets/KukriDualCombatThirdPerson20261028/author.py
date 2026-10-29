"""Dual combat on native bodies, driven by the actual FPS dual arm trajectories.

Camera-space reach is refitted to native shoulders, elbow hinges and fixed
weapon mounts. The saved full-body takes supply the supported lower body.
No source assets, first-person clips or gameplay timings are modified.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import numpy as np
from scipy.ndimage import gaussian_filter1d
from scipy.spatial.transform import Rotation as R

OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1]
spec=importlib.util.spec_from_file_location('dual_combat_carry',ROOT/'SourceAssets/KukriDualIdleThirdPerson20261027/author.py')
carry=importlib.util.module_from_spec(spec);spec.loader.exec_module(carry)
base,c=carry.base,carry.c
RATE=120
FPS_DIR=ROOT/'SourceAssets/DualKukriIdle20261025/Clips'
ROLES=dict(Slash1='DualAttack',Slash2='DualAttack2',Thrust='DualAttack3',Charge='DualHeavyCharge',Heavy='DualHeavyRelease')
# Viewmodel +X right / -Y forward -> native body -X right / +Y forward.
TO_BODY=R.from_euler('z',180.,degrees=True)

def phase(t,a,b):return c.ease((t-a)/(b-a))

def fps_source(name):
    raw=(FPS_DIR/(name+'.json')).read_bytes();data=json.loads(raw)
    dump=json.loads((ROOT/'SourceAssets/Kukri20261020/Work/ue_sword_dump.json').read_text())
    names=data['bones'];ix={n:i for i,n in enumerate(names)};parent=dict(zip(dump['names'],dump['parents']))
    rows=data['frames'];n=len(rows)
    p=np.array([[f[b][0] for b in names] for f in rows]);q=np.array([[f[b][1] for b in names] for f in rows])[:,:,[1,2,3,0]]
    scale=np.array([[f[b][2] for b in names] for f in rows])
    for i,b in enumerate(names):
        par=parent[b]
        if par is None:continue
        j=ix[par];pq=R.from_quat(q[:,j])
        p[:,i]=p[:,j]+pq.apply(p[:,i]*scale[:,j]);q[:,i]=(pq*R.from_quat(q[:,i])).as_quat();scale[:,i]*=scale[:,j]
    left=json.loads((FPS_DIR.parent/'left_kukri.json').read_text())['rel_to_hand_l']['rotation_wxyz']
    blades={'r':R.from_quat(q[:,ix['WPN_root']]),'l':R.from_quat(q[:,ix['hand_l']])*R.from_quat(np.array(left)[[1,2,3,0]])}
    return dict(data=data,p=p,q=q,ix=ix,blades=blades,sha256=hashlib.sha256(raw).hexdigest())

def support(body,source,role,t):
    take=source['clips'][role];frames=np.asarray(take['frames']);length=take['duration'];end=t[-1]
    if role.startswith('Slash'):
        hit=.357 if role=='Slash1' else .380
        source_hit=take['markers'].get('Contact',length*.30)
        source_end=take['markers'].get('Release',length*.50)
        st=np.interp(t,[0.,hit,.47,.99,end],[0.,source_hit,source_end,length*.83,length])
    elif role=='Thrust':
        st=np.interp(t,[0.,.60,.72,end],[0.,take['markers'].get('Contact',length*.3),take['markers'].get('Release',length*.5),length])
    else:st=t/end*length
    f=np.array([c.sample(frames,x,take['rate']) for x in st])
    # Match the existing dual carry at both boundaries. Heavy starts at the
    # charge endpoint and is handled together with that take below.
    weight=(np.ones(len(t)) if role=='Heavy' else phase(t,0.,.14))
    if role!='Charge':weight*=1.-phase(t,end-.30,end)
    f=c.blend(np.repeat(body.idle[None],len(t),axis=0),f,weight[:,None,None])
    if role.startswith('Slash'):
        # A modest counter-turn carries the second, offhand contact. Feet and
        # pelvis remain the donor support rather than mirrored local bones.
        second=(phase(t,.49,.73)*(1.-phase(t,1.04,end-.15)))
        for bone,amount in [('spine_01',4.),('spine_03',6.),('spine_05',5.)]:
            i=body.ix[bone];p,q=body.world(f)
            body.set_world_rotations(f,{i:R.from_euler('z',(amount*second)[:,None],degrees=True)*R.from_quat(q[:,i])})
    return f

def solve(body,side,origin,goal,bend,beta,bank,ip,iq):
    ui,ei,hi=[body.ix[n+'_'+side] for n in ('upperarm','lowerarm','hand')]
    u0,v0=ip[ei]-ip[ui],ip[hi]-ip[ei];l1,l2=np.linalg.norm(u0),np.linalg.norm(v0)
    axis=c.unit(goal-origin);d=np.linalg.norm(goal-origin,axis=-1)
    a=(l1*l1-l2*l2+d*d)/(2.*d)
    b=R.from_rotvec(axis*beta[...,None]).apply(bend)
    elbow=origin+axis*a[...,None]+b*np.sqrt(np.maximum(0.,l1*l1-a*a))[...,None]
    u,v=elbow-origin,goal-elbow
    upper=c.frame(u,v)*c.frame(u0,v0).inv()*R.from_quat(iq[ui])
    fore=R.from_rotvec(c.unit(v)*bank[...,None])*c.frame(v,u)*c.frame(v0,u0).inv()*R.from_quat(iq[ei])
    return elbow,upper,fore

def fit_arm(body,f,side,fp,t,weight):
    idle=body.idle;ip,iq=body.world(idle);p,q=body.world(f);n=len(f)
    chest=body.ix['spine_05'];ci=body.ix['clavicle_'+side]
    ui,ei,hi=[body.ix[k+'_'+side] for k in ('upperarm','lowerarm','hand')]
    torso=R.from_quat(q[:,chest])*R.from_quat(body.tq[chest]).inv()
    rest_torso=R.from_quat(iq[chest])*R.from_quat(body.tq[chest]).inv()
    sx=fp['ix'];sp=fp['p'];su,se,sh=[sx[k+'_'+side] for k in ('upperarm','lowerarm','hand')]
    length=np.linalg.norm(ip[ei]-ip[ui])+np.linalg.norm(ip[hi]-ip[ei])
    source_length=np.linalg.norm(sp[0,se]-sp[0,su])+np.linalg.norm(sp[0,sh]-sp[0,se])
    local=TO_BODY.apply(sp[:,sh]-sp[:,su])*length/source_length
    local0=rest_torso.inv().apply(ip[hi]-ip[ui]);sign=1. if side=='l' else -1.
    # Keep the low return outside the flank, and high windup forward of the
    # face. Full-body clothing and head exist outside the FPS camera crop.
    low=1.-phase(local[:,2],-.55*length,-.22*length)
    local[:,0]=local[:,0]*(1.-.55*low)+sign*.27*length*.55*low
    local[:,1]=np.maximum(local[:,1],.18*length+.12*length*phase(local[:,2],-.15*length,.25*length))
    local*=np.minimum(1.,.94*length/np.maximum(np.linalg.norm(local,axis=1),1e-8))[:,None]
    local=local0+(local-local0)*weight[:,None]
    # Scapula follows the arm lift, without moving the clavicle out of its socket.
    raised=phase(local[:,2],-.2*length,.4*length)*weight
    scap=R.from_euler('y',(-sign*8.*raised)[:,None],degrees=True)
    body.set_world_rotations(f,{ci:torso*scap*rest_torso.inv()*R.from_quat(iq[ci])})
    p,q=body.world(f);origin=p[:,ui];goal=origin+torso.apply(local);axis=c.unit(goal-origin)
    rest_axis=c.unit(torso.apply(np.tile(rest_torso.inv().apply(ip[hi]-ip[ui]),(n,1))))
    rest_pole=torso.apply(np.tile(rest_torso.inv().apply(ip[ei]-ip[ui]),(n,1)))
    rest_bend=c.unit(rest_pole-rest_axis*np.sum(rest_pole*rest_axis,axis=1)[:,None])
    seed=c.align(rest_axis,axis).apply(rest_bend)
    pole=torso.apply(TO_BODY.apply(sp[:,se]-sp[:,su]))
    wanted=c.unit(pole-axis*np.sum(pole*axis,axis=1)[:,None])
    swivel=np.unwrap(np.arctan2(np.sum(axis*np.cross(seed,wanted),axis=1),np.sum(seed*wanted,axis=1)))
    swivel=np.clip(swivel,-np.radians(65.),np.radians(65.))*weight
    bend=R.from_rotvec(axis*swivel[:,None]).apply(seed)
    mount=carry.dual.v1.left_grip(body)[2] if side=='l' else base.native.blade_mount(body)[1]
    guided=torso*TO_BODY*fp['blades'][side]*mount.inv()
    neutral=torso*rest_torso.inv()*R.from_quat(iq[hi])
    desired=R.from_quat(c.slerp(neutral.as_quat(),guided.as_quat(),weight[:,None]))
    beta,bank=np.meshgrid(np.radians(np.arange(-40.,41.,10.)),np.radians(np.arange(-100.,101.,10.)),indexing='ij')
    choices=np.c_[beta.ravel(),bank.ravel()];count=len(choices);cost=np.empty((n,count))
    wrist=R.from_quat(idle[hi,3:7]);head=p[:,body.ix['head']]+torso.apply(np.tile([0.,0.,7.],(n,1)))
    size=length/60.
    for k in range(n):
        a=np.repeat(origin[k][None],count,axis=0);g=np.repeat(goal[k][None],count,axis=0);b=np.repeat(bend[k][None],count,axis=0)
        e,_,fore=solve(body,side,a,g,b,choices[:,0]*weight[k],choices[:,1]*weight[k],ip,iq)
        residual=((fore*wrist).inv()*desired[k]).magnitude()
        el=torso[k].inv().apply(e-a);inward=np.maximum(0.,-sign*el[:,0]-3.*size)/(10.*size)
        clearance=np.zeros(count)
        for start,end in [(a,e),(e,g)]:
            for fract in (.3,.6,.9):
                point=start+(end-start)*fract
                hd=np.linalg.norm((point-head[k])/(np.array([14.,15.,17.])*size),axis=1)
                clearance+=np.maximum(0.,1.-hd)**2
                rel=torso[k].inv().apply(point-p[k,chest])
                torso_d=np.sqrt((rel[:,0]/(18.*size))**2+(rel[:,1]/(14.*size))**2)
                clearance+=np.maximum(0.,1.-torso_d)**2*((rel[:,2]<0.)&(rel[:,2]>-42.*size))
                if side=='l':
                    # The primary arm is already authored: keep the offhand
                    # elbow/forearm on a separate crossing depth.
                    for rbone in ('lowerarm_r','hand_r'):
                        distance=np.linalg.norm(point-p[k,body.ix[rbone]],axis=1)
                        clearance+=np.maximum(0.,1.-distance/(10.*size))**2
        cost[k]=7.*residual**2+.15*choices[:,0]**2+.035*choices[:,1]**2+3.*inward**2+18.*clearance
    difference=choices[:,None]-choices[None];transition=.7*np.sum(difference*difference,axis=2)
    transition[np.max(np.abs(difference),axis=2)>np.radians(10.1)]=np.inf
    back=np.zeros((n,count),dtype=np.int32);score=cost[0].copy()
    for k in range(1,n):
        values=score[:,None]+transition;back[k]=np.argmin(values,axis=0);score=cost[k]+values[back[k],np.arange(count)]
    route=np.empty(n,dtype=np.int32);route[-1]=int(np.argmin(score))
    for k in range(n-1,0,-1):route[k-1]=back[k,route[k]]
    angles=gaussian_filter1d(choices[route],1.2,axis=0,mode='nearest')*weight[:,None]
    _,upper,fore=solve(body,side,origin,goal,bend,angles[:,0],angles[:,1],ip,iq)
    relative=(fore.inv()*desired*wrist.inv()).as_quat();longitudinal=c.unit(body.ref[hi,:3])
    twist=c.unit(np.c_[(relative[:,:3]@longitudinal)[:,None]*longitudinal,relative[:,3]])
    angle=np.unwrap(2.*np.arctan2(twist[:,:3]@longitudinal,twist[:,3]));angle-=2.*np.pi*round(float(angle[0])/(2.*np.pi))
    tw=R.from_rotvec(longitudinal[None]*(np.radians(28.)*np.tanh(angle/np.radians(28.))*weight)[:,None])
    swing=(R.from_quat(relative)*R.from_quat(twist).inv()).as_rotvec();amount=np.linalg.norm(swing,axis=1);limit=np.radians(32.)
    sw=R.from_rotvec(swing*(limit*np.tanh(amount/limit)/np.maximum(amount,1e-9)*weight)[:,None])
    body.set_world_rotations(f,{ui:upper,ei:fore,hi:fore*sw*tw*wrist})
    for i,name in enumerate(body.names):
        if name.endswith('_'+side) and name.startswith(('thumb_','index_','middle_','ring_','pinky_')):f[:,i]=idle[i]

def helpers(body,f):
    derived=f.copy();base.native.native_twists(body,derived)
    seed=body.idle[None].copy();base.native.native_twists(body,seed)
    for i,name in enumerate(body.names):
        if name.startswith(('upperarm_twist_','lowerarm_twist_')):
            offset=R.from_quat(body.idle[i,3:7])*R.from_quat(seed[0,i,3:7]).inv()
            f[:,i,3:7]=(offset*R.from_quat(derived[:,i,3:7])).as_quat()

def main():
    inputs=json.loads((OUT/'inputs.json').read_text());fps={r:fps_source(n) for r,n in ROLES.items()}
    report=dict(version='Dual combat native offhand V1',bodies={},runtime_tested=False,rendered=False,first_person_changed=False,
        fps_sources={r:dict(name=ROLES[r],sha256=v['sha256'],duration=v['data']['length'],contact=v['data'].get('contact')) for r,v in fps.items()})
    for label,source in inputs.items():
        body=c.Body(source['native']);idle_loop=np.asarray(source['clips']['Dual.Idle']['frames']);body.idle=idle_loop[0].copy()
        clips={};motion={}
        for role,fp in fps.items():
            t=np.arange(len(fp['p']))/RATE;f=support(body,source,role,t)
            weight=np.ones(len(t)) if role=='Heavy' else phase(t,0.,.16)
            if role!='Charge':weight*=1.-phase(t,t[-1]-.30,t[-1])
            for side in ('r','l'):fit_arm(body,f,side,fp,t,weight)
            helpers(body,f)
            if role!='Heavy':f[0]=body.idle
            if role!='Charge':f[-1]=body.idle
            # The charge and release share the exact loaded boundary. Fade
            # its tiny solver difference before contact, never through impact.
            if role=='Heavy':
                delta=motion['Charge'][-1];blend=1.-phase(t,0.,.025)
                f=c.blend(f,np.repeat(delta[None],len(f),axis=0),blend[:,None,None])
            motion[role]=f
            contact={'Slash1':.357,'Slash2':.380,'Thrust':.60,'Charge':0.,'Heavy':.083}[role]
            release=(fp['data'].get('contact') or [0.,t[-1]*.999])[-1]
            clips['Dual.'+role]=dict(rate_num=RATE,rate_den=1,frames=carry.continuous(f).tolist(),
                contact=contact/t[-1],release=release/t[-1],offhand_contact=(fp['data'].get('contact') or [])[2:],
                source=str(FPS_DIR/(ROLES[role]+'.json')),support_source=source['clips'][role]['asset'],
                adaptation='FPS dual contact clock; native shoulder/elbow solve, fixed grip, limited wrist and distributed forearm twist')
            print('DUAL_COMBAT_AUTHORED',label,role,len(f),flush=True)
        for role in ('Recover1','Recover2'):
            f=np.array([c.sample(idle_loop,t,source['clips']['Dual.Idle']['rate']) for t in np.arange(61)/RATE])
            f[0]=body.idle
            clips['Dual.'+role]=dict(rate_num=RATE,rate_den=1,frames=carry.continuous(f).tolist(),contact=0.,release=.999,
                source=source['clips']['Dual.Idle']['asset'],adaptation='Matched dual carry after the complete FPS attack return')
        output=dict(mesh=source['native']['mesh'],names=body.names,parents=body.parents,clips=clips)
        (OUT/(label+'-actions.json')).write_text(json.dumps(output,separators=(',',':')))
        report['bodies'][label]=dict(previous_roles={'Dual.'+r:v for r,v in source['previous_roles'].items()},source_idle=source['clips']['Dual.Idle']['asset'])
    (OUT/'authoring.json').write_text(json.dumps(report,indent=2))

if __name__=='__main__':main()
