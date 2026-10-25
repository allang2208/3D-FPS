"""Lock retargeted female support to native wrist anchors without scaling bones."""
import copy,json,math
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R,Slerp
OUT=Path(__file__).resolve().parents[2]/'SourceAssets/FurnitureRest20261022'/globals().get('FURNITURE_REVISION','MeshyBedSupportedHands20261024')
KIND=globals().get('FURNITURE_KIND','Bed');TIME_OFFSET=globals().get('SUPPORT_TIME_OFFSET',0.)
START=globals().get('SUPPORT_START',4.7+TIME_OFFSET);END=globals().get('SUPPORT_END',6.6+TIME_OFFSET)
FADE_IN=globals().get('SUPPORT_FADE_IN',.45);FADE_OUT=globals().get('SUPPORT_FADE_OUT',.65)
ENTER='Rest.'+KIND+'.Enter';EXIT='Rest.'+KIND+'.Exit';CONTACT=round(START*30);RELEASE=round(END*30)+1
read=lambda p:json.loads(p.read_text());data=read(OUT/'kaitlin_arm_locals.json');native=read(OUT/'native_saved_samples.json')['kaitlin'];ix={n:i for i,n in enumerate(native['names'])}
local=np.asarray(data['clips'][ENTER]['frames']);world=np.asarray(native['clips'][ENTER]['world']);output=local.copy()
def unit(v):return v/max(np.linalg.norm(v),1e-9)
def basis(v,n):
    y=unit(v);z=unit(n-y*(y@n));return np.column_stack((np.cross(y,z),y,z))
def smooth(v):
    v=np.clip(v,0,1);return v**3*(v*(v*6-15)+10)
def between(a,b):
    a,b=unit(a),unit(b);cross=np.cross(a,b);length=np.linalg.norm(cross)
    return np.eye(3) if length<1e-8 else R.from_rotvec(cross/length*math.atan2(length,a@b)).as_matrix()
anchors={};previous={};diagnostics=[]
for side in ('l','r'):
    c=ix['hand_'+side];sample=world[CONTACT];anchor=np.median(world[CONTACT:RELEASE,c,:3],axis=0);anchor[2]=sample[c,2]
    hand_rotation=R.from_quat(sample[c,3:7]).as_matrix();forward=unit(sample[ix['middle_01_'+side],:3]-sample[c,:3]);across=sample[ix['index_01_'+side],:3]-sample[ix['pinky_01_'+side],:3];across=unit(across-forward*(across@forward))
    anchors[side]=(anchor,hand_rotation,hand_rotation.T@np.column_stack((across,forward,np.cross(across,forward))))
for j,frame in enumerate(world):
    t=j/30;weight=float(smooth((t-START+FADE_IN)/FADE_IN)*(1-smooth((t-END)/FADE_OUT)))
    if weight<=0:continue
    row={'time':t,'hands':{}}
    for side,sign,offset in [('l',1,0),('r',-1,3)]:
        a,b,c=[ix[n+'_'+side] for n in ('upperarm','lowerarm','hand')];shoulder,elbow,wrist=frame[[a,b,c],:3]
        rotations=[R.from_quat(frame[k,3:7]).as_matrix() for k in (a,b,c)]
        upper,lower=elbow-shoulder,wrist-elbow;l1,l2=np.linalg.norm(upper),np.linalg.norm(lower)
        target=wrist*(1-weight)+anchors[side][0]*weight;axis=unit(target-shoulder);distance=min(np.linalg.norm(target-shoulder),l1+l2-.15)
        hand=Slerp([0,1],R.from_matrix([rotations[2],anchors[side][1]]))(weight).as_matrix()
        palm=hand@anchors[side][2];across,forward,down=palm[:,0]*sign,palm[:,1],palm[:,2]*sign
        oldaxis=unit(wrist-shoulder);bend=between(oldaxis,axis)@unit(upper-oldaxis*(upper@oldaxis));normal=unit(np.cross(upper,lower))
        upper_c=basis(upper,normal).T@rotations[0];lower_c=basis(lower,normal).T@rotations[1]
        along=(l1*l1+distance*distance-l2*l2)/(2*distance);height=math.sqrt(max(0,l1*l1-along*along));end=shoulder+axis*distance;best=None
        prior=bend
        if side in previous:
            ps,pe,pw=previous[side];pa=unit(pw-ps);prior=between(pa,axis)@unit(pe-ps-pa*((pe-ps)@pa))
        for angle in np.linspace(-100,100,101):
            direction=R.from_rotvec(axis*math.radians(angle)).as_matrix()@bend;knee=shoulder+axis*along+direction*height;forearm=unit(end-knee)
            extension=math.degrees(math.atan2(forearm@down,forearm@forward));deviation=math.degrees(math.asin(np.clip(forearm@across,-1,1)))
            continuity=math.degrees(math.acos(np.clip(direction@prior,-1,1)))
            score=max(0,extension-71)**2*12+max(0,abs(deviation)-18)**2*8+angle*angle*.015+continuity*continuity*.25
            if best is None or score<best[0]:best=(score,knee,extension,deviation)
        knee=best[1];normal=unit(np.cross(knee-shoulder,end-knee));upper_rotation=basis(knee-shoulder,normal)@upper_c;lower_rotation=basis(end-knee,normal)@lower_c
        parent=rotations[0]@R.from_quat(local[j,offset,3:7]).as_matrix().T
        for k,rotation in enumerate((parent.T@upper_rotation,upper_rotation.T@lower_rotation,lower_rotation.T@hand)):
            # Fade all corrections at the handoff, including any elbow-pole edit.
            original=R.from_quat(local[j,offset+k,3:7]);corrected=R.from_matrix(rotation)
            output[j,offset+k,3:7]=Slerp([0,1],R.from_quat([original.as_quat(),corrected.as_quat()]))(weight).as_quat()
        previous[side]=(shoulder,knee,end);row['hands'][side]={'wrist_extension':best[2],'wrist_deviation':best[3],'target_error_cm':float(np.linalg.norm(target-end))}
    diagnostics.append(row)
result=copy.deepcopy(data);result['clips'][ENTER]['frames']=output.tolist();leave=np.asarray(result['clips'][EXIT]['frames']);leave[:len(output)]=output[::-1];result['clips'][EXIT]['frames']=leave.tolist()
(OUT/'kaitlin_corrected_arms.json').write_text(json.dumps(result,separators=(',',':')))
(OUT/'kaitlin_support_fit.json').write_text(json.dumps({'anchors':{s:v[0].tolist() for s,v in anchors.items()},'samples':diagnostics},indent=2))
print('KAITLIN_SUPPORT_FIT',max(h['target_error_cm'] for r in diagnostics for h in r['hands'].values()))
