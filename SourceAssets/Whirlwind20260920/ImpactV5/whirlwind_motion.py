"""V5: accepted anticipation, two connected drives and a weighted brake.

Grip, blade and both arms are baked together. UE owns the -720 degree turn.
Reference: BV18b4y1774T at 3:00-3:04, observed from local reference frames.
The reference's held horizontal blade, rapid sweep and follow-through inform
this adaptation; its video, mesh and audio are not game assets.
"""
import bisect
import json
import math
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
from diagonal_motion import READY,IDLE_FACE
from pommel_motion import shaft

P=Path(__file__).parent
T=json.loads((P.parents[2]/'Content/ColdSteelData/skills.json').read_text(encoding='utf-8'))['whirlwind']
FPS=480
READY_END=T['readySeconds']
SPIN_END=READY_END+T['spinSeconds']
ATTACK_END=SPIN_END+T['recoverSeconds']
IDLE=(READY,READY@IDLE_FACE)
COIL=shaft((.84,.10,.53),(.19,.35,-.145),25)
LOADED=shaft((.90,.08,.40),(.205,.30,-.17),25)
HELD=shaft((1,.10,0),(.16,.36,-.18),25)
LEAD=shaft((.97,.24,.025),(.05,.43,-.17),25)
PASS=shaft((1,.10,-.025),(.085,.38,-.195),25)
DRIVE=shaft((.98,.20,.015),(.035,.425,-.175),25)
FOLLOW=shaft((1,.08,-.035),(.065,.38,-.215),25)
BRAKE=shaft((.99,.08,.10),(.12,.32,-.235),25)
KNOTS=[0,READY_END*.28,READY_END*.68,READY_END,
       READY_END+T['spinSeconds']*.16,
       READY_END+T['spinSeconds']*.49,
       READY_END+T['spinSeconds']*.66,SPIN_END,
       SPIN_END+T['recoverSeconds']*.18,ATTACK_END]
KEYS=[IDLE,COIL,LOADED,HELD,LEAD,PASS,DRIVE,FOLLOW,BRAKE,IDLE]

def rotation_vector(q):
    q=q.normalized()
    if q.w<0:q.negate()
    angle=2*math.acos(max(-1,min(1,q.w)))
    axis=Vector((q.x,q.y,q.z))
    return axis.normalized()*angle if axis.length>1e-8 else Vector((0,0,0))

def rotation(v):
    return Quaternion(v.normalized(),v.length) if v.length>1e-8 else Quaternion((1,0,0,0))

def tangents(values):
    result=[Vector((0,0,0)) for _ in values]
    # Harmonic tangents slow down through the loaded section. Only a genuine
    # direction reversal stops an axis; passing knots do not stop the motion.
    for i in range(1,len(values)-1):
        before=KNOTS[i]-KNOTS[i-1];after=KNOTS[i+1]-KNOTS[i]
        a=(values[i]-values[i-1])/before;b=(values[i+1]-values[i])/after
        for axis in range(3):
            if a[axis]*b[axis]>0:
                w1=2*after+before;w2=after+2*before
                slope=(w1+w2)/(w1/a[axis]+w2/b[axis])
                limit=1.5*min(abs(a[axis]),abs(b[axis]))
                result[i][axis]=math.copysign(min(abs(slope),limit),slope)
    return result

def curve(values,velocity,t):
    t=max(KNOTS[0],min(KNOTS[-1],t))
    i=min(len(KNOTS)-2,max(0,bisect.bisect_right(KNOTS,t)-1))
    duration=KNOTS[i+1]-KNOTS[i];u=(t-KNOTS[i])/duration
    a=values[i];d=values[i+1]-a
    v0=velocity[i]*duration;v1=velocity[i+1]*duration
    # Quintic Hermite: shared endpoint velocities and zero endpoint
    # acceleration give C2 continuity across the complete trajectory.
    return a+v0*u+(10*d-6*v0-4*v1)*u**3+(-15*d+8*v0+7*v1)*u**4+(6*d-3*v0-3*v1)*u**5

BASE=KEYS[0][0].to_quaternion()
POSITIONS=[g.translation.copy() for g,s in KEYS]
ROTATIONS=[rotation_vector(BASE.inverted()@g.to_quaternion()) for g,s in KEYS]
FACES=[rotation_vector(g.to_quaternion().inverted()@s.to_quaternion()) for g,s in KEYS]
POSITION_VELOCITY=tangents(POSITIONS)
ROTATION_VELOCITY=tangents(ROTATIONS)
FACE_VELOCITY=tangents(FACES)

def poses(t):
    position=curve(POSITIONS,POSITION_VELOCITY,t)
    orientation=BASE@rotation(curve(ROTATIONS,ROTATION_VELOCITY,t))
    grip=Matrix.LocRotScale(position,orientation,Vector((1,1,1)))
    blade=grip@rotation(curve(FACES,FACE_VELOCITY,t)).to_matrix().to_4x4()
    return grip,blade
