import json, math
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R, Slerp
O=Path(__file__).parent;S=O.parent
g=json.loads((O/'geometry.json').read_text());rest={n:np.array(m) for n,m in g['rest'].items()};parents=g['parents'];names=list(rest);ri={n:np.linalg.inv(m) for n,m in rest.items()};I=np.eye(4)
contact=json.loads((O/'contact_fit.json').read_text());target={n:np.array(m) for n,m in contact['finger_local'].items()};digits=list(target)
changed=['clavicle_l','upperarm_l','lowerarm_l','lowerarm_aux_l','lowerarm_twist_02_l','lowerarm_twist_01_l','hand_l',*digits]
source=json.loads((O/'source_poses.json').read_text());rows={b:[{n:np.array(m) for n,m in p.items()} for p in ps] for b,ps in source.items()};del source
clocks=[json.loads((S/f'Super90LoaderR{rev}_20261009/timing.json').read_text())['source_frames'] for rev in (16,15,14)]
def smooth(x):x=np.clip(x,0,1);return x*x*x*(x*(x*6-15)+10)
def phase(f,a,b):return smooth((f-a)/(b-a))
def unit(v):return v/np.linalg.norm(v)
def trans(v):m=I.copy();m[:3,3]=v;return m
def blend(a,b,t):
    if t<=0:return a.copy()
    if t>=1:return b.copy()
    out=I.copy();out[:3,:3]=Slerp([0,1],R.from_matrix([a[:3,:3],b[:3,:3]]))([t]).as_matrix()[0];out[:3,3]=a[:3,3]*(1-t)+b[:3,3]*t;return out
def swing(a,b):
    a=unit(a);b=unit(b);cross=np.cross(a,b);length=np.linalg.norm(cross)
    if length<1e-8:return np.eye(3)
    return R.from_rotvec(cross/length*math.atan2(length,np.dot(a,b))).as_matrix()
def basis(axis,side):
    a=unit(axis);s=unit(side-a*np.dot(a,side));return np.column_stack((a,s,np.cross(a,s)))
def rack_time(branch,f):
    if branch=='cycle':return 16+f*52/66
    for values in clocks:f=float(np.interp(f,np.arange(len(values)),values))
    return f-114
fore=rest['hand_l'][:3,3]-rest['lowerarm_l'][:3,3]
upper=rest['lowerarm_l'][:3,3]-rest['upperarm_l'][:3,3]
width=rest['index_01_l'][:3,3]-rest['pinky_01_l'][:3,3]
fore_basis=basis(fore,width)
rest_normal=unit(np.cross(upper,fore))
bolt=g['meshes']['Super90_bolt']['positions'];knob_rest=np.array([v for v in bolt if v[0]>.026]).mean(0)

