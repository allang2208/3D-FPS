"""Keep both original grips rigid; fit the rifle bearing around its stock path."""
import math
from mathutils import Matrix,Vector,Quaternion

class GripBearing:
 def __init__(self,idle,rest,stock):
  self.idle,self.rest,self.stock=idle,rest,stock
  self.hands={s:idle['WPN_root'].inverted()@idle['hand_'+s] for s in ('r','l')}
  self.ref=(rest['hand_r'].translation-rest['lowerarm_r'].translation).normalized()
  self.lengths={s:((idle['lowerarm_'+s].translation-idle['upperarm_'+s].translation).length,
                  (idle['hand_'+s].translation-idle['lowerarm_'+s].translation).length) for s in ('r','l')}
  self.previous=Vector();self.translation=Vector()
 def fit(self,root,shoulders,weight):
  stock_initial=root@self.stock
  pivot=(root@self.hands['r']).translation
  def candidate(v,shift):
   angle=v.length
   q=Quaternion(v/angle,angle) if angle>1e-8 else Quaternion()
   transform=Matrix.Translation(pivot)@q.to_matrix().to_4x4()@Matrix.Translation(-pivot)
   gun=transform@root;gun.translation+=shift
   h=gun@self.hands['r'];wr=h.translation;sh=shoulders['r']
   a,b=self.lengths['r'];d=(wr-sh).length;axis=(wr-sh).normalized()
   along=(a*a-b*b+d*d)/(2*d);radius=math.sqrt(max(0,a*a-along*along))
   desired=h.to_quaternion()@self.rest['hand_r'].to_quaternion().inverted()@self.ref
   pole=-desired+axis*desired.dot(axis);pole.normalize()
   elbow=sh+axis*along+pole*radius
   bend=desired.angle((wr-elbow).normalized())
   reach=0.
   for side in ('r','l'):
    dist=((gun@self.hands[side]).translation-shoulders[side]).length
    upper,lower=self.lengths[side]
    reach+=max(0,dist-(upper+lower)*.94)**2
   stock_error=(gun@self.stock-stock_initial).length_squared
   cost=(250*max(0,bend-math.radians(24))**2+.1*bend*bend+angle*angle
         +.3*(v-self.previous).length_squared+80*shift.length_squared
         +20*(shift-self.translation).length_squared+30*stock_error+20000*reach)
   return cost,gun,bend,elbow
  cap=math.radians(100)*weight
  def limit(v):return v.normalized()*cap if v.length>cap else v
  best=min([Vector(),limit(self.previous)],key=lambda v:candidate(v,self.translation)[0])
  shift=self.translation.copy()
  for step in (math.radians(v)*weight for v in (24,12,6,3,1.5,.75,.375)):
   for iteration in range(10):
    options=[(best,shift)]
    for axis in range(3):
     for sign in (-1,1):
      v=best.copy();v[axis]+=step*sign;options.append((limit(v),shift))
      t=shift.copy();t[axis]+=.12*step*sign
      if t.length<=.16*weight:options.append((best,t))
    nxt,tr=min(options,key=lambda x:candidate(*x)[0])
    if (nxt-best).length+(tr-shift).length<1e-8:break
    best,shift=nxt,tr
  self.previous=best.copy();self.translation=shift.copy()
  _,gun,bend,elbow=candidate(best,shift)
  return gun,{'bearing_adjustment_deg':math.degrees(best.length),'min_bend_deg':math.degrees(bend),
              'rotation_vector':list(best),'translation_cm':[100*x for x in shift],
              'stock_delta_cm':[100*x for x in (gun@self.stock-stock_initial)],'elbow':list(elbow)}
