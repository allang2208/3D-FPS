extends "res://scripts/portal.gd"
## 双向试验入口；识别试验玩家，返回前保存独立世界。
var transitioning := false

func _on_body_entered(body: Node3D) -> void:
	if transitioning or not body is CharacterBody3D or target_scene.is_empty():
		return
	var scene := get_tree().current_scene
	if body.name != "Player" and not (scene != null and scene.get("player") == body):
		return
	if scene != null and scene.has_method("player_bounds"):
		var result: Error = scene.world.save_world(scene.save_path)
		if result != OK:
			scene.status.text = "保存失败，暂未离开：" + error_string(result)
			return
		scene.save_delay = -1.0
	transitioning = true
	# 离开物理回调后再进入加载流程。
	load("res://ui/loading_screen.gd").load_scene.call_deferred(target_scene)
