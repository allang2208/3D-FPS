"""Original precision industrial modelling toolkit, metres, Blender 4.3+.
Closed primitives, physically sized UVs and separate functional UCX collisions.
This is production geometry generation, not a visual or gameplay test harness.
"""
import math
from collections import defaultdict
from mathutils import Vector
G={};C=defaultdict(list);ROOM=None
FACES=[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
def group(kind):return G.setdefault((ROOM,kind),dict(v=[],f=[],m=[],uv=[],smooth=[]))
def poly(kind,vs,fs,mat,uv=None,smooth=False):
 g=group(kind);off=len(g['v']);g['v'].extend(tuple(v) for v in vs);g['f'].extend(tuple(off+i for i in f) for f in fs)
 g['m'].extend([mat]*len(fs));g['uv'].extend(uv if uv is not None else [None]*len(fs));g['smooth'].extend(smooth if isinstance(smooth,list) else [smooth]*len(fs))
def hull(kind,vs,fs):C[(ROOM,kind)].append(([tuple(p) for p in vs],fs))
def box(kind,c,size,mat='Concrete',yaw=0,collision=False):
 assert min(size)>0,('positive dimensions',kind,size)
 co,si=math.cos(yaw),math.sin(yaw);a,b,h=[x/2 for x in size]
 vs=[(c[0]+dx*co-dy*si,c[1]+dx*si+dy*co,c[2]+dz) for dx,dy,dz in [(-a,-b,-h),(a,-b,-h),(a,b,-h),(-a,b,-h),(-a,-b,h),(a,-b,h),(a,b,h),(-a,b,h)]]
 if kind:poly(kind,vs,FACES,mat)
 if collision:hull(collision if isinstance(collision,str) else kind,vs,FACES)
def basis(axis):
 n=Vector(axis).normalized();a=Vector((0,0,1)).cross(n) if abs(n.z)<.9 else Vector((1,0,0));a.normalize();return n,a,n.cross(a)
def beam(kind,a,b,width,height,mat='Steel',collision=False):
 a,b=Vector(a),Vector(b);n,u,v=basis(b-a);vs=[p+u*x*width/2+v*y*height/2 for p in (a,b) for x,y in [(-1,-1),(1,-1),(1,1),(-1,1)]]
 poly(kind,vs,FACES,mat)
 if collision:hull(kind,vs,FACES)
def prism(kind,outline,z0,z1,mat='Concrete',collision=False):
 n=len(outline);vs=[(x,y,z) for z in (z0,z1) for x,y in outline];fs=[tuple(reversed(range(n))),tuple(n+i for i in range(n))]
 fs.extend((i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n));poly(kind,vs,fs,mat)
 if collision:hull(kind,vs,fs)
def lathe(kind,c,axis,profile,mat='Steel',segments=40,collision=False):
 n,u,v=basis(axis);c=Vector(c);vs=[];fs=[];uv=[];sm=[]
 for z,r in profile:vs.extend(c+n*z+(u*math.cos(i*math.tau/segments)+v*math.sin(i*math.tau/segments))*r for i in range(segments))
 for k in range(len(profile)-1):
  for i in range(segments):
   j=(i+1)%segments;fs.append((k*segments+i,k*segments+j,(k+1)*segments+j,(k+1)*segments+i));rr=(profile[k][1]+profile[k+1][1])/2
   uv.append([(i/segments*math.tau*rr,profile[k][0]),((i+1)/segments*math.tau*rr,profile[k][0]),((i+1)/segments*math.tau*rr,profile[k+1][0]),(i/segments*math.tau*rr,profile[k+1][0])]);sm.append(True)
 fs.extend([tuple(reversed(range(segments))),tuple((len(profile)-1)*segments+i for i in range(segments))]);uv.extend([None,None]);sm.extend([False,False]);poly(kind,vs,fs,mat,uv,sm)
 if collision:hull(kind,vs,fs)
def cylinder(kind,a,b,r,mat='Steel',segments=24,collision=False):
 a,b=Vector(a),Vector(b);lathe(kind,a,b-a,[(0,r),((b-a).length,r)],mat,segments,collision)
def ring(kind,c,axis,outer,inner,depth,mat='Steel',segments=40):
 n,u,v=basis(axis);c=Vector(c);vs=[];fs=[];sm=[]
 for z,r in [(-depth/2,outer),(depth/2,outer),(depth/2,inner),(-depth/2,inner)]:vs.extend(c+n*z+(u*math.cos(i*math.tau/segments)+v*math.sin(i*math.tau/segments))*r for i in range(segments))
 for k in range(4):
  for i in range(segments):j=(i+1)%segments;kk=(k+1)%4;fs.append((k*segments+i,k*segments+j,kk*segments+j,kk*segments+i));sm.append(k%2==0)
 poly(kind,vs,fs,mat,smooth=sm)
def torus(kind,c,axis,major,minor,mat='Steel',segments=40,sides=8):
 n,u,v=basis(axis);c=Vector(c);vs=[];fs=[]
 for i in range(segments):
  d=u*math.cos(i*math.tau/segments)+v*math.sin(i*math.tau/segments)
  for j in range(sides):t=j*math.tau/sides;vs.append(c+d*(major+minor*math.cos(t))+n*minor*math.sin(t))
 for i in range(segments):
  for j in range(sides):fs.append((i*sides+j,((i+1)%segments)*sides+j,((i+1)%segments)*sides+(j+1)%sides,i*sides+(j+1)%sides))
 poly(kind,vs,fs,mat,smooth=True)
def tube(kind,points,r,mat='Rubber',sides=12):
 ps=[Vector(p) for p in points];frames=[];previous=None;dist=[0]
 for i,p in enumerate(ps):
  t=(ps[min(i+1,len(ps)-1)]-ps[max(0,i-1)]).normalized()
  if previous is None:n,a,b=basis(t)
  else:a=(previous-t*previous.dot(t)).normalized();b=t.cross(a)
  previous=a;frames.append((p,t,a,b))
  if i:dist.append(dist[-1]+(p-ps[i-1]).length)
 vs=[];fs=[];uv=[]
 for p,t,a,b in frames:vs.extend(p+r*(a*math.cos(j*math.tau/sides)+b*math.sin(j*math.tau/sides)) for j in range(sides))
 for i in range(len(ps)-1):
  for j in range(sides):
   k=(j+1)%sides;fs.append((i*sides+j,i*sides+k,(i+1)*sides+k,(i+1)*sides+j));uv.append([(j/sides*math.tau*r,dist[i]),((j+1)/sides*math.tau*r,dist[i]),((j+1)/sides*math.tau*r,dist[i+1]),(j/sides*math.tau*r,dist[i+1])])
 fs.extend([tuple(reversed(range(sides))),tuple((len(ps)-1)*sides+j for j in range(sides))]);uv.extend([None,None]);poly(kind,vs,fs,mat,uv,[True]*(len(fs)-2)+[False,False])
def rounded_pipe(kind,points,r,mat='Enamel',sides=20):
 ps=[Vector(p) for p in points];path=[ps[0]]
 for i in range(1,len(ps)-1):
  p=ps[i];a=(p-ps[i-1]).normalized();b=(ps[i+1]-p).normalized();reach=min(max(.25,r*2.2),(p-ps[i-1]).length*.4,(ps[i+1]-p).length*.4);start=p-a*reach;end=p+b*reach
  for j in range(9):t=j/8;path.append((1-t)**2*start+2*t*(1-t)*p+t*t*end)
 path.append(ps[-1]);tube(kind,path,r,mat,sides)
def bolt(kind,c,axis,r=.022):
 c=Vector(c);n=Vector(axis).normalized();lathe(kind,c,n,[(0,r*1.35),(.006,r*1.35)],'Steel',12);lathe(kind,c+n*.006,n,[(0,r),(.022,r)],'Steel',6)
def flange(kind,c,axis,r,bolts=12):
 n,u,v=basis(axis);c=Vector(c)
 for offset in (-.026,.026):ring(kind,c+n*offset,n,r+.095,r*.85,.038,'Steel')
 ring(kind,c,n,r+.073,r*.88,.014,'Rubber')
 for i in range(bolts):a=i*math.tau/bolts;bolt(kind,c+n*.05+(u*math.cos(a)+v*math.sin(a))*(r+.045),n,.018)
def rail(a,b,kind='Rails',height=1.08):
 a,b=Vector(a),Vector(b);d=b-a;horiz=Vector((d.x,d.y,0)).normalized();side=Vector((-horiz.y,horiz.x,0))
 for z in (.50,height):tube(kind,[a+Vector((0,0,z)),b+Vector((0,0,z))],.032,'Yellow',12)
 count=max(1,math.ceil(d.length/1.25))
 for i in range(count+1):
  p=a+d*i/count;box(kind,p+Vector((0,0,height/2)),(.058,.058,height),'Paint');box(kind,p+Vector((0,0,.015)),(.16,.16,.03),'Steel')
 vs=[p+side*s*.04+Vector((0,0,z)) for p in (a,b) for s,z in [(-1,0),(1,0),(1,height+.035),(-1,height+.035)]];hull(kind,vs,FACES)
def stairs(x,y,width,count,rise=.16,going=.36,base=0):
 for i in range(count):
  top=base+(i+1)*rise;box('Structure',(x,y+(i+.5)*going,(base+top)/2),(width,going,top-base),'Concrete',collision=True);box('Trim',(x,y+(i+.04)*going,top+.004),(width-.03,.025,.008),'Yellow')
 for s in (-1,1):rail((x+s*(width/2+.02),y+.5*going,base+rise),(x+s*(width/2+.02),y+(count-.5)*going,base+count*rise))
def wall(a,b,height,door=False,thickness=.30):
 a,b=Vector(a),Vector(b);d=b-a;length=d.length;yaw=math.atan2(d.y,d.x);d.normalize()
 def fill(lo,hi,z0,z1):
  if hi-lo<.001:return
  p=a+d*(lo+hi)/2;box('Structure',(p.x,p.y,(z0+z1)/2),(hi-lo,thickness,z1-z0),'Concrete',yaw,True)
 if door:
  fill(0,length/2-1.56,0,height);fill(length/2-1.56,length/2+1.56,2.86,height);fill(length/2+1.56,length,0,height)
  for t in (length/2-1.535,length/2+1.535):p=a+d*t;box('Structure',(p.x,p.y,1.4),(.07,thickness+.08,2.8),'Steel',yaw,True)
  p=(a+b)/2;box('Structure',(p.x,p.y,2.835),(3.14,thickness+.08,.07),'Steel',yaw,True)
 else:fill(0,length,0,height)
 for lo,hi in ([(0,length/2-1.59),(length/2+1.59,length)] if door else [(0,length)]):
  p=a+d*(lo+hi)/2
  for z in (.16,1.48):box('Trim',(p.x,p.y,z),(hi-lo,thickness+.025,.045),'Paint',yaw)
def pavement(x0,y0,x1,y1,step=1.25):
 box('Structure',((x0+x1)/2,(y0+y1)/2,-.14),(x1-x0,y1-y0,.28),'Concrete',collision=True)
 nx=math.ceil((x1-x0)/step);ny=math.ceil((y1-y0)/step);dx=(x1-x0)/nx;dy=(y1-y0)/ny
 for ix in range(nx):
  for iy in range(ny):box('FloorFinish',(x0+(ix+.5)*dx,y0+(iy+.5)*dy,-.009),(dx-.012,dy-.012,.02),'Floor')
def i_column(x,y,h):
 box('Structure',(x,y,h/2),(.075,.38,h),'Paint',collision=True)
 for yy in (-.205,.205):box('Structure',(x,y+yy,h/2),(.42,.045,h),'Paint',collision=True)
 box('Structure',(x,y,.055),(.68,.72,.11),'Steel',collision=True)
 for dx in (-.24,.24):
  for dy in (-.27,.27):bolt('Hardware',(x+dx,y+dy,.11),(0,0,1),.032)
def insulator(c,height=.5,r=.095):
 x,y,z=c;profile=[(0,r*.72)]
 for i in range(5):t=height*i/5;profile.extend([(t+.006,r*.72),(t+height*.055,r*1.25),(t+height*.13,r*1.25),(t+height*.17,r*.72)])
 profile.append((height,r*.65));lathe('Hardware',c,(0,0,1),profile,'Ceramic',24);cylinder('Hardware',(x,y,z-.03),(x,y,z+.02),r*.7,'Steel',16);cylinder('Hardware',(x,y,z+height),(x,y,z+height+.07),r*.55,'Copper',16)
def printed_plate(kind,c,w,h,key,normal,atlas,depth=.018,margin=0):
 """Solid plate with one printed front; no second cap beneath its artwork."""
 n,u,v=basis(normal);c=Vector(c);x0,y0,x1,y1=atlas['rects'][key];W,H=atlas['size']
 coords=[(x0/W,1-y1/H),(x1/W,1-y1/H),(x1/W,1-y0/H),(x0/W,1-y0/H)]
 ratio=(x1-x0)/(y1-y0);fw=min(w,h*ratio);fh=fw/ratio
 outer=[c+u*x*(w/2+margin)+v*y*(h/2+margin) for x,y in [(-1,-1),(1,-1),(1,1),(-1,1)]]
 inner=[c+u*x*fw/2+v*y*fh/2 for x,y in [(-1,-1),(1,-1),(1,1),(-1,1)]]
 back=[p-n*depth for p in outer]
 poly(kind,list(reversed(back)),[(0,1,2,3)],'Steel')
 for i in range(4):
  j=(i+1)%4
  poly(kind,[back[i],back[j],outer[j],outer[i]],[(0,1,2,3)],'Steel')
  if (outer[i]-inner[i]).cross(outer[j]-inner[i]).length>1.e-10:
   poly(kind,[outer[i],outer[j],inner[j],inner[i]],[(0,1,2,3)],'Steel')
 poly(kind,inner,[(0,1,2,3)],'Labels',[coords])

def plate(c,w,h,key,normal=(0,-1,0),atlas=None):
 n,u,v=basis(normal);c=Vector(c)
 printed_plate('Signs',c,w,h,key,normal,atlas)
 for dx in (-1,1):
  for dy in (-1,1):bolt('Hardware',c+u*dx*(w/2-.035)+v*dy*(h/2-.035),n,.006)
def tray(a,b,z,width=.48):
 a,b=Vector((a[0],a[1],z)),Vector((b[0],b[1],z));d=(b-a).normalized();s=Vector((-d.y,d.x,0));length=(b-a).length
 for sign in (-1,1):beam('Cablework',a+s*width/2*sign,b+s*width/2*sign,.045,.11,'Steel')
 for i in range(math.ceil(length/.42)+1):p=a+(b-a)*i/math.ceil(length/.42);beam('Cablework',p-s*width/2,p+s*width/2,.025,.035,'Steel')
 for j in (-1,0,1):tube('Cablework',[a+s*j*.10+Vector((0,0,.045)),b+s*j*.10+Vector((0,0,.045))],.033,'Rubber',10)
