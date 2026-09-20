"""Fit the raised grip to the user's near-extended left-arm pose before baking."""
import json, math
from pathlib import Path
HERE=Path(__file__).resolve().parent
AUTHOR=HERE/'author_attack.py'
ns={'__file__':str(AUTHOR)}
exec(compile(AUTHOR.read_text(encoding='utf-8').split('\nreport = ')[0],str(AUTHOR),'exec'),ns)
rest=ns['rest']; frames=[]
for label,frame in [('raised',ns['RAISED']),('top',ns['TOP'])]:
    candidates=[]
    for roll in range(-160,1,5):
        ns['CFG']['top_grip_roll_degrees']['l']=roll
        pose=ns['pose_frame'](frame,.45,False,{})
        row={'grip_roll_l':roll,'arms':{}}
        for side in ('l','r'):
            U,F,H=[s+'_'+side for s in ('upperarm','lowerarm','hand')]
            shoulder,elbow,hand=[pose[b].translation for b in (U,F,H)]
            neutral=pose[H].to_quaternion()@rest[H].to_quaternion().inverted()@(rest[H].translation-rest[F].translation).normalized()
            row['arms'][side]={'hand':list(hand),'elbow':list(elbow),'shoulder':list(shoulder),
                'elbow_interior_degrees':math.degrees((shoulder-elbow).angle(hand-elbow)),
                'wrist_axis_degrees':math.degrees(neutral.angle((hand-elbow).normalized())),
                'reach_m':(hand-shoulder).length}
        l=row['arms']['l'];r=row['arms']['r']
        row['cost']=l['wrist_axis_degrees']**2+max(0,148-l['elbow_interior_degrees'])**2*2
        candidates.append(row)
    chosen=min(candidates,key=lambda c:c['cost'])
    frames.append({'phase':label,'choice':chosen})
(HERE/'overhead_pose_fit.json').write_text(json.dumps(frames,indent=2),encoding='utf-8')
print(json.dumps(frames),flush=True)

# Author the overhead elbow plane against the new horizontal handle, retaining
# the fitted grip and bone lengths instead of steering from wrist twist alone.
ns['CFG']['top_grip_roll_degrees']['l']=-85
plane_options=[[.5,-.65,-.4],[.9,-.4,-.2],[.6,-.25,-.8],[.25,-.15,-1.0],[.4,.15,-1.0],[.7,-.6,.2]]
plane_fit=[]
for guide in plane_options:
    ns['CFG']['elbow_pole_top']['l']=guide
    phases=[]
    for label,frame in [('raised',ns['RAISED']),('top',ns['TOP'])]:
        pose=ns['pose_frame'](frame,.45,False,{})
        shoulder,elbow,hand=[pose[b].translation for b in ('upperarm_l','lowerarm_l','hand_l')]
        neutral=pose['hand_l'].to_quaternion()@rest['hand_l'].to_quaternion().inverted()@(rest['hand_l'].translation-rest['lowerarm_l'].translation).normalized()
        phases.append({'phase':label,'elbow':list(elbow),'wrist_axis_degrees':math.degrees(neutral.angle((hand-elbow).normalized())),'neutral_forearm':list(neutral)})
    plane_fit.append({'guide':guide,'phases':phases})
(HERE/'overhead_plane_fit.json').write_text(json.dumps(plane_fit,indent=2),encoding='utf-8')
print(json.dumps(plane_fit),flush=True)
