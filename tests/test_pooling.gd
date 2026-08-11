extends SceneTree
## 对象池回归：连射/抛壳后实例数封顶、回收后复用同一实例、信号连接不残留
## 运行： $godot --headless --path 'E:\3d\3-dfps' --script res://tests/test_pooling.gd

const ProjectileScript := preload("res://scripts/projectile.gd")
const CasingScript := preload("res://scripts/casing.gd")

var _frames := 0
var _fails: Array[String] = []
var _pool: ProjectilePool
var _cpool: CasingPool
var _probe: Projectile

func _process(_delta: float) -> bool:
	_frames += 1
	if _frames == 1:
		# 连射 40 发（超过池容量 32）+ 抛 40 颗壳（超过 20）
		for i in 40:
			ProjectileScript.fire(root, Vector3(0, 1, 0) + Vector3(i * 0.1, 0, 0), Vector3(0, 0, -1), 90.0, 25, 0.0)
			CasingScript.spawn(root, Vector3(0, 1, 0), Vector3.RIGHT)
		_pool = ProjectilePool.for_scene(root)
		_cpool = CasingPool.for_scene(root)
	if _frames == 3:
		# 池实例数不得超过容量（超出部分走"回收最早一发"复用），总实例数=容量（不增长）
		if _pool._active.size() > ProjectilePool.POOL_SIZE:
			_fails.append("projectile active overflow: %d" % _pool._active.size())
		if _cpool._active.size() > CasingPool.POOL_SIZE:
			_fails.append("casing active overflow: %d" % _cpool._active.size())
		if _pool._available.size() + _pool._active.size() != ProjectilePool.POOL_SIZE:
			_fails.append("projectile total != pool size: %d+%d" % [_pool._available.size(), _pool._active.size()])
		if _cpool._available.size() + _cpool._active.size() != CasingPool.POOL_SIZE:
			_fails.append("casing total != pool size: %d+%d" % [_cpool._available.size(), _cpool._active.size()])
		# 回收：断连 + 回到可用区
		_probe = _pool._active[0]
		_probe.hit_enemy.connect(_on_hit)
		_probe._release()
		if _probe.get_signal_connection_list("hit_enemy").size() != 0:
			_fails.append("signal not disconnected on release")
		if _pool._active.size() != ProjectilePool.POOL_SIZE - 1 or _pool._available.size() != 1:
			_fails.append("release counts wrong: %d/%d" % [_pool._active.size(), _pool._available.size()])
		# 复用：同一实例回到活跃区，旧连接清空后重新接上只留 1 条
		var reused := _pool.acquire(Vector3.ZERO, Vector3.FORWARD, 90.0, 25, 0.0)
		if reused != _probe:
			_fails.append("pool did not reuse freed instance")
		if reused.get_signal_connection_list("hit_enemy").size() != 0:
			_fails.append("signal leftover after reuse")
		reused.hit_enemy.connect(_on_hit)
		if reused.get_signal_connection_list("hit_enemy").size() != 1:
			_fails.append("reconnect count != 1")
		# 弹壳池同一套机制
		var c0: Casing = _cpool._active[0]
		c0._release()
		var c1 := _cpool.acquire(Vector3.ZERO, Vector3.UP, Vector3.ZERO, 1.0)
		if c1 != c0:
			_fails.append("casing pool did not reuse freed instance")
		for f in _fails:
			print("FAIL ", f)
		print("TEST pooling=", _fails.is_empty())
		quit(0 if _fails.is_empty() else 1)
		return false
	return false

func _on_hit(_headshot: bool) -> void:
	pass
