"""Fit planted palms and distributed torso recline to the native body proportions."""
import copy,json,math,shutil
from pathlib import Path
import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.spatial.transform import Rotation as R,Slerp

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'SourceAssets/FurnitureRest20261022/MeshyBedSideHands20261024'
OUT=BASE.parent/'MeshyBedSupportedHands20261024';OUT.mkdir(exist_ok=True)
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
h={'__file__':str(ROOT/'Tools/FurnitureRest/meshy_bed_side_hands.py')}
exec((ROOT/'Tools/FurnitureRest/meshy_bed_side_hands.py').read_text().split('for j,original in enumerate(frames):')[0],h)
fk,rot,ix,unit,basis,smooth,between=[h[n] for n in ('fk','rot','ix','unit','basis','smooth','between')]
surface=h['ns']['surface'];handrot=h['ns']['ns']['handrot'];bind=h['ns']['bind']
data=copy.deepcopy(read(BASE/'authored.json'));original_frames=np.asarray(data['clips']['Rest.Bed.Enter']['frames'])
seated_support=read(OUT/'seated_support.json') if (OUT/'seated_support.json').exists() else []
torso=[('spine_01',.25),('spine_02',.50),('spine_03',.72),('spine_04',.90),('spine_05',1.),('clavicle_l',1.),('clavicle_r',1.)]
curve=PchipInterpolator([3.65,3.9,4.2,4.5,4.8,5.3,6.,6.5,7.,7.45],[-5.,3.,28.,54.,57.,59.,60.,65.,85.,88.])
def mixrot(a,b,t):return Slerp([0,1],R.from_matrix([a,b]))(float(np.clip(t,0,1))).as_matrix()
def lean(w):
    v=w[ix['spine_05'],:3,3]-w[ix['pelvis'],:3,3]
    return float(np.degrees(np.arctan2(-v[1],v[2])))
def bend_torso(original,angle):
    f=original.copy();w=fk(original)
    for name,factor in torso:rot(f,ix[name],R.from_euler('x',angle*factor,degrees=True).as_matrix()@w[ix[name],:3,:3])
    difference=lean(fk(f))-lean(w)
    for name in ('neck_01','neck_02','head'):rot(f,ix[name],R.from_euler('x',difference,degrees=True).as_matrix()@w[ix[name],:3,:3])
    return f

previous_arms={}
def arm(f,original_world,side,target,hand_rotation):
    a,b,c=[ix[n+'_'+side] for n in ('upperarm','lowerarm','hand')]
    w=fk(f);shoulder=w[a,:3,3]
    upper=original_world[b,:3,3]-original_world[a,:3,3];lower=original_world[c,:3,3]-original_world[b,:3,3]
    l1,l2=np.linalg.norm(upper),np.linalg.norm(lower);axis=unit(target-shoulder)
    distance=min(np.linalg.norm(target-shoulder),(l1+l2)*.985)
    ref_axis=unit(upper+lower);bend=between(ref_axis,axis)@unit(upper-ref_axis*(upper@ref_axis))
    normal=unit(np.cross(upper,lower));upper_c=basis(upper,normal).T@original_world[a,:3,:3];lower_c=basis(lower,normal).T@original_world[b,:3,:3]
    along=(l1*l1+distance*distance-l2*l2)/(2*distance);height=math.sqrt(max(0.,l1*l1-along*along));wrist=shoulder+axis*distance
    palm=hand_rotation@bind[c,:3,:3].T@h['ns']['ns']['palm'][side];sign=1 if side=='l' else -1
    forward,across,down=palm[:,1],palm[:,0]*sign,palm[:,2]*sign
    prior_bend=bend
    if side in previous_arms:
        ps,pe,pw=previous_arms[side];old=unit(pw-ps);prior_bend=between(old,axis)@unit(pe-ps-old*((pe-ps)@old))
    best=None
    for angle in np.linspace(-110,110,111):
        elbow=shoulder+axis*along+R.from_rotvec(axis*math.radians(angle)).as_matrix()@bend*height
        forearm=unit(wrist-elbow)
        extension=math.degrees(math.atan2(forearm@down,forearm@forward))
        deviation=math.degrees(math.asin(np.clip(forearm@across,-1,1)))
        outside=(elbow[0]-shoulder[0])*sign
        current_bend=unit(elbow-shoulder-axis*along)
        continuity=math.degrees(math.acos(np.clip(current_bend@prior_bend,-1,1)))
        score=max(0.,extension-70.)**2*12.+max(0.,abs(deviation)-18.)**2*8.+max(0.,1.-outside)**2*4.+angle*angle*.008+continuity*continuity*.25
        if best is None or score<best[0]:best=(score,elbow,extension,deviation)
    elbow=best[1];normal=unit(np.cross(elbow-shoulder,wrist-elbow))
    rot(f,a,basis(elbow-shoulder,normal)@upper_c);rot(f,b,basis(wrist-elbow,normal)@lower_c);rot(f,c,hand_rotation)
    return {'wrist_extension':best[2],'wrist_deviation':best[3],'target_error_cm':float(np.linalg.norm(target-wrist))}

