"""Author camera-space poses from the observed native video frames.

The optimization is part of pose construction, not an animation acceptance test.
It holds bone lengths and the accepted closed grasp, and fits only rotation and
rigid placement. Screen landmarks are approximate observations; hidden depth is
explicitly reconstructed. No source-game bone tracks are used.
"""
import json
import math
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation as R

P = Path(__file__).parent
inputs = json.loads((P/'authoring_inputs.json').read_text())
annotations = json.loads((P/'reference_annotations.json').read_text(encoding='utf-8'))
bones = inputs['bones']
rest = {n:np.array(v['rest']) for n,v in bones.items()}
idle = {n:np.array(v['idle']) for n,v in bones.items()}
parent = {n:v['parent'] for n,v in bones.items()}
H0, W0 = idle['hand_r'], idle['WPN_root']
G = np.linalg.inv(W0)@H0
Hinv = np.linalg.inv(H0)
hand_closed = {n:Hinv@m for n,m in idle.items()}
hand_rest = {n:np.linalg.inv(rest['hand_r'])@m for n,m in rest.items()}
local_closed = {n:np.linalg.inv(idle[parent[n]])@m for n,m in idle.items() if parent[n]}
A = np.array([.0285727177,.102494739,.994323134])
L = np.array([-.994306445,.105071038,.017741533])
N = np.cross(A,L)
F = 240/math.tan(math.radians(75/2))
CX,CY=426.,240.

def unit(v):
    v=np.asarray(v,float)
    return v/max(np.linalg.norm(v),1e-10)

def transform(q, t):
    m=np.eye(4);m[:3,:3]=q;m[:3,3]=t;return m

def project(v):
    v=np.asarray(v)
    return np.stack([CX+F*v[...,0]/np.maximum(v[...,1],.03),CY-F*v[...,2]/np.maximum(v[...,1],.03)],axis=-1)

def ray(pixel, depth):
    return np.array([(pixel[0]-CX)*depth/F,depth,-(pixel[1]-CY)*depth/F])

def rot_between(a,b):
    a,b=unit(a),unit(b);v=np.cross(a,b);dot=np.clip(np.dot(a,b),-1,1)
    if np.linalg.norm(v)<1e-8:
        if dot>0:return np.eye(3)
        axis=unit(np.cross(a,[1,0,0] if abs(a[0])<.8 else [0,1,0]))
        return R.from_rotvec(axis*math.pi).as_matrix()
    return R.from_rotvec(unit(v)*math.acos(dot)).as_matrix()

PALM_LOCAL=np.column_stack([A,L,N])

def palm_seed(row):
    middle=(np.array(row['index_mcp'])+row['pinky_mcp'])/2
    delta=middle-np.array(row['wrist'])
    l=unit([delta[0],row['palm_long_depth']*np.linalg.norm(delta),-delta[1]])
    n=unit(row['palm_normal_prior']);n=unit(n-l*np.dot(n,l))
    a=unit(np.cross(l,n))
    return np.column_stack([a,l,n])@PALM_LOCAL.T

def hand_points(H):
    return np.array([H[:3,3],(H@hand_closed['index_01_r'])[:3,3],
                     (H@hand_closed['pinky_01_r'])[:3,3]])

def fit_hand(row):
    q=palm_seed(row);w=np.array(row['wrist'],float)
    target=np.array([w,row['index_mcp'],row['pinky_mcp']])
    def decode(x):return transform(R.from_rotvec(x[3:]).as_matrix()@q,ray(x[:2],math.exp(x[2])))
    def cost(x):
        H=decode(x)
        return np.r_[((project(hand_points(H))-target)*np.array([[1.5],[.65],[.65]])/12).ravel(),
                     x[3:]/.30,(x[2]-math.log(.29))/.50]
    x0=np.r_[w,math.log(.29),[0.,0.,0.]]
    solution=least_squares(cost,x0,bounds=(np.r_[w-20,math.log(.17),[-.6]*3],
                                         np.r_[w+20,math.log(.48),[.6]*3]),max_nfev=100)
    return decode(solution.x)

def weapon_seed(row,H):
    delta=np.array(row['guard'])-row['pommel']
    shaft=unit([delta[0],row['shaft_depth_prior']*np.linalg.norm(delta),-delta[1]])
    # Roll is seeded from the accepted hand/hilt relation, independently of shaft
    # direction. The solver can adapt the visible guard edge without flipping it.
    held=H@np.linalg.inv(G)
    q=rot_between(held[:3,2],shaft)@held[:3,:3]
    return q

