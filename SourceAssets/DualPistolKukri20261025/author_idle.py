"""Pistol + off-hand kukri dual idle, authored to BV1hQnh6hEio (Krait P68 Commando full kit, knife-and-gun hold).

Candidate only; no Content or game code changes. Camera space: X forward, Y right, Z up, cm, eye at origin.
- Right: the accepted M1911 Contact idle grip, moved as one rigid gun+hand group (centred, canted), arm re-solved.
- Left: the off-hand SK_M4_BareArmsV7 arm with the accepted M4 VRE vertical-grip fist. The kukri sits reversed
  in that fist (blade out of the pinky side) as the reference knife is held; edge in = toward the palm heel.
- Native bone lengths, elbow hinge, forearm twist 100 %/50 %; V9 surface with JC_ correctives (v9_surface.py).
"""
import json, sys
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R

P = Path(__file__).resolve().parent
ROOT = P.parents[1]
V4 = ROOT/'SourceAssets/PistolBookPoseV4_20261020'
V9R = ROOT/'SourceAssets/BareSkinV9Rollout_20261017'
sys.path.insert(0, str(V9R)); sys.path.insert(0, str(P))
from jc import Driver
import v9_surface

def read(path): return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def unit(v): v=np.asarray(v,float);return v/np.linalg.norm(v)
def matrix(q,p):
    m=np.eye(4);m[:3,:3]=q;m[:3,3]=p;return m
def frame(x,z):
    x=unit(x);z=unit(z-x*np.dot(x,z));return np.column_stack((x,np.cross(z,x),z))
def convert(m):
    m=np.array(m);s=np.diag([1,-1,1]);return matrix(s@m[:3,:3]@s,100*s@m[:3,3])
def rest_of(s): return {n:matrix(R.from_quat(b['q']).as_matrix(),b['t']) for n,b in s['bones'].items()}
def parents_of(s):
    names={b['index']:n for n,b in s['bones'].items()}
    return {n:names.get(b['parent']) for n,b in s['bones'].items()}
def chain(n,root,parents):
    while n:
        if n==root:return True
        n=parents[n]
    return False

controls=read(P/'pose_controls.json')
surface=v9_surface.load()
LR=rest_of(surface['snapshot']);LP=parents_of(surface['snapshot'])
right=read(V9R/'Snapshots/8f309afe12dd.json');RR=rest_of(right);RP=parents_of(right)
src=read(V4/'contact_source.json');sr={n:convert(m) for n,m in src['rest'].items()}
raw=read(V9R/'ClipsTrue/M1911.json');m4=read(V9R/'ClipsTrue/M4.json')

def solve_arm(rest,source,parents,side,shoulder,wrist,pole,hand_rotation):
    """V4 solver: coherent elbow hinge + native 100/50 forearm roll; grasp locals untouched."""
    C,U,E,H=[n+'_'+side for n in ('clavicle','upperarm','lowerarm','hand')]
    ru=rest[E][:3,3]-rest[U][:3,3];rl=rest[H][:3,3]-rest[E][:3,3]
    a,b=np.linalg.norm(ru),np.linalg.norm(rl)
    shoulder=np.asarray(shoulder,float).copy();wrist=np.asarray(wrist,float);pole=np.asarray(pole,float)
    reach=wrist-shoulder;dist=np.linalg.norm(reach)
    if dist>(a+b)*.94:shoulder+=unit(reach)*(dist-(a+b)*.94)
    axis=unit(wrist-shoulder);dist=np.linalg.norm(wrist-shoulder)
    along=(a*a-b*b+dist*dist)/(2*dist);centre=shoulder+axis*along
    bend=unit(pole-centre-axis*np.dot(pole-centre,axis))
    elbow=centre+bend*np.sqrt(max(0,a*a-along*along))
    ud=unit(elbow-shoulder);ld=unit(wrist-elbow);normal=unit(np.cross(ud,ld))
    normal0=unit(np.cross(ru,rl))
    uq=frame(ud,normal)@frame(ru,normal0).T
    lq=frame(ld,normal)@frame(rl,normal0).T
    out={n:m.copy() for n,m in source.items()}
    out[U]=matrix(uq@rest[U][:3,:3],shoulder)
    out[E]=matrix(lq@rest[E][:3,:3],elbow)
    out[H]=matrix(hand_rotation,wrist)
    out[C][:3,3]+=shoulder-source[U][:3,3]
    delta=hand_rotation@rest[H][:3,:3].T@lq.T
    q=R.from_matrix(delta).as_quat()
    if q[3]<0:q=-q
    roll=2*np.arctan2(np.dot(q[:3],ld),q[3])
    for n in out:
        if not chain(n,C,parents) or n in (C,U,E,H):continue
        par=parents[n]
        donor=rest if 'twist_' in n else source
        out[n]=out[par]@np.linalg.inv(donor[par])@donor[n]
        if n in ('lowerarm_twist_01_'+side,'lowerarm_twist_02_'+side):
            factor=1. if '_01_' in n else .5
            out[n][:3,:3]=R.from_rotvec(ld*roll*factor).as_matrix()@out[n][:3,:3]
    return out,{'reach':float(dist/(a+b)),'shoulder_shift_cm':float(np.linalg.norm(shoulder-np.asarray(controls[side_key(side)+'_shoulder'],float)))}

