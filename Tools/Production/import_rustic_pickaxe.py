"""Install the supplied rustic pickaxe and its fitted two-hand presentation.

New asset paths keep the former pickaxe recoverable. No PIE or acceptance run.
Run in the live editor, or UnrealEditor-Cmd -run=pythonscript after it is closed.
"""
import json
from pathlib import Path

import unreal as u

ROOT = Path(u.Paths.project_dir()).resolve()
SOURCE = ROOT / 'SourceAssets/RusticPickaxe20260919'
DEST = '/Game/Items/ProductionTools/RusticPickaxe20260919'
TOOLS = u.AssetToolsHelpers.get_asset_tools()
EAL = u.EditorAssetLibrary
LIB = u.MaterialEditingLibrary
is_commandlet = '-run=pythonscript' in u.SystemLibrary.get_command_line().lower()
if not is_commandlet and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
    raise RuntimeError('Stop PIE before importing the rustic pickaxe. No assets changed.')
for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
    if package.get_name().startswith(DEST + '/'):
        raise RuntimeError('Save this pickaxe package first: ' + package.get_name())
report = {'saved': [], 'runtime_tested': False, 'preview_rendered': False}
u.SystemLibrary.execute_console_command(None, 'Interchange.FeatureFlags.Import.FBX 0')
EAL.make_directory(DEST)


def save(asset):
    if not asset or not EAL.save_loaded_asset(asset, False):
        raise RuntimeError('Could not save: ' + str(asset))
    report['saved'].append(asset.get_path_name())
    return asset


def import_asset(file, name, options=None):
    task = u.AssetImportTask()
    task.filename = str(file)
    task.destination_path = DEST
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = True
    if options:
        task.options = options
    TOOLS.import_asset_tasks([task])
    asset = u.load_asset(DEST + '/' + name)
    if not asset:
        raise RuntimeError('Import did not produce ' + name)
    return asset


textures = {}
for label, srgb, compression in (
        ('BaseColor', True, u.TextureCompressionSettings.TC_DEFAULT),
        ('MetallicRoughness', False, u.TextureCompressionSettings.TC_MASKS),
        ('Normal', False, u.TextureCompressionSettings.TC_NORMALMAP)):
    texture = import_asset(SOURCE/'Textures'/(label+'.jpg'), 'T_RusticPickaxe_' + label)
    texture.set_editor_property('srgb', srgb)
    texture.set_editor_property('compression_settings', compression)
    texture.set_editor_property('flip_green_channel', label == 'Normal')
    texture.set_editor_property('never_stream', False)
    # Keep the source resolution for first-person details.
    texture.set_editor_property('max_texture_size', 0)
    textures[label] = save(texture)

material = u.load_asset(DEST + '/M_RusticPickaxe')
if not material:
    material = TOOLS.create_asset('M_RusticPickaxe', DEST, u.Material, u.MaterialFactoryNew())
if not LIB.get_material_expressions(material):
    samplers = {'BaseColor': u.MaterialSamplerType.SAMPLERTYPE_COLOR,
                'MetallicRoughness': u.MaterialSamplerType.SAMPLERTYPE_MASKS,
                'Normal': u.MaterialSamplerType.SAMPLERTYPE_NORMAL}
    samples = {}
    for label, texture in textures.items():
        node = LIB.create_material_expression(material, u.MaterialExpressionTextureSample)
        node.set_editor_property('texture', texture)
        node.set_editor_property('sampler_type', samplers[label])
        samples[label] = node
    for label, channel, prop in (
            ('BaseColor', 'RGB', u.MaterialProperty.MP_BASE_COLOR),
            ('MetallicRoughness', 'G', u.MaterialProperty.MP_ROUGHNESS),
            ('MetallicRoughness', 'B', u.MaterialProperty.MP_METALLIC),
            ('Normal', 'RGB', u.MaterialProperty.MP_NORMAL)):
        LIB.connect_material_property(samples[label], channel, prop)
    LIB.layout_material_expressions(material)
material.set_editor_property('two_sided', False)
material.set_editor_property('used_with_skeletal_mesh', True)
LIB.recompile_material(material)
save(material)

options = u.FbxImportUI()
options.automated_import_should_detect_type = False
options.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
options.import_mesh = True
options.import_as_skeletal = False
options.import_animations = False
options.import_materials = False
options.import_textures = False
options.static_mesh_import_data.combine_meshes = True
options.static_mesh_import_data.auto_generate_collision = True
options.static_mesh_import_data.generate_lightmap_u_vs = True
options.static_mesh_import_data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
world = import_asset(SOURCE/'Export/RusticPickaxe_World.fbx', 'SM_RusticPickaxe', options)
world.set_material(0, material)
mesh_editor = u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
for level in (1, 2):
    if mesh_editor.import_lod(world, level, str(SOURCE/'Export'/f'RusticPickaxe_LOD{level}.fbx')) != level:
        raise RuntimeError('Could not import pickaxe LOD' + str(level))
