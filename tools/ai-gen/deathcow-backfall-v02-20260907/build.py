import bpy,math,json
from pathlib import Path
from mathutils import Vector,Matrix
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'deathcow-motion-v01-20260907/fat-zombie-motion-v01.blend'))
s=bpy.context.scene;s.render.fps=84
arm=next(o for o in s.objects if o.type=='ARMATURE');body=next(o for o in s.objects if o.type=='MESH')
for tr in arm.animation_data.nla_tracks:tr.mute=True
arm.animation_data.action=bpy.data.actions['Idle'];s.frame_set(0)
W=arm.matrix_world.copy();IW=W.inverted()
names={b.name.split(':')[-1].split('_')[0]:b.name for b in arm.pose.bones}
def bone(n):return arm.pose.bones[names[n]]
base={n:(W@bone(n).matrix).copy() for n in names}
heads={n:W@bone(n).head for n in names};tails={n:W@bone(n).tail for n in names}
basis={b.name:b.matrix_basis.copy() for b in arm.pose.bones}
arm.animation_data.action=None
def smooth(x):
 x=max(0,min(1,x));return x*x*(3-2*x)
def curve(t,ks):return herm(t,ks)
def setworld(n,m):bone(n).matrix=IW@m;bpy.context.view_layer.update()
def orient(n,h,t):
 q=(tails[n]-heads[n]).rotation_difference((t-h).normalized())
 m=q.to_matrix().to_4x4()@base[n];m.translation=h;setworld(n,m)
def solve(a,t,l1,l2,pole):
 v=t-a;d=max(.0001,min(v.length,l1+l2-.0005));u=v.normalized()
 k=(l1*l1-l2*l2+d*d)/(2*d);p=(pole-u*pole.dot(u)).normalized()
 return a+u*k+p*math.sqrt(max(0,l1*l1-k*k)),a+u*d
def herm(t,keys):
 # Continuous cubic tangents, not a full stop at every intermediate key.
 for i in range(len(keys)-1):
  a,x=keys[i];b,y=keys[i+1]
  if t<=b:
   u=max(0,(t-a)/(b-a));m0=0 if i==0 else (y-keys[i-1][1])/(b-keys[i-1][0]);m1=0 if i+2==len(keys) else (keys[i+2][1]-x)/(keys[i+2][0]-a)
   return (2*u**3-3*u*u+1)*x+(u**3-2*u*u+u)*(b-a)*m0+(-2*u**3+3*u*u)*y+(u**3-u*u)*(b-a)*m1
 return keys[-1][1]

action=bpy.data.actions.new('Death');action.use_fake_user=True;arm.animation_data.action=action
samples=[]
foot_vertices={}
for side in ['Left','Right']:
 ids={body.vertex_groups[names[side+k]].index for k in ['Foot','ToeBase']}
 foot_vertices[side]=[v.index for v in body.data.vertices if sum(g.weight for g in v.groups if g.group in ids)>.65]

