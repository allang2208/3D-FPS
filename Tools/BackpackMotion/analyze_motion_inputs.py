"""Numerical input-response diagnosis from sampled source animations, not a game render."""
import json,math
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation,Slerp
R=Path('D:/FPS3D/FPSGAME/Saved/SlingMotionDiagnosis20261022')
clips=json.loads((R/'animation_inputs.json').read_text());report=[]
for name,clip in clips.items():
    times=np.array([r['time'] for r in clip['samples']]);positions=np.array([r['position'] for r in clip['samples']])
    rotations=Rotation.from_quat([r['rotation'] for r in clip['samples']]);slerp=Slerp(times,rotations)
    for fps in [8,15,30,60]:
        dt=1/fps;rate=1.5 if '.Walk.' in name else 1.2
        sample=np.arange(0,clip['length']/rate,dt)*rate
        pts=np.column_stack([np.interp(sample,times,positions[:,axis]) for axis in range(3)])
        rots=slerp(sample)
        for mode in ['before','after']:
            frequency,damping,angle,scale,bounce,reset=(3.8,.9,2.4,1.,.3,.1) if mode=='before' else (3.,.78,3.2,3.,.5,.35)
            x=np.zeros(3);v=np.zeros(3);off=np.zeros(3);ov=np.zeros(3);av=np.zeros(3);angular=np.zeros(3);peak=height=0.;resets=0
            for i in range(1,len(pts)):
                if dt>reset:resets+=1;continue
                raw=(pts[i]-pts[i-1])/dt;filtered=av+(raw-av)*(1-math.exp(-24*dt));acc=(filtered-av)/dt;av=filtered
                acc*=min(1.,2200/max(np.linalg.norm(acc),1e-9))
                omega=(rots[i-1].inv()*rots[i]).as_rotvec()*180/math.pi/dt
                angular+=(omega-angular)*(1-math.exp(-18*dt))
                response=angle/2.4*scale
                target=(np.array([-acc[1]*.0012,acc[0]*.0012,0])-angular*.02)*response
                ot=np.array([-acc[0]*.00015,0,-acc[2]*.00045])*response
                steps=math.ceil(dt*120);step=dt/steps;w=2*math.pi*frequency
                for _ in range(steps):
                    v+=(w*w*(target-x)-2*damping*w*v)*step;x+=v*step
                    ov+=(w*w*(ot-off)-2*damping*w*ov)*step;off+=ov*step
                    limits=np.array([angle,angle*.8,angle*.7]);clamp=np.abs(x)>limits
                    x=np.clip(x,-limits,limits);v[clamp&(x*v>0)]=0
                    limits=np.array([.3,0,bounce]);clamp=np.abs(off)>limits
                    off=np.clip(off,-limits,limits);ov[clamp&(off*ov>0)]=0
                # Ignore initial velocity acquisition, use the running portion.
                if i*dt>.3:peak=max(peak,float(np.abs(x).max()));height=max(height,float(abs(off[2])))
            report.append({'animation':name,'fps':fps,'mode':mode,'peak_axis_angle_deg':round(peak,4),'peak_vertical_translation_cm':round(height,4),'reset_frames':resets})
(R/'response_comparison.json').write_text(json.dumps({'scope':'source torso animation input replay; no native pose graph, rendered view or gameplay acceptance','rows':report},indent=2))
for row in report:
    if row['fps'] in [8,60]:print(json.dumps(row))
