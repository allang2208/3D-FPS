"""Deep sofa sitting with hanging legs, relaxed hands and separate exit contacts."""
import copy, json, math
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R, Slerp

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'SourceAssets/FurnitureRest20261022/RelaxedSeatV5'
OUT.mkdir(parents=True,exist_ok=True)
ns={'__file__':str(ROOT/'Tools/FurnitureRest/refine.py')}
exec((ROOT/'Tools/FurnitureRest/refine.py').read_text().split('specs=')[0],ns)
fk,rot,ik,handrot,ease,ix,bind,ref,pose,key,pair,sample=[ns[n] for n in
    ('fk','rot','ik','handrot','ease','ix','bind','ref','pose','key','pair','sample')]
source=ns['source']
def world(f,i):
    chain=[]
    while i>=0:
        chain.append(i);i=source['parents'][i]
    chain.reverse();rows=f[chain]
    matrices=np.tile(np.eye(4),(len(chain),1,1))
    matrices[:,:3,:3]=R.from_quat(rows[:,3:7]).as_matrix()*rows[:,None,7:]
    matrices[:,:3,3]=rows[:,:3]
    w=np.eye(4)
    for m in matrices:w=w@m
    return w
def rot(f,i,q):
    parent=source['parents'][i]
    f[i,3:7]=R.from_matrix(world(f,parent)[:3,:3].T@q if parent>=0 else q).as_quat()
ns['rot']=rot
configs={name:json.loads((ROOT/'Content/ColdSteelData'/name).read_text(encoding='utf-8-sig'))
         for name in ('furniture_rest.json','apartment_furniture_rest.json')}
result={k:source[k] for k in ('mesh','skeleton','names','parents','reference')}
result['clips']={};milestones={}

def blendrot(a,b,t):
    return Slerp([0,1],R.from_matrix(np.array([a,b])))(float(np.clip(t,0,1))).as_matrix()

def routes(apartment):
    # Keep the approach and seat anchor; the authored pelvis travels deeper.
    depth=24.
    start_y=74. if apartment else 70.
    front=27. if apartment else 14.
    standing=key([0,start_y,86.38],0,0,pair([0,0,0],12,start_y,9),0,
                 pair([0,start_y,0],24,1,68),forward=(0,.12,-1),normal=(1,0,.12))
    load=key([0,45,83],0,-20,pair([0,0,0],13,57,9),0,
             pair([0,45,0],18,21,67),thigh_hands=.6)
    edge=key([0,0,80],0,-7,pair([0,0,0],13,front,9),0,
             pair([0,0,79],16,18,10),thigh_hands=.8)
    # A nearly horizontal thigh clears the cushion. Calves hang forward of
    # the front upholstery; ankle height follows bone lengths, not the floor.
    end=key([0,-depth,79],0,5,pair([0,0,0],14,47-depth,35),-12,
            pair([0,-depth,0],16,14,90))
    end['feet']['l'][1]+=.8;end['feet']['r'][1]-=1.2;end['feet']['r'][2]+=.6
    scoot=copy.deepcopy(end);scoot['hip'][1]+=.8;scoot['hip'][2]+=.4
    scoot['lean']=-3
    enter=[(0,standing),(.5,load),(1.15,edge),(2.05,scoot),(2.8,end)]
    # Gather the feet on the floor before the pelvis rises out of the seat.
    reach=copy.deepcopy(edge);reach['lean']=-10
    leave=[(0,end),(.45,end),(1.35,reach),(1.6,reach),(2.2,load),(2.8,standing),(3.1,standing)]
    return enter,leave,end,depth

