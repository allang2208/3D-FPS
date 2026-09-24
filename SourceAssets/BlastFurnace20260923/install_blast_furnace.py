"""Install the authored blast furnace into the project (background commandlet).

    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' \
        'D:/FPS3D/FPSGAME/FPSGAME.uproject' -run=pythonscript \
        '-script=D:/FPS3D/FPSGAME/SourceAssets/BlastFurnace20260923/install_blast_furnace.py' \
        -unattended -nop4 -nosplash -abslog=.../install-blast-furnace.log

Three guarded stages in one process, so the project is loaded once:

1. import the seven generated PBR map sets and build one material each;
2. import ``SM_BlastFurnace.fbx`` and bind the seven slots by name;
3. append one entry to the active voxel build palette.

Every stage skips work that already exists and says so, so a re-run never
silently overwrites a revision. Nothing is placed in a level and no PIE,
screenshot or acceptance run happens here.
"""
import json
import math
import re
from pathlib import Path

import unreal as u

HERE = Path(__file__).resolve().parent
ROOT = '/Game/Props/BlastFurnace20260923'
TEX_ROOT = ROOT + '/Textures'
MAT_ROOT = ROOT + '/Materials'
MESH_PATH = ROOT + '/SM_BlastFurnace'
PALETTE = '/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette'

MATERIAL_SPEC = [
    ('BlastFurnace_Masonry', (0.34, 0.33, 0.31), 0.78, 0.0),
    ('BlastFurnace_Firebrick', (0.36, 0.29, 0.23), 0.82, 0.0),
    ('BlastFurnace_WroughtIron', (0.16, 0.15, 0.15), 0.45, 0.90),
    ('BlastFurnace_ClayLuting', (0.30, 0.21, 0.15), 0.88, 0.0),
    ('BlastFurnace_SlagLining', (0.18, 0.17, 0.17), 0.60, 0.05),
    ('BlastFurnace_EmberBed', (0.13, 0.12, 0.12), 0.80, 0.0),
    ('BlastFurnace_OreLump', (0.19, 0.16, 0.14), 0.72, 0.10),
]
CHANNELS = ('BaseColor', 'Roughness', 'Metallic', 'Normal', 'AO')

ASSETS = u.AssetToolsHelpers.get_asset_tools()
EDITOR = u.EditorAssetLibrary
MATERIALS_LIB = u.MaterialEditingLibrary
receipt = {'root': ROOT, 'stages': {}, 'runtime_tested': False, 'rendered': False}


def log(message):
    print('[blast_furnace] ' + message, flush=True)


def save(asset):
    package = u.load_package(asset.get_path_name().split('.')[0])
    if not u.EditorLoadingAndSavingUtils.save_packages([package], False):
        raise RuntimeError('Save failed: ' + asset.get_path_name())


def connect(source, source_pin, target, target_pin):
    # connect_material_expressions returns False without raising, so every link
    # has to be checked or the material compiles with a silently empty pin.
    if not MATERIALS_LIB.connect_material_expressions(source, source_pin, target, target_pin):
        raise RuntimeError('Material link failed: %s -> %s' % (source_pin, target_pin))


def connect_output(node, pin, prop):
    if not MATERIALS_LIB.connect_material_property(node, pin, prop):
        raise RuntimeError('Material output failed: ' + str(prop))


