"""PKM support wrist correction, preserving gun/right-hand/contact action tracks."""
import bpy,json,math,sys
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).parent;R=O.parent;E=O/'Exports';E.mkdir(exist_ok=True)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(R/'HandReload10/PKM_ReloadHands_Editable.blend'))
s=bpy.context.scene;r=bpy.data.objects['PKM_Manny_Rig'];s.render.fps=60;s.render.fps_base=1
def action(a):r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
action(bpy.data.actions['PKM_Game_idle']);s.frame_set(0);bpy.context.view_layer.update()
rest={b.name:b.matrix_local.copy() for b in r.data.bones};base={b.name:b.matrix.copy() for b in r.pose.bones};parent={b.name:b.parent.name if b.parent else None for b in r.data.bones}
localrest={n:rest[parent[n]].inverted()@m if parent[n] else m.copy() for n,m in rest.items()}
fit=Matrix(json.loads((R/'Animation03/animation_manifest.json').read_text())['fit_matrix']);W0=base['WPN_root']@fit
spec=json.loads((O/'support_fit.json').read_text());H=W0@Matrix(spec['hand_gun']);S=W0@Vector(spec['shoulder_gun']);elbow=W0@Vector(spec['elbow_gun'])
names=[n for n in base if n.endswith('_l') and n.startswith(('clavicle','upperarm','lowerarm','hand','thumb','index','middle','ring','pinky'))]
target={n:base[n].copy() for n in names}
shift=S-base['upperarm_l'].translation;target['clavicle_l'].translation+=shift
def frame(axis,normal):
 x=axis.normalized();z=(normal-x*normal.dot(x)).normalized();y=z.cross(x).normalized();return Matrix((x,y,z)).transposed()
old_upper=base['lowerarm_l'].translation-base['upperarm_l'].translation;old_lower=base['hand_l'].translation-base['lowerarm_l'].translation
new_upper=elbow-S;new_lower=H.translation-elbow
old_plane=old_upper.cross(old_lower).normalized();new_plane=new_upper.cross(new_lower).normalized()
# Keep the elbow's original hinge plane. Pointing a forearm at the hand
# without preserving this plane twists the sleeve at the elbow.
for bone,oldaxis,newaxis,point in [('upperarm_l',old_upper,new_upper,S),('lowerarm_l',old_lower,new_lower,elbow)]:
 q=frame(newaxis,new_plane)@frame(oldaxis,old_plane).transposed()
 target[bone]=q.to_4x4()@base[bone];target[bone].translation=point
target['hand_l']=H
delta=target['upperarm_l']@base['upperarm_l'].inverted()
for n in names:
 if n.startswith('upperarm_twist_'):target[n]=delta@base[n]
# Compute only REST-relative axial twist, in component space. Wrist bending
# never enters the forearm roll helpers. Preserve the existing skin weights.
Lf=target['lowerarm_l'];Df=Lf.to_3x3()@rest['lowerarm_l'].to_3x3().inverted();Dh=H.to_3x3()@rest['hand_l'].to_3x3().inverted()
dq=(Dh@Df.inverted()).to_quaternion();axis=new_lower.normalized();v=Vector((dq.x,dq.y,dq.z));v=axis*v.dot(axis)
twist=Quaternion((dq.w,v.x,v.y,v.z));twist.normalize()
if twist.w<0:twist.negate()
for suffix,fraction in [('02',.40),('01',.82)]:
 n='lowerarm_twist_'+suffix+'_l';m=Lf@rest['lowerarm_l'].inverted()@rest[n]
 q=Quaternion().slerp(twist,fraction);p=m.translation.copy();m=q.to_matrix().to_4x4()@m;m.translation=p;target[n]=m
print('PKM12_AXIAL_TWIST_DEG',math.degrees(twist.angle),flush=True)
for n in names:
 if n.startswith(('thumb','index','middle','ring','pinky')):target[n]=target[parent[n]]@base[parent[n]].inverted()@base[n]
