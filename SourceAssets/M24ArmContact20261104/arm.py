"""Native M24 elbow hinge; distribute pronation only through the forearm."""
U0=native_rest['lowerarm_l'].translation-native_rest['upperarm_l'].translation
F0=native_rest['hand_l'].translation-native_rest['lowerarm_l'].translation
N0=U0.cross(F0).normalized()
FU0=frame(U0,N0);FL0=frame(F0,N0)

def contact_reach(fr,x,weight):
    target=fr.H+fr.basis@Vector(x[:3])*.001
    previous=fr.S;v=target-fr.S;limit=(fr.A+fr.B)*(1-.036*weight)-.0001
    shift=v.normalized()*max(0.,v.length-limit)
    if shift.length>.065:raise RuntimeError(f'Contact requires {shift.length*1000:.1f} mm shoulder movement at {fr.family}/{fr.f:.3f}')
    fr.S=previous+shift
    try:out=fr.pose(x)
    finally:fr.S=previous
    out['clavicle_l']=Matrix.LocRotScale(fr.row['clavicle_l'].translation+shift,fr.row['clavicle_l'].to_quaternion(),fr.row['clavicle_l'].to_scale())
    return out

def wrap_angle(x):return (x+math.pi)%(2*math.pi)-math.pi
def hinge_frames(S,E,H,hand_q,source):
    u=E-S;f=H-E;n=u.cross(f)
    bend=math.atan2(n.length,u.dot(f))
    carried=U0.normalized().rotation_difference(u.normalized())@N0
    carried=(carried-u.normalized()*carried.dot(u.normalized())).normalized()
    if n.length<1e-9:n=carried
    else:n.normalize()
    if carried.dot(n)<0:carried=-carried
    w=smooth((math.degrees(bend)-8)/20)
    n=(carried*(1-w)+n*w).normalized()
    du=(frame(u,n)@FU0.transposed()).to_quaternion()
    dl=(frame(f,n)@FL0.transposed()).to_quaternion()
    dh=hand_q@native_rest['hand_l'].to_quaternion().inverted()
    delta=dl.inverted()@dh
    tau=wrap_angle(2*math.atan2(Vector((delta.x,delta.y,delta.z)).dot(F0.normalized()),delta.w))
    return du,dl,tau

def correct_arm(row,weight,tau_hint=None):
    if weight<=1e-9:return row,{'elbow_shift_mm':0.,'forearm_roll_deg':0.}
    out={n:m.copy() for n,m in row.items()}
    S=row['upperarm_l'].translation;E=row['lowerarm_l'].translation;H=row['hand_l'].translation
    du,dl,tau=hinge_frames(S,E,H,row['hand_l'].to_quaternion(),row)
    axis=(H-S).normalized();center=S+axis*(E-S).dot(axis);radius=E-center
    # Continuous bounded movement on the exact two-bone circle relieves severe
    # pronation without changing either bone length or the fixed grip target.
    psi=0.
    if abs(tau)>math.radians(95) and radius.length>.005:
        trial=center+Quaternion(axis,math.radians(2))@radius
        _,_,trial_tau=hinge_frames(S,trial,H,row['hand_l'].to_quaternion(),row)
        derivative=wrap_angle(trial_tau-tau)/math.radians(2)
        if abs(derivative)>.2:
            maximum=min(math.radians(25),2*math.asin(min(1.,.03/(2*radius.length))))
            psi=max(-maximum,min(maximum,-(tau-math.copysign(math.radians(95),tau))/derivative))*weight
    newE=center+Quaternion(axis,psi)@radius
    du,dl,tau=hinge_frames(S,newE,H,row['hand_l'].to_quaternion(),row)
    if tau_hint is not None:tau+=2*math.pi*round((tau_hint-tau)/(2*math.pi))
    u=newE-S;f=H-newE
    upper_swing=(E-S).normalized().rotation_difference(u.normalized())
    lower_swing=(H-E).normalized().rotation_difference(f.normalized())
    for n in ('upperarm_l','lowerarm_l'):
        q0=(upper_swing if n=='upperarm_l' else lower_swing)@row[n].to_quaternion()
        q1=(du if n=='upperarm_l' else dl)@native_rest[n].to_quaternion()
        out[n]=Matrix.LocRotScale(S if n=='upperarm_l' else newE,q0.slerp(q1,weight),row[n].to_scale())
    for n in ('upperarm_twist_01_l','upperarm_twist_02_l','lowerarm_twist_01_l','lowerarm_twist_02_l'):
        upper=n.startswith('upperarm');parent=parents[n]
        local=row[parent].inverted()@row[n]
        if upper:target=du@native_rest[n].to_quaternion();carried=upper_swing@row[n].to_quaternion()
        else:
            share=1. if '_01_' in n else .5
            target=Quaternion(f.normalized(),tau*share)@dl@native_rest[n].to_quaternion()
            carried=lower_swing@row[n].to_quaternion()
        out[n]=Matrix.LocRotScale(out[parent]@local.translation,carried.slerp(target,weight),row[n].to_scale())
    return out,{'elbow_shift_mm':(newE-E).length*1000,'forearm_roll_deg':math.degrees(tau)}
