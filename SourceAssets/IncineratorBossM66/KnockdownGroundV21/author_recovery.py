"""Replace the hovering down/get-up poses on the current M66 rig; keep gameplay timing."""
from pathlib import Path
BASE=Path('D:/FPS3D/FPSGAME/SourceAssets/IncineratorBossM66');ROOT=BASE/'KnockdownGroundV21'
exec((ROOT/'find_support_pose.py').read_text('utf-8').split('rows=[]')[0])
DOWN_PITCH=1.55;DOWN_ROLL=-.35
from mathutils import Matrix,Vector,Quaternion
for folder in ('Authoring','Export','Records'):(ROOT/folder).mkdir(exist_ok=True)
rig.animation_data.action=None
if mesh.data.shape_keys:
 for key in mesh.data.shape_keys.key_blocks:key.value=0.
def below(n,parent):
 while parents[n]:
  n=parents[n]
  if n==parent:return True
 return False
upper,lower,wrist='Bone_027','Bone_026','Bone_037'
arm=[n for n in ordered if n==upper or below(n,upper)]
hand_bones={wrist,*[n for n in ordered if below(n,wrist)]}
hand_ids=[v.index for v in mesh.data.vertices if sum(g.weight for g in v.groups if groups.get(g.group) in hand_bones)>.7]
body_ids=body
leg_ids=feet_ids
hand_set=set(hand_ids)
hand_local=np.array([neutral[wrist].inverted()@v.co for v in mesh.data.vertices if v.index in hand_set])
length_a=(neutral[lower].translation-neutral[upper].translation).length
length_b=(neutral[wrist].translation-neutral[lower].translation).length
def snapshot():return {n:rig.pose.bones[n].matrix.copy() for n in ordered}
def local_snapshot():return {n:rig.pose.bones[n].matrix_basis.copy() for n in ordered}
def surface():
 bpy.context.view_layer.update();ev=mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
 a=np.empty(len(ev.data.vertices)*3);ev.data.vertices.foreach_get('co',a);a=a.reshape(-1,3)
 m=np.array(ev.matrix_world);return a@m[:3,:3].T+m[:3,3]
def ground():
 a=surface();shift=Vector((0,0,floor_z-float(a[:,2].min())))
 delta=rig.matrix_world.inverted().to_3x3()@shift
 worlds=snapshot()
 for mat in worlds.values():mat.translation+=delta
 apply_worlds(worlds)

# Fixed lateral hand placement avoids dragging the planted palm through the body.
make_pose('Landing',.9,.9);bpy.context.view_layer.update();down=snapshot()
finger_a=neutral['Bone_061'].translation-neutral[wrist].translation
finger_b=neutral['Bone_073'].translation-neutral[wrist].translation
normal_local=neutral[wrist].to_quaternion().inverted()@finger_a.cross(finger_b).normalized()
old_q=down[wrist].to_quaternion();normal_world=old_q@normal_local
up=Vector((0,0,1 if normal_world.z>=0 else -1))
plant_q=normal_world.rotation_difference(up)@old_q
plant_pos=down[wrist].translation.copy()
outward=down[upper].translation-down['Bone_000'].translation;outward.z=0
if outward.length>1e-5:plant_pos+=outward.normalized()*.10
rotated=hand_local@np.array(plant_q.to_matrix()).T
plant_pos.z=floor_z-float(rotated[:,2].min())+.008
make_pose('Airborne',.3,1.1);air=local_snapshot()

def plant_hand(weight):
 if weight<=0:return 0.
 worlds=snapshot();old={n:m.copy() for n,m in worlds.items()};locals_now={n:old[parents[n]].inverted()@old[n] if parents[n] else old[n] for n in ordered}
 shoulder=old[upper].translation.copy();target=plant_pos.copy()
 ratio=(target-shoulder).length/(length_a+length_b)
 weight*=1.-smooth((ratio-.985)/.095)
 if weight<=0:return 0.
 goal=old[wrist].translation.lerp(target,weight)
 axis=(goal-shoulder).normalized();distance=min((goal-shoulder).length,(length_a+length_b)*.995)
 pole=old[lower].translation-shoulder;pole-=axis*pole.dot(axis)
 if pole.length<1e-5:pole=Vector((1,0,0))-axis*axis.x
 pole.normalize();along=(length_a**2-length_b**2+distance**2)/(2*distance)
 elbow=shoulder+axis*along+pole*math.sqrt(max(0.,length_a**2-along**2))
 goal=shoulder+axis*distance
 for n,a,b,oa,ob in ((upper,shoulder,elbow,old[upper].translation,old[lower].translation),(lower,elbow,goal,old[lower].translation,old[wrist].translation)):
  q=(ob-oa).normalized().rotation_difference((b-a).normalized())@old[n].to_quaternion()
  worlds[n]=Matrix.LocRotScale(a,q,old[n].to_scale())
 worlds[wrist]=Matrix.LocRotScale(goal,old[wrist].to_quaternion().slerp(plant_q,weight),old[wrist].to_scale())
 for n in arm:
  if n not in (upper,lower,wrist):worlds[n]=worlds[parents[n]]@locals_now[n]
 apply_worlds(worlds)
 return weight

