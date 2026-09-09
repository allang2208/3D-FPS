extends SceneTree
const OUT="E:/无尽轮回/3d/free-hands-20260908/"
func _initialize():call_deferred("run")
func transform(rows)->Transform3D:
 return Transform3D(Basis(Vector3(rows[0][0],rows[1][0],rows[2][0]),Vector3(rows[0][1],rows[1][1],rows[2][1]),Vector3(rows[0][2],rows[1][2],rows[2][2])),Vector3(rows[0][3],rows[1][3],rows[2][3]))
func portable(material:Material)->Material:
 var copy=material.duplicate(true)
 for property in copy.get_property_list():
  if not property.usage&PROPERTY_USAGE_STORAGE:continue
  var value=copy.get(property.name)
  if value is Texture2D:copy.set(property.name,ImageTexture.create_from_image(value.get_image()))
 return copy
func run():
 root.get_node("HUD").set_process(false)
 var profiles=JSON.parse_string(FileAccess.get_file_as_string(OUT+"hand-rigs.json"))
 DirAccess.make_dir_recursive_absolute(OUT+"prepared-v3")
 var weapons=OS.get_cmdline_user_args()
 if weapons.is_empty():weapons=PackedStringArray(profiles.keys())
 for weapon in weapons:
  var profile=profiles[weapon]
  var document=GLTFDocument.new();var state=GLTFState.new();state.use_named_skin_binds=true
  assert(document.append_from_file(OUT+"hands-"+weapon+"-v3.glb",state)==OK)
  var donor=document.generate_scene(state);var src:MeshInstance3D=donor.find_child("SK_FP_CH_Default_Cubic",true,false)
  var m=load("res://scenes/weapons/"+weapon+".tscn").instantiate();m.fitted_hands_enabled=false;root.add_child(m);m.advance_pose(0,0)
  var dst:MeshInstance3D=m.find_child(profile.mesh,true,false);var result=ArrayMesh.new()
  var hands=PackedInt32Array()
  var target_rig:Skeleton3D=dst.get_node(dst.skeleton)
  var wrists=[target_rig.find_bone(profile.bind_names[int(profile.mapping.hand_l)]),target_rig.find_bone(profile.bind_names[int(profile.mapping.hand_r)])]
  for j in dst.skin.get_bind_count():
   var ancestor=target_rig.find_bone(profile.bind_names[j])
   while ancestor>=0:
    if ancestor in wrists:hands.append(j);break
    ancestor=target_rig.get_bone_parent(ancestor)
  var retained=0
  for si in dst.mesh.get_surface_count():
   var a=dst.mesh.surface_get_arrays(si);var bs=a[Mesh.ARRAY_BONES];var ws=a[Mesh.ARRAY_WEIGHTS];var old=a[Mesh.ARRAY_INDEX];var indices=PackedInt32Array()
   if old==null or old.is_empty():old=PackedInt32Array(range(a[Mesh.ARRAY_VERTEX].size()))
   for k in range(0,old.size(),3):
    var remove=true
    for v in [old[k],old[k+1],old[k+2]]:
     var mass=0.0
     for j in 4:
      if bs[v*4+j] in hands:mass+=ws[v*4+j]
     if mass<=.5:remove=false
    if not remove:indices.append_array(PackedInt32Array([old[k],old[k+1],old[k+2]]))
   if indices.is_empty():continue
   a[Mesh.ARRAY_INDEX]=indices;var surface=result.get_surface_count();result.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,a);result.surface_set_material(surface,portable(dst.get_active_material(si)));retained+=indices.size()/3
  var inverse=transform(profile.inverse_space);var remap={}
  for j in src.skin.get_bind_count():
   var name_=str(src.skin.get_bind_name(j));if name_.is_empty():name_=src.get_node(src.skeleton).get_bone_name(src.skin.get_bind_bone(j))
   remap[j]=int(profile.mapping.get(name_,-1))
  # Surface zero is the template's retained sleeves, never transplanted.
  for si in range(1,src.mesh.get_surface_count()):
   var a=src.mesh.surface_get_arrays(si);var ps=a[Mesh.ARRAY_VERTEX];var ns=a[Mesh.ARRAY_NORMAL];var bs=a[Mesh.ARRAY_BONES];var ws=a[Mesh.ARRAY_WEIGHTS]
   for v in ps.size():
    ps[v]=inverse*ps[v];ns[v]=(inverse.basis.inverse().transposed()*ns[v]).normalized()
    for j in 4:
     var b=remap[bs[v*4+j]];assert(b>=0 or ws[v*4+j]<.00001,"unmapped donor weight")
     bs[v*4+j]=maxi(0,b)
   a[Mesh.ARRAY_VERTEX]=ps;a[Mesh.ARRAY_NORMAL]=ns;a[Mesh.ARRAY_BONES]=bs;a[Mesh.ARRAY_TANGENT]=null
   var temp=ArrayMesh.new();temp.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES,a)
   var st=SurfaceTool.new();st.create_from(temp,0);st.generate_tangents();st.index();var surface=result.get_surface_count();st.commit(result);result.surface_set_material(surface,src.get_active_material(si))
  result.set_meta("preserve_fitted_hand",true);result.set_meta("target_mesh",profile.mesh);result.set_meta("target_bind_names",profile.bind_names);result.set_meta("retained_sleeve_triangles",retained);result.set_meta("replaced_hand_binds",hands)
  assert(ResourceSaver.save(result,OUT+"prepared-v3/"+weapon+".res")==OK)
  print("ASSEMBLED_HANDS ",weapon," surfaces=",result.get_surface_count()," sleeve_triangles=",retained)
  donor.free();m.queue_free();await process_frame
 print("HANDS_ASSEMBLY_COMPLETE");quit()
