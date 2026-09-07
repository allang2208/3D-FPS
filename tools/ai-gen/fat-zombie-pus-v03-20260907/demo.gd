extends Node3D
class Walker extends CharacterBody3D:
 var hp:=100
 var is_dead:=false
 var caption:Label3D
 func _ready()->void:
  set_meta("faction","player")
  collision_layer=4
  var c:=CollisionShape3D.new()
  var shape:=CapsuleShape3D.new()
  shape.radius=.15;shape.height=.6
  c.shape=shape;c.position.y=.3;add_child(c)
  var mesh:=MeshInstance3D.new()
  var sphere:=SphereMesh.new()
  sphere.radius=.15;sphere.height=.3
  mesh.mesh=sphere;mesh.position.y=.2
  var mat:=StandardMaterial3D.new();mat.albedo_color=Color(.15,.5,.9)
  mesh.material_override=mat;add_child(mesh)
  caption=Label3D.new();caption.position.y=.8;caption.font_size=48;add_child(caption)
 func take_damage(d:int,_type:String,_src:Node3D)->void:
  hp=maxi(0,hp-d);is_dead=hp==0
 func _physics_process(delta:float)->void:
  var dir:=Vector3.ZERO
  if Input.is_physical_key_pressed(KEY_W):dir.z-=1
  if Input.is_physical_key_pressed(KEY_S):dir.z+=1
  if Input.is_physical_key_pressed(KEY_A):dir.x-=1
  if Input.is_physical_key_pressed(KEY_D):dir.x+=1
  if not is_dead:position+=dir.normalized()*2*delta
  caption.text="HP %d"%hp
var walker:Walker
func _ready()->void:
 var env:=WorldEnvironment.new()
 env.environment=Environment.new()
 env.environment.background_mode=Environment.BG_COLOR
 env.environment.background_color=Color(.09,.11,.14)
 env.environment.ambient_light_source=Environment.AMBIENT_SOURCE_COLOR
 env.environment.ambient_light_color=Color(.8,.88,1)
 env.environment.ambient_light_energy=.7
 add_child(env)
 var light:=DirectionalLight3D.new()
 add_child(light)
 light.rotation_degrees=Vector3(-50,-35,0)
 light.light_energy=1.6
 light.shadow_enabled=true
 light.shadow_bias=.12
 light.shadow_normal_bias=2.0
 var ground:=MeshInstance3D.new()
 ground.mesh=PlaneMesh.new()
 ground.mesh.size=Vector2(30,30)
 var material:=StandardMaterial3D.new()
 material.albedo_color=Color(.20,.23,.26)
 ground.material_override=material
 add_child(ground)
 var camera:=Camera3D.new()
 add_child(camera)
 camera.position=Vector3(0,4.5,6.5)
 camera.look_at(Vector3(0,.5,0))
 camera.projection=Camera3D.PROJECTION_ORTHOGONAL
 camera.size=4.9
 camera.current=true

 var floor_body:=StaticBody3D.new()
 var floor_collision:=CollisionShape3D.new()
 var box:=BoxShape3D.new()
 box.size=Vector3(30,.2,30)
 floor_collision.shape=box
 floor_collision.position.y=-.1
 floor_body.add_child(floor_collision)
 add_child(floor_body)
 walker=Walker.new();add_child(walker);walker.position=Vector3(0,0,2)
 var label:=Label.new()
 label.text="WASD: move into puddles   R: new random death / reset HP"
 label.position=Vector2(20,20);add_child(label)
 spawn_batch()
func spawn_batch()->void:
 walker.hp=100;walker.is_dead=false;walker.position=Vector3(0,0,2)
 for n in get_children():
  if n.get_script()==load("res://death_sequence.gd") or n.get_script()==load("res://pus_pool.gd"):n.queue_free()
 for i in 3:
  var seq:Node3D=load("res://death_sequence.gd").new()
  add_child(seq);seq.position.x=(i-1)*2.8;seq.rotation.y=.4
  seq.begin_death()
func _unhandled_key_input(event:InputEvent)->void:
 if event is InputEventKey and event.pressed and not event.echo and event.physical_keycode==KEY_R:spawn_batch()
