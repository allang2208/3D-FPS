"""Reuse the live M24 pull, finger curl and return, retargeting contact to M249.

The native rigs have the same anatomical bone axes but different root scales and
weapon frames. Keep one independent M249 clip for that skeleton boundary; deploy
and retract sample it in opposite directions. This is production fitting only.
"""
from pathlib import Path
import json,pickle,gzip,sys,numpy as np
from scipy.optimize import least_squares
from scipy.ndimage import gaussian_filter1d
from motion import *
from support_pose import apply_support
r=Path(__file__).resolve().parent;root=r.parent
d=pickle.load(open(r/'m24_inputs.pkl','rb'));m=pickle.load(open(r/'m249_inputs.pkl','rb'))
g=pickle.load(open(r/'geometry.pkl','rb'));names=m['names']
parents={n:(names[p] if p>=0 else None) for n,p in zip(names,m['parents'])}
B={n:matrix(v) for n,v in zip(names,m['bind'])}
local0={n:matrix(v) for n,v in zip(names,m['frames'][0])};home=compose(names,parents,local0)
parameters=json.loads((r/'hold_fit.json').read_text())['parameters']
home=apply_support(home,local0,names,parents,B,home,parameters)
local0={n:(np.linalg.inv(home[parents[n]])@home[n] if parents[n] else home[n].copy()) for n in names}
duration=.48;fps=200;times=np.arange(97)/fps
donor=[donor_pose(d,'bipod',t) for t in times];donor_home=donor_pose(d,'bipod',0)[0]
geo=json.loads((root/'Repair08/bipod_geometry.json').read_text());leg=geo['legs'][0]
pivot,tip,folded=[np.array(leg[k]) for k in ('pivot','tip','folded_tip')]
closed=swing(tip,folded);rootq=rot(B['WPN_root'])
raw=np.load(root/'Geometry/LegLeft.npz');rawp=raw['positions']
comp=np.c_[5.45+100*rawp[:,1],100*rawp[:,0]-28.6,100*rawp[:,2]-5.3]
rod=(comp-B['WPN_root'][:3,3])@rootq-pivot
tri=raw['faces'];edges=np.concatenate((tri[:,[0,1]],tri[:,[1,2]],tri[:,[2,0]]))
edge_a,edge_b=rod[edges[:,0]],rod[edges[:,1]]
handbones=[]
for n in names:
    p=n
    while p and p!='hand_l':p=parents[p]
    if p=='hand_l':handbones.append(n)
digits=[n for n in handbones if n.startswith(('thumb','index','middle','ring','pinky'))]
weaponbones=[]
for n in names:
    parent=n
    while parent and parent!='WPN_root':parent=parents[parent]
    if parent=='WPN_root':weaponbones.append(n)
# Seat the rod one finger segment deeper into the grasp, drawing the palm in.
contact_bone='middle_02_l'
index=names.index(contact_bone);vertices=np.array(g['vertices'])
ids=np.array([i for i,ws in enumerate(g['weights']) if sum(w for j,w in ws if j==index)>.72])
palmar=unit(B['middle_01_l'][:3,3]-B['hand_l'][:3,3]);across=unit(B['index_01_l'][:3,3]-B['pinky_01_l'][:3,3])
palmar=unit(np.cross(palmar,across))
if palmar@(B['middle_03_l'][:3,3]-B['middle_01_l'][:3,3])<0:palmar=-palmar
axis=unit(rot(B[contact_bone])[:,0]);v=vertices[ids]-B[contact_bone][:3,3]
axial=v@axis;lo,hi=np.quantile(axial,[.30,.72]);ids=ids[(axial>=lo)&(axial<=hi)]
v=vertices[ids]-B[contact_bone][:3,3];ids=ids[v@palmar>=np.quantile(v@palmar,.75)]
padP=np.c_[vertices[ids],np.ones(len(ids))]
padWeights={n:np.array([sum(w for j,w in g['weights'][i] if j==names.index(n)) for i in ids]) for n in handbones}
padWeights={n:w for n,w in padWeights.items() if w.max()>0}

def shaped_hand(h,loc,weight):
    out={'hand_l':h.copy()}
    for n in handbones:
        if n=='hand_l':continue
        child=local0[n].copy()
        if n in digits:child[:3,:3]=blend(rot(child),rot(loc[n]),weight)*np.linalg.norm(child[:3,:3],axis=0)
        out[n]=out[parents[n]]@child
    return out
def pad_point(h,loc):
    pose=shaped_hand(h,loc,1.);out=np.zeros((len(ids),3))
    for n,w in padWeights.items():out+=((padP@(pose[n]@np.linalg.inv(B[n])).T)[:,:3])*w[:,None]
    return out.mean(0)
