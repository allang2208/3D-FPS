"""Replace the extreme-scale main floor with a subdivided mesh at unit scale.

Preserves the existing actor, materials, transform origin, footprint and collision
profile. Does not start gameplay or modify the shared engine cube.
"""
import json
import math
import shutil
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
MAP = '/Game/GameMaps/DayNight_Lighting'
ASSET = '/Game/GameMaps/Geometry/SM_MainGround_Subdivided'
OUT = ROOT / 'Saved/FatZombiePusVisibility/ground_fix'
OUT.mkdir(parents=True, exist_ok=True)
level = u.get_editor_subsystem(u.LevelEditorSubsystem)
level.load_level(MAP)
floor = next(a for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
             if a.get_name() == 'Floor')
component = floor.static_mesh_component
original = component.static_mesh
scale = floor.get_actor_scale3d()
if original.get_path_name() != '/Engine/BasicShapes/Cube.Cube':
    raise RuntimeError('Floor mesh changed; do not overwrite a different ground setup.')
dimensions = [100*scale.x, 100*scale.y, 100*scale.z]
record = {
    'map': MAP, 'actor': floor.get_path_name(), 'old_mesh': original.get_path_name(),
    'old_scale': [scale.x, scale.y, scale.z],
    'location': str(floor.get_actor_location()), 'rotation': str(floor.get_actor_rotation()),
    'dimensions_cm': dimensions, 'replacement': ASSET,
    'collision_profile': str(component.get_collision_profile_name()),
    'material': component.get_material(0).get_path_name(),
    'nominal_cell_cm': 10000,
}
backup = OUT / 'DayNight_Lighting.before.umap'
if not backup.exists():
    shutil.copy2(ROOT / 'Content/GameMaps/DayNight_Lighting.umap', backup)
(OUT / 'source.json').write_text(json.dumps(record, indent=2), encoding='utf-8')

mesh = u.DynamicMesh()
mesh, collision = u.GeometryScript_Primitives.append_box_with_collision(
    mesh, u.GeometryScriptPrimitiveOptions(), u.Transform(),
    dimensions[0], dimensions[1], dimensions[2],
    max(0, math.ceil(dimensions[0]/10000)-1),
    max(0, math.ceil(dimensions[1]/10000)-1), 0,
    u.GeometryScriptPrimitiveOriginMode.CENTER)
u.EditorAssetLibrary.make_directory('/Game/GameMaps/Geometry')
asset, outcome = u.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(
    mesh, ASSET, u.GeometryScriptCreateNewStaticMeshAssetOptions(
        enable_recompute_tangents=True, enable_nanite=False, enable_collision=True))
if not asset:
    raise RuntimeError('Ground mesh creation failed: '+str(outcome))
asset.set_material(0, component.get_material(0))
u.GeometryScript_Collision.set_simple_collision_of_static_mesh(
    collision, asset, u.GeometryScriptSetSimpleCollisionOptions())
if not u.EditorAssetLibrary.save_loaded_asset(asset, False):
    raise RuntimeError('Could not save the subdivided ground mesh.')
component.set_static_mesh(asset)
floor.set_actor_scale3d(u.Vector(1,1,1))
if not level.save_current_level():
    raise RuntimeError('Could not save the main floor replacement.')
record['new_scale'] = [1,1,1]
record['triangle_count'] = mesh.get_triangle_count()
(OUT / 'applied.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
print('FAT_PUS_MAIN_GROUND_FIXED', record['triangle_count'], dimensions)
