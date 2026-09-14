"""Third normal attack: supported high-to-low preparation into a forward thrust."""
from mathutils import Vector,Matrix
from diagonal_motion import READY,IDLE_FACE,arc_frame,blend_pair,smooth

FPS=480
ALIGN_END=.24
LOAD_END=.40
CONTACT_START=.48
EXTENSION_END=.58
CONTACT_END=.64
ARREST_END=.64
RETURN_CORNER=.94
ATTACK_END=1.25
LUNGE_START=.40
LUNGE_END=.64
LUNGE_CM=100.0
IDLE=(READY,READY@IDLE_FACE)

def aimed_frame(position):
    # Both the hilt and the blade use one shaft. The edge stays independent of
    # the idle face, just as in the accepted diagonal slashes.
    grip,blade=arc_frame(1,90,position)
    direction=(Vector((0,1.65,0))-Vector(position)).normalized()
    rotation=Vector((0,1,0)).rotation_difference(direction).to_matrix().to_4x4()
    result=[]
    for frame in (grip,blade):
        basis=rotation@frame;basis.translation=Vector(position);result.append(basis)
    return tuple(result)

ALIGNED=aimed_frame((.14,.39,-.16))
LOADED=aimed_frame((.10,.30,-.12))
EXTENDED=aimed_frame((.03,.79,-.07))

def poses(t):
    if t<ALIGN_END:return blend_pair(IDLE,ALIGNED,smooth(t/ALIGN_END))
    if t<LOAD_END:return blend_pair(ALIGNED,LOADED,smooth((t-ALIGN_END)/(LOAD_END-ALIGN_END)))
    if t<=CONTACT_START:return LOADED
    if t<EXTENSION_END:
        u=smooth((t-CONTACT_START)/(EXTENSION_END-CONTACT_START))
        return aimed_frame(Vector((.10,.30,-.12)).lerp(Vector((.03,.79,-.07)),u))
    if t<=ARREST_END:return EXTENDED
    if t<RETURN_CORNER:
        # Leave the contact axis first; start decisively and decelerate before
        # rotating back upright. The handle and both fists retreat together.
        u=(t-ARREST_END)/(RETURN_CORNER-ARREST_END)
        return blend_pair(EXTENDED,ALIGNED,1-(1-u)**3)
    return blend_pair(ALIGNED,IDLE,smooth((t-RETURN_CORNER)/(ATTACK_END-RETURN_CORNER)))
