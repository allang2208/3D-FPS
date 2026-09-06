# 3.2 m bind centreline -> 6.4 m; radius and grip size are unchanged.
WHIP_LENGTH=6.4
bpy.context.view_layer.objects.active=a;bpy.ops.object.mode_set(mode='EDIT')
start=Vector((-.87,-.025,1.10))
for i in range(33):
 b=a.data.edit_bones[f'whip.{i:02d}'];b.head=start+Vector((0,0,-i*.2));b.tail=b.head+Vector((0,0,-.2))
bpy.ops.object.mode_set(mode='OBJECT')
for v in whip.data.vertices:
 ring=v.index//8;v.co.z=start.z-ring*.2

def animate_long_whip(arm,grip,direction,t,clip,curve,ground_z=.025):
 points=[]
 for i in range(129):
  u=i/128;angle=u*math.tau*2.10
  # Two loose hanging loops store the extra length without sinking through the floor.
  coil=Vector((.39*math.sin(angle)*(1-.15*u),-.13*u-.11*math.sin(math.pi*u),-.46*(1-math.cos(angle))-.05*u))
  over=Vector((-.20*math.sin(math.pi*u),4.8*u,1.0*math.sin(math.pi*u)))
  crest=Vector((-.12*math.sin(math.pi*u),-2.8*u,3.4*math.sin(math.pi*u*.72)))
  contact=Vector((.05*math.sin(math.tau*u),-6.1*u,-.68*u))
  follow=Vector((.40*math.sin(math.pi*u),-5.2*u,-1.4*u))
  recoil=Vector((.80*math.sin(math.pi*u),-3.0*u,-1.0*u))
  off=coil
  if clip=='Attack':
   # Hand descends first. A crest travels forward, then the tip lashes downward.
   delayed=t-.10*u*max(0,min(1,(t-.68)/.20))
   off=curve(delayed,[(0,coil),(.40,over),(.49,crest),(.59625,contact),(.70,follow),(.96,recoil),(1.39,coil),(1.5,coil)])
   if .70<t<1.5:
    envelope=math.sin(math.pi*(t-.70)/.8)**2
    off+=Vector((.26*math.sin(12*(t-.70)-5*u),.14*math.sin(11*(t-.70)-5*u),.15*math.sin(13*(t-.70)-6*u)))*u*envelope
  if clip=='Death':
   settle=curve(t,[(0,0),(.62,0),(1.12,1),(1.4,1)])
   ground=Vector((.55*math.sin(angle),.48*(1-math.cos(angle))+.12*u,.055-grip.z))
   off=off.lerp(ground,settle)
  points.append(grip+off)
 # Fit the curve to one fixed physical length, enforcing a ground floor.
 for iteration in range(12):
  length=sum((q-p).length for p,q in zip(points,points[1:]));scale=WHIP_LENGTH/max(.001,length)
  points=[grip+(p-grip)*scale for p in points]
  for p in points:p.z=max(ground_z,p.z)
 # Equal arc-length resampling gives the 33 rigid ring bones even spacing.
 distances=[0.]
 for p,q in zip(points,points[1:]):distances.append(distances[-1]+(q-p).length)
 ring_points=[];cursor=0
 for i in range(33):
  distance=distances[-1]*i/32
  while cursor<127 and distances[cursor+1]<distance:cursor+=1
  f=(distance-distances[cursor])/max(1e-8,distances[cursor+1]-distances[cursor]);ring_points.append(points[cursor].lerp(points[cursor+1],f))
 normal=Vector((0,1,0))
 for i,p in enumerate(ring_points):
  tangent=(ring_points[min(32,i+1)]-ring_points[max(0,i-1)]).normalized();normal-=tangent*normal.dot(tangent)
  if normal.length<1e-5:normal=Vector((1,0,0))-tangent*tangent.x
  normal.normalize();z=normal.cross(tangent);m=Matrix((normal,tangent,z)).transposed().to_4x4();m.translation=p;arm.pose.bones[f'whip.{i:02d}'].matrix=m