def side_key(side): return 'right' if side=='r' else 'left'

def clavicle_share(l,k):
    """Turn the left clavicle by k x the upper arm's deformation about the shoulder joint (in place).
    The V7 bind clavicle points back along camera -X, so a raised upper arm pinches the shoulder skin
    (diag_upper_skin.py); OffhandKukriComponent.cpp applies the same share after the solve."""
    if k<=0:return
    rb=LR['clavicle_l'][:3,:3]
    o_up=rb.T@(LR['upperarm_l'][:3,3]-LR['clavicle_l'][:3,3])
    deform=R.from_matrix(l['upperarm_l'][:3,:3]@LR['upperarm_l'][:3,:3].T)
    rn=R.from_rotvec(deform.as_rotvec()*k).as_matrix()@rb
    l['clavicle_l']=matrix(rn,l['upperarm_l'][:3,3]-rn@o_up)

def pistol_idle():
    """Saved M1911 Contact idle, frame 0, in the base view basis (no anchor offset)."""
    pose={n:(convert(src['poses']['idle'][n])@np.linalg.inv(sr[n])@RR[n] if n in sr else RR[n].copy()) for n in RR}
    clip=raw['clips']['/Game/Weapons/M1911/Contact20260913/Animations/A_M1911_idle']
    for n,row in zip(raw['bones'],clip['frames'][0]):pose[n]=matrix(R.from_quat(row[3:7]).as_matrix(),row[:3])
    view=matrix(R.from_euler('z',-90,degrees=True).as_matrix(),np.zeros(3))
    return {n:view@m for n,m in pose.items()},view

def compose(pose,c):
    """Rigid gun+hand transform: rear sight to target, bore toward the aim point, canted about the bore."""
    r0=pose['WPN_RearSight'][:3,3];f0=pose['WPN_FrontSight'][:3,3];u0=pose['WPN_root'][:3,2]
    rear=np.array(c['rear_sight'],float);bore=unit(np.array(c['aim_point'],float)-rear)
    up=np.array([0,0,1.]);up=unit(up-bore*np.dot(up,bore))
    up=R.from_rotvec(bore*np.radians(c['cant_degrees'])).as_matrix()@up
    q=frame(bore,up)@frame(f0-r0,u0).T
    return matrix(q,rear-q@r0)

def circle(a,b,c):
    ab,ac=b-a,c-a;n=np.cross(ab,ac)
    centre=a+(np.dot(ac,ac)*np.cross(n,ab)+np.dot(ab,ab)*np.cross(ac,n))/(2*np.dot(n,n))
    return centre,unit(n)

def vertical_fist():
    """Accepted M4 VRE vertical-grip left fist and the handle axis its four fingers wrap."""
    clip=m4['clips']['/Game/Weapons/M4VerticalGripVRENatural/Vertical/A_M4_Vertical_idle']
    pose={n:matrix(R.from_quat(row[3:7]).as_matrix(),row[:3]) for n,row in zip(m4['bones'],clip['frames'][0])}
    source={n:m.copy() for n,m in LR.items()};source.update(pose)
    centres=[];radii={}
    for f in ('index','middle','ring','pinky'):
        pts=[source[f'{f}_0{k}_l'][:3,3] for k in (1,2,3)]
        c,_=circle(*pts);centres.append(c);radii[f]=float(np.mean([np.linalg.norm(p-c) for p in pts]))
    centres=np.array(centres);mean=centres.mean(axis=0)
    axis=np.linalg.svd(centres-mean)[2][0]
    if np.dot(axis,centres[3]-centres[0])<0:axis=-axis
    hand=source['hand_l']
    finger=source['middle_01_l'][:3,3]-hand[:3,3];edge=unit(finger-axis*np.dot(finger,axis))
    line=float(np.max(np.linalg.norm(np.cross(centres-mean,axis),axis=1)))
    return source,{'centre':mean,'axis':axis,'edge':edge,'radii':radii,'centre_line_error_cm':line,
                   'finger_span_cm':float(np.linalg.norm(centres[3]-centres[0]))}

def kukri_frame(origin_on_axis,blade,edge,fist_on_handle):
    e=unit(edge-blade*np.dot(edge,blade))
    return matrix(np.column_stack((e,np.cross(blade,e),blade)),origin_on_axis-fist_on_handle*blade)

