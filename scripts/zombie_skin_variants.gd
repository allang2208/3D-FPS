extends RefCounted
## Cosmetic-only selection. Preserve model, skeleton, animation and gameplay identity.
const SKINS := {
 "res://assets/models/modern_zombie/modern_zombie_v02.glb": "res://assets/models/zombie_skin_variants/modern_albedo.png",
 "res://assets/models/humanoid_variants/miner_zombie_v02.glb": "res://assets/models/zombie_skin_variants/miner_albedo.png",
 "res://assets/models/humanoid_variants/runner_zombie_v02.glb": "res://assets/models/zombie_skin_variants/runner_albedo.png",
}

static func apply(model: Node3D, choice: int = -1) -> int:
 if model == null or not SKINS.has(model.scene_file_path):
  return -1
 var picked := randi_range(0, 1) if choice < 0 else clampi(choice, 0, 1)
 var texture: Texture2D = load(SKINS[model.scene_file_path]) if picked == 1 else null
 _apply_materials(model, texture, {})
 return picked

static func _apply_materials(node: Node, texture: Texture2D, copies: Dictionary) -> void:
 if node is MeshInstance3D and node.mesh:
  for surface in node.mesh.get_surface_count():
   var source := node.get_active_material(surface) as StandardMaterial3D
   if source == null: continue
   if not copies.has(source):
    var material := source.duplicate() as StandardMaterial3D
    if texture != null: material.albedo_texture = texture
    copies[source] = material
   node.set_surface_override_material(surface, copies[source])
 for child in node.get_children():
  _apply_materials(child, texture, copies)
