"""Bed-family refinement: soft arms, staggered leg lift, supported head and rest."""
import copy,json,math
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R,Slerp
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'SourceAssets/FurnitureRest20261022/BedBaseline20261023'
OUT=ROOT/'SourceAssets/FurnitureRest20261022/BedNaturalV8'
OUT.mkdir(parents=True,exist_ok=True)
ns={'__file__':str(ROOT/'Tools/FurnitureRest/relaxed_seat.py')}
exec((ROOT/'Tools/FurnitureRest/relaxed_seat.py').read_text().split('for apartment in (False,True):')[0],ns)
fk,rot,ik,handrot,ix,ref,bind,blendrot,world=[ns[k] for k in ('fk','rot','ik','handrot','ix','ref','bind','blendrot','world')]
palm=handrot.__globals__['palm']
source=json.loads((BASE/'authored.json').read_text());result={k:source[k] for k in ('mesh','skeleton','names','parents','reference')};result['clips']={}
configs={name:json.loads((ROOT/'Content/ColdSteelData'/name).read_text(encoding='utf-8-sig')) for name in ('furniture_rest.json','apartment_furniture_rest.json')}
kinds=json.loads((BASE/'inventory.json').read_text(encoding='utf-8'))['types']
hand_fit=json.loads((OUT/'hand_fit.json').read_text()) if (OUT/'hand_fit.json').exists() else {}
head_fit=json.loads((OUT/'head_fit.json').read_text()) if (OUT/'head_fit.json').exists() else {}
heel_fit=json.loads((OUT/'heel_fit.json').read_text()) if (OUT/'heel_fit.json').exists() else {}
def smooth(t):
    t=float(np.clip(t,0,1));return t*t*t*(t*(6*t-15)+10)
def sample(frames,t,rate=30):
    value=float(np.clip(t*rate,0,len(frames)-1));j=min(int(value),len(frames)-2);a=frames[j];b=frames[j+1];u=value-j
    f=a*(1-u)+b*u;q=b[:,3:7].copy();q[np.sum(a[:,3:7]*q,axis=1)<0]*=-1
    f[:,3:7]=a[:,3:7]*(1-u)+q*u;f[:,3:7]/=np.linalg.norm(f[:,3:7],axis=1)[:,None]
    return f
def turn_at(w):
    across=w[ix['upperarm_l'],:3,3]-w[ix['upperarm_r'],:3,3]
    return R.from_euler('z',math.atan2(across[1],across[0])).as_matrix()
def hanging(f,side,sign,turn):
    h=f.copy();h[ix['clavicle_'+side],3:7]=ref[ix['clavicle_'+side],3:7];w=fk(h)
    a,b,c=[ix[n+'_'+side] for n in ('upperarm','lowerarm','hand')]
    length=np.linalg.norm(w[b,:3,3]-w[a,:3,3])+np.linalg.norm(w[c,:3,3]-w[b,:3,3])
    direction=turn@np.array([sign*.195,.045,-1]);direction/=np.linalg.norm(direction)
    target=w[a,:3,3]+direction*length*(.977 if side=='l' else .973)
    ik(h,side,('upperarm','lowerarm','hand'),target,w[a,:3,3]+turn@np.array([sign*4,-10,-28]))
    handrot(h,side,turn@np.array([sign*.015,.1,-1]),turn@np.array([-sign,0,0]))
    return h
def fingers(f,side,normal,weight,resting=0.):
    relaxed={'thumb':(-7,-5,-2),'index':(-17,-18,-8),'middle':(-16,-18,-8),'ring':(-13,-16,-7),'pinky':(-10,-13,-6)}
    braced={'thumb':(-8,-5,-2),'index':(-12,-13,-6),'middle':(-12,-14,-6),'ring':(-9,-11,-5),'pinky':(-6,-8,-4)}
    amounts={digit:np.array(angles)*(1-resting)+np.array(relaxed[digit])*resting for digit,angles in braced.items()}
    for digit,angles in amounts.items():
        for joint,angle in enumerate(angles,1):
            b=ix[f'{digit}_{joint:02d}_{side}'];w=world(f,b)
            direction=(world(f,ix[f'{digit}_{joint+1:02d}_{side}'])[:3,3]-w[:3,3]) if joint<3 else (w[:3,3]-world(f,ix[f'{digit}_02_{side}'])[:3,3])
            axis=np.cross(direction,normal);axis/=np.linalg.norm(axis)
            rot(f,b,R.from_rotvec(axis*math.radians(angle*weight)).as_matrix()@w[:3,:3])

