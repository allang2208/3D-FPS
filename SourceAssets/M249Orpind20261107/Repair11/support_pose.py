"""Shared left support correction, preserving the weapon and the right arm."""
import numpy as np
from motion import *
def apply_support(p,local,names,parents,bind,reference,parameters,weight=1.):
    if weight<=1.e-8:return {n:v.copy() for n,v in p.items()}
    out={n:v.copy() for n,v in p.items()};a,e,h=[p[n][:3,3].copy() for n in ('upperarm_l','lowerarm_l','hand_l')]
    shift=rot(p['WPN_root'])@rot(reference['WPN_root']).T@np.array(parameters[:3])*weight
    target=h+shift;axis=unit(target-a);distance=np.linalg.norm(target-a);la=np.linalg.norm(e-a);lb=np.linalg.norm(h-e)
    along=(la*la-lb*lb+distance*distance)/(2*distance);pole=unit(e-a-axis*((e-a)@axis));center=a+axis*along;radius=np.sqrt(max(0,la*la-along*along))
    hand_rotation=rot(p['hand_l'])
    if len(parameters)>=10:
        basis=rot(p['WPN_root'])@rot(reference['WPN_root']).T
        hand_rotation=basis@R.from_rotvec(np.array(parameters[7:10])*weight).as_matrix()@basis.T@hand_rotation
    rest=unit(bind['hand_l'][:3,3]-bind['lowerarm_l'][:3,3]);forearm_axis=hand_rotation@rot(bind['hand_l']).T@rest
    desired=target-lb*forearm_axis-center;desired=unit(desired-axis*(desired@axis))
    angle=np.clip(np.arctan2(axis@np.cross(pole,desired),pole@desired),-1.2,1.2)
    def bend_at(t):
        e1=center+turn(axis,angle*t)@pole*radius
        return np.arccos(np.clip(unit(target-e1)@forearm_axis,-1,1))
    turn_weight=0.
    if bend_at(0)>np.radians(32):
        lo,hi=0.,1.
        if bend_at(1)>np.radians(32):turn_weight=1.
        else:
            for _ in range(12):
                mid=(lo+hi)*.5
                if bend_at(mid)>np.radians(32):lo=mid
                else:hi=mid
            turn_weight=hi
    elbow=center+turn(axis,angle*turn_weight)@pole*radius
    # Keep the support forearm outside the projecting factory ammunition box.
    outward=-np.sign(np.cross(axis,elbow-center)[0])
    elbow=center+turn(axis,outward*.55*weight)@(elbow-center)
    for prefix,oldorigin,origin,delta in (('upperarm',a,a,swing(e-a,elbow-a)),('lowerarm',e,elbow,swing(h-e,target-elbow))):
        for suffix in ('','_twist_01','_twist_02'):
            name=prefix+suffix+'_l';out[name][:3,:3]=delta@p[name][:3,:3];out[name][:3,3]=origin+delta@(p[name][:3,3]-oldorigin)
    out['hand_l'][:3,3]=target
    out['hand_l'][:3,:3]=hand_rotation*np.linalg.norm(p['hand_l'][:3,:3],axis=0)
    digits=sorted(n for n in names if n.endswith('_l') and n.startswith(('thumb','index','middle','ring','pinky')) and 'metacarpal' not in n)
    for name in names:
        if name.endswith('_l') and name.startswith(('thumb','index','middle','ring','pinky')):
            child=local[name].copy();base=np.linalg.inv(bind[parents[name]])@bind[name]
            amount=(1. if 'metacarpal' in name else parameters[6] if name.startswith('thumb') else parameters[3+int(name.split('_')[1])-1]) if len(parameters)>=7 else (parameters[4] if name.startswith('thumb') else parameters[3])
            child[:3,:3]=blend(rot(base),rot(child),1.-weight*(1.-amount))*np.linalg.norm(child[:3,:3],axis=0)
            if len(parameters)>10 and name in digits:child[:3,:3]=turn([0,0,1],parameters[10+digits.index(name)]*weight)@child[:3,:3]
            out[name]=out[parents[name]]@child
    if 'ik_hand_l' in out:out['ik_hand_l']=out['hand_l']@np.linalg.inv(p['hand_l'])@p['ik_hand_l']
    return out