def correct(p,branch,f,support=True):
    out={n:m.copy() for n,m in p.items()};end={'normal':144,'empty':180,'cycle':66}[branch]
    if branch!='normal':
        t=rack_time(branch,f);w=phase(t,23,32)*(1-phase(t,48,56))
        if w>0:
            gun=p['WPN_root']@ri['WPN_root'];gi=np.linalg.inv(gun)
            knob=(gi@p['WPN_bolt']@ri['WPN_bolt']@np.r_[knob_rest,1])[:3]
            shift=knob-np.array(contact['handle_centre_gun'])
            delta=trans(shift)@np.array(contact['hand_gun_delta'])@trans(-shift)
            out['hand_l']=gun@blend(I,delta,w)@gi@p['hand_l']
            for n in digits:
                local=np.linalg.inv(p[parents[n]])@p[n]
                # Fold the same grasp only over its contact window; carry the
                # existing open-hand shape outside it, with thumb kept clear.
                close=phase(t,27,33)*(1-phase(t,44,49))
                amount=w if n.startswith('thumb') else close
                out[n]=out[parents[n]]@blend(local,target[n],amount)
        # Cross above the receiver before approaching its right-side handle.
        # The old travel takes the thumb straight through the top/side wall.
        # This positional arc is zero throughout the actual pull and leaves
        # the accepted loader push, clip duration and final foregrip unchanged.
        lift=(.082*phase(t,12,18)*(1-phase(t,26,32)) if branch=='empty'
              else .118*phase(t,16,20)*(1-phase(t,24,31)))
        lift+=.045*phase(t,49,53)*(1-phase(t,57,63))
        if lift>0:
            gun=p['WPN_root']@ri['WPN_root']
            step=gun[:3,:3]@np.array([0.,0.,lift])
            for n in ('hand_l',*digits):out[n][:3,3]+=step
    if not support:return out
    hand=out['hand_l'];a=p['upperarm_l'][:3,3].copy();old_e=p['lowerarm_l'][:3,3];h=hand[:3,3]
    l1=np.linalg.norm(old_e-a);l2=np.linalg.norm(fore)*l1/np.linalg.norm(upper);axis=unit(h-a);d=np.linalg.norm(h-a)
    old_axis=axis.copy();old_pole=unit(old_e-a-old_axis*np.dot(old_e-a,old_axis))
    short=max(0,.935*(l1+l2)-d);shift=axis*(-short*short/(short+(l1+l2)*.0142))
    a+=shift;out['clavicle_l'][:3,3]+=shift;d=np.linalg.norm(h-a)
    hd=hand[:3,:3]@ri['hand_l'][:3,:3]
    pole=old_pole
    wanted=-(hd@unit(fore));wanted-=axis*np.dot(wanted,axis)
    if np.linalg.norm(wanted)>1e-6:
        wanted=unit(wanted);angle=math.atan2(np.dot(axis,np.cross(pole,wanted)),np.dot(pole,wanted))
        pole=R.from_rotvec(axis*np.clip(angle,-math.radians(32),math.radians(32))).apply(pole)
    along=(l1*l1-l2*l2+d*d)/(2*d);radius=math.sqrt(max(0,l1*l1-along*along))
    e=a+axis*along+pole*radius
    # Palm width defines forearm roll. Do not add fractional twist to a parent
    # that already carries the full roll: the native skin blends those bones.
    df=basis(h-e,hd@width)@fore_basis.T
    du=swing(df@upper,e-a)@df
    lower=I.copy();lower[:3,:3]=df;lower[:3,3]=e-df@rest['lowerarm_l'][:3,3]
    up=I.copy();up[:3,:3]=du;up[:3,3]=a-du@rest['upperarm_l'][:3,3]
    desired={n:lower@rest[n] for n in ('lowerarm_l','lowerarm_aux_l','lowerarm_twist_02_l','lowerarm_twist_01_l')}
    desired['upperarm_l']=up@rest['upperarm_l']
    # This skin has no lowerarm_l weights: its elbow is carried by aux, and
    # the wrist by twist_01. Give aux the elbow bisector, then converge early
    # to the palm-aligned forearm so the distal skin does not counter-rotate.
    for n,amount in (('lowerarm_aux_l',.5),('lowerarm_twist_02_l',.88)):
        turn=Slerp([0,1],R.from_matrix([du,df]))([amount]).as_matrix()[0]
        desired[n][:3,:3]=turn@rest[n][:3,:3]
    # The same roll reconstruction now runs after the Super90 runtime blend,
    # including idle/ADS. Keep matching corrected endpoints instead of fading
    # back into the rejected twisted idle at the end of a reload.
    for n,m in desired.items():out[n]=m
    # Interpolating rotations never moves the accepted wrist/loader contact.
    return out

def packed(p):return {n:m.tolist() for n,m in p.items()}
if __name__=='__main__':
    out={b:[packed(correct(p,b,f)) for f,p in enumerate(ps)] for b,ps in rows.items()}
    (O/'repaired_poses.json').write_text(json.dumps(out,separators=(',',':')))
    print('R23_BASE_POSES_SAVED',flush=True)
