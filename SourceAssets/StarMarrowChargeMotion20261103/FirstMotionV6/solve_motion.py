"""First delivered sword track, rebuilt arm chains and a separate release/regrip arc."""
from pathlib import Path
import sys
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P.parent/'AuditV3'))
from motion_math import *
from scipy.interpolate import CubicSpline, PchipInterpolator
from scipy.spatial.transform import Slerp, RotationSpline
from scipy.optimize import minimize
sys.path.insert(0,str(P.parent/'RhythmV4'))
import rhythm
P=Path(__file__).resolve().parent
variant='LongGrip' if '--long-grip' in sys.argv else 'Standard'
source=json.loads((P/'first-version.json').read_text())
raw=source['variants'][variant]

def convert(local):
    w={}
    for n,v in zip(source['names'],local):w[n]=w.get(source['parents'][n],np.eye(4))@mat(v)
    return {n:A@w[n]@np.linalg.inv(nrest[n])@AI@rest[n] for n in names}

idle=convert(raw['idle']);original=[convert(row) for row in raw['frames']]
real=np.arange(round(rhythm.DURATION*rhythm.FPS)+1)/rhythm.FPS
phase=rhythm.SOURCE_TIME(real)
source_time=np.arange(len(original))/raw['fps']

def ease(a,b,t):return rhythm.ease(a,b,t)
def scal(m):return np.linalg.norm(m[:3,:3],axis=0)
def between(a,b):
    a,b=unit(a),unit(b);q=np.r_[np.cross(a,b),1.+a@b]
    if np.linalg.norm(q)<1e-8:return axis_angle(np.cross(a,[0,0,1]),np.pi)
    return R.from_quat(unit(q)).as_matrix()
def blend(a,b,w):return a@R.from_rotvec(R.from_matrix(a.T@b).as_rotvec()*w).as_matrix()
def local_of(pose):return {n:np.linalg.inv(pose[parents[n]])@pose[n] if parents[n] else pose[n] for n in names}
local_idle=local_of(idle);local_rest=local_of(rest)
grip={s:np.linalg.inv(idle['WPN_root'])@idle['hand_'+s] for s in ['l','r']}
q0=rotation(idle['WPN_root']);p0=idle['WPN_root'][:3,3];blade0=q0[:,2]

# Exact first-delivery component-space sword transforms, only retimed to the
# already installed 2.8 s clock. Neither hand solver can change this track.
wp=np.array([[np.interp(t,source_time,[m['WPN_root'][j,3] for m in original]) for j in range(3)] for t in phase])
wq=Slerp(source_time,R.from_matrix([rotation(m['WPN_root']) for m in original]))(phase).as_matrix()
lp_source=smooth([m['hand_l'][:3,3] for m in original],2.5)
lq_source=R.from_rotvec(smooth(R.from_matrix([rotation(m['hand_l']) for m in original]).as_rotvec(),2.5))
lp_curve=CubicSpline(source_time,lp_source)
lq_curve=Slerp(source_time,lq_source)
exec((P/'open_hand.py').read_text())

