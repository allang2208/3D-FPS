"""Authoring-only wrist support and complete, canted-axis recovery flourishes."""
import math
from mathutils import Matrix,Quaternion,Vector

PROFILES={
    'compact':{'suffix':'','outward':.028,'forward':.018,'axis_cant_deg':38.,'finger_open':1.},
    'wide':{'suffix':'_fitted','outward':.065,'forward':.045,'axis_cant_deg':64.,'finger_open':1.16},
    'long':{'suffix':'_long','outward':.080,'forward':.075,'axis_cant_deg':78.,'finger_open':1.20}}

def smooth(x):
    x=max(0.,min(1.,x));return x*x*x*(10.-15.*x+6.*x*x)

def window(t,a,b,c,d):return smooth((t-a)/(b-a))*(1.-smooth((t-c)/(d-c)))

def axial(a,b,axis):
    q=a@b.inverted();return (2*math.atan2(Vector((q.x,q.y,q.z)).dot(axis),q.w)+math.pi)%(2*math.pi)-math.pi

def unwrap(value,previous):return value if previous is None else previous+(value-previous+math.pi)%(2*math.pi)-math.pi

def two_bone(idle,side,hand,shoulder,pole_target,rest,weight):
    u,f,h=[n+'_'+side for n in ('upperarm','lowerarm','hand')]
    a,e,w=[idle[n].translation for n in (u,f,h)]
    l1,l2=(e-a).length,(w-e).length;target=hand.translation
    delta=target-shoulder;distance=delta.length;axis=delta.normalized()
    reach=(l1+l2)*.985
    if distance>reach:shoulder+=axis*(distance-reach);distance=reach
    distance=max(abs(l1-l2)+.0001,distance)
    along=(l1*l1-l2*l2+distance*distance)/(2*distance)
    center=shoulder+axis*along;radius=math.sqrt(max(0.,l1*l1-along*along))
    pole=pole_target-shoulder;pole=(pole-axis*pole.dot(axis)).normalized()
    neutral=hand.to_quaternion()@rest[h].to_quaternion().inverted()@(rest[h].translation-rest[f].translation).normalized()
    desired=target-neutral*l2-center;desired-=axis*desired.dot(axis)
    if desired.length>1e-7:
        desired.normalize();angle=math.atan2(axis.dot(pole.cross(desired)),pole.dot(desired))
        pole=Quaternion(axis,max(-math.radians(48),min(math.radians(48),angle))*weight)@pole
    return shoulder,center+pole*radius,neutral

def natural_hand(idle,rest,side,hand,shoulder,pole_target,weight):
    shoulder,elbow,neutral=two_bone(idle,side,hand,shoulder.copy(),pole_target,rest,weight)
    fore=(hand.translation-elbow).normalized();bend=neutral.angle(fore)
    # Move the held group's orientation, not the hand through its grip. These
    # are rig-space authoring limits, not medical joint-angle thresholds.
    excess=max(0.,bend-math.radians(24.))
    correction=neutral.rotation_difference(fore)
    amount=min(math.radians(65.),excess)/max(bend,1e-7)*weight
    rotation=Quaternion().slerp(correction,amount)
    result=Matrix.LocRotScale(hand.translation,rotation@hand.to_quaternion(),hand.to_scale())
    shoulder,elbow,_=two_bone(idle,side,result,shoulder,pole_target,rest,weight)
    return result,shoulder,elbow

def support_twist(p,idle,rest,side,stations,weight,state):
    if weight<1e-8:
        state.pop(side,None);return
    u,f,h=[n+'_'+side for n in ('upperarm','lowerarm','hand')]
    upper_axis=(p[f].translation-p[u].translation).normalized()
    fore_axis=(p[h].translation-p[f].translation).normalized()
    old_fore=(idle[h].translation-idle[f].translation).normalized()
    upper=p[u].to_quaternion()@idle[u].to_quaternion().inverted()
    full=p[f].to_quaternion()@idle[f].to_quaternion().inverted()
    hinge=(upper@old_fore).rotation_difference(fore_axis)@upper
    residual=unwrap(axial(full,hinge,fore_axis),state.get(side))
    state[side]=residual
    share=max(-math.radians(38),min(math.radians(38),residual*.32))*weight
    upper_turn=Quaternion(upper_axis,share)
    for n in (u,'upperarm_twist_01_'+side,'upperarm_twist_02_'+side):
        p[n]=Matrix.LocRotScale(p[n].translation,upper_turn@p[n].to_quaternion(),p[n].to_scale())
    upper=upper_turn@upper
    hinge=(upper@old_fore).rotation_difference(fore_axis)@upper
    residual=unwrap(axial(full,hinge,fore_axis),residual)
    for n,station in stations.items():
        # The elbow side follows the humerus; twist increases toward the wrist.
        # Every helper stays on its own transported full-length forearm segment.
        fraction=1.-weight*(1.-station)
        q=Quaternion(fore_axis,residual*fraction)@hinge@idle[n].to_quaternion()
        p[n]=Matrix.LocRotScale(p[n].translation,q,p[n].to_scale())

def relax_fingers(p,idle,side,t,profile,parents,local_rest):
    release=smooth((t-.385)/.055)
    for finger in ('thumb','middle','ring','pinky'):
        close_start=.642 if finger=='thumb' else .657
        close_end=.690 if finger=='thumb' else .710
        amount=release*(1.-smooth((t-close_start)/(close_end-close_start)))*profile['finger_open']
        for j in (1,2,3):
            n=f'{finger}_{j:02d}_{side}'
            if n not in p:continue
            parent=parents[n];loc,q,scale=(idle[parent].inverted()@idle[n]).decompose()
            factor=(.55 if finger=='thumb' else .66 if j==1 else .94)*amount
            p[n]=p[parent]@Matrix.LocRotScale(loc,q.slerp(local_rest[n].to_quaternion(),min(.96,factor)),scale)

def spin_gun(root,p,idle,rest,side,t,profile,weapon,camera):
    progress=smooth((t-.435)/.240)
    if progress<=0. or progress>=1.:return root
    hand='hand_'+side
    delta=p[hand]@idle[hand].inverted()
    lateral=delta.to_quaternion()@camera((0,1,0))
    forward=(p[hand].translation-p['lowerarm_'+side].translation).normalized()
    sign=1. if side=='r' else -1.
    cant=math.radians(min(82.,profile['axis_cant_deg']+(10. if weapon=='DW715' else 0.)))
    # Tilt the whole revolution's axis toward the forearm direction. The muzzle
    # then circles outside the wrist instead of sweeping back through it. The
    # curled index contact remains the centre; there is no free-floating shift.
    axis=(lateral*math.cos(cant)+forward*(sign*math.sin(cant))).normalized()
    pivot=p['index_02_'+side].translation
    return Matrix.Translation(pivot)@Quaternion(axis,progress*2.*math.pi).to_matrix().to_4x4()@Matrix.Translation(-pivot)@root
