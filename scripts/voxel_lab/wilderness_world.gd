extends "res://scripts/voxel_lab/smooth_world.gd"
## 全旷野使用同一套世界坐标密度；只在编辑附近创建网格，不预生成整张地图。
const Bridge := preload("res://scripts/voxel_lab/terrain_material_bridge.gd")
var terrain: Terrain3D
var columns: Dictionary = {}
var jobs: Array[Vector3i] = []
var pending_holes: Dictionary = {}
var source_pixels: Dictionary = {}
var loading := false
var exit_save_path := ""
var soil_scars: Dictionary = {}
var quarried_rocks: Dictionary = {}

func _ready() -> void:
	super._ready()
	Bridge.bind_to_mesh(ground_material,terrain.material)

func generator_id() -> String:
	return "wilderness-valley03-global-v1"

func contains_cell(p: Vector3i) -> bool:
	return p.x>=-496 and p.x<496 and p.z>=-496 and p.z<496 and p.y>=-64 and p.y<192 and is_finite(natural_height(p.x,p.z))

func natural_height(x: float,z: float) -> float:
	var ix:=floori(x)
	var iz:=floori(z)
	if x==ix and z==iz: return _height_sample(ix,iz)
	return lerpf(lerpf(_height_sample(ix,iz),_height_sample(ix+1,iz),x-ix),lerpf(_height_sample(ix,iz+1),_height_sample(ix+1,iz+1),x-ix),z-iz)

func _height_sample(x: int,z: int) -> float:
	var key:=Vector2i(x,z)
	if grid_height_cache.has(key): return grid_height_cache[key]
	# get_height 会把带 hole 的像素返回 NaN；原始高度图才是稳定数据源。
	var region: Terrain3DRegion=terrain.data.get_regionp(Vector3(x,0,z))
	if region==null: return NAN
	var map: Image=region.get_map(Terrain3DRegion.TYPE_HEIGHT)
	var height:=map.get_pixel(posmod(x,terrain.region_size),posmod(z,terrain.region_size)).r
	grid_height_cache[key]=height
	return height

func limit_density(d: float,p: Vector3) -> float:
	return maxf(d,-65.0-p.y)

func get_cell(p: Vector3i) -> int:
	if not contains_cell(p): return EMPTY
	return edits.get(p,initial_cell(p))

func store_cell(_p: Vector3i,_kind: int) -> void:
	pass # 稀疏编辑字典即数据源，未修改单元从源高度推导。

func reset_data() -> void:
	edits.clear()
	soil_scars.clear()
	quarried_rocks.clear()
	edit_history.clear()
	stock={1:32,2:32,3:0,4:64}

func mine(p: Vector3i) -> bool:
	var previous:=soil_scars.has(Vector2i(p.x,p.z))
	var previous_stock: Dictionary=stock.duplicate()
	var changed:=p.y>-64 and ready_at(p) and super.mine(p)
	if changed:
		# Formal wilderness rewards go to the RPG backpack. Do not also mint a
		# second copy into the voxel-lab fill reserve.
		stock=previous_stock
		edit_history.back()["scar_before"]=previous
	return changed

func place(p: Vector3i,kind: int,occupied: AABB) -> bool:
	var previous:=soil_scars.has(Vector2i(p.x,p.z))
	var changed:=super.place(p,kind,occupied)
	if changed: edit_history.back()["scar_before"]=previous
	return changed

func change_cell(p: Vector3i,kind: int) -> void:
	if absf(natural_height(p.x,p.z)-(p.y+0.5))<1.5: soil_scars[Vector2i(p.x,p.z)]=true
	super.change_cell(p,kind)

func undo_edit(occupied: AABB) -> bool:
	if edit_history.is_empty(): return false
	var record: Dictionary=edit_history.back().duplicate()
	if not super.undo_edit(occupied): return false
	var p: Vector3i=record.cell
	if not record.get("scar_before",false): soil_scars.erase(Vector2i(p.x,p.z))
	for key in affected_chunks(p): rebuild_chunk(key)
	return true

func save_metadata() -> Dictionary:
	var scars: Array=[]
	for p in soil_scars: scars.append([p.x,p.y])
	return {"soil_scars":scars,"quarried_rocks":quarried_rocks.duplicate()}

func validate_metadata(data: Dictionary) -> bool:
	var rocks: Variant=data.get("quarried_rocks",{})
	if not rocks is Dictionary: return false
	for key in rocks:
		if not key is String or not rocks[key] is bool or not rocks[key]: return false
	var scars: Variant=data.get("soil_scars",[])
	if not scars is Array: return false
	for row in scars:
		if not row is Array or row.size()!=2: return false
		for value in row:
			if not (value is float or value is int) or not is_finite(value) or value!=floor(value) or value< -496 or value>=496: return false
	return true

func restore_metadata(data: Dictionary) -> void:
	quarried_rocks=data.get("quarried_rocks",{}).duplicate()
	for row in data.get("soil_scars",[]): soil_scars[Vector2i(row[0],row[1])]=true

func is_bedrock(p: Vector3i) -> bool:
	return p.y<=-64

func can_place(p: Vector3i,kind: int,occupied: AABB) -> bool:
	return ready_at(p) and super.can_place(p,kind,occupied)

func ready_at(p: Vector3i) -> bool:
	if not jobs.is_empty(): return false
	var col:=Vector2i(floori(p.x/8.0),floori(p.z/8.0))
	for z in range(-1,2):
		for x in range(-1,2):
			if not columns.has(col+Vector2i(x,z)): return false
	return true

