class_name CasingPool
extends Node3D
## 弹壳对象池：预分配 N 颗，落地/寿命结束回收复用，消除每发 new/free 抖动。
## 池节点挂在当前场景根下（场景切换自动释放并从静态表清除）。
## 使用方无需感知：CasingScript.spawn(...) 内部自动走池。

const CasingScript := preload("res://scripts/casing.gd")
const POOL_SIZE := 20

static var _pools := {}  # scene_root -> CasingPool

static func for_scene(scene_root: Node) -> CasingPool:
	var key: Object = scene_root
	var pool: CasingPool = _pools.get(key)
	if pool == null or not is_instance_valid(pool):
		pool = CasingPool.new()
		pool.name = "CasingPool"
		scene_root.add_child(pool)
		_pools[key] = pool
		pool._preallocate()
	return pool

var _available: Array[Casing] = []
var _active: Array[Casing] = []

func _preallocate() -> void:
	for i in POOL_SIZE:
		var c: Casing = CasingScript.new()
		add_child(c)
		c._init_pooled(self)
		_available.append(c)

func acquire(origin: Vector3, vel: Vector3, rot: Vector3, lifetime: float) -> Casing:
	var c: Casing
	if _available.is_empty():
		if _active.is_empty():
			c = CasingScript.new()
			add_child(c)
			c._init_pooled(self)
		else:
			c = _active.pop_front()
			c._deactivate()
	else:
		c = _available.pop_back()
	c._acquire(origin, vel, rot, lifetime)
	_active.append(c)
	return c

func recycle(c: Casing) -> void:
	_active.erase(c)
	_available.append(c)

func _exit_tree() -> void:
	for key in _pools.keys():
		if _pools[key] == self:
			_pools.erase(key)
			break
