"""Installed heavy chop -> combo finisher; repair elbow roll without moving grips.

The combo retains its 2.05 s source clock, 0.60 s impact and 0.54-0.72 window.
Heavy charge/release retain all original timing, including the 0.35 s pull pause.
"""
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R
from scipy.interpolate import PchipInterpolator

P=Path(__file__).resolve().parent
FPS=60

def ease(t):
    t=np.clip(t,0.,1.);return t*t*(3-2*t)

def blend(a,b,t):
    out=a*(1-t)+b*t
    qa,qb=a[:,3:7],b[:,3:7]
    qb=np.where((qa*qb).sum(1)[:,None]<0,-qb,qb)
    q=qa*(1-t)+qb*t
    out[:,3:7]=q/np.linalg.norm(q,axis=1)[:,None]
    return out

def sample(frames,t):
    f=np.clip(t*FPS,0,len(frames)-1);i=int(f)
    return blend(frames[i],frames[min(i+1,len(frames)-1)],f-i)

def world(frame,parents):
    out=frame.copy()
    for i,p in enumerate(parents):
        if p<0:continue
        q=R.from_quat(out[p,3:7])
        out[i,:3]=out[p,:3]+q.apply(frame[i,:3]*out[p,7:])
        out[i,3:7]=(q*R.from_quat(frame[i,3:7])).as_quat()
        out[i,7:]=out[p,7:]*frame[i,7:]
    return out

def unit(v):return v/max(np.linalg.norm(v),1e-10)

def swing(a,b):
    a,b=unit(a),unit(b);q=np.r_[np.cross(a,b),1+np.dot(a,b)]
    return R.from_quat(q/np.linalg.norm(q))

def basis(axis,hinge):
    x=unit(axis);z=unit(hinge);return np.column_stack([x,unit(np.cross(z,x)),z])

def elbow_transport(worlds,bind,ids,weights):
    """Small bend-plane adjustment absorbs excess palm roll without moving hands."""
    up,lo,hand=ids
    bu=bind[lo,:3]-bind[up,:3];bf=bind[hand,:3]-bind[lo,:3];bh=unit(np.cross(bu,bf))
    raw=[]
    for w in worlds:
        s,e,h=w[[up,lo,hand],:3];axis=unit(h-s);centre=s+axis*np.dot(e-s,axis);pole=e-centre
        best=(float('inf'),0.)
        for degrees in range(-75,76,3):
            candidate=centre+R.from_rotvec(axis*np.radians(degrees)).apply(pole)
            if np.linalg.norm(candidate-e)>8.:continue
            f=h-candidate;hinge=unit(np.cross(candidate-s,f))
            delta=R.from_matrix(basis(f,hinge)@basis(bf,bh).T)
            q=(R.from_quat(w[hand,3:7])*(delta*R.from_quat(bind[hand,3:7])).inv()).as_quat()
            phi=(np.degrees(2*np.arctan2(np.dot(q[:3],unit(f)),q[3]))+180)%360-180
            cost=.015*degrees*degrees+2*max(0,abs(phi)-105)**2
            if cost<best[0]:best=(cost,float(degrees))
        raw.append(best[1])
    angles=np.convolve(np.pad(raw,(2,2),mode='edge'),[.1,.2,.4,.2,.1],mode='valid')*weights
    out=worlds.copy()
    for j,w in enumerate(worlds):
        s,e,h=w[[up,lo,hand],:3];axis=unit(h-s);centre=s+axis*np.dot(e-s,axis)
        goal=centre+R.from_rotvec(axis*np.radians(angles[j])).apply(e-centre)
        du=swing(e-s,goal-s);dl=swing(h-e,h-goal)
        out[j,up,3:7]=(du*R.from_quat(w[up,3:7])).as_quat()
        out[j,lo,:3]=goal;out[j,lo,3:7]=(dl*R.from_quat(w[lo,3:7])).as_quat()
    return out

def hinge_angles(w,bind,ids):
    up,lo,h=ids
    u,f=w[lo,:3]-w[up,:3],w[h,:3]-w[lo,:3]
    hinge=unit(np.cross(u,f))
    ref=unit(np.cross(bind[lo,:3]-bind[up,:3],bind[h,:3]-bind[lo,:3]))
    angles=[]
    for bone,axis in [(up,unit(u)),(lo,unit(f))]:
        original=(R.from_quat(w[bone,3:7])*R.from_quat(bind[bone,3:7]).inv()).apply(ref)
        original=unit(original-axis*np.dot(original,axis))
        angles.append(np.arctan2(np.dot(axis,np.cross(original,hinge)),np.dot(original,hinge)))
    bend=np.arccos(np.clip(np.dot(unit(u),unit(f)),-1,1))
    return angles,bend