for kind in kinds:
    cfg=configs['apartment_furniture_rest.json' if kind=='ApartmentBed' else 'furniture_rest.json']
    entry=source['clips'][f'Rest.{kind}.Enter'];originals=np.array(entry['frames']);duration=entry['duration']
    sit,lift,pivot,recline=(1.45,2.55,3.45,4.2) if kind=='ApartmentBed' else (1.35,2.15,3.,3.85)
    support='r' if cfg['types'][kind]['entry_yaw']>0 else 'l'
    planted=fk(sample(originals,sit))
    entry_forward=turn_at(planted)[:,1]
    trajectories={};cameras={}
    for phase in ('Enter','Idle'):
        data=entry if phase=='Enter' else source['clips'][f'Rest.{kind}.Idle'];take=[];source_take=np.array(data['frames'])
        if phase=='Enter':source_take=np.concatenate((source_take,np.repeat(source_take[-1:],18,axis=0)))
        for j,frame in enumerate(source_take):
            t=j/data['rate'];original=sample(source_take,t*.5) if phase=='Idle' and kind!='ApartmentBed' else frame.copy()
            f=original.copy();old=fk(original);turn=turn_at(old)
            active=t if phase=='Enter' else duration+.6
            settle=smooth((active-(recline-.35))/(duration-(recline-.35)))
            align=smooth((active-pivot)/(duration-pivot)) if kind=='Hospital' else 0.
            body_shift=np.array([0.,-16.*align,0.])
            f[ix['pelvis'],:3]+=body_shift
            if kind=='Ward' and phase=='Enter' and sit+.1<t<duration-.15:
                f[ix['pelvis'],2]+=.6*math.sin(math.pi*(t-sit-.1)/(duration-.15-sit-.1))**2
            if kind=='ApartmentBed':
                # Its thick pillow needs the upper back/neck to rise together;
                # don't lift the whole body or force a single neck joint.
                for bone,angle in [('spine_01',-7),('spine_02',-10),('spine_03',-10),('spine_04',-10),('spine_05',-10),('neck_01',-18),('neck_02',-18),('head',-14)]:
                    q=R.from_rotvec(turn[:,0]*math.radians(angle*settle)).as_matrix()@old[ix[bone],:3,:3]
                    rot(f,ix[bone],q)
            if kind=='Hospital':
                for bone,angle in [('spine_01',-5),('spine_02',-7),('spine_03',-6),('spine_04',-6),('spine_05',-6),('neck_01',2),('neck_02',2),('head',-6)]:
                    rot(f,ix[bone],R.from_rotvec(turn[:,0]*math.radians(angle*align)).as_matrix()@old[ix[bone],:3,:3])
            if kind in head_fit:
                for bone,angle in head_fit[kind]['angles'].items():
                    target=turn@R.from_euler('x',angle,degrees=True).as_matrix()@bind[ix[bone],:3,:3]
                    rot(f,ix[bone],blendrot(fk(f)[ix[bone],:3,:3],target,settle))
            stagger=phase=='Enter' and sit+.1<t<duration-.15
            if stagger or align>0:
                shift=.12*math.sin(math.pi*(t-sit-.1)/(duration-.15-sit-.1))**2 if stagger else 0.
                for side in ('l','r'):
                    lead=1 if side==support else -1;w=fk(sample(originals,t+lead*shift)) if phase=='Enter' else old
                    ik(f,side,('thigh','calf','foot'),w[ix['foot_'+side],:3,3]+np.array([0.,-1.*align,0.]),w[ix['calf_'+side],:3,3]+body_shift)
                    rot(f,ix['foot_'+side],w[ix['foot_'+side],:3,:3])
            if settle>0 and kind in heel_fit:
                for side in ('l','r'):
                    w=fk(f);a,b,c=[ix[n+'_'+side] for n in ('thigh','calf','foot')]
                    hip,knee,foot=w[[a,b,c],:3,3];target=foot-np.array([0.,0.,heel_fit[kind]*settle])
                    length=(np.linalg.norm(knee-hip)+np.linalg.norm(foot-knee))*.985
                    delta=target-hip;horizontal=np.linalg.norm(delta[:2]);allowed=math.sqrt(max(1,length*length-delta[2]*delta[2]))
                    if horizontal>allowed:target[:2]=hip[:2]+delta[:2]*(allowed/horizontal)
                    ik(f,side,('thigh','calf','foot'),target,knee+np.array([0,0,8]))
                    rot(f,c,w[c,:3,:3])
            for side,sign in [('l',1),('r',-1)]:
                supporting=side==support
                rest=smooth((active-(duration-.15))/.75) if side=='l' else settle
                reach=smooth((active-(.5 if supporting else .68))/((sit+.05 if supporting else sit+.3)-(.5 if supporting else .68)))
                h=hanging(f,side,sign,turn);hw=fk(h)
                hand=ix['hand_'+side];elbow=ix['lowerarm_'+side];cl=ix['clavicle_'+side]
                f[cl,3:7]=R.from_matrix(blendrot(R.from_quat(h[cl,3:7]).as_matrix(),R.from_quat(original[cl,3:7]).as_matrix(),reach)).as_quat()
                # A brief real plant supports the leg lift; hands then
                # reposition at different times as the body turns inward.
                anchor_end=lift+.18 if supporting else lift-.12
                move=smooth((active-anchor_end)/(pivot+.18-anchor_end))
                target=planted[hand,:3,3]*(1-move)+(old[hand,:3,3]+body_shift)*move
                if kind=='Bunk':target[2]+=1.2*(1-move)
                if phase=='Enter':target+=np.array([0,0,2.5])*math.sin(math.pi*move)
                pose_q=blendrot(planted[hand,:3,:3],old[hand,:3,:3],move)
                # Spread the two support palms diagonally away from the legs;
                # rotate them back while each hand repositions on the bed.
                brace_forward=entry_forward+np.array([0.,-1.,0.]) if supporting else np.array([0.,1.,0.])
                handrot(f,side,brace_forward,np.array([0.,0.,-1.]))
                pose_q=blendrot(fk(f)[hand,:3,:3],old[hand,:3,:3],move) if supporting else fk(f)[hand,:3,:3]
                # One relaxed hand rests on the abdomen; the other stays
                # beside the body. This also narrows the lower-bunk posture.
                w=fk(f);pelvis=w[ix['pelvis'],:3,3]
                height=hand_fit.get(kind,{}).get('wrist_height_offset_cm',17.5)
                rest_target=(pelvis+turn@np.array([12,-6,height])) if side=='l' else old[hand,:3,3]+body_shift
                target=target*(1-rest)+rest_target*rest
                if side=='l':target+=turn@np.array([8,0,16])*math.sin(math.pi*rest)
                reach_target=hw[hand,:3,3]*(1-reach)+target*reach
                reach_target+=turn@np.array([sign*3,0,9 if kind=='Bunk' else 3])*math.sin(math.pi*reach)
                shoulder=w[ix['upperarm_'+side],:3,3]
                rest_pole=shoulder+np.array([sign*19,16,-8])
                pole=hw[elbow,:3,3]*(1-reach)+(old[elbow,:3,3]*(1-rest)+rest_pole*rest)*reach
                ik(f,side,('upperarm','lowerarm','hand'),reach_target,pole)
                if rest>0:
                    if side=='l':
                        current=fk(f)
                        normal=-(current[ix['spine_02'],:3,:3]@bind[ix['spine_02'],:3,:3].T@np.array([0.,1.,0.]))
                        normal/=np.linalg.norm(normal)
                        forward=current[hand,:3,3]-current[elbow,:3,3]
                        forward-=normal*np.dot(forward,normal);forward/=np.linalg.norm(forward)
                    else:
                        forward=turn@np.array([-.08,1.,.04]);normal=np.array([0.,0.,-1.])
                    handrot(f,side,forward,normal);rest_q=fk(f)[hand,:3,:3]
                    pose_q=blendrot(pose_q,rest_q,rest)
                rot(f,hand,blendrot(hw[hand,:3,:3],pose_q,smooth(reach)))
                hand_q=fk(f)[hand,:3,:3]
                normal=hand_q@bind[hand,:3,:3].T@palm[side][:,2]*(1 if side=='l' else -1)
                fingers(f,side,normal,reach,rest)
            take.append(f.tolist())
        trajectories[phase]=take
    # The same supported movement is used in reverse for leaving the bed.
    trajectories['Exit']=copy.deepcopy(trajectories['Enter'][::-1])
    trajectories['Exit'].extend(copy.deepcopy(trajectories['Enter'][0]) for _ in range(9))
    for phase,take in trajectories.items():
        role=f'Rest.{kind}.{phase}';camera=[]
        for frame in take:
            w=fk(np.array(frame));head=w[ix['head']]
            eye=head[:3,3]+head[:3,:3]@bind[ix['head'],:3,:3].T@np.array([0,7,6]);camera.append([*eye.tolist(),0.,0.])
        length=(len(take)-1)/30
        result['clips'][role]={'rate':30,'duration':length,'frames':take}
        cfg['clips'][role]={'duration':length,'camera':camera}
    print('BED_NATURAL_AUTHORED',kind,flush=True)
result['changed_roles']=list(result['clips'])
(OUT/'authored.json').write_text(json.dumps(result,separators=(',',':')))
for name,cfg in configs.items():(OUT/name).write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding='utf-8')
merged=copy.deepcopy(configs['furniture_rest.json'])
for key in ('clips','types'):merged[key].update(configs['apartment_furniture_rest.json'][key])
merged['furniture']+=configs['apartment_furniture_rest.json']['furniture']
(OUT/'review_config.json').write_text(json.dumps(merged,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'Geometry').mkdir(exist_ok=True)
lookup=json.loads((BASE/'Geometry/index.json').read_text())
(OUT/'Geometry/index.json').write_text(json.dumps({k:str(BASE/'Geometry'/v) for k,v in lookup.items()},indent=2))
(OUT/'ReviewSaved').mkdir(exist_ok=True)
(OUT/'ReviewSaved/body.json').write_bytes((BASE/'ReviewSaved/body.json').read_bytes())
