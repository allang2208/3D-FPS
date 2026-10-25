"""Furniture-relative native animation, solved at each sample with fixed contacts."""
import json, math, sys
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R, Slerp

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'SourceAssets/FurnitureRest20261022/RefineV2'
OUT.mkdir(parents=True,exist_ok=True)
source=json.loads((ROOT/'SourceAssets/PlayerDeath20261006/authoring-input.json').read_text())
names,parents=source['names'],source['parents'];ix={n:i for i,n in enumerate(names)}
ref=np.asarray(source['reference']);hip=ix['pelvis']
def fk(f):
    m=np.tile(np.eye(4),(len(f),1,1));m[:,:3,:3]=R.from_quat(f[:,3:7]).as_matrix()*f[:,None,7:];m[:,:3,3]=f[:,:3]
    for i,p in enumerate(parents):
        if p>=0:m[i]=m[p]@m[i]
    return m
bind=fk(ref)
def rot(f,i,q):
    p=parents[i];w=fk(f)
    f[i,3:7]=R.from_matrix(w[p,:3,:3].T@q if p>=0 else q).as_quat()
def between(a,b):
    a=a/np.linalg.norm(a);b=b/np.linalg.norm(b);v=np.cross(a,b);s=np.linalg.norm(v)
    if s<1e-8:return np.eye(3)
    return R.from_rotvec(v/s*math.atan2(s,np.dot(a,b))).as_matrix()
def ik(f,side,chain,target,pole):
    a,b,c=[ix[n+'_'+side] for n in chain];w=fk(f);h,k,e=w[[a,b,c],:3,3]
    l1=np.linalg.norm(k-h);l2=np.linalg.norm(e-k);v=target-h;distance=np.linalg.norm(v);v/=distance
    distance=np.clip(distance,abs(l1-l2)+.05,l1+l2-.05)
    bend=pole-h;bend-=v*np.dot(bend,v);bend/=np.linalg.norm(bend)
    along=(l1*l1+distance*distance-l2*l2)/(2*distance)
    knee=h+v*along+bend*math.sqrt(max(0,l1*l1-along*along))
    rot(f,a,between(k-h,knee-h)@w[a,:3,:3]);w=fk(f)
    rot(f,b,between(w[c,:3,3]-w[b,:3,3],target-w[b,:3,3])@w[b,:3,:3])
def ease(t):
    t=np.clip(t,0,1);return t*t*(3-2*t)
def unit(v):return v/np.linalg.norm(v)
# Calibrate palm orientation from the native fingers, not an arbitrary wrist Euler offset.
palm={}
for side in ('l','r'):
    p=lambda n:bind[ix[n+'_'+side],:3,3]
    forward=unit(p('middle_01')-p('hand'))
    across=unit(p('index_01')-p('pinky_01'));across=unit(across-forward*np.dot(across,forward))
    palm[side]=np.column_stack((across,forward,np.cross(across,forward)))
def handrot(f,side,forward,normal):
    # The same anatomical thumb-side convention is retained on both hands.
    y=unit(forward);z=unit(normal-y*np.dot(normal,y));x=np.cross(y,z)
    if side=='r':x=-x;z=-z
    rot(f,ix['hand_'+side],np.column_stack((x,y,z))@palm[side].T@bind[ix['hand_'+side],:3,:3])

def pose(p):
    f=ref.copy();origin=np.asarray(p['hip'],float);yaw=p['yaw'];lean=p['lean']
    turn=R.from_euler('z',yaw,degrees=True).as_matrix()
    f[hip,:3]=origin
    rot(f,hip,turn@R.from_euler('x',lean*(.87+.13*p['flatness']),degrees=True).as_matrix()@bind[hip,:3,:3])
    # Distribute flexion through pelvis, lumbar, thoracic spine and neck.
    for bone,factor in [('spine_01',.91),('spine_02',.95),('spine_03',1),('spine_04',1),('spine_05',1),('neck_01',.96),('neck_02',.94),('head',.92)]:
        if bone.startswith('spine_'):factor=factor+(1-factor)*p['flatness']
        angle=lean*factor-(p['neck_lift'] if bone.startswith('neck_') else 0)
        if bone in ix:rot(f,ix[bone],turn@R.from_euler('x',angle,degrees=True).as_matrix()@bind[ix[bone],:3,:3])
    for side,sign in [('l',1),('r',-1)]:
        foot=np.asarray(p['feet'][side],float)
        pole=origin+turn@np.array([sign*20,100,20])
        ik(f,side,('thigh','calf','foot'),foot,pole)
        rot(f,ix['foot_'+side],turn@R.from_euler('x',p['foot_pitch'],degrees=True).as_matrix()@bind[ix['foot_'+side],:3,:3])
        hand=np.asarray(p['hands'][side],float)
        w=fk(f);a=w[ix['thigh_'+side],:3,3];b=w[ix['calf_'+side],:3,3]
        thigh=a+.55*(b-a)+turn@np.array([sign*1,0,6])
        hand=hand*(1-p['thigh_hands'])+thigh*p['thigh_hands']
        ik(f,side,('upperarm','lowerarm','hand'),hand,origin+turn@np.array([sign*48,-8,28]))
        handrot(f,side,turn@np.array(p['hand_forward']),turn@np.array(p['hand_normal']))
    return f

