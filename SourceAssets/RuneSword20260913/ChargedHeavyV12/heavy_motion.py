"""Dedicated supported high-right charge and accelerated diagonal heavy cut.

Reference: accepted V6 load/cut/side-return and V8 nonlinear rhythm. Right hand
stays nearest the guard; left hand supports the pommel. Idle face remains an
independent local twist, never applied to the cutting edge during contact.
"""
from diagonal_motion import READY,IDLE_FACE,arc_frame,blend_pair,smooth

CHARGE_SECONDS=2.0
LOAD_END=1.9
CONTACT_END=.075
FOLLOW_END=.2375
ARREST_END=.2875
RETURN_CORNER=.5875
RELEASE_END=1.0
FPS=480

IDLE=(READY,READY@IDLE_FACE)
RAISED=arc_frame(1,8,(.23,.36,.035))
LOAD=arc_frame(1,-35,(.27,.30,.10))
HEAVY_LOAD=arc_frame(1,-48,(.28,.27,.16))
FINISH=arc_frame(1,216,(-.39,.25,-.34))
RETURN=arc_frame(1,125,(-.23,.37,-.12))

def charge_pose(t):
    if t<.65:return blend_pair(IDLE,RAISED,smooth(t/.65))
    if t<1.6:return blend_pair(RAISED,LOAD,smooth((t-.65)/.95))
    if t<LOAD_END:return blend_pair(LOAD,HEAVY_LOAD,smooth((t-1.6)/.3))
    return HEAVY_LOAD

def release_pose(t):
    if t<=CONTACT_END:
        u=max(0,t)/CONTACT_END;travel=u*u*(2-u)
        # 243 degrees: pull from behind the right shoulder, extend through the
        # centre, and carry down/out to the left. Both hands share this shaft.
        import math
        return arc_frame(1,-48+243*travel,
                         (.28-.63*travel,.27+.18*math.sin(math.pi*travel),.16-.46*travel))
    if t<=FOLLOW_END:
        u=(t-CONTACT_END)/(FOLLOW_END-CONTACT_END);carry=1-(1-u)**3
        return arc_frame(1,195+21*carry,(-.35-.04*carry,.27-.02*carry,-.30-.04*carry))
    if t<=ARREST_END:return FINISH
    if t<RETURN_CORNER:return blend_pair(FINISH,RETURN,smooth((t-ARREST_END)/(RETURN_CORNER-ARREST_END)))
    return blend_pair(RETURN,IDLE,smooth((t-RETURN_CORNER)/(RELEASE_END-RETURN_CORNER)))

def full_pose(t):
    return charge_pose(t) if t<=CHARGE_SECONDS else release_pose(t-CHARGE_SECONDS)
