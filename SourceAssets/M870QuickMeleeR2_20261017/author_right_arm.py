"""R2: preserve the strike and both palms; keep the right shoulder opening offscreen.

Use the actual native skin as authoring constraints. Retain the SUPER90 R9 arm
roll with minimum-swing alignment instead of rebuilding the skin from an idle
elbow-plane frame. No render, gameplay run or acceptance test is performed.
"""
import json,gzip,copy
from collections import Counter
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
from scipy.interpolate import PchipInterpolator
from scipy.spatial.transform import Rotation as R

O=Path(__file__).parent;PREV=O.parent/'M870QuickMeleeSuper9020261017'
source=(PREV/'author_motion.py').read_text(encoding='utf-8').split('base,controls=solve_family')[0]
exec(compile(source,str(PREV/'author_motion.py'),'exec'))
# Helpers above use this script's directory, so D/T are the newly frozen R1
# installation and S is the currently installed SUPER90 donor.
m4={n:mat(v) for n,v in D['ruler_world'].items()}
target_axis=yaw@axis_frame(m4,np.array([0,0,1]))
reference_hand=np.array([0.,7.,-7.])+yaw@m4['hand_r'][:3,3]
TC,SC=camera(T,'m870'),camera(S,'super90');TCi=np.linalg.inv(TC)
with gzip.open(O/'native_skin.json.gz','rt',encoding='utf-8') as f:skin=json.load(f)
vertices=np.array(skin['vertices']);weights=skin['weights'];faces=np.array(skin['faces'],dtype=int)
bind={n:mat(v) for n,v in skin['rest'].items()};inverse_bind={n:np.linalg.inv(m) for n,m in bind.items()}
right_weight=np.array([sum(w for n,w in row.items() if n.endswith('_r')) for row in weights])
prox_weight=np.array([sum(row.get(n,0.) for n in ('clavicle_r','upperarm_r')) for row in weights])
arm_weight=np.array([sum(w for n,w in row.items() if n.endswith('_r') and n.startswith(('upperarm','lowerarm','clavicle'))) for row in weights])

# Weld coincident import seams for boundary selection. Only the proximal right
# skin opening is constrained; fingers, gun and unrelated model pieces are not.
_,weld=np.unique(np.round(vertices,4),axis=0,return_inverse=True)
edge_count=Counter()
for tri in faces:
    for a,b in zip(tri,np.roll(tri,-1)):
        a,b=int(weld[a]),int(weld[b])
        if a!=b:edge_count[tuple(sorted((a,b)))]+=1
boundary={n for edge,count in edge_count.items() if count==1 for n in edge}
cut_ids=np.array([i for i in range(len(vertices)) if weld[i] in boundary and prox_weight[i]>.05],dtype=int)
if not len(cut_ids):raise RuntimeError('No proximal right-arm boundary found in the native authoring surface')
arm_ids=np.flatnonzero(arm_weight>.75)[::24]
def groups(ids):
    v=np.c_[vertices[ids],np.ones(len(ids))];out={}
    for n in bind:
        ws=np.array([weights[i].get(n,0.) for i in ids]);active=np.flatnonzero(ws>0)
        if len(active):out[n]=(active,(v[active]@inverse_bind[n].T)*ws[active,None])
    return len(ids),out
CUT=groups(cut_ids);ARM=groups(arm_ids)
def skin_points(p,group):
    count,bones=group;out=np.zeros((count,3))
    for n,(ids,points) in bones.items():out[ids]+=(points@p[n].T)[:,:3]
    return out
tv=np.tan(np.deg2rad(75./2));th=tv*(1467/751)
# A plane beyond the bottom-right corner keeps the whole opening outside the
# supplied viewport while allowing a natural outward shoulder, not a forced
# low shoulder that would trade the visible hole for an over-bent wrist.
corner_normal=np.array([2.,-1/th,1/tv]);corner_margin=3.*np.linalg.norm(corner_normal)
print('M870_R2_AUTHORING_SURFACE',len(cut_ids),'opening vertices',len(arm_ids),'arm controls',flush=True)

def axial_angle(delta,axis):
    q=R.from_matrix(delta).as_quat()
    if q[3]<0:q=-q
    return 2*np.arctan2(q[:3]@unit(axis),q[3])

