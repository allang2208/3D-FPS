import math
from mathutils import Vector,Matrix
from diagonal_motion import READY,IDLE_FACE,arc_frame,blend_pair,smooth
FPS=480
RAISE_END=.20
HOLD_END=.35
BREAK_SECONDS=.40
TOTAL=HOLD_END+BREAK_SECONDS
IDLE=(READY,READY@IDLE_FACE)
grip,blade=arc_frame(-1,18,(.20,.46,-.14))
direction=blade.to_3x3()@Vector((0,0,1))
edge=Vector((0,-1,0)).cross(direction).normalized()
normal=direction.cross(edge).normalized()
blade=Matrix((edge,normal,direction)).transposed().to_4x4()
blade.translation=grip.translation
GUARD=(grip,blade)
DROPPED=arc_frame(-1,48,(.25,.33,-.27))
def poses(t):
    if t<RAISE_END:return blend_pair(IDLE,GUARD,smooth(t/RAISE_END))
    if t<=HOLD_END:return GUARD
    u=t-HOLD_END
    if u<.12:return blend_pair(GUARD,DROPPED,smooth(u/.12))
    return blend_pair(DROPPED,IDLE,smooth((u-.12)/(BREAK_SECONDS-.12)))
