"""Place the blade in front of the planted body. Work in UE component space (cm)."""
from pathlib import Path
import json, math
import numpy as np
from scipy.spatial.transform import Rotation as Rot

P=Path(__file__).resolve().parent
anchors=json.loads((P/'body-anchors.json').read_text())
def load_surface(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))
def rigmat(row):
    m=np.eye(4)
    m[:3,:3]=Rot.from_quat(row[3:7]).as_matrix()*row[7:]
    m[:3,3]=row[:3]
    return m
def rigid(p,r):
    m=np.eye(4);m[:3,3]=p;m[:3,:3]=r;return m
def unit(v): return v/max(1.e-10,np.linalg.norm(v))
def rotation(m):return m[:3,:3]/np.linalg.norm(m[:3,:3],axis=0)
def smooth(v):
    t=min(1.,max(0.,v));return t*t*t*(10.+t*(-15.+6.*t))
def between(a,b):
    a,b=unit(a),unit(b)
    q=np.r_[np.cross(a,b),1.+a@b]
    if np.linalg.norm(q)<1e-8:
        return Rot.from_rotvec(math.pi*unit(np.cross(a,[0.,0.,1.]))).as_matrix()
    return Rot.from_quat(q).as_matrix()
def blend(a,b,t):
    r=rotation(a);v=Rot.from_matrix(r.T@rotation(b)).as_rotvec()*t
    scale=(1-t)*np.linalg.norm(a[:3,:3],axis=0)+t*np.linalg.norm(b[:3,:3],axis=0)
    m=rigid(a[:3,3]*(1-t)+b[:3,3]*t, r@Rot.from_rotvec(v).as_matrix()*scale);return m
def globalize(values,parents):
    world={}
    def walk(n):
        if n not in world:world[n]=walk(parents[n])@values[n] if parents[n] in values else values[n]
        return world[n]
    for n in values:walk(n)
    return world
def palm(ref):
    inv=np.linalg.inv(ref['hand_r'])
    points=[(inv@ref[n+'_01_r'])[:3,3] for n in ('index','middle','pinky')]
    x=unit(points[1]);y=unit(points[0]-points[2]-x*(x@(points[0]-points[2])))
    return rigid(np.mean(points,axis=0),np.column_stack([x,y,np.cross(x,y)]))
def nativem(row):
    return rigid(row['p'],Rot.from_quat(row['q']).as_matrix())

# Same anatomical palm mapping and frozen idle weapon-to-wrist relation as the
# world weapon presentation. Persist this small input so the take is rebuildable.
mount_source=P/'body-weapon-mount.json'
if not mount_source.exists():
    d=load_surface(P/'Review/Native/Standard/surface.json')
    src_ref={n:nativem(r) for n,r in zip(d['bone_names'],d['rest'])}
    full=load_surface(P/'Review/Native/StandardIdleEntry/surface.json')['frames'][0]
    mount_source.write_text(json.dumps(dict(palm=palm(src_ref).tolist(),
        blade_in_hand=(np.linalg.inv(nativem(full['bones']['hand_r']))@nativem(full['weapon'])).tolist())))
mount=json.loads(mount_source.read_text())

def stroke(t):
    # Blade heading in world-body coordinates, camera forward along +Y and
    # camera right along -X. The arc remains in the frontal half-space.
    if t<=.30:return 78.,7.,np.array([-31.,46.,4.])
    if t<=.47:
        u=(t-.30)/.17
        u=(-2*u**3+3*u*u)+.60*(u**3-2*u*u+u)+.68*(u**3-u*u)
        return 78.-150.*u,7.-13.*u,np.array([-31.+61.*u,46.+6.*np.sin(np.pi*u),4.-10.*u])
    u=smooth((t-.47)/.08)
    brake=smooth((t-.55)/.11)
    return -72.-36.*u-4.*brake,-6.-6.*u-6.*brake,np.array([30.+9.*u-2.*brake,46.-4.*u,-6.-6.*u-4.*brake])
def frame(yaw,elev,sign):
    a,b=np.radians([yaw,elev])
    z=np.array([-np.sin(a)*np.cos(b),np.cos(a)*np.cos(b),np.sin(b)])
    x=sign*np.array([np.cos(a),np.sin(a),0])
    return np.column_stack([x,np.cross(z,x),z])
def chain_frame(direction,normal):
    x=unit(direction);z=unit(normal-x*(x@normal));return np.column_stack([x,np.cross(z,x),z])