# ----------------------------------------------------------------------
# stage 1: textures and materials
# ----------------------------------------------------------------------
def import_textures():
    imported = []
    for name, *_rest in MATERIAL_SPEC:
        for channel in CHANNELS:
            png = HERE / 'Authored' / 'Textures' / ('%s_%s.png' % (name, channel))
            if not png.exists():
                raise RuntimeError('Missing generated map: ' + str(png))
            asset_name = 'T_%s_%s' % (name, channel)
            asset_path = '%s/%s' % (TEX_ROOT, asset_name)
            if EDITOR.does_asset_exist(asset_path):
                imported.append(asset_path)
                continue
            task = u.AssetImportTask()
            task.filename = str(png)
            task.destination_path = TEX_ROOT
            task.destination_name = asset_name
            task.automated = True
            task.replace_existing = False
            task.save = False
            ASSETS.import_asset_tasks([task])
            if not EDITOR.does_asset_exist(asset_path):
                raise RuntimeError('Texture import failed: ' + asset_path)
            imported.append(asset_path)
    # Colour data is sRGB; every other channel is linear data and must not be
    # gamma-decoded on sampling.
    for asset_path in imported:
        texture = u.load_asset(asset_path)
        if texture is None:
            raise RuntimeError('Texture missing after import: ' + asset_path)
        srgb = asset_path.endswith('_BaseColor')
        texture.set_editor_property('srgb', srgb)
        if asset_path.endswith('_Normal'):
            texture.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_NORMALMAP)
        elif not srgb:
            texture.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_MASKS)
        else:
            texture.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_DEFAULT)
        # Read the values back: a wrong enum name falls back to the default
        # silently in this build.
        if bool(texture.get_editor_property('srgb')) != srgb:
            raise RuntimeError('sRGB did not stick on ' + asset_path)
        save(texture)
    receipt['stages']['textures'] = {'count': len(imported), 'folder': TEX_ROOT}
    log('textures %d' % len(imported))


