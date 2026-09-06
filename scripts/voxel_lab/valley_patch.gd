extends "res://scripts/voxel_lab/smooth_world.gd"
## 外圈保持源地表，避免试验挖掘破坏与 Terrain3D 的边界。
func surface_position(at: Vector3) -> Vector3:
	var edge := maxf(absf(at.x),absf(at.z))
	if edge>20.0:
		if absf(at.x)>23.0:
			at.x=signf(at.x)*24.0
		if absf(at.z)>23.0:
			at.z=signf(at.z)*24.0
		at.y = natural_height(at.x,at.z)
	return at

func normal_at(p: Vector3) -> Vector3:
	if maxf(absf(p.x),absf(p.z))>20.0:
		return Vector3(natural_height(p.x-0.08,p.z)-natural_height(p.x+0.08,p.z),0.16,natural_height(p.x,p.z-0.08)-natural_height(p.x,p.z+0.08)).normalized()
	return super.normal_at(p)

func mine(p: Vector3i) -> bool:
	if abs(p.x)>=18 or abs(p.z)>=18:
		return false
	return super.mine(p)

func can_place(p: Vector3i, kind: int, occupied: AABB) -> bool:
	return abs(p.x)<18 and abs(p.z)<18 and super.can_place(p,kind,occupied)
