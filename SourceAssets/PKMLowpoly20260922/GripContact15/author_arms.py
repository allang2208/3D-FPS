"""Refine PKM attachment wrist support without moving the hand's grip anchor."""
import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).parent;A=O.parent/'Accessories14'
fit=json.loads((O/'fit_frames.json').read_text())['arms'];clips=json.loads((A/'animations.json').read_text());report={}
bpy.context.preferences.filepaths.save_version=0
def smooth(x):x=max(0,min(1,x));return x*x*(3-2*x)
def ramp(t,a,b):return smooth((t-a)/(b-a))
def frame(axis,width):
 x=axis.normalized();y=(width-x*width.dot(x)).normalized();z=x.cross(y).normalized();return Matrix((x,y,z)).transposed()
def mix(a,b,w):
 p,q,s=a.decompose();p2,q2,s2=b.decompose();return Matrix.LocRotScale(p.lerp(p2,w),q.slerp(q2,w),s.lerp(s2,w))
def bags(a):
 for l in a.layers:
  for s in l.strips:yield from s.channelbags
for family in ['vertical','canted','prism','angled']:
 bpy.ops.wm.open_mainfile(filepath=str(A/f'PKM_{family}_Editable.blend'))
 r=bpy.data.objects['PKM_Manny_Rig'];scene=bpy.context.scene
 def action(a):r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
 rest={b.name:b.matrix_local.copy() for b in r.data.bones};parents={b.name:b.parent.name if b.parent else None for b in r.data.bones}
 localrest={n:rest[parents[n]].inverted()@m if parents[n] else m for n,m in rest.items()}
 names=['clavicle_l','upperarm_l','lowerarm_l','upperarm_twist_01_l','upperarm_twist_02_l','lowerarm_twist_01_l','lowerarm_twist_02_l','hand_l']
 action(bpy.data.actions[f'A_PKM_{family}_idle']);scene.frame_set(0);bpy.context.view_layer.update();W0=r.pose.bones['WPN_root'].matrix.copy()
 shoulder_shift=Vector(fit[family]['shift']);elbow_target=Vector(fit[family]['elbow'])
 restaxis=rest['hand_l'].translation-rest['lowerarm_l'].translation
 restwidth=rest['index_metacarpal_l'].translation-rest['pinky_metacarpal_l'].translation
 restframe=frame(restaxis,restwidth)
 for key,info in clips.items():
  fam,clip=key.split('/')
  if fam!=family:continue
  source=bpy.data.actions[info['name']];action(source);fps=info['fps'];count=round(info['seconds']*fps);samples=[];scene.render.fps=60
  for f in range(count+1):
   sf=f*60/fps;scene.frame_set(int(sf),subframe=sf%1);bpy.context.view_layer.update();samples.append({b.name:b.matrix.copy() for b in r.pose.bones})
  out=source.copy();out.name=info['name']+'_Contact15';out.use_fake_user=True
  for bag in bags(out):
   for curve in list(bag.fcurves):
    if any(curve.data_path.startswith(f'pose.bones["{n}"]') for n in names):bag.fcurves.remove(curve)
    elif fps!=60:
     for p in curve.keyframe_points:p.co.x*=fps/60;p.handle_left.x*=fps/60;p.handle_right.x*=fps/60
  action(out);scene.render.fps=fps;previous={}
  for f,row in enumerate(samples):
   t=f/fps;w=1-ramp(t,.26,.62)+ramp(t,2.13,2.30) if clip.startswith('reload') else 1.
   desired={n:m.copy() for n,m in row.items()}
   if w>1e-7:
    X=row['WPN_root']@W0.inverted();S0=row['upperarm_l'].translation;E0=row['lowerarm_l'].translation;H=row['hand_l'];P=H.translation
    shift=X.to_3x3()@shoulder_shift*w;S=S0+shift;L1=(E0-S0).length;L2=(P-E0).length
    delta=P-S;dist=delta.length;axis=delta.normalized()
    # Keep original bone lengths at the transition extremes as well as idle.
    if dist>L1+L2-.004:S+=axis*(dist-(L1+L2-.004));dist=(P-S).length
    along=(L1*L1-L2*L2+dist*dist)/(2*dist);height=math.sqrt(max(0,L1*L1-along*along));C=S+axis*along
    pole0=E0-C;pole0=(pole0-axis*pole0.dot(axis)).normalized()
    pole1=X@elbow_target-C;pole1=(pole1-axis*pole1.dot(axis)).normalized()
    theta=math.atan2(axis.dot(pole0.cross(pole1)),pole0.dot(pole1));E=C+Quaternion(axis,theta*w)@pole0*height
    upper0=E0-S0;lower0=P-E0;upper=E-S;lower=P-E
    plane0=upper0.cross(lower0);plane=upper.cross(lower)
    Ru=frame(upper,plane)@frame(upper0,plane0).transposed()@row['upperarm_l'].to_3x3()
    desired['upperarm_l']=Ru.to_4x4();desired['upperarm_l'].translation=S
    desired['clavicle_l'].translation+=S-S0
    # Palm-width roll contains only the hand's transverse orientation. Keep
    # wrist flexion out of roll, and move all lower-arm helpers as one segment.
    hand_deform=H.to_3x3()@rest['hand_l'].to_3x3().inverted()
    targetR=frame(lower,hand_deform@restwidth)@restframe.transposed()@rest['lowerarm_l'].to_3x3()
    carryR=lower0.rotation_difference(lower).to_matrix()@row['lowerarm_l'].to_3x3()
    desired['lowerarm_l']=carryR.to_quaternion().slerp(targetR.to_quaternion(),w).to_matrix().to_4x4();desired['lowerarm_l'].translation=E
    for segment in ['upperarm','lowerarm']:
     parent=segment+'_l'
     for suffix in ['01','02']:
      n=segment+'_twist_'+suffix+'_l';oldlocal=row[parent].inverted()@row[n];correct=rest[parent].inverted()@rest[n]
      desired[n]=desired[parent]@mix(oldlocal,correct,w)
    # hand_l and every finger retain their exact source component transform.
   for n in names:
    parent=parents[n];basis=localrest[n].inverted()@desired[parent].inverted()@desired[n];loc,q,sc=basis.decompose()
    if n in previous and previous[n].dot(q)<0:q.negate()
    previous[n]=q.copy();b=r.pose.bones[n];b.location=loc;b.rotation_mode='QUATERNION';b.rotation_quaternion=q;b.scale=sc
    for prop in ['location','rotation_quaternion','scale']:b.keyframe_insert(prop,frame=f,group=n)
  for bag in bags(out):
   for curve in bag.fcurves:
    if any(curve.data_path.startswith(f'pose.bones["{n}"]') for n in names):
     for point in curve.keyframe_points:point.interpolation='LINEAR'
  scene.frame_start=0;scene.frame_end=count;scene.frame_set(0)
  bpy.ops.object.select_all(action='DESELECT');r.hide_set(False);r.select_set(True);bpy.context.view_layer.objects.active=r
  dest=O/'Animations'/family;dest.mkdir(parents=True,exist_ok=True)
  bpy.ops.export_scene.fbx(filepath=str(dest/(info['name']+'.fbx')),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0,bake_anim_step=1)
  report[key]={**info,'editable_action':out.name,'changes':'Left arm support and coherent twist helpers; hand/fingers retained'}
  if fps!=60:
   for bag in bags(out):
    for curve in bag.fcurves:
     for p in curve.keyframe_points:p.co.x*=60/fps;p.handle_left.x*=60/fps;p.handle_right.x*=60/fps
  print('PKM15_ARM_EXPORTED',key,flush=True)
 scene.render.fps=60;action(bpy.data.actions[f'A_PKM_{family}_idle_Contact15']);scene.frame_start=0;scene.frame_end=60;scene.frame_set(0)
 bpy.ops.wm.save_as_mainfile(filepath=str(O/f'PKM_{family}_Editable.blend'))
 (O/'animations.json').write_text(json.dumps(report,indent=2))
print('PKM15_ARMS_COMPLETE',flush=True)
