"""Repair Manny deformation in rejected retarget. Preserve weapon tracks/timing.
Editable source and FBX are candidates until rendered/imported verification.
"""
import bpy,math,json
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion,Euler
O=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath='D:/FPS3D/FPSGAME/SourceAssets/M4HK416Replica20260910/M4_HK416_Drum_Editable.blend')
r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
names=[b.name for b in r.pose.bones];parents={b.name:b.parent.name if b.parent else None for b in r.pose.bones};rest={b.name:b.bone.matrix_local.copy() for b in r.pose.bones}
lr={n:rest[parents[n]].inverted()@rest[n] if parents[n] else rest[n] for n in names}
def action(a):
 r.animation_data_create();r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
def frame(f):s.frame_set(int(f),subframe=f-int(f));bpy.context.view_layer.update()
action(bpy.data.actions['M4_idle']);frame(0)
base={b.name:b.matrix.copy() for b in r.pose.bones};idle={b.name:b.matrix_basis.copy() for b in r.pose.bones}
action(bpy.data.actions['M4_reload']);frame(80)
grip={b.name:b.matrix_basis.copy() for b in r.pose.bones}
armref={b.name:b.matrix.copy() for b in r.pose.bones}
grip_hand_rel=r.pose.bones['WPN_SOCKET_Magazine'].matrix.inverted()@r.pose.bones['hand_l'].matrix
def smooth(x):
 x=max(0,min(1,x));return x*x*(3-2*x)
def win(t,a,b,c,d):return smooth((t-a)/(b-a))*(1-smooth((t-c)/(d-c)))
def plane(a,b,c,previous=None):
 x=(b-a).normalized();z=x.cross(c-b).normalized()
 if previous is not None and z.dot(previous@Vector((0,0,1)))<0:z=-z
 y=z.cross(x).normalized();return Matrix((x,y,z)).transposed().to_quaternion()
baseplanes={side:plane(*[armref[n+'_'+side].translation for n in ['upperarm','lowerarm','hand']]) for side in ['l','r']}
handmesh=bpy.data.objects['SK_Manny_Arms_Export'];pads={}
for n in ['index_03_r','middle_03_r']:
 group=handmesh.vertex_groups[n].index
 points=[rest[n].inverted()@handmesh.matrix_world@v.co for v in handmesh.data.vertices if any(g.group==group and g.weight>.8 for g in v.groups)]
 pads[n]=sum(points,Vector())/len(points)
def move_hand(p,side,shift,turn):
 un='upperarm_'+side;fn='lowerarm_'+side;hn='hand_'+side
 a,b,c=[p[n].translation.copy() for n in [un,fn,hn]];l1=(b-a).length;l2=(c-b).length
 for n in names:
  if n==hn or n.endswith('_'+side) and n.startswith(('thumb','index','middle','ring','pinky')):
   p[n]=Matrix.LocRotScale(c+turn@(p[n].translation-c)+shift,turn@p[n].to_quaternion(),p[n].to_scale())
 goal=p[hn].translation;axis=(goal-a).normalized();dist=(goal-a).length
 reach=math.sqrt(l1*l1+l2*l2+2*l1*l2*math.cos(math.radians(15)))
 if dist>reach:a+=axis*(dist-reach);dist=(goal-a).length
 pole=Vector((-.25 if side=='l' else .25,0,-1));pole-=axis*pole.dot(axis);pole.normalize();along=(l1*l1-l2*l2+dist*dist)/(2*dist);elbow=a+axis*along+pole*math.sqrt(max(0,l1*l1-along*along))
 stable=plane(a,elbow,goal);planehistory[side]=stable
 delta=stable@baseplanes[side].inverted();uq=delta@armref[un].to_quaternion();fq=delta@armref[fn].to_quaternion()
 direction=armref[fn].to_quaternion().inverted()@(armref[hn].translation-armref[fn].translation);fq=(fq@direction).rotation_difference(goal-elbow)@fq
 p[un]=Matrix.LocRotScale(a,uq,p[un].to_scale());p[fn]=Matrix.LocRotScale(elbow,fq,p[fn].to_scale())
 roll=(lr[hn].inverted()@p[fn].inverted()@p[hn]).to_quaternion().to_swing_twist('X')[1]
 while roll-rollhistory[side]>math.pi:roll-=2*math.pi
 while roll-rollhistory[side]<-math.pi:roll+=2*math.pi
 rollhistory[side]=roll
 for n in names:
  if n.startswith(('upperarm_twist','lowerarm_twist')) and n.endswith('_'+side):
   basis=idle[n].copy()
   if n.startswith('lowerarm_twist'):basis=Matrix.LocRotScale(basis.translation,Quaternion(Vector((1,0,0)),roll*(.5 if '_02_' in n else 1)),basis.to_scale())
   p[n]=p[parents[n]]@lr[n]@basis