def smooth(x):x=max(0,min(1,x));return x*x*(3-2*x)
def ramp(t,a,b):return smooth((t-a)/(b-a))
def mixmat(a,b,w):
 p,q,sc=a.decompose();p2,q2,sc2=b.decompose();return Matrix.LocRotScale(p.lerp(p2,w),q.slerp(q2,w),sc.lerp(sc2,w))
if '--pose-only' in sys.argv:
 out=r.animation_data.action.copy();out.name='PKM_Game_idle_Wrist12';action(out)
 for n in names:
  p=parent[n];local=(target[p] if p in target else base[p]).inverted()@target[n] if p else target[n]
  b=r.pose.bones[n];loc,q,scale=(localrest[n].inverted()@local).decompose();b.location=loc;b.rotation_mode='QUATERNION';b.rotation_quaternion=q;b.scale=scale
  for prop in ['location','rotation_quaternion','scale']:b.keyframe_insert(prop,frame=0,group=n)
 s.frame_set(0);bpy.ops.wm.save_as_mainfile(filepath=str(O/'PKM_WristCandidate.blend'));sys.exit(0)
clips={'idle':1,'aim':1,'fire':.1,'aim_fire':.1,'equip':.72,'inspect':4.2,'sprint_enter':.32,'sprint_loop':1,'sprint_exit':.32,'quick_melee':.9,'reload':6.5,'reload_empty':7.5}
record={}
for key,duration in clips.items():
 name={'reload':'PKM_Reload_Normal_HandReload10','reload_empty':'PKM_Reload_Empty_HandReload10'}.get(key,'PKM_Game_'+key)
 src=bpy.data.actions[name];action(src);frames=round(duration*60);samples=[]
 for f in range(frames+1):s.frame_set(f);bpy.context.view_layer.update();samples.append({b.name:b.matrix.copy() for b in r.pose.bones})
 out=src.copy();out.name=name+'_Wrist12';out.use_fake_user=True;action(out);previous={}
 for f,old in enumerate(samples):
  t=f/60;weight=1-ramp(t,.26,.62)+ramp(t,2.13,2.30) if key.startswith('reload') else 1.0
  W=old['WPN_root']@fit;X=W@W0.inverted();goal={n:X@m for n,m in target.items()};d={n:m.copy() for n,m in old.items()}
  for n in names:
   p=parent[n];a=old[p].inverted()@old[n] if p else old[n];b=(goal[p] if p in goal else old[p]).inverted()@goal[n] if p else goal[n]
   local=mixmat(a,b,weight);d[n]=d[p]@local if p else local
  for n in names:
   p=parent[n];local=d[p].inverted()@d[n] if p else d[n];loc,q,scale=(localrest[n].inverted()@local).decompose()
   if n in previous and previous[n].dot(q)<0:q.negate()
   previous[n]=q.copy();b=r.pose.bones[n];b.location=loc;b.rotation_mode='QUATERNION';b.rotation_quaternion=q;b.scale=scale
   for prop in ['location','rotation_quaternion','scale']:b.keyframe_insert(prop,frame=f,group=n)
 for layer in out.layers:
  for strip in layer.strips:
   for bag in strip.channelbags:
    for curve in bag.fcurves:
     if any(('pose.bones["'+n+'"]') in curve.data_path for n in names):
      for point in curve.keyframe_points:point.interpolation='LINEAR'
 s.frame_start=0;s.frame_end=frames;s.frame_set(0);bpy.ops.object.select_all(action='DESELECT');r.hide_set(False);r.select_set(True);bpy.context.view_layer.objects.active=r
 bpy.ops.export_scene.fbx(filepath=str(E/('A_PKM_'+key+'.fbx')),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0,bake_anim_step=1)
 record[key]={'action':out.name,'seconds':frames/60};print('PKM12_EXPORTED',key,flush=True)
action(bpy.data.actions[record['idle']['action']]);s.frame_start=0;s.frame_end=60;s.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'PKM_WristContact_Editable.blend'))
(O/'authoring.json').write_text(json.dumps({'clips':clips,'actions':record,'source':'HandReload10','bones_changed':names,'mesh_changed':False,'weights_changed':False,'only_reload_support_windows_changed':True,'runtime_tested':False},indent=2))
print('PKM12_AUTHOR_COMPLETE',flush=True)
