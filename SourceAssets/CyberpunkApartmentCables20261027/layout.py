"""Production cable routes. Coordinates are metres in each furniture's author frame.

Only free spans simulate. Small rounded guides carry the line past a hard edge,
because CableComponent sweeps particles rather than the full segment capsule.
"""
from pathlib import Path
import math, json
R=Path(__file__).resolve().parent
SNAP=json.loads((R/'scene_inputs.json').read_text())
ACTORS={a['actor']:a for a in SNAP['actors']}
PARAMETERS=dict(num_sides=12,solver_iterations=12,substep_time=1/120.,
    use_substepping=True,enable_collision=True,collision_friction=.18,
    cable_gravity_scale=1.,enable_stiffness=False,
    skip_cable_update_when_not_visible=True,skip_cable_update_when_not_owner_recently_rendered=False)

def local(actor,p,component=None):
    return dict(actor=actor,p=list(p),component=component)

def world(p):return dict(actor=None,p=list(p),component=None)

def position(a):
    if not a['actor']:return a['p']
    row=ACTORS[a['actor']]
    c=next((c for c in row['components'] if c['name']==a['component']),row['components'][0])
    q=(a['p'][0]*100,-a['p'][1]*100,a['p'][2]*100)
    return [c['p'][i]+sum(q[j]*c['axes'][j][i] for j in range(3)) for i in range(3)]

ROUTES=[]
def span(name,a,b,slack=1.10,width=.42,extra=0):
    dist=math.dist(position(a),position(b));length=dist*slack+extra
    ROUTES.append(dict(name=name,start=a,end=b,length_cm=round(length,3),
        width_cm=width,segments=max(12,min(64,math.ceil(length/2.5)))))

DESKS=[dict(room='Office',actor='AP_Office_Workstation',half=.40,w=2.30,xs=[-.62,0,.62],wall=[24.2,-417.5,48],normal=[1,0,0]),
       dict(room='Bed2',actor='AP_Bed2_Desk',half=.34,w=1.65,xs=[-.15],wall=[2530,-24.2,48],normal=[0,-1,0]),
       dict(room='Bed3',actor='AP_Bed3_Desk',half=.34,w=1.65,xs=[-.15],wall=[2975.8,-1427.5,55],normal=[-1,0,0])]
HARDWARE=[]
for d in DESKS:
    host=d['actor'];h=d['half'];room=d['room'];pc=host+'_PC'
    HARDWARE.append(dict(key=room+'DeskRouting',parent=host))
    # Display-link docks supply the display and carry its video link; two
    # independent flexible spans per lead, separated by a rounded desk guide.
    for i,x in enumerate(d['xs']):
        x+=.075 # Clear the central monitor support tube.
        a=(x,.255,1.12);entry=(x,h-.018,.8125);exit=(x,h+.035,.715)
        dock=(-.36+i*.08,h+.035,.690)
        span(room+'_Display'+str(i+1)+'_Top',local(host,a),local(host,entry),1.07,extra=1.0)
        span(room+'_Display'+str(i+1)+'_Drop',local(host,exit),local(host,dock),1.10,extra=2.0)
    for side,x in [('L',-d['w']/2+.13),('R',d['w']/2-.13)]:
        entry=(x,h-.018,.8125);exit=(x,h+.035,.715)
        span(room+'_Speaker'+side+'_Top',local(host,(x,.237,.86)),local(host,entry),1.08,.32,1)
        span(room+'_Speaker'+side+'_Drop',local(host,exit),local(host,(-.18 if side=='L' else -.10,h+.045,.67)),1.045,.32,1)
    span(room+'_PC_Data',local(pc,(-.06,.265,.40)),local(host,(-.03,h+.035,.69)),1.12,.38,3)
    span(room+'_PC_Power',local(pc,(.06,.265,.12)),local(host,(-.25,h+.045,.67)),1.10,.62,3)
    w=[d['wall'][i]+d['normal'][i]*3.8 for i in range(3)]
    span(room+'_WallFeed',world(w),local(host,(-.40,h+.045,.67)),1.12,.62,3)
    HARDWARE.append(dict(key='PCPorts',parent=pc))

# Headphones: one upper lead to the back-edge guide and one under-desk return.
span('Bed2_Headphones_Top',local('BP_Headphones',(.092,0,.085)),local('AP_Bed2_Desk',(.56,.322,.8125)),1.13,.28,3)
span('Bed2_Headphones_Return',local('AP_Bed2_Desk',(.56,.375,.715)),local('AP_Bed2_Desk',(-.25,.385,.65)),1.045,.28,2)
HARDWARE.append(dict(key='HeadphoneSocket',parent='BP_Headphones'))

# Exposed appliance connectors sit outside their cabinet skins. Service loops
# are confined to rear/side service spaces, not the moving doors or walkway.
span('Laundry_Washer',world([28.0,-1330,110]),local('AP_Laundry_Washer',(-.24,.345,.70)),1.12,.62,3)
span('Kitchen_Fridge',world([1120,-2034.7,125]),local('AP_Container_Fridge_Lower',(.21,.409,.23),'Body'),1.055,.70,2)
span('Living_TV_Power',world([2109.5,-650,55]),world([2103,-630,89]),1.16,.52,2)
span('Living_TV_Data',world([2109.5,-655,55]),world([2103,-635,89]),1.12,.35,2)
span('Gym_Power',local('AP_Gym_Treadmill',(-.50,.85,.09)),world([285,-2160,3.4]),1.12,.65,4)
span('Gym_Safety',local('AP_Gym_Treadmill',(.27,.38,1.16)),local('AP_Gym_Treadmill',(.17,.382,1.14)),1.0,.30,20)
HARDWARE.extend([dict(key='WasherSocket',parent='AP_Laundry_Washer'),dict(key='FridgeSocket',parent='AP_Container_Fridge_Lower',component='Body'),dict(key='GymRouting',parent='AP_Gym_Treadmill'),dict(key='WorldTerminals',parent=None)])

# A pendant's suspension is under tension. Keep its actual ceiling and shade
# anchors and full hanging length; only tiny length tolerance, no sideways loop.
for i,x in enumerate((7.85,8.85)):
    span('Dining_Pendant'+str(i+1),local('AP_PracticalLights',(x,10.28,3.6825)),local('AP_PracticalLights',(x,10.28,2.425)),1.0003,1.2)

REPLACEMENTS=[('AP_Office_Workstation','CyberWorkstation'),('AP_Bed2_Desk','WritingDesk'),('AP_Bed3_Desk','WritingDesk'),('AP_Gym_Treadmill','Treadmill'),('BP_Headphones','Headphones'),('BP_DeskCableTray','DeskCableTray'),('AP_PracticalLights','PracticalLights')]