for f in range(127):
 t=f/84
 for pb in arm.pose.bones:pb.matrix_basis=basis[pb.name].copy()
 bpy.context.view_layer.update()
 ang=curve(t,[(0,0),(.16,-.13),(.36,-.31),(.57,-.7),(.79,-1.65),(.94,-2.43),(1.05,-2.33),(1.22,-2.48),(1.5,-2.48)])
 y=curve(t,[(0,0),(.18,.025),(.38,.10),(.63,.24),(.91,.36),(1.5,.36)])
 z=curve(t,[(0,0),(.18,-.035),(.4,-.16),(.66,-.31),(.94,-.43),(1.07,-.408),(1.23,-.43),(1.5,-.43)])
 rot=Matrix.Rotation(ang,4,'X')@Matrix.Rotation(.045*smooth(t/.8),4,'Z')
 pivot=heads['Hips'];T=Matrix.Translation(pivot+Vector((.018*smooth(t/.9),y,z)))@rot@Matrix.Translation(-pivot)
 for n in ['Hips','Spine','Spine1','Spine2','Neck','Head']:
  setworld(n,T@base[n])
 # Late head motion around its own joint adds a short impact lag.
 h=bone('Head');m=(W@h.matrix).copy()
 lag=.06*math.sin(max(0,min(1,(t-.87)/.32))*math.pi)
 m=Matrix.Translation(m.translation)@Matrix.Rotation(lag,4,'X')@Matrix.Translation(-m.translation)@m
 setworld('Head',m)
 for side,sign,delay in [('Left',1,0),('Right',-1,.06)]:
  u=smooth((t-.38-delay)/.73)
  hip=T@heads[side+'UpLeg']
  target=heads[side+'Foot'].lerp(Vector((heads[side+'Foot'].x+sign*.08,-.31+(0 if sign==1 else .08),.10)),u)
  target.z+=.12*math.sin(math.pi*u)
  a=side+'UpLeg';b=side+'Leg'
  pole=Vector((sign*.18,-1+1.1*u,.05+1.5*u))
  knee,ankle=solve(hip,target,(tails[a]-heads[a]).length,(tails[b]-heads[b]).length,pole)
  orient(a,hip,knee);orient(b,knee,ankle)
  foot=side+'Foot';toe=side+'ToeBase'
  fr=Matrix.Rotation(-1.0*u,4,'X')
  fm=fr@base[foot];fm.translation=ankle;setworld(foot,fm)
  tm=fr@base[toe];tm.translation=ankle+fr.to_3x3()@(heads[toe]-heads[foot]);setworld(toe,tm)
  shoulder=side+'Shoulder';ua=side+'Arm';fa=side+'ForeArm';hand=side+'Hand'
  setworld(shoulder,T@base[shoulder]);sh=T@heads[ua]
  release=smooth((t-.12-delay)/.52);settle=smooth((t-.72-delay)/.52)
  natural=T@heads[hand]
  wide=sh+Vector((sign*.25,-.20,.035))
  final=sh+Vector((sign*.30,-.12,-.04))
  target=natural.lerp(wide,release).lerp(final,settle)
  elbow,wrist=solve(sh,target,(tails[ua]-heads[ua]).length,(tails[fa]-heads[fa]).length,Vector((sign,.15,-.35)))
  orient(ua,sh,elbow);orient(fa,elbow,wrist)
  direction=(T.to_3x3()@(tails[hand]-heads[hand])).lerp(Vector((sign*.09,-.07,-.025)),settle)
  orient(hand,wrist,wrist+direction)
 bpy.context.view_layer.update()
 ev=body.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh()
 low=min((ev.matrix_world@v.co).z for v in me.vertices);ev.to_mesh_clear()
 # Ground contact correction moves the skeleton, and is baked into the actual clip.
 correction=.005-low
 hm=(W@bone('Hips').matrix).copy();hm.translation.z+=correction;setworld('Hips',hm)

 # Settle the legs AFTER the torso ground correction, which previously lifted the feet.
 leg_report={}
 for side,sign,delay in [('Left',1,0),('Right',-1,.06)]:
  weight=smooth((t-.88-delay)/.48)
  if weight<=0:continue
  upper=side+'UpLeg';lower=side+'Leg';foot=side+'Foot';toe=side+'ToeBase'
  hip=(W@bone(upper).matrix).translation.copy()
  current=(W@bone(foot).matrix).translation.copy()
  l1=(tails[upper]-heads[upper]).length;l2=(tails[lower]-heads[lower]).length
  ev=body.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh()
  initial_heel=min((ev.matrix_world@me.vertices[i].co).z for i in foot_vertices[side]);ev.to_mesh_clear()
  desired_heel=initial_heel*(1-weight)+.008*weight
  target_z=.10
  # Near-extended knees, slightly splayed legs; heel height calibrated on skinned geometry.
  for iteration in range(3):
   dx=sign*.09
   dy=math.sqrt(max(.001,((l1+l2)*.975)**2-(hip.z-target_z)**2-dx*dx))
   resting=Vector((hip.x+dx,hip.y-dy,target_z))
   target=current.lerp(resting,weight)
   knee,ankle=solve(hip,target,l1,l2,Vector((sign*.35,-.1,1)))
   orient(upper,hip,knee);orient(lower,knee,ankle)
   fr=Matrix.Rotation(-1.0*smooth((t-.38-delay)/.73),4,'X')
   fm=fr@base[foot];fm.translation=ankle;setworld(foot,fm)
   tm=fr@base[toe];tm.translation=ankle+fr.to_3x3()@(heads[toe]-heads[foot]);setworld(toe,tm)
   ev=body.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh()
   heel=min((ev.matrix_world@me.vertices[i].co).z for i in foot_vertices[side]);ev.to_mesh_clear()
   if weight>.001:target_z+=(desired_heel-heel)/weight
  leg_report[side]={'heel_min_z':heel,'settle':weight}

 samples.append({'t':t,'ground_correction':correction,'legs':leg_report})
 for pb in arm.pose.bones:
  pb.rotation_mode='QUATERNION'
  for prop in ['location','rotation_quaternion','scale']:pb.keyframe_insert(prop,frame=f,group=pb.name)
for layer in action.layers:
 for strip in layer.strips:
  for bag in strip.channelbags:
   for fc in bag.fcurves:
    for k in fc.keyframe_points:k.interpolation='LINEAR'
arm.animation_data.action=None
tr=arm.animation_data.nla_tracks.new();tr.name='Death';tr.strips.new('Death',0,action)
for tr in arm.animation_data.nla_tracks:tr.mute=False
bpy.ops.object.select_all(action='DESELECT')
for o in s.objects:
 if o.type in {'MESH','ARMATURE'}:o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(P/'fat-zombie-backfall-v02.glb'),export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='NLA_TRACKS',export_frame_range=False,export_force_sampling=True)
for tr in arm.animation_data.nla_tracks:tr.mute=True
arm.animation_data.action=action;s.frame_set(126)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'fat-zombie-backfall-v02.blend'))
(P/'build-report.json').write_text(json.dumps(samples,indent=2))
print('BACKFALL_BUILD_COMPLETE')