class Arm:
    def __init__(self,s):
        self.s=s;self.C='clavicle_'+s;self.U='upperarm_'+s;self.L='lowerarm_'+s;self.H='hand_'+s
        self.a=idle[self.U][:3,3];self.e0=idle[self.L][:3,3];self.h0=idle[self.H][:3,3]
        u0=self.e0-self.a;f0=self.h0-self.e0;n0=unit(np.cross(u0,f0))
        self.upper=np.linalg.norm(u0);self.fore=np.linalg.norm(f0)
        self.Bu=frame(u0,n0);self.Bl=frame(f0,n0)
        self.ru=rotation(idle[self.U]);self.rl=rotation(idle[self.L]);self.rel=self.rl.T@rotation(idle[self.H])
        self.axis=self.rl.T@unit(f0);self.reach0=unit(self.h0-self.a)
        self.pole0=unit(u0-self.reach0*(u0@self.reach0))
        self.wrist_axis=rotation(rest[self.H]).T@unit(rest[self.H][:3,3]-rest[self.L][:3,3])
        self.neutral=between(self.rel@self.wrist_axis,self.axis)@self.rel
    def shoulder(self,t):
        w=ease(.035,.27,t)*(1.-ease(.70,1.25,t))
        turn=np.radians(-31. if self.s=='l' else 15.)*w
        cq=axis_angle([0,0,1],turn)
        c=idle[self.C].copy();c[:3,:3]=cq@c[:3,:3]
        a=c[:3,3]+cq@(self.a-idle[self.C][:3,3])
        return a,c
    def elbow(self,h,a,phi):
        reach=np.linalg.norm(h-a);direction=unit(h-a)
        along=(self.upper**2-self.fore**2+reach**2)/(2*reach)
        radius=np.sqrt(max(0.,self.upper**2-along**2))
        pole=between(self.reach0,direction)@self.pole0
        e=a+direction*along+axis_angle(direction,phi)@pole*radius
        u=e-a;f=h-e;n=unit(np.cross(u,f))
        return e,frame(u,n)@self.Bu.T@self.ru,frame(f,n)@self.Bl.T@self.rl
    def angles(self,h,e,l,q):
        bend=np.arccos(np.clip(unit(h-e)@(q@self.wrist_axis),-1.,1.))
        turn=twist(l.T@q@self.rel.T,self.axis)
        return bend,turn
    def bounded_palm(self,l,q,weight):
        delta=l.T@q@self.neutral.T;tau=twist(delta,self.axis)
        swing=delta@axis_angle(self.axis,-tau)
        v=R.from_matrix(swing).as_rotvec();v*=min(1.,np.radians(32.)/max(np.linalg.norm(v),1e-9))
        target=R.from_rotvec(v).as_matrix()@axis_angle(self.axis,np.clip(tau,-np.radians(90.),np.radians(90.)))@self.neutral
        return l@blend(self.rel,target,weight)

arms={s:Arm(s) for s in ['l','r']}

# Roll the normal grip around the handle; its thumb-to-guard direction never
# reverses. This allows the FIRST sword angle without folding the right wrist.
arm=arms['r'];last=np.zeros(2);solved={'r':[],'l':[]};metrics={'r':[],'l':[]}
grip_roll=[];right_phi=[]
def grip_clearance(t):return ease(.015,.18,t)*(1.-ease(1.18,1.64,t))
for k,t in enumerate(phase):
    a,c=arm.shoulder(t);w=ease(.015,.17,t)*(1.-ease(1.20,1.68,t))
    def state(x):
        roll,phi=x;roll*=w;phi*=w
        spin=axis_angle([0,0,1],roll)
        gp=grip['r'][:3,3].copy();gp[:2]*=1.+.035*np.sin(roll)**2
        gp[2]-=.025*grip_clearance(t)
        h=wp[k]+wq[k]@spin@gp;q=wq[k]@spin@rotation(grip['r'])
        e,u,l=arm.elbow(h,a,phi);bend,tau=arm.angles(h,e,l,q)
        return h,q,e,u,l,bend,tau
    def cost(x):
        h,q,e,u,l,bend,tau=state(x)
        return (.18*bend*bend+12.*max(0.,bend-np.radians(27.))**2+.025*tau*tau
            +.018*x[0]**2+.018*x[1]**2+.08*np.sum((x-last)**2)
            +max(0.,.09-e[1])**2*180.+max(0.,.29-e[0])**2*30.)
    opt=minimize(cost,last,method='L-BFGS-B',bounds=[(-2.8,2.8),(-1.8,1.8)])
    last=opt.x;grip_roll.append(last[0]*w);right_phi.append(last[1]*w)
grip_roll=smooth(grip_roll,1.25);right_phi=smooth(right_phi,1.25)
for k,t in enumerate(phase):
    a,c=arm.shoulder(t);roll=grip_roll[k];spin=axis_angle([0,0,1],roll)
    gp=grip['r'][:3,3].copy();gp[:2]*=1.+.035*np.sin(roll)**2
    gp[2]-=.025*grip_clearance(t)
    h=wp[k]+wq[k]@spin@gp;q=wq[k]@spin@rotation(grip['r'])
    e,u,l=arm.elbow(h,a,right_phi[k]);bend,tau=arm.angles(h,e,l,q)
    solved['r'].append((a,c,h,e,u,l,q,tau))
    metrics['r'].append(dict(wrist_deg=float(np.degrees(bend)),twist_deg=float(np.degrees(tau)),grip_roll_deg=float(np.degrees(roll))))