def skin(pose):
    snap=surface['snapshot'];x=surface['X'].copy()
    driver=Driver(snap['bones'],list(surface['shapes']))
    sig={n:(m[:3,3],R.from_matrix(m[:3,:3]).as_quat()) for n,m in pose.items()}
    amounts=driver.weights(sig)
    for name,amount in amounts.items():
        if amount>.001 and name in surface['shapes']:x+=amount*surface['shapes'][name]
    rest=rest_of(snap);posed=np.zeros_like(x)
    for n in rest:
        ix=[i for i,w in enumerate(surface['W']) if n in w]
        if not ix:continue
        wt=np.array([surface['W'][i][n] for i in ix]);xf=pose[n]@np.linalg.inv(rest[n])
        posed[ix]+=(x[ix]@xf[:3,:3].T+xf[:3,3])*wt[:,None]
    sides={s:driver.signature(sig,s) for s in 'lr'}
    return posed,{n:float(a) for n,a in amounts.items() if a>.001},sides

def ndc(p,fov=None):
    t=np.tan(np.radians(fov or controls['vertical_fov'])/2)
    return [round(float(p[1]/(p[0]*t*16/9)),3),round(float(-p[2]/(p[0]*t)),3)]

def segment_gap(a0,a1,b0,b1,n=64):
    s=np.linspace(0,1,n)[:,None];A=a0+(a1-a0)*s;B=b0+(b1-b0)*s
    d=np.linalg.norm(A[:,None]-B[None],axis=2);i,j=np.unravel_index(np.argmin(d),d.shape)
    return float(d[i,j]),A[i],B[j]

def wrist_signature(l,r):
    """Driver signature [elbow, flexion, deviation, hand roll] of both wrists (C++ corrective convention)."""
    pose={n:m for n,m in LR.items()}
    for n in LR:
        if chain(n,'clavicle_l',LP):pose[n]=l[n]
        elif chain(n,'clavicle_r',LP) and n in r:pose[n]=r[n]
    sig={n:(m[:3,3],R.from_matrix(m[:3,:3]).as_quat()) for n,m in pose.items()}
    return {s:DRIVER.signature(sig,s)[:4] for s in 'lr'},pose

def build(c):
    idle,view=IDLE
    G=compose(idle,c['gun'])
    gun={n:G@m for n,m in idle.items()}
    r,rdiag=solve_arm(RR,gun,RP,'r',c['right_shoulder'],gun['hand_r'][:3,3],c['right_pole'],gun['hand_r'][:3,:3])
    source,fist=FIST
    kc=c['kukri']
    # The fist frame (origin at the fist centre, Z along the handle toward the pinky, X toward the knuckles)
    # places the hand; the kukri hangs off hand_l by the contact-fitted grip.json.
    knuckle_in_hand=np.linalg.inv(source['hand_l'])@kukri_frame(fist['centre'],fist['axis'],fist['edge'],0.)
    kukri_in_hand=GRIP_IN_HAND
    K=kukri_frame(np.array(kc['fist_centre'],float),unit(kc['blade_direction']),np.array(kc['knuckle_direction'],float),0.)
    hand=K@np.linalg.inv(knuckle_in_hand)
    l,ldiag=solve_arm(LR,source,LP,'l',c['left_shoulder'],hand[:3,3],c['left_pole'],hand[:3,:3])
    wrists,pose=wrist_signature(l,r)
    Kc=l['hand_l']@kukri_in_hand
    # The right hand body: wrist to the middle knuckle, then the gun grip below the slide.
    rh=[r['hand_r'][:3,3],r['middle_01_r'][:3,3]]
    gaps=[segment_gap(l['lowerarm_l'][:3,3],l['hand_l'][:3,3],r['lowerarm_r'][:3,3],r['hand_r'][:3,3])[0],
          segment_gap(l['lowerarm_l'][:3,3],l['hand_l'][:3,3],*rh)[0]]
    dorsal=-np.cross(l['index_01_l'][:3,3]-l['hand_l'][:3,3],l['pinky_01_l'][:3,3]-l['hand_l'][:3,3])
    view_dir=unit(l['hand_l'][:3,3])
    return {'G':G,'view':view,'gun':gun,'r':r,'l':l,'K':K,'Kc':Kc,'kukri_in_hand':kukri_in_hand,'pose':pose,
            'wrists':wrists,'gaps':gaps,'rdiag':rdiag,'ldiag':ldiag,'fist':fist,
            'dorsal_to_eye':float(np.dot(unit(dorsal),-view_dir))}