def repair(frames,data,weights,twist_anchor=None):
    names,parents=data['names'],data['parents'];index={n:i for i,n in enumerate(names)}
    bind=world(np.array(data['reference']),parents)
    worlds=np.array([world(f,parents) for f in frames])
    for side in ('r','l'):
        up,lo,h=[index[k+'_'+side] for k in ('upperarm','lowerarm','hand')]
        old=worlds.copy();worlds=elbow_transport(worlds,bind,(up,lo,h),weights)
        for j,w in enumerate(worlds):
            for limb,root,end in [('upperarm',up,lo),('lowerarm',lo,h)]:
                turn=swing(old[j,end,:3]-old[j,root,:3],w[end,:3]-w[root,:3])
                for suffix in ('01','02'):
                    bone=index[limb+'_twist_'+suffix+'_'+side]
                    worlds[j,bone,:3]=w[root,:3]+turn.apply(old[j,bone,:3]-old[j,root,:3])
                    worlds[j,bone,3:7]=(turn*R.from_quat(old[j,bone,3:7])).as_quat()
    corrected=worlds.copy()
    metrics={};anchors={}
    for side in ('r','l'):
        up,lo,h=[index[k+'_'+side] for k in ('upperarm','lowerarm','hand')]
        raw=[hinge_angles(w,bind,(up,lo,h)) for w in worlds]
        angles=np.unwrap(np.array([v[0] for v in raw]),axis=0)
        # At near extension the bend plane is underdetermined. Fade correction
        # by actual bend, never select a frame-dependent antipodal branch.
        bends=np.array([v[1] for v in raw])
        active=weights*ease((np.degrees(bends)-10)/25)
        # Read palm axial rotation against a pure-hinge lower arm. The imported
        # twist_02 track carried an extra half-turn; halving the MAIN bone's
        # correction would leave the elbow skin ~90 degrees off its bend plane.
        palm=[]
        for j,w in enumerate(worlds):
            f=unit(w[h,:3]-w[lo,:3])
            lq=R.from_rotvec(f*angles[j,1])*R.from_quat(w[lo,3:7])
            delta=lq*R.from_quat(bind[lo,3:7]).inv()
            residual=R.from_quat(w[h,3:7])*(delta*R.from_quat(bind[h,3:7])).inv()
            q=residual.as_quat()
            palm.append(2*np.arctan2(np.dot(q[:3],f),q[3]))
        palm=np.unwrap(palm)
        reference=twist_anchor[side] if twist_anchor else (palm[0]+np.pi)%(2*np.pi)-np.pi
        palm+=2*np.pi*round((reference-palm[0])/(2*np.pi))
        anchors[side]=float(palm[-1])
        for j,w in enumerate(worlds):
            u=unit(w[lo,:3]-w[up,:3]);f=unit(w[h,:3]-w[lo,:3])
            # Shoulder-side support remains authored; roll ramps into the elbow.
            # At the other end V9 twist_01 retains the wrist roll, twist_02 halves it.
            for bone,axis,angle in [(up,u,angles[j,0]),
                    (index['upperarm_twist_02_'+side],u,angles[j,0]),
                    (lo,f,angles[j,1])]:
                corrected[j,bone,3:7]=(R.from_rotvec(axis*angle*active[j])*R.from_quat(w[bone,3:7])).as_quat()
            lq=R.from_rotvec(f*angles[j,1])*R.from_quat(w[lo,3:7])
            delta=lq*R.from_quat(bind[lo,3:7]).inv()
            for suffix,fraction in [('01',1.),('02',.5)]:
                bone=index['lowerarm_twist_'+suffix+'_'+side]
                goal=R.from_rotvec(f*palm[j]*fraction)*delta*R.from_quat(bind[bone,3:7])
                original=R.from_quat(w[bone,3:7])
                change=(goal*original.inv()).as_rotvec()
                corrected[j,bone,3:7]=(R.from_rotvec(change*active[j])*original).as_quat()
        after=np.array([hinge_angles(w,bind,(up,lo,h))[0] for w in corrected])
        full=active>.999
        metrics[side]=dict(before_hinge_error_deg=float(np.degrees(abs(angles[full])).max()) if full.any() else 0,
                           after_hinge_error_deg=float(np.degrees(abs(after[full])).max()) if full.any() else 0,
                           max_roll_deg=float(np.degrees(abs(angles)).max()))
    # Re-express rotations against the corrected parent. Local translations and
    # scales stay byte-for-byte equal, and hands/fingers retain their world pose.
    result=frames.copy()
    for j,w in enumerate(corrected):
        for i,p in enumerate(parents):
            if p>=0:result[j,i,3:7]=(R.from_quat(w[p,3:7]).inv()*R.from_quat(w[i,3:7])).as_quat()
    return result,metrics,anchors

