"""Native shoulder/elbow poses from the accepted pistol + reverse-kukri grasp.

Keep both hand orientations and their contact spacing; fit the whole group to
each body's shoulders instead of importing the displaced FPS shoulder roots.
"""
import importlib.util
import json
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from scipy.spatial.transform import Rotation as R

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
spec=importlib.util.spec_from_file_location('native_quick',ROOT/'SourceAssets/KukriQuickFirstPerson20261025/author.py')
q=importlib.util.module_from_spec(spec);spec.loader.exec_module(q)
c=q.c
SOURCE=ROOT/'SourceAssets/DualPistolKukri20261025'
C=R.from_euler('z',90,degrees=True)
def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
snapshots={s:read(ROOT/'SourceAssets/BareSkinV9Rollout_20261017/Snapshots'/f) for s,f in
    [('l','01e184ddd1b7.json'),('r','8f309afe12dd.json')]}

def palm_mount(body,side):
    source=snapshots[side]['bones'];hand=source['hand_'+side]
    sq=R.from_quat(hand['q']);tp=body.tp[body.ix['hand_'+side]];tq=R.from_quat(body.tq[body.ix['hand_'+side]])
    a=np.array([sq.inv().apply(np.array(source[d+'_01_'+side]['t'])-hand['t']) for d in ('index','middle','pinky')])
    b=np.array([tq.inv().apply(body.tp[body.ix[d+'_01_'+side]]-tp) for d in ('index','middle','pinky')])
    rot=c.frame(b[1],b[0]-b[2])*c.frame(a[1],a[0]-a[2]).inv()
    return rot,b.mean(0)-rot.apply(a.mean(0))

def segment_distance(a,b,c0,d):
    # Closest points on two finite forearm bones.
    u=b-a;v=d-c0;w=a-c0
    aa=u@u;bb=u@v;cc=v@v;dd=u@w;ee=v@w
    den=aa*cc-bb*bb
    s=np.clip((bb*ee-cc*dd)/max(den,1e-9),0,1)
    t=np.clip((bb*s+ee)/cc,0,1)
    s=np.clip((bb*t-dd)/aa,0,1)
    return np.linalg.norm(a+s*u-c0-t*v)

def author(data,label):
    body=c.Body(data);base=np.array(data['idle']);book=np.array(data['book'])
    for i,n in enumerate(body.names):
        if n=='clavicle_l' or (n.endswith('_l') and any(x in n for x in ('upperarm','lowerarm','hand'))):base[i]=book[i]
    p0,_=body.world(base[None]);p0=p0[0]
    ids={s:[body.ix[a+'_'+s] for a in ('upperarm','lowerarm','hand')] for s in 'rl'}
    shoulders=np.array([p0[ids[s][0]] for s in 'rl']);mid=shoulders.mean(0)
    lengths={s:sum(np.linalg.norm(body.ref[i,:3]) for i in ids[s][1:]) for s in 'rl'}
    scale=np.mean(list(lengths.values()))/51.35
    mounts={s:palm_mount(body,s) for s in 'rl'}
    report={};clips={}
    for role,file in [('Hip','candidate.json'),('Aim','candidate_ads.json')]:
        src=read(SOURCE/file)
        source={s:np.array(src['poses']['right' if s=='r' else 'left']['hand_'+s]) for s in 'rl'}
        rotations={s:C*R.from_matrix(source[s][:3,:3])*mounts[s][0].inv() for s in 'rl'}
        origins={s:C.apply(source[s][:3,3])-rotations[s].apply(mounts[s][1]) for s in 'rl'}
        span=origins['l']-origins['r']
        preferred=mid+np.array([-2.5,32. if role=='Hip' else 35.,-10. if role=='Hip' else -3.])*scale
        def make(x):
            frames=base[None].copy();goals={'r':x[:3],'l':x[:3]+span};poles={}
            for j,s in enumerate('rl'):
                sh=shoulders[j];axis=c.unit(goals[s]-sh)
                down=np.array([-18. if s=='r' else 20.,9.,-28. if s=='r' else -36.])
                bend=c.unit(down-axis*(down@axis));bend=R.from_rotvec(axis*x[3+j]).apply(bend)
                poles[s]=sh+bend*60
                q.solve(body,frames,s,goals[s][None],poles[s][None],R.from_quat(rotations[s].as_quat()[None]),np.ones(1))
            pos,rot=body.world(frames)
            return frames,pos[0],rot[0],goals
        def loss(x):
            f,p,r,goals=make(x)
            value=.24*np.sum((x[:3]-preferred)**2)+.3*np.sum(x[3:]**2)
            for s in 'rl':
                u,e,h=ids[s];expected=rotations[s].apply(R.from_quat(body.ref[h,3:7]).inv().apply(c.unit(body.ref[h,:3])))
                direction=c.unit(p[h]-p[e]);bend=np.arccos(np.clip(expected@direction,-1,1))
                value+=220*bend*bend+500*np.sum((p[h]-goals[s])**2)
                value+=4*max(0,10*scale-abs(p[e,0]-mid[0]))**2
                value+=4*max(0,p0[body.ix['spine_03'],1]+12*scale-p[e,1])**2
            gap=segment_distance(p[ids['r'][1]],p[ids['r'][2]],p[ids['l'][1]],p[ids['l'][2]])
            value+=45*max(0,5.8*scale-gap)**2
            return value
        bounds=[(preferred[k]-d,preferred[k]+d) for k,d in enumerate((7,8,8))]+[(-1.1,1.1),(-1.1,1.1)]
        fit=minimize(loss,np.r_[preferred,0.,0.],method='Powell',bounds=bounds,options={'maxiter':70,'xtol':1e-4,'ftol':1e-5})
        frames,p,r,goals=make(fit.x);q.native_twists(body,frames)
        clips[role]={'rate':1,'frames':np.repeat(frames,2,axis=0).tolist(),
            'source':str(SOURCE/file),'adaptation':'Accepted reverse-kukri palm frames and two-hand spacing; native body shoulders and elbow support; book carry arm reference'}
        report[role]={'optimizer_message':str(fit.message),'native_arm_lengths_cm':lengths,
            'right_hand_cm':p[ids['r'][2]].tolist(),'left_hand_cm':p[ids['l'][2]].tolist(),
            'forearm_bone_clearance_cm':float(segment_distance(p[ids['r'][1]],p[ids['r'][2]],p[ids['l'][1]],p[ids['l'][2]])),
            'body_source':data['idle_asset'],'book_source':data['book_asset']}
    (OUT/(label+'-actions.json')).write_text(json.dumps(dict(mesh=body.data['mesh'],names=body.names,clips=clips),separators=(',',':')))
    return report

if __name__=='__main__':
    report={'bodies':{label:author(data,label) for label,data in read(OUT/'inputs.json').items()},'runtime_tested':False,'rendered':False}
    (OUT/'authoring.json').write_text(json.dumps(report,indent=2))
    print('NATIVE_PISTOL_KUKRI_HIP_AIM_AUTHORED',flush=True)
