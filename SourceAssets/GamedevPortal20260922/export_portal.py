"""Migrate the existing gamedev mesh. No generation, rendering or source-file overwrite."""
import bpy
import json
import shutil
from pathlib import Path
from mathutils import Vector

HERE = Path(__file__).parent
OUT = HERE/'Authored'
OUT.mkdir(parents=True, exist_ok=True)
SOURCE_ROOT = Path('E:/无尽轮回/长期备份/2026-7-13-1/game-dev')
SOURCE = SOURCE_ROOT/'tools/ai-gen/_settlement_building_pack_20260821/portal/portal_model.blend'
shutil.copy2(SOURCE, OUT/'GamedevPortal_Original.blend')
shutil.copy2(SOURCE_ROOT/'assets/terrain/portal_structure_occluder.png', HERE/'reference_portal.png')
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 0.01
root = bpy.data.objects['PORTAL_ROOT_ROT_Z_44_8']
unrotate = root.matrix_world.inverted()
source_parts = [o for o in scene.objects if o.type == 'MESH' and o.name.startswith('Portal_')]
material_names = {
    'MAT_Weathered_Stone': 'Portal_WhiteMarble',
    'MAT_Fieldstone_Foundation': 'Portal_PolishedMolding',
    'MAT_Muted_Plaster': 'Portal_WhiteMarble',
    'MAT_Aged_Brass': 'Portal_SatinGold',
    'MAT_Warm_Glow': 'Portal_Energy',
}
materials = {}
marble_path = Path('D:/FPS3D/FPSGAME/SourceAssets/SquareAltar20260922/Authored/T_SquareAltar_Marble.png')
image = bpy.data.images.load(str(marble_path))
image.pack()
recipes = {
    'Portal_WhiteMarble': ((.87,.86,.83), .31, 0),
    'Portal_PolishedMolding': ((.91,.90,.87), .23, 0),
    'Portal_SatinGold': ((.67,.43,.15), .27, .92),
    'Portal_Energy': ((.025,.42,.48), .2, 0),
}
for name, (color, roughness, metallic) in recipes.items():
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    shader = next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    shader.inputs['Base Color'].default_value = (*color,1)
    shader.inputs['Roughness'].default_value = roughness
    shader.inputs['Metallic'].default_value = metallic
    if 'Marble' in name or 'Molding' in name:
        texture = mat.node_tree.nodes.new('ShaderNodeTexImage'); texture.image = image
        mix = mat.node_tree.nodes.new('ShaderNodeMixRGB'); mix.inputs[0].default_value = .52
        mix.inputs[1].default_value = (*color,1)
        mat.node_tree.links.new(texture.outputs['Color'], mix.inputs[2])
        mat.node_tree.links.new(mix.outputs[0], shader.inputs['Base Color'])
    if name == 'Portal_Energy':
        shader.inputs['Emission Color'].default_value = (*color,1)
        shader.inputs['Emission Strength'].default_value = 3.2
    materials[name] = mat

parts = []
depsgraph = bpy.context.evaluated_depsgraph_get()
for original in source_parts:
    # Preserve original topology and proportions, with smooth bevel tessellation for FPS viewing.
    for modifier in original.modifiers:
        if modifier.type == 'BEVEL':
            modifier.segments = max(modifier.segments, 3)
    depsgraph.update()
    evaluated = original.evaluated_get(depsgraph)
    mesh = bpy.data.meshes.new_from_object(evaluated, depsgraph=depsgraph)
    transform = unrotate @ original.matrix_world
    for vertex in mesh.vertices:
        vertex.co = (transform @ vertex.co) * .01  # original authoring dimensions are centimetres
    mesh.materials.clear()
    old_mat = original.material_slots[0].material.name
    mesh.materials.append(materials[material_names[old_mat]])
    mesh.update()
    while mesh.uv_layers:
        mesh.uv_layers.remove(mesh.uv_layers[0])
    uv = mesh.uv_layers.new(name='UV0_Physical')
    is_core = original.name == 'Portal_CyanCore'
    for poly in mesh.polygons:
        poly.material_index = 0
        normal = poly.normal
        axis = max(range(3), key=lambda i: abs(normal[i]))
        for loop_index in poly.loop_indices:
            p = mesh.vertices[mesh.loops[loop_index].vertex_index].co
            if is_core:
                uv.data[loop_index].uv = ((p.x+.85)/1.70, (p.z-.37)/2.88)
            else:
                uv.data[loop_index].uv = ((p.y,p.z) if axis == 0 else (p.x,p.z) if axis == 1 else (p.x,p.y))
    # Bake the doorway's forward axis into vertices. UE travel actors face +X.
    # UVs retain the original physical projection and the core's normalized field.
    for vertex in mesh.vertices:
        x, y, z = vertex.co
        vertex.co = (-y*100.0, x*100.0, z*100.0)
    mesh.update()
    part = bpy.data.objects.new(original.name+'_UE', mesh)
    scene.collection.objects.link(part)
    parts.append(part)

for obj in list(scene.objects):
    if obj not in parts:
        bpy.data.objects.remove(obj, do_unlink=True)

scene.cursor.location = (0,0,0)
exports = []
groups = [('SM_GamedevPortal_Frame', [p for p in parts if 'CyanCore' not in p.name]),
          ('SM_GamedevPortal_Energy', [p for p in parts if 'CyanCore' in p.name])]
for name, group in groups:
    bpy.ops.object.select_all(action='DESELECT')
    for p in group: p.select_set(True)
    bpy.context.view_layer.objects.active = group[0]
    if len(group) > 1:
        bpy.ops.object.join()
    obj = bpy.context.object
    obj.name = name
    bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    triangulate = obj.modifiers.new('ExportTriangles', 'TRIANGULATE')
    bpy.ops.object.modifier_apply(modifier=triangulate.name)
    bpy.ops.export_scene.fbx(filepath=str(OUT/(name+'.fbx')), use_selection=True, object_types={'MESH'},
        apply_unit_scale=True, apply_scale_options='FBX_SCALE_ALL', axis_forward='-Y', axis_up='Z',
        use_mesh_modifiers=True, mesh_smooth_type='FACE', add_leaf_bones=False, bake_anim=False)
    exports.append({'asset': name, 'triangles': len(obj.data.polygons),
        'dimensions_m': [d*0.01 for d in obj.dimensions], 'materials': [m.name for m in obj.data.materials]})

bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'GamedevPortal_UE.blend'))
(HERE/'export_manifest.json').write_text(json.dumps({'source': str(SOURCE), 'exports': exports,
    'source_unit': 'cm', 'export_unit': 'cm', 'display_rotation_removed_degrees': 44.8, 'mesh_forward': '+X',
    'geometry': 'Original mesh and proportions retained; bevel segments raised to at least 3.',
    'rendered': False, 'tested': False}, ensure_ascii=False, indent=2), encoding='utf-8')
print('GAMEDEV_PORTAL_EXPORTED ' + str(OUT))