def fit_family(family):
    idle={n:TC@m for n,m in decode(T,'idle',family)[0].items()}
    current=[{n:TC@m for n,m in p.items()} for p in decode(T,'melee',family)]
    donors=[{n:SC@m for n,m in p.items()} for p in decode(S,'melee',family)]
    a0,e0,h0=[idle[n][:3,3] for n in ('upperarm_r','lowerarm_r','hand_r')]
    u0,f0=e0-a0,h0-e0;la,lb=np.linalg.norm(u0),np.linalg.norm(f0)
    donor_inverse={n:rot(donors[0][n]).T for n in ('upperarm_r','lowerarm_r','lowerarm_twist_02_r','lowerarm_twist_01_r')}
    roll_names=('lowerarm_r','lowerarm_twist_02_r','lowerarm_twist_01_r')
    def pose(i,x,roll_reference):
        p={n:m.copy() for n,m in current[i].items()};h=p['hand_r'][:3,3]
        a=x[:3].copy();axis=unit(h-a);distance=np.linalg.norm(h-a)
        reach=(la+lb)*.96
        if distance>reach:a+=axis*(distance-reach);distance=reach
        minimum=abs(la-lb)+.02
        if distance<minimum:a-=axis*(minimum-distance);distance=minimum
        ref=current[i]['lowerarm_r'][:3,3]-a
        pole=unit(ref-axis*(ref@axis));pole=turn(axis,x[3])@pole
        along=(la*la-lb*lb+distance*distance)/(2*distance)
        e=a+axis*along+pole*np.sqrt(max(0.,la*la-along*along))
        upper,fore=e-a,h-e
        # Borrow the donor's axial rotation; only swing its segment to the new
        # M870 target. This avoids a changing elbow cross product rolling skin.
        du=rot(donors[i]['upperarm_r'])@donor_inverse['upperarm_r']
        du=swing(du@u0,upper)@du
        palm=rot(p['hand_r'])@rot(idle['hand_r']).T
        distal=swing(palm@f0,fore)@palm
        rolls={}
        def fore_driver(n,amount):
            d=rot(donors[i][n])@donor_inverse[n];d=swing(d@f0,fore)@d
            roll=axial_angle(distal@d.T,fore)
            roll+=2*np.pi*round((roll_reference[n]-roll)/(2*np.pi))
            rolls[n]=roll
            return turn(fore,roll*amount)@d
        proximal=fore_driver('lowerarm_r',.35)
        p['clavicle_r'][:3,3]+=a-current[i]['upperarm_r'][:3,3]
        p['upperarm_r'][:3,3]=a;p['upperarm_r'][:3,:3]=du@idle['upperarm_r'][:3,:3]
        for n in ('lowerarm_r','lowerarm_aux_r','lowerarm_twist_02_r','lowerarm_twist_01_r'):
            offset=idle[n][:3,3]-idle['lowerarm_r'][:3,3];station=offset@f0/(f0@f0)
            if n=='lowerarm_aux_r':driver=blend(du,proximal,.5)
            elif n=='lowerarm_r':driver=proximal
            else:driver=fore_driver(n,.35+.65*ease(station/(2/3)))
            p[n][:3,3]=e+station*fore+driver@(offset-station*f0)
            p[n][:3,:3]=driver@idle[n][:3,:3]
        return p,a,e,h,unit(palm@f0),distance/(la+lb),rolls

    # Continuous authoring controls; no per-frame fallback or position snapping.
    knots=list(range(0,frames+1,2))
    if knots[-1]!=frames:knots.append(frames)
    controls=[];roll_controls=[];previous=None;roll_reference={n:0. for n in roll_names}
    lower=np.array([-40.,-8.,-72.,-1.5]);upper=np.array([48.,58.,10.,1.5])
    for i in knots:
        base=current[i]['upperarm_r'][:3,3]
        if i in (0,frames):
            controls.append(np.r_[base,0.]);previous=controls[-1].copy()
            roll_reference=pose(i,previous,roll_reference)[-1]
            roll_controls.append([roll_reference[n] for n in roll_names]);continue
        old_e=current[i]['lowerarm_r'][:3,3]
        guess=np.r_[base,0.] if previous is None else previous.copy()
        if previous is not None:
            prior=knots[knots.index(i)-1]
            guess[:3]+=base-current[prior]['upperarm_r'][:3,3]
        guess=np.clip(guess,lower+1e-5,upper-1e-5)
        def residual(x):
            p,a,e,h,desired,reach,_=pose(i,x,roll_reference)
            cut=skin_points(p,CUT);arm=skin_points(p,ARM)
            front=ease(cut[:,0]/5.)
            opening=np.maximum(0.,cut@corner_normal+corner_margin)*front
            # Shoulder opening stays beyond the lower-right frame; skin near the eye must
            # not become a giant foreground patch while the hand stays fixed.
            eye=np.maximum(0.,14.-np.linalg.norm(arm,axis=1))
            current_bias=(a-base)/np.array([20.,14.,28.])
            temporal=(x-guess)/np.array([8.,8.,8.,.7])
            return np.r_[opening/.055,eye/.35,(unit(h-e)-desired)/.24,
                         current_bias,(e-old_e)/20.,x[3]/1.2,temporal,
                         max(0.,e[2]-h[2]+1.)/5.,max(0.,reach-.94)/.035]
        solved=least_squares(residual,guess,bounds=(lower,upper),max_nfev=65,ftol=2e-5,xtol=2e-5,gtol=2e-5)
        controls.append(solved.x);previous=solved.x
        roll_reference=pose(i,solved.x,roll_reference)[-1]
        roll_controls.append([roll_reference[n] for n in roll_names])
    dense=PchipInterpolator(times[knots],np.array(controls),axis=0)(times)
    dense_roll=PchipInterpolator(times[knots],np.array(roll_controls),axis=0)(times)
    rows=[]
    for i,x in enumerate(dense):
        p=pose(i,x,dict(zip(roll_names,dense_roll[i])))[0]
        if i in (0,frames):p=current[i]
        component={n:TCi@m for n,m in p.items()}
        rows.append({n:pack(np.linalg.inv(component[parents[n]])@component[n] if parents[n] else component[n]) for n in names})
    print('M870_R2_RIGHT_ARM_AUTHORED',family,len(rows),'samples',flush=True)
    return rows,dense.tolist()

