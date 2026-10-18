"""Author one complete two-hand Jason take, on native hinges and real rack grips."""
import json,math
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as Q
from scipy.optimize import least_squares
from scipy.interpolate import PchipInterpolator
O=Path(__file__).parent;R=O.parents[1]
inputs=json.loads((R/'SourceAssets/ThirdPersonWizardDrink20261010/inputs.json').read_text())
rig=json.loads((O/'body_rig.json').read_text()) if (O/'body_rig.json').exists() else inputs['target']
names=rig['names'];parents=rig['parents'];ix={n:i for i,n in enumerate(names)};ref=np.array(rig['reference'])
accepted=json.loads((R/'SourceAssets/ThirdPersonWizardDrink20261010/authored.json').read_text())
donor=np.array(accepted['clips']['Consume.Drink']['frames']);idle=np.array(inputs['target']['clips']['idle']['frames'][0])
grasp=json.loads((O/'native_grasp.json').read_text());motion=json.loads((O/'fps_motion.json').read_text());times=motion['times']
mouth_local=np.array(accepted['mouth_in_head']);bite=np.array(motion['bite_in_object'])
def unit(v):return v/max(np.linalg.norm(v),1e-10)
def ease(t):t=np.clip(t,0,1);return t*t*t*(t*(6*t-15)+10)
def rotq(v):return Q.from_rotvec(v)
def frame(x,y):
    x=unit(x);y=unit(y-x*np.dot(x,y));return Q.from_matrix(np.column_stack([x,y,np.cross(x,y)]))
def align(a,b):
    a=unit(a);b=unit(b);v=np.r_[np.cross(a,b),1+np.dot(a,b)]
    return Q.from_quat(v/np.linalg.norm(v)) if np.linalg.norm(v)>1e-7 else Q.from_rotvec(unit(np.cross(a,[0,0,1]))*math.pi)
def matrix(v):
    m=np.eye(4);m[:3,:3]=Q.from_quat(v[3:7]).as_matrix();m[:3,3]=v[:3];return m
def fk(f):
    w=f.copy()
    for i,p in enumerate(parents):
        if p>=0:
            q=Q.from_quat(w[p,3:7]);w[i,:3]=w[p,:3]+q.apply(f[i,:3]*w[p,7:]);w[i,3:7]=(q*Q.from_quat(f[i,3:7])).as_quat();w[i,7:]=w[p,7:]*f[i,7:]
    return w
def under(i,a):
    while i>=0:
        if i==a:return True
        i=parents[i]
    return False
def sample(t):
    at=np.clip(t,0,1)*(len(donor)-1);i=min(int(at),len(donor)-2);a=at-i
    f=donor[i]*(1-a)+donor[i+1]*a;qa=Q.from_quat(donor[i,:,3:7]);qb=Q.from_quat(donor[i+1,:,3:7]);f[:,3:7]=(rotq((qb*qa.inv()).as_rotvec()*a)*qa).as_quat();return f
bind=fk(ref);mounts={};hand_in_food={};grip=ref.copy();sp={n:np.array(v) for n,v in grasp['source_pose'].items()};sb={n:np.array(v) for n,v in grasp['source_bind'].items()}
for side in ['l','r']:
    hand='hand_'+side;h=ix[hand];src=sb[hand];dst=bind[h]
    a=np.array([Q.from_quat(src[3:]).inv().apply(sb[d+'_01_'+side][:3]-src[:3]) for d in ['index','middle','pinky']])
    b=np.array([Q.from_quat(dst[3:7]).inv().apply(bind[ix[d+'_01_'+side],:3]-dst[:3]) for d in ['index','middle','pinky']])
    mq=frame(b[1],b[0]-b[2])*frame(a[1],a[0]-a[2]).inv();mp=b.mean(axis=0)-mq.apply(a.mean(axis=0));mounts[side]=np.r_[mp,mq.as_quat()]
    hand_in_food[side]=matrix(grasp['hand_in_object'][side])@np.linalg.inv(matrix(mounts[side]))
    # Same anatomical mount and per-digit transfer as FFPSBodyGripRig.
    desired={};worldq={};sq=Q.from_quat(sp[hand][3:]);nq=Q.from_quat(dst[3:7]);frameq=nq*mq*sq.inv()
    def point(n):return dst[:3]+nq.apply(mp+mq.apply(sq.inv().apply(sp[n][:3]-sp[hand][:3])))
    for digit in ['thumb','index','middle','ring','pinky']:
        ns=[f'{digit}_{j:02}_{side}' for j in range(1,4)];bs=[ix[n] for n in ns]
        for j in range(3):
            a0,b0=(j,j+1) if j<2 else (1,2)
            na=Q.from_quat(bind[bs[j],3:7]).inv().apply(bind[bs[b0],:3]-bind[bs[a0],:3]);sa=Q.from_quat(sb[ns[j]][3:]).inv().apply(sb[ns[b0]][:3]-sb[ns[a0]][:3])
            desired[bs[j]]=frameq*Q.from_quat(sp[ns[j]][3:])*align(na,sa)
        root=bind[bs[0],:3];goal=point(ns[2]);pole=point(ns[1]);l1=np.linalg.norm(bind[bs[1],:3]-root);l2=np.linalg.norm(bind[bs[2],:3]-bind[bs[1],:3]);axis=unit(goal-root);reach=np.clip(np.linalg.norm(goal-root),abs(l1-l2)+.001,l1+l2-.001)
        bend=unit(pole-root-axis*np.dot(pole-root,axis));along=(l1*l1-l2*l2+reach*reach)/(2*reach);joint=root+axis*along+bend*np.sqrt(max(0,l1*l1-along*along))
        for j,span in enumerate([joint-root,root+axis*reach-joint]):
            na=Q.from_quat(bind[bs[j],3:7]).inv().apply(bind[bs[j+1],:3]-bind[bs[j],:3]);desired[bs[j]]=align(desired[bs[j]].apply(na),span)*desired[bs[j]]
    for i,p in enumerate(parents):
        pq=worldq[p] if p>=0 else Q.identity();local=Q.from_quat(ref[i,3:7])
        if i in desired:local=pq.inv()*desired[i]
        elif '_half_' in names[i] and p in desired:
            delta=Q.from_quat(ref[p,3:7]).inv()*Q.from_quat(grip[p,3:7]);local=rotq(-delta.as_rotvec()*.5)*local
        worldq[i]=pq*local
        if i!=h and under(i,h):grip[i,3:7]=local.as_quat()

