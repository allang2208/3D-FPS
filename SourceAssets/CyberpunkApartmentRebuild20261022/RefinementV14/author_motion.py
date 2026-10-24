"""Apartment-sized rest takes. Native bone lengths; explicit contact milestones."""
import json,math,copy
from pathlib import Path
import numpy as np
from motion_math import key,pair,pose,sample,fk,bind,ix,ref,names,parents,source
R=Path(__file__).resolve().parent
DEST='/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV14/Meshes'

def bed_keys():
    # Centimetres, native body axes: +Y footward, +X left; open aisle is -X.
    e=105.;h=79.;floor=9.;y=0.
    standing=key([-e-56,y,86.38],90,0,pair([-e-56,y,0],13,0,floor,90),0,pair([-e-56,y,0],24,0,68,90),forward=(0,.12,-1),normal=(1,0,.12))
    load=key([-e-38,y,83],90,-16,pair([-e-51,y,0],13,0,floor,90),0,pair([-e-38,y,0],21,10,68,90))
    edge=key([-e-1,y,h],90,8,pair([-e-1,y,0],13,27,floor,90),0,pair([-e-1,y,74],24,-15,0,90))
    brace=key([-e-1,y,h+3],90,26,pair([-e-1,y,0],13,27,floor,90),0,pair([-e-1,y,74],24,-17,0,90))
    lift=key([-e-1,y,h+6],90,30,pair([-e-1,y,67],13,40,29,90),52,pair([-e-1,y,74],24,-17,0,90))
    swing=key([-75,y,h+6],46,44,pair([-75,y,67],13,63,28,46),72,pair([-75,y,74],25,-16,0,46))
    onbed=key([-40,y,h+2],0,48,pair([-40,y,67],13,72,18),86,pair([-40,y,74],24,-14,0))
    resting=key([-40,y,h],0,88,pair([-40,y,67],13,75,11),88,pair([-40,y,74],24,-7,0),flatness=1,neck_lift=0)
    enter=[(0,standing),(.55,load),(1.45,edge),(1.8,brace),(2.55,lift),(3.45,swing),(4.2,onbed),(5.35,resting)]
    # Independent exit: lift trunk, gather both legs, swing them fully beyond
    # the mattress edge, then lower feet. Standing begins only after contact.
    edge_high=copy.deepcopy(lift)
    edge_high['lean']=22
    edge_land=copy.deepcopy(edge)
    push=key([-e-27,y,78],90,-24,pair([-e-1,y,0],13,27,floor,90),0,pair([-e-27,y,0],18,22,68,90),thigh_hands=.7)
    up=key([-e-31,y,86.38],90,0,pair([-e-1,y,0],13,27,floor,90),0,pair([-e-31,y,0],24,0,68,90),forward=(0,.12,-1),normal=(1,0,.12))
    step=copy.deepcopy(up)
    step['hip'][0]=-e-45
    step['feet']['l'][0]=-e-54;step['feet']['l'][2]=15
    step['hands']=pair([-e-45,y,0],24,0,68,90)
    exit=[(0,resting),(.95,onbed),(1.85,swing),(2.6,edge_high),(3.4,edge_land),(3.7,edge_land),(4.15,push),(4.7,up),(5.05,step),(5.45,standing),(5.7,standing)]
    return enter,exit,resting

def sofa_keys():
    # Sitting close to the front welt leaves calves outside the enlarged base.
    standing=key([0,74,86.38],0,0,pair([0,0,0],13,74,9),0,pair([0,74,0],24,0,68),forward=(0,.12,-1),normal=(1,0,.12))
    load=key([0,44,82],0,-22,pair([0,0,0],13,54,9),0,pair([0,44,0],18,22,67),thigh_hands=.8)
    edge=key([0,0,79],0,-8,pair([0,0,0],13,27,9),0,pair([0,0,79],17,22,6),thigh_hands=1)
    seated=copy.deepcopy(edge);seated['lean']=12
    return [(0,standing),(.6,load),(1.5,edge),(2.15,seated)],[(0,seated),(.5,edge),(1.2,load),(1.95,standing),(2.2,standing)],seated

clips={};cameras={};types={};milestones={}
for kind,route in [('ApartmentBed',bed_keys()),('ApartmentSofa',sofa_keys())]:
    enter,leave,end=route
    take_idle=[]
    for i in range(121):
        p=copy.deepcopy(end);p['lean']+=.22*math.sin(math.pi*i/120)**2;take_idle.append(pose(p))
    types[kind]=dict(lying=kind=='ApartmentBed',surface_height=67 if kind=='ApartmentBed' else 65,entry_offset=enter[0][1]['hip'][:2]+[0],entry_yaw=enter[0][1]['yaw'])
    milestones[kind]=dict(enter=[t for t,p in enter],exit=[t for t,p in leave])
    for phase,keys in [('Enter',enter),('Idle',None),('Exit',leave)]:
        take=take_idle if keys is None else [pose(sample(keys,t)) for t in np.linspace(0,keys[-1][0],round(keys[-1][0]*30)+1)]
        duration=(len(take)-1)/30;role=f'Rest.{kind}.{phase}';camera=[]
        for f in take:
            w=fk(f);head=w[ix['head']];eye=head[:3,3]+head[:3,:3]@bind[ix['head'],:3,:3].T@np.array([0,7,6])
            camera.append([*eye.tolist(),0.,0.])
        clips[role]=dict(rate=30,duration=duration,frames=np.asarray(take).tolist());cameras[role]=dict(duration=duration,camera=camera)
        print('AP14_AUTHORED',role,len(take),flush=True)
profiles=[dict(mesh=DEST+'/SM_AP14_Bed.SM_AP14_Bed',caption='双人床',scale=[1.4,1.4,1.],slots=[dict(kind='ApartmentBed',seat=[0,-20,67],yaw=90)]),dict(mesh=DEST+'/SM_AP14_Sofa.SM_AP14_Sofa',caption='沙发',scale=[1.2,1.2,1.],slots=[dict(kind='ApartmentSofa',seat=[x,39,65],yaw=90) for x in (-75,0,75)])]
(R/'authored.json').write_text(json.dumps(dict(mesh=source['mesh'],skeleton=source['skeleton'],names=names,parents=parents,reference=ref.tolist(),clips=clips),separators=(',',':')))
(R/'apartment_furniture_rest.json').write_text(json.dumps(dict(version=1,types=types,furniture=profiles,clips=cameras),ensure_ascii=False,indent=2),encoding='utf-8')
(R/'contact_schedule.json').write_text(json.dumps(milestones,indent=2))
