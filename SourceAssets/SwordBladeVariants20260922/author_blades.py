"""Six blade variants from the accepted factory surfaces. UI assets, no review renders."""
import bpy
import json
import math
import numpy as np
from pathlib import Path
from mathutils import Matrix, Vector

P = Path(__file__).resolve().parent
ROOT = P.parents[1]
OUT = P / 'Export'
ICONS = P / 'Icons'
OUT.mkdir(exist_ok=True)
ICONS.mkdir(exist_ok=True)
bpy.context.preferences.filepaths.save_version = 0
OPTIONS = ['extended_edge', 'heavy_spine', 'feather_edge']
HOSTS = [
    dict(key='Frost', weapon='ue_frost_crystal_sword', catalog='frost-sword-modules.json',
         source='FrostSwordModules20260915/FrostSword_Modular_Editable.blend',
         object='SM_FrostSword_Blade_factory', root=.085, spread=.14),
    dict(key='Rune', weapon='ue_rune_sword', catalog='rune-sword-modules.json',
         source='RuneSwordModules20260919/RuneSword_Modular_Editable.blend',
         object='SM_RuneSword_Blade_factory', root=.165, spread=.12),
]


def smooth(t):
    t = np.clip(t, 0., 1.)
    return t * t * (3. - 2. * t)


def shape(points, option, host, low, high):
    """Continuous deformation; the original mounting region has identity Jacobian."""
    x, y, z = points.T
    root = host['root']
    free_length = high - root
    t = np.clip((z - root) / free_length, 0., 1.)
    shoulder = smooth(t / .20)
    # Protect the central native glyph lane; reshape the shoulders and cutting edges.
    outer = smooth((np.abs(x) - .012) / .018)
    q = points.copy()
    if option == 'extended_edge':
        q[:, 2] += .15 * (high - low) * smooth(t)
        q[:, 0] *= 1. - .035 * smooth((t - .45) / .55) * outer
    elif option == 'heavy_spine':
        body = shoulder * (1. - .72 * smooth((t - .60) / .40))
        q[:, 0] *= 1. + host['spread'] * body * outer
        spine = np.exp(-np.square(x / .024))
        q[:, 1] *= 1. + body * (.14 + .26 * spine)
    elif option == 'feather_edge':
        body = shoulder * (1. - .25 * smooth((t - .82) / .18))
        q[:, 0] *= 1. - .145 * body * outer
        q[:, 1] *= 1. - body * (.05 + .19 * outer)
    return q


def deform(base, option, host, coords):
    obj = base.copy()
    obj.data = base.data.copy()
    obj.name = 'SM_' + host['key'] + 'Sword_Blade_' + option + '_V1'
    bpy.context.scene.collection.objects.link(obj)
    mesh = obj.data
    normal = np.array([tuple(n.vector) for n in mesh.corner_normals], dtype=np.float64)
    low, high = coords[:, 2].min(), coords[:, 2].max()
    fn = lambda p: shape(p, option, host, low, high)
    changed = fn(coords)
    # Transform imported split normals by the inverse transpose of the local map.
    eps = 1.e-6
    jac = np.empty((len(coords), 3, 3), dtype=np.float64)
    for axis in range(3):
        offset = np.zeros(3)
        offset[axis] = eps
        jac[:, :, axis] = (fn(coords + offset) - fn(coords - offset)) / (2. * eps)
    inv_t = np.linalg.inv(jac).transpose(0, 2, 1)
    indices = np.array([loop.vertex_index for loop in mesh.loops], dtype=np.int32)
    normal = np.einsum('nij,nj->ni', inv_t[indices], normal)
    normal /= np.maximum(np.linalg.norm(normal, axis=1, keepdims=True), 1.e-12)
    mesh.vertices.foreach_set('co', changed.astype(np.float32).ravel())
    # Set smooth BEFORE split normals, retaining the source's hard corners.
    for face in mesh.polygons:
        face.use_smooth = True
    mesh.update()
    mesh.normals_split_custom_set(normal.tolist())
    if 'SurfaceNormal' in mesh.attributes:
        mesh.attributes['SurfaceNormal'].data.foreach_set('vector', normal.astype(np.float32).ravel())
    obj['blade_variant'] = option
    obj['factory_source'] = host['source']
    obj['frozen_root_z_m'] = host['root']
    obj['detail_policy'] = 'Original topology, UV layers, corner colors and material indices retained.'
    return obj, fn, changed