# Keep the first palm-up caress. The left hand leaves early enough that the
# rising blade/guard cannot sweep through it, then circles the pommel from left.
park=idle['hand_l'][:3,3]+[-.19,-.055,-.025]
left_pos=[];left_rot=[];contact_weights=[]
recovery_times=[.66,.78,.92,1.10,1.26,1.43,1.58,1.7]
def near(t):return int(np.argmin(abs(phase-t)))
def held(t):
    k=near(t);return wp[k]+wq[k]@grip['l'][:3,3]
withdraw=CubicSpline(recovery_times,[lp_curve(.66)+[-.02,-.035,-.025],
    lp_curve(.66)+[-.12,-.10,-.065],park+[-.015,0,-.035],park,
    held(1.26)+[-.13,-.075,-.045],held(1.43)+[-.075,-.045,-.025],
    held(1.58)+[-.018,-.01,-.005],idle['hand_l'][:3,3]],bc_type='clamped')
entry=CubicSpline([0.,.035,.12,.23,.34,.43],
    [idle['hand_l'][:3,3],idle['hand_l'][:3,3]+[-.025,-.015,-.012],
     park+[-.01,0,.02],park+[-.025,.035,.04],
     lp_curve(.43)+[-.10,-.08,-.06],lp_curve(.43)+[-.02,-.035,-.025]],bc_type='clamped')
for k,t in enumerate(phase):
    contact=ease(.08,.28,t)*(1.-ease(.66,.84,t))
    if t<.43:
        p=entry(t)
        if t>.34:p=p*(1.-ease(.34,.43,t))+(lp_curve(t)+[-.02,-.035,-.025])*ease(.34,.43,t)
    elif t<=.66:
        p=lp_curve(t)+np.array([-.02,-.035,-.025])*ease(.04,.25,t)
    else:p=withdraw(t)
    holdq=wq[k]@rotation(grip['l'])
    q=lq_curve(min(t,.66)).as_matrix()
    if t<.43:q=blend(rotation(idle['hand_l']),q,ease(.12,.43,t))
    # Reset to the accepted idle palm during the clear withdrawal; follow the
    # moving handle only once the left hand is outside the guard's swept volume.
    if t>.66:q=blend(q,rotation(idle['hand_l']),ease(.68,1.02,t))
    if t>1.15:q=blend(q,holdq,ease(1.15,1.60,t))
    left_pos.append(p);left_rot.append(q);contact_weights.append(contact)
left_pos=np.array(left_pos);left_rot=np.array(left_rot)
arm=arms['l']
for k,t in enumerate(phase):
    a,c=arm.shoulder(t);h=left_pos[k].copy();q=left_rot[k]
    # Fixed bone lengths; a few centimetres of reachable palm arc replace the
    # old stretched upper/lower arms. Shoulder motion is in the clavicle chain.
    offset=h-a;limit=.94*(arm.upper+arm.fore)
    if np.linalg.norm(offset)>limit:h=a+unit(offset)*limit
    e,u,l=arm.elbow(h,a,-.40*ease(.05,.30,t)*(1.-ease(.74,1.35,t)))
    free=ease(.015,.15,t)*(1.-ease(1.33,1.70,t))
    q=arm.bounded_palm(l,q,free) if free>.00001 else blend(l@arm.rel,q,1.-free)
    # Regrip rotation approaches the accepted grasp rather than turning through
    # the full axial circle on recovery.
    if t>1.30:q=blend(q,wq[k]@rotation(grip['l']),ease(1.30,1.70,t))
    bend,tau=arm.angles(h,e,l,q)
    solved['l'].append((a,c,h,e,u,l,q,tau))
    metrics['l'].append(dict(wrist_deg=float(np.degrees(bend)),twist_deg=float(np.degrees(tau))))

for s in ['l','r']:
    turns=np.unwrap([v[-1] for v in solved[s]])
    solved[s]=[(*v[:-1],turns[k]) for k,v in enumerate(solved[s])]

