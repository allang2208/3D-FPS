"""Right-high to left-low cut; mirror the weapon path without swapping hands.

Grip orientation and blade-facing orientation are separate authoring channels.
The blade's width axis stays tangent to the cutting arc during active contact.
"""
import math
from mathutils import Matrix,Vector

WINDUP_END=.40
CONTACT_START=.90
CONTACT_END=1.015
FOLLOW_END=1.115
ATTACK_END=1.65
READY=Matrix.Translation((.13,.48,-.08))@Matrix.Rotation(math.radians(-18),4,'X')@Matrix.Rotation(math.radians(65),4,'Z')
IDLE_FACE=Matrix.Rotation(math.radians(50),4,'Z')

def smooth(t):
    t=max(0,min(1,t));return t*t*(3-2*t)

def blend(a,b,t):
    return Matrix.LocRotScale(a.translation.lerp(b.translation,t),a.to_quaternion().slerp(b.to_quaternion(),t),Vector((1,1,1)))

def blend_pair(a,b,t):
    grip=blend(a[0],b[0],t)
    roll_a=(a[0].inverted()@a[1]).to_quaternion()
    roll_b=(b[0].inverted()@b[1]).to_quaternion()
    # Interpolate only the local twist. Independently slerping two world
    # rotations could separate the blade axis from the two-hand hilt axis.
    return grip,grip@roll_a.slerp(roll_b,t).to_matrix().to_4x4()

def arc_frame(sign,theta,position):
    diagonal=Vector((sign*.75,0,.66)).normalized();forward=Vector((0,1,0))
    theta=math.radians(theta)
    blade=diagonal*math.cos(theta)+forward*math.sin(theta)
    edge=-diagonal*math.sin(theta)+forward*math.cos(theta)
    normal=blade.cross(edge).normalized()
    blade_pose=Matrix((edge,normal,blade)).transposed().to_4x4()
    blade_pose.translation=Vector(position)
    # A stable grasp basis follows the blade axis while roll is solved through
    # the complete arms. Blade width follows the cutting plane independently.
    yaw=math.atan2(-blade.x,blade.y);tilt=-math.acos(max(-1,min(1,blade.z)))
    grip_pose=Matrix.Translation(position)@Matrix.Rotation(yaw,4,'Z')@Matrix.Rotation(tilt,4,'X')@Matrix.Rotation(math.radians(25),4,'Z')
    return grip_pose,blade_pose

def poses(name,t):
    sign=1 if name=='Slash1' else -1
    load=arc_frame(sign,-35,(sign*.27,.30,.10))
    if t<WINDUP_END:
        # First move the hilt out to the side, then lift and draw back. This
        # keeps the guard readable while most of the blade leaves the screen.
        raised=arc_frame(sign,8,(sign*.23,.36,.035))
        if t<.17:
            u=smooth(t/.17)
            return blend_pair((READY,READY@IDLE_FACE),raised,u)
        u=smooth((t-.17)/(WINDUP_END-.17))
        return blend_pair(raised,load,u)
    if t<=CONTACT_START:return load
    if t<=CONTACT_END:
        u=(t-CONTACT_START)/(CONTACT_END-CONTACT_START)
        # Zero initial speed releases from the hold into a 220-degree cut.
        # The final slope remains nonzero so the blade carries through the hit.
        travel=u*u*(2-u)
        theta=-35+220*travel
        y=.30+.15*math.sin(math.pi*travel)
        return arc_frame(sign,theta,(sign*(.27-.59*travel),y,.10-.37*travel))
    finish=arc_frame(sign,208,(-sign*.37,.26,-.31))
    if t<=FOLLOW_END:
        u=(t-CONTACT_END)/(FOLLOW_END-CONTACT_END)
        carry=1-(1-u)**3
        return arc_frame(sign,185+23*carry,(-sign*(.32+.05*carry),.30-.04*carry,-.27-.04*carry))
    # Stay at the outside edge while lifting the hilt, then return to idle.
    # Only this final return blends back to the requested left-face idle view.
    raised_return=arc_frame(sign,125,(-sign*.23,.37,-.12))
    if t<1.34:
        u=smooth((t-FOLLOW_END)/(1.34-FOLLOW_END))
        return blend_pair(finish,raised_return,u)
    u=smooth((t-1.34)/(ATTACK_END-1.34))
    return blend_pair(raised_return,(READY,READY@IDLE_FACE),u)
