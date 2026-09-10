"""Use the existing Manny authoring rig's valid arm deformation as the base.
Carry each complete first-person arm to sparse, fitted contact transforms.
This preserves the authored wrist/twist relationship instead of re-solving
different-rig wrist axes. Shoulder roots are intentionally free viewmodel controls.
"""
import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion,Euler
O=Path(__file__).resolve().parent
clearance=json.loads((O/'release_path_clearance.json').read_text()) if (O/'release_path_clearance.json').exists() else {}
bpy.ops.wm.open_mainfile(filepath='D:/FPS3D/FPSGAME/SourceAssets/M4HK416Replica20260910/M4_HK416_Drum_Editable.blend')
r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
names=[b.name for b in r.pose.bones];parent={b.name:b.parent.name if b.parent else None for b in r.pose.bones};rest={b.name:b.bone.matrix_local.copy() for b in r.pose.bones}
lr={n:rest[parent[n]].inverted()@rest[n] if parent[n] else rest[n] for n in names}
def act(a):r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
def sample(a,f):
 act(a);s.frame_set(int(f),subframe=f-int(f));bpy.context.view_layer.update();return {b.name:b.matrix.copy() for b in r.pose.bones}
base=sample(bpy.data.actions['M4_idle'],0)
# Move the supporting palm forward along the handguard, clear of the magazine rim.
for n in names:
 if n.endswith('_l'):base[n].translation+=base['WPN_root'].to_3x3()@Vector((0,-.012,0))
grip=sample(bpy.data.actions['M4_reload'],80)
idlelocal={n:lr[n].inverted()@(base[parent[n]].inverted()@base[n] if parent[n] else base[n]) for n in names}
griplocal={n:lr[n].inverted()@(grip[parent[n]].inverted()@grip[n] if parent[n] else grip[n]) for n in names}
griprel=grip['WPN_SOCKET_Magazine'].inverted()@grip['hand_l']
release_griplocal={n:m.copy() for n,m in griplocal.items()}
fit=json.loads((O/'fitted_grip.json').read_text())
griprel.translation+=Vector(fit['shift'])
for n,q in fit['finger_local_rotations'].items():
 m=griplocal[n];griplocal[n]=Matrix.LocRotScale(m.translation,Quaternion(q),m.to_scale())
def smooth(x):x=max(0,min(1,x));return x*x*(3-2*x)
def win(t,a,b,c,d):return smooth((t-a)/(b-a))*(1-smooth((t-c)/(d-c)))
def mix(a,b,w):
 p,q,z=a.decompose();P,Q,Z=b.decompose();return Matrix.LocRotScale(p.lerp(P,w),q.slerp(Q,w),z.lerp(Z,w))
def interpolate(frames,keys,f,n):
 left=max(k for k in keys if k<=f);right=min(k for k in keys if k>=f)
 return mix(frames[left][n],frames[right][n],smooth((f-left)/max(1,right-left)))
handmesh=bpy.data.objects['SK_Manny_Arms_Export'];pads={}
for n in ['index_03_r','middle_03_r']:
 gi=handmesh.vertex_groups[n].index;points=[rest[n].inverted()@handmesh.matrix_world@v.co for v in handmesh.data.vertices if any(g.group==gi and g.weight>.8 for g in v.groups)];pads[n]=sum(points,Vector())/len(points)
# Preserve the previously visible empty-magazine throw; keep the repaired
# hand-contact and insertion phases independent from the departing magazine.
with bpy.data.libraries.load('D:/FPS3D/FPSGAME/SourceAssets/M4ContactImpact20260910/M4_Hand_MAT_Editable.blend',link=False) as (src,dst):dst.actions=['M4_MAT_reload_empty']
throw_action=dst.actions[0];throw_action.name='REFERENCE_empty_throw';throw=[sample(throw_action,f) for f in range(41)]
wrap=json.loads((O/'wrap_fit.json').read_text());griprel=Matrix(wrap['hand_magazine_matrix'])
for n,q in wrap['bone_local_rotations'].items():
 m=griplocal[n];griplocal[n]=Matrix.LocRotScale(idlelocal[n].translation,Quaternion(q),idlelocal[n].to_scale())