rows=[]
for k,t in enumerate(phase):
    pose={n:m.copy() for n,m in idle.items()};pose['WPN_root']=make(wp[k],wq[k],scal(idle['WPN_root']))
    for s in ['l','r']:
        arm=arms[s];a,c,h,e,u,l,q,tau=solved[s][k];pose[arm.C]=c
        pose[arm.U]=make(a,u,scal(idle[arm.U]));pose[arm.L]=make(e,l,scal(idle[arm.L]));pose[arm.H]=make(h,q,scal(idle[arm.H]))
        for i,share in [('01',1.),('02',.5)]:
            n='upperarm_twist_'+i+'_'+s;pose[n]=pose[arm.U]@np.linalg.inv(idle[arm.U])@idle[n]
            n='lowerarm_twist_'+i+'_'+s;rel=np.linalg.inv(idle[arm.L])@idle[n]
            pose[n]=make((pose[arm.L]@np.r_[rel[:3,3],1])[:3],l@axis_angle(arm.axis,tau*share)@rotation(rel),scal(idle[n]))
        for n in names:
            digit=n.split('_')[0]
            if not n.endswith('_'+s) or digit not in ['thumb','index','middle','ring','pinky']:continue
            rel=local_idle[n].copy()
            if s=='l':
                delay={'thumb':0.,'index':.003,'middle':.006,'ring':.009,'pinky':.012}[digit]
                # Curl the fingertips while clear of the sword, before they
                # can sweep through the wider pommel on the regrip approach.
                close=.88*ease(.83+delay,1.12+delay,t)+.12*ease(1.43+delay,1.68+delay,t)
                open_weight=ease(.015+delay,.17+delay,t)*(1.-close)
                if n in open_local:rel[:3,:3]=blend(rotation(rel),rotation(open_local[n]),open_weight)*scal(rel)
                elif digit=='thumb':rel[:3,:3]=blend(rotation(rel),rotation(local_rest[n]),.65*open_weight)*scal(rel)
            pose[n]=pose[parents[n]]@rel
            if s=='r' and n=='thumb_01_r':
                # The factory thumb points into the crystal sword's guard.
                # Fold it around the handle while the support hand is free.
                current=rotation(pose[n])@unit(rotation(idle[n]).T@(idle['thumb_02_r'][:3,3]-idle[n][:3,3]))
                spin=axis_angle([0,0,1],grip_roll[k])
                target=wq[k]@spin@unit([.025,.028,-.002])
                correction=blend(np.eye(3),between(current,target),grip_clearance(t))
                pose[n][:3,:3]=correction@pose[n][:3,:3]
    rows.append(pose)
rows[0]={n:m.copy() for n,m in idle.items()};rows[-1]={n:m.copy() for n,m in idle.items()}
out=P/variant;out.mkdir(exist_ok=True)
(out/'poses.json').write_text(json.dumps(dict(variant=variant,fps=120,seconds=rhythm.DURATION,names=names,
    poses=[[row[n].tolist() for n in names] for row in rows],metrics=metrics),separators=(',',':')))
native_idle_world={}
for n,v in zip(source['names'],raw['idle']):native_idle_world[n]=native_idle_world.get(source['parents'][n],np.eye(4))@mat(v)
tracks={n:[] for n in names};previous={}
for row in rows:
    world={n:AI@row[n]@np.linalg.inv(rest[n])@A@nrest[n] for n in names}
    for n in names:
        pn=source['parents'][n];parent=world.get(pn,native_idle_world.get(pn,np.eye(4)))
        local=np.linalg.inv(parent)@world[n];q=R.from_matrix(rotation(local)).as_quat()
        if n in previous and q@previous[n]<0:q=-q
        previous[n]=q;tracks[n].append(dict(p=local[:3,3].tolist(),q=q.tolist(),s=scal(local).tolist()))
(out/'tracks.json').write_text(json.dumps(dict(fps=120,seconds=rhythm.DURATION,tracks=tracks),separators=(',',':')))
print('FIRST_MOTION_AUTHORED',variant,{s:{key:round(max(abs(m[key]) for m in metrics[s]),2) for key in metrics[s][0]} for s in ['l','r']},
    'return_turn_degrees',{s:round(float(np.degrees(solved[s][-1][-1])),3) for s in ['l','r']})