# Entire rack moves in front of the native body, independently of the eye rig.
# Offset is relative to the lips: forward is body +Y, lateral is body X.
keys=np.array([[0,-3,-48],[.55,-3,-48],[1,0,-33],[1.65,7,-18],[2.75,8,-12],[3.75,6,-8],[4.25,4,-5],[4.65,2,-1.5],[4.75,2,-1.5],[4.9,3,-10],[5.3,0,-32],[5.625,-3,-48],[6,-3,-48]])
forward=PchipInterpolator(keys[:,0],keys[:,1]);height=PchipInterpolator(keys[:,0],keys[:,2])
pitch=PchipInterpolator([0,.55,1.65,2.75,4.65,4.75,5.3,5.625,6],[-55,-55,18,24,30,30,-30,-55,-55])
basis=Q.from_euler('z',90,degrees=True);object_base=Q.from_euler('z',-90,degrees=True)
arm={};previous={};previous_elbow={}
for side in ['l','r']:
    u,e,h=[ix[n+'_'+side] for n in ['upperarm','lowerarm','hand']];axis=unit(ref[h,:3]);lr=Q.from_quat(ref[e,3:7]);rd=lr.apply(axis);hinge=unit(np.cross(unit(ref[e,:3]),rd));rest_flex=np.arccos(np.clip(unit(ref[e,:3])@rd,-1,1))
    helpers=[j for j in range(len(names)) if under(j,u) and j not in (u,e,h) and not under(j,h)]
    arm[side]=(u,e,h,axis,lr,hinge,rest_flex,helpers)