report={'method':'Manny authored local grasp poses, anatomical hinge curls, elbow-plane solve and distributed wrist roll','clips':{}}
for clip in ['reload','reload_empty','equip_charge','drum_reload','drum_reload_empty']:
 an=('A_M4_HK416_' if clip.startswith('drum') else 'M4_HK416_')+clip
 old=bpy.data.actions[an];action(old);end=round(old.frame_range[1]);samples=[];oldlocal=[]
 for f in range(end+1):
  frame(f);samples.append({b.name:b.matrix.copy() for b in r.pose.bones});oldlocal.append({b.name:b.matrix_basis.copy() for b in r.pose.bones})
 final=[];fingermax=0;twistmismatch=0;planehistory={side:baseplanes[side].copy() for side in ['l','r']};rollhistory={side:idle['hand_'+side].to_quaternion().to_swing_twist('X')[1] for side in ['l','r']}
 # Rebuild sparse, meaningful wrist poses. The captured reference includes
 # transition spikes (132 and 146 degrees on consecutive equip frames) and
 # must not be copied as dense orientation keys onto the different rig.
 landmarks=[0,9,15,18,22,30,end] if clip=='equip_charge' else ([0,12,21,40,54,80,100,115,130,142,end] if clip.endswith('empty') else [0,15,29,54,76,95,113,end])
 anchors={f:{n:samples[f][n].copy() for n in ['hand_l','hand_r']} for f in landmarks}
 release_rel=samples[min(130,end)]['WPN_root'].inverted()@samples[min(130,end)]['hand_l']
 for f,p in enumerate(samples):
  t=f/60;empty=clip.endswith('empty');equip=clip=='equip_charge';drum=clip.startswith('drum')
  for side in ['l','r']:
   un='upperarm_'+side;fn='lowerarm_'+side;hn='hand_'+side
   root=p['WPN_root'];held=root@base['WPN_root'].inverted()@base[hn]
   # Retain a stable support/trigger hand on the rifle throughout its action.
   if (equip and side=='l') or (not equip and side=='r'):
    target=held
   else:
    left=max(x for x in landmarks if x<=f);right=min(x for x in landmarks if x>=f);alpha=smooth((f-left)/max(1,right-left));l=anchors[left][hn];v=anchors[right][hn]
    target=Matrix.LocRotScale(l.translation.lerp(v.translation,alpha),l.to_quaternion().slerp(v.to_quaternion(),alpha),l.to_scale())
    if not equip:
     weight=win(t,.42,.72,1.33,1.63) if empty else win(t,.05,.38,1.58,1.88)
     grasp=p['WPN_SOCKET_Magazine']@grip_hand_rel
     target.translation=target.translation.lerp(grasp.translation,weight)
     q=held.to_quaternion().slerp(grasp.to_quaternion(),weight)
     if empty:q=q.slerp((root@release_rel).to_quaternion(),win(t,1.82,2.07,2.24,2.55))
     target=Matrix.LocRotScale(target.translation,q,target.to_scale())
   p[hn]=target
   # Re-solve elbow position for the repaired wrist, without changing bone lengths.
   shoulder=base[un].translation.copy();wrist=target.translation
   hint=base[fn].translation+(wrist-base[hn].translation)*.25
   l1=(base[fn].translation-base[un].translation).length;l2=(base[hn].translation-base[fn].translation).length
   axis=(wrist-shoulder).normalized();dist=(wrist-shoulder).length
   reach=math.sqrt(l1*l1+l2*l2+2*l1*l2*math.cos(math.radians(15)))
   if dist>reach:shoulder+=axis*(dist-reach);dist=(wrist-shoulder).length
   pole=Vector((-.25 if side=='l' else .25,0,-1));pole-=axis*pole.dot(axis);pole.normalize();along=(l1*l1-l2*l2+dist*dist)/(2*dist)
   p[un].translation=shoulder;p[fn].translation=shoulder+axis*along+pole*math.sqrt(max(0,l1*l1-along*along))
   # Use the elbow bending plane instead of the source rig's arbitrary bone roll.
   a,b,c=[p[n].translation.copy() for n in [un,fn,hn]]
   stable=plane(a,b,c);planehistory[side]=stable
   delta=stable@baseplanes[side].inverted()
   uq=delta@armref[un].to_quaternion()
   fq=delta@armref[fn].to_quaternion()
   direction=armref[fn].to_quaternion().inverted()@(armref[hn].translation-armref[fn].translation)
   fq=(fq@direction).rotation_difference(c-b)@fq
   p[un]=Matrix.LocRotScale(a,uq,p[un].to_scale());p[fn]=Matrix.LocRotScale(b,fq,p[fn].to_scale())
   # Manny forearm roll is around local X. Original rig distributes half/full
   # wrist roll to twist_02 / twist_01. The former retarget froze both at idle.
   handbasis=lr[hn].inverted()@p[fn].inverted()@p[hn]
   roll=handbasis.to_quaternion().to_swing_twist('X')[1]
   while roll-rollhistory[side]>math.pi:roll-=2*math.pi
   while roll-rollhistory[side]<-math.pi:roll+=2*math.pi
   rollhistory[side]=roll
   for n in names:
    if n.startswith(('upperarm_twist','lowerarm_twist')) and n.endswith('_'+side):
     basis=idle[n].copy()
     if n.startswith('lowerarm_twist'):
      factor=.5 if '_02_' in n else 1.0
      basis=Matrix.LocRotScale(basis.translation,Quaternion(Vector((1,0,0)),roll*factor),basis.to_scale())
     p[n]=p[parents[n]]@lr[n]@basis
   for digit in ['thumb','index','middle','ring','pinky']:
    meta=digit+'_metacarpal_'+side
    if meta in p:p[meta]=p[hn]@lr[meta]@idle[meta]
    for j in range(1,4):
     n=f'{digit}_{j:02}_{side}';q=idle[n].to_quaternion()
     if side=='l' and not equip:
      # Keep the thumb's authored opposition and palm spread. Pull/insertion
      # use the original valid M4 magazine grasp, with matched HK416 phases.
      w=win(t,.05,.28,1.55 if empty else 1.60,1.91 if empty else 2.04)
      q=q.slerp(grip[n].to_quaternion(),w)
      release=win(t,1.82,2.07,2.24,2.55) if empty else 0
      if digit!='thumb':
       e=grip[n].to_euler();e.x=math.radians(max(-12,min(12,math.degrees(e.x)))) if j==1 else 0;e.y=math.radians(max(-14,min(14,math.degrees(e.y)))) if j==1 else 0;e.z=math.radians([48,72,38][j-1])
       q=q.slerp(e.to_quaternion(),release)
      else:
       e=idle[n].to_euler();e.z=math.radians([25,5,22][j-1]);q=q.slerp(e.to_quaternion(),release)
     elif side=='r' and not equip and digit=='index' and j>1:
      q=q.slerp(Quaternion(Vector((0,0,1)),math.radians(60 if j==2 else 20)),win(t,0,.15,end/60-.15,end/60))
     elif side=='r' and equip:
      weight=win(t,.03,.13,.36,.60)
      e=idle[n].to_euler()
      if digit in ['index','middle']:e=Euler((0,math.radians(2 if digit=='index' else -2),math.radians([12,65,32][j-1])))
      elif digit!='thumb':e=Euler((0,0,math.radians([55,80,35][j-1])))
      else:e.z=math.radians([20,10,35][j-1])
      q=q.slerp(e.to_quaternion(),weight)
     basis=Matrix.LocRotScale(idle[n].translation,q,idle[n].to_scale())
     p[n]=p[parents[n]]@lr[n]@basis
     if j>1 and digit!='thumb':fingermax=max(fingermax,abs(math.degrees(q.to_euler().z)))
   if side=='l' and empty:
    weight=win(t,1.95,2.15,2.20,2.40);root=p['WPN_root']
    turn=Quaternion().slerp(Euler((0,math.radians(-5),math.radians(-15))).to_quaternion(),weight)
    move_hand(p,side,root.to_3x3()@Vector((.013113424,-.014230929,.005153637))*weight,root.to_quaternion()@turn@root.to_quaternion().inverted())
   if side=='r' and equip:
    root=p['WPN_root'];travel=(root.inverted()@p['WPN_ChargingHandle']).translation.y-.01
    pad=sum((p[n]@v for n,v in pads.items()),Vector())/2
    goal=root@Vector((-.005,.024+travel,.105))
    move_hand(p,side,(goal-pad)*win(t,.08,.20,.316667,.43),Quaternion())
   # Limit true wrist deviation/flexion, rather than allowing the source palm
   # roll to become a 180-degree wrist inversion on Manny's different axes.
   before=p[hn].copy();hb=lr[hn].inverted()@p[fn].inverted()@before;e=hb.to_euler('XYZ')
   e.x=max(math.radians(-125),min(math.radians(125),e.x));e.y=max(math.radians(-35),min(math.radians(35),e.y));e.z=max(math.radians(-50),min(math.radians(50),e.z))
   p[hn]=p[fn]@lr[hn]@Matrix.LocRotScale(hb.translation,e.to_quaternion(),hb.to_scale())
   turn=p[hn]@before.inverted()
   for n in names:
    if n.endswith('_'+side) and n.startswith(('thumb','index','middle','ring','pinky')):p[n]=turn@p[n]
    if n.startswith('lowerarm_twist') and n.endswith('_'+side):
     basis=idle[n];q=Quaternion(Vector((1,0,0)),e.x*(.5 if '_02_' in n else 1))
     p[n]=p[parents[n]]@lr[n]@Matrix.LocRotScale(basis.translation,q,basis.to_scale())
  final.append(p)
 # Resample arm-local curves with a short symmetric filter. The weapon curves
 # and gameplay cue clock are untouched; the filter removes frame spikes.
 localsamples=[{n:lr[n].inverted()@(p[parents[n]].inverted()@p[n] if parents[n] else p[n]) for n in names} for p in final]
 for f,p in enumerate(final):
  for n in names:
   if not n.endswith(('_l','_r')) or not n.startswith(('hand','upperarm','lowerarm','clavicle')):continue
   q=localsamples[f][n].to_quaternion();v=Vector((0,0,0,0));total=0
   for j in range(max(0,f-5),min(end,f+5)+1):
    other=localsamples[j][n].to_quaternion()
    if q.dot(other)<0:other.negate()
    w=math.exp(-.5*((j-f)/2.4)**2);v+=Vector(other)*w;total+=w
   smoothq=Quaternion(v/total).normalized();lm=localsamples[f][n];localsamples[f][n]=Matrix.LocRotScale(lm.translation,smoothq,lm.to_scale())
 for f,p in enumerate(final):
  for n in names:
   if n.startswith('WPN_'):continue
   lm=localsamples[f][n]
   edge=win(f,0,8,end-8,end)
   if n.endswith(('_l','_r')):
    start=idle[n];loc,q,sc=lm.decompose();q=start.to_quaternion().slerp(q,edge);lm=Matrix.LocRotScale(start.translation.lerp(loc,edge),q,start.to_scale().lerp(sc,edge))
   p[n]=(p[parents[n]] if parents[n] else Matrix.Identity(4))@lr[n]@lm
 a=bpy.data.actions.new('M4_MAT_'+clip);a.use_fake_user=True;r.animation_data.action=a;previous={}
 for f,p in enumerate(final):
  for n in names:
   lp=p[parents[n]].inverted()@p[n] if parents[n] else p[n]
   loc,q,scale=(lr[n].inverted()@lp).decompose()
   if n in previous and previous[n].dot(q)<0:q.negate()
   previous[n]=q.copy();b=r.pose.bones[n];b.rotation_mode='QUATERNION';b.location=loc;b.rotation_quaternion=q;b.scale=scale
   for prop in ['location','rotation_quaternion','scale']:b.keyframe_insert(prop,frame=f)
 for layer in a.layers:
  for strip in layer.strips:
   for bag in strip.channelbags:
    for curve in bag.fcurves:
     for k in curve.keyframe_points:k.interpolation='LINEAR'
 s.render.fps=60;s.frame_start=0;s.frame_end=end
 bpy.ops.object.select_all(action='DESELECT');r.select_set(True);bpy.context.view_layer.objects.active=r
 bpy.ops.export_scene.fbx(filepath=str(O/f'A_M4_MAT_{clip}.fbx'),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_step=1,bake_anim_simplify_factor=0)
 report['clips'][clip]={'frames':end+1,'duration':end/60,'nonthumb_distal_max_flex_deg':fingermax}
 print('REPAIRED',clip,flush=True)
action(bpy.data.actions['M4_MAT_reload_empty']);frame(130)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'M4_Hand_MAT_Editable.blend'))
(O/'repair_report.json').write_text(json.dumps(report,indent=2))