def build_materials():
    built = []
    for name, color, roughness, metallic in MATERIAL_SPEC:
        mat_path = '%s/M_%s' % (MAT_ROOT, name)
        if EDITOR.does_asset_exist(mat_path):
            built.append(mat_path)
            log('material exists, kept: ' + mat_path)
            continue
        mat = ASSETS.create_asset('M_' + name, MAT_ROOT, u.Material, u.MaterialFactoryNew())
        if mat is None:
            raise RuntimeError('Could not create material ' + mat_path)
        tint = MATERIALS_LIB.create_material_expression(mat, u.MaterialExpressionVectorParameter)
        tint.set_editor_property('parameter_name', 'BaseTint')
        tint.set_editor_property('default_value', u.LinearColor(color[0], color[1], color[2], 1.0))

        def sampler(channel):
            node = MATERIALS_LIB.create_material_expression(mat, u.MaterialExpressionTextureSampleParameter2D)
            node.set_editor_property('parameter_name', channel)
            node.set_editor_property('texture', u.load_asset('%s/T_%s_%s' % (TEX_ROOT, name, channel)))
            if channel == 'BaseColor':
                node.set_editor_property('sampler_type', u.MaterialSamplerType.SAMPLERTYPE_COLOR)
            else:
                node.set_editor_property('sampler_type', u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
            return node

        base = sampler('BaseColor')
        ao = sampler('AO')
        # Base colour is attenuated by the baked occlusion; a colour-only map
        # would not be a PBR set.
        tinted = MATERIALS_LIB.create_material_expression(mat, u.MaterialExpressionMultiply)
        connect(tint, 'RGB', tinted, 'A')
        connect(base, 'RGB', tinted, 'B')
        occluded = MATERIALS_LIB.create_material_expression(mat, u.MaterialExpressionMultiply)
        connect(tinted, '', occluded, 'A')
        connect(ao, 'R', occluded, 'B')
        connect_output(occluded, '', u.MaterialProperty.MP_BASE_COLOR)

        roughness_scale = MATERIALS_LIB.create_material_expression(mat, u.MaterialExpressionScalarParameter)
        roughness_scale.set_editor_property('parameter_name', 'RoughnessScale')
        roughness_scale.set_editor_property('default_value', 1.0)
        rough = sampler('Roughness')
        rough_mul = MATERIALS_LIB.create_material_expression(mat, u.MaterialExpressionMultiply)
        connect(rough, 'R', rough_mul, 'A')
        connect(roughness_scale, '', rough_mul, 'B')
        connect_output(rough_mul, '', u.MaterialProperty.MP_ROUGHNESS)

        metallic_scale = MATERIALS_LIB.create_material_expression(mat, u.MaterialExpressionScalarParameter)
        metallic_scale.set_editor_property('parameter_name', 'MetallicScale')
        metallic_scale.set_editor_property('default_value', 1.0)
        metal = sampler('Metallic')
        metal_mul = MATERIALS_LIB.create_material_expression(mat, u.MaterialExpressionMultiply)
        connect(metal, 'R', metal_mul, 'A')
        connect(metallic_scale, '', metal_mul, 'B')
        connect_output(metal_mul, '', u.MaterialProperty.MP_METALLIC)

        # Unpack the tangent-space normal by hand: (sample * 2) + (-1). This
        # avoids depending on whether the NormalMap expression class is exposed
        # to Python in this build.
        normal = sampler('Normal')
        two = MATERIALS_LIB.create_material_expression(mat, u.MaterialExpressionConstant)
        two.set_editor_property('r', 2.0)
        minus_one = MATERIALS_LIB.create_material_expression(mat, u.MaterialExpressionConstant)
        minus_one.set_editor_property('r', -1.0)
        scaled = MATERIALS_LIB.create_material_expression(mat, u.MaterialExpressionMultiply)
        connect(normal, 'RGB', scaled, 'A')
        connect(two, '', scaled, 'B')
        unpacked = MATERIALS_LIB.create_material_expression(mat, u.MaterialExpressionAdd)
        connect(scaled, '', unpacked, 'A')
        connect(minus_one, '', unpacked, 'B')
        connect_output(unpacked, '', u.MaterialProperty.MP_NORMAL)

        errors = MATERIALS_LIB.recompile_material(mat)
        # recompile_material returns the error list; [] is success.
        if errors:
            raise RuntimeError('Material compile failed for %s: %s' % (name, errors))
        if MATERIALS_LIB.get_material_property_input_node(mat, u.MaterialProperty.MP_BASE_COLOR) is None:
            raise RuntimeError('Base colour ended up unconnected on ' + name)
        EDITOR.set_metadata_tag(mat, 'Source', 'BlastFurnace20260923 authored PBR set')
        save(mat)
        built.append(mat_path)
    receipt['stages']['materials'] = {'count': len(built), 'folder': MAT_ROOT}
    log('materials %d' % len(built))


# ----------------------------------------------------------------------
# stage 2: the mesh
# ----------------------------------------------------------------------
def import_mesh():
    if EDITOR.does_asset_exist(MESH_PATH):
        mesh = u.load_asset(MESH_PATH)
        log('mesh exists, kept: ' + MESH_PATH)
        receipt['stages']['mesh'] = {'asset': MESH_PATH, 'imported': False,
                                     'slots': [str(s.get_editor_property('material_slot_name'))
                                               for s in mesh.get_editor_property('static_materials')]}
        return mesh
    fbx = HERE / 'Authored' / 'SM_BlastFurnace.fbx'
    if not fbx.exists():
        raise RuntimeError('Missing FBX: ' + str(fbx))
    options = u.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
    options.import_mesh = True
    options.import_as_skeletal = False
    options.import_materials = False
    options.import_textures = False
    data = options.static_mesh_import_data
    data.combine_meshes = True
    data.auto_generate_collision = False
    data.generate_lightmap_u_vs = True
    data.transform_vertex_to_absolute = True
    data.convert_scene = True
    data.convert_scene_unit = True
    data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    task = u.AssetImportTask()
    task.filename = str(fbx)
    task.destination_path = ROOT
    task.destination_name = 'SM_BlastFurnace'
    task.automated = True
    task.replace_existing = False
    task.save = False
    task.options = options
    task.factory = u.FbxFactory()
    ASSETS.import_asset_tasks([task])
    mesh = u.load_asset(MESH_PATH)
    if mesh is None:
        raise RuntimeError('Furnace FBX import failed')

    slots = []
    bound = []
    for index, slot in enumerate(mesh.get_editor_property('static_materials')):
        raw = str(slot.get_editor_property('material_slot_name'))
        name = re.sub(r'[._][0-9]{3}$', '', raw)
        mat = u.load_asset('%s/M_%s' % (MAT_ROOT, name))
        if mat is None:
            raise RuntimeError('Required furnace material missing: ' + name)
        mesh.set_material(index, mat)
        slots.append(name)
        bound.append(mat.get_path_name())
    if len(slots) != len(MATERIAL_SPEC):
        raise RuntimeError('Expected %d material slots, FBX gave %d: %s'
                           % (len(MATERIAL_SPEC), len(slots), slots))

    # The charging bowl is concave, so one convex hull would fill the mouth.
    # Triangle collision keeps the interior open and still stops bullets.
    mesh.get_editor_property('body_setup').set_editor_property(
        'collision_trace_flag', u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    nanite = mesh.get_editor_property('nanite_settings')
    nanite.enabled = True
    mesh.set_editor_property('nanite_settings', nanite)
    EDITOR.set_metadata_tag(mesh, 'SourceAuthoring', 'SourceAssets/BlastFurnace20260923/author_blast_furnace.py')
    EDITOR.set_metadata_tag(mesh, 'PlacementContract', '20 cm lattice, bounds-centred pivot, base on Z = 0')
    save(mesh)

    box = mesh.get_bounds()
    size = [2 * box.box_extent.x, 2 * box.box_extent.y, 2 * box.box_extent.z]
    # The 20 cm-lattice footprint is a save contract; assert it here so a
    # silently rescaled import can never be registered as a prefab.
    for measured, expected in zip(size, (120.0, 100.0, 220.0)):
        if abs(measured - expected) > 0.5:
            raise RuntimeError('Imported mesh has the wrong scale: %s, expected 120/100/220' % size)
    receipt['stages']['mesh'] = {'asset': MESH_PATH, 'imported': True, 'slots': slots,
                                 'materials': bound,
                                 'size_cm': [round(v, 3) for v in size],
                                 'collision': 'CTF_USE_COMPLEX_AS_SIMPLE', 'nanite': True}
    log('mesh imported, slots %s, size %s' % (slots, receipt['stages']['mesh']['size_cm']))
    return mesh


# ----------------------------------------------------------------------
# stage 3: building palette entry
# ----------------------------------------------------------------------
def register_prefab(mesh):
    palette = u.load_asset(PALETTE)
    if palette is None:
        raise RuntimeError('Active building palette missing: ' + PALETTE)
    box = mesh.get_bounds()
    size = [2 * box.box_extent.x, 2 * box.box_extent.y, 2 * box.box_extent.z]
    cells = [max(1, math.ceil((v - 0.01) / 20.0)) for v in size]
    offset_z = -(cells[2] * 20.0 - size[2]) / 2.0
    available = [str(m.get_editor_property('id')) for m in palette.get_editor_property('materials')]
    drawer = 'stone' if 'stone' in available else ''
    if any(str(e.get_editor_property('id')) == 'blast_furnace'
           for e in palette.get_editor_property('components')):
        log('blast_furnace already registered; entry preserved')
        receipt['stages']['palette'] = {'palette': PALETTE, 'registered': False,
                                        'existing_ids': available}
        return
    entry = u.VoxelBuildPrefab()
    entry.set_editor_property('id', 'blast_furnace')
    entry.set_editor_property('display_name', u.Text('冶炼高炉'))
    entry.set_editor_property('mesh', mesh)
    entry.set_editor_property('footprint', u.IntVector(cells[0], cells[1], cells[2]))
    entry.set_editor_property('material', drawer)
    # ComputeTransform centres the mesh in its occupied volume; the vertical
    # rounding margin is subtracted so the bed actually sits on the ground.
    entry.set_editor_property('pivot_offset_cm', u.Vector(0.0, 0.0, offset_z))
    components = list(palette.get_editor_property('components'))
    palette.modify()
    components.append(entry)
    palette.set_editor_property('components', components)
    if not u.EditorLoadingAndSavingUtils.save_packages([u.load_package(PALETTE)], False):
        raise RuntimeError('Palette save failed')
    receipt['stages']['palette'] = {
        'palette': PALETTE, 'registered': True, 'id': 'blast_furnace', 'name': '冶炼高炉',
        'drawer_material': drawer, 'available_materials': available,
        'mesh_size_cm': [round(v, 3) for v in size], 'footprint': cells,
        'pivot_offset_cm': [0.0, 0.0, round(offset_z, 5)]}
    log('palette entry added: %s cells=%s offset_z=%.5f drawer=%s'
        % (receipt['stages']['palette']['id'], cells, offset_z, drawer or '(none)'))


def main():
    import_textures()
    build_materials()
    mesh = import_mesh()
    register_prefab(mesh)
    receipt['runtime_tested'] = False
    (HERE / 'install_receipt.json').write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
    print('BLAST_FURNACE_INSTALL_DONE ' + json.dumps(receipt, ensure_ascii=False), flush=True)


main()
