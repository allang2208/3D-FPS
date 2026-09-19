import bpy,math,json,sys
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
OUT=Path(__file__).resolve().parent;sys.path.insert(0,str(OUT))
from preview_setup import setup,render
r,s,drum=setup();grip=json.loads((OUT/'grip_pose.json').read_text())
d=json.loads(Path('D:/FPS3D/FPSGAME/SourceAssets/M4Drum20260909/build.json').read_text());G=Matrix(d['source_to_component']);center=Vector(d['center']);bind=r.data.bones['WPN_SOCKET_Magazine'].matrix_local.copy()
fingers=list(grip['fingers']);target_wrist=Matrix(grip['wrist_in_drum']);target_fingers={n:Matrix(m) for n,m in grip['fingers'].items()}
def action(a):
 r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
def frame(f):s.frame_set(f);bpy.context.view_layer.update()
def smooth(x):x=max(0,min(1,x));return x*x*(3-2*x)
def blend(a,b,t):
 p,q,z=a.decompose();P,Q,Z=b.decompose();return Matrix.LocRotScale(p.lerp(P,t),q.slerp(Q,t),z.lerp(Z,t))
def arm_to(goal):
 upper=r.pose.bones['upperarm_l'].matrix.copy();fore=r.pose.bones['lowerarm_l'].matrix.copy();old=r.pose.bones['hand_l'].matrix.copy()
 a=upper.translation.copy();b=fore.translation;c=old.translation;target=goal.translation;l1=(b-a).length;l2=(c-b).length;axis=(target-a).normalized();dist=(target-a).length
 if dist>l1+l2-.00001:a+=axis*(dist-l1-l2+.00001);dist=l1+l2-.00001
 pole=b-a-axis*(b-a).dot(axis);pole.normalize();along=(l1*l1-l2*l2+dist*dist)/(2*dist);elbow=a+axis*along+pole*math.sqrt(max(0,l1*l1-along*along))
 r.pose.bones['upperarm_l'].matrix=Matrix.LocRotScale(a,(b-upper.translation).rotation_difference(elbow-a)@upper.to_quaternion(),upper.to_scale());bpy.context.view_layer.update()
 r.pose.bones['lowerarm_l'].matrix=Matrix.LocRotScale(elbow,(c-b).rotation_difference(target-elbow)@fore.to_quaternion(),fore.to_scale());bpy.context.view_layer.update()
 r.pose.bones['hand_l'].matrix=goal;bpy.context.view_layer.update()
report={}
for clip,end,start,lock,seat,release in [('reload',126,8,25,95,110),('reload_empty',162,27,43,80,98)]:
 source=bpy.data.actions['M4_HK416_'+clip];samples=[];contacts=[];max_right=0
 for t in range(end+1):
  action(source);frame(t);right=r.pose.bones['hand_r'].matrix.copy()
  D=r.pose.bones['WPN_SOCKET_Magazine'].matrix@bind.inverted()@G@Matrix.Translation(center)
  weight=smooth((t-start)/(lock-start))*(1-smooth((t-seat)/(release-seat)))
  goal=blend(r.pose.bones['hand_l'].matrix,D@target_wrist,weight)
  # Fingers open during the approach and close only as the hand reaches the drum.
  close=smooth((t-(lock-8))/8);opening=smooth((t-start)/max(1,lock-start-8))*(1-close)
  if weight>0:
   arm_to(goal)
   for n in fingers:
    b=r.pose.bones[n];p,q,z=target_fingers[n].decompose();q=q.slerp(Quaternion(),opening*.65)
    b.matrix_basis=blend(b.matrix_basis,Matrix.LocRotScale(p,q,z),weight)
   bpy.context.view_layer.update()
  if lock<=t<=seat:
   local=D.inverted()@r.pose.bones['hand_l'].matrix;contacts.append((local.translation-target_wrist.translation).length*100)
  max_right=max(max_right,(right.translation-r.pose.bones['hand_r'].head).length*100)
  samples.append({b.name:b.matrix_basis.copy() for b in r.pose.bones})
 a=bpy.data.actions.new('A_M4_DrumGrip_'+clip);a.use_fake_user=True;r.animation_data.action=a;previous={}
 for t,poses in enumerate(samples):
  for n,m in poses.items():
   b=r.pose.bones[n];p,q,z=m.decompose()
   if n in previous and previous[n].dot(q)<0:q.negate()
   previous[n]=q.copy();b.rotation_mode='QUATERNION';b.location=p;b.rotation_quaternion=q;b.scale=z
   for prop in ['location','rotation_quaternion','scale']:b.keyframe_insert(prop,frame=t)
 for layer in a.layers:
  for strip in layer.strips:
   for bag in strip.channelbags:
    for curve in bag.fcurves:
     for k in curve.keyframe_points:k.interpolation='LINEAR'
 s.render.fps=60;s.frame_start=0;s.frame_end=end
 bpy.ops.object.select_all(action='DESELECT');r.select_set(True);bpy.context.view_layer.objects.active=r
 bpy.ops.export_scene.fbx(filepath=str(OUT/(a.name+'.fbx')),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_step=1,bake_anim_simplify_factor=0)
 report[clip]={'frames':end+1,'duration':end/60,'open_start':start,'grip_locked':lock,'seat':seat,'release_complete':release,'contact_slip_cm':max(contacts),'right_hand_change_cm':max_right,'loop':False}
 assert max(contacts)<.001 and max_right<.001
 for t in [start,lock,seat,release]:render(r,s,t,OUT/f'after_{clip}_{t}.png')
 # Render an actual-mesh motion strip from a stable close-up angle.
 folder=OUT/'Frames'/clip;folder.mkdir(parents=True,exist_ok=True)
 for t in range(0,end+1,3):
  frame(t);D=r.pose.bones['WPN_root'].matrix;focus=D.translation
  s.camera.data.type='ORTHO';s.camera.data.ortho_scale=.85;s.camera.location=focus+Vector((.65,-.35,.22));s.camera.rotation_euler=(focus-s.camera.location).to_track_quat('-Z','Y').to_euler()
  s.render.resolution_x=800;s.render.resolution_y=600;s.render.filepath=str(folder/f'{t:03}.png');bpy.ops.render.render(write_still=True)
 print('DRUM_GRIP_CLIP_PASS',clip,report[clip],flush=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'M4_DrumGrip_Editable.blend'))
(OUT/'animation_report.json').write_text(json.dumps(report,indent=2))
