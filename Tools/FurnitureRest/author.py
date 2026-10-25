"""Author native Jason rest clips and per-mesh furniture anchors, without a render/test run."""
import json, math, sys
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'SourceAssets/FurnitureRest20261022'
OUT.mkdir(parents=True,exist_ok=True)
d=json.loads((ROOT/'SourceAssets/PlayerDeath20261006/authoring-input.json').read_text())
names,parents=d['names'],d['parents']; ix={n:i for i,n in enumerate(names)}
ref=np.array(d['reference']); hip=ix['pelvis']

def fk(f):
    w=f.copy()
    for i,p in enumerate(parents):
        if p<0:continue
        q=R.from_quat(w[p,3:7]); w[i,:3]=w[p,:3]+q.apply(f[i,:3]*w[p,7:])
        w[i,3:7]=(q*R.from_quat(f[i,3:7])).as_quat();w[i,7:]=w[p,7:]*f[i,7:]
    return w

def rotation_between(a,b):
    a=a/np.linalg.norm(a);b=b/np.linalg.norm(b); dot=np.clip(a@b,-1,1)
    cross=np.cross(a,b)
    if np.linalg.norm(cross)<1e-7:
        return R.identity() if dot>0 else R.from_rotvec(np.array([1.,0,0])*math.pi)
    return R.from_rotvec(cross/np.linalg.norm(cross)*math.acos(dot))

def world_rotation(f,i,q):
    p=parents[i];w=fk(f)
    f[i,3:7]=(R.from_quat(w[p,3:7]).inv()*q).as_quat() if p>=0 else q.as_quat()

def solve(f,a,b,c,target,pole):
    a,b,c=ix[a],ix[b],ix[c];w=fk(f);root=w[a,:3]
    l1=np.linalg.norm(w[b,:3]-root);l2=np.linalg.norm(w[c,:3]-w[b,:3])
    delta=np.array(target)-root;dist=np.clip(np.linalg.norm(delta),abs(l1-l2)+.01,l1+l2-.01)
    direction=delta/np.linalg.norm(delta); v=np.array(pole)-root
    bend=v-direction*np.dot(v,direction);bend/=np.linalg.norm(bend)
    along=(l1*l1+dist*dist-l2*l2)/(2*dist)
    elbow=root+direction*along+bend*math.sqrt(max(0,l1*l1-along*along))
    world_rotation(f,a,rotation_between(w[b,:3]-root,elbow-root)*R.from_quat(w[a,3:7]))
    w=fk(f);world_rotation(f,b,rotation_between(w[c,:3]-w[b,:3],np.array(target)-w[b,:3])*R.from_quat(w[b,3:7]))

refworld=fk(ref)
def pose(y,z,lean=0,lie=0,breath=0):
    f=ref.copy();f[hip,:3]=[0,y,z]
    bodyrot=R.from_euler('x',lean,degrees=True)
    world_rotation(f,hip,bodyrot*R.from_quat(refworld[hip,3:7]))
    # Small chest expansion, no whole-body translation of the supported pelvis.
    f[ix['spine_03'],0]+=breath
    for side,sign in [('l',1),('r',-1)]:
        foot=np.array([sign*12,36*(1-lie)+74*lie,7*(1-lie)+54*lie])
        if z>75:foot=np.array([sign*10,y+2,7])
        solve(f,'thigh_'+side,'calf_'+side,'foot_'+side,foot,[sign*17,y+80,z])
        world_rotation(f,ix['foot_'+side],R.from_euler('x',lie*86,degrees=True)*R.from_quat(refworld[ix['foot_'+side],3:7]))
        # Hands settle on thighs for seats and alongside the hips for a bed.
        hand=np.array([sign*(17+6*lie),y+22*(1-lie)-10*lie,60*(1-lie)+55*lie])
        if z>75:hand=np.array([sign*23,y+3,69])
        solve(f,'upperarm_'+side,'lowerarm_'+side,'hand_'+side,hand,[sign*52,y+5,z+8])
        # Keep the donor's native palm basis; turn from T-pose to palm-down contact.
        q=R.from_euler('y',sign*82,degrees=True)*R.from_quat(refworld[ix['hand_'+side],3:7])
        world_rotation(f,ix['hand_'+side],q)
        for digit in ('index','middle','ring','pinky'):
            for seg,angle in [('01',12),('02',18),('03',10)]:
                bone=f'{digit}_{seg}_{side}'
                if bone in ix:
                    i=ix[bone];f[i,3:7]=(R.from_quat(f[i,3:7])*R.from_euler('z',sign*angle,degrees=True)).as_quat()
    return f

