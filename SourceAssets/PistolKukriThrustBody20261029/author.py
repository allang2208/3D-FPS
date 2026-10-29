"""Native full-arm thrust, contact-aligned to the accepted FPS knife action.

The donor supplies body-space shoulder/elbow/reach; FPS supplies timing and
reverse-grip palm orientation only. Never transfer camera-space wrist points.
"""
import importlib.util,json,re
from pathlib import Path
import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.ndimage import gaussian_filter1d
from scipy.spatial.transform import Rotation as R
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1]
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
carry=module('knife_carry','SourceAssets/PistolKukriBody20261025/author.py')
dual=module('knife_solver','SourceAssets/KukriDualCombatThirdPerson20261028/author.py')
c=carry.c;native=carry.q
LENGTH=.633;RATE=120;T=np.linspace(0,LENGTH,77)
M=np.diag([-1.,1.,1.]);C=R.from_euler('z',90,degrees=True)
def curve(times,values):return PchipInterpolator(times,values)(T)
W=curve([0,.08,.16,.25,.30,.43,LENGTH],[0,.35,1,1,1,.60,0])
G=curve([0,.08,.16,.25,.30,.44,LENGTH],[0,.65,1,1,.9,.55,0])
def solve_arm(body,f,side,goal,pole,hand,weight):
    ip,iq=body.world(body.idle);p,q=body.world(f)
    ui,ei,hi=[body.ix[n+'_'+side] for n in ('upperarm','lowerarm','hand')]
    origin=p[:,ui];length=np.linalg.norm(body.ref[ei,:3])+np.linalg.norm(body.ref[hi,:3])
    delta=goal-origin;goal=origin+delta*np.minimum(1.,.94*length/np.maximum(np.linalg.norm(delta,axis=1),1e-8))[:,None]
    axis=c.unit(goal-origin);bend=c.unit(pole-origin-axis*np.sum((pole-origin)*axis,axis=1)[:,None])
    beta,bank=np.meshgrid(np.radians(np.arange(-40.,41.,10.)),np.radians(np.arange(-100.,101.,10.)),indexing='ij')
    choices=np.c_[beta.ravel(),bank.ravel()];count=len(choices);cost=[];wrist=R.from_quat(body.idle[hi,3:7])
    for k in range(len(T)):
        e,u,fore=dual.solve(body,side,np.repeat(origin[k][None],count,axis=0),np.repeat(goal[k][None],count,axis=0),
            np.repeat(bend[k][None],count,axis=0),choices[:,0]*weight[k],choices[:,1]*weight[k],ip,iq)
        residual=((fore*wrist).inv()*hand[k]).magnitude()
        sign=1 if side=='l' else -1
        cost.append(9*residual**2+.2*choices[:,0]**2+.04*choices[:,1]**2+
            3*np.maximum(0.,-sign*(e[:,0]-origin[k,0])/10.)**2)
    cost=np.array(cost);dif=choices[:,None]-choices[None];trans=.8*np.sum(dif*dif,axis=2)
    trans[np.max(abs(dif),axis=2)>np.radians(10.1)]=np.inf
    back=np.zeros((len(T),count),int);score=cost[0]
    for k in range(1,len(T)):
        values=score[:,None]+trans;back[k]=values.argmin(0);score=cost[k]+values[back[k],np.arange(count)]
    route=np.zeros(len(T),int);route[-1]=score.argmin()
    for k in range(len(T)-1,0,-1):route[k-1]=back[k,route[k]]
    angles=gaussian_filter1d(choices[route],1.3,axis=0)*weight[:,None]
    _,upper,fore=dual.solve(body,side,origin,goal,bend,angles[:,0],angles[:,1],ip,iq)
    body.set_world_rotations(f,{ui:upper,ei:fore,hi:hand})

