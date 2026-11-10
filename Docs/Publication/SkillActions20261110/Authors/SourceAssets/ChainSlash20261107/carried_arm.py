"""Bound local joint changes relative to the accepted sword grip throughout a turn."""
import math
from mathutils import Quaternion, Vector

def limited_swing(a,b,limit):
    q=a.rotation_difference(b)
    return Quaternion().slerp(q,min(1.,limit/max(q.angle,1e-6)))

def solve(A,pose,idle,side,elbow_target,weight,shoulder_turn=None):
    if weight<=0:return
    n=lambda key:key+'_'+side
    u,l,h=[n(b) for b in ('upperarm','lowerarm','hand')]
    s0,e0,w0=[idle[k].translation for k in (u,l,h)]
    u0=(e0-s0).normalized();f0=(w0-e0).normalized()
    w=pose[h].translation
    carry=pose[h].to_quaternion()@idle[h].to_quaternion().inverted()
    ideal=carry@f0;guide=(w-elbow_target).normalized()
    tilt=limited_swing(ideal,guide,math.radians(20)*weight)
    fore=tilt@carry;f=fore@f0;e=w-f*(w0-e0).length
    # Transport the upper skin from the very same idle frame as the forearm.
    # This removes axial IK pole flips at almost folded or extended elbows.
    # Distribute bounded relative bend along the chain without changing bone length.
    axis=fore@u0
    preferred_shoulder=s0.copy()
    preferred_shoulder.y-=.06*weight
    preferred_shoulder.z-=.07*weight
    target=(e-preferred_shoulder).normalized()
    # Near a reversal choose the exterior shoulder direction rather than an
    # ambiguous 180-degree rotation axis. The camera is at the origin.
    if axis.dot(target)<-.82:
        outward=Vector((.55 if side=='l' else -.55,.72,.45))
        tangent=outward-axis*outward.dot(axis)
        target=(target+tangent*(max(0.,-axis.dot(target)-.82)*5)).normalized()
    normal=axis.cross(target)
    # This bounded rotation goes continuously to identity at the antipode.
    # A shortest-arc rotation there can alternate between opposite half turns.
    upper=Quaternion(normal.normalized(),math.radians(43)*normal.length*weight)@fore if normal.length>1.e-7 else fore
    if shoulder_turn is not None:
        turn=Vector(shoulder_turn)
        upper=fore@Quaternion(turn.normalized(),turn.length) if turn.length>1.e-8 else fore
    s=e-(upper@u0)*(e0-s0).length
    # Add only a small, continuous twist around the forearm; keep the wrist
    # station on the palm frame and the middle station halfway down the roll.
    twist=.34*math.sin(A.axis_angle(upper@fore.inverted(),f))*weight
    shaft=Quaternion(f,-twist)@fore
    for stem,origin,old,turn in [
        ('clavicle',s,s0,upper),('upperarm',s,s0,upper),('upperarm_twist_01',s,s0,upper),('upperarm_twist_02',s,s0,upper),
        ('lowerarm',e,e0,shaft),('lowerarm_twist_02',e,e0,Quaternion(f,.5*twist)@shaft),('lowerarm_twist_01',e,e0,fore)]:
        key=n(stem);ref=idle[key]
        pose[key]=A.mat(origin+turn@(ref.translation-old),turn@ref.to_quaternion(),ref.to_scale())
