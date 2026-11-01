"""C8 returning-thunder forging: broad closed silver knots, no lightning fin."""
import numpy as np
CX=-.0004452141001820564
CZ=.9095
STYLES=[dict(id='guan_lei_seat',name='贯雷锤座',bulk=.0038,width=.0031,depth=.00155,
 paths=[[(.035,.968),(.047,.974),(.058,.966),(.058,.956),(.049,.943),
         (.040,.949),(.047,.958),(.051,.964),(.046,.968),(.035,.968)],
        [(.043,.972),(.039,.965),(.045,.960)]],
 lower=True,seams=True,
 appearance='原厂雷纹圆徽 · 闭合嵌银回环结 · 宽厚回折锻肩')]

def smooth(a,b,v):
 t=np.clip((v-a)/(b-a),0,1);return t*t*(3-2*t)
def distance(x,z,paths):
 out=np.full(np.shape(x),1.,dtype=np.float64)
 for path in paths:
  for a,b in zip(path,path[1:]):
   vx=b[0]-a[0];vz=b[1]-a[1];t=np.clip(((x-a[0])*vx+(z-a[1])*vz)/(vx*vx+vz*vz),0,1)
   out=np.minimum(out,np.sqrt((x-a[0]-t*vx)**2+(z-a[1]-t*vz)**2))
 return out
def fields(p,s):
 x=np.abs(p[:,0]-CX);z=p[:,2];y=np.abs(p[:,1]);r=np.sqrt((x/.0535)**2+((z-CZ)/.0412)**2)
 # Freeze the factory seal and every real head/neck mating surface. Broader
 # shoulders grow in depth and sweep back into the body without floating rails.
 gate=smooth(1.055,1.14,r)*(1-smooth(.0618,.0641,x))*smooth(.846,.851,z)*(1-smooth(.975,.979,z))*smooth(.019,.029,y)
 d=np.minimum(distance(x,z,s['paths']),distance(x,2*CZ-z,s['paths']))
 outer=s['width']*.5;inner=s['width']*.22
 carved=smooth(outer,inner,d);silver=smooth(inner,inner-.00024,d)*gate
 incision=-s['depth']*carved+(s['depth']-.00022)*smooth(inner,inner-.00028,d)
 upper=((x-.048)/.017)**2+((z-.957)/.021)**2
 lower=((x-.048)/.017)**2+((z-.862)/.018)**2
 shoulder=1-smooth(.10,1.1,np.minimum(upper,lower))
 # Broad recessed edge tracing the returning knot, not JiLei's parallel
 # upward lightning strokes. No protruding bands or separate steel bars.
 contours=[[(.031,.973),(.042,.976),(.060,.969),(.061,.953),(.055,.938)]]
 ds=np.minimum(distance(x,z,contours),distance(x,2*CZ-z,contours))
 seam=smooth(.00072,.00020,ds)*gate
 depth=(s['bulk']*shoulder+incision)*gate-.00060*seam
 return depth,silver,carved*gate,seam,shoulder*gate
def deformation(p,s):
 d=fields(p,s)[0];return np.where(p[:,1]<0,-d,d)
