"""Polish the accepted drum motion; keep hand/drum contact and all timing."""
import bpy,math,json,sys
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).parent;OLD=O.parent/'Revision2'
bpy.ops.wm.open_mainfile(filepath=str(OLD/'M4_DrumGrip_Rebuilt.blend'))
r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;rest=r.data.bones
un,fn,hn='upperarm_l','lowerarm_l','hand_l'
ru=rest[fn].head_local-rest[un].head_local;rv=rest[hn].head_local-rest[fn].head_local;l1=ru.length;l2=rv.length;ru.normalize();rv.normalize()
def smooth(t):
 t=max(0,min(1,t));return t*t*(3-2*t)
def update():bpy.context.view_layer.update()
def solve(old,w):
 goal=old[hn];a=old[un].translation;target=goal.translation
 desired=goal.to_3x3()@rest[hn].matrix_local.to_3x3().inverted()@rv;desired.normalize()
 ideal=target-desired*l2;shift=ideal+(a-ideal).normalized()*l1-a
 if shift.length>.06:shift=shift.normalized()*.06
 shift*=w;A=a+shift;delta=target-A;dist=delta.length;axis=delta.normalized()
 oldpole=old[fn].translation-A;oldpole-=axis*oldpole.dot(axis);oldpole.normalize()
 pole=ideal-A;pole-=axis*pole.dot(axis);pole.normalize();pole=oldpole.lerp(pole,w).normalized()
 along=(l1*l1-l2*l2+dist*dist)/(2*dist);elbow=A+axis*along+pole*math.sqrt(max(0,l1*l1-along*along))
 u=(elbow-A).normalized();v=(target-elbow).normalized();old_u=(old[fn].translation-a).normalized();old_v=(target-old[fn].translation).normalized()
 uswing=old_u.rotation_difference(u);vswing=old_v.rotation_difference(v)
 clav=old['clavicle_l'].copy();clav.translation+=shift;r.pose.bones['clavicle_l'].matrix=clav;update()
 upper=Matrix.LocRotScale(A,uswing@old[un].to_quaternion(),Vector((1,1,1)));r.pose.bones[un].matrix=upper;update()
 for n in ['upperarm_twist_01_l','upperarm_twist_02_l']:
  m=upper@old[un].inverted()@old[n];r.pose.bones[n].matrix=m;update()
 base=vswing@old[fn].to_quaternion();neutral=base@rest[fn].matrix_local.to_quaternion().inverted()@rest[hn].matrix_local.to_quaternion()
 q=goal.to_quaternion()@neutral.inverted();twist=2*math.atan2(Vector((q.x,q.y,q.z)).dot(v),q.w)
 twist=(twist+math.pi)%(2*math.pi)-math.pi
 lower=Matrix.LocRotScale(elbow,Quaternion(v,twist*.10*w)@base,Vector((1,1,1)));r.pose.bones[fn].matrix=lower;update()
 for n,fraction in [('lowerarm_twist_02_l',.55),('lowerarm_twist_01_l',.95)]:
  oldq=vswing@old[n].to_quaternion();targetq=Quaternion(v,twist*fraction)@base@rest[fn].matrix_local.to_quaternion().inverted()@rest[n].matrix_local.to_quaternion()
  p=elbow+v*(rest[n].head_local-rest[fn].head_local).length
  r.pose.bones[n].matrix=Matrix.LocRotScale(p,oldq.slerp(targetq,w),Vector((1,1,1)));update()
 r.pose.bones[hn].matrix=goal;update()
 return {'shoulder_shift_cm':shift.length*100,'wrist_bend_deg':math.degrees(v.angle(desired)),'twist_deg':math.degrees(twist),'hand_error_cm':(r.pose.bones[hn].head-target).length*100}
report={}
for clip,end in [('reload',126),('reload_empty',162)]:
 a=bpy.data.actions['A_M4_DrumGrip_'+clip];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];raw=[]
 for k in range(end*2+1):
  s.frame_set(k//2,subframe=(k%2)/2);update();raw.append({'global':{b.name:b.matrix.copy() for b in r.pose.bones},'basis':{b.name:b.matrix_basis.copy() for b in r.pose.bones}})
 r.animation_data.action=None;poses=[];rows=[]
 for k,p in enumerate(raw):
  t=k/2;s.frame_set(k//2,subframe=(k%2)/2)
  for n,m in p['basis'].items():r.pose.bones[n].matrix_basis=m
  update();w=smooth(t/12)*smooth((end-t)/12);row=solve(p['global'],w);row['frame']=t;rows.append(row);poses.append({b.name:b.matrix_basis.copy() for b in r.pose.bones})
 a.name='BeforeWrist_'+clip;a=bpy.data.actions.new('A_M4_DrumGrip_'+clip);a.use_fake_user=True;r.animation_data.action=a;previous={}
 for k,p in enumerate(poses):
  t=k/2
  for n,m in p.items():
   b=r.pose.bones[n];loc,q,z=m.decompose()
   if n in previous and previous[n].dot(q)<0:q.negate()
   previous[n]=q.copy();b.rotation_mode='QUATERNION';b.location=loc;b.rotation_quaternion=q;b.scale=z
   for prop in ['location','rotation_quaternion','scale']:b.keyframe_insert(prop,frame=t)
 for layer in a.layers:
  for strip in layer.strips:
   for bag in strip.channelbags:
    for curve in bag.fcurves:
     for k in curve.keyframe_points:k.interpolation='LINEAR'
 s.render.fps=60;s.frame_start=0;s.frame_end=end;bpy.ops.object.select_all(action='DESELECT');r.select_set(True);bpy.context.view_layer.objects.active=r
 bpy.ops.export_scene.fbx(filepath=str(O/(a.name+'.fbx')),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_step=.5,bake_anim_simplify_factor=0)
 report[clip]=rows;r.animation_data.action=None;print(clip,'BEND',max(x['wrist_bend_deg'] for x in rows),'SHOULDER',max(x['shoulder_shift_cm'] for x in rows),flush=True)
r.animation_data.action=bpy.data.actions['A_M4_DrumGrip_reload'];r.animation_data.action_slot=r.animation_data.action.slots[0];s.frame_start=0;s.frame_end=126;s.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'M4_DrumGrip_Rebuilt.blend'));(O/'wrist_report.json').write_text(json.dumps(report,indent=2))
