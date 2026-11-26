"""Author a three-stage one-handed blade blank fitted to the current Kukri.

Uses the existing weapon's measured silhouette. The sacrificial tong shank,
station support plane and contact profile share the established forge frame.
Run in background Blender; import_all_melee.py installs only saved outputs.
"""
import bpy
import bmesh
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'SourceAssets/ForgeAllMelee20261024'
EXPORT = OUT / 'Export'
EXPORT.mkdir(parents=True, exist_ok=True)
DEST = '/Game/Props/ForgeInteraction20260927/SingleHanded20261024'
source = json.loads((ROOT / 'SourceAssets/Kukri20261020/model.json').read_text(encoding='utf-8'))
# Blade +Z becomes blank +X. The cutting edge (+X in the weapon) becomes
# -Y in the blank, keeping the thick spine on the same side as the Dao blank.
silhouette = [(z - 18, -edge, -spine) for z, thickness, spine, edge in source['profile'] if z >= 6]
tip_x, tip_y = source['tip_cm'][2] - 18, -source['tip_cm'][0]
silhouette.append((tip_x, tip_y - .10, tip_y + .10))

def section_at(x):
    for a, b in zip(silhouette, silhouette[1:]):
        if a[0] <= x <= b[0]:
            t = (x - a[0]) / (b[0] - a[0])
            return tuple(a[i] + (b[i] - a[i]) * t for i in (1, 2))
    raise ValueError('Strike point outside blade')

def point(x):
    a, b = section_at(x)
    y = (a + b) * .5
    return [round(.5 - y / 24, 6), round(.375 - x / 60, 6)]

profile = {
    'label': '单手刀剑坯（尼泊尔弯刀）', 'crown': [.48, 1],
    'grip_cm': [-24, 0, .475], 'strike_radius_cm': 1.3,
    'quench_tip_cm': [round(tip_x, 4), round(tip_y, 4), .375],
    'quench_heel_cm': [-12, -.235, .475], 'quench_drop_cm': 40,
    'aim_min': [.38, .20], 'aim_max': [.86, .61],
    'heat_span_cm': [-10, 6], 'heat_center_cm': [-2, -2.8, 7],
    'veil_scale': [.26, .20, 1],
    'points': [point(z - 18) for z in (9.5, 11, 12.5, 14, 15.5, 17, 19, 21)],
    'stages': [],
}
for stage in range(3):
    swell = 1 + .10 * (2 - stage)
    top = .85 + .15 * (2 - stage)
    sections = [[-31, -1.2, 1.2, .95, .38], [-23, -1.2, 1.2, .95, .38],
                [-21, -1.25, 1.25, .95, .38], [-16, -1.6, 1.6, top, .35]]
    for x, ymin, ymax in silhouette:
        center, half = (ymin + ymax) * .5, (ymax - ymin) * .5 * swell
        sections.append([round(x, 4), round(center - half, 4), round(center + half, 4),
                         top if x < tip_x else .65, .24 + .08 * (2 - stage)])
    profile['stages'].append({'mesh': f'{DEST}/SM_ForgeSingleHandedBlank{stage}', 'sections': sections})

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version = 0
bpy.context.scene.unit_settings.system = 'METRIC'
bpy.context.scene.unit_settings.scale_length = 1
material = bpy.data.materials.new('HotBlank')
material.diffuse_color = (.16, .05, .014, 1)
material.use_nodes = True
bsdf = material.node_tree.nodes.get('Principled BSDF')
bsdf.inputs['Base Color'].default_value = (.16, .05, .014, 1)
bsdf.inputs['Metallic'].default_value = .7
bsdf.inputs['Roughness'].default_value = .8
outputs = []
for stage in profile['stages']:
    name = stage['mesh'].rsplit('/', 1)[-1]
    vertices, faces = [], []
    for x, ymin, ymax, top, edge in stage['sections']:
        crown = ymin + (ymax - ymin) * profile['crown'][0]
        vertices += [(x * .01, -y * .01, z * .01) for y, z in
                     ((ymin, 0), (ymax, 0), (ymax, top), (crown, top), (ymin, edge))]
    last = (len(stage['sections']) - 1) * 5
    faces = [tuple(reversed(range(5))), tuple(last + i for i in range(5))]
    for row in range(len(stage['sections']) - 1):
        for col in range(5):
            a, b = row * 5 + col, row * 5 + (col + 1) % 5
            faces.append((a, b, b + 5, a + 5))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    bm = bmesh.new(); bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces)); bm.to_mesh(mesh); bm.free()
    obj = bpy.data.objects.new(name, mesh); bpy.context.collection.objects.link(obj)
    mesh.materials.append(material)
    bpy.ops.object.select_all(action='DESELECT'); obj.select_set(True); bpy.context.view_layer.objects.active = obj
    bevel = obj.modifiers.new('Rounded unsharpened forging edges', 'BEVEL')
    bevel.width = .0005; bevel.segments = 3; bevel.limit_method = 'ANGLE'
    bevel.angle_limit = math.radians(35); bevel.use_clamp_overlap = True
    bpy.ops.object.modifier_apply(modifier=bevel.name)
    bm = bmesh.new(); bm.from_mesh(mesh)
    bmesh.ops.dissolve_degenerate(bm, dist=.000001, edges=list(bm.edges))
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces)); bm.to_mesh(mesh); bm.free()
    for polygon in mesh.polygons: polygon.use_smooth = True
    normal = obj.modifiers.new('Weighted working normals', 'WEIGHTED_NORMAL')
    normal.keep_sharp = True; normal.weight = 50
    bpy.ops.object.modifier_apply(modifier=normal.name)
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=1.15, island_margin=.025); bpy.ops.object.mode_set(mode='OBJECT')
    color = mesh.color_attributes.new(name='Wear', type='FLOAT_COLOR', domain='CORNER')
    for value in color.data: value.color = (.08, 0, 0, 1)
    tri = obj.modifiers.new('Export triangles', 'TRIANGULATE'); bpy.ops.object.modifier_apply(modifier=tri.name)
    path = EXPORT / (name + '.fbx')
    bpy.ops.export_scene.fbx(filepath=str(path), use_selection=True, object_types={'MESH'},
        apply_unit_scale=True, apply_scale_options='FBX_SCALE_NONE', axis_forward='-Y', axis_up='Z',
        use_mesh_modifiers=True, mesh_smooth_type='FACE', use_tspace=True, bake_anim=False)
    outputs.append({'mesh': stage['mesh'], 'file': str(path), 'vertices': len(mesh.vertices), 'triangles': len(mesh.polygons)})
    obj.hide_set(True)
bpy.data.objects['SM_ForgeSingleHandedBlank2'].hide_set(False)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'Single_Handed_Blank_Editable.blend'))
(OUT / 'single_handed_profile.json').write_text(json.dumps(profile, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
(OUT / 'authored.json').write_text(json.dumps({'assets': outputs,
    'silhouette_source': 'SourceAssets/Kukri20261020/model.json',
    'frame': 'UE cm; support Z=0; unchanged sacrificial tong grip (-24,0,.475)',
    'rendered': False, 'runtime_tested': False}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('SINGLE_HANDED_BLANK_AUTHORED ' + str(OUT), flush=True)