def blend(a,b,u):
    u=np.clip(u,0,1);u=u*u*(3-2*u);f=a*(1-u)+b*u
    q=b[:,3:7].copy();q[np.sum(a[:,3:7]*q,axis=1)<0]*=-1
    f[:,3:7]=a[:,3:7]*(1-u)+q*u;f[:,3:7]/=np.linalg.norm(f[:,3:7],axis=1)[:,None]
    return f

profiles_only='--profiles-only' in sys.argv
bunk_only='--bunk-only' in sys.argv
clips=json.loads((OUT/'authored.json').read_text())['clips'] if bunk_only else {}
camera=json.loads((OUT/'furniture_rest.json').read_text(encoding='utf-8'))['clips'] if profiles_only or bunk_only else {}
for kind,lean in ([] if profiles_only else [('Bunk',90)] if bunk_only else [('Chair',0),('Sofa',14),('Bed',90),('Bunk',90)]):
    lying=kind in ('Bed','Bunk')
    end=pose(0,54,lean,1 if lying else 0)
    stand=pose(50,ref[hip,2],0)
    seated=pose(0,54,0)
    keys=[(0,stand),(.28,pose(43,82,-16)),(.82,pose(4,58,-10)),(1.12,seated)]
    if kind=='Bunk':
        # The upper frame starts at 158 cm. Duck before moving beneath it;
        # only return to standing after the runtime root has cleared the bunk.
        crouched=pose(50,54,-22)
        for side,sign in [('l',1),('r',-1)]:
            solve(crouched,'thigh_'+side,'calf_'+side,'foot_'+side,[sign*12,52,7],[sign*17,115,50])
        keys=[(0,crouched),(.45,pose(25,54,-15)),(.85,seated),(1.12,seated)]
    if lying:keys.extend([(1.75,pose(0,54,42,.45)),(2.40,end),(2.7,end)])
    else:keys.extend([(1.30,pose(0,53,lean)),(1.5,end)])
    frames=[]
    for t in np.linspace(0,keys[-1][0],round(keys[-1][0]*30)+1):
        j=next((j for j in range(len(keys)-1) if t<=keys[j+1][0]),len(keys)-2)
        a,p=keys[j];b,q=keys[j+1];frames.append(blend(p,q,(t-a)/(b-a)))
    idle=[pose(0,54,lean,1 if lying else 0,.22*math.sin(2*math.pi*i/120)**2) for i in range(121)]
    # Rise has its own acceleration: pause/load, lift, then recover. It is not
    # the same sit-down clock played backwards at a single multiplier.
    leave=[];exit_duration=2.5 if lying else 1.35
    for t in np.linspace(0,exit_duration,round(exit_duration*30)+1):
        p=t/exit_duration
        source=np.interp(p,[0,.15,.48,.86,1],[1,.94,.66,.10,0])*(len(frames)-1)
        a=min(int(source),len(frames)-2);leave.append(blend(frames[a],frames[a+1],source-a))
    for phase,take in [('Enter',frames),('Idle',idle),('Exit',leave)]:
        role=f'Rest.{kind}.{phase}';duration=(len(take)-1)/30
        cameras=[]
        for f in take:
            w=fk(f);head=w[ix['head'],:3]
            # Authored camera follows the head, lifted clear of face and pillow.
            slope=math.degrees(math.atan2(-(w[ix['head'],1]-w[hip,1]),max(.001,w[ix['head'],2]-w[hip,2])))
            eye=head+np.array([0,7*math.cos(math.radians(slope)),6+7*math.sin(math.radians(slope))])
            cameras.append([*eye.tolist(),max(0,slope)*.72])
        clips[role]={'rate':30,'duration':duration,'frames':np.asarray(take).tolist()}
        camera[role]={'duration':duration,'camera':cameras}

