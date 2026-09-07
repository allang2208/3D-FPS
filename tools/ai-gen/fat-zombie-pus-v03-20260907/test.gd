extends SceneTree
class Target extends CharacterBody3D:
 var hp:=100
 var is_dead:=false
 func take_damage(d:int,_type:String,_src:Node3D)->void:hp-=d
func _initialize()->void:call_deferred("run")
func target(parent:Node,faction:String)->Target:
 var b:=Target.new()
 b.set_meta("faction",faction)
 b.collision_layer=4
 var c:=CollisionShape3D.new()
 var shape:=CapsuleShape3D.new()
 shape.radius=.15;shape.height=1.6
 c.shape=shape;c.position.y=.8
 b.add_child(c);parent.add_child(b)
 return b
func run()->void:
 var world:=Node3D.new()
 root.add_child(world);current_scene=world
 var floor:=StaticBody3D.new()
 var floor_shape:=CollisionShape3D.new()
 var box:=BoxShape3D.new();box.size=Vector3(30,.2,30)
 floor_shape.shape=box;floor_shape.position.y=-.1
 floor.add_child(floor_shape);world.add_child(floor)
 await physics_frame
 var seq:Node3D=load("res://death_sequence.gd").new()
 world.add_child(seq);seq.set_physics_process(false)
 var pools:Array=[]
 seq.puddle_spawned.connect(func(p):pools.append(p))
 seq.begin_death();seq.begin_death()
 seq.advance(2.49);assert(pools.is_empty() and seq.model.visible)
 seq.advance(.02);assert(pools.size()==1 and not seq.model.visible)
 seq.advance(10);assert(pools.size()==1)
 var p:Area3D=pools[0]
 for tick in 100:
  await physics_frame
  if p.surface_ready:break
 assert(p.surface_ready)
 p.set_physics_process(false)
 p.age=0
 p.set_visual_age(.5)
 var enemy:=target(world,"player")
 var ally:=target(world,"monster")
 var neutral:=target(world,"neutral")
 await physics_frame
 await physics_frame
 assert(p.get_overlapping_bodies().has(enemy),"real Area3D overlap")
 p.advance(.49,p.get_overlapping_bodies());assert(enemy.hp==100)
 p.advance(.01,p.get_overlapping_bodies());assert(enemy.hp==92 and ally.hp==100 and neutral.hp==100)
 enemy.position=Vector3(1.5,0,1.5)
 await physics_frame
 await physics_frame
 p.advance(.5,p.get_overlapping_bodies());assert(enemy.hp==92)
 enemy.position=Vector3(0,1,0)
 p.advance(.5,[enemy]);assert(enemy.hp==92,"above puddle")
 enemy.position=Vector3.ZERO
 p.advance(1.0,[enemy]);assert(enemy.hp==76,"low frame interval crossing")
 p.age=5.6;p.advance(.3,[enemy]);assert(enemy.hp==76,"no damage while fading")
 p.advance(.2,[enemy]);assert(p.is_queued_for_deletion())
 var a:Area3D=load("res://pus_pool.gd").new()
 var b:Area3D=load("res://pus_pool.gd").new()
 a.random_seed=17;b.random_seed=81
 world.add_child(a);world.add_child(b)
 assert(a.polygon!=b.polygon,"random silhouettes")
 print("PUS_TEST_COMPLETE sequence_once=true faction=true overlap=true exit=true height=true low_fps=true expiry=true random=true")
 quit()
