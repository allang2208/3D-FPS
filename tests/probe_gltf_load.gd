extends SceneTree

var _probe_path := ""

func _init() -> void:
	_probe_path = OS.get_environment("GLB_PATH")
	if _probe_path == "":
		_probe_path = "res://assets/models/tacz_ak47/ak47_replace.glb"
	# 看门狗：30 秒强制退出，避免解析挂死
	var timer := Timer.new()
	timer.wait_time = 30.0
	timer.one_shot = true
	timer.autostart = true
	timer.timeout.connect(func() -> void:
		print("TIMEOUT parsing ", _probe_path)
		quit(2)
	)
	root.add_child(timer)
	var f := FileAccess.open(_probe_path, FileAccess.READ)
	if f == null:
		print("CANNOT OPEN ", _probe_path, " err=", FileAccess.get_open_error())
		quit(1)
		return
	var bytes := f.get_buffer(f.get_length())
	f.close()
	var doc := GLTFDocument.new()
	var state := GLTFState.new()
	var err := doc.append_from_buffer(bytes, "", state)
	print("GLB=", _probe_path, " err=", err)
	if err != OK:
		print("LOAD FAILED with err=", err)
		quit(1)
	else:
		var scene := doc.generate_scene(state)
		print("GENERATE_SCENE=", scene)
		if scene == null:
			print("GENERATE FAILED")
			quit(3)
		else:
			print("GENERATE OK, nodes=", scene.get_child_count())
			# 复刻编辑器导入器：用文件 + 全 flags
			for flags in [0, 1, 2, 4, 8, 16, 1 | 2, 1 | 2 | 16, 1 | 2 | 8, 1 | 2 | 8 | 16, 1 | 2 | 8 | 16 | 64]:
				var s2 := GLTFState.new()
				var d2 := GLTFDocument.new()
				var e2 := d2.append_from_file(_probe_path, s2, flags)
				var sc2: Node = null
				if e2 == OK:
					sc2 = d2.generate_scene(s2)
				print("FLAGS=", flags, " err=", e2, " scene=", sc2)
			quit(0)