def wrist_fit(f,w,side,target,rotation):
    for _ in range(3):
        info=arm(f,w,side,target,rotation)
        if info['wrist_extension']<=71.:break
        c=ix['hand_'+side];sign=1 if side=='l' else -1
        across=(rotation@bind[c,:3,:3].T@h['ns']['ns']['palm'][side])[:,0]*sign
        rotation=R.from_rotvec(across*math.radians(info['wrist_extension']-70.)).as_matrix()@rotation
    info=arm(f,w,side,target,rotation)
    return info,rotation

def relaxed_wrist(f,side,rotation):
    world=fk(f);b,c=[ix[n+'_'+side] for n in ('lowerarm','hand')]
    forward=rotation@bind[c,:3,:3].T@h['ns']['ns']['palm'][side][:,1]
    forearm=unit(world[c,:3,3]-world[b,:3,3]);swing=R.from_matrix(between(forward,forearm)).as_rotvec()
    angle=np.linalg.norm(swing)
    if angle>math.radians(18.):rotation=R.from_rotvec(swing*(1-math.radians(18.)/angle)).as_matrix()@rotation
    rot(f,c,rotation)
    return rotation

# Calibrate the contact plane from the native palm/finger skin. The anatomical
# finger-bone plane is not parallel to the underside of this particular mesh.
support=original_frames[round(4.7*30)].copy();contact_rotations={};palm_calibration={}
geometry=h['geometry'];dominant=[geometry['bone_names'][max(ws,key=lambda p:p[1])[0]] for ws in geometry['weights']]
for side in ('l','r'):
    handrot(support,side,[0,1,0],[0,0,-1])
    selected=[i for i,n in enumerate(dominant) if n.startswith(('hand_','thumb_','index_','middle_','ring_','pinky_')) and n.endswith('_'+side)][::3]
    groups={part:[j for j,i in enumerate(selected) if dominant[i].startswith(part+'_')] for part in ('hand','thumb','index','middle','ring','pinky')}
    w=fk(support);c=ix['hand_'+side];vertices=h['hand_points'](support,side)-w[c,:3,3]
    palm=w[c,:3,:3]@bind[c,:3,:3].T@h['ns']['ns']['palm'][side];sign=1 if side=='l' else -1
    best=None
    for roll in range(-15,16):
        for pitch in range(-12,13):
            correction=R.from_rotvec(palm[:,0]*sign*math.radians(pitch)).as_matrix()@R.from_rotvec(palm[:,1]*math.radians(roll)).as_matrix()
            v=vertices@correction.T;levels=[v[g,2].min() for g in groups.values()]
            score=(levels[0]-min(levels))**2*6.+np.var(levels)+(roll*roll+pitch*pitch)*.001
            if best is None or score<best[0]:best=(score,correction,roll,pitch,levels)
    contact_rotations[side]=best[1]@w[c,:3,:3]
    palm_calibration[side]={'roll':best[2],'pitch':best[3],'pad_to_lowest_cm':float(best[4][0]-min(best[4]))}