profiles=[]
def furniture(path,caption,kind,points,yaw=90):
    asset=path+'.'+path.rsplit('/',1)[1]
    profiles.append({'mesh':asset,'caption':caption,'slots':[{'kind':kind,'seat':p,'yaw':yaw} for p in points]})
staff='/Game/Dungeons/StaffLiving20261002'
furniture(staff+'/Meshes/SM_Staff_Chair','椅子','Chair',[[0,1,49]])
furniture('/Game/Dungeons/ReceptionHall20261006/Refine20261007/Meshes/SM_Staff_Chair','椅子','Chair',[[0,1,49]])
furniture('/Game/Dungeons/MedicalExecutiveOffice20261010/Meshes/SM_MedOffice_ErgonomicChair','办公椅','Chair',[[0,1,52]])
furniture('/Game/Dungeons/MedicalExecutiveOffice20261010/Meshes/SM_MedOffice_VisitorChair','会客椅','Chair',[[0,1,50]])
for path in [staff+'/Meshes/SM_Staff_Sofa','/Game/Dungeons/ReceptionHall20261006/Refine20261007/Meshes/SM_RH2_Sofa']:
    furniture(path,'沙发','Sofa',[[-75,5,65],[0,5,65],[75,5,65]])
furniture(staff+'/Meshes/SM_Staff_ChangingBench','长凳','Chair',[[-70,0,49],[0,0,49],[70,0,49]])
furniture('/Game/Dungeons/ReceptionHall20261006/Refine20261007/Meshes/SM_Staff_ChangingBench','长凳','Chair',[[-70,0,49],[0,0,49],[70,0,49]])
furniture('/Game/Props/HospitalWaitingBench20260929/SM_Hospital_Waiting_Bench','候诊长椅','Chair',[[-72,0,55],[0,0,55],[72,0,55]])
# The ward derivative is baked to 1.5x. Its linen top is 86-90 cm and
# the pillow lies at -X; the original source remains a separate profile.
furniture('/Game/Dungeons/IsolationWard20260929/Props/SM_Ward_HospitalBed','病床','Bed',[[-22,0,88]],0)
furniture('/Game/Props/HospitalBed20260929/SM_HospitalBed','病床','Bed',[[-14.67,0,58.67]],0)
for v in range(4):
    furniture(staff+f'/ScenePolishV4/Meshes/SM_Staff_BunkBedMessy{v}_V4','下铺','Bunk',[[0,0,70]],180)
for name,width in [('BedKing',180),('BedQueen',150)]:
    furniture('/Game/Props/CyberpunkApartmentRebuild20261022/Meshes/SM_AP_'+name,'床铺','Bed',[[0,0,67]],90)
    furniture('/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV2/Meshes/SM_AP_'+name,'床铺','Bed',[[0,0,67]],90)
for version in (2,3):
    furniture(f'/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV{version}/Meshes/SM_AP_TrainingBench','训练凳','Chair',[[0,38,53]],90)

if not profiles_only:
    (OUT/'authored.json').write_text(json.dumps({'mesh':d['mesh'],'skeleton':d['skeleton'],'names':names,'clips':clips},separators=(',',':')),encoding='utf-8')
(OUT/'furniture_rest.json').write_text(json.dumps({'version':1,'furniture':profiles,'clips':camera},ensure_ascii=False,indent=2),encoding='utf-8')
print('AUTHORED',len(clips),'native clips;',len(profiles),'furniture mesh profiles')
