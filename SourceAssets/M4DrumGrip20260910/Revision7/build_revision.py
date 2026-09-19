import bpy,math,json
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'Revision6/M4_DrumThrow_Editable.blend'))
r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
with bpy.data.libraries.load(str(O.parent.parent/'M4ContactImpact20260910/M4_Hand_MAT_Editable.blend'),link=False) as (src,dst):
 dst.actions=['M4_MAT_reload','M4_MAT_reload_empty']
standard=dict(zip(['reload','reload_empty'],dst.actions))
with bpy.data.libraries.load(str(O.parent.parent/'M4SlapImpact20260910/M4_Hand_MAT_Editable.blend'),link=False) as (src,dst):
 dst.actions=['M4_MAT_reload_empty']
standard['reload_empty']=dst.actions[0]
names=[b.name for b in r.pose.bones];parents={b.name:b.parent.name if b.parent else None for b in r.pose.bones}
rest={b.name:b.bone.matrix_local.copy() for b in r.pose.bones}
lr={n:rest[parents[n]].inverted()@rest[n] if parents[n] else rest[n] for n in names}
def smooth(t):
 t=max(0,min(1,t));return t*t*(3-2*t)
def mix(a,b,t):
 p,q,z=a.decompose();P,Q,Z=b.decompose();return Matrix.LocRotScale(p.lerp(P,t),q.slerp(Q,t),z.lerp(Z,t))
def sample(a,t):
 r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(int(t),subframe=t%1);bpy.context.view_layer.update();return {b.name:b.matrix.copy() for b in r.pose.bones}
def mapped(t,empty):return t+(14*smooth((t-109)/2) if empty else 0)
report={}
for clip,end in [('reload',126),('reload_empty',148)]:
 empty=clip.endswith('empty');old=bpy.data.actions['A_M4_DrumThrow_'+clip];out=[];position_error=angle_error=0
 for k in range(end*2+1):
  f=k/2;oldf=mapped(f,empty);base=sample(old,oldf);std=sample(standard[clip],oldf);delta=std['WPN_root']@base['WPN_root'].inverted();p={n:delta@m for n,m in base.items()}
  # Use the ordinary magazine's weapon motion and complete right arm.
  for n in names:
   if n.endswith('_r'):p[n]=std[n].copy()
  if empty and f>104:
   weight=smooth((f-104)/10)*(1-smooth((f-122)/10))
   # The drum is already seated. Blend out to the original magazine's clear
   # withdrawal/lift, then use its complete slap and recovery without new IK.
   left=[n for n in names if n.endswith('_l')];leftset=set(left)
   local0={n:(p[parents[n]].inverted()@p[n] if parents[n] else p[n]) for n in left}
   local1={n:((std[parents[n]] if parents[n] in leftset else p[parents[n]]).inverted()@std[n] if parents[n] else std[n]) for n in left}
   for n in left:p[n]=(p[parents[n]] if parents[n] else Matrix.Identity(4))@mix(local0[n],local1[n],weight)
  if empty and 108<f<126:
   clearance=smooth((f-108)/7)*(1-smooth((f-119)/7))
   pivot=p['upperarm_l'].translation;direction=p['hand_l'].translation-pivot
   target=direction+Vector((0,0,.025*clearance))
   turn=direction.rotation_difference(target).to_matrix().to_4x4()
   offset=Matrix.Translation(pivot)@turn@Matrix.Translation(-pivot)
   for n in names:
    if n.endswith('_l') and n!='clavicle_l':p[n]=offset@p[n]
  # Keep the accepted drum grasp and magazine motion through insertion.
  a=std['WPN_root'];b=p['WPN_root'];position_error=max(position_error,(a.translation-b.translation).length*100)
  q=a.to_quaternion().rotation_difference(b.to_quaternion());angle_error=max(angle_error,min(q.angle,2*math.pi-q.angle)*180/math.pi)
  out.append(p)
 old.name='BeforeMatch_'+clip
 a=bpy.data.actions.new('A_M4_DrumMatch_'+clip);a.use_fake_user=True;r.animation_data.action=a;previous={}
 for k,p in enumerate(out):
  for n in names:
   local=lr[n].inverted()@(p[parents[n]].inverted()@p[n] if parents[n] else p[n]);loc,q,z=local.decompose()
   if n in previous and previous[n].dot(q)<0:q.negate()
   previous[n]=q.copy();b=r.pose.bones[n];b.rotation_mode='QUATERNION';b.location=loc;b.rotation_quaternion=q;b.scale=z
   for prop in ['location','rotation_quaternion','scale']:b.keyframe_insert(prop,frame=k/2)
 for layer in a.layers:
  for strip in layer.strips:
   for bag in strip.channelbags:
    for curve in bag.fcurves:
     for key in curve.keyframe_points:key.interpolation='LINEAR'
 s.render.fps=60;s.frame_start=0;s.frame_end=end;bpy.ops.object.select_all(action='DESELECT');r.select_set(True);bpy.context.view_layer.objects.active=r
 bpy.ops.export_scene.fbx(filepath=str(O/(a.name+'.fbx')),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_step=.5,bake_anim_simplify_factor=0)
 report[clip]={'frames':end,'duration':end/60,'weapon_position_difference_cm':position_error,'weapon_angle_difference_deg':angle_error,'slap_source_contact_frame':130 if empty else None,'slap_new_contact_frame':116 if empty else None,'removed_windup_frames':14 if empty else 0}
 r.animation_data.action=None
r.animation_data.action=bpy.data.actions['A_M4_DrumMatch_reload_empty'];r.animation_data.action_slot=r.animation_data.action.slots[0];s.frame_start=0;s.frame_end=148;s.frame_set(116)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'M4_DrumMatch_Editable.blend'));(O/'build_report.json').write_text(json.dumps(report,indent=2));print('DRUM_MATCH_BUILD_PASS')
