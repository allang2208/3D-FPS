"""Fit wrists and skin twist with continuous, bounded elbow-plane motion."""
import json
import math
from pathlib import Path
import numpy as np

OUT=Path(__file__).resolve().parent
root=OUT.parent
# Reference/grip/skin math only: do not run V3's unbounded elbow optimizer.
helper=root/'ThirdPersonSwordGrip20261007/refine_kwang_grip.py'
ns={'__file__':str(helper)}
exec(compile(helper.read_text().split('clips={}')[0],str(helper),'exec'),ns)
source=json.loads((root/'ThirdPersonMeleeRegression20261010/adapted-actions.json').read_text())
names=source['names'];ix={n:i for i,n in enumerate(names)}
fk,fit=ns['fk'],ns['fit']
unit,rot,inv=ns['unit'],ns['rot'],ns['inv']
compose,target=ns['compose'],ns['target']
arms,lengths,ref=ns['arms'],ns['lengths'],ns['ref']
angles=np.radians(np.arange(-180.,180.,5.))
swivels=np.radians(np.arange(-60.,61.,5.))
N=len(angles)*len(swivels)
roll_index=np.repeat(np.arange(len(angles)),len(swivels))
swivel_index=np.tile(np.arange(len(swivels)),len(angles))
# Follow the fast blade turn without lagging the wrist; elbow remains bounded.
# Sparse transitions limit relative grip roll to 20 and swivel to 15 deg/60 Hz.
offsets=np.array([(a,s) for a in range(-4,5) for s in range(-3,4)])
pr=roll_index[:,None]+offsets[None,:,0]
ps=swivel_index[:,None]+offsets[None,:,1]
valid=(ps>=0)&(ps<len(swivels))
previous=(pr%len(angles))*len(swivels)+np.clip(ps,0,len(swivels)-1)
transition=2*np.radians(offsets[:,0]*5.)**2+3*np.radians(offsets[:,1]*5.)**2

def candidates(w,side,hand):
    a,b,c=arms[side];A=w[a,:3];C=hand[:3];l1,l2=lengths[side]
    ray=unit(C-A);distance=np.linalg.norm(C-A)
    along=(l1*l1-l2*l2+distance*distance)/(2*distance)
    pole=w[b,:3]-A;pole=unit(pole-ray*np.dot(pole,ray))
    radius=math.sqrt(max(0.,l1*l1-along*along))
    elbows=A+ray*along+radius*(np.cos(swivels)[:,None]*pole+np.sin(swivels)[:,None]*np.cross(ray,pole))
    desired=rot(hand[3:7],rot(inv(ref[c,3:7]),unit(ref[c,:3])))
    lower=C-elbows;lower/=np.maximum(np.linalg.norm(lower,axis=1)[:,None],1e-9)
    bends=np.arccos(np.clip(lower@desired,-1,1))
    return elbows,bends,max(0.,distance-(l1+l2)*.985)

clip=source['clips']['Overhead']
original=np.asarray(clip['frames']);world=[fk(f) for f in original]
weapons=[compose(w[ix['hand_r'],:7],ns['hand_to_weapon']) for w in world]
solutions={};report={}
for side in ('r','l'):
    scores=[];elbows=[];bends=[];old_bends=[]
    a,b,c=arms[side]
    for w,wp in zip(world,weapons):
        rows=[];points=[];br=[]
        desired=rot(w[c,3:7],rot(inv(ref[c,3:7]),unit(ref[c,:3])))
        old_bends.append(math.acos(np.clip(np.dot(unit(w[c,:3]-w[b,:3]),desired),-1,1)))
        for angle in angles:
            hand=target(wp,side,angle);E,bend,reach=candidates(w,side,hand)
            rows.extend(12*bend*bend+30*np.maximum(0.,bend-math.radians(45))**2+
                        5*swivels*swivels+.015*angle*angle+100*reach*reach)
            points.extend(E);br.extend(bend)
        scores.append(rows);elbows.append(points);bends.append(br)
    scores=np.asarray(scores);elbows=np.asarray(elbows);bends=np.asarray(bends)
    # Fit the ready/end pose too. Forcing the old zero grip angle reintroduces
    # the same wrist fold during entry and recovery. Runtime blends the curve.
    start=int(np.argmin(scores[0]));costs=np.full(N,np.inf);costs[start]=scores[0,start]
    local=np.array([rot(inv(w[ns['parents'][a],3:7]),E-w[a,:3])/lengths[side][0]
                    for w,E in zip(world,elbows)])
    links=[]
    for i in range(1,len(original)):
        move=local[i,:,None,:]-local[i-1,previous,:]
        matrix=costs[previous]+transition+18*np.sum(move*move,axis=2)
        matrix[~valid]=np.inf
        best=np.argmin(matrix,axis=1)
        links.append(previous[np.arange(N),best])
        costs=scores[i]+matrix[np.arange(N),best]
    path=[start]
    for prev in reversed(links):path.append(int(prev[path[-1]]))
    selected=np.asarray(path[::-1]);selected_elbows=elbows[np.arange(len(original)),selected]
    solutions[side]={'roll':np.unwrap(angles[roll_index[selected]]),'elbow':selected_elbows}
    new_bends=bends[np.arange(len(original)),selected]
    report[side]={'before_wrist_swing_max_degrees':float(np.degrees(max(old_bends))),
                  'after_wrist_swing_max_degrees':float(np.degrees(max(new_bends))),
                  'after_wrist_swing_p95_degrees':float(np.degrees(np.percentile(new_bends,95))),
                  'best_possible_wrist_swing_max_degrees':float(np.degrees(np.max(np.min(bends,axis=1)))),
                  'worst_frame':int(np.argmax(new_bends)),
                  'roll_endpoints_degrees':np.degrees(solutions[side]['roll'][[0,-1]]).tolist(),
                  'max_elbow_displacement_cm':float(np.max(np.linalg.norm(selected_elbows-np.array([w[b,:3] for w in world]),axis=1))),
                  'max_elbow_swivel_degrees':float(np.max(np.abs(np.degrees(swivels[swivel_index[selected]])))),
                  'max_roll_step_degrees':float(np.max(np.abs(np.degrees(np.diff(solutions[side]['roll'])))))}
result=[];max_contact=0.
for i,(f,w,wp) in enumerate(zip(original,world,weapons)):
    frame=f.copy()
    for side in ('r','l'):
        hand=target(wp,side,solutions[side]['roll'][i])
        fit(frame,w,side,hand,solutions[side]['elbow'][i])
    ww=fk(frame)
    for side in ('r','l'):
        hand=target(wp,side,solutions[side]['roll'][i])
        max_contact=max(max_contact,float(np.linalg.norm(ww[ix['hand_'+side],:3]-hand[:3])))
    result.append(frame.tolist())
result,dense_roll=ns['densify_contact'](result,np.degrees(solutions['r']['roll']).tolist())
clip['frames']=result
clip['rate']=120
roll=np.radians(dense_roll)
clip['curves']={'SwordGripRoll':np.degrees(roll).tolist(),
                'SwordGripRollSin':np.sin(roll).tolist(),'SwordGripRollCos':np.cos(roll).tolist()}
source['clips']={'Overhead':clip,'DashOverhead':clip}
source['provenance']+='; bounded elbow hemisphere and continuous wrist/grip fit'
report['max_wrist_target_error_cm']=max_contact
report['production_rate']=120
(OUT/'candidate-actions.json').write_text(json.dumps(source,separators=(',',':')))
(OUT/'candidate-contact.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