def section_hit(section,rotation,approach):
    axis=unit(tip);center=axis*section;da=(edge_a-center)@axis;db=(edge_b-center)@axis
    cut=(da*db<=0)&(np.abs(da-db)>1e-9)
    pts=edge_a[cut]+(edge_b[cut]-edge_a[cut])*(da[cut]/(da[cut]-db[cut]))[:,None]
    # Fit the measured outer surface, never the rod center or bounding box.
    score=pts@(rotation.T@approach);return pts[np.argmax(score)]

import trimesh
rod_solid=trimesh.Trimesh(rod,tri,process=True)
rod_solid.fix_normals()
handset=set(handbones)
surface_ids=np.array([i for i,ws in enumerate(g['weights']) if sum(w for b,w in ws if names[b] in handset)>.98])
surfaceP=np.c_[vertices[surface_ids],np.ones(len(surface_ids))]
surfaceW={n:np.array([sum(w for b,w in g['weights'][i] if names[b]==n) for i in surface_ids]) for n in handbones}
surfaceW={n:w for n,w in surfaceW.items() if w.max()>0}
grip_clearance={float(k):v for k,v in json.loads((r/'authoring.json').read_text())['grip_clearance_cm'].items()} if '--reuse-contact' in sys.argv else {}
def fit_surface(h,loc,root,legq,approach,key):
    if key in grip_clearance:return grip_clearance[key]
    pose=shaped_hand(h,loc,1.);points=np.zeros((len(surface_ids),3))
    for n,w in surfaceW.items():points+=((surfaceP@(pose[n]@np.linalg.inv(B[n])).T)[:,:3])*w[:,None]
    rq=rot(root);points=((points-root[:3,3])@rq-pivot)@legq
    direction=approach@rq@legq
    def worst(offset):
        p=points+direction*offset
        near=((p>=rod_solid.bounds[0]-.2)&(p<=rod_solid.bounds[1]+.2)).all(1)
        return float(trimesh.proximity.signed_distance(rod_solid,p[near]).max()) if near.any() else -1.
    lo,hi=0.,.25
    if worst(0.)<=-.12:grip_clearance[key]=0.;return 0.
    while worst(hi)>-.12 and hi<4.:hi+=.25
    if worst(hi)>-.12:raise RuntimeError('Contact surface fit needs a different finger pose at '+str(key))
    for _ in range(9):
        mid=(lo+hi)*.5
        if worst(mid)>-.12:lo=mid
        else:hi=mid
    grip_clearance[key]=hi;return hi

poses=[];hands=[];shape_weights=[];mechanical=[]
for i,t in enumerate(times):
    source,_=donor[i];working=min(max(t,.12),.30);grasp,loc=donor_pose(d,'bipod',working);p={n:v.copy() for n,v in home.items()}
    # Retain the M24 pull; close the fingers slightly around the deeper contact.
    loc={n:v.copy() for n,v in loc.items()}
    for n in digits:loc[n]=mix(loc[n],local0[n],.50 if n.startswith('thumb') else .38)
    donor[i]=(source,loc)
    gunmove=np.eye(4);gunmove[:3,:3]=rot(source['WPN_root'])@rot(donor_home['WPN_root']).T
    gunmove[:3,3]=(source['WPN_root'][:3,3]-donor_home['WPN_root'][:3,3])*100
    # Preserve the M24 held-gun pullback while retaining M249's idle grips.
    for n in weaponbones:p[n]=gunmove@home[n]
    right=p['WPN_root']@np.linalg.inv(home['WPN_root'])@home['hand_r']
    weight=float(ease((t-.045)/.075)*(1-ease((t-.325)/.075)))
    opened=float(ease((t-.06)/.06)*(1-ease((t-.33)/.05)))
    orientation=rot(grasp['hand_l'])
    # One reversible phase drives both hands and legs at the M249 runtime speed.
    phase=float(np.clip((t-.12)/.18,0,1));legq=blend(closed,np.eye(3),smooth(phase))
    mountq=rot(p['WPN_root']);legrotation=mountq@legq
    section=10.5-1.0*(1-smooth((t-.12)/.09))
    h=np.eye(4);h[:3,:3]=orientation*np.linalg.norm(home['hand_l'][:3,:3],axis=0)
    # Palmar direction from the posed fingers gives the outer approach direction.
    shaped=shaped_hand(h,loc,1.)
    forward=unit(shaped['middle_01_l'][:3,3]-shaped['hand_l'][:3,3])
    lateral=unit(shaped['index_01_l'][:3,3]-shaped['pinky_01_l'][:3,3])
    normal=unit(np.cross(forward,lateral))
    if normal@(shaped['middle_03_l'][:3,3]-shaped['middle_01_l'][:3,3])<0:normal=-normal
    rodaxis=legrotation@unit(tip);approach=-unit(normal-rodaxis*(normal@rodaxis))
    hit=p['WPN_root'][:3,3]+mountq@pivot+legrotation@section_hit(section,legrotation,approach)
    h[:3,3]=hit+approach*.18-pad_point(h,loc)
    h[:3,3]+=approach*fit_surface(h,loc,p['WPN_root'],legq,approach,round(working,4))
    origin=gunmove@home['hand_l'];escape=origin[:3,3]+np.array([-8.5,0.,-7.])
    if t<.025:at=origin[:3,3]
    elif t<.06:at=(1-smooth((t-.025)/.035))*origin[:3,3]+smooth((t-.025)/.035)*escape
    elif t<.12:at=(1-smooth((t-.06)/.06))*escape+smooth((t-.06)/.06)*h[:3,3]
    elif t<=.30:at=h[:3,3]
    elif t<.34:at=h[:3,3]+approach*(6.*smooth((t-.30)/.04))
    elif t<.385:at=(1-smooth((t-.34)/.045))*(h[:3,3]+approach*6.)+smooth((t-.34)/.045)*(origin[:3,3]+np.array([-8.5,-3.,-3.]))
    else:at=(1-smooth((t-.385)/.055))*(origin[:3,3]+np.array([-8.5,-3.,-3.]))+smooth((t-.385)/.055)*origin[:3,3]
    at+=np.array([-.12,0.,0.])*float(ease(t/.025)*(1-ease((t-.44)/.04)))*(1-opened)
    target=mix(origin,h,weight);target[:3,3]=at
    hands.append({'l':target,'r':right});poses.append(p);shape_weights.append(opened)
    mechanical.append(dict(time=float(t),open_phase=phase,leg_rotation=R.from_matrix(legq).as_quat().tolist()))