frames=[];metrics=[];object_frames=[]
for seconds in np.linspace(0,6,361):
    phase=np.interp(seconds,[0,.55,2.75,4.65,4.75,5.625,6],[0,0,.4,.64,.75,1,1]);f=sample(phase)
    for i,n in enumerate(names):
        if n in ('clavicle_l','clavicle_r'):f[i]=idle[i]
        if n.startswith(('neck_','head','spine_')):
            q=Q.from_quat(donor[0,i,3:7]);gain=.35 if n.startswith(('neck_','head')) else .55
            f[i,3:7]=(rotq((Q.from_quat(f[i,3:7])*q.inv()).as_rotvec()*gain)*q).as_quat()
    w=fk(f);mouth=w[ix['head'],:3]+Q.from_quat(w[ix['head'],3:7]).apply(mouth_local)
    oq=basis*Q.from_euler('y',-float(pitch(seconds)),degrees=True)*object_base
    bite_world=mouth+np.array([0,float(forward(seconds)),float(height(seconds))]);op=bite_world-oq.apply(bite)
    ob=matrix(np.r_[op,oq.as_quat()]);object_frames.append(np.r_[op,oq.as_quat()].tolist());row={'time':float(seconds),'arms':{}}
    for side,sign in [('l',1),('r',-1)]:
        u,e,h,axis,lr,hinge,rest_flex,helpers=arm[side];shoulder=w[u,:3];base_upper=Q.from_quat(w[parents[u],3:7])*Q.from_quat(ref[u,3:7]);wrist_rest=Q.from_quat(ref[h,3:7]);target=ob@hand_in_food[side];target_q=Q.from_matrix(target[:3,:3]);target_p=target[:3,3]
        def solvepose(x):
            uq=rotq(x[:3])*base_upper;lq=rotq(hinge*(x[3]-rest_flex))*lr*rotq(axis*x[4]);eq=uq*lq;elbow=shoulder+uq.apply(ref[e,:3]);hp=elbow+eq.apply(ref[h,:3]);hq=eq*wrist_rest*rotq(x[5:8]);return uq,lq,elbow,hp,hq
        initial=previous.get(side,np.r_[np.zeros(3),np.deg2rad(85),0,np.zeros(3)]).copy()
        def residual(x):
            _,_,elbow,hp,hq=solvepose(x)
            # Keep each elbow outside its side of the torso and below the shoulder.
            clearance=[max(0,20-sign*elbow[0]),max(0,5-elbow[1]),max(0,elbow[2]-shoulder[2]+2)]
            smooth=np.r_[(x-previous[side])*.15,(elbow-previous_elbow[side])*1.2] if side in previous else np.zeros(11)
            return np.r_[(hp-target_p)/.12,(target_q.inv()*hq).as_rotvec()/.035,np.array(clearance)/1.0,x[5:8]*.35,x[:3]*.03,smooth]
        low=np.r_[[-2.8]*3,np.deg2rad(20),np.deg2rad(-90),np.deg2rad([-20,-30,-30])];high=np.r_[[2.8]*3,np.deg2rad(145),np.deg2rad(90),np.deg2rad([20,30,30])]
        result=least_squares(residual,np.clip(initial,low+1e-6,high-1e-6),bounds=(low,high),max_nfev=65,ftol=1e-6,xtol=1e-6,gtol=1e-6)
        previous[side]=result.x;uq,lq,elbow,hp,hq=solvepose(result.x);previous_elbow[side]=elbow.copy()
        f[u,3:7]=(Q.from_quat(w[parents[u],3:7]).inv()*uq).as_quat();f[e,3:7]=lq.as_quat();f[h,3:7]=(wrist_rest*rotq(result.x[5:8])).as_quat()
        for j in helpers:
            f[j]=ref[j]
            if parents[j]==e:
                station=np.clip(np.dot(ref[j,:3],axis)/np.linalg.norm(ref[h,:3]),0,1);f[j,3:7]=(rotq(axis*(-result.x[4]*(1-station)))*Q.from_quat(ref[j,3:7])).as_quat()
        closure=ease((seconds-times['grab']*.42)/(times['grab']*.58))*(1-ease((seconds-times['release'])/.08))
        for j in range(len(names)):
            if j!=h and under(j,h):
                a=Q.from_quat(ref[j,3:7]);b=Q.from_quat(grip[j,3:7]);f[j]=ref[j];f[j,3:7]=(rotq((b*a.inv()).as_rotvec()*closure)*a).as_quat()
        row['arms'][side]=dict(wrist_error_cm=float(np.linalg.norm(hp-target_p)),wrist_rotation_error_deg=float(np.linalg.norm((target_q.inv()*hq).as_rotvec())*180/math.pi),elbow=elbow.tolist(),shoulder=shoulder.tolist(),wrist=hp.tolist(),elbow_flex_deg=float(np.rad2deg(result.x[3])),forearm_roll_deg=float(np.rad2deg(result.x[4])),wrist_delta_deg=np.rad2deg(result.x[5:8]).tolist())
    frames.append(f);metrics.append(row)
frames=np.array(frames)
for i in range(1,len(frames)):
    flip=np.sum(frames[i-1,:,3:7]*frames[i,:,3:7],axis=1)<0;frames[i,flip,3:7]*=-1
out=dict(mesh=rig['mesh'],names=names,parents=parents,reference=ref.tolist(),rate=60,frames=frames.tolist(),object_frames=object_frames,hand_in_food={s:v.tolist() for s,v in hand_in_food.items()},mounts={s:v.tolist() for s,v in mounts.items()},mouth_in_head=mouth_local.tolist(),times=times,source=accepted['clips']['Consume.Drink']['source'],source_url=accepted['source_url'])
(O/'authored_body.json').write_text(json.dumps(out,separators=(',',':')));(O/'body_fit.json').write_text(json.dumps(metrics,indent=2))
print('LAMB_NATIVE_BODY_AUTHORED',len(frames),'max wrist position error',max(a['wrist_error_cm'] for row in metrics for a in row['arms'].values()),'max rotation error',max(a['wrist_rotation_error_deg'] for row in metrics for a in row['arms'].values()))
