"""Copy the complete M4 slap chain; adapt contact by rigid arm translation."""
from mathutils import Matrix,Vector

def smooth(a,b,f):
 t=max(0.,min(1.,(f-a)/(b-a)));return t*t*(3.-2.*t)

def align_release_hand(p,frame,slap,parents,release_frame=116.):
 # Only enter after the drum has seated. Full M4 articulation covers the
 # wind-up, strike and rebound; the source drum owns the final idle handoff.
 # Standard/extended magazines retain M4's frame 130 contact and 162 end;
 # the drum uses the same articulation fourteen source frames earlier.
 phase=frame-(release_frame-116.)
 weight=smooth(88.,108.,phase)*(1.-smooth(134.,148.,phase))
 if weight<=0:return
 root_delta=p['WPN_root']@slap['WPN_root'].inverted()
 # Fit in weapon coordinates; translating the clavicle and its complete
 # descendants preserves M4 elbow/wrist/finger and twist-bone rotations.
 offset=p['WPN_root'].to_3x3()@Vector(CONTACT_SHIFT)
 target={n:Matrix.Translation(offset)@root_delta@m for n,m in slap.items() if n.endswith('_l') and n in p}
 original={n:m.copy() for n,m in p.items()}
 for n in target:
  parent=parents[n];a=original[parent].inverted()@original[n]
  b=(target[parent] if parent in target else original[parent]).inverted()@target[n]
  loc,q,scale=a.decompose();loc1,q1,scale1=b.decompose()
  p[n]=p[parent]@Matrix.LocRotScale(loc.lerp(loc1,weight),q.slerp(q1,weight),scale.lerp(scale1,weight))

# Replaced by the source-model palm/button fit in HK416SlapSights20261001.
CONTACT_SHIFT=(.000704320148,.011797219515,.008466903120)
