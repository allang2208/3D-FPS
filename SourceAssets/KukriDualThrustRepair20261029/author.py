"""Dual thrust repair on native body chains; gameplay contact clock stays fixed."""
import importlib.util,json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R
from scipy.interpolate import PchipInterpolator
from scipy.ndimage import gaussian_filter1d
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1]
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
previous=module('completion_reference','SourceAssets/KukriThirdPersonCompletion20261029/author.py')
old,c=previous.old,previous.c
RATE=120
ROLE='Kukri.FullBody.Dual.Thrust'
def body_for(label,source):
    b=c.Body(old.base.rig.DATA[label]);b.idle=np.array(source['clips']['Kukri.FullBody.Dual.Idle']['frames'])[0].copy();return b
def metrics(b,f,rate=120):
    p,q=b.world(f);result={}
    for side in 'rl':
        u,e,h=[b.ix[k+'_'+side] for k in ('upperarm','lowerarm','hand')]
        upper=p[:,e]-p[:,u];fore=p[:,h]-p[:,e]
        palm=(R.from_quat(q[:,h])*R.from_quat(b.ref[h,3:7]).inv()).apply(np.tile(c.unit(b.ref[h,:3]),(len(f),1)))
        bend=np.degrees(np.arccos(np.clip(np.sum(c.unit(fore)*palm,axis=1),-1,1)))
        elbow=np.degrees(np.arccos(np.clip(np.sum(c.unit(upper)*c.unit(fore),axis=1),-1,1)))
        reach=np.linalg.norm(p[:,h]-p[:,u],axis=1)/(np.linalg.norm(upper,axis=1)+np.linalg.norm(fore,axis=1))
        result[side]={'wrist_max_deg':float(bend.max()),'contact_reach_ratio':float(reach[round(.6*rate)]),
            'contact_elbow_flex_deg':float(elbow[round(.6*rate)]),'max_hand_step_cm':float(np.linalg.norm(np.diff(p[:,h],axis=0),axis=1).max()),
            'reach_over_90_seconds':float(np.sum(reach>.9)/rate),
            'samples':[{'t':t,'reach':round(float(reach[round(t*rate)]),3),'elbow':round(float(elbow[round(t*rate)]),1),'wrist':round(float(bend[round(t*rate)]),1),'hand':np.round(p[round(t*rate),h],2).tolist()} for t in [0,.24,.4,.5,.54,.6,.72,.9,1.4]]}
    return result