def key(hip,yaw,lean,feet,foot_pitch,hands,forward=(0,1,0),normal=(0,0,-1),thigh_hands=0,neck_lift=0,flatness=0):
    return dict(hip=hip,yaw=yaw,lean=lean,feet=feet,foot_pitch=foot_pitch,hands=hands,hand_forward=forward,hand_normal=normal,thigh_hands=thigh_hands,neck_lift=neck_lift,flatness=flatness)
def pair(origin,dx,y,z,yaw=0):
    m=R.from_euler('z',yaw,degrees=True).as_matrix();o=np.asarray(origin)
    return {s:(o+m@np.array([k*dx,y,z])).tolist() for s,k in [('l',1),('r',-1)]}
def sample(keys,t):
    j=next((j for j in range(len(keys)-1) if t<=keys[j+1][0]),len(keys)-2)
    ta,a=keys[j];tb,b=keys[j+1];u=ease((t-ta)/(tb-ta))
    def mix(a,b):
        if isinstance(a,dict):return {k:mix(a[k],b[k]) for k in a}
        return np.asarray(a)*(1-u)+np.asarray(b)*u
    return mix(a,b)

def chair(height,sofa=False,clearance=12,front=40):
    h=height+clearance;front=14 if sofa else front
    end=key([0,0,h],0,12 if sofa else 3,pair([0,0,0],12,front,8),0,pair([0,0,h],16,24,6),thigh_hands=1)
    stand=key([0,70,86.38],0,0,pair([0,0,0],12,72,8),0,pair([0,70,0],24,1,68),forward=(0,.12,-1),normal=(1,0,.12))
    load=key([0,45,82],0,-23,pair([0,0,0],12,57,8),0,pair([0,45,0],18,21,64),thigh_hands=.6)
    land=key([0,0,h+1],0,-12,pair([0,0,0],12,front,8),0,pair([0,0,h],16,24,7),thigh_hands=1)
    keys=[(0,stand),(.45,load),(1.25,land),(1.85,end)]
    for _,p in keys:
        for f in p['feet'].values():f[2]+=1
    return keys

def bed(height,width,bunk=False,clinical=False):
    e=width/2;h=height+(15.5 if bunk else (13 if height<70 else 16) if clinical else 12);y=(32 if height<70 else 20) if clinical else 6;lean=48 if bunk else 12
    foot_length=61 if clinical and height<70 else 78
    hand_z=height+(12 if bunk else 10 if clinical else 7.5)
    start=[e+54,y,86.38]
    stand=key(start,-90,0,pair([e+54,y,0],12,2,8,-90),0,pair([e+54,y,0],24,0,68,-90),forward=(0,.12,-1),normal=(1,0,.12))
    load=key([e+45,y,82],-90,-18,pair([e+54,y,0],12,2,8,-90),0,pair([e+45,y,0],18,15,65,-90))
    hanging=max(8,height-57)
    # Pelvis stays on the side edge while both feet clear the mattress height.
    sit=key([e+3,y,h],-90,lean,pair([e+3,y,0],12,35,hanging,-90),0,pair([e+3,y,hand_z],23,-12,0,-90))
    lift=key([e+3,y,h+2],-90,max(35,lean),pair([e+3,y,height],12,51,24,-90),50,pair([e+3,y,hand_z],23,-15,0,-90))
    swing=key([e-19,y,h+2],-48,55 if bunk else 42,pair([e-19,y,height],12,foot_length-12,23,-48),70,pair([e-19,y,hand_z],24,-16,0,-48))
    rest_x=-12 if clinical and height>=70 else 0
    settle=key([rest_x,y,h],0,68,pair([rest_x,y,height],12,foot_length-1,13),85,pair([rest_x,y,hand_z],25,-7,0),flatness=.4 if bunk or clinical else 0)
    end=key([rest_x,y,h],0,88,pair([rest_x,y,height],12,foot_length,10),88,pair([rest_x,y,hand_z],24,-5,0),neck_lift=-18 if bunk else -5,flatness=1 if bunk or clinical else 0)
    keys=[(0,stand),(.5,load),(1.35,sit),(2.15,lift),(3.0,swing),(3.85,settle),(4.6,end)]
    if bunk:
        load['hip'][2]=76;load['lean']=-16
        duck=key([e+38,y,58],-90,-8,pair([e+45,y,0],12,8,9,-90),0,pair([e+38,y,height+8],23,-35,0,-90))
        keys.insert(2,(.9,duck))
        # The ladder is on +Y of the static mesh. Enter the open, opposite side.
        for _,p in keys:
            p['hip'][0]*=-1;p['yaw']*=-1
            for field in ('feet','hands'):
                a,b=p[field]['l'],p[field]['r'];p[field]={'l':[-b[0],b[1],b[2]],'r':[-a[0],a[1],a[2]]}
    for _,p in keys:
        for f in p['feet'].values():f[2]+=1
    return keys

