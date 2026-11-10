"""Build connected skinning frames from the actual mesh bind pose."""
import math
from mathutils import Quaternion
def rebuild(A,pose,bind,side,strength):
    if strength<=0:return
    upper,lower,hand=['%s_%s'%(name,side) for name in ('upperarm','lowerarm','hand')]
    s,e,w=[pose[k].translation for k in (upper,lower,hand)]
    s0,e0,w0=[bind[k].translation for k in (upper,lower,hand)]
    ua=(e-s).normalized();fa=(w-e).normalized()
    ub=(e0-s0).normalized();fb=(w0-e0).normalized()
    palm=pose[hand].to_quaternion()@bind[hand].to_quaternion().inverted()
    wrist=(palm@fb).rotation_difference(fa)@palm
    original=pose[upper].to_quaternion()@bind[upper].to_quaternion().inverted()
    hinge=(original@fb).rotation_difference(fa)@original
    # Signed and bounded without a +/-180 jump. Axial roll occurs along the
    # forearm. Its elbow-side frame and the humerus meet in pure flexion.
    twist=.61*math.sin(A.axis_angle(wrist@hinge.inverted(),fa))
    fore=Quaternion(fa,-twist)@wrist
    humerus=(fore@ub).rotation_difference(ua)@fore
    for name,start,base,turn in [
        ('clavicle',s,s0,humerus),('upperarm',s,s0,humerus),('upperarm_twist_02',s,s0,humerus),('upperarm_twist_01',s,s0,humerus),
        ('lowerarm',e,e0,fore),('lowerarm_twist_02',e,e0,Quaternion(fa,.5*twist)@fore),('lowerarm_twist_01',e,e0,wrist)]:
        n=name+'_'+side; source=pose[n];target=start+turn@(bind[n].translation-base)
        pose[n]=A.mat(source.translation.lerp(target,strength),
                      source.to_quaternion().slerp(turn@bind[n].to_quaternion(),strength),source.to_scale())