def diagnose():
    src=json.loads((OUT/'inputs.json').read_text());report={}
    for label,d in src.items():
        b=body_for(label,d);report[label]=metrics(b,np.array(d['clips'][ROLE]['frames']))
    (OUT/'before-metrics.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,ensure_ascii=False,indent=2))
def fit_chain(b,f,side,goal,pole,hand,weight):
    ip,iq=b.world(b.idle);p,q=b.world(f)
    u,e,h=[b.ix[k+'_'+side] for k in ('upperarm','lowerarm','hand')]
    origin=p[:,u];axis=c.unit(goal-origin)
    bend=c.unit(pole-origin-axis*np.sum((pole-origin)*axis,axis=1)[:,None])
    beta,bank=np.meshgrid(np.radians(np.arange(-20.,21.,10.)),np.radians(np.arange(-180.,181.,15.)),indexing='ij')
    choices=np.c_[beta.ravel(),bank.ravel()];count=len(choices);cost=[];wrist=R.from_quat(b.idle[h,3:7])
    for k in range(len(f)):
        el,up,fore=old.solve(b,side,np.repeat(origin[k][None],count,axis=0),np.repeat(goal[k][None],count,axis=0),
            np.repeat(bend[k][None],count,axis=0),choices[:,0]*weight[k],choices[:,1]*weight[k],ip,iq)
        residual=((fore*wrist).inv()*hand[k]).magnitude()
        sign=1 if side=='l' else -1
        # Keep elbows below their shoulders and in their own blade lanes.
        high=np.maximum(0.,el[:,2]-origin[k,2]+3.)/12.
        inward=np.maximum(0.,-sign*(el[:,0]-origin[k,0])-3.)/12.
        cost.append(12.*residual**2+.9*choices[:,0]**2+.018*choices[:,1]**2+10.*high**2+8.*inward**2)
    cost=np.array(cost);dif=choices[:,None]-choices[None];trans=.9*np.sum(dif*dif,axis=2)
    trans[np.max(abs(dif),axis=2)>np.radians(20.1)]=np.inf
    back=np.zeros((len(f),count),int);score=cost[0]
    for k in range(1,len(f)):
        vals=score[:,None]+trans;back[k]=vals.argmin(0);score=cost[k]+vals[back[k],np.arange(count)]
    route=np.zeros(len(f),int);route[-1]=score.argmin()
    for k in range(len(f)-1,0,-1):route[k-1]=back[k,route[k]]
    angles=gaussian_filter1d(choices[route],2.,axis=0,mode='nearest')*weight[:,None]
    _,upper,fore=old.solve(b,side,origin,goal,bend,angles[:,0],angles[:,1],ip,iq)
    b.set_world_rotations(f,{u:upper,e:fore,h:hand})

def make():
    src=json.loads((OUT/'inputs.json').read_text());report={}
    for label,d in src.items():
        b=body_for(label,d);take=d['clips'][ROLE];f=np.array(take['frames']);t=np.arange(len(f))/RATE
        ip,iq=b.world(b.idle);p,q=b.world(f);ch=b.ix['spine_05']
        torso=R.from_quat(q[:,ch])*R.from_quat(b.tq[ch]).inv()
        idle_torso=R.from_quat(iq[ch])*R.from_quat(b.tq[ch]).inv()
        facing=torso.apply(np.tile([0.,1.,0.],(len(f),1)))
        heading=R.from_rotvec(np.c_[np.zeros(len(f)),np.zeros(len(f)),np.arctan2(-facing[:,0],facing[:,1])])
        w=c.ease(t/.24)*(1.-c.ease((t-1.35)/(.70)))
        # The torso/feet retain the existing planted stride. Both native arms
        # drive forward from low ready, never copying camera-cropped FPS reach.
        for side in 'rl':
            u,e,h=[b.ix[k+'_'+side] for k in ('upperarm','lowerarm','hand')]
            length=np.linalg.norm(ip[e]-ip[u])+np.linalg.norm(ip[h]-ip[e]);sign=1 if side=='l' else -1
            rest=idle_torso.inv().apply(ip[h]-ip[u])
            target=np.array([[sign*.12,.28,-.44],[sign*.10,.36,-.35],
                [sign*.035,.965,-.13],[sign*.035,.965,-.13],
                [sign*.07,.89,-.19],[sign*.15,.49,-.37],[sign*.21,.30,-.55]])*length
            if side=='l':target[:,2]-=2.
            target[2:4]=c.unit(target[2:4])*(.975*length)
            active=PchipInterpolator([0,.30,.60,.80,.95,1.25,2.05],target)(t)
            goal=p[:,u]+torso.apply(np.tile(rest,(len(f),1)))*(1-w[:,None])+heading.apply(active)*w[:,None]
            restpole=idle_torso.inv().apply(ip[e]-ip[u])
            pole=p[:,u]+torso.apply(np.tile(restpole,(len(f),1)))*(1-w[:,None])+heading.apply(np.tile(np.array([sign*.28,.08,-.54])*length,(len(f),1)))*w[:,None]
            # The curved kukri tip is +Z with a +X edge offset. An outward
            # blade lane keeps its actual tip forward without forcing a
            # hammer-style fist through a 90-degree wrist bend.
            z=c.unit(np.array([sign*.65,.76,-.035]));x=c.unit(np.array([0.,1.,0.])-z*np.dot(z,[0.,1.,0.]))
            blade=R.from_rotvec([0.,sign*np.pi*.5,0.])*R.from_matrix(np.column_stack((x,np.cross(z,x),z)))
            mount=previous.mounts(b)[side][1]
            ready=torso*idle_torso.inv()*R.from_quat(iq[h]);desired=heading*blade*mount.inv()
            # Choose one continuous palm-turn branch for the whole take.
            # Per-frame shortest-path slerp flips at 180 degrees as the torso
            # returns, creating a visible offhand snap despite smooth inputs.
            delta=(ready.inv()*desired).as_quat()
            if delta[0,3]<0:delta[0]*=-1
            for k in range(1,len(delta)):
                if np.dot(delta[k-1],delta[k])<0:delta[k]*=-1
            sine=np.linalg.norm(delta[:,:3],axis=1)
            rotation=delta[:,:3]*(2*np.arctan2(sine,delta[:,3])/np.maximum(sine,1e-9))[:,None]
            hand=ready*R.from_rotvec(rotation*w[:,None])
            fit_chain(b,f,side,goal,pole,hand,w)
            # Keep entry/return palm changes reachable as the elbow folds.
            # Refit the complete chain after relaxing palm direction, rather
            # than clamping a wrist joint onto a contradictory forearm.
            for repeat in range(2):
                wp,wq=b.world(f);forearm=c.unit(wp[:,h]-wp[:,e])
                palm=(R.from_quat(wq[:,h])*R.from_quat(b.ref[h,3:7]).inv()).apply(np.tile(c.unit(b.ref[h,:3]),(len(f),1)))
                angle=np.arccos(np.clip(np.sum(palm*forearm,axis=1),-1,1))
                amount=np.maximum(0.,angle-np.radians(43.))/np.maximum(angle,1e-8)
                if not np.any(amount>0):break
                relaxed=R.from_rotvec(c.align(palm,forearm).as_rotvec()*amount[:,None])*R.from_quat(wq[:,h])
                fit_chain(b,f,side,goal,pole,relaxed,w)
            for i,name in enumerate(b.names):
                if name.endswith('_'+side) and name.startswith(('thumb_','index_','middle_','ring_','pinky_')):f[:,i]=b.idle[i]
        old.helpers(b,f);f[0]=b.idle;f[-1]=b.idle
        frames=old.carry.continuous(f)
        output={'mesh':d['mesh'],'names':b.names,'parents':b.parents,'clips':{ROLE:{'rate_num':RATE,'rate_den':1,
            'frames':frames.tolist(),'contact':.60/t[-1],'release':.72/t[-1],
            'source':take['asset'],'adaptation':'Native low-elbow dual thrust; long visible drive, forward blade lanes, same replicated 0.60/0.72 contact clock'}}}
        (OUT/(label+'-actions.json')).write_text(json.dumps(output,separators=(',',':')))
        report[label]=metrics(b,f);print('THRUST_AUTHORED',label,{s:{k:v for k,v in m.items() if k!='samples'} for s,m in report[label].items()},flush=True)
    (OUT/'after-metrics.json').write_text(json.dumps(report,indent=2))
if __name__=='__main__':
    import sys
    if '--make' in sys.argv:make()
    else:diagnose()