def fit_closed(row,Hseed,prev=None):
    seed=weapon_seed(row,Hseed)
    hilt=np.array([[0,0,0,1],[0,0,-.265,1]])
    target=np.array([row['guard'],row['pommel']])
    hands=np.array([row['wrist'],row['index_mcp'],row['pinky_mcp']])
    def decode(x):return transform(R.from_rotvec(x[3:]).as_matrix()@seed,ray(x[:2],math.exp(x[2])))
    def cost(x):
        W=decode(x);H=W@G
        e=[((project((W@hilt.T).T[:,:3])-target)/13).ravel(),
           ((project(hand_points(H))-hands)*np.array([[1.2],[.55],[.55]])/15).ravel(),
           x[3:]/.8,[(x[2]-math.log(.29))/.6]]
        return np.concatenate(e)
    center=np.array(row['guard'],float)
    x0=np.r_[center,math.log(.29),[0.,0.,0.]]
    solution=least_squares(cost,x0,bounds=(np.r_[center-55,math.log(.14),[-1.5]*3],
                                         np.r_[center+55,math.log(.65),[1.5]*3]),max_nfev=150)
    W=decode(solution.x)
    return W@G,W

# Individual support stations for each observed phase; these are depth priors,
# not a claim to have measured an invisible pressure point in the video.
SUPPORT = {
 1:(.036,.064,.019,-.074),2:(.041,.061,.022,-.077),
 3:(.047,.056,.024,-.082),4:(.050,.054,.023,-.087),
 5:(.052,.052,.023,-.092),6:(.052,.054,.024,-.094),
 7:(.047,.060,.024,-.085),8:(.040,.065,.021,-.077),
}

def fit_open(row,Hseed):
    frame=row['frame'];qs=weapon_seed(row,Hseed)
    a,l,n,station=SUPPORT[frame]
    anchor=A*a+L*l+N*n
    targets=np.array([row['guard'],row['pommel']],float)
    hands=np.array([row['wrist'],row['index_mcp'],row['pinky_mcp']],float)
    hilt=np.array([[0,0,0,1],[0,0,-.265,1]])
    center=np.array(row['guard'],float)
    def decode(x):
        W=transform(R.from_rotvec(x[3:6]).as_matrix()@qs,ray(x[:2],math.exp(x[2])))
        H=transform(R.from_rotvec(x[9:12]).as_matrix()@Hseed[:3,:3],Hseed[:3,3]+x[6:9])
        return H,W
    def cost(x):
        H,W=decode(x)
        hand_anchor=(H@np.r_[anchor,1])[:3]
        station_center=(W@np.array([0,0,station,1]))[:3]
        rad=hand_anchor-station_center;rad-=W[:3,2]*np.dot(rad,W[:3,2])
        # Hilt radius comes from the selected model's grip cross-section.
        contact=station_center+unit(rad)*.022
        e=[((project((W@hilt.T).T[:,:3])-targets)/12).ravel(),
           ((project(hand_points(H))-hands)*np.array([[1.25],[.6],[.6]])/14).ravel(),
           (hand_anchor-contact)/.008,x[3:6]/.8,x[6:9]/.035,x[9:12]/.25,
           [(x[2]-math.log(.29))/.65]]
        return np.concatenate(e)
    x0=np.r_[center,math.log(.29),np.zeros(9)]
    solution=least_squares(cost,x0,bounds=(np.r_[center-65,math.log(.14),[-1.6]*3,[-.10]*3,[-.7]*3],
                                         np.r_[center+65,math.log(.65),[1.6]*3,[.10]*3,[.7]*3]),max_nfev=220)
    return decode(solution.x)

def depth(n):return 1+depth(parent[n]) if parent[n] else 0
fingers=sorted([n for n in bones if n.endswith('_r') and n.startswith(('thumb','index','middle','ring','pinky'))],key=depth)
segment_axis={}
closed_angles={}
for digit in ['index','middle','ring','pinky','thumb']:
    values=[]
    for j in range(1,4):
        name=f'{digit}_{j:02d}_r';next_name=f'{digit}_{j+1:02d}_r'
        if j<3:
            axis=hand_rest[next_name][:3,3]-hand_rest[name][:3,3]
            direction=hand_closed[next_name][:3,3]-hand_closed[name][:3,3]
        else:
            prev=f'{digit}_{j-1:02d}_r'
            # Distal skin extends along the transported incoming segment.
            axis=hand_rest[name][:3,3]-hand_rest[prev][:3,3]
            incoming=hand_closed[name][:3,3]-hand_closed[prev][:3,3]
            relative=hand_closed[name][:3,:3]@hand_closed[prev][:3,:3].T
            direction=relative@incoming
        segment_axis[name]=unit(axis)
        v=unit(direction)
        values.append(math.degrees(math.atan2(np.dot(v,N),np.dot(v,L))))
    closed_angles[digit]=np.diff([0]+list(np.rad2deg(np.unwrap(np.deg2rad(values))))).tolist()

BASE={'index':[60,75,35],'middle':[65,78,38],'ring':[68,80,40],'pinky':[70,81,41]}
THUMB = [
 None,
 [[.60,.65,.45],[.55,.70,.45],[.44,.74,.49]],
 [[.82,.44,.28],[.82,.46,.33],[.78,.48,.40]],
 [[.88,.36,.22],[.88,.36,.30],[.84,.38,.39]],
 [[.92,.28,.20],[.91,.30,.26],[.88,.34,.31]],
 [[.94,.22,.15],[.94,.24,.18],[.92,.28,.21]],
 [[.95,.19,.14],[.94,.21,.19],[.91,.27,.29]],
 [[.89,.32,.29],[.80,.40,.44],[.67,.42,.61]],
 [[.77,.43,.46],[.57,.42,.70],[.38,.33,.86]],
]