def continuous(frames):
    for i in range(1,len(frames)):
        q=frames[i,:,3:7];q[(frames[i-1,:,3:7]*q).sum(1)<0]*=-1
    return frames

def carry_weapon(frame,reference,data):
    names=data['names'];parents=data['parents']
    if 'WPN_root' not in names:return frame
    h=names.index('hand_r');k=names.index('WPN_root');p=parents[k]
    ref=world(reference,parents);pose=world(frame,parents)
    q0=R.from_quat(ref[h,3:7]);qh=R.from_quat(pose[h,3:7]);qp=R.from_quat(pose[p,3:7])
    offset=q0.inv().apply(ref[k,:3]-ref[h,:3])/ref[h,7:]
    target=pose[h,:3]+qh.apply(offset*pose[h,7:])
    frame[k,:3]=qp.inv().apply(target-pose[p,:3])/pose[p,7:]
    frame[k,3:7]=(qp.inv()*qh*q0.inv()*R.from_quat(ref[k,3:7])).as_quat()
    return frame

def combo(charge,release,idle,data):
    strike=PchipInterpolator([.36,.49,.54,.60,.72],[0,.10,.19,.24,20/60])
    result=[]
    for i in range(124):
        t=i/FPS
        # Direct, smooth lift into the accepted heavy-ready pose. Compressing
        # the entire charge also compressed its grip preparation into a jerk.
        if t<=.36:l=blend(idle,release[0],ease(t/.36))
        elif t<=.72:l=sample(release,float(strike(t)))
        elif t<=.82:l=release[20].copy()
        else:l=blend(release[20],idle,ease((t-.82)/1.03))
        result.append(carry_weapon(l,idle,data))
    result[0]=idle.copy();result[-1]=idle.copy()
    return np.array(result)

def main():
    from elbow_skin import fit_elbow_skin
    from pull_arm import repair_pull
    report={}
    for label in ('Jason','Kaitlin'):
        data=json.loads((P/(label+'-source.json')).read_text())
        source={k:np.array(v['frames']) for k,v in data['clips'].items()}
        output={};metrics={}
        anchor=None
        for role in ('DualCharge','DualRelease'):
            ts=np.arange(len(source[role]))/FPS
            weights=ease(ts/.36) if role=='DualCharge' else 1-ease((ts-68/60)/(28/60))
            output[role],metrics[role],anchor=repair(source[role],data,weights,anchor)
        output['Combo3']=combo(output['DualCharge'],output['DualRelease'],source['Idle'][0],data)
        skin_anchor=None
        for role,frames in output.items():
            ts=np.arange(len(frames))/FPS
            weights=ease(ts/.36) if role=='DualCharge' else 1-ease((ts-68/60)/(28/60)) if role=='DualRelease' else ease(ts/.36)*(1-ease((ts-.82)/1.03))
            output[role],next_anchor=fit_elbow_skin(frames,data,weights,skin_anchor if role=='DualRelease' else None)
            if role=='DualCharge':skin_anchor=next_anchor
        # The pull keeps its weapon target and clocks but uses a lowered,
        # continuous elbow arc, including the recovery into the idle pose.
        output['DualRelease'],metrics['pull']=repair_pull(output['DualRelease'],data,True)
        report[label]=metrics
        checks={}
        for role,frames in output.items():
            continuous(frames)
            if role in source:
                worst=0.;elbow_move=0.
                for a,b in zip(source[role],frames):
                    wa,wb=world(a,data['parents']),world(b,data['parents'])
                    ids=[data['names'].index(n) for n in ('hand_r','hand_l')]
                    worst=max(worst,float(np.linalg.norm(wa[ids,:3]-wb[ids,:3],axis=1).max()))
                    elbows=[data['names'].index(n) for n in ('lowerarm_r','lowerarm_l')]
                    elbow_move=max(elbow_move,float(np.linalg.norm(wa[elbows,:3]-wb[elbows,:3],axis=1).max()))
                primary=[data['names'].index(k+'_'+s) for s in ('r','l') for k in ('upperarm','lowerarm','hand')]
                checks[role]=dict(max_hand_position_change_cm=worst,elbow_reposition_cm=elbow_move,primary_local_translation_error=float(abs(source[role][:,primary,:3]-frames[:,primary,:3]).max()))
            output[role]=frames.round(9).tolist()
        report[label]['grip_preservation']=checks
        (P/(label+'-moves.json')).write_text(json.dumps(dict(mesh=data['mesh'],names=data['names'],fps=FPS,clips=output),separators=(',',':')),'utf8')
    (P/'authoring-report.json').write_text(json.dumps(report,indent=2),'utf8')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