def export(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.hide_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.fbx(
        filepath=str(OUT / (obj.name + '.fbx')), use_selection=True,
        object_types={'MESH'}, axis_forward='-Y', axis_up='Z',
        add_leaf_bones=False, bake_anim=False, mesh_smooth_type='FACE', use_tspace=True)


def icon_studio(objects, host):
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 48
    scene.cycles.use_denoising = True
    scene.render.resolution_x = scene.render.resolution_y = 1024
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Medium High Contrast'
    scene.world = bpy.data.worlds.new('Neutral blade icon studio')
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.2, .2, .2, 1)
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .65
    camera = bpy.data.objects.new('Blade icon camera - tip left', bpy.data.cameras.new('Blade icon camera'))
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.data.type = 'ORTHO'
    camera.data.clip_start = .001
    camera.data.ortho_scale = max(o.dimensions.z for o in objects.values()) / .84
    # Camera right = -blade Z; camera up = blade X. No image mirroring.
    camera.rotation_euler = Matrix(((0, 1, 0), (0, 0, -1), (-1, 0, 0))).to_euler()
    lamps = []
    for name, offset, energy, size in [
        ('Key', (.38, -.60, .35), 95, .75),
        ('Fill', (-.32, -.42, -.15), 45, .65),
        ('Rim', (.12, .28, .30), 65, .50),
    ]:
        lamp = bpy.data.objects.new(name, bpy.data.lights.new(name, 'AREA'))
        scene.collection.objects.link(lamp)
        lamp.data.energy = energy
        lamp.data.shape = 'DISK'
        lamp.data.size = size
        lamps.append((lamp, Vector(offset)))
    for option, obj in objects.items():
        for other in objects.values():
            other.hide_render = other != obj
        obj.hide_set(False)
        center = sum((Vector(v) for v in obj.bound_box), Vector()) / 8
        camera.location = center + Vector((0, -1.5, 0))
        for lamp, offset in lamps:
            lamp.location = center + offset
            lamp.rotation_euler = (center - lamp.location).to_track_quat('-Z', 'Y').to_euler()
        filename = host['weapon'] + '_blade_1_' + option + '.png'
        scene.render.filepath = str(ICONS / filename)
        bpy.ops.render.render(write_still=True)
        print('BLADE_MENU_ICON ' + filename, flush=True)


manifest = []
for host in HOSTS:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system = 'METRIC'
    source = ROOT / 'SourceAssets' / host['source']
    with bpy.data.libraries.load(str(source), link=False) as (src, dst):
        dst.objects = [host['object']]
    base = dst.objects[0]
    bpy.context.scene.collection.objects.link(base)
    base.hide_set(False)
    base.hide_render = False
    base.location = Vector((0, 0, 0))
    coords = np.array([tuple(v.co) for v in base.data.vertices], dtype=np.float64)
    catalog = json.loads((ROOT / 'Content/ColdSteelData' / host['catalog']).read_text(encoding='utf-8'))
    factory = catalog['slots']['blade_1']['factory']
    objects = {}
    for option in OPTIONS:
        obj, fn, changed = deform(base, option, host, coords)
        export(obj)
        obj.hide_render = True
        objects[option] = obj
        dims = list(factory['rune_dimensions_cm'])
        # Projected effects follow the new axial span; UV0 native ink remains attached.
        ends = np.array([[0, 0, dims[1] / 100.], [0, 0, (dims[1] + dims[2]) / 100.]])
        new_ends = fn(ends)
        dims[1] = float(new_ends[0, 2] * 100.)
        dims[2] = float((new_ends[1, 2] - new_ends[0, 2]) * 100.)
        dims[0] *= 1. + host['spread'] if option == 'heavy_spine' else .88 if option == 'feather_edge' else 1.
        manifest.append(dict(weapon=host['weapon'], catalog=host['catalog'], option=option,
            mesh=obj.name, source=str(source), object=host['object'],
            donor=factory['mesh'], rune_dimensions_cm=dims,
            material_slot_names=[m.name if m else '' for m in obj.data.materials],
            bounds_m=[changed.min(axis=0).tolist(), changed.max(axis=0).tolist()],
            frozen_root_z_m=host['root'],
            icon=host['weapon'] + '_blade_1_' + option + '.png'))
    base.hide_render = True
    base.hide_set(True)
    bpy.context.view_layer.update()
    icon_studio(objects, host)
    for obj in objects.values():
        obj.hide_render = False
        obj.hide_set(True)
    objects['extended_edge'].hide_set(False)
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(P / (host['key'] + 'Sword_Blades_V1_Editable.blend')))
    (P / 'variants.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('SIX_SWORD_BLADES_AUTHORED', flush=True)
