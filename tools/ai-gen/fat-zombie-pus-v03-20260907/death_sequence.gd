extends Node3D
signal puddle_spawned(puddle: Area3D)
@export var corpse_hold := 1.0
@export var puddle_seed := -1
var elapsed := 0.0
var model: Node3D
var player: AnimationPlayer
var spawned := false
var started := false
func _ready() -> void:
 model=load("res://model.glb").instantiate()
 add_child(model)
 player=model.find_child("AnimationPlayer",true,false)
 player.get_animation("Death").loop_mode=Animation.LOOP_NONE
 player.play("Idle")
func begin_death() -> void:
 if started:return
 started=true
 elapsed=0
 player.play("Death")
 player.pause()
func _physics_process(delta: float) -> void:
 if started:advance(delta)
func advance(delta: float) -> void:
 if not started or spawned:return
 elapsed+=delta
 player.seek(minf(elapsed,1.5),true)
 if elapsed>=1.5+corpse_hold:
  # Hide corpse first, then spawn one independent hazard at the saved death position.
  model.hide()
  spawned=true
  var puddle:Area3D=load("res://pus_pool.gd").new()
  puddle.random_seed=puddle_seed
  puddle.position=get_parent().to_local(global_position)
  get_parent().add_child(puddle)
  puddle_spawned.emit(puddle)
