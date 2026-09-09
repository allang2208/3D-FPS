extends SceneTree
func _initialize():call_deferred("run")
func run():
 root.get_node("HUD").set_process(false)
 var vertices=0
 for weapon in ["infima_ar","akm_classic","hk416","qbz191","m16","infima_handgun"]:
  var m=load("res://scenes/weapons/"+weapon+".tscn").instantiate();root.add_child(m)
  var mesh_path="res://assets/models/player_hands/free_fitted_v1/"+weapon+".res"
  assert(ResourceLoader.get_dependencies(mesh_path).is_empty(),weapon+" nonportable hand resource")
  var mesh=load(mesh_path) as ArrayMesh
  var n:MeshInstance3D=m.find_child(str(mesh.get_meta("target_mesh")),true,false)
  assert(n.mesh==mesh and n.get_meta("fitted_hands_version","")=="free_fitted_v1")
  var hand_binds:PackedInt32Array=mesh.get_meta("replaced_hand_binds")
  for surface in mesh.get_surface_count():
   var material=mesh.surface_get_material(surface) as StandardMaterial3D
   assert(material!=null,weapon+" missing material")
   if surface in [0,1,2]:assert(material.albedo_texture!=null and material.albedo_texture.get_width()>0,weapon+" missing embedded texture")
   var a=mesh.surface_get_arrays(surface);var points=a[Mesh.ARRAY_VERTEX];var bones=a[Mesh.ARRAY_BONES];var weights=a[Mesh.ARRAY_WEIGHTS]
   for v in points.size():
    assert(points[v].is_finite());var total=0.0
    for k in 4:
     assert(bones[v*4+k]>=0 and bones[v*4+k]<n.skin.get_bind_count())
     assert(is_finite(weights[v*4+k]) and weights[v*4+k]>=0);total+=weights[v*4+k]
    assert(absf(total-1.0)<.0002,weapon+" unnormalized skin")
   if surface==0:
    var indices=a[Mesh.ARRAY_INDEX]
    for tri in range(0,indices.size(),3):
     var original_hand=true
     for corner in 3:
      var v=indices[tri+corner];var hand_weight=0.0
      for k in 4:
       if bones[v*4+k] in hand_binds:hand_weight+=weights[v*4+k]
      if hand_weight<=.5:original_hand=false
     assert(not original_hand,weapon+" old hand face remains")
   else:vertices+=points.size()
  for grip in ([false] if weapon=="infima_handgun" else [true,"vertical","handstop","canted",false]):
   m.apply_gunsmith_parts({} if not grip else {"underbarrel":grip,"magazine":"large_drum"});m.advance_pose(0,0)
   assert(n.mesh==mesh,weapon+" attachment replaced fitted hands")
  print("FITTED_HANDS_OK ",weapon," bind order, embedded textures, weights, old hand removal, attachment retention")
  m.queue_free();await process_frame
 print("FITTED_HANDS_COMPLETE weapons=6 checked_hand_vertices=",vertices);quit()
