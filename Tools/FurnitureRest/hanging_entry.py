"""Keep V5 seating; replace the locked pre-seat arms with a soft hanging reach."""
import copy,json,math,hashlib
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R,Slerp
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'SourceAssets/FurnitureRest20261022/RelaxedSeatV5'
OUT=ROOT/'SourceAssets/FurnitureRest20261022/HangingEntryV6'
OUT.mkdir(parents=True,exist_ok=True)
ns={'__file__':str(ROOT/'Tools/FurnitureRest/relaxed_seat.py')}
exec((ROOT/'Tools/FurnitureRest/relaxed_seat.py').read_text().split('for apartment in (False,True):')[0],ns)
fk,rot,ik,handrot,ix,ref,blendrot=[ns[k] for k in ('fk','rot','ik','handrot','ix','ref','blendrot')]
source=json.loads((BASE/'authored.json').read_text())
result=copy.deepcopy(source)
changed=[]
def smooth(t):
    t=float(np.clip(t,0,1));return t*t*t*(t*(6*t-15)+10)
def hanging(f,side,sign,t,phase):
    # Shoulder to wrist reach is below full extension. Slight elbow flexion
    # and an inward palm replace the previous unreachable wrist target.
    h=f.copy();cl=ix['clavicle_'+side];h[cl,3:7]=ref[cl,3:7]
    w=fk(h);a,b,c=[ix[n+'_'+side] for n in ('upperarm','lowerarm','hand')]
    length=np.linalg.norm(w[b,:3,3]-w[a,:3,3])+np.linalg.norm(w[c,:3,3]-w[b,:3,3])
    sway=(.35 if side=='l' else -.25)*math.sin(math.pi*min(t,1.2)/1.2) if phase=='Enter' else 0.
    direction=np.array([sign*.195,.045+sway*.01,-1.]);direction/=np.linalg.norm(direction)
    target=w[a,:3,3]+direction*length*(.977 if side=='l' else .973)
    pole=w[a,:3,3]+np.array([sign*4.,-10.,-28.])
    ik(h,side,('upperarm','lowerarm','hand'),target,pole)
    # Fingers hang beside the thigh instead of following the forearm's
    # inward bend into it. Preserve a small, soft wrist angle.
    handrot(h,side,np.array([sign*.015,.10,-1.]),np.array([-sign,0.,0.]))
    for digit in ('thumb','index','middle','ring','pinky'):
        for joint in (1,2,3):
            bone=ix[f'{digit}_{joint:02d}_{side}'];h[bone,3:7]=ref[bone,3:7]
    return h

for role,take in source['clips'].items():
    kind,phase=role.split('.')[1:]
    if phase=='Idle':continue
    outer='r' if kind.endswith('Left') else 'l' if kind.endswith('Right') else None
    frames=[]
    for j,frame in enumerate(take['frames']):
        t=j/take['rate'];original=np.array(frame);f=original.copy();old=fk(original)
        for side,sign in [('l',1),('r',-1)]:
            supporting=side==outer
            if phase=='Enter':
                start=.55 if supporting else (.68 if side=='l' else .8)
                finish=2.18 if supporting else (2.36 if side=='l' else 2.5)
                reach=smooth((t-start)/(finish-start))
            else:
                reach=1-smooth((t-2.15)/.65)
            if reach>=1.-1e-10:continue
            h=hanging(original,side,sign,t,phase);hw=fk(h)
            cl=ix['clavicle_'+side]
            f[cl,3:7]=R.from_matrix(blendrot(R.from_quat(h[cl,3:7]).as_matrix(),R.from_quat(original[cl,3:7]).as_matrix(),reach)).as_quat()
            hand=ix['hand_'+side];elbow=ix['lowerarm_'+side]
            target=hw[hand,:3,3]*(1-reach)+old[hand,:3,3]*reach
            target+=np.array([sign*(3.5 if supporting else 5.5),1.,4.])*math.sin(math.pi*reach)
            pole=hw[elbow,:3,3]*(1-reach)+old[elbow,:3,3]*reach
            ik(f,side,('upperarm','lowerarm','hand'),target,pole)
            # Palm rotation follows the elbow movement instead of leading it.
            wrist=smooth(reach)
            rot(f,hand,blendrot(hw[hand,:3,:3],old[hand,:3,:3],wrist))
            for digit in ('thumb','index','middle','ring','pinky'):
                for joint in (1,2,3):
                    bone=ix[f'{digit}_{joint:02d}_{side}']
                    amount=smooth((reach-.05)/.95)
                    f[bone,3:7]=R.from_matrix(blendrot(R.from_quat(h[bone,3:7]).as_matrix(),R.from_quat(original[bone,3:7]).as_matrix(),amount)).as_quat()
        frames.append(f.tolist())
    result['clips'][role]['frames']=frames;changed.append(role)
    print('HANGING_ENTRY_AUTHORED',role,flush=True)
result['changed_roles']=changed
(OUT/'authored.json').write_text(json.dumps(result,separators=(',',':')))
for name in ('furniture_rest.json','apartment_furniture_rest.json'):
    (OUT/name).write_bytes((ROOT/'Content/ColdSteelData'/name).read_bytes())
merged=json.loads((OUT/'furniture_rest.json').read_text(encoding='utf-8-sig'))
overlay=json.loads((OUT/'apartment_furniture_rest.json').read_text(encoding='utf-8-sig'))
for key in ('clips','types'):merged[key].update(overlay[key])
merged['furniture']+=overlay['furniture']
(OUT/'review_config.json').write_text(json.dumps(merged,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'Geometry').mkdir(exist_ok=True)
(OUT/'Geometry/index.json').write_bytes((BASE/'Geometry/index.json').read_bytes())
(OUT/'source_revision.json').write_text(json.dumps({'base':str(BASE/'authored.json'),
    'base_sha256':hashlib.sha256((BASE/'authored.json').read_bytes()).hexdigest(),
    'changed_roles':changed,'idle_reused':True,'lower_body_unchanged':True},indent=2))
