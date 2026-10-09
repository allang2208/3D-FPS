"""Choose an outside thumb contact whose full return does not wind the forearm."""
import json,math
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).parent;author=O.parent/'Super90Speedloader20261007/author_speedloader.py';s={'__file__':str(author)}
exec(compile(author.read_text().split('def local_rows(')[0],str(author),'exec'),s)
base=Matrix(s['hand_fit']['press_hand_in_idle']);pad=s['thumb_pad'];contact=base@pad;axis=s['right'];names=[n for n in s['names'] if 'arm' in n or n.startswith('hand_')]
rows=[]
for roll in range(-180,181,30):
    q=Quaternion(axis,math.radians(roll))@base.to_quaternion();hand=Matrix.LocRotScale(contact-q@pad,q,Vector((1,1,1)))
    s['hand_fit']['press_hand_in_idle']=[list(r) for r in hand];s['pose_cache'].clear()
    end_error=0.;max_step=0.;swing_max=0.
    for count in (1,7):
        prev=s['pose'](s['last_frame'](count),count,True)[0]
        for f in range(s['last_frame'](count)+1,s['duration'](count,True)+1):
            p=s['pose'](f,count,True)[0]
            for n in names:
                a=p[n].to_quaternion().rotation_difference(prev[n].to_quaternion()).angle;max_step=max(max_step,math.degrees(min(a,2*math.pi-a)))
            if f==s['last_frame'](count)+44:
                neutral=p['lowerarm_l'].to_quaternion()@s['rest']['lowerarm_l'].to_quaternion().inverted()@s['rest']['hand_l'].to_quaternion()
                dq=p['hand_l'].to_quaternion()@neutral.inverted();v=(p['hand_l'].translation-p['lowerarm_l'].translation).normalized();angle=2*math.atan2(Vector((dq.x,dq.y,dq.z)).dot(v),dq.w)
                a=(dq@Quaternion(v,angle).inverted()).angle;swing_max=max(swing_max,math.degrees(min(a,2*math.pi-a)))
            prev=p
        for n in names:
            a=p[n].to_quaternion().rotation_difference(s['idle'][n].to_quaternion()).angle;end_error=max(end_error,math.degrees(min(a,2*math.pi-a)))
    row={'roll':roll,'hand':[list(r) for r in hand],'max_step':max_step,'end_error':end_error,'contact_swing':swing_max}
    row['score']=end_error*1000+max(0,swing_max-45)**2*20+max_step+abs(roll)*.015
    rows.append(row);print('PRESS_TURN', {k:v for k,v in row.items() if k!='hand'},flush=True)
best=min(rows,key=lambda r:r['score']);out=json.loads((O/'hand_fit.json').read_text());out['press_hand_in_idle']=best['hand'];out['press_return_fit']={'selected':best,'candidates':rows}
(O/'hand_fit.json').write_text(json.dumps(out,indent=2));print('PRESS_TURN_SELECTED',best['roll'],best['end_error'],best['max_step'],flush=True)
