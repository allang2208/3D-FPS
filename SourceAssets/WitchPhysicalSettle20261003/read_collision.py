"""Read only the Witch's current asset collision and native defaults."""
import json
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/WitchPhysicalSettle20261003')
staff = u.load_asset('/Game/Monsters/WitchRebuilt/Props/SM_WitchRebuilt_StaffPhysics')
body = staff.get_editor_property('body_setup')
aggregate = body.get_editor_property('agg_geom')
def vector(v):
    return [v.x, v.y, v.z]
collision = u.GeometryScript_Collision.get_simple_collision_from_static_mesh(staff)
dynamic = u.GeometryScript_Primitives.append_simple_collision_shapes(
    u.DynamicMesh(), u.GeometryScriptPrimitiveOptions(), u.Transform(), collision,
    u.GeometryScriptSimpleCollisionTriangulationOptions())
dynamic, positions, gaps = u.GeometryScript_MeshQueries.get_all_vertex_positions(dynamic, True)
points = [vector(v) for v in u.GeometryScript_List.convert_vector_list_to_array(positions)]
collision_bounds = {'vertices': len(points),
                    'min': [min(v[i] for v in points) for i in range(3)],
                    'max': [max(v[i] for v in points) for i in range(3)]}
default = u.get_default_object(u.WitchRebuiltMonster)
prop = default.get_editor_property('staff')
corpse = u.load_asset('/Game/Monsters/WitchRebuilt/CorpseFollow/SK_WitchRebuilt_CorpseFollow')
physics = corpse.get_editor_property('physics_asset')
visible_bounds = staff.get_bounding_box()
report = {'staff_mesh': staff.get_path_name(), 'collision_trace_flag': str(body.get_editor_property('collision_trace_flag')),
          'staff_default_mobility': str(prop.get_editor_property('mobility')),
          'staff_default_mesh': prop.get_editor_property('static_mesh').get_path_name(),
          'convex_count': u.GeometryScript_Collision.get_simple_collision_shape_count(collision),
          'collision_bounds': collision_bounds,
          'visible_bounds': {'min': vector(visible_bounds.min), 'max': vector(visible_bounds.max)},
          'corpse_physics': physics.get_path_name(),
          'mesh_always_create_physics_state': default.get_editor_property('mesh').get_editor_property('always_create_physics_state'),
          'staff_auto_weld': prop.get_editor_property('body_instance').get_editor_property('auto_weld'),
          'runtime_simulation': False, 'read_only': True}
(ROOT / 'Receipts/collision-before.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('WITCH_COLLISION_SOURCE ' + json.dumps(report))
