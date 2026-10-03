"""Inspect the residual rapid elbow changes with the palm contacts fixed."""
import json
from pathlib import Path
import numpy as np
from scipy.ndimage import gaussian_filter1d
from scipy.spatial.transform import Rotation as R
HERE=Path(__file__).resolve().parent
before=json.loads((HERE/'Inputs/poses.json').read_text());after=json.loads((HERE/'SavedReadback/poses.json').read_text())
native=json.loads((HERE/'Inputs/BarePalmV7.json').read_text())['bones']
def unit(v):return v/np.linalg.norm(v)
def angle(a,b):return float(np.degrees(np.arccos(np.clip(unit(a)@unit(b),-1,1))))
def swing(a,b):return R.from_quat(unit(np.r_[np.cross(a,b),1+a@b]))
f0=unit(np.array(native['hand_l']['p'])-native['lowerarm_l']['p']);ref=R.from_quat(native['hand_l']['q']).inv()
report={}
for name in ['A_PKM_reload','A_PKM_reload_empty']:
    rows=after[name]['frames'];axes=[];radials=[];centers=[];radii=[];frames=[];phases=[]
    for row in rows:
        s,e,w=[np.array(row[n]['p']) for n in ['upperarm_l','lowerarm_l','hand_l']]
        axis=unit(w-s);d=np.linalg.norm(w-s);l1=np.linalg.norm(e-s);l2=np.linalg.norm(w-e)
        center=s+axis*(l1*l1-l2*l2+d*d)/(2*d);radial=e-center;radius=np.linalg.norm(radial)
        x=unit(radial) if not frames else swing(axes[-1],axis).apply(frames[-1][0]);y=np.cross(axis,x)
        phases.append(np.arctan2(radial@y,radial@x));frames.append((x,y));axes.append(axis);centers.append(center);radii.append(radius)
    phases=np.unwrap(phases);smoothed=gaussian_filter1d(phases,3,mode='nearest');candidate=[]
    for i,(row,phase) in enumerate(zip(rows,smoothed)):
        # Exact authored endpoints; the surrounding idle is already stationary.
        weight=min(1.,i/12.,(len(rows)-1-i)/12.);weight=weight*weight*(3-2*weight)
        phase=phases[i]+(phase-phases[i])*weight;x,y=frames[i]
        candidate.append(centers[i]+radii[i]*(np.cos(phase)*x+np.sin(phase)*y))
    stages={}
    for stage,elbows in [('original',[np.array(r['lowerarm_l']['p']) for r in before[name]['frames']]),
        ('joint49',[np.array(r['lowerarm_l']['p']) for r in rows]),('smoothed',candidate)]:
        upper=[];wrists=[]
        for i,(row,e) in enumerate(zip(rows,elbows)):
            s=np.array(row['upperarm_l']['p']);w=np.array(row['hand_l']['p']);hand=(R.from_quat(row['hand_l']['q'])*ref).apply(f0)
            upper.append(unit(e-s));wrists.append(angle(hand,w-e))
        steps=[angle(a,b) for a,b in zip(upper,upper[1:])]
        stages[stage]={'max_direction_step':max(steps),'max_step_frame':int(np.argmax(steps))+1,'max_wrist':max(wrists),
            'frame262_step':steps[261],'frame125_step':steps[124]}
    stages['extra_elbow_travel_cm']=float(max(np.linalg.norm(e-np.array(r['lowerarm_l']['p'])) for e,r in zip(candidate,rows)))
    report[name]=stages
(HERE/'elbow_continuity_inspection.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
