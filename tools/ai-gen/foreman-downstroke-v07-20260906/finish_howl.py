# Preserve Howl body animation and retarget its accessory to the corrected palm.
act=bpy.data.actions['Howl'];a.animation_data.action=act
for frame in range(3*FPS+1):
 s.frame_set(frame);bpy.context.view_layer.update()
 delta=a.pose.bones['hand.R'].matrix@rest['hand.R'].inverted()
 grip=delta@Vector((-.805,-.235,1.18));direction=(delta.to_3x3()@Vector((0,-1,0))).normalized()
 animate_long_whip(a,grip,direction,frame/FPS,'Howl',curve)
 for i in range(33):
  pb=a.pose.bones[f'whip.{i:02d}']
  for channel in ['location','rotation_quaternion','scale']:pb.keyframe_insert(channel,frame=frame,group=pb.name)
 for side,sign in [('L',1),('R',-1)]:
  for name,world_axis,angle in [('fingers_cup.'+side,Vector((0,sign,0)),.88 if side=='R' else .19),('fingers_tip.'+side,Vector((0,sign,0)),.528 if side=='R' else .114),('thumb.'+side,Vector((.8,-sign*.5,0)).normalized(),.85 if side=='R' else .15)]:
   pb=a.pose.bones[name];pb.rotation_mode='QUATERNION';pb.rotation_quaternion=Quaternion(rest[name].to_3x3().inverted()@world_axis,angle);pb.keyframe_insert('rotation_quaternion',frame=frame,group=name)
