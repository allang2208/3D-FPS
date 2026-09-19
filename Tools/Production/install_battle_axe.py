"""Install the weathered battle axe as the FPSGAME lumber axe.

UnrealEditor-Cmd <uproject> -run=pythonscript -script=<this> -unattended -NullRHI -nosplash

Replaces the runtime references of tool_axe on both presentation lines:
  * world/pickup mesh  -> /Game/Items/ProductionTools/BattleAxe20260919/SM_BattleAxe (+2 authored LODs)
  * first-person viewmodel -> /Game/Items/ProductionTools/GripMotion20260913/SK_Harvest_Axe
Retired assets stay on disk. Source textures are the user's Meshy package; textures use sRGB
for BaseColor and linear for normal/metallic/roughness, normal green flipped per project
Meshy convention (see meshy-humanoid.md). No PIE, no render tests.
"""
import hashlib
import json
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.project_dir()).resolve()
SOURCE = ROOT / 'SourceAssets/BattleAxeReplace20260919'
TEX_SRC = SOURCE / 'Input' / 'Meshy_AI_Weathered_Battle_Axe_0918025738_texture_fbx'
FIT = SOURCE / 'Fitted'
VIEWMODEL = SOURCE / 'Viewmodel' / 'Export' / 'SK_Harvest_Axe.fbx'
DEST = '/Game/Items/ProductionTools/BattleAxe20260919'
GRIP = '/Game/Items/ProductionTools/GripMotion20260913'
TOOLS = u.AssetToolsHelpers.get_asset_tools()
EAL = u.EditorAssetLibrary
LIB = u.MaterialEditingLibrary
report = {'saved': [], 'runtime_tested': False,
          'source': 'Meshy_AI_Weathered_Battle_Axe_0918025738_texture_fbx.zip (user asset)'}
u.SystemLibrary.execute_console_command(None, 'Interchange.FeatureFlags.Import.FBX 0')


def save(asset):
    if not asset or not EAL.save_loaded_asset(asset, False):
        raise RuntimeError('Could not save: ' + str(asset))
    report['saved'].append(asset.get_path_name())
    return asset


def import_asset(file, name, options=None, dest=DEST):
    task = u.AssetImportTask()
    task.filename = str(file)
    task.destination_path = dest
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = True
    if options:
        task.options = options
    TOOLS.import_asset_tasks([task])
    asset = u.load_asset(dest + '/' + name)
    if not asset:
        raise RuntimeError('Could not import: ' + str(file))
    return asset


def node(material, cls, **properties):
    result = LIB.create_material_expression(material, cls)
    for key, value in properties.items():
        result.set_editor_property(key, value)
    return result


def wire(source, target, pin, output=''):
    if not LIB.connect_material_expressions(source, output, target, pin):
        raise RuntimeError('Could not connect ' + pin)


EAL.make_directory(DEST)

# ---------------------------------------------------------------- textures
texture_sources = {}
textures = {}
for name, file, srgb, settings, flip_green in [
        ('T_BattleAxe_BaseColor', TEX_SRC / 'Meshy_AI_Weathered_Battle_Axe_0918025738_texture.png', True,
         u.TextureCompressionSettings.TC_DEFAULT, False),
        ('T_BattleAxe_Normal', TEX_SRC / 'Meshy_AI_Weathered_Battle_Axe_0918025738_texture_normal.png', False,
         u.TextureCompressionSettings.TC_NORMALMAP, True),
        ('T_BattleAxe_Metallic', TEX_SRC / 'Meshy_AI_Weathered_Battle_Axe_0918025738_texture_metallic.png', False,
         u.TextureCompressionSettings.TC_MASKS, False),
        ('T_BattleAxe_Roughness', TEX_SRC / 'Meshy_AI_Weathered_Battle_Axe_0918025738_texture_roughness.png', False,
         u.TextureCompressionSettings.TC_MASKS, False)]:
    texture = import_asset(file, name)
    texture.set_editor_property('srgb', srgb)
    texture.set_editor_property('never_stream', False)
    texture.set_editor_property('max_texture_size', 2048)
    texture.set_editor_property('compression_settings', settings)
    # The Meshy FBX carries OpenGL-convention normals; UE wants the green channel flipped.
    texture.set_editor_property('flip_green_channel', flip_green)
    save(texture)
    textures[name] = texture
    texture_sources[name] = {'file': str(file.relative_to(ROOT)),
                             'sha256': hashlib.sha256(file.read_bytes()).hexdigest()}
report['textures'] = texture_sources

# ---------------------------------------------------------------- material
# One material serves both presentation lines. Rebuilding the graph of a material that saved
# meshes already reference can assert !IsRooted and kill the process, so an existing graph is
# kept as-is; to change the graph, build it under a new asset name instead.
material = u.load_asset(DEST + '/M_BattleAxe')
if material and LIB.get_material_expressions(material):
    report['material_build'] = 'skipped: existing graph kept'
