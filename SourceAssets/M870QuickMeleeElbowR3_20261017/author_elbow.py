"""R3: one anatomical elbow hinge, native helper stations, bounded flexion.

Preserve installed palms, fingers, weapon and left arm. Author only the right
support and retain the actual shoulder-opening clearance used by R2.
"""
import json
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scipy.interpolate import PchipInterpolator
from scipy.spatial.transform import Rotation as R

O=Path(__file__).parent
prior=O.parent/'M870QuickMeleeR2_20261017/author_right_arm.py'
# Frozen R1/R2 helpers provide data-model pose decoding, the current hip camera,
# native skin constraints and track encoding. Their authoring passes are not run.
prefix=prior.read_text(encoding='utf-8').split('def axial_angle')[0]
exec(compile(prefix.replace('M870_R2_AUTHORING_SURFACE','M870_R3_AUTHORING_SURFACE'),str(prior),'exec'))

native={n:TC@m for n,m in bind.items()}
au,ef,hw=[native[n][:3,3] for n in ('upperarm_r','lowerarm_r','hand_r')]
ru,rf=ef-au,hw-ef
v7=json.loads((O.parent/'Super90QuickMelee20261008/LeftArmR5/v7_skin_basis.json').read_text())
mapping=json.loads((O.parent/'BenelliM4Super9020261006/authoring.json').read_text())
vr={n:np.array(m) for n,m in v7['rest'].items()}
vh=unit(np.cross(vr['lowerarm_r'][:3,3]-vr['upperarm_r'][:3,3],vr['hand_r'][:3,3]-vr['lowerarm_r'][:3,3]))
reflection=np.diag([1.,-1.,1.])

def skin_hinge(bone):
    # A hinge is an axial vector: Blender -> UE reflection changes its sign.
    h=-reflection@np.array(mapping['v7_to_native_warp'][bone])[:3,:3]@vh
    return unit(TC[:3,:3]@h)

FU=frame(ru,skin_hinge('upperarm_r'))
FF=frame(rf,skin_hinge('lowerarm_r'))
active=ease(times/.09)*(1-ease((times-.70)/.20))
maximum_flexion=np.deg2rad(135.)
maximum_pronation=np.deg2rad(110.)
write=['clavicle_r','upperarm_r','lowerarm_r','lowerarm_aux_r','lowerarm_twist_02_r','lowerarm_twist_01_r','hand_r']

def axial_angle(delta,axis):
    q=R.from_matrix(delta).as_quat()
    if q[3]<0:q=-q
    return 2*np.arctan2(q[:3]@unit(axis),q[3])