def contact_grip(fist_pose):
    """grip_fit.py result: kukri relative to hand_l and the contact-adjusted digits (VRE source space)."""
    path=P/'grip.json'
    if not path.exists():
        # Unfitted fallback: reversed, edge in, fist centre 8.5 cm down the handle.
        source,fist=fist_pose
        k=kukri_frame(fist['centre'],fist['axis'],fist['edge'],0.)@np.diag([-1,-1,1,1])@matrix(np.eye(3),[0,0,8.5])
        return np.linalg.inv(source['hand_l'])@k,{}
    g=read(path)
    return np.array(g['kukri_in_hand']),{n:np.array(m) for n,m in g['digits'].items()}

IDLE=pistol_idle()
FIST=vertical_fist()
GRIP_IN_HAND,GRIP_DIGITS=contact_grip(FIST)
FIST[0].update(GRIP_DIGITS)
DRIVER=Driver(surface['snapshot']['bones'],list(surface['shapes']))

def main(c,tag=''):
    b=build(c);fov=c['vertical_fov']
    ndc_=lambda p:ndc(p,fov)
    out=lambda name:P/(name+tag+('.npz' if not name.endswith('.json') else ''))
    G,view,gun,r,l,K,Kc=[b[k] for k in ('G','view','gun','r','l','K','Kc')]
    geo=np.load(V4/'gun_idle.npz');xg=100*geo['X']*np.array([1,-1,1])
    xf=G@view;np.savez_compressed(out('gun_camera'),X=xg@xf[:3,:3].T+xf[:3,3],T=geo['T'][:,::-1],UV=geo['UV'][:,::-1],slots=geo['slots'])
    km=np.load(P/'kukri_mesh.npz')
    np.savez_compressed(out('kukri_camera'),X=km['X']@Kc[:3,:3].T+Kc[:3,3],T=km['T'],UV=km['UV'],slots=km['slots'])
    X,correctives,_=skin(b['pose'])
    np.savez_compressed(out('arms_camera'),X=X,T=surface['T'],UV=surface['UV'])
    kc=c['kukri'];tip=Kc@np.array([6.18,0,26.29,1]);pommel=Kc@np.array([0.4,0,-12.5,1])
    fist_centre=K[:3,3]
    diag={'ndc':{'rear_sight':ndc_(gun['WPN_RearSight'][:3,3]),'front_sight':ndc_(gun['WPN_FrontSight'][:3,3]),
                 'right_wrist':ndc_(r['hand_r'][:3,3]),'right_elbow':ndc_(r['lowerarm_r'][:3,3]),
                 'fist_centre':ndc_(fist_centre),'left_wrist':ndc_(l['hand_l'][:3,3]),
                 'left_elbow':ndc_(l['lowerarm_l'][:3,3]),'kukri_tip':ndc_(tip[:3]),'kukri_pommel':ndc_(pommel[:3])},
          'cm':{'right_wrist':r['hand_r'][:3,3].round(2).tolist(),'right_elbow':r['lowerarm_r'][:3,3].round(2).tolist(),
                'left_wrist':l['hand_l'][:3,3].round(2).tolist(),'left_elbow':l['lowerarm_l'][:3,3].round(2).tolist(),
                'kukri_tip':tip[:3].round(2).tolist(),'kukri_pommel':pommel[:3].round(2).tolist()},
          'forearm_gap_cm':[round(g,2) for g in b['gaps']],'reach':{'right':b['rdiag'],'left':b['ldiag']},
          'left_dorsal_to_eye':round(b['dorsal_to_eye'],3),
          'wrist_signature_elbow_flex_dev_roll':{s:[round(v,1) for v in w] for s,w in b['wrists'].items()},
          'source_wrist_signature':{'r':[84.3,15.2,-22.4,14.6],'l':[29.8,-0.6,0.3,-42.6]},
          'fist_fit':{k:(v.round(3).tolist() if isinstance(v,np.ndarray) else v) for k,v in b['fist'].items()}}
    (P/('candidate'+tag+'.json')).write_text(json.dumps({'candidate_only':True,'runtime_integrated':False,'controls':c,
        'diagnostics':diag,'kukri_in_hand':b['kukri_in_hand'].tolist(),'gun_composition':G.tolist(),
        'poses':{'left':{n:l[n].tolist() for n in l if chain(n,'clavicle_l',LP)},
                 'right':{n:r[n].tolist() for n in r if chain(n,'clavicle_r',RP)}},
        'active_correctives':correctives},indent=1),encoding='utf-8')
    print(json.dumps(diag['ndc']));print(json.dumps(diag['cm']))
    print('gaps',diag['forearm_gap_cm'],'reach',diag['reach'],'dorsal',diag['left_dorsal_to_eye'])
    print('wrists',diag['wrist_signature_elbow_flex_dev_roll'])

if __name__=='__main__':
    if '--ads' in sys.argv:main(controls['ads'],'_ads')
    else:main(controls)
