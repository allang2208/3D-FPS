"""Blender background authoring: four 1m ice masonry modules, no scene render."""
import bpy, bmesh, random, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / 'SourceAssets/IceWall20260930'
DEST.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.unit_settings.system = 'METRIC'
manifest = []
for index in range(1, 5):
    random.seed(93000 + index)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0))
    ob = bpy.context.object
    ob.name = f'SM_IceBlock_{index:02d}'
    for vertex in ob.data.vertices:
        # Keep Y/Z joint planes; shallow front/back deformation makes each block distinct.
        vertex.co.x *= random.uniform(.95, 1.0)
    bevel = ob.modifiers.new('IrregularChippedEdges', 'BEVEL')
    bevel.width = .018 + index * .003
    bevel.segments = 2
    bpy.ops.object.modifier_apply(modifier=bevel.name)
    bm = bmesh.new(); bm.from_mesh(ob.data)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(ob.data); bm.free()
    for face in ob.data.polygons:
        face.use_smooth = False
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=1.1, island_margin=.03)
    bpy.ops.object.mode_set(mode='OBJECT')
    color = ob.data.color_attributes.new(name='Frost', type='BYTE_COLOR', domain='CORNER')
    for loop in ob.data.loops:
        co = ob.data.vertices[loop.vertex_index].co
        frost = min(1, max(0, (max(abs(co.y), abs(co.z)) - .40) * 7))
        color.data[loop.index].color = (frost, frost, frost, 1)
    bpy.ops.export_scene.fbx(filepath=str(DEST / (ob.name + '.fbx')), use_selection=True,
        object_types={'MESH'}, add_leaf_bones=False, axis_forward='-Y', axis_up='Z',
        apply_unit_scale=True, bake_anim=False, mesh_smooth_type='FACE')
    manifest.append({'mesh': ob.name, 'source_unit': 'meters', 'runtime_unit': 'centimeters',
                     'triangles': sum(len(p.vertices)-2 for p in ob.data.polygons)})
    ob.hide_set(True); ob.select_set(False)
bpy.ops.wm.save_as_mainfile(filepath=str(DEST / 'IceWallBlocks.blend'))
(DEST / 'geometry.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