report={}
for clip in ['reload','reload_empty','equip_charge']:
 equip=clip=='equip_charge';empty=clip.endswith('empty');drum=clip.startswith('drum');end=38 if equip else 162 if empty else 126
 old=bpy.data.actions[('A_M4_HK416_' if drum else 'M4_HK416_')+clip]
 raw=[sample(old,f) for f in range(end+1)]
 if clip=='reload':
  # The inherited middle key spun the stock directly into the first-person
  # camera. Keep the rifle between its extraction and insertion orientations.
  target=mix(raw[29]['WPN_root'],raw[76]['WPN_root'],(54-29)/(76-29));delta=target@raw[54]['WPN_root'].inverted()
  raw[54]={n:delta@m for n,m in raw[54].items()}

 # Rebuild magazine travel in rifle space. Entry and seating are distinct,
 # monotonic phases; the same visible magazine is reset only below the view.
 magrest=base['WPN_root'].inverted()@base['WPN_SOCKET_Magazine']
 if not equip:
  mk=[(0,(0,0,0),0),(25,(0,0,0),0),(29,(0,0,-.020),0),(36,(0,0,-.19),0),(45,(.06,.03,-.48),12),(55,(.07,.035,-.48),12),(68,(.025,.01,-.18),8),(76,(0,0,-.070),0),(90,(0,0,-.012),0),(95,(0,0,0),0),(126,(0,0,0),0)] if not empty else [(0,(0,0,0),0),(20,(0,0,0),0),(21,(0,0,-.015),0),(29,(.01,0,-.60),0),(35,(.06,.025,-.48),10),(44,(.03,.008,-.23),6),(54,(0,0,-.070),0),(74,(0,0,-.008),0),(80,(0,0,0),0),(162,(0,0,0),0)]
  for f,p in enumerate(raw):
   k=next(i for i in range(len(mk)-1) if mk[i][0]<=f<=mk[i+1][0]);a,apos,ang=mk[k];b,bpos,bng=mk[k+1];u=smooth((f-a)/(b-a))
   m=magrest.copy();m.translation+=Vector(apos).lerp(Vector(bpos),u)
   m=Matrix.LocRotScale(m.translation,Quaternion(Vector((0,1,0)),math.radians(ang+(bng-ang)*u))@m.to_quaternion(),m.to_scale())
   p['WPN_SOCKET_Magazine']=p['WPN_root']@m
   if empty:
    bolt=base['WPN_root'].inverted()@base['WPN_bolt'];bolt.translation.y+=.035*(1-smooth((f-130)/2))
    p['WPN_bolt']=p['WPN_root']@bolt
    catch=base['WPN_root'].inverted()@base['WPN_BoltCatch']
    catch=Matrix.LocRotScale(catch.translation,Quaternion(Vector((0,1,0)),math.radians(10)*(1-smooth((f-130)/.75)))@catch.to_quaternion(),catch.to_scale())
    p['WPN_BoltCatch']=p['WPN_root']@catch

 authored=bpy.data.actions['M4_equip' if equip else 'M4_reload']
 poses=[sample(authored,f/end*(62 if equip else 188)) for f in range(end+1)]
 keys=[0,9,15,18,22,30,end] if equip else ([0,12,21,40,54,80,100,115,130,142,end] if empty else [0,15,29,54,76,95,113,end])
 release=raw[min(130,end)]['WPN_root'].inverted()@raw[min(130,end)]['hand_l']
 out=[]
 for f in range(end+1):
  p={n:m.copy() for n,m in raw[f].items()};t=f/60
  root=interpolate(raw,keys,f,'WPN_root');delta=root@p['WPN_root'].inverted()
  for n in names:p[n]=delta@p[n]
  root=p['WPN_root']
  if empty and f<=40:
   original=root.copy();root=throw[f]['WPN_root'] if f<=33 else mix(throw[f]['WPN_root'],root,smooth((f-33)/7));delta=root@original.inverted()
   for n in names:p[n]=delta@p[n]
   p['WPN_SOCKET_Magazine']=throw[f]['WPN_SOCKET_Magazine'].copy() if f<=35 else mix(throw[f]['WPN_SOCKET_Magazine'],p['WPN_SOCKET_Magazine'],smooth((f-35)/5))
  for side in ['l','r']:
   hn='hand_'+side;held=root@base['WPN_root'].inverted()@base[hn]
   w=0;releasew=0
   if (equip and side=='l') or (not equip and side=='r'):target=held
   else:
    target=interpolate(raw,keys,f,hn)
    if equip:
     # Express the sparse hook in the correspondingly smoothed rifle space.
     left=max(k for k in keys if k<=f);right=min(k for k in keys if k>=f)
     target=root@mix(raw[left]['WPN_root'].inverted()@raw[left][hn],raw[right]['WPN_root'].inverted()@raw[right][hn],smooth((f-left)/max(1,right-left)))
    else:
     w=win(t,.42,.72,1.48,1.72) if empty else win(t,.05,.38,1.68,1.91)
     grasp=p['WPN_SOCKET_Magazine']@griprel;target.translation=target.translation.lerp(grasp.translation,w)
     q=held.to_quaternion().slerp(grasp.to_quaternion(),w)
     releasew=win(t,1.82,2.07,2.24,2.55) if empty else 0
     q=q.slerp((root@release).to_quaternion(),releasew);target=Matrix.LocRotScale(target.translation,q,target.to_scale())
   reference=base if equip or side=='r' else poses[f]
   delta=target@reference[hn].inverted()
   for n in names:
    if n.endswith('_'+side):p[n]=delta@reference[n]
   for digit in ['thumb','index','middle','ring','pinky']:
    meta=digit+'_metacarpal_'+side
    if meta in p:p[meta]=p[hn]@lr[meta]@(mix(idlelocal[meta],griplocal[meta],w) if side=='l' and not equip else idlelocal[meta])
    for j in [1,2,3]:
     n=f'{digit}_{j:02}_{side}';q=idlelocal[n].to_quaternion()
     if side=='l' and not equip:
      q=q.slerp(griplocal[n].to_quaternion(),w)
      if digit!='thumb':
       e=release_griplocal[n].to_euler();e.x=math.radians(max(-12,min(12,math.degrees(e.x)))) if j==1 else 0;e.y=math.radians(max(-14,min(14,math.degrees(e.y)))) if j==1 else 0;e.z=math.radians([48,72,38][j-1]);q=q.slerp(e.to_quaternion(),releasew)
      else:
       e=idlelocal[n].to_euler();e.z=math.radians([25,5,22][j-1]);q=q.slerp(e.to_quaternion(),releasew)
     if side=='r' and not equip and digit=='index' and j>1:q=q.slerp(Quaternion(Vector((0,0,1)),math.radians(60 if j==2 else 20)),win(t,0,.15,end/60-.15,end/60))
     if side=='r' and equip:
      e=idlelocal[n].to_euler()
      if digit in ['index','middle']:e=Euler((0,math.radians(2 if digit=='index' else -2),math.radians([12,65,32][j-1])))
      elif digit!='thumb':e=Euler((0,0,math.radians([55,80,35][j-1])))
      else:e.z=math.radians([20,10,35][j-1])
      q=q.slerp(e.to_quaternion(),win(t,.03,.13,.36,.60))
     p[n]=p[parent[n]]@lr[n]@Matrix.LocRotScale(idlelocal[n].translation,q,idlelocal[n].to_scale())
   if side=='r' and equip:
    travel=(root.inverted()@p['WPN_ChargingHandle']).translation.y-.01;goal=root@Vector((-.005,.024+travel,.105));pad=sum((p[n]@v for n,v in pads.items()),Vector())/2;shift=(goal-pad)*win(t,.08,.20,.316667,.43)
    for n in names:
     if n.endswith('_r'):p[n].translation+=shift
   if side=='l' and empty:
    weight=win(t,1.95,2.15,2.20,2.40);turn=Quaternion().slerp(Euler((0,math.radians(-5),math.radians(-15))).to_quaternion(),weight);turn=root.to_quaternion()@turn@root.to_quaternion().inverted();pivot=p[hn].translation.copy();shift=root.to_3x3()@Vector((.013113424,-.014230929,.005153637))*weight
    for n in names:
     if n.endswith('_l'):p[n]=Matrix.LocRotScale(pivot+turn@(p[n].translation-pivot)+shift,turn@p[n].to_quaternion(),p[n].to_scale())
    push=clearance.get(str(f),0)
    for n in names:
     if n.endswith('_l'):p[n].translation+=root.to_3x3()@Vector((push,0,0))
  out.append(p)
 # Rebuild the post-seat path in weapon space: withdraw outside the magazine
 # before changing grip orientation. The previous direct return passed through it.
 if not equip:
  initial=[{n:m.copy() for n,m in p.items()} for p in out]
  holdframe=88 if empty else 98
  handrel=lambda f: initial[f]['WPN_root'].inverted()@initial[f]['hand_l']
  escape=(initial[holdframe]['WPN_root'].inverted()@initial[holdframe]['WPN_SOCKET_Magazine']).to_3x3()@Vector((0,-.050,0))
  grasp=handrel(holdframe);held=base['WPN_root'].inverted()@base['hand_l'];contact=handrel(130) if empty else held
  def shifted(m,v):
   q=m.copy();q.translation+=Vector(v);return q
  if empty:
   contact.translation.x+=.0005
   anchors=[(88,grasp),(95,shifted(grasp,escape)),(101,shifted(grasp,escape+Vector((.100,0,0)))),
            (111,shifted(contact,(.125,-.025,.010))),
            (125,shifted(contact,(.120,-.018,.035))),
            (127,shifted(contact,(.092,-.014,.025))),
            (130,contact),(131,contact),
            (135,shifted(contact,(.065,0,.025))),
            (143,shifted(held,(.085,0,.020))),
            (154,shifted(held,(.035,0,0))),(162,held)]
  else:
   anchors=[(98,grasp),(104,shifted(grasp,escape)),
            (110,shifted(grasp,escape+Vector((.100,0,0)))),
            (119,shifted(held,(.085,0,0))),
            (123,shifted(held,(.045,0,0))),(126,held)]
  fingerframes=[(88,88),(95,88),(111,130),(135,130),(151,162),(162,162)] if empty else [(98,98),(104,98),(118,126),(126,126)]
  # Approach the magazine from below its base, then lift into the fitted grasp.
  entryend=44 if empty else 23;entrystart=0
  entrygrasp=handrel(entryend);entryescape=(initial[entryend]['WPN_root'].inverted()@initial[entryend]['WPN_SOCKET_Magazine']).to_3x3()@Vector((0,-.080,0))
  if empty:
   low=held.copy();low.translation=Vector((.30,.06,-.65))
   entryanchors=[(0,held),(6,shifted(held,(.085,0,-.035))),(19,low),(28,low),(35,shifted(entrygrasp,entryescape+Vector((.085,0,0)))),(39,shifted(entrygrasp,entryescape)),(43,entrygrasp),(44,entrygrasp)]
  else:
   entryanchors=[(0,held),(6,shifted(held,(.085,0,0))),(12,shifted(entrygrasp,entryescape+Vector((.085,0,0)))),(18,shifted(entrygrasp,entryescape)),(23,entrygrasp)]
  for f in range(entrystart,entryend+1):
   k=next(i for i in range(len(entryanchors)-1) if entryanchors[i][0]<=f<=entryanchors[i+1][0]);a,A=entryanchors[k];b,B=entryanchors[k+1];u=smooth((f-a)/(b-a));root=initial[f]['WPN_root'];target=root@mix(A,B,u);delta=target@initial[f]['hand_l'].inverted()
   if empty and 6<=f<=35:
    lowworld=Vector((-.35,.20,-.95));startworld=initial[6]['WPN_root']@shifted(held,(.085,0,-.035));target.translation=startworld.translation.lerp(lowworld,smooth((f-6)/13));delta=target@initial[f]['hand_l'].inverted()
   if empty and f>=35:
    # Follow the moving new magazine while approaching from below its base.
    dynamic=initial[f]['WPN_root'].inverted()@initial[f]['WPN_SOCKET_Magazine']@griprel
    below=(initial[f]['WPN_root'].inverted()@initial[f]['WPN_SOCKET_Magazine']).to_3x3()@Vector((0,-.050,0))
    goal=shifted(dynamic,below*(1-smooth((f-39)/4))+Vector((.12*(1-smooth((f-35)/4)),0,0)))
    target=initial[f]['WPN_root']@goal;target.translation=Vector((-.35,.20,-.95)).lerp(target.translation,smooth((f-35)/4))
    delta=target@initial[f]['hand_l'].inverted()
   for n in names:
    if n.endswith('_l'):out[f][n]=delta@initial[f][n]
   u=smooth((f-35)/4) if empty else smooth((f-entrystart)/max(1,entryend-entrystart-5))
   for n in names:
    if n.endswith('_l') and n.startswith(('thumb','index','middle','ring','pinky')):
     finger_u=smooth((f-entryend+4)/4) if n.startswith('thumb') else u
     m=mix(initial[entrystart][parent[n]].inverted()@initial[entrystart][n],initial[entryend][parent[n]].inverted()@initial[entryend][n],finger_u);out[f][n]=out[f][parent[n]]@m
  for f in range(holdframe,end+1):
   k=next(i for i in range(len(anchors)-1) if anchors[i][0]<=f<=anchors[i+1][0]);a,A=anchors[k];b,B=anchors[k+1];u=(f-a)/(b-a)
   # Constant-speed final swing followed by a one-frame arrest, no ease-in at impact.
   u=u if empty and 125<=f<=130 else smooth(u)
   root=initial[f]['WPN_root'];target=root@mix(A,B,u);delta=target@initial[f]['hand_l'].inverted()
   for n in names:
    if n.endswith('_l'):out[f][n]=delta@initial[f][n]
   k=next(i for i in range(len(fingerframes)-1) if fingerframes[i][0]<=f<=fingerframes[i+1][0]);a,A=fingerframes[k];b,B=fingerframes[k+1];u=smooth((f-a)/(b-a))
   for n in names:
    if n.endswith('_l') and n.startswith(('thumb','index','middle','ring','pinky')):
     m=mix(initial[A][parent[n]].inverted()@initial[A][n],initial[B][parent[n]].inverted()@initial[B][n],u)
     out[f][n]=out[f][parent[n]]@m
   if empty:
    recoil=win(f,130,131,132,141)
    response=root@Matrix.Translation((-.008*recoil,0,-.002*recoil))@Quaternion(Vector((0,1,0)),math.radians(3.5)*recoil).to_matrix().to_4x4()@root.inverted()
    for n in names:out[f][n]=response@out[f][n]
 # Full wrap: loosen the middle joints before withdrawing through the palm side.
 # The approach reverses the same mesh-tested contact path.
 if not equip:
  openlocal={n:m.copy() for n,m in griplocal.items()}
  for n,q in json.loads((O/'open_grip_fit.json').read_text())['rotations'].items():
   m=openlocal[n];openlocal[n]=Matrix.LocRotScale(m.translation,Quaternion(q),m.to_scale())
  previous=[{n:m.copy() for n,m in p.items()} for p in out]
  def hand_target(f,target):
   delta=target@previous[f]['hand_l'].inverted()
   for n in names:
    if n.endswith('_l'):out[f][n]=delta@previous[f][n]
  def fingers(f,A,B,w):
   for n in names:
    if n.endswith('_l') and n.startswith(('thumb','index','middle','ring','pinky')):
     out[f][n]=out[f][parent[n]]@lr[n]@mix(A[n],B[n],w)
  def grasp_target(f,u):
   target=out[f]['WPN_SOCKET_Magazine']@griprel
   target.translation+=out[f]['WPN_SOCKET_Magazine'].to_3x3()@Vector((.085*u,0,0))
   return target
  start,finish=(38,43) if empty else (12,23)
  # Retain the low, off-screen retrieval while the old magazine flies away.
  for f in range(start):
   u=smooth(f/6) if empty else smooth(f/12)
   fingers(f,idlelocal,openlocal,u)
   if not empty:
    held=out[f]['WPN_root']@base['WPN_root'].inverted()@base['hand_l'];outer=held.copy();outer.translation+=out[f]['WPN_root'].to_3x3()@Vector((.085,0,0))
    target=mix(held,outer,smooth(f/6)) if f<=6 else mix(outer,grasp_target(f,1),smooth((f-6)/6));hand_target(f,target);fingers(f,idlelocal,openlocal,u)
   elif f>=35:
    target=grasp_target(f,1);target.translation=Vector((-.35,.20,-.95)).lerp(target.translation,smooth((f-35)/3));target.translation+=out[f]['WPN_SOCKET_Magazine'].to_3x3()@Vector((.03*win(f,35,36,37,38),0,0));hand_target(f,target);fingers(f,openlocal,openlocal,0)
  for f in range(start,finish+1):
   u=1-smooth((f-start)/(finish-start));hand_target(f,grasp_target(f,u));fingers(f,griplocal,openlocal,max(0,min(1,(u-.2)/.6)))
  hold=88 if empty else 98
  for f in range(finish,hold+1):
   hand_target(f,grasp_target(f,0));fingers(f,griplocal,griplocal,0)
  released=101 if empty else 110;rejoin=111 if empty else 119
  for f in range(hold,released+1):
   u=smooth((f-hold)/(released-hold));hand_target(f,grasp_target(f,u));fingers(f,griplocal,openlocal,max(0,min(1,(u-.2)/.6)))
  rel=out[released]['WPN_root'].inverted()@out[released]['hand_l'];endrel=previous[rejoin]['WPN_root'].inverted()@previous[rejoin]['hand_l']
  endlocal={n:lr[n].inverted()@(previous[rejoin][parent[n]].inverted()@previous[rejoin][n] if parent[n] else previous[rejoin][n]) for n in names}
  for f in range(released+1,rejoin+1):
   u=smooth((f-released)/(rejoin-released));hand_target(f,out[f]['WPN_root']@mix(rel,endrel,u));fingers(f,openlocal,endlocal,u)
 if equip:
  initial=[{n:m.copy() for n,m in p.items()} for p in out]
  held=base['WPN_root'].inverted()@base['hand_r']
  hook=initial[18]['WPN_root'].inverted()@initial[18]['hand_r'];hook.translation+=Vector((-.036,-.006,0))
  hookrel=(initial[18]['WPN_root'].inverted()@initial[18]['WPN_ChargingHandle']).inverted()@hook
  def shifted(m,v):q=m.copy();q.translation+=Vector(v);return q
  contact=lambda f:initial[f]['WPN_root'].inverted()@initial[f]['WPN_ChargingHandle']@hookrel
  anchors=[(0,held),(3,shifted(held,(-.060,0,0))),(7,shifted(contact(12),(-.070,.025,.045))),(12,contact(12)),(19,contact(19)),(22,shifted(contact(19),(-.065,.025,.045))),(27,shifted(held,(-.090,.01,.020))),(33,shifted(held,(-.045,0,0))),(38,held)]
  for f in range(end+1):
   if 12<=f<=19:goal=contact(f)
   else:
    k=next(i for i in range(len(anchors)-1) if anchors[i][0]<=f<=anchors[i+1][0]);a,A=anchors[k];b,B=anchors[k+1];goal=mix(A,B,smooth((f-a)/(b-a)))
   target=initial[f]['WPN_root']@goal;delta=target@initial[f]['hand_r'].inverted()
   for n in names:
    if n.endswith('_r'):out[f][n]=delta@initial[f][n]
   blend=win(f,3,10,22,33)
   for n in names:
    if n.endswith('_r') and n.startswith(('thumb','index','middle','ring','pinky')):
     m=mix(initial[0][parent[n]].inverted()@initial[0][n],initial[18][parent[n]].inverted()@initial[18][n],blend)
     if n=='thumb_01_r':
      b=lr[n].inverted()@m;m=lr[n]@Matrix.LocRotScale(b.translation,b.to_quaternion()@Quaternion(Vector((0,1,0)),math.radians(-5)*blend),b.to_scale())
     out[f][n]=out[f][parent[n]]@m
 # Bake at 480 Hz with an exact magazine-space grasp constraint. Sampling
 # only integer 60 Hz poses allowed the arm chain and magazine to interpolate
 # along different arcs, causing millimetres of slip between otherwise valid keys.
 localposes=[{n:p[parent[n]].inverted()@p[n] if parent[n] else p[n] for n in names} for p in out]
 dense=[]
 for k in range(end*8+1):
  f=k/8;i=int(f);j=min(end,i+1);p={}
  for n in names:p[n]=(p[parent[n]] if parent[n] else Matrix.Identity(4))@mix(localposes[i][n],localposes[j][n],f-i)
  # Independently interpolated arm chains previously drifted up to 17 mm
  # between 60 Hz anchors. Reconstruct wrist trajectories in rifle space.
  root=p['WPN_root'];ri=out[i]['WPN_root'].inverted();rj=out[j]['WPN_root'].inverted()
  for n in names:
   if n.startswith('WPN_') and n!='WPN_root':p[n]=root@mix(ri@out[i][n],rj@out[j][n],f-i)
  for side in ['l','r']:
   hn='hand_'+side
   goal=root@mix(ri@out[i][hn],rj@out[j][hn],f-i)
   if (equip and side=='l') or (not equip and side=='r'):goal=root@base['WPN_root'].inverted()@base[hn]
   if equip and side=='r' and 12<=f<=19:goal=p['WPN_ChargingHandle']@hookrel
   delta=goal@p[hn].inverted()
   for n in names:
    if n.endswith('_'+side):p[n]=delta@p[n]
  if not equip and ((43<=f<=88) if empty else (23<=f<=98)):
   goal=p['WPN_SOCKET_Magazine']@griprel;delta=goal@p['hand_l'].inverted()
   for n in names:
    if n.endswith('_l'):p[n]=delta@p[n]
  dense.append(p)
 a=bpy.data.actions.new('M4_MAT_'+clip);a.use_fake_user=True;r.animation_data.action=a;previous={}
 for k,p in enumerate(dense):
  f=k/8
  for n in names:
   local=lr[n].inverted()@(p[parent[n]].inverted()@p[n] if parent[n] else p[n]);loc,q,z=local.decompose()
   if n in previous and previous[n].dot(q)<0:q.negate()
   previous[n]=q.copy();b=r.pose.bones[n];b.rotation_mode='QUATERNION';b.location=loc;b.rotation_quaternion=q;b.scale=z
   for prop in ['location','rotation_quaternion','scale']:b.keyframe_insert(prop,frame=f)
 for layer in a.layers:
  for strip in layer.strips:
   for bag in strip.channelbags:
    for curve in bag.fcurves:
     for k in curve.keyframe_points:k.interpolation='LINEAR'
 s.render.fps=60;s.frame_start=0;s.frame_end=end;bpy.ops.object.select_all(action='DESELECT');r.select_set(True);bpy.context.view_layer.objects.active=r
 bpy.ops.export_scene.fbx(filepath=str(O/f'A_M4_MAT_{clip}.fbx'),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_step=.125,bake_anim_simplify_factor=0)
 report[clip]={'duration':end/60,'keys':len(dense),'sample_rate':480,'arm_deformation_source':authored.name,'viewmodel_shoulder_controls':'free in camera space'}
sample(bpy.data.actions['M4_MAT_reload_empty'],130);bpy.ops.wm.save_as_mainfile(filepath=str(O/'M4_Hand_MAT_Editable.blend'));(O/'repair_report.json').write_text(json.dumps(report,indent=2));print('AUTHORED_REPAIR_DONE')
