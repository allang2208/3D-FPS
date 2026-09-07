extends Area3D
## Call before add_child; faction persists independently of the deleted corpse.
@export var source_faction: StringName = &"monster"
@export var hostile_factions: Array[StringName] = [&"player", &"friendly"]
@export var damage := 8
@export var tick_interval := .5
@export var lifetime := 6.0
@export var random_seed := -1
var age := 0.0
var polygon := PackedVector2Array()
var _mat: ShaderMaterial
var _mesh: MeshInstance3D
var _exposure := {}
var _phase := 0.0
var _collision: CollisionShape3D

func _ready() -> void:
 collision_layer=0
 collision_mask=0xFFFFFFFF
 var rng:=RandomNumberGenerator.new()
 if random_seed<0:rng.randomize()
 else:rng.seed=random_seed
 _phase=rng.randf_range(0,100)
 var rx:=rng.randf_range(.85,1.20)
 var rz:=rng.randf_range(.70,1.0)
 var angle:=rng.randf_range(0,TAU)
 var phases:=Vector3(rng.randf_range(0,TAU),rng.randf_range(0,TAU),rng.randf_range(0,TAU))
 for i in 96:
  var a:=TAU*i/96.0
  var r:=1.0+.10*sin(a*3+phases.x)+.065*sin(a*5+phases.y)+.04*sin(a*9+phases.z)
  polygon.append(Vector2(cos(a)*rx*r,sin(a)*rz*r).rotated(angle))

 _mesh=MeshInstance3D.new()
 _mesh.cast_shadow=GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
 _mat=ShaderMaterial.new()
 _mat.shader=load("res://pus.gdshader")
 _mat.set_shader_parameter("seed_phase",_phase)
 _mesh.material_override=_mat
 _mesh.visible=false
 add_child(_mesh)
 _collision=CollisionShape3D.new()
 add_child(_collision)
 # Shared radial vertices are sampled only once. No horizontal mesh scaling.
 _samples.append(Vector3.ZERO)
 _uv_radius.append(0.0)
 for ring in range(1,RINGS+1):
  for point in polygon:
   var q:Vector2=point*ring/RINGS
   _samples.append(Vector3(q.x,0,q.y))
   _uv_radius.append(ring*1.0/RINGS)
 _valid.resize(_samples.size())
 _normals.resize(_samples.size())
 set_visual_age(0)

signal surface_built
const RINGS:=16
const FRAME_RAY_BUDGET:=384
static var _budget_frame: int=-1
static var _budget_used:=0
@export_flags_3d_physics var ground_mask:int=1
@export var max_slope_degrees:=55.0
@export var ground_clearance:=.010
var surface_ready:=false
var _cursor:=0
var _samples:=PackedVector3Array()
var _normals:=PackedVector3Array()
var _uv_radius:=PackedFloat32Array()
var _valid:=PackedByteArray()
var _triangles:Array[Vector3i]=[]
var _anchor_rid:=RID()
var _cells:Dictionary={}
const CELL_SIZE:=.15
var _spread:=0.0
var sample_ray_count:=0

func _ray_at(local:Vector3,above:float,below:float)->Dictionary:
 var origin:=to_global(local)
 var query:=PhysicsRayQueryParameters3D.create(origin+Vector3.UP*above,origin-Vector3.UP*below,ground_mask)
 query.exclude=[get_rid()]
 query.collide_with_areas=false
 sample_ray_count+=1
 return get_world_3d().direct_space_state.intersect_ray(query)

func _sample_batch()->void:
 var frame:=Engine.get_physics_frames()
 if frame!=_budget_frame:
  _budget_frame=frame
  _budget_used=0
 var count:=0
 while _cursor<_samples.size() and count<128 and _budget_used<FRAME_RAY_BUDGET:
  var idx:=_cursor
  _cursor+=1
  if idx>0:
   var parent:=0 if idx<=polygon.size() else idx-polygon.size()
   if _valid[parent]==0:continue
   _samples[idx].y=_samples[parent].y
  var hit:=_ray_at(_samples[idx],.16 if idx>0 else .15,.20 if idx>0 else 1.0)
  count+=1
  _budget_used+=1
  if hit.is_empty():continue
  if hit.normal.y<cos(deg_to_rad(max_slope_degrees)):continue
  # Stay on the supporting collider, not an overhead floor or nearby actor.
  if idx==0:_anchor_rid=hit.rid
  elif hit.rid!=_anchor_rid:continue
  _samples[idx]=to_local(hit.position)
  _normals[idx]=global_basis.inverse()*hit.normal
  _valid[idx]=1
 if _cursor==_samples.size():_finish_surface()

func _edge_ok(a:int,b:int)->bool:
 var d:=_samples[a]-_samples[b]
 return absf(d.y)<=Vector2(d.x,d.z).length()*tan(deg_to_rad(max_slope_degrees))+.015

