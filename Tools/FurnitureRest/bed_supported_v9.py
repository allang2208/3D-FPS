"""Supported bed-edge seating and native knee hinges, using the sofa entry donor."""
import copy,json,math
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R,Slerp
from scipy.interpolate import PchipInterpolator
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'SourceAssets/FurnitureRest20261022/BedNaturalV8'
OUT=ROOT/'SourceAssets/FurnitureRest20261022/BedSupportedV9'
OUT.mkdir(parents=True,exist_ok=True)
ns={'__file__':str(ROOT/'Tools/FurnitureRest/bed_natural.py')}
exec((ROOT/'Tools/FurnitureRest/bed_natural.py').read_text().split('for kind in kinds:')[0],ns)
fk,rot,ik,handrot,ix,ref,bind,blendrot,hanging,fingers,smooth=[ns[k] for k in ('fk','rot','ik','handrot','ix','ref','bind','blendrot','hanging','fingers','smooth')]
source=json.loads((BASE/'authored.json').read_text())
donor=json.loads((OUT.parent/'HangingEntryV6/authored.json').read_text())['clips']['Rest.Sofa.Enter']
df=np.array(donor['frames'])
configs={n:json.loads((ROOT/'Content/ColdSteelData'/n).read_text(encoding='utf-8-sig')) for n in ('furniture_rest.json','apartment_furniture_rest.json')}
kinds=sorted({k.split('.')[1] for k in source['clips']})
routes=json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))['clips']
if not (OUT/'baseline_routes.json').exists():(OUT/'baseline_routes.json').write_text(json.dumps({k:routes[k] for k in source['clips']},indent=2))
result={k:source[k] for k in ('mesh','skeleton','names','parents','reference')};result['clips']={}
support_fit=json.loads((OUT/'support_fit.json').read_text()) if (OUT/'support_fit.json').exists() else {}

def unit(a):return a/max(np.linalg.norm(a),1e-9)
def sample(frames,t,rate=30):
    value=np.clip(t*rate,0,len(frames)-1);j=min(int(value),len(frames)-2);u=value-j
    a=frames[j];b=frames[j+1];f=a*(1-u)+b*u;q=b[:,3:7].copy();q[(a[:,3:7]*q).sum(axis=1)<0]*=-1
    f[:,3:7]=a[:,3:7]*(1-u)+q*u;f[:,3:7]/=np.linalg.norm(f[:,3:7],axis=1)[:,None];return f
def mix(a,b,t):return sample(np.array([a,b]),t,1)
def basis(direction,normal):
    y=unit(direction);z=unit(normal-y*(normal@y));return np.column_stack((np.cross(y,z),y,z))

# A single anatomical hinge frame owns each leg, rather than accumulating
# shortest-arc rotations from several independently retimed poses.
legref={}
donor_seat=fk(sample(df,1.15))
for side in ('l','r'):
    a,b,c=[ix[n+'_'+side] for n in ('thigh','calf','foot')]
    hip,knee,foot=donor_seat[[a,b,c],:3,3];upper=knee-hip;lower=foot-knee
    normal=unit(np.cross(upper,lower))
    legref[side]=(np.linalg.norm(upper),np.linalg.norm(lower),basis(upper,normal),basis(lower,normal))
def leg(f,side,target,pole,foot_rotation):
    a,b,c=[ix[n+'_'+side] for n in ('thigh','calf','foot')];w=fk(f);hip=w[a,:3,3]
    l1,l2,b1,b2=legref[side];v=target-hip;dist=np.linalg.norm(v);direction=unit(v)
    dist=np.clip(dist,abs(l1-l2)+.05,l1+l2-.35);end=hip+direction*dist
    bend=unit(pole-direction*(pole@direction));along=(l1*l1+dist*dist-l2*l2)/(2*dist)
    knee=hip+direction*along+bend*math.sqrt(max(0,l1*l1-along*along))
    normal=unit(np.cross(knee-hip,end-knee))
    rot(f,a,basis(knee-hip,normal)@b1.T@donor_seat[a,:3,:3])
    rot(f,b,basis(end-knee,normal)@b2.T@donor_seat[b,:3,:3]);rot(f,c,foot_rotation)