base,controls=fit_family('base')
output=dict(revision='M870QuickMelee-RightArmOpening-R2-20261017',melee_path=T['melee']['path'],duration=duration,
            fps=fps,frames=frames,base_tracks=[track(n,[row[n] for row in base]) for n in names],profiles={},
            ownership_curve=T['ownership_curve'],runtime_tested=False,visual_accepted=False)
all_controls={'base':controls};identity=np.array([0,0,0,0,0,0,1,0,0,0])
for family,spec in T['profiles'].items():
    rows,controls=fit_family(family);all_controls[family]=controls;tracks=[]
    for n in names:
        a=np.array([row[n] for row in base]);b=np.array([row[n] for row in rows])
        q=(R.from_quat(b[:,3:7])*R.from_quat(a[:,3:7]).inv()).as_quat();q[q[:,3]<0]*=-1
        delta=np.c_[b[:,:3]-a[:,:3],q,b[:,7:]-a[:,7:]]
        if np.max(np.abs(delta-identity))>1e-6:tracks.append(track(n,delta,True))
    output['profiles'][family]=dict(path=spec['path'],clip=dict(base=T['melee']['path'],duration=duration,tracks=tracks))
(O/'animation_patch.json').write_text(json.dumps(output,separators=(',',':')),encoding='utf-8')
(O/'authoring_controls.json').write_text(json.dumps(all_controls,separators=(',',':')),encoding='utf-8')
(O/'authoring.json').write_text(json.dumps(dict(revision=output['revision'],duration=duration,contact_seconds=1/6,
    opening_vertices=len(cut_ids),opening_margin_cm=3.,viewport=[1467,751],vertical_fov=75.,skin_path=skin['path'],
    method='Native shoulder-boundary constraints; SUPER90 R9 minimum-swing arm roll; palms and strike preserved',
    authored_only=True,runtime_tested=False,visual_accepted=False),indent=2),encoding='utf-8')