def finger_pose(row, digit_params=None, thumb_delta=None):
    frame=row['frame'];p={'hand_r':np.eye(4)};loc={}
    if frame==0 or frame>=9:
        return {n:local_closed[n].copy() for n in fingers}
    params=digit_params or row['digits']
    for name in fingers:
        digit=name.split('_')[0]
        if 'metacarpal' in name:
            cup={'index':0,'middle':-.3,'ring':-2.,'pinky':-4.}[digit]
            # Small independent palm cupping follows the observed open/catch
            # section; it does not translate finger roots to chase the hilt.
            cup*= [0,.15,.35,.65,.85,1,1,.55,.2][frame]
            m=local_closed[name].copy();m[:3,:3]=R.from_rotvec(L*math.radians(cup)).as_matrix()@m[:3,:3]
            p[name]=p[parent[name]]@m;loc[name]=m;continue
        j=int(name.split('_')[1])-1
        if digit=='thumb':
            direction=unit(A*THUMB[frame][j][0]+L*THUMB[frame][j][1]+N*THUMB[frame][j][2])
            if thumb_delta is not None:
                direction=R.from_rotvec(np.asarray(thumb_delta)).apply(direction)
        else:
            flex=np.array(params[digit][:3])*np.array(closed_angles[digit])/np.array(BASE[digit])
            curl=math.radians(sum(flex[:j+1]));spread=math.radians(params[digit][3])
            direction=unit((L*math.cos(spread)+A*math.sin(spread))*math.cos(curl)+N*math.sin(curl))
        q=rot_between(segment_axis[name],direction)@hand_rest[name][:3,:3]
        translation=(p[parent[name]]@np.r_[local_closed[name][:3,3],1])[:3]
        p[name]=transform(q,translation)
        loc[name]=np.linalg.inv(p[parent[name]])@p[name]
    return loc

def fingertip(H,local,digit):
    p=H.copy()
    meta=f'{digit}_metacarpal_r'
    if meta in local:p=p@local[meta]
    for j in range(1,4):p=p@local[f'{digit}_{j:02d}_r']
    # The vertex mesh is retained. This endpoint is only a fitting landmark,
    # not a mesh collision/contact claim.
    n=f'{digit}_03_r'
    direction=hand_rest[n][:3,:3].T@segment_axis[n]
    length={'thumb':.023,'index':.019,'middle':.023,'ring':.022,'pinky':.018}[digit]
    return (p@np.r_[direction*length,1])[:3]

def fit_digits(row,H):
    params=json.loads(json.dumps(row['digits']));thumb_delta=np.zeros(3)
    if row['frame'] not in range(1,9):return finger_pose(row),params,thumb_delta
    for digit,target in row['tips'].items():
        if digit=='thumb':
            def cost(x):
                local=finger_pose(row,params,x)
                return np.r_[(project(fingertip(H,local,digit))-target)/10,x/.20]
            sol=least_squares(cost,np.zeros(3),bounds=(-.40,.40),max_nfev=55)
            thumb_delta=sol.x
        else:
            seed=np.array(params[digit],float)
            def cost(x):
                trial=dict(params);trial[digit]=x.tolist();local=finger_pose(row,trial,thumb_delta)
                return np.r_[(project(fingertip(H,local,digit))-target)/10,(x-seed)/np.array([14,18,15,8])]
            low=np.maximum(seed-[16,22,18,12],[-6,0,0,-38])
            high=np.minimum(seed+[16,22,18,12],[90,100,70,25])
            sol=least_squares(cost,seed,bounds=(low,high),max_nfev=70)
            params[digit]=sol.x.tolist()
    return finger_pose(row,params,thumb_delta),params,thumb_delta

frames=[]
for row in annotations['records']:
    f=row['frame'];Hseed=fit_hand(row)
    H,W=fit_open(row,Hseed) if 1<=f<=8 else fit_closed(row,Hseed)
    local,params,thumb=fit_digits(row,H)
    frames.append({'frame':f,'video_seconds':row['video_seconds'],'hand_r':H.tolist(),'weapon':W.tolist(),
                   'finger_local':{n:m.tolist() for n,m in local.items()},
                   'authored_finger_degrees':params,'thumb_adjustment_radians':thumb.tolist(),
                   'grip':'changing contact' if 1<=f<=8 else 'accepted closed grasp',
                   'palm_observation':row['observation']})
    if f%10==0:print('REFERENCE_POSE_AUTHORED',f,flush=True)
(P/'reference_poses.json').write_text(json.dumps({'fps':30,'duration':2,'frames':frames,
    'method':'Native-frame observed landmark fitting and independent articulated digit poses',
    'depth':'Inferred from one view and existing model dimensions',
    'testing':'No rendered, collision or runtime acceptance performed'},indent=2),encoding='utf-8')
print('REFERENCE_POSES_READY',len(frames),flush=True)
