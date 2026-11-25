"""Retarget the innkeeper and herbalist idle to the stablemaster's actual reach and cuffs."""
from pathlib import Path
import json,sys,math
import numpy as np
from scipy.spatial.transform import Rotation
P=Path(__file__).resolve().parents[5]
sys.path.insert(0,str(P/'Tools/VillageTavernKeeper/Idle'))
from retarget_idle import forward_kinematics,rotation,unit,swing,body_frame
R=P/'SourceAssets/HillsVillageStable';O=R/'StablemasterMeshyR4'
def read(p):return json.loads(p.read_bytes())
r=read(R/'StablemasterMeshyR3/Authoring/idle_reference.json')
names=r['names'];ix={n:i for i,n in enumerate(names)};parents=r['parents']
native=np.asarray(r['reference']);ref=forward_kinematics(native,parents)
donors=read(O/'npc_standing.json')
keeper=donors['A_TavernKeeper_Idle'];herbalist=donors['A_VillageHerbalist_Idle']
palm=read(O/'palms.json')
def basis(d):
    i={n:j for j,n in enumerate(d['names'])};p=np.array(d['reference'])[:,:3]
    return body_frame(p,i['upperarm_l'],i['upperarm_r'],[i['foot_l'],i['foot_r']],[i['ball_l'],i['ball_r']])
target_basis=body_frame(ref[:,:3,3],ix['LeftArm'],ix['RightArm'],[ix['LeftFoot'],ix['RightFoot']],[ix['LeftToeBase'],ix['RightToeBase']])
mapping=[target_basis@basis(d).T for d in (keeper,herbalist)]
dn={n:i for i,n in enumerate(keeper['names'])}
rate=keeper['rate'];frames=np.array(keeper['frames']);herb=np.asarray(herbalist['frames'])
torso={'Spine02':'spine_01','Spine01':'spine_02','Spine':'spine_03','neck':'neck_01','Head':'head','LeftShoulder':'clavicle_l','RightShoulder':'clavicle_r'}
tracks={n:[] for n in names};ranges=[[],[]]
for f in range(len(frames)-1):
    phase=math.tau*f/(len(frames)-1)
    frame=native.copy();world=ref.copy()
    def set_world(i,desired):
        frame[i,3:7]=(rotation(world[parents[i]]).inv()*desired).as_quat()
    for n,source in torso.items():
        i=ix[n];s=dn[source];b=mapping[0]
        diff=Rotation.from_quat(frames[f,s,3:])*Rotation.from_quat(frames[0,s,3:]).inv()
        desired=Rotation.from_matrix(b@diff.as_matrix()@b.T)*rotation(ref[i])
        if n in ('neck','Head'):
            share=.55 if n=='Head' else .45
            desired=Rotation.from_rotvec(target_basis[:,2]*np.radians((2.6*np.sin(phase)+.6*np.sin(2*phase))*share))*desired
        elif n in ('RightShoulder','LeftShoulder'):
            sign=1 if n=='LeftShoulder' else -1
            desired=Rotation.from_rotvec(target_basis[:,1]*np.radians(2.3*sign))*desired
        if n=='Spine':
            move=(b@(frames[f,s,:3]-frames[0,s,:3]))*.50
            frame[i,:3]+=np.linalg.solve(world[parents[i],:3,:3],move)
        set_world(i,desired);world=forward_kinematics(frame,parents)
    for k,(side,suffix,sign) in enumerate([('Left','_l',1),('Right','_r',-1)]):
        src=frames if k==0 else herb;b=mapping[k]
        arm,elbow,wrist=[ix[side+n] for n in ('Arm','ForeArm','Hand')]
        sh=world[arm,:3,3].copy();hand=dn['hand'+suffix];fore=dn['lowerarm'+suffix]
        # Left wrist sits slightly forward of the belt pouch. Right fingers
        # fall next to the coat skirt. Both arms remain away from the cloth.
        target=np.array([23.7,8.35,86.7]) if k==0 else np.array([-22.75,5.35,85.8])
        target+=sh-ref[arm,:3,3]+b@(src[f,hand,:3]-src[0,hand,:3])*.55
        u=np.linalg.norm(ref[elbow,:3,3]-ref[arm,:3,3])
        l=np.linalg.norm(ref[wrist,:3,3]-ref[elbow,:3,3])
        aim=unit(target-sh);dist=np.clip(np.linalg.norm(target-sh),abs(u-l)+.01,u+l-.15)
        target=sh+aim*dist
        pole=b@(src[f,fore,:3]-src[f,dn['upperarm'+suffix],:3])+np.array([sign*.7,-2.8,0])
        ortho=unit(pole-aim*np.dot(pole,aim))
        along=(u*u+dist*dist-l*l)/(2*dist)
        epos=sh+aim*along+ortho*np.sqrt(max(0.,u*u-along*along))
        for a,child,point in [(arm,elbow,epos),(elbow,wrist,target)]:
            current=world[child,:3,3]-world[a,:3,3]
            set_world(a,swing(current,point-world[a,:3,3])*rotation(world[a]))
            world=forward_kinematics(frame,parents)
        # Preserve rest roll; aim the actual center fingertips rather than an
        # assumed forward axis from Meshy's hand bone.
        direction=rotation(world[wrist])*rotation(ref[wrist]).inv()
        current=direction.apply(palm[side+'Hand'])
        wish=unit(np.array([sign*.045,.15 if k==0 else .11,-1.]))
        set_world(wrist,swing(current,wish)*rotation(world[wrist]))
        world=forward_kinematics(frame,parents)
        ranges[k].append(world[wrist,:3,3].tolist())
    for n,i in ix.items():
        q=frame[i].copy()
        if tracks[n] and np.dot(q[3:7],tracks[n][-1][3:7])<0:q[3:7]*=-1
        tracks[n].append(q.tolist())
for n,s in tracks.items():
    s.append(s[0].copy())
    if np.max(np.abs(np.array(s)-s[0]))<1.e-7:tracks[n]=s[:1]
(O/'standing.json').write_text(json.dumps(dict(rate=rate,frame_count=len(frames)-1,tracks=tracks),separators=(',',':')))
(O/'standing_fit.json').write_text(json.dumps(dict(donors=[keeper['path'],herbalist['path']],duration_seconds=(len(frames)-1)/rate,wrist_frame0=[rr[0] for rr in ranges],stance='arms relaxed at sides, pouch-side wrist forward',source_palm_vectors=palm),indent=2))
