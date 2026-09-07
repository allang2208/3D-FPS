extends RefCounted
const SIDES := [Vector3i.LEFT,Vector3i.RIGHT,Vector3i.FORWARD,Vector3i.BACK]
const MAX_SPAN := 4 # 4 half-metre cells = 2 m cantilever.
const Catalog := preload("res://scripts/building/build_piece_catalog.gd")

static func supported(cells: Dictionary, anchors: Dictionary, rotations: Dictionary = {}) -> Dictionary:
	var cost := {}
	var queue: Array[Vector3i] = []
	for cell in anchors:
		if cells.has(cell) and Catalog.supports_weight(str(cells[cell])):
			cost[cell] = 0
			queue.append(cell)
	var index := 0
	while index < queue.size():
		var cell := queue[index]
		index += 1
		for step in [Vector3i.UP]+SIDES:
			var next: Vector3i = cell+step
			var distance: int = cost[cell]+(0 if step==Vector3i.UP else 1)
			if distance<=MAX_SPAN and cells.has(next) and Catalog.supports_weight(str(cells[next])) and distance<int(cost.get(next,999)):
				cost[next]=distance
				queue.append(next)
	# Non-load-bearing pieces may rest on the foundation or on fully supported
	# structural cells, but never propagate support to another piece.
	var occupancy:=Catalog.build_occupancy(cells,rotations)
	for root in cells:
		if Catalog.supports_weight(str(cells[root])): continue
		if anchors.has(root):
			cost[root]=0
			continue
		var supported_base:=true
		for offset in Catalog.bottom_offsets(str(cells[root]),int(rotations.get(root,0))):
			var below_root=occupancy.get(root+offset+Vector3i.DOWN)
			if below_root==null or not cost.has(below_root) or not Catalog.supports_weight(str(cells.get(below_root,""))):
				supported_base=false
				break
		if supported_base: cost[root]=0
	return cost
