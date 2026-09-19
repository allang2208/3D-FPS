"""Extended magazine ONLY: move accepted curled hand into the factory upper shell.
Keep the source weapon/magazine motion, finger articulation, timing and slap intact.
Use a two-bone arm solve to retain shoulder position and arm lengths.
"""
import bpy,math,json
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent
def smooth(x):x=max(0,min(1,x));return x*x*(3-2*x)
def aimed(old,old_end,origin,end):
 olddir=old_end-old.translation;q=olddir.rotation_difference(end-origin)
 return Matrix.LocRotScale(origin,q@old.to_quaternion(),old.to_scale())
reports={}
for clip,folder,end,window in [('reload','M4TacticalToss20260910',126,(43,61,95,108)),('reload_empty','M4SlapImpact20260910',162,(35,43,80,100))]:
 bpy.ops.wm.open_mainfile(filepath=str(O.parent/folder/'M4_Hand_MAT_Editable.blend'))
 rig=bpy.data.objects['SK_M4_Infima'];scene=bpy.context.scene;old=bpy.data.actions['M4_MAT_'+clip];rig.animation_data.action=old;rig.animation_data.action_slot=old.slots[0]
 names=[b.name for b in rig.pose.bones];parent={b.name:b.parent.name if b.parent else None for b in rig.pose.bones};rest={b.name:b.matrix_local.copy() for b in rig.data.bones};localrest={n:rest[parent[n]].inverted()@rest[n] if parent[n] else rest[n] for n in names}
 W=rig.matrix_world.copy();Wi=W.inverted();samples=[]
 # Palm moves inward and toward the feed end, leaving extension below the pinky.
 pivot=Vector((.028,.248,-.150));rot=Matrix.Rotation(math.radians(8),4,'Z')
 full=Matrix.Translation(Vector((.015,.020,.013)))@Matrix.Translation(pivot)@rot@Matrix.Translation(-pivot)
 for k in range(end*8+1):
  f=k/8;scene.frame_set(int(f),subframe=f-int(f));bpy.context.view_layer.update();p={b.name:b.matrix.copy() for b in rig.pose.bones}
  weight=smooth((f-window[0])/(window[1]-window[0]))*(1-smooth((f-window[2])/(window[3]-window[2])))
  if weight>0:
   loc,q,sc=full.decompose();step=Matrix.LocRotScale(loc*weight,Matrix.Identity(3).to_quaternion().slerp(q,weight),Vector((1,1,1)))
   mag=W@p['WPN_SOCKET_Magazine']@rest['WPN_SOCKET_Magazine'].inverted()@Wi
   delta=Wi@mag@step@mag.inverted()@W
   shoulder=p['upperarm_l'].translation;elbow=p['lowerarm_l'].translation;wrist=p['hand_l'].translation;target=(delta@p['hand_l']).translation
   l1=(elbow-shoulder).length;l2=(wrist-elbow).length;axis=(target-shoulder).normalized();distance=min((target-shoulder).length,l1+l2-1e-5)
   pole=elbow-shoulder-axis*(elbow-shoulder).dot(axis);pole.normalize()
   reach=(l1*l1-l2*l2+distance*distance)/(2*distance);height=math.sqrt(max(0,l1*l1-reach*reach));newelbow=shoulder+axis*reach+pole*height
   upper=aimed(p['upperarm_l'],elbow,shoulder,newelbow);lower=aimed(p['lowerarm_l'],wrist,newelbow,target)
   du=upper@p['upperarm_l'].inverted();dl=lower@p['lowerarm_l'].inverted()
   for n in names:
    if not n.endswith('_l'):continue
    if n.startswith(('hand','thumb','index','middle','ring','pinky')):p[n]=delta@p[n]
    elif n.startswith('lowerarm'):p[n]=dl@p[n]
    elif n.startswith('upperarm'):p[n]=du@p[n]
  samples.append(p)
 action=bpy.data.actions.new('M4_ExtMag_'+clip);action.use_fake_user=True;rig.animation_data.action=action;previous={}
 for k,p in enumerate(samples):
  for n in names:
   local=localrest[n].inverted()@(p[parent[n]].inverted()@p[n] if parent[n] else p[n]);loc,q,sc=local.decompose()
   if n in previous and previous[n].dot(q)<0:q.negate()
   previous[n]=q.copy();b=rig.pose.bones[n];b.rotation_mode='QUATERNION';b.location=loc;b.rotation_quaternion=q;b.scale=sc
   for prop in ['location','rotation_quaternion','scale']:b.keyframe_insert(prop,frame=k/8)
 for layer in action.layers:
  for strip in layer.strips:
   for bag in strip.channelbags:
    for fc in bag.fcurves:
     for key in fc.keyframe_points:key.interpolation='LINEAR'
 scene.render.fps=60;scene.frame_start=0;scene.frame_end=end;bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
 bpy.ops.export_scene.fbx(filepath=str(O/'FBX'/('A_M4_ExtMag_'+clip+'.fbx')),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_step=.125,bake_anim_simplify_factor=0)
 scene.frame_set(window[1]);bpy.ops.wm.save_as_mainfile(filepath=str(O/('M4_ExtMag_'+clip+'_Editable.blend')))
 reports[clip]={'source':folder,'duration':end/60,'sample_rate':480,'blend_window_frames':window,'rest_frame_translation_cm':[1.5,2,1.3],'palm_yaw_degrees':8,'finger_articulation':'retained','weapon_magazine_tracks':'retained','runtime_validation':'not run'}
 print('GRIP_AUTHORED',clip,flush=True)
(O/'grip_authoring.json').write_text(json.dumps(reports,indent=2))