specs={'Chair':(49,0),'Chair50':(50,0),'Chair52':(52,0),'Chair53':(53,0),'Chair55':(55,0),'Bench':(48.5,0),'Sofa':(65,0),
       'Bed':(67,150),'BedKing':(67,180),'Hospital':(58.67,122.67),'Ward':(88,184),'Bunk':(70,84)}
selected=sys.argv[sys.argv.index('--kinds')+1].split(',') if '--kinds' in sys.argv else list(specs)
clips={};cameras={};types={}
if '--kinds' in sys.argv and (OUT/'authored.json').exists():
    clips=json.loads((OUT/'authored.json').read_text())['clips'];previous=json.loads((OUT/'furniture_rest.json').read_text(encoding='utf-8'))
    cameras=previous['clips'];types=previous['types']
for kind in selected:
    h,width=specs[kind];keys=bed(h,width,kind=='Bunk',kind in ('Ward','Hospital')) if width else chair(h,kind=='Sofa',{'Sofa':14,'Chair53':15,'Chair55':14,'Bench':13,'Chair50':14,'Chair52':15}.get(kind,12),22 if kind=='Chair55' else 40)
    frames=[pose(sample(keys,t)) for t in np.linspace(0,keys[-1][0],round(keys[-1][0]*30)+1)]
    idle=[]
    for i in range(121):
        p=sample(keys,keys[-1][0]);p['lean']+=.28*math.sin(2*math.pi*i/120)**2;idle.append(pose(p))
    exit_duration=4.6 if width else 1.85
    leave=[pose(sample(keys,keys[-1][0]*(1-ease(t/exit_duration)))) for t in np.linspace(0,exit_duration,round(exit_duration*30)+1)]
    leave.extend([leave[-1].copy() for _ in range(9)])
    types[kind]={'lying':bool(width),'surface_height':h,'entry_offset':keys[0][1]['hip'][:2]+[0], 'entry_yaw':keys[0][1]['yaw']}
    for phase,take in [('Enter',frames),('Idle',idle),('Exit',leave)]:
        duration=(len(take)-1)/30;role=f'Rest.{kind}.{phase}';camera=[]
        for f in take:
            w=fk(f);head=w[ix['head']];eye=head[:3,3]+head[:3,:3]@bind[ix['head'],:3,:3].T@np.array([0,7,6])
            chest=w[ix['spine_03'],:3,3]-w[hip,:3,3];pitch=math.degrees(math.atan2(np.linalg.norm(chest[:2]),max(.01,chest[2])))
            forward=head[:3,:3]@bind[ix['head'],:3,:3].T@np.array([0,1,0])
            camera.append([*eye.tolist(),pitch*.72,math.degrees(math.atan2(-forward[0],forward[1]))])
        clips[role]={'rate':30,'duration':duration,'frames':np.asarray(take).tolist()};cameras[role]={'duration':duration,'camera':camera}
    print('SOLVED',kind,flush=True)
profiles=json.loads((ROOT/'SourceAssets/FurnitureRest20261022/furniture_rest.json').read_text(encoding='utf-8'))['furniture']
for p in profiles:
    mesh=p['mesh']
    for s in p['slots']:
        if s['kind']=='Chair':s['seat'][1]+=7
        if s['kind']=='Sofa':s['seat'][1]=40
        if 'ErgonomicChair' in mesh:s['kind']='Chair52';s['yaw']=270;s['seat'][1]=-15
        if 'VisitorChair' in mesh:s['kind']='Chair50';s['yaw']=270;s['seat'][1]=-10
        if 'ChangingBench' in mesh:s['kind']='Bench';s['seat'][2]=48.5;s['seat'][1]=10
        if 'Waiting_Bench' in mesh:s['kind']='Chair55'
        if 'TrainingBench' in mesh:s['kind']='Chair53';s['seat'][1]=47
        if 'BedKing' in mesh:s['kind']='BedKing'
        if 'SM_Ward_HospitalBed' in mesh:s['kind']='Ward'
        elif 'SM_HospitalBed' in mesh:s['kind']='Hospital'
    if 'Waiting_Bench' in mesh:
        p['slots']=[dict(kind='Chair55',seat=[x,22,55],yaw=90) for x in (-84,-28,28,84)]
(OUT/'authored.json').write_text(json.dumps(dict(mesh=source['mesh'],skeleton=source['skeleton'],names=names,parents=parents,reference=ref.tolist(),clips=clips),separators=(',',':')))
(OUT/'furniture_rest.json').write_text(json.dumps(dict(version=2,types=types,furniture=profiles,clips=cameras),ensure_ascii=False,indent=2),encoding='utf-8')
