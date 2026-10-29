"""Native third-person charged kukri cut, adapted from CC0 UAL2 B/B Rec.

The existing heavy executor supplies the charge and release clocks. The source
keeps the torso dip and recovery; its wide rotating cut is fitted to the current
right-shoulder-back / upper-right-to-lower-left weapon contract. No gameplay or
first-person animation is changed.
"""
import importlib.util
import json
from pathlib import Path

import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.spatial.transform import Rotation as R

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
BASE = ROOT/'SourceAssets/KukriThirdPerson20261024/ComboV3'


def module(name, path):
    spec = importlib.util.spec_from_file_location(name,path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


c = module('kukri_heavy_combo',BASE/'author.py')
fingers = module('kukri_heavy_fingers',ROOT/'SourceAssets/KukriThrustHand20261025/author.py')
CHARGE_LENGTH, RELEASE_LENGTH = 2.,35/30
RK = np.array([0.,4/120,.075,16/120,.22,.35,.62,.85,1.05,RELEASE_LENGTH])
CK = np.array([0.,.13,.25,.40,.80,1.40,1.80,CHARGE_LENGTH])


def interp(keys,values,t):
    return PchipInterpolator(keys,np.asarray(values))(t)


def rotations(keys,quats,times):
    values=[]
    for t in times:
        k=int(np.clip(np.searchsorted(keys,t,side='right')-1,0,len(keys)-2))
        w=c.ease((t-keys[k])/(keys[k+1]-keys[k]))
        values.append(c.slerp(quats[k],quats[k+1],w))
    return R.from_quat(values)


def blade(direction):
    tip=c.unit(np.asarray(direction,dtype=float))
    edge=c.unit(np.array([0.,0.,-1.])+tip*tip[2])
    return c.frame(edge,np.cross(tip,edge))


def torso(body,source,heading,weight):
    """Keep the donor flexion, but turn its rotating sweep into a front cut."""
    result=source.copy()
    _,world=body.world(result)
    desired={}
    for name in ('pelvis','spine_01','spine_02','spine_03','neck_01','head'):
        i=body.ix[name]
        q=R.from_quat(world[:,i])
        forward=(q*R.from_quat(body.tq[i]).inv()).apply(np.tile([0.,1.,0.],(len(result),1)))
        yaw=np.arctan2(-forward[:,0],forward[:,1])
        target=np.radians(heading*(.2 if name in ('neck_01','head') else .65 if name=='pelvis' else 1.))
        desired[i]=R.from_euler('z',(target-yaw)[:,None])*q
    body.set_world_rotations(result,desired)
    for i,w in enumerate(weight):result[i]=c.blend(body.idle,result[i],w)
    return result


def fit_feet(body,frames,times,keys,offsets,heel,weight,size):
    idle_p,idle_q=body.world(body.idle)
    goals={};rots={}
    for side in 'lr':
        i=body.ix['foot_'+side];ball=body.ix['ball_'+side]
        lift=interp(keys,offsets[side],times)*size
        angle=interp(keys,heel[side],times)
        rots[side]=R.from_euler('x',angle[:,None],degrees=True)*R.from_quat(np.tile(idle_q[i],(len(times),1)))
        toe=R.from_quat(idle_q[i]).inv().apply(idle_p[ball]-idle_p[i])
        delta=rots[side].apply(np.tile(toe,(len(times),1)))
        goals[side]=idle_p[i]+lift
        # Heel rotation about the ball of the foot preserves the planted toe.
        goals[side]+=np.tile(idle_p[ball]-idle_p[i],(len(times),1))-delta
    p,_=body.world(frames)
    drop=np.zeros(len(frames))
    for side in 'lr':
        h,k,a=[p[:,body.ix[n+'_'+side]] for n in ('thigh','calf','foot')]
        reach=(np.linalg.norm(k-h,axis=1)+np.linalg.norm(a-k,axis=1))*.990
        goal=goals[side]
        maxz=goal[:,2]+np.sqrt(np.maximum(1.,reach**2-np.sum((goal[:,:2]-h[:,:2])**2,axis=1)))
        drop=np.maximum(drop,h[:,2]-maxz)
    frames[:,body.hip,2]-=drop
    for side in 'lr':
        target=frames[:,body.hip,:3]+np.array([-31 if side=='r' else 28,39,-30])*size
        pole=idle_p[body.ix['calf_'+side]]*(1-weight[:,None])+target*weight[:,None]
        body.solve(frames,[n+'_'+side for n in ('thigh','calf','foot')],goals[side],pole,rots[side])


def fit_arms(body,frames,times,keys,right,left,rightq,leftq,poles,size):
    hips=frames[:,body.hip,:3]
    for side,offsets,qs in [('r',right,rightq),('l',left,leftq)]:
        goals=hips+interp(keys,offsets,times)
        pole=hips+interp(keys,poles[side],times)
        body.solve(frames,[n+'_'+side for n in ('upperarm','lowerarm','hand')],goals,pole,rotations(keys,qs,times))


def closed_guard(body,frames,times,fist,charge):
    for i,name in enumerate(body.names):
        digit=name.split('_')[0]
        if not name.endswith('_l') or digit not in ('thumb','index','middle','ring','pinky'):continue
        if charge:
            delay={'pinky':0.,'ring':.006,'middle':.012,'index':.02,'thumb':.045}[digit]
            w=c.ease((times-delay)/.21)
        else:w=1-c.ease((times-.62)/.43)
        frames[:,i,3:7]=c.slerp(frames[:,i,3:7],fist[i,3:7],w[:,None])


def make_body(label,data,previous,fist_source):
    body=c.Body(data);size=body.scale/94.
    ip,iq=body.world(body.idle);hip=ip[body.hip]
    ri,li=body.ix['hand_r'],body.ix['hand_l']
    idle_right=ip[ri]-hip;idle_left=ip[li]-hip
    elbow={s:ip[body.ix['lowerarm_'+s]]-hip for s in 'lr'}
    raw=body.retarget(np.asarray(c.SOURCE['clips']['Sword_Regular_B']['frames']))
    rec=body.retarget(np.asarray(c.SOURCE['clips']['Sword_Regular_B_Rec']['frames']))
    rt=np.arange(round(RELEASE_LENGTH*120)+1)/120
    bt=np.array([0.,4/120,.075,16/120,.22,.35])
    bs=np.array([0.,.12,.23,.30,.42,(len(raw)-1)/60])
    rct=np.array([.35,.62,.85,1.05,RELEASE_LENGTH])
    rcs=np.array([0.,.22,.60,.92,(len(rec)-1)/60])
    source=np.array([c.sample(raw,float(interp(bt,bs,t))) if t<=.35 else c.sample(rec,float(interp(rct,rcs,t))) for t in rt])
    heading=interp(RK,[32,23,-8,-26,-29,-25,-12,4,12,12],rt)
    rw=.68*(1-c.ease((rt-.85)/(RELEASE_LENGTH-.85)))
    release=torso(body,source,heading,rw)
    hip_keys=np.array([[3,-7,-9],[2,-4,-8],[-1,6,-10],[-2,10,-13],[0,10,-10],
                       [0,9,-8],[0,6,-5],[0,2,-2],[0,0,0],[0,0,0]])*size
    release[:,body.hip,:3]=hip+interp(RK,hip_keys,rt)
    # The front foot receives the cut; the rear foot pushes through its toe.
    # Both feet return in separate small steps instead of sliding together.
    fo={'l':np.array([[0,0,0],[0,2,2],[0,10,2],[0,12,0],[0,12,0],[0,12,0],
                       [0,12,0],[0,6,5],[0,0,0],[0,0,0]]),
        'r':np.array([[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,2,4],
                       [0,4,0],[0,4,0],[0,0,3],[0,0,0]])}
    heel={'l':[0,0,0,0,0,0,0,0,0,0],'r':[0,-6,-15,-18,-12,-4,0,0,0,0]}
    active=1-c.ease((rt-.85)/(RELEASE_LENGTH-.85))
    fit_feet(body,release,rt,RK,fo,heel,active,size)
    right=np.array([[-29,-12,67],[-26,18,72],[-7,49,27],[29,33,8],[35,6,5],
                    [29,4,12],[-5,22,26],[-26,8,29],idle_right/size,idle_right/size])*size
    left=np.array([[27,29,42],[27,30,43],[28,28,43],[29,20,38],[30,18,35],
                   [29,21,36],[28,28,37],[27,38,30],idle_left/size,idle_left/size])*size
    directions=[[.06,-.97,.24],[.06,.40,.91],[.30,.95,-.10],[.50,.50,-.70],
                [.45,.05,-.89],[.30,.30,-.90],[-.10,.85,-.52],[-.12,.98,.15]]
    rq=np.array([(blade(d)*body.blade_local.inv()).as_quat() for d in directions]+[iq[ri],iq[ri]])
    guard=(R.from_euler('xz',[-12,-10],degrees=True)*R.from_quat(iq[li])).as_quat()
    lq=np.array([guard]*7+[c.slerp(guard,iq[li],.5),iq[li],iq[li]])
    poles={'r':np.array([[-43,0,46],[-42,12,47],[-29,22,20],[-6,14,0],[-10,1,9],
                        [-20,-1,16],[-35,3,18],[-36,1,22],elbow['r']/size,elbow['r']/size])*size,
           'l':np.array([[42,7,23]]*6+[[41,12,24],[37,16,21],elbow['l']/size,elbow['l']/size])*size}
    fit_arms(body,release,rt,RK,right,left,rq,lq,poles,size)
    fist=fingers.native_fist(body,fist_source)
    closed_guard(body,release,rt,fist,False)
    release=body.twists(release)
    for i,t in enumerate(rt):release[i]=c.blend(release[i],body.idle,c.ease((t-1.05)/(RELEASE_LENGTH-1.05)))
    release[-1]=body.idle

    # Build the charge into that exact release pose. The final hold contains no
    # new sway clock; the gameplay owner may hold it for any charge duration.
    ct=np.arange(121)/60
    cw=c.ease(ct/.40)
    charge=torso(body,np.repeat(raw[:1],len(ct),axis=0),np.full(len(ct),32.),.68*cw)
    ch=np.array([[0,0,0],[0,-2,-2],[1,-4,-5],[2,-6,-7],[3,-7,-9],
                 [3,-7,-9],[3,-7,-9],[3,-7,-9]])*size
    charge[:,body.hip,:3]=hip+interp(CK,ch,ct)
    zeros={s:np.zeros((len(CK),3)) for s in 'lr'}
    fit_feet(body,charge,ct,CK,zeros,{s:np.zeros(len(CK)) for s in 'lr'},cw,size)
    cr=np.array([idle_right/size,[-35,0,28],[-35,3,60],[-32,-5,65],
                 [-29,-12,67],[-29,-12,67],[-29,-12,67],[-29,-12,67]])*size
    cl=np.array([idle_left/size,[28,42,30],[28,35,39],[27,29,42],
                 [27,29,42],[27,29,42],[27,29,42],[27,29,42]])*size
    up=(blade([-.25,.30,.92])*body.blade_local.inv()).as_quat()
    upright=(blade([.03,.05,.998])*body.blade_local.inv()).as_quat()
    almost=(blade([.08,-.94,.32])*body.blade_local.inv()).as_quat()
    crq=np.array([iq[ri],up,upright,almost,rq[0],rq[0],rq[0],rq[0]])
    clq=np.array([iq[li],c.slerp(iq[li],guard,.4),guard,guard,guard,guard,guard,guard])
    cp={'r':np.array([elbow['r']/size,[-39,-1,22],[-43,0,43],[-43,0,46],
                       [-43,0,46],[-43,0,46],[-43,0,46],[-43,0,46]])*size,
        'l':np.array([elbow['l']/size,[39,16,23],[42,7,23],[42,7,23],
                       [42,7,23],[42,7,23],[42,7,23],[42,7,23]])*size}
    fit_arms(body,charge,ct,CK,cr,cl,crq,clq,cp,size)
    closed_guard(body,charge,ct,fist,True)
    charge=body.twists(charge)
    for i,t in enumerate(ct):
        # Match helper bones as well as primary limbs across the phase handoff.
        charge[i]=c.blend(charge[i],release[0],c.ease((t-.40)/.40))
    charge[0]=body.idle
    charge[ct>=.80]=release[0]
    src='; '.join(c.SOURCE['clips'][key]['asset'] for key in ('Sword_Regular_B','Sword_Regular_B_Rec'))
    clips={
        'Charge':dict(frames=charge.tolist(),rate=60,loop=False,contact=.20,release=.40,
            source=src,adaptation='Native shoulder-back chamber into the exact Heavy first frame; planted bent legs and rear weight; closed left guard; held last pose.'),
        'Heavy':dict(frames=release.tolist(),rate=120,loop=False,contact=.075/RELEASE_LENGTH,release=.133/RELEASE_LENGTH,
            source=src,adaptation='Retimed B/B Rec torso dip and recovery; reduced turn, native shoulder-to-opposite-low blade arc, front foot receive and rear toe push; closed left guard; full idle recovery.')}
    (OUT/(label+'-actions.json')).write_text(json.dumps(dict(mesh=data['mesh'],names=data['names'],parents=data['parents'],clips=clips),separators=(',',':')))
    return dict(mesh=data['mesh'],skeleton=data['skeleton'],previous_roles=previous,
        source_attack_clock=bt.tolist(),source_attack_times=bs.tolist(),source_recovery_clock=rct.tolist(),source_recovery_times=rcs.tolist(),
        charge_seconds=CHARGE_LENGTH,release_seconds=RELEASE_LENGTH,charge_rate=60,release_rate=120,
        contact_seconds=.075,release_seconds_marker=.133,charge_hold_from=.80,matched_endpoints=True,
        frames={k:len(v['frames']) for k,v in clips.items()})


def main():
    cfg=json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
    fist=json.loads((ROOT/'SourceAssets/UnarmedIdle20261001/full-pose.json').read_text())
    receipt=dict(bodies={},source_license='CC0 Quaternius UAL2',
        source_url='https://quaternius.com/packs/universalanimationlibrary2.html',
        source_cache=str((BASE/'inputs.json').relative_to(ROOT)),runtime_tested=False,rendered=False,
        first_person_changed=False,gameplay_changed=False)
    for label,data in c.INPUT['targets'].items():
        active=cfg if label=='jason' else cfg['body_variants'][label]
        previous={k:active['clips']['Kukri.FullBody.'+k] for k in ('Charge','Heavy')}
        receipt['bodies'][label]=make_body(label,data,previous,fist)
        print('KUKRI_HEAVY_AUTHORED '+label,flush=True)
    (OUT/'authoring.json').write_text(json.dumps(receipt,indent=2))


if __name__=='__main__':
    main()
