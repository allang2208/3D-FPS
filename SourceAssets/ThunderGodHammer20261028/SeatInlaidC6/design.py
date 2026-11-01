"""Selected C language: carve the native solid, with flush silver-filled floors."""
import numpy as np
CX=-.0004452141001820564
CZ=.9095
STYLES=[
 dict(id='reinforced_block',name='厚壁重铸座',bulk=.0022,width=.0030,depth=.00115,paths=[[(.043,.969),(.057,.953),(.050,.949),(.060,.935)]],lower=True,seams=False,appearance='原厂雷纹圆徽 · 厚肩锻体 · 宽槽嵌银雷纹'),
 dict(id='ribbed_light',name='镂肋轻型座',bulk=-.0014,width=.0023,depth=.0010,paths=[[(.046,.970),(.056,.958),(.049,.953),(.058,.940)]],lower=False,seams=False,appearance='原厂雷纹圆徽 · 内收镂空肩部 · 单路嵌银雷纹'),
 dict(id='laminated_damper',name='叠片缓冲座',bulk=.0008,width=.0026,depth=.00105,paths=[[(.044,.968),(.056,.954),(.051,.949),(.059,.938)]],lower=True,seams=True,appearance='原厂雷纹圆徽 · 内嵌缓冲层缝 · 折槽嵌银雷纹'),
]
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
 # Native seal, head interfaces, neck mating face and cap lip are immutable.
 gate=smooth(1.055,1.14,r)*(1-smooth(.0618,.0641,x))*smooth(.846,.851,z)*(1-smooth(.975,.979,z))*smooth(.019,.029,y)
 d=distance(x,z,s['paths'])
 if s['lower']:d=np.minimum(d,distance(x,2*CZ-z,s['paths']))
 width=s['width'];outer=width*.5;inner=width*.22
 carved=smooth(outer,inner,d)
 silver=smooth(inner,inner-.00024,d)*gate
 # Silver floor sits 0.22 mm below the neighboring native surface; dark channel
 # walls remain deeper. This is one continuous solid, not added strip geometry.
 incision=-s['depth']*carved+(s['depth']-.00022)*smooth(inner,inner-.00028,d)
 upper=np.maximum(np.abs((x-.048)/.016),np.abs((z-.958)/.019))
 lower=np.maximum(np.abs((x-.048)/.016),np.abs((z-.862)/.015))
 shoulder=(1-smooth(.32,1.,np.minimum(upper,lower)))
 seam=np.zeros_like(x)
 if s['seams']:
  lines=[[(.030,.972),(.043,.967),(.058,.955)],[(.031,.968),(.044,.963),(.058,.951)]]
  ds=np.minimum(distance(x,z,lines),distance(x,2*CZ-z,lines))
  seam=smooth(.00065,.00017,ds)*gate
  # Recessed layer seams stop on the casting instead of protruding steel leaves.
 depth=(s['bulk']*shoulder+incision)*gate-.00055*seam
 return depth,silver,carved*gate,seam,shoulder*gate
def deformation(p,s):
 d=fields(p,s)[0];return np.where(p[:,1]<0,-d,d)
