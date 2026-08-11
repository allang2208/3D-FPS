class_name ProjectilePool
extends Node3D
## 子弹对象池：预分配 N 发，命中/寿命结束回收复用，消除每发 new/free 抖动。
## 池节点挂在当前场景根下（场景切换自动释放并从静态表清除）。
## 使用方无需感知：ProjectileScript.fire(...) 内部自动走池。

const ProjectileScript := preload("res://scripts/projectile.gd")
const POOL_SIZE := 32

static var _pools := {}  # scene_root -> ProjectilePool

static func for_scene(scene_root: Node) -> ProjectilePool:
	var key: Object = scene_root
	var pool: ProjectilePool = _pools.get(key)
	if pool == null or not is_instance_valid(pool):
		pool = ProjectilePool.new()
		pool.name = "ProjectilePool"
		scene_root.add_child(pool)
		_pools[key] = pool
		pool._preallocate()
	return pool

var _available: Array[Projectile] = []
var _active: Array[Projectile] = []

func _preallocate() -> void:
	for i in POOL_SIZE:
		var p: Projectile = ProjectileScript.new()
		add_child(p)
		p._init_pooled(self)
		_available.append(p)

func acquire(origin: Vector3, dir: Vector3, speed: float, damage: int, gravity: float) -> Projectile:
	var p: Projectile
	if _available.is_empty():
		# 池满：回收最早的一发再复用（正常火率下不会触发，兜底防内存无限增长）
		if _active.is_empty():
			p = ProjectileScript.new()
			add_child(p)
			p._init_pooled(self)
		else:
			p = _active.pop_front()
			p._deactivate()
	else:
		p = _available.pop_back()
	p._acquire(origin, dir, speed, damage, gravity)
	_active.append(p)
	return p

func recycle(p: Projectile) -> void:
	_active.erase(p)
	_available.append(p)

func _exit_tree() -> void:
	for key in _pools.keys():
		if _pools[key] == self:
			_pools.erase(key)
			break