func _add_triangle(a:int,b:int,c:int)->void:
 if _valid[a]==0 or _valid[b]==0 or _valid[c]==0:return
 if not _edge_ok(a,b) or not _edge_ok(b,c) or not _edge_ok(c,a):return
 var tri:=Vector3i(a,b,c)
 _triangles.append(tri)
 var pa:=Vector2(_samples[a].x,_samples[a].z)
 var pb:=Vector2(_samples[b].x,_samples[b].z)
 var pc:=Vector2(_samples[c].x,_samples[c].z)
 var lo:=Vector2i((pa.min(pb).min(pc)/CELL_SIZE).floor())
 var hi:=Vector2i((pa.max(pb).max(pc)/CELL_SIZE).floor())
 for x in range(lo.x,hi.x+1):
  for z in range(lo.y,hi.y+1):
   var key:=Vector2i(x,z)
   if not _cells.has(key):_cells[key]=[]
   _cells[key].append(tri)

func _finish_surface()->void:
 var n:=polygon.size()
 for i in n:
  _add_triangle(0,1+i,1+(i+1)%n)
 for ring in range(1,RINGS):
  var inner:=1+(ring-1)*n
  var outer:=1+ring*n
  for i in n:
   var j:=(i+1)%n
   _add_triangle(inner+i,outer+i,outer+j)
   _add_triangle(inner+i,outer+j,inner+j)
 surface_ready=true
 if _triangles.is_empty():
  surface_built.emit()
  queue_free()
  return
 var st:=SurfaceTool.new()
 st.begin(Mesh.PRIMITIVE_TRIANGLES)
 var low:=INF
 var high:=-INF
 for tri in _triangles:
  for idx in [tri.x,tri.y,tri.z]:
   var v:=_samples[idx]+Vector3.UP*ground_clearance
   st.set_normal(_normals[idx])
   st.set_uv(Vector2(_uv_radius[idx],0))
   st.add_vertex(v)
   low=minf(low,v.y);high=maxf(high,v.y)
 _mesh.mesh=st.commit()
 var shape:=CylinderShape3D.new()
 shape.radius=1.6
 shape.height=high-low+.6
 _collision.shape=shape
 _collision.position.y=(high+low)/2
 _mesh.visible=true
 surface_built.emit()

## Returns cached supporting height and shader reveal radius; no per-frame terrain ray.
func surface_at(point:Vector3)->Vector2:
 var local:=to_local(point)
 var q:=Vector2(local.x,local.z)
 var key:=Vector2i((q/CELL_SIZE).floor())
 for tri:Vector3i in _cells.get(key,[]):
  var a:=_samples[tri.x];var b:=_samples[tri.y];var c:=_samples[tri.z]
  var v0:=Vector2(b.x-a.x,b.z-a.z)
  var v1:=Vector2(c.x-a.x,c.z-a.z)
  var v2:=q-Vector2(a.x,a.z)
  var den:=v0.cross(v1)
  if absf(den)<.0000001:continue
  var u:=v2.cross(v1)/den
  var v:=v0.cross(v2)/den
  if u>=-.00001 and v>=-.00001 and u+v<=1.00001:
   return Vector2(a.y*(1-u-v)+b.y*u+c.y*v,_uv_radius[tri.x]*(1-u-v)+_uv_radius[tri.y]*u+_uv_radius[tri.z]*v)
 return Vector2(INF,INF)

func faction_of(body: Node) -> StringName:
 if body.has_meta("faction"):return StringName(body.get_meta("faction"))
 if body.is_in_group("player") or body.name==&"Player":return &"player"
 if body.is_in_group("friendly"):return &"friendly"
 if body.is_in_group("enemies"):return &"monster"
 return &"neutral"

func contains_point(point: Vector3) -> bool:
 if not surface_ready or _spread<=0:return false
 var surface:=surface_at(point)
 if not is_finite(surface.x) or surface.y>_spread:return false
 var height:=to_local(point).y-surface.x
 return height>=-.06 and height<=.12

func _physics_process(delta: float) -> void:
 if not surface_ready:
  _sample_batch()
  return
 advance(delta,get_overlapping_bodies())

func advance(delta: float, bodies: Array) -> void:
 if not surface_ready:return
 var active_delta:=minf(delta,maxf(0,lifetime-.4-age))
 age+=delta
 set_visual_age(age)
 var present:={}
 if active_delta>0:
  for body in bodies:
   if not is_instance_valid(body) or not body.has_method("take_damage"):continue
   if body.get("is_dead")==true or body.get("_dead")==true:continue
   var faction:=faction_of(body)
   if faction==source_faction or not hostile_factions.has(faction):continue
   if not contains_point(body.global_position):continue
   var id:int=body.get_instance_id()
   present[id]=true
   var elapsed:float=_exposure.get(id,0.0)+active_delta
   while elapsed+0.000001>=tick_interval:
    elapsed-=tick_interval
    body.take_damage(damage,"magic",self)
    if not is_instance_valid(body) or body.get("is_dead")==true or body.get("_dead")==true:break
   _exposure[id]=elapsed
 for id in _exposure.keys():
  if not present.has(id):_exposure.erase(id)
 if age>=lifetime:queue_free()

func set_visual_age(time: float) -> void:
 _mat.set_shader_parameter("clock",time)
 _mat.set_shader_parameter("opacity",1.0-smoothstep(lifetime-.4,lifetime,time))
 _spread=smoothstep(0,.35,time)
 _mat.set_shader_parameter("spread",_spread)
