extends SceneTree
const OUT="E:/无尽轮回/3d/free-hands-20260908/"
func _initialize():call_deferred("run")
func run():
 root.get_node("HUD").set_process(false);DirAccess.make_dir_recursive_absolute(OUT+"editable-v6")
 var profiles=JSON.parse_string(FileAccess.get_file_as_string(OUT+"hand-rigs.json"))
 for weapon in profiles:
  var wrapper=load("res://scenes/weapons/"+weapon+".tscn").instantiate()
  var source=wrapper.model_resource.instantiate();root.add_child(source)
  var mesh:MeshInstance3D=source.find_child(profiles[weapon].mesh,true,false)
  mesh.mesh=load(OUT+"prepared-v3/"+weapon+".res")
  var document=GLTFDocument.new();var state=GLTFState.new();state.use_named_skin_binds=true
  assert(document.append_from_scene(source,state)==OK)
  assert(document.write_to_filesystem(state,OUT+"editable-v6/"+weapon+".glb")==OK)
  print("EDITABLE_EXPORTED ",weapon)
  source.queue_free();wrapper.free();await process_frame
 print("EDITABLE_HANDS_COMPLETE");quit()