else:
    material = material or TOOLS.create_asset('M_BattleAxe', DEST, u.Material, u.MaterialFactoryNew())
    for expression in list(LIB.get_material_expressions(material)):
        LIB.delete_material_expression(material, expression)
    material.set_editor_property('two_sided', False)
    material.set_editor_property('shading_model', u.MaterialShadingModel.MSM_DEFAULT_LIT)
    samples = {}
    for name, sampler in [('T_BattleAxe_BaseColor', u.MaterialSamplerType.SAMPLERTYPE_COLOR),
                          ('T_BattleAxe_Normal', u.MaterialSamplerType.SAMPLERTYPE_NORMAL),
                          ('T_BattleAxe_Metallic', u.MaterialSamplerType.SAMPLERTYPE_MASKS),
                          ('T_BattleAxe_Roughness', u.MaterialSamplerType.SAMPLERTYPE_MASKS)]:
        samples[name] = node(material, u.MaterialExpressionTextureSample, texture=textures[name], sampler_type=sampler)
    for name, property_name, output in [
            ('T_BattleAxe_BaseColor', 'BASE_COLOR', 'RGB'),
            ('T_BattleAxe_Normal', 'NORMAL', 'RGB'),
            ('T_BattleAxe_Metallic', 'METALLIC', 'R'),
            ('T_BattleAxe_Roughness', 'ROUGHNESS', 'R')]:
        if not LIB.connect_material_property(samples[name], output, getattr(u.MaterialProperty, 'MP_' + property_name)):
            raise RuntimeError('Could not bind ' + name)
    LIB.layout_material_expressions(material)
    report['material_build'] = 'built'
# The first-person viewmodel is a skeletal mesh, so the same graph needs that usage flag.
material.set_editor_property('used_with_skeletal_mesh', True)
errors = LIB.recompile_material(material)
if errors:
    raise RuntimeError('M_BattleAxe compile errors: ' + str(errors))
save(material)
report['material'] = material.get_path_name()

# ---------------------------------------------------------------- world mesh + LODs
options = u.FbxImportUI()
options.import_mesh = True
options.import_materials = False
options.import_textures = False
options.import_as_skeletal = False
options.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
options.automated_import_should_detect_type = False
options.static_mesh_import_data.combine_meshes = True
options.static_mesh_import_data.auto_generate_collision = True
options.static_mesh_import_data.generate_lightmap_u_vs = True
options.static_mesh_import_data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
mesh = import_asset(FIT / 'BattleAxe_16000.fbx', 'SM_BattleAxe', options)
mesh.set_material(0, material)
editor = u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
for index, source in [(1, FIT / 'BattleAxe_LOD1.fbx'), (2, FIT / 'BattleAxe_LOD2.fbx')]:
    if editor.import_lod(mesh, index, str(source)) != index:
        raise RuntimeError(f'Could not import tool LOD{index}')
if not editor.set_lod_screen_sizes(mesh, [1.0, 0.35, 0.1]):
    raise RuntimeError('Could not set tool LOD transitions')
settings = mesh.get_editor_property('nanite_settings')
settings.enabled = False
mesh.set_editor_property('nanite_settings', settings)
save(mesh)
report['world_mesh'] = {'asset': mesh.get_path_name(), 'triangles': 16000,
                        'lods': [16000, 2500, 600], 'screen_sizes': [1.0, 0.35, 0.1]}

# ---------------------------------------------------------------- viewmodel
# Slots are matched by name: the arms keep the current M4 arm materials, and the tool slot
# takes M_BattleAxe so both the dropped and the held axe show the new textures. The retired
# M_Harvest_Axe (an old-texture copy) is left untouched on disk.
current_arms = u.load_asset('/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416')
bindings = {str(slot.material_slot_name): slot.material_interface
            for slot in current_arms.get_editor_property('materials')}
bindings['M_Harvest_Axe'] = material
viewmodel_options = u.FbxImportUI()
viewmodel_options.automated_import_should_detect_type = False
viewmodel_options.mesh_type_to_import = u.FBXImportType.FBXIT_SKELETAL_MESH
viewmodel_options.import_as_skeletal = True
viewmodel_options.import_mesh = True
viewmodel_options.import_animations = False
viewmodel_options.import_materials = False
viewmodel_options.import_textures = False
viewmodel_options.create_physics_asset = False
viewmodel_options.skeletal_mesh_import_data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
viewmodel_options.skeletal_mesh_import_data.vertex_color_import_option = u.VertexColorImportOption.REPLACE
viewmodel = import_asset(VIEWMODEL, 'SK_Harvest_Axe', viewmodel_options, dest=GRIP)
# The 2026-09-13 grip-motion import created a skeleton in memory but never saved its package,
# so the mesh and its five clips shipped with a dangling skeleton reference. Persist it here;
# the clips already point at this exact path, so saving it repairs their binding too.
skeleton = viewmodel.get_editor_property('skeleton')
if not skeleton:
    raise RuntimeError('Imported viewmodel has no skeleton')
skeleton_path = skeleton.get_path_name().split('.')[0]
skeleton_existed = EAL.does_asset_exist(skeleton_path)
save(skeleton)
try:
    bone_count = len(skeleton.get_editor_property('bone_tree'))
except Exception:
    bone_count = None
report['skeleton'] = {'asset': skeleton_path, 'existed_before': skeleton_existed, 'bones': bone_count}
slots = viewmodel.get_editor_property('materials')
resolved = []
for i, slot in enumerate(slots):
    name = str(slot.material_slot_name)
    if name not in bindings:
        raise RuntimeError('Unmapped viewmodel material slot: ' + name)
    slot.material_interface = bindings[name]
    slots[i] = slot
    resolved.append({'slot': name, 'material': bindings[name].get_path_name()})
viewmodel.set_editor_property('materials', slots)
viewmodel.set_editor_property('positive_bounds_extension', u.Vector(80, 80, 80))
viewmodel.set_editor_property('negative_bounds_extension', u.Vector(80, 80, 80))
save(viewmodel)
report['viewmodel'] = {'asset': viewmodel.get_path_name(), 'triangles': 32000,
                       'slots': resolved,
                       'skeleton': viewmodel.get_editor_property('skeleton').get_path_name()}

(SOURCE / 'ue-import.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
u.log('BATTLE_AXE_INSTALLED')