func prepare_at(p: Vector3i) -> void:
	if not contains_cell(p) or not jobs.is_empty(): return
	var center:=Vector2i(floori(p.x/8.0),floori(p.z/8.0))
	var dirty: Dictionary={}
	for z in range(center.y-1,center.y+2):
		for x in range(center.x-1,center.x+2):
			var col:=Vector2i(x,z)
			if x*8 < -504 or x*8>=504 or z*8 < -504 or z*8>=504: continue
			if not columns.has(col):
				columns[col]=true
				pending_holes[col]=true
				for dz in range(-1,2):
					for dx in range(-1,2): dirty[col+Vector2i(dx,dz)]=true
	for col in dirty:
		if columns.has(col): _queue_column(col)
	# 深挖/高处建造按实际操作高度扩展，地表列无需固定垂直范围。
	for key in affected_chunks(p):
		if not chunks.has(key) and not jobs.has(key): jobs.append(key)

func _queue_column(col: Vector2i) -> void:
	var low:=INF
	var high:=-INF
	for z in range(-1,10):
		for x in range(-1,10):
			var h:=natural_height(col.x*8+x,col.y*8+z)
			low=minf(low,h)
			high=maxf(high,h)
	if not is_finite(low) or not is_finite(high): return
	for y in range(floori((low-2)/8.0),floori((high+2)/8.0)+1):
		var key:=Vector3i(col.x,y,col.y)
		if not jobs.has(key): jobs.append(key)
	for key in chunks:
		if key.x==col.x and key.z==col.y and not jobs.has(key): jobs.append(key)

func surface_position(at: Vector3) -> Vector3:
	# Surface Nets 的外围双网格单元贴合 Terrain3D hole 消失的相邻四边形。
	var col:=Vector2i(floori((at.x+0.001)/8.0),floori((at.z+0.001)/8.0))
	var xcell:=floori(at.x)
	var zcell:=floori(at.z)
	var snapped:=false
	var left: bool=columns.has(col) or (posmod(zcell,8)==7 and columns.has(col+Vector2i.DOWN))
	var right: bool=columns.has(col+Vector2i.RIGHT) or (posmod(zcell,8)==7 and columns.has(col+Vector2i.ONE))
	var top: bool=columns.has(col) or (posmod(xcell,8)==7 and columns.has(col+Vector2i.RIGHT))
	var bottom: bool=columns.has(col+Vector2i.DOWN) or (posmod(xcell,8)==7 and columns.has(col+Vector2i.ONE))
	if posmod(xcell,8)==7 and left!=right:
		at.x=float(xcell+1 if left else xcell)
		snapped=true
	if posmod(zcell,8)==7 and top!=bottom:
		at.z=float(zcell+1 if top else zcell)
		snapped=true
	if snapped: at.y=natural_height(at.x,at.z)
	return at

func surface_weights(at: Vector3) -> Color:
	var weights:=super.surface_weights(at)
	var depth:=natural_height(at.x,at.z)-at.y
	# 去掉草皮后立即是裸土，深于五米才渐变岩层。
	weights.g=maxf(weights.g,smoothstep(0.04,0.25,depth))
	for z in range(floori(at.z)-1,floori(at.z)+2):
		for x in range(floori(at.x)-1,floori(at.x)+2):
			if soil_scars.has(Vector2i(x,z)):
				weights.g=maxf(weights.g,1.0-smoothstep(0.35,1.35,Vector2(at.x-x-0.5,at.z-z-0.5).length()))
	weights.r=smoothstep(5.0,8.0,depth)
	return weights

func _process(_delta: float) -> void:
	if jobs.is_empty(): return
	rebuild_chunk(jobs.pop_front())
	if jobs.is_empty(): _apply_holes()

func _apply_holes() -> void:
	for col in pending_holes:
		for z in range(col.y*8,col.y*8+8):
			for x in range(col.x*8,col.x*8+8):
				var p:=Vector3(x,0,z)
				var region: Terrain3DRegion=terrain.data.get_regionp(p)
				if region==null: continue
				var image: Image=region.get_map(Terrain3DRegion.TYPE_CONTROL)
				var pixel:=Vector2i(posmod(x,terrain.region_size),posmod(z,terrain.region_size))
				var key:=Vector2i(x,z)
				if not source_pixels.has(key): source_pixels[key]=[image,pixel,image.get_pixelv(pixel)]
				terrain.data.set_control_hole(p,true)
	pending_holes.clear()
	terrain.data.update_maps(Terrain3DRegion.TYPE_CONTROL)
	terrain.collision.build()
	Bridge.sync_parameters(ground_material,terrain.material)
	loading=false

func rebuild_all() -> void:
	# load_world 先验证再进入这里；失效存档不会破坏当前世界。
	var restored_points: Array=edits.keys()
	for scar in soil_scars: restored_points.append(Vector3i(scar.x,floori(natural_height(scar.x,scar.y)),scar.y))
	for p in restored_points:
		var center:=Vector2i(floori(p.x/8.0),floori(p.z/8.0))
		for z in range(center.y-1,center.y+2):
			for x in range(center.x-1,center.x+2):
				var col:=Vector2i(x,z)
				columns[col]=true
				pending_holes[col]=true
	for col in columns: _queue_column(col)
	for p in edits:
		for key in affected_chunks(p):
			if not jobs.has(key): jobs.append(key)
	loading=not jobs.is_empty()

func _exit_tree() -> void:
	if not exit_save_path.is_empty():
		var result:=save_world(exit_save_path)
		if result!=OK: push_error("旷野地形退出保存失败: "+error_string(result))
	for record in source_pixels.values(): record[0].set_pixelv(record[1],record[2])