for kind in kinds:
    cfg=configs['apartment_furniture_rest.json' if kind=='ApartmentBed' else 'furniture_rest.json'];spec=cfg['types'][kind]
    height=spec['surface_height'];yaw0=spec['entry_yaw'];entry_turn=R.from_euler('z',yaw0,degrees=True).as_matrix()
    origin=np.array(spec['entry_offset'],float)-entry_turn@np.array([0.,70.,0.])
    oldidle=np.array(source['clips'][f'Rest.{kind}.Idle']['frames']);end=oldidle[0];ew=fk(end);resthip=ew[ix['pelvis'],:3,3]
    seat=sample(df,1.15);seat[ix['pelvis'],:3]=origin+entry_turn@seat[ix['pelvis'],:3];seat[ix['pelvis'],2]=height+14
    rot(seat,ix['pelvis'],entry_turn@fk(sample(df,1.15))[ix['pelvis'],:3,:3]);sw=fk(seat)
    seat_pos=seat[ix['pelvis'],:3].copy();poses=[]
    support_curve=PchipInterpolator(*np.array(support_fit[kind]).T) if kind in support_fit else lambda t:0.
    for frame_index in range(175):
        t=frame_index/30;land=smooth(t/1.6);lift=smooth((t-1.8)/.85);pivot=smooth((t-2.65)/1.15);lie=smooth((t-3.8)/1.25)
        yaw=yaw0*(1-pivot);turn=R.from_euler('z',yaw,degrees=True).as_matrix()
        if t<=1.6:
            donor_t=1.15*t/1.6;d=sample(df,donor_t);dw=fk(d);f=d.copy()
            f[ix['pelvis'],:3]=origin+entry_turn@d[ix['pelvis'],:3]
            f[ix['pelvis'],2]+=(height+14-80)*smooth(donor_t/1.15)
            f[ix['pelvis'],2]+=float(support_curve(t))
            if kind=='Bunk':f[ix['pelvis'],2]-=20*math.sin(math.pi*smooth((t-.15)/1.4))**2
            rot(f,ix['pelvis'],entry_turn@dw[ix['pelvis'],:3,:3])
            if kind=='Bunk':
                duck=smooth((t-.48)/.85)
                for bone in ('pelvis','spine_01','spine_02','spine_03','spine_04','spine_05','neck_01','neck_02','head'):
                    current=fk(f)[ix[bone],:3,:3];angle={'neck_01':50,'neck_02':35,'head':20}.get(bone,68)
                    target=entry_turn@R.from_euler('x',angle,degrees=True).as_matrix()@bind[ix[bone],:3,:3]
                    rot(f,ix[bone],blendrot(current,target,duck))
            for side,sign in [('l',1),('r',-1)]:
                target=origin+entry_turn@dw[ix['foot_'+side],:3,3]
                target+=entry_turn@np.array([0.,25*smooth(t/1.6),0.])
                target[2]+=(height-28-9)*smooth((t-.95)/.65)
                leg(f,side,target,entry_turn@np.array([0.,1.,.12]),entry_turn@dw[ix['foot_'+side],:3,:3])
        else:
            f=seat.copy();hip=seat_pos*(1-pivot)+resthip*pivot;hip[2]+=float(support_curve(t));f[ix['pelvis'],:3]=hip
            for bone,factor in [('pelvis',.87),('spine_01',.91),('spine_02',.95),('spine_03',1),('spine_04',1),('spine_05',1),('neck_01',.96),('neck_02',.94),('head',.92)]:
                if kind=='Bunk':q=turn@R.from_euler('x',{'neck_01':50,'neck_02':35,'head':20}.get(bone,68),degrees=True).as_matrix()@bind[ix[bone],:3,:3]
                else:q=turn@blendrot(donor_seat[ix[bone],:3,:3],R.from_euler('x',25*factor,degrees=True).as_matrix()@bind[ix[bone],:3,:3],lift)
                rot(f,ix[bone],blendrot(q,ew[ix[bone],:3,:3],lie))
            for side,sign in [('l',1),('r',-1)]:
                rise=smooth((t-1.8-(.12 if side=='r' else 0))/.73)
                seated=origin+entry_turn@(donor_seat[ix['foot_'+side],:3,3]+np.array([0.,25.,0.]));seated[2]=height-28
                raised=hip+turn@np.array([sign*13,54,0]);raised[2]=height+20
                target=seated*(1-rise)+raised*rise
                target=target*(1-lie)+ew[ix['foot_'+side],:3,3]*lie
                knee_tilt=20+55*rise+15*lie
                pole=turn@np.array([0,math.cos(math.radians(knee_tilt)),math.sin(math.radians(knee_tilt))])
                q=turn@R.from_euler('x',65*rise+23*lie,degrees=True).as_matrix()@bind[ix['foot_'+side],:3,:3]
                leg(f,side,target,pole,blendrot(q,ew[ix['foot_'+side],:3,:3],lie))
        # Soft sofa-style approach, then firm bed support before the feet lift.
        w=fk(f)
        for side,sign in [('l',1),('r',-1)]:
            h=hanging(f,side,sign,turn);hw=fk(h);hand=ix['hand_'+side];elbow=ix['lowerarm_'+side]
            reach_start=(.1 if side=='l' else .2) if kind=='Bunk' else (.55 if side=='l' else .72)
            reach_end=(1.05 if side=='l' else 1.12) if kind=='Bunk' else 1.75
            reach=smooth((t-reach_start)/(reach_end-reach_start))
            release=smooth((t-(4.1 if side=='l' else 3.25))/(1.4 if side=='l' else 1.8))
            wrist_height=height+(7.5 if kind=='ApartmentBed' else 6.)
            anchor=origin+entry_turn@np.array([sign*23.,-8.,wrist_height])
            moving=f[ix['pelvis'],:3]+turn@np.array([sign*23.,-8.,wrist_height-f[ix['pelvis'],2]])
            replant=smooth((t-(2.65 if side=='l' else 3.2))/(.55 if side=='l' else .6))
            target=moving if t>=2.65 else anchor
            target+=np.array([0,0,4])*math.sin(math.pi*replant)
            target=target*(1-release)+ew[hand,:3,3]*release
            target+=np.array([sign*4,0,12])*math.sin(math.pi*release)
            target=hw[hand,:3,3]*(1-reach)+target*reach
            target+=turn@np.array([sign*3,0,11 if kind=='Bunk' else 5])*math.sin(math.pi*reach)
            pole=w[ix['upperarm_'+side],:3,3]+turn@np.array([sign*27,-10,-20])
            pole=pole*(1-release)+ew[elbow,:3,3]*release
            ik(f,side,('upperarm','lowerarm','hand'),target,pole)
            handrot(f,side,turn@np.array([sign*.45,-.89,0]),np.array([0.,0.,-1.]))
            q=blendrot(fk(f)[hand,:3,:3],ew[hand,:3,:3],release)
            rot(f,hand,blendrot(hw[hand,:3,:3],q,smooth(reach)))
            for digit in ('thumb','index','middle','ring','pinky'):
                for joint in (1,2,3):
                    b=ix[f'{digit}_{joint:02d}_{side}'];f[b,3:7]=R.from_matrix(blendrot(R.from_quat(ref[b,3:7]).as_matrix(),R.from_quat(end[b,3:7]).as_matrix(),release)).as_quat()
            if release<1:
                normal=fk(f)[hand,:3,:3]@bind[hand,:3,:3].T@ns['palm'][side][:,2]*(1 if side=='l' else -1)
                fingers(f,side,normal,reach*(1-release),0)
        poses.append(f.tolist())
    idle=[]
    for original in oldidle:
        f=original.copy();w=fk(f)
        for side in ('l','r'):leg(f,side,w[ix['foot_'+side],:3,3],np.array([0.,0.,1.]),w[ix['foot_'+side],:3,:3])
        idle.append(f.tolist())
    # End hand contact exactly in the supported idle, without another late IK pass.
    end_pose=np.array(idle[0]);from_pose=np.array(poses[151])
    for j in range(152,len(poses)):
        f=np.array(poses[j]);blend=smooth((j-151)/(174-151))
        for b,name in enumerate(source['names']):
            if name.startswith(('clavicle','upperarm','lowerarm','hand','thumb','index_','middle','ring','pinky')):
                f[b,3:7]=R.from_matrix(blendrot(R.from_quat(from_pose[b,3:7]).as_matrix(),R.from_quat(end_pose[b,3:7]).as_matrix(),blend)).as_quat()
        poses[j]=f.tolist()
    poses[-1]=idle[0]
    takes={'Enter':poses,'Idle':idle,'Exit':copy.deepcopy(poses[::-1])+[copy.deepcopy(poses[0]) for _ in range(9)]}
    for phase,frames in takes.items():
        role=f'Rest.{kind}.{phase}';duration=(len(frames)-1)/30;camera=[]
        for f in frames:
            head=fk(np.array(f))[ix['head']];eye=head[:3,3]+head[:3,:3]@bind[ix['head'],:3,:3].T@np.array([0,7,6]);camera.append([*eye.tolist(),0.,0.])
        result['clips'][role]={'rate':30,'duration':duration,'frames':frames};cfg['clips'][role]={'duration':duration,'camera':camera}
    print('BED_SUPPORTED_AUTHORED',kind,flush=True)
result['changed_roles']=list(result['clips']);(OUT/'authored.json').write_text(json.dumps(result,separators=(',',':')))
for n,c in configs.items():(OUT/n).write_text(json.dumps(c,ensure_ascii=False,indent=2),encoding='utf-8')
merged=copy.deepcopy(configs['furniture_rest.json'])
for k in ('types','clips'):merged[k].update(configs['apartment_furniture_rest.json'][k])
merged['furniture']+=configs['apartment_furniture_rest.json']['furniture'];(OUT/'review_config.json').write_text(json.dumps(merged,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'Geometry').mkdir(exist_ok=True);(OUT/'Geometry/index.json').write_bytes((BASE/'Geometry/index.json').read_bytes())
(OUT/'ReviewSaved').mkdir(exist_ok=True)
for n in ('body.json','head.json'):(OUT/'ReviewSaved'/n).write_bytes((BASE/'ReviewSaved'/n).read_bytes())