result=[];notes=[]
for j,original in enumerate(original_frames):
    t=j/30;source_world=fk(original);original=original.copy()
    drop=seated_support[j]['root_drop_cm'] if j<len(seated_support) else 0.
    original[ix['pelvis'],2]-=drop
    f=original.copy();w=fk(original)
    torso_weight=float(smooth((t-3.65)/.5)*(1-smooth((t-7.0)/.45)))
    desired=lean(w)*(1-torso_weight)+float(curve(np.clip(t,3.65,7.45)))*torso_weight
    if torso_weight>0:
        low,high=-25.,65.
        for _ in range(12):
            mid=(low+high)/2;candidate=bend_torso(original,mid)
            if lean(fk(candidate))<desired:low=mid
            else:high=mid
        f=bend_torso(original,(low+high)/2)
    frame_clear=float(smooth((t-.8)/.2)*(1-smooth((t-1.2)/.3)))
    if frame_clear>0:
        for side in ('l','r'):
            foot=ix['foot_'+side]
            target=source_world[foot,:3,3]+[0.,4.*frame_clear,-drop*(1-frame_clear)]
            h['ns']['solve'](f,side,('thigh','calf','foot'),target,source_world[foot,:3,:3])
    row={'time':t,'torso_lean_before':lean(w),'torso_lean_after':lean(fk(f)),'seated_root_drop_cm':drop,'hands':{}}
    for side,sign in [('l',1),('r',-1)]:
        delay=.05 if side=='r' else 0.
        weight=float(smooth((t-3.9-delay)/.70)*(1-smooth((t-6.65-delay)/.65)))
        release_lift=3.*float(smooth((t-6.6)/.25)*(1-smooth((t-7.15)/.3)))
        if weight<=0 and torso_weight<=0 and drop<=0:continue
        c=ix['hand_'+side]
        flat_rotation=contact_rotations[side]
        # Both native palms carry load on the same stationary mattress patch.
        anchor=np.array([-2. if side=='l' else -59.,11.,70.])
        natural=source_world[c,:3,3]-[0.,0.,drop*.2]
        target=natural*(1-weight)+anchor*weight
        target[2]+=release_lift
        hand_rotation=mixrot(w[c,:3,:3],flat_rotation,weight)
        # Interpolate finger articulation toward the original open support pose.
        for digit in ('thumb','index','middle','ring','pinky'):
            for joint in (1,2,3):
                bone=ix[f'{digit}_{joint:02d}_{side}']
                f[bone,3:7]=R.from_matrix(mixrot(R.from_quat(original[bone,3:7]).as_matrix(),R.from_quat(support[bone,3:7]).as_matrix(),weight)).as_quat()
        if t<3.65:
            h['ns']['solve'](f,side,('upperarm','lowerarm','hand'),target,hand_rotation)
            hand_rotation=relaxed_wrist(f,side,hand_rotation)
            info={'target_error_cm':float(np.linalg.norm(fk(f)[c,:3,3]-target))}
        else:info,hand_rotation=wrist_fit(f,w,side,target,hand_rotation)
        for _ in range(2):
            vertices=h['hand_points'](f,side);low=vertices[np.argsort(vertices[:,2])[:16]]
            gap=min(float(p[2]-surface(p[0],p[1])) for p in low)
            # Fit the hand skin, not merely the wrist bone, to the contact plane.
            desired_gap=.45+release_lift
            shift=(desired_gap-gap)*(1. if gap<desired_gap else weight)
            if abs(shift)<.02:break
            target[2]+=shift
            if t<3.65:
                h['ns']['solve'](f,side,('upperarm','lowerarm','hand'),target,hand_rotation)
                hand_rotation=relaxed_wrist(f,side,hand_rotation)
                info={'target_error_cm':float(np.linalg.norm(fk(f)[c,:3,3]-target))}
            else:info,hand_rotation=wrist_fit(f,w,side,target,hand_rotation)
        row['hands'][side]={**info,'contact_weight':weight,'target':target.tolist()}
    restore=float(smooth((t-7.2)/.25))
    if restore>0:
        for name,bone in ix.items():
            if name.startswith(('upperarm_','lowerarm_','hand_','thumb_','index_','middle_','ring_','pinky_')):
                f[bone,3:7]=R.from_matrix(mixrot(R.from_quat(f[bone,3:7]).as_matrix(),R.from_quat(original[bone,3:7]).as_matrix(),restore)).as_quat()
    world=fk(f)
    for side in ('l','r'):previous_arms[side]=world[[ix[n+'_'+side] for n in ('upperarm','lowerarm','hand')],:3,3].copy()
    result.append(f);notes.append(row)
data['clips']['Rest.Bed.Enter']['frames']=np.asarray(result).tolist()
leave=np.asarray(data['clips']['Rest.Bed.Exit']['frames']);leave[:len(result)]=np.asarray(result)[::-1]
data['clips']['Rest.Bed.Exit']['frames']=leave.tolist()
roles=data['changed_roles'];cfg=read(ROOT/'Content/ColdSteelData/furniture_rest.json');body=read(ROOT/'Content/ColdSteelData/player_body.json')
metadata={}
for role in roles:
    camera=[]
    for f in np.asarray(data['clips'][role]['frames']):
        head=fk(f)[ix['head']];eye=head[:3,3]+head[:3,:3]@bind[ix['head'],:3,:3].T@np.array([0.,7.,6.]);camera.append([*eye.tolist(),0.,0.])
    metadata[role]={'duration':data['clips'][role]['duration'],'camera':camera}
cfg['clips'].update(metadata)
snapshot=OUT/'baseline_routes.json'
if not snapshot.exists():snapshot.write_text(json.dumps({'default':{r:body['clips'][r] for r in roles},'variants':{
    n:{'mesh':v['body_mesh'],'clips':{r:v['clips'][r] for r in roles}} for n,v in body.get('body_variants',{}).items() if v.get('ready')}},indent=2))
for name,value in [('authored.json',data),('support_fitting.json',notes),('clip_metadata.json',metadata),('review_config.json',cfg)]:
    (OUT/name).write_text(json.dumps(value,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
(OUT/'palm_plane_calibration.json').write_text(json.dumps(palm_calibration,indent=2))
(OUT/'ReviewSaved').mkdir(exist_ok=True)
for name in ('body.json','head.json'):
    if not (OUT/'ReviewSaved'/name).exists():shutil.copyfile(BASE/'ReviewSaved'/name,OUT/'ReviewSaved'/name)
print('MESHY_BED_SUPPORTED_HANDS_AUTHORED',flush=True)