def solve_arm(side):
    upper,lower,wrist=[n+'_'+side for n in ('upperarm','lowerarm','hand')]
    a0,e0,h0=[home[n][:3,3] for n in (upper,lower,wrist)];la=np.linalg.norm(e0-a0);lb=np.linalg.norm(h0-e0)
    u0=B[lower][:3,3]-B[upper][:3,3];f0=B[wrist][:3,3]-B[lower][:3,3];hinge0=unit(np.cross(u0,f0));ff=frame(f0,hinge0)
    controls=[];previous=np.zeros(4);rolls=[];reference=0.
    def solve(i,x,ref):
        h=hands[i][side];at=h[:3,3];a=a0+x[:3];axis=unit(at-a);distance=np.linalg.norm(at-a)
        bounded=np.clip(distance,abs(la-lb)+2.,(la+lb)*.965);a+=axis*(distance-bounded);distance=bounded
        pole=unit(e0-a0);pole=unit(pole-axis*(pole@axis));pole=turn(axis,x[3])@pole
        along=(la*la-lb*lb+distance*distance)/(2*distance);e=a+axis*along+pole*np.sqrt(max(0,la*la-along*along))
        u,f=e-a,at-e;hinge=unit(np.cross(u,f));bend=np.degrees(np.arccos(np.clip(unit(u)@unit(f),-1,1)))
        crease=smooth((bend-30)/40);neutral=turn(f,np.radians(20 if side=='l' else -20)*crease)@frame(f,hinge)@ff.T
        palm=rot(h)@rot(B[wrist]).T;distal=swing(palm@f0,f)@palm
        q=R.from_matrix(distal@neutral.T).as_quat();roll=2*np.arctan2(q[:3]@unit(f),q[3]);roll+=2*np.pi*round((ref-roll)/(2*np.pi))
        return a,e,at,neutral,palm,roll
    for i,t in enumerate(times):
        def residual(x):
            a,e,h,neutral,palm,roll=solve(i,x,reference);wrist_angle=np.arccos(np.clip(unit(h-e)@unit(palm@f0),-1,1))
            return np.r_[max(0,wrist_angle-np.radians(35))/np.radians(4),(a-a0)/10.,(e-e0)/22.,
                (x-previous)/np.array([4.,4.,4.,.35]),x[3]/1.8,max(0,abs(roll)-np.radians(110))/np.radians(15),
                max(0,e[2]-h[2]+1)/3.,max(0,3.-a[1])/.4,max(0,a[2]+5.)/.5]
        fit=least_squares(residual,previous,bounds=([-14,-12,-16,-2.6],[14,16,10,2.6]),max_nfev=65)
        previous=fit.x;controls.append(previous.copy());reference=solve(i,previous,reference)[-1];rolls.append(reference)
    controls=gaussian_filter1d(np.array(controls),1.,axis=0,mode='nearest')
    for i,t in enumerate(times):
        activity=float(ease(t/.085)*(1-ease((t-.36)/.08)))
        x=controls[i]*activity;a,e,h,neutral,palm,roll=solve(i,x,rolls[i])
        # Keep the existing idle pose exactly at both handoff ends.
        p=poses[i];f=h-e;u=e-a;fore=np.clip(roll,-np.radians(110),np.radians(110))
        elbow=turn(f,roll-fore)@neutral;upper_frame=swing(elbow@u0,u)@elbow
        p['clavicle_'+side]=home['clavicle_'+side].copy();p['clavicle_'+side][:3,3]+=a-a0
        for segment,origin,oldorigin,restaxis,axis,driver,homeaxis in (
            ('upperarm',a,B[upper][:3,3],u0,u,upper_frame,e0-a0),
            ('lowerarm',e,B[lower][:3,3],f0,f,elbow,h0-e0)):
            for suffix,share in (('',0.),('_twist_01',1.),('_twist_02',.5)):
                n=segment+suffix+'_'+side;offset=B[n][:3,3]-oldorigin;station=offset@restaxis/(restaxis@restaxis)
                desired=(turn(f,fore*share)@driver if segment=='lowerarm' else driver)@rot(B[n])
                carried=swing(homeaxis,axis)@rot(home[n]);rotation=blend(carried,desired,activity)
                delta=rotation@rot(B[n]).T
                p[n]=home[n].copy();p[n][:3,:3]=rotation*np.linalg.norm(home[n][:3,:3],axis=0)
                p[n][:3,3]=origin+station*axis+delta@(offset-station*restaxis)
        p[wrist]=hands[i][side]
        for n in names:
            if n.endswith('_'+side) and n.startswith(('thumb','index','middle','ring','pinky')):
                child=local0[n].copy()
                if side=='l':
                    # Release the wrap before translating away; reverse this at
                    # the return contact instead of dragging curled fingertips.
                    release=float(ease(t/.025)*(1-ease((t-.44)/.04)))
                    relaxed=rot(child)
                    if 'metacarpal' not in n:
                        degrees=(-25. if '_01_' in n else 15.) if n.startswith('thumb') else 30. if '_03_' not in n else 20.
                        relaxed=turn([0,0,1],np.radians(degrees)*release)@relaxed
                    child[:3,:3]=blend(relaxed,rot(donor[i][1][n]),shape_weights[i])*np.linalg.norm(child[:3,:3],axis=0)
                p[n]=p[parents[n]]@child
        if 'ik_hand_'+side in p:p['ik_hand_'+side]=p[wrist]@np.linalg.inv(home[wrist])@home['ik_hand_'+side]
    return controls.tolist()