def solve_family(family):
    current=[{n:TC@m for n,m in p.items()} for p in decode(T,'melee',family)]
    idle={n:TC@m for n,m in decode(T,'idle',family)[0].items()}
    a0,e0,h0=[idle[n][:3,3] for n in ('upperarm_r','lowerarm_r','hand_r')]
    la,lb=np.linalg.norm(e0-a0),np.linalg.norm(h0-e0)
    minimum=np.sqrt(la*la+lb*lb+2*la*lb*np.cos(maximum_flexion))
    maximum=(la+lb)*.95

    def pose(i,x,roll_reference):
        original=current[i];p={n:m.copy() for n,m in original.items()}
        h=p['hand_r'][:3,3];a=p['upperarm_r'][:3,3]+x[:3]
        axis=unit(h-a);distance=np.linalg.norm(h-a)
        # Open a deeply folded elbow instead of trying to hide its collapse
        # with axial rotation. Both anatomical segment lengths are retained.
        target=np.clip(distance,minimum,maximum)
        a+=axis*(distance-target);distance=target
        pole=original['lowerarm_r'][:3,3]-a
        pole=unit(pole-axis*(pole@axis));pole=turn(axis,x[3])@pole
        along=(la*la-lb*lb+distance*distance)/(2*distance)
        e=a+axis*along+pole*np.sqrt(max(0.,la*la-along*along))
        upper,fore=e-a,h-e;hinge=unit(np.cross(upper,fore))
        du=frame(upper,hinge)@FU.T
        neutral=frame(fore,hinge)@FF.T
        palm=rot(p['hand_r'])@rot(native['hand_r']).T
        distal=swing(palm@rf,fore)@palm
        roll=axial_angle(distal@neutral.T,fore)
        roll+=2*np.pi*round((roll_reference-roll)/(2*np.pi))
        desired={n:m.copy() for n,m in original.items()}
        desired['clavicle_r'][:3,3]+=a-original['upperarm_r'][:3,3]
        desired['upperarm_r'][:3,3]=a
        desired['upperarm_r'][:3,:3]=du@rot(native['upperarm_r'])*np.linalg.norm(original['upperarm_r'][:3,:3],axis=0)
        for n in ('lowerarm_r','lowerarm_aux_r','lowerarm_twist_02_r','lowerarm_twist_01_r'):
            offset=native[n][:3,3]-ef;station=offset@rf/(rf@rf)
            # One shared proximal frame: no donor-relative roll is reapplied
            # independently to elbow/aux/twist bones. The real native stations
            # are elbow, 1/3 and 2/3; the distal station carries full palm roll.
            amount=np.clip(station/(2/3),0.,1.)
            driver=turn(fore,roll*amount)@neutral
            if n=='lowerarm_aux_r':driver=blend(du,neutral,.5)
            desired[n][:3,3]=e+station*fore+driver@(offset-station*rf)
            desired[n][:3,:3]=driver@rot(native[n])*np.linalg.norm(original[n][:3,:3],axis=0)
        w=active[i]
        for n in write[:-1]:
            p[n][:3,3]=(1-w)*original[n][:3,3]+w*desired[n][:3,3]
            p[n][:3,:3]=blend(rot(original[n]),rot(desired[n]),w)*np.linalg.norm(original[n][:3,:3],axis=0)
        return p,a,e,h,unit(palm@rf),roll

    knots=list(range(0,frames+1,2))
    if knots[-1]!=frames:knots.append(frames)
    controls=[];roll_controls=[];previous=np.zeros(4);reference=0.
    lower=np.array([-14.,-14.,-18.,-.85]);upper=-lower
    for i in knots:
        if active[i]<1e-8:
            controls.append(np.zeros(4));reference=pose(i,controls[-1],reference)[-1]
            roll_controls.append(reference);previous=controls[-1].copy();continue
        original=current[i];a_base=original['upperarm_r'][:3,3];e_base=original['lowerarm_r'][:3,3]
        guess=np.clip(previous,lower+1e-6,upper-1e-6)
        def residual(x):
            p,a,e,h,wrist_axis,roll=pose(i,x,reference)
            cut=skin_points(p,CUT);arm=skin_points(p,ARM)
            opening=np.maximum(0.,cut@corner_normal+corner_margin)*ease(cut[:,0]/5.)
            eye=np.maximum(0.,14.-np.linalg.norm(arm,axis=1))
            return np.r_[opening/.055,eye/.35,
                (unit(h-e)-wrist_axis)/.30,(a-a_base)/np.array([7.,7.,9.]),
                (e-e_base)/8.,x[3]/.55,(x-guess)/np.array([3.,3.,3.,.35]),
                max(0.,abs(roll)-maximum_pronation)/np.deg2rad(12.),
                max(0.,e[2]-h[2]+1.)/5.]
        solved=least_squares(residual,guess,bounds=(lower,upper),max_nfev=65,ftol=2e-5,xtol=2e-5,gtol=2e-5)
        controls.append(solved.x);previous=solved.x
        reference=pose(i,solved.x,reference)[-1];roll_controls.append(reference)
    dense=PchipInterpolator(times[knots],np.array(controls),axis=0)(times)
    rolls=PchipInterpolator(times[knots],np.array(roll_controls))(times)
    rows=[]
    for i,x in enumerate(dense):
        p=pose(i,x,rolls[i])[0]
        if i in (0,frames):p=current[i]
        component={n:TCi@m for n,m in p.items()}
        rows.append({n:pack(np.linalg.inv(component[parents[n]])@component[n] if parents[n] else component[n]) for n in names})
    print('M870_R3_ELBOW_AUTHORED',family,len(rows),'samples',flush=True)
    return rows,dict(shoulder_and_pole=dense.tolist(),forearm_roll=rolls.tolist())

base,controls=solve_family('base')
output=dict(revision='M870QuickMelee-AnatomicalElbow-R3-20261017',melee_path=T['melee']['path'],duration=duration,
    fps=fps,frames=frames,base_tracks=[track(n,[row[n] for row in base]) for n in names],profiles={},
    write_bones=write,ownership_curve=T['ownership_curve'],runtime_tested=False,visual_accepted=False)
all_controls={'base':controls};identity=np.array([0,0,0,0,0,0,1,0,0,0])
for family,spec in T['profiles'].items():
    rows,controls=solve_family(family);all_controls[family]=controls;tracks=[]
    for n in names:
        a=np.array([row[n] for row in base]);b=np.array([row[n] for row in rows])
        q=(R.from_quat(b[:,3:7])*R.from_quat(a[:,3:7]).inv()).as_quat();q[q[:,3]<0]*=-1
        delta=np.c_[b[:,:3]-a[:,:3],q,b[:,7:]-a[:,7:]]
        if np.max(np.abs(delta-identity))>1e-6:tracks.append(track(n,delta,True))
    output['profiles'][family]=dict(path=spec['path'],clip=dict(base=T['melee']['path'],duration=duration,tracks=tracks))
(O/'animation_patch.json').write_text(json.dumps(output,separators=(',',':')),encoding='utf-8')
(O/'authoring_controls.json').write_text(json.dumps(all_controls,separators=(',',':')),encoding='utf-8')
(O/'authoring.json').write_text(json.dumps(dict(revision=output['revision'],duration=duration,contact_seconds=1/6,
    skin_path=skin['path'],opening_vertices=len(cut_ids),opening_margin_cm=3.,viewport=[1467,751],vertical_fov=75.,
    maximum_authored_flexion_degrees=135.,pronation_preference_degrees=110.,
    method='Shared native skin hinge; elbow/aux free of palm roll; native forearm stations; open deep flexion; preserve R2 shoulder clearance',
    runtime_tested=False,visual_accepted=False),indent=2),encoding='utf-8')