def relaxed_hands(f,original,outer,depth,weight,phase,t,apartment):
    base_world=fk(original)
    for side,sign in [('l',1),('r',-1)]:
        support=side==outer
        # Placement starts at different times, after the seat takes the weight.
        delay=1.05 if support else (1.25 if side=='l' else 1.42)
        contact=float(ease((t-delay)/(2.65-delay))) if phase=='Enter' else 1. if phase=='Idle' else float(1-ease((t-.5)/1.05))
        if contact<1e-8:continue
        w=fk(f);cl=ix['clavicle_'+side]
        rot(f,cl,R.from_euler('y',sign*1.5*weight,degrees=True).as_matrix()@w[cl,:3,:3])
        if support:
            target=np.array([sign*(38 if apartment else 35),-depth+(24 if apartment else 23),99.1 if apartment else 97.9])
            forward=np.array([sign*.04,.68,-.73]);normal=np.array([0.,-.73,-.68])
        else:
            target=np.array([sign*(15 if side=='l' else 18),-depth+(12 if side=='l' else 15),90 if side=='l' else 89.5])
            forward=np.array([-sign*.16,1.,-.13]);normal=np.array([sign*.08,-.13,-1.])
        hand=base_world[ix['hand_'+side],:3,3]*(1-contact)+target*contact
        hand+=np.array([sign*2,0,4])*math.sin(math.pi*contact)
        shoulder=fk(f)[ix['upperarm_'+side],:3,3]
        pole=shoulder+np.array([sign*(18 if support else 10),13,-28])
        ik(f,side,('upperarm','lowerarm','hand'),hand,pole)
        handrot(f,side,forward,normal)
        desired=fk(f)[ix['hand_'+side],:3,:3]
        rot(f,ix['hand_'+side],blendrot(base_world[ix['hand_'+side],:3,:3],desired,contact))
        # Give every finger its own flexion; no flat fan and no clenched fist.
        palmnormal=normal/np.linalg.norm(normal)
        # The native reference fingers are already curled. A resting palm
        # opens those joints slightly instead of adding another fist curl.
        amounts=({'index':(-16,-18,-8),'middle':(-15,-18,-8),'ring':(-13,-15,-7),
                  'pinky':(-10,-12,-6),'thumb':(-10,-8,-4)} if support else
                 {'index':(-4,-3,-2),'middle':(-3,-3,-2),'ring':(-1,-1,0),
                  'pinky':(2,1,1),'thumb':(-2,0,0)})
        for digit,angles in amounts.items():
            for joint,angle in enumerate(angles,1):
                bone=ix[f'{digit}_{joint:02d}_{side}'];wb=world(f,bone)
                if joint<3:direction=world(f,ix[f'{digit}_{joint+1:02d}_{side}'])[:3,3]-wb[:3,3]
                else:direction=wb[:3,3]-world(f,ix[f'{digit}_02_{side}'])[:3,3]
                axis=np.cross(direction,palmnormal);axis/=np.linalg.norm(axis)
                settle=float(ease((contact-(.04 if digit in ('ring','pinky') else 0))/.96))
                breath=.65*math.sin(math.pi*t/4)**2 if phase=='Idle' else 0.
                rot(f,bone,R.from_rotvec(axis*math.radians((angle+breath)*settle)).as_matrix()@wb[:3,:3])

for apartment in (False,True):
    config=configs['apartment_furniture_rest.json' if apartment else 'furniture_rest.json']
    prefix='ApartmentSofa' if apartment else 'Sofa'
    enter,leave,end,depth=routes(apartment)
    for suffix,outer in [('',None),('Left','r'),('Right','l')]:
        kind=prefix+suffix
        config['types'][kind]=dict(config['types'][prefix])
        milestones[kind]={'depth_cm':depth,'enter':[t for t,p in enter],'exit':[t for t,p in leave]}
        for phase,keys in [('Enter',enter),('Idle',None),('Exit',leave)]:
            duration=keys[-1][0] if keys else 4.
            frames=[];camera=[]
            for t in np.linspace(0,duration,round(duration*30)+1):
                p=copy.deepcopy(end) if keys is None else sample(keys,t)
                f=pose(p);original=f.copy();oldworld=fk(original)
                amount=float(ease((t-1.1)/1.55)) if phase=='Enter' else 1. if phase=='Idle' else float(1-ease((t-.45)/1.15))
                breath=.32*math.sin(math.pi*t/4)**2 if phase=='Idle' else 0.
                for bone,angle in [('spine_01',4),('spine_02',2),('spine_03',0),('spine_04',-2),('spine_05',-2),('neck_01',-1),('neck_02',0),('head',0)]:
                    lateral=(-1 if outer=='r' else 1 if outer else .2)*(5. if bone.startswith('spine') else 1.5)
                    target=R.from_euler('yx',[lateral,angle+breath],degrees=True).as_matrix()@bind[ix[bone],:3,:3]
                    rot(f,ix[bone],blendrot(oldworld[ix[bone],:3,:3],target,amount))
                relaxed_hands(f,original,outer,depth,amount,phase,float(t),apartment)
                w=fk(f);head=w[ix['head']]
                eye=head[:3,3]+head[:3,:3]@bind[ix['head'],:3,:3].T@np.array([0,7,6])
                camera.append([*eye.tolist(),0.,0.]);frames.append(f.tolist())
            role=f'Rest.{kind}.{phase}'
            result['clips'][role]={'rate':30,'duration':duration,'frames':frames}
            config['clips'][role]={'duration':duration,'camera':camera}
            print('RELAXED_SEAT_AUTHORED',role,len(frames),flush=True)
    for profile in config['furniture']:
        if profile['slots'][0]['kind'].startswith(prefix):
            for slot in profile['slots']:
                slot['kind']=prefix+('Left' if slot['seat'][0]<0 else 'Right' if slot['seat'][0]>0 else '')

(OUT/'authored.json').write_text(json.dumps(result,separators=(',',':')))
for name,cfg in configs.items():(OUT/name).write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding='utf-8')
merged=copy.deepcopy(configs['furniture_rest.json'])
for name in ('types','clips'):merged[name].update(configs['apartment_furniture_rest.json'][name])
merged['furniture']+=configs['apartment_furniture_rest.json']['furniture']
(OUT/'review_config.json').write_text(json.dumps(merged,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'contact_schedule.json').write_text(json.dumps(milestones,indent=2))