def plant_feet(weight):
 if weight<=0:return
 worlds=snapshot();old={n:m.copy() for n,m in worlds.items()}
 locals_now={n:old[parents[n]].inverted()@old[n] if parents[n] else old[n] for n in ordered}
 for side,u,k,f in chains:
  hip=old[u].translation.copy();goal=old[f].translation.lerp(base_feet[side],weight)
  a=(neutral[k].translation-neutral[u].translation).length;b=(neutral[f].translation-neutral[k].translation).length
  axis=(goal-hip).normalized();distance=max(.01,min((goal-hip).length,(a+b)*.995))
  pole=old[k].translation-hip;pole-=axis*pole.dot(axis)
  if pole.length<1e-5:pole=Vector((0,-1,0))-axis*(-axis.y)
  pole.normalize();along=(a*a-b*b+distance*distance)/(2*distance)
  knee=hip+axis*along+pole*math.sqrt(max(0.,a*a-along*along));goal=hip+axis*distance
  for n,start,end,old_start,old_end in ((u,hip,knee,old[u].translation,old[k].translation),(k,knee,goal,old[k].translation,old[f].translation)):
   q=(old_end-old_start).normalized().rotation_difference((end-start).normalized())@old[n].to_quaternion()
   worlds[n]=Matrix.LocRotScale(start,q,old[n].to_scale())
  worlds[f]=Matrix.LocRotScale(goal,old[f].to_quaternion().slerp(neutral[f].to_quaternion(),weight),old[f].to_scale())
  for n in ordered:
   if n not in (u,k,f) and below(n,u):worlds[n]=worlds[parents[n]]@locals_now[n]
 apply_worlds(worlds)

def pose(role,t,duration):
 make_pose(role,t,duration)
 if role=='Landing' and t<.22:
  f=smooth(t/.22)
  for n,pb in ((n,rig.pose.bones[n]) for n in ordered):
   target=pb.matrix_basis;start=air[n]
   pb.matrix_basis=Matrix.LocRotScale(start.translation.lerp(target.translation,f),start.to_quaternion().slerp(target.to_quaternion(),f),start.to_scale().lerp(target.to_scale(),f))
  ground()
 if role=='GetUp':
  bpy.context.view_layer.update();plant_feet(smooth((t-.45)/.90));ground()
 # Settle onto the torso and palm; support the early recovery before release.
 weight=smooth((t-.28)/.49) if role=='Landing' else 1.-smooth((t-1.15)/.95)
 bpy.context.view_layer.update();applied=plant_hand(weight);ground()
 return applied

contracts=[];samples=[];endpoints={}
for role,duration in [('Landing',.9),('GetUp',3.2)]:
 action=bpy.data.actions.new('A_M66_'+role+'_V21');action.use_fake_user=True;rig.animation_data.action=action
 previous={};frames=round(duration*60);scene.render.fps=60;scene.frame_start=0;scene.frame_end=frames
 for frame in range(frames+1):
  scene.frame_set(frame);t=frame/60.;weight=pose(role,t,duration)
  for pb in rig.pose.bones:
   q=pb.rotation_quaternion.copy()
   if pb.name in previous and q.dot(previous[pb.name])<0:q.negate()
   pb.rotation_quaternion=q;previous[pb.name]=q
   for channel in ('location','rotation_quaternion','scale'):pb.keyframe_insert(channel,frame=frame,group=pb.name)
  if frame%6==0 or frame==frames:
   a=surface();samples.append(dict(role=role,seconds=t,surface_gap_cm=float((a[:,2].min()-floor_z)*100),body_gap_cm=float((a[body_ids,2].min()-floor_z)*100),hand_gap_cm=float((a[hand_ids,2].min()-floor_z)*100),feet_gap_cm=float((a[leg_ids,2].min()-floor_z)*100),palm_support_weight=weight))
  if frame in (0,frames):endpoints[role+str(frame)]={n:list(rig.pose.bones[n].matrix_basis.translation)+list(rig.pose.bones[n].rotation_quaternion) for n in ordered}
 for layer in action.layers:
  for strip in layer.strips:
   for curve in strip.channelbag(action.slots[0]).fcurves:
    for key in curve.keyframe_points:key.interpolation='LINEAR'
 scene.frame_set(0);bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);mesh.select_set(True);bpy.context.view_layer.objects.active=rig
 path=ROOT/'Export'/('A_M66_'+role+'_V21.fbx')
 bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'ARMATURE','MESH'},add_leaf_bones=False,use_armature_deform_only=False,
  bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_use_all_bones=True,bake_anim_force_startend_keying=True,
  bake_anim_step=1.,bake_anim_simplify_factor=0.,use_mesh_modifiers=False,axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',mesh_smooth_type='OFF',path_mode='AUTO')
 contracts.append(dict(role=role,action=action.name,fbx=str(path),seconds=duration,frames=frames+1,fps=60,loop=False))
 print('M66_RECOVERY_EXPORTED',role,flush=True)
rig.animation_data.action=bpy.data.actions['A_M66_GetUp_V21']
if rig.animation_data.action.slots:rig.animation_data.action_slot=rig.animation_data.action.slots[0]
scene.frame_start=0;scene.frame_end=192;scene.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authoring/M66_recovery_v21.blend'))
report=dict(clips=contracts,source_mesh=str(BASE/'FurnaceBreathV17/Authoring/M66_furnace_breath_v17.blend'),samples=samples,
 bone_count=len(ordered),mesh_and_weights_changed=False,gameplay_timing_changed=False,root_motion=False,
 palm_target=list(plant_pos),endpoints=endpoints,game_tested=False)
(ROOT/'Records/animation_manifest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('M66_RECOVERY_AUTHORED',len(contracts),flush=True)