def solve_arm(pose,base,src,parents,side,target,weight):
    U,L,H=[k+'_'+side for k in ('upperarm','lowerarm','hand')]
    C='clavicle_'+side
    A,E,W=[base[k][:3,3] for k in (U,L,H)]
    T=target[:3,3]
    reach=T-A;d=np.linalg.norm(reach);axis=unit(reach)
    a,b=np.linalg.norm(E-A),np.linalg.norm(W-E)
    # Carry the clavicle slightly at the bounds; never stretch either arm.
    shift=max(0.,d-(a+b)*.98)*axis
    shoulder=A+shift
    axis=unit(T-shoulder);d=np.linalg.norm(T-shoulder)
    along=(a*a-b*b+d*d)/(2.*d)
    old=unit(W-A)
    pole=between(old,axis)@unit(E-A-old*((E-A)@old))
    elbow=shoulder+axis*along+pole*np.sqrt(max(0.,a*a-along*along))
    normal0=unit(np.cross(E-A,W-E));normal=unit(np.cross(elbow-shoulder,T-elbow))
    du=chain_frame(elbow-shoulder,normal)@chain_frame(E-A,normal0).T
    dl=between(du@(W-E),T-elbow)@du
    pose[C]=base[C].copy();pose[C][:3,3]+=shift
    pose[U]=rigid(shoulder,du@base[U][:3,:3]);pose[L]=rigid(elbow,dl@base[L][:3,:3]);pose[H]=target
    # Corrective/helper branches, including fingers, follow the bone that owns
    # them. Lower arm twist is shared towards the wrist; never turn the elbow
    # cap through the entire palm roll.
    inherited={C,U,L,H}
    for n in pose:
        parent=parents[n]
        if parent not in inherited:continue
        inherited.add(n)
        if n in (U,L,H):continue
        pose[n]=pose[parent]@src[n]
        if n.startswith('lowerarm_twist_') and n.endswith('_'+side):
            delta=rotation(target)@rotation(base[H]).T@dl.T
            q=Rot.from_matrix(delta).as_quat();direction=unit(T-elbow)
            angle=2*np.arctan2(q[:3]@direction,q[3]);angle=(angle+np.pi)%(2*np.pi)-np.pi
            part=1. if '_01_' in n else .5
            pose[n][:3,:3]=Rot.from_rotvec(direction*angle*weight*part).as_matrix()@pose[n][:3,:3]

def author(variant,data):
    names=data['names'];parents=dict(zip(names,data['parents']))
    local={k:{n:rigmat(row) for n,row in data[k].items()} for k in ('land','idle','ref')}
    world={k:globalize(v,parents) for k,v in local.items()}
    land,idle,ref=(world[k] for k in ('land','idle','ref'))
    blade_in_hand=palm(ref)@np.linalg.inv(np.array(mount['palm']))@np.array(mount['blade_in_hand'])
    weapon={k:v['hand_r']@blade_in_hand for k,v in world.items()}
    grips={k:{s:np.linalg.inv(weapon[k])@v['hand_'+s] for s in ('r','l')} for k,v in world.items()}
    sign=max((-1,1),key=lambda sign:np.trace(rotation(weapon['land']).T@frame(78,7,sign)))
    out={n:[] for n in names}
    prev={}
    report={'mount':blade_in_hand.tolist(),'sign':int(sign),'frames':[]}
    for i in range(73):
        t=i/60;prep=smooth(t/.24);back=smooth((t-.66)/.54)
        y,e,point=stroke(t)
        target=rigid(point+[0.,18.,idle['spine_03'][2,3]],frame(y,e,sign))
        target=blend(weapon['land'],target,prep) if t<.30 else target
        target=blend(target,weapon['idle'],back)
        localbase={}
        for n in names:
            # Keep the heavy landing stance through both the cut and brake.
            lower=n in ('root','pelvis') or n.startswith(('thigh','calf','foot','ball','ik_foot','ik_knee'))
            localbase[n]=blend(local['land'][n],local['idle'][n],back if lower else prep)
        base=globalize(localbase,parents)
        # The heavy landing has a deep hip hinge. Keep those legs planted but
        # bring the ribcage back up as the hilt rises, so the arms clear the chest.
        lower_spine='spine_01'
        upright=localbase[lower_spine].copy()
        upright[:3,:3]=rotation(base[parents[lower_spine]]).T@rotation(idle[lower_spine])*np.linalg.norm(upright[:3,:3],axis=0)
        localbase[lower_spine]=blend(localbase[lower_spine],upright,prep)
        base=globalize(localbase,parents)
        spine_turn=math.radians((18.-40.*smooth((t-.27)/.23))*prep*(1.-back))
        for n in ('spine_01','spine_02','spine_03'):
            parent=rotation(base[parents[n]])
            localbase[n][:3,:3]=parent.T@Rot.from_rotvec([0,0,spine_turn/3.]).as_matrix()@parent@localbase[n][:3,:3]
        base=globalize(localbase,parents)
        pose={n:m.copy() for n,m in base.items()}
        for side in ('r','l'):
            grip=blend(grips['land'][side],grips['idle'][side],prep)
            solve_arm(pose,base,localbase,parents,side,target@grip,prep*(1-back))
        if i==0:pose=land
        if i==72:pose=idle
        # Mesh-space IK hand targets follow their solved wrists, including the recovery.
        for side in ('r','l'):
            h='hand_'+side;n='ik_hand_'+side
            if n in pose:
                pose[n]=pose[h]@np.linalg.inv(base[h])@base[n] if i not in (0,72) else pose[n]
        for n in names:
            m=np.linalg.inv(pose[parents[n]])@pose[n] if parents[n] in pose else pose[n]
            try:q=Rot.from_matrix(rotation(m)).as_quat()
            except ValueError as exc:raise ValueError(f'{variant} frame={i} bone={n}') from exc
            if n in prev and prev[n]@q<0:q=-q
            prev[n]=q
            out[n].append([*m[:3,3],*q,*np.linalg.norm(m[:3,:3],axis=0)])
        report['frames'].append(target.tolist())
    (P/(variant+'-body-tracks.json')).write_text(json.dumps(dict(skeleton=data['skeleton'],tracks=out),separators=(',',':')))
    (P/(variant+'-mount.json')).write_text(json.dumps(report))
for variant,data in anchors.items():author(variant,data)
