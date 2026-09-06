extends SceneTree
func _initialize():call_deferred("run")
func run():
 var world=load("res://scenes/foreman_demo.tscn").instantiate()
 root.add_child(world);current_scene=world
 await process_frame
 var old=world.get_node("ForemanZombie");var tr=old.transform;old.free()
 var enemy=load("res://scenes/enemies/foreman_zombie.tscn").instantiate()
 enemy.get_node("Model").free()
 var model=load("res://tools/ai-gen/foreman-downstroke-v07-20260906/foreman-downstroke-v07.glb").instantiate();model.name="Model";enemy.add_child(model);enemy.transform=tr;world.add_child(enemy);enemy.set_physics_process(false)
 for clip in ["Idle","Attack","Death"]:
  enemy._sync_pose(clip,1.4 if clip=="Death" else .59625 if clip=="Attack" else 0.)
  await process_frame
  var sk=enemy._skeleton
  var mi=enemy._model.find_child("ForemanBody",true,false)
  var arr=mi.mesh.surface_get_arrays(0)
  var verts=arr[Mesh.ARRAY_VERTEX];var bones=arr[Mesh.ARRAY_BONES];var weights=arr[Mesh.ARRAY_WEIGHTS]
  var low=INF
  var transforms=[]
  for i in mi.skin.get_bind_count():
   var bone=sk.find_bone(mi.skin.get_bind_name(i))
   if bone<0:bone=mi.skin.get_bind_bone(i)
   transforms.append(sk.get_bone_global_pose(bone)*mi.skin.get_bind_pose(i))
  for v in verts.size():
   var point=Vector3.ZERO
   for k in range(4):point+=(transforms[bones[v*4+k]]*verts[v])*weights[v*4+k]
   low=minf(low,sk.to_global(point).y)
  assert(low>-.006 and low<.02,"Godot deformed body stays on ground")
  print("MESH_LOW ",clip," ",low)
 world.queue_free();await process_frame;quit()
