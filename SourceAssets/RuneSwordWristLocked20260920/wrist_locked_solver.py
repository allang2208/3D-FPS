"""Support the proximal elbow while retaining the pre-V3 wrist approach.

All joint origins are fixed. Hand and distal lowerarm_twist_01 keep their full
source transforms. Only upper-arm roll and the elbow-side skin supports change.
"""
import math
from mathutils import Matrix,Quaternion,Vector

UPPER_CAP=math.radians(45.)
ELBOW_CAP=math.radians(60.)
DISTAL_LOCK_STATION=.78

def smooth(x):
 x=max(0.,min(1.,x));return x*x*x*(10.-15.*x+6.*x*x)
def axial(a,b,axis):
 q=a@b.inverted()
 return (2*math.atan2(Vector((q.x,q.y,q.z)).dot(axis),q.w)+math.pi)%(2*math.pi)-math.pi
def unwrap(x,previous):return x if previous is None else previous+(x-previous+math.pi)%(2*math.pi)-math.pi

def support_elbow(source,rest,stations,side,state,weight):
 if weight<1e-8:
  # A full spin or a free-hand pose can wind the source angle by a revolution.
  # Idle support resumes on its own branch after that non-contact interval.
  state.pop(side+'_seam',None)
  return {}
 U,F,H=[n+'_'+side for n in ('upperarm','lowerarm','hand')]
 upper_axis=(source[F].translation-source[U].translation).normalized()
 fore_axis=(source[H].translation-source[F].translation).normalized()
 rest_fore=(rest[H].translation-rest[F].translation).normalized()
 original_upper=source[U].to_quaternion()@rest[U].to_quaternion().inverted()
 original_fore=source[F].to_quaternion()@rest[F].to_quaternion().inverted()
 def seam(roll):
  up=Quaternion(upper_axis,roll)@original_upper
  hinge=(up@rest_fore).rotation_difference(fore_axis)@up
  return axial(original_fore,hinge,fore_axis)
 original_seam=unwrap(seam(0.),state.get(side+'_seam'));state[side+'_seam']=original_seam
 # Preserve already supported working poses. No new bend plane, IK pole or
 # per-frame hand reconstruction is introduced on top of the accepted motion.
 influence=weight*smooth((abs(original_seam)-math.radians(8.))/math.radians(35.))
 if influence<1e-8:return {}
 def cost(roll):
  error=unwrap(seam(roll),original_seam)
  return error*error+.20*roll*roll
 steps=30
 candidates=[-UPPER_CAP+2*UPPER_CAP*i/steps for i in range(steps+1)]
 best=min(candidates,key=cost);interval=2*UPPER_CAP/steps
 lo,hi=max(-UPPER_CAP,best-interval),min(UPPER_CAP,best+interval)
 for _ in range(15):
  a=lo+(hi-lo)*.382;b=lo+(hi-lo)*.618
  if cost(a)<cost(b):hi=b
  else:lo=a
 upper_roll=(lo+hi)*.5*influence
 upper_turn=Quaternion(upper_axis,upper_roll)
 remaining=unwrap(seam(upper_roll),original_seam)
 elbow_correction=max(-ELBOW_CAP,min(ELBOW_CAP,remaining))*influence
 result={}
 def rotate_only(n,turn):
  m=source[n]
  result[n]=Matrix.LocRotScale(m.translation,turn@m.to_quaternion(),m.decompose()[2])
 for n in (U,'upperarm_twist_01_'+side,'upperarm_twist_02_'+side):rotate_only(n,upper_turn)
 rotate_only(F,Quaternion(fore_axis,-elbow_correction))
 proximal='lowerarm_twist_02_'+side
 station=stations[side][proximal]
 share=max(0.,min(1.,1.-station/DISTAL_LOCK_STATION))
 rotate_only(proximal,Quaternion(fore_axis,-elbow_correction*share))
 # The wrist-side twist bone, hand, fingers, and every joint origin are source
 # anchors. Compensating parent-local keys keep those world transforms fixed.
 return result
