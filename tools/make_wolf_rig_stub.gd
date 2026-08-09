extends SceneTree
## 临时占位：用原静态 GLB 生成 black_wolf_rigged.scn，让游戏在黑狼骨架烘焙完成前可启动。
## 动画线 bake_wolf_rig.gd 跑通后直接覆盖此文件即可，无副作用。

func _initialize() -> void:
	var root := Node3D.new()
	root.name = "WolfRigStub"
	root.scale = Vector3.ONE * 1.9
	var glb: Node3D = load("res://assets/models/black_wolf_trellis.glb").instantiate()
	root.add_child(glb)
	glb.owner = root
	var packed := PackedScene.new()
	var err := packed.pack(root)
	if err != OK:
		push_error("pack 失败: %s" % err)
		quit(1)
		return
	err = ResourceSaver.save(packed, "res://assets/models/black_wolf_rigged.scn")
	print("STUB save err=", err, " path=res://assets/models/black_wolf_rigged.scn")
	quit(0 if err == OK else 1)
