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
report={}
for clip in ['reload','reload_empty','equip_charge']:
 equip=clip=='equip_charge';empty=clip.endswith('empty');drum=clip.startswith('drum');end=38 if equip else 162 if empty else 126
 old=bpy.data.actions[('A_M4_HK416_' if drum else 'M4_HK416_')+clip]
 raw=[sample(old,f) for f in range(end+1)]
 authored=bpy.data.actions['M4_equip' if equip else 'M4_reload']
 poses=[sample(authored,f/end*(62 if equip else 188)) for f in range(end+1)]
 keys=[0,9,15,18,22,30,end] if equip else ([0,12,21,40,54,80,100,115,130,142,end] if empty else [0,15,29,54,76,95,113,end])
 release=raw[min(130,end)]['WPN_root'].inverted()@raw[min(130,end)]['hand_l']
 out=[]
 for f in range(end+1):
  p={n:m.copy() for n,m in raw[f].items()};t=f/60
  if equip:
   root=interpolate(raw,keys,f,'WPN_root');delta=root@p['WPN_root'].inverted()
   for n in names:p[n]=delta@p[n]
  root=p['WPN_root']
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
    if meta in p:p[meta]=p[hn]@lr[meta]@idlelocal[meta]
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
 if empty:
  # Wind up outside the receiver, strike in four frames, arrest at the existing
  # bolt-release cue (frame 130), then withdraw with a short visible rebound.
  knots=[(106,106),(122,118),(126,121),(130,130),(131,130.6),(134,138),(142,146),(150,150)]
  original=[{n:m.copy() for n,m in p.items()} for p in out]
  for f in range(106,151):
   k=next(i for i in range(len(knots)-1) if knots[i][0]<=f<=knots[i+1][0]);x,y=knots[k];X,Y=knots[k+1];src=y+(Y-y)*(f-x)/(X-x);i=int(src);j=min(end,i+1);frac=src-i
   srcroot=mix(original[i]['WPN_root'],original[j]['WPN_root'],frac);root=out[f]['WPN_root']
   for n in names:
    if n.endswith('_l'):out[f][n]=root@srcroot.inverted()@mix(original[i][n],original[j][n],frac)
   recoil=win(f,130,131,132,138)
   response=root@Matrix.Translation((-.0025*recoil,0,0))@Quaternion(Vector((0,1,0)),math.radians(.8)*recoil).to_matrix().to_4x4()@root.inverted()
   for n in names:out[f][n]=response@out[f][n]
 # Bake at 240 Hz with an exact magazine-space grasp constraint. Sampling
 # only integer 60 Hz poses allowed the arm chain and magazine to interpolate
 # along different arcs, causing millimetres of slip between otherwise valid keys.
 localposes=[{n:p[parent[n]].inverted()@p[n] if parent[n] else p[n] for n in names} for p in out]
 dense=[]
 for k in range(end*4+1):
  f=k/4;i=int(f);j=min(end,i+1);p={}
  for n in names:p[n]=(p[parent[n]] if parent[n] else Matrix.Identity(4))@mix(localposes[i][n],localposes[j][n],f-i)
  if not equip and ((44<=f<=88) if empty else (23<=f<=100)):
   goal=p['WPN_SOCKET_Magazine']@griprel;delta=goal@p['hand_l'].inverted()
   for n in names:
    if n.endswith('_l'):p[n]=delta@p[n]
  dense.append(p)
 a=bpy.data.actions.new('M4_MAT_'+clip);a.use_fake_user=True;r.animation_data.action=a;previous={}
 for k,p in enumerate(dense):
  f=k/4
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
 bpy.ops.export_scene.fbx(filepath=str(O/f'A_M4_MAT_{clip}.fbx'),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_step=.25,bake_anim_simplify_factor=0)
 report[clip]={'duration':end/60,'keys':len(dense),'sample_rate':240,'arm_deformation_source':authored.name,'viewmodel_shoulder_controls':'free in camera space'}
sample(bpy.data.actions['M4_MAT_reload_empty'],130);bpy.ops.wm.save_as_mainfile(filepath=str(O/'M4_Hand_MAT_Editable.blend'));(O/'repair_report.json').write_text(json.dumps(report,indent=2));print('AUTHORED_REPAIR_DONE')
