"""Native right hinge, bounded elbow arc and separate axial hand rotation."""
from pathlib import Path
exec(compile((Path(__file__).parent/'common.py').read_text(),'common','exec'))
import numpy as np
def frame(x,z):
    x=x.normalized();z=(z-x*z.dot(x)).normalized();return Matrix((x,z.cross(x),z)).transposed()
U0=native['lowerarm_r'].translation-native['upperarm_r'].translation
F0=native['hand_r'].translation-native['lowerarm_r'].translation
N0=U0.cross(F0).normalized();FU0=frame(U0,N0);FL0=frame(F0,N0)
def arm(reference,target,phi=0.,shift=Vector(),write=True):
    row=clone(target)
    S0=reference['upperarm_r'].translation;E0=reference['lowerarm_r'].translation;H0=reference['hand_r'].translation
    S1=S0+shift;H=row['hand_r'].translation;A=(E0-S0).length;B=(H0-E0).length
    v=H-S1;d=v.length;axis=v.normalized()
    if d>=(A+B)*.98 or d<=abs(A-B)+.005:return None,{'score':1e12}
    along=(A*A-B*B+d*d)/(2*d);center=S1+axis*along;radius=math.sqrt(max(1e-10,A*A-along*along))
    pole=E0-center;pole-=axis*pole.dot(axis);E=center+Quaternion(axis,math.radians(phi))@pole.normalized()*radius
    u=E-S1;f=H-E;n=u.cross(f).normalized()
    du=(frame(u,n)@FU0.transposed()).to_quaternion();dl=(frame(f,n)@FL0.transposed()).to_quaternion()
    dh=row['hand_r'].to_quaternion()@native['hand_r'].to_quaternion().inverted()
    extra=dl.inverted()@dh
    tau=2*math.atan2(Vector((extra.x,extra.y,extra.z)).dot(F0.normalized()),extra.w)
    tau=(tau+math.pi)%(2*math.pi)-math.pi
    bend=math.degrees(f.normalized().angle(dh@F0.normalized()))
    ec,sc,hc=C@E,C@S1,C@H
    score=3*bend*bend+12*max(0.,bend-32.)**2
    score+=.28*(math.degrees(tau)-85.)**2+8*max(0.,abs(math.degrees(tau))-115.)**2
    score+=.4*phi*phi+5*(shift.length*1000)**2
    score+=2*max(0.,ec.z-min(sc.z,hc.z)+1)**2+4*max(0.,-ec.y)**2
    info={'score':score,'bend':bend,'roll':math.degrees(tau),'pole_degrees':phi,'shift_m':list(shift),'elbow_m':list(E)}
    if not write:return None,info
    row['clavicle_r']=reference['clavicle_r'].copy();row['clavicle_r'].translation+=shift
    row['upperarm_r']=Matrix.LocRotScale(S1,du@native['upperarm_r'].to_quaternion(),reference['upperarm_r'].to_scale())
    row['lowerarm_r']=Matrix.LocRotScale(E,dl@native['lowerarm_r'].to_quaternion(),reference['lowerarm_r'].to_scale())
    for name in names:
        if name in ('upperarm_r','lowerarm_r') or under(name,'hand_r') or not under(name,'upperarm_r'):continue
        upper=name.startswith('upperarm');q=(du if upper else dl)@native[name].to_quaternion()
        if name.startswith('lowerarm_twist'):
            q=Quaternion(f.normalized(),tau*(1. if '_01_' in name else .5))@q
        rel=local(reference,name)
        row[name]=Matrix.LocRotScale(row[parents[name]]@rel.translation,q,reference[name].to_scale())
    row['ik_hand_r']=row['hand_r'].copy()
    return row,info
def fit_arm(reference,target,previous=0.,cap=55.):
    candidates=[x*cap/11 for x in range(-11,12)]
    def score(p):return arm(reference,target,p,write=False)[1]['score']+.3*(p-previous)**2
    best=min(candidates,key=score)
    for step in (2.,1.,.5):best=min((max(-cap,best-step),best,min(cap,best+step)),key=score)
    row,info=arm(reference,target,best);return row,info

if __name__=='__main__':
    for family in ('base','skeleton_base'):
        for t in (.08,.15,.25,.325,.46,.55,.65):
            row,_=compose(entry(family,'quick_melee'),t);_,info=fit_arm(row,row)
            print(family,t,info,flush=True)