mesh_editor.set_lod_screen_sizes(world, [1., .35, .1])
nanite = world.get_editor_property('nanite_settings')
nanite.enabled = False
world.set_editor_property('nanite_settings', nanite)
save(world)

options = u.FbxImportUI()
options.automated_import_should_detect_type = False
options.mesh_type_to_import = u.FBXImportType.FBXIT_SKELETAL_MESH
options.import_as_skeletal = True
options.import_mesh = True
options.import_animations = False
options.import_materials = False
options.import_textures = False
options.create_physics_asset = False
options.skeletal_mesh_import_data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
options.skeletal_mesh_import_data.vertex_color_import_option = u.VertexColorImportOption.REPLACE
viewmodel = import_asset(SOURCE/'Export/SK_RusticPickaxe.fbx', 'SK_RusticPickaxe', options)
skeleton = save(viewmodel.get_editor_property('skeleton'))
arms = u.load_asset('/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416')
bindings = {str(slot.material_slot_name): slot.material_interface for slot in arms.get_editor_property('materials')}
bindings['M_RusticPickaxe'] = material
slots = viewmodel.get_editor_property('materials')
for i, slot in enumerate(slots):
    name = str(slot.material_slot_name)
    if name not in bindings:
        raise RuntimeError('Unmapped pickaxe material: ' + name)
    slot.material_interface = bindings[name]
    slots[i] = slot
viewmodel.set_editor_property('materials', slots)
viewmodel.set_editor_property('positive_bounds_extension', u.Vector(80, 80, 80))
viewmodel.set_editor_property('negative_bounds_extension', u.Vector(80, 80, 80))
save(viewmodel)

compression = u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
# The specialised importer below owns Swing/HitRecover and their timing.
for clip in ('Idle', 'Equip', 'Walk', 'Run'):
    options = u.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.mesh_type_to_import = u.FBXImportType.FBXIT_ANIMATION
    options.import_mesh = False
    options.import_animations = True
    options.import_materials = False
    options.import_textures = False
    options.skeleton = skeleton
    options.anim_sequence_import_data.set_editor_property('use_default_sample_rate', False)
    options.anim_sequence_import_data.set_editor_property('custom_sample_rate', 150)
    name = 'A_RusticPickaxe_' + clip
    animation = import_asset(SOURCE/'Export'/(name+'.fbx'), name, options)
    if compression:
        animation.set_editor_property('bone_compression_settings', compression)
    save(animation)

report['world_mesh'] = world.get_path_name()
report['viewmodel'] = viewmodel.get_path_name()
report['animation_prefix'] = DEST + '/A_RusticPickaxe_'
# Switch the catalogue only after all referenced packages have been saved.
# Existing saved pickaxes already refresh these three presentation fields via
# NormalizeProductionState; no item identity or inventory layout is changed.
catalog_path = ROOT / 'Content/ColdSteelData/production_tools.json'
catalog_text = catalog_path.read_text(encoding='utf-8')
definition = json.loads(catalog_text)['tool_pickaxe']
for key, value in (('tool_mesh', report['world_mesh']),
                   ('tool_viewmodel', report['viewmodel']),
                   ('tool_animation_prefix', report['animation_prefix'])):
    before = '"' + key + '": ' + json.dumps(definition[key])
    after = '"' + key + '": ' + json.dumps(value)
    if before not in catalog_text:
        raise RuntimeError('Pickaxe catalogue entry changed: ' + key)
    catalog_text = catalog_text.replace(before, after, 1)
catalog_path.write_text(catalog_text, encoding='utf-8')
# The specialised importer also installs attack timings; keep a full reinstall
# on the current overhead family instead of silently restoring the old swing.
exec(compile((ROOT/'Tools/Production/import_pickaxe_overhead.py').read_text(encoding='utf-8'),
             str(ROOT/'Tools/Production/import_pickaxe_overhead.py'), 'exec'), {'__name__': '__main__'})
report['attack_receipt'] = 'SourceAssets/PickaxeSightline20260919/import_receipt.json'
report['catalogue_updated'] = True
(SOURCE/'import_receipt.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
u.log('RUSTIC_PICKAXE_IMPORTED')