controls={side:solve_arm(side) for side in ('l','r')}
poses[0]={n:v.copy() for n,v in home.items()};poses[-1]={n:v.copy() for n,v in home.items()}
tracks={};world=np.array([[p[n] for n in names] for p in poses])
for n in names:
    values=[];previous=None
    for p in poses:
        a=np.linalg.inv(p[parents[n]])@p[n] if parents[n] else p[n];q=R.from_matrix(rot(a)).as_quat()
        if previous is not None and q@previous<0:q=-q
        previous=q;values.append([*a[:3,3],*q,*np.linalg.norm(a[:3,:3],axis=0)])
    tracks[n]=values
with gzip.open(r/'bipod.pending.gz','wt') as f:json.dump(dict(fps=fps,duration=duration,tracks=tracks),f,separators=(',',':'))
(r/'bipod.pending.gz').replace(r/'bipod.json.gz')
with (r/'authored_world.pkl').open('wb') as f:pickle.dump(dict(names=names,times=times,world=world),f)
(r/'authoring.json').write_text(json.dumps(dict(source=d['bipod']['path'],source_profile='/Game/Weapons/M24/MotionPolish20261027/DA_M24_SupportGrip',
    native_mesh='/Game/Weapons/M249/SK_M249_V7',skeleton_exception='M24 and PKM-native M249 use different root frames and native scale',
    duration=duration,runtime_duration=.90,grip_contact=.225,pull_complete=.5625,hand_returned=.825,near_leg='A',
    contact_bone=contact_bone,pad_vertices=ids.tolist(),section_cm=[9.5,10.5],grip_clearance_cm=grip_clearance,controls=controls,mechanical=mechanical,runtime_tested=False),indent=2))
print('M249_BIPOD_AUTHORED',len(poses),'native poses; M24 live contact source',flush=True)