def main():
    data=json.loads((OUT/'inputs.json').read_text());report={'bodies':{},'runtime_tested':False,'rendered':False}
    text=(ROOT/'Source/FPSGAME/Weapons/Kukri/OffhandKukriAuthoredStrike.h').read_text()
    keys=re.findall(r'\{([\d.]+)f,FVector\([^)]*\),FQuat\(([^)]*)\)',text)
    kt=np.array([float(t) for t,_ in keys]);kq=np.array([[float(v) for v in q.split(',')] for _,q in keys])
    from scipy.spatial.transform import Slerp
    fp_hand=Slerp(kt,R.from_quat(kq))(T)
    for label,d in data.items():
        body=c.Body(d);body.idle=np.array(d['idle']);ip,iq=body.world(body.idle)
        donor=d['clips']['Thrust'];sf=np.array(donor['frames']);sp,sq=body.world(sf)
        u,e,h=[body.ix[n+'_r'] for n in ('upperarm','lowerarm','hand')]
        source_contact=float(np.argmax((sp[:,h]-sp[:,u])[:,1])/donor['rate'])
        source_contact=np.clip(source_contact,.15,donor['duration']-.15)
        clock=PchipInterpolator([0,.16,.25,.32,LENGTH],[0,source_contact*.62,source_contact,
            source_contact+.15*(donor['duration']-source_contact),donor['duration']])(T)
        sample=np.array([c.sample(sf,t,donor['rate']) for t in clock]);dp,dq=body.world(sample)
        f=np.repeat(body.idle[None],len(T),axis=0)
        # Donor torso weight transfer, mirrored toward the left blade; lower
        # body remains available to the native locomotion layer at runtime.
        for name in ('spine_01','spine_02','spine_03','spine_04','spine_05'):
            if name not in body.ix:continue
            i=body.ix[name];delta=R.from_quat(sample[:,i,3:7])*R.from_quat(sf[0,i,3:7]).inv()
            mirrored=R.from_matrix(M@delta.as_matrix()@M)
            f[:,i,3:7]=(R.from_rotvec(mirrored.as_rotvec()*(.28*W)[:,None])*R.from_quat(body.idle[i,3:7])).as_quat()
        p,q=body.world(f);chest=body.ix['spine_03'];torso=R.from_quat(q[:,chest])*R.from_quat(iq[chest]).inv()
        scale=(np.linalg.norm(body.ref[body.ix['lowerarm_l'],:3])+np.linalg.norm(body.ref[body.ix['hand_l'],:3]))/60.
        for side in ('r','l'):
            ui,ei,hi=[body.ix[n+'_'+side] for n in ('upperarm','lowerarm','hand')]
            rest_hand=torso*R.from_quat(iq[hi]);origin=p[:,ui]
            rest_reach=torso.apply(np.tile(ip[hi]-ip[ui],(len(T),1)))
            rest_pole=torso.apply(np.tile(ip[ei]-ip[ui],(len(T),1)))
            if side=='r':
                # Gun remains on its own grip, aimed forward while making room
                # beside the blade. No FPS camera crop/large downward gun roll.
                goal=origin+rest_reach+torso.apply(G[:,None]*np.array([-11.,-8.,-9.])*scale)
                pole=origin+rest_pole+torso.apply(G[:,None]*np.array([-7.,0.,-4.])*scale)
                hand=rest_hand;weight=G
            else:
                source_torso=R.from_quat(dq[:,chest])*R.from_quat(body.tq[chest]).inv()
                reach=source_torso.inv().apply(dp[:,h]-dp[:,u])@M
                elbow=source_torso.inv().apply(dp[:,e]-dp[:,u])@M
                # Native shoulder-relative donor reach, with a small lateral
                # blade lane. Scale/cap by native bone length, not camera height.
                reach[:,0]+=5.*scale
                goal=origin+rest_reach*(1-W[:,None])+torso.apply(reach)*W[:,None]
                pole=origin+rest_pole*(1-W[:,None])+torso.apply(elbow)*W[:,None]
                mount,_=carry.palm_mount(body,'l')
                desired=torso*C*fp_hand*mount.inv()
                hand=R.from_quat(c.slerp(rest_hand.as_quat(),desired.as_quat(),W[:,None]));weight=W
            solve_arm(body,f,side,goal,pole,hand,weight)
        # Helpers are derived together from the final complete arm and carry
        # their accepted baseline offset; don't zero twist/corrective tracks.
        derived=f.copy();native.native_twists(body,derived)
        seed=body.idle[None].copy();native.native_twists(body,seed)
        for i,name in enumerate(body.names):
            if name.startswith(('upperarm_twist_','lowerarm_twist_')):
                f[:,i,3:7]=(R.from_quat(body.idle[i,3:7])*R.from_quat(seed[0,i,3:7]).inv()*R.from_quat(derived[:,i,3:7])).as_quat()
        f=c.blend(np.repeat(body.idle[None],len(T),axis=0),f,c.ease(T/.06)[:,None,None])
        f=c.blend(f,np.repeat(body.idle[None],len(T),axis=0),c.ease((T-.46)/(LENGTH-.46))[:,None,None])
        f[0]=body.idle;f[-1]=body.idle
        for k in range(1,len(f)):
            flip=np.sum(f[k-1,:,3:7]*f[k,:,3:7],axis=1)<0;f[k,flip,3:7]*=-1
        out=dict(mesh=d['mesh'],names=body.names,parents=body.parents,clips={'Thrust':dict(rate_num=120,rate_den=1,
            frames=f.tolist(),source=donor['asset'],adaptation='Native mirrored donor shoulder/elbow/reach; FPS palm and 0.250/0.633 s clock; independent forward pistol grip; native helpers')})
        (OUT/(label+'-actions.json')).write_text(json.dumps(out,separators=(',',':')))
        wp,wq=body.world(f)
        report['bodies'][label]=dict(mesh=d['mesh'],source_contact=float(source_contact),length=LENGTH,contact=.25,
            right_palm_drift_degrees=float(np.max((R.from_quat(wq[:,body.ix['hand_r']])*R.from_quat(iq[body.ix['hand_r']]).inv()).magnitude())*180/np.pi),
            frames=len(f),source=donor['asset'])
        print('PISTOL_KUKRI_THRUST_AUTHORED',label,flush=True)
    (OUT/'authoring.json').write_text(json.dumps(report,indent=2))
if __name__=='__main__':main()
