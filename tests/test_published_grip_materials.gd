extends SceneTree
class Profile:
 var upper:int
 var lower:int
 var hand:int
 var fingers={}
 var separate_hand=false
 var return_times=Vector2(1.1,1.2)
 var equip_return=Vector2(1.02,1.38)
func _initialize():call_deferred("run")
func run():
 var rig=Skeleton3D.new();root.add_child(rig)
 for name in ["root","upperarm_l","lowerarm_l","hand_l"]:rig.add_bone(name)
 for i in range(1,4):rig.set_bone_parent(i,i-1)
 rig.set_bone_pose_position(1,Vector3(0,.3,0));rig.set_bone_pose_position(2,Vector3(0,-.18,0));rig.set_bone_pose_position(3,Vector3(0,-.18,0))
 var profile=Profile.new();profile.upper=1;profile.lower=2;profile.hand=3
 for f in ["index","middle","ring","pinky","thumb"]:
  profile.fingers[f]=[]
  for j in 3:
   var b=rig.get_bone_count();rig.add_bone(f+str(j));rig.set_bone_parent(b,3 if j==0 else b-1);rig.set_bone_pose_position(b,Vector3(.02,0,.01 if j==0 else 0));profile.fingers[f].append(b)
 var holder=BoneAttachment3D.new();holder.bone_name="root";rig.add_child(holder)
 var part=Node3D.new();holder.add_child(part);part.set_meta("vertical_grip",true)
 var target=Marker3D.new();target.name="HandTarget";target.position=Vector3(.05,.02,0);part.add_child(target)
 var baseline=[]
 for b in rig.get_bone_count():baseline.append(rig.get_bone_pose(b))
 var pose=preload("res://scripts/foregrip_pose.gd").new()
 for speed in [1.0,1.5]:
  pose.begin("equip_charge",1.9,speed)
  for frame in 250:
   pose.restore(rig);pose.advance(1.0/120);pose.apply(rig,part,profile)
   if pose.elapsed<1.02:assert(pose.weight==0)
   if pose.elapsed>=1.38:assert(rig.get_bone_global_pose(3).origin.distance_to(target.position)<.001)
   for b in rig.get_bone_count():assert(rig.get_bone_global_pose(b).origin.is_finite())
  pose.restore(rig)
  for b in rig.get_bone_count():assert(rig.get_bone_pose(b).is_equal_approx(baseline[b]))
 var model=Node3D.new();root.add_child(model)
 var receiver=MeshInstance3D.new();receiver.name="Upper_reciever_low_003";receiver.mesh=BoxMesh.new();model.add_child(receiver)
 var coating=ShaderMaterial.new();coating.shader=load("res://assets/models/hk416/materials_v3/coating.gdshader")
 var pixels=Image.create(4,4,false,Image.FORMAT_RGB8);pixels.fill(Color(.035,.035,.035));var texture=ImageTexture.create_from_image(pixels)
 coating.set_shader_parameter("coating_albedo",texture);coating.set_meta("rifle_clean_profile",{"color":Color(.14,.145,.15),"roughness":.36,"metallic":.38,"specular":.42});receiver.material_override=coating
 var attachment=Node3D.new();model.add_child(attachment)
 var metal=MeshInstance3D.new();metal.mesh=BoxMesh.new();metal.position.x=.2;attachment.add_child(metal)
 var finish=ShaderMaterial.new();finish.shader=load("res://assets/materials/weapon_finish.gdshader");finish.set_shader_parameter("finish_texture",texture);finish.set_shader_parameter("surface_metallic",.3);finish.set_shader_parameter("surface_roughness",.6);finish.set_shader_parameter("surface_specular",.25);finish.set_shader_parameter("finish_strength",.22);finish.set_shader_parameter("tint",Color(.22,.23,.24));metal.material_override=finish
 var glass=MeshInstance3D.new();glass.mesh=BoxMesh.new();glass.material_override=StandardMaterial3D.new();attachment.add_child(glass);var protected=glass.material_override
 var matcher=preload("res://scripts/attachment_material_match.gd")
 matcher.apply(model,{"part":attachment});var color=metal.material_override.get_shader_parameter("tint")
 assert(metal.material_override.get_shader_parameter("finish_strength")<=.0251);assert(glass.material_override==protected)
 matcher.apply(model,{"part":attachment});assert(metal.material_override.get_shader_parameter("tint")==color)
 var camera=Camera3D.new();root.add_child(camera);camera.position=Vector3(0,0,3);camera.make_current()
 var light=DirectionalLight3D.new();root.add_child(light)
 for frame in 8:await process_frame
 if DisplayServer.get_name()!="headless":await RenderingServer.frame_post_draw
 print("PASS standalone grip return/restore/speed; clean coating/matching/idempotence/protected surfaces; shaders rendered")
 rig.free();model.free();camera.free();light.free();quit()
