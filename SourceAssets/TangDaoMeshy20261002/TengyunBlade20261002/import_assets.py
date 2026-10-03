"""Import/save the authored blade, full LODs, PBR, native runes and framed UI icon."""
import json, shutil, runpy
from pathlib import Path
import unreal as u
P = Path(__file__).resolve().parent
ROOT = P.parents[2]
if Path(u.Paths.project_dir()).resolve() != ROOT:
    raise RuntimeError('Tengyun blade assets require the FPSGAME host')
M = json.loads((P / 'blade_manifest.json').read_text(encoding='utf-8'))
D = M['ue_root']
SURFACE_D = M.get('surface_ue_root', D)
REUSE_SURFACE = M.get('reuse_saved_surface', False)
REVISION = M.get('repair_revision', 'TangDaoTengyunBlade20261002')
A, L, E = u.AssetToolsHelpers.get_asset_tools(), u.EditorAssetLibrary, u.MaterialEditingLibrary
previous_file = P / 'import_receipt.json'
previous = json.loads(previous_file.read_text(encoding='utf-8')) if previous_file.exists() else {}
owned_paths = set(previous.get('assets', []))
commandlet = '-run=pythonscript' in u.SystemLibrary.get_command_line().lower()
editor = None if commandlet else u.get_editor_subsystem(u.LevelEditorSubsystem)
playing = bool(editor and editor.is_in_play_in_editor())
if playing:
    raise RuntimeError('Save blade geometry outside PIE; importing in play saved empty LOD render data. Existing play state is preserved.')
receipt = {'revision': REVISION, 'assets': [], 'complete': False, 'runtime_tested': False,
           'mesh': M['mesh'], 'lod_triangles_authored': M['lod_triangles'], 'native_rune_graph_retained': True,
           'mounting_root_unchanged': M.get('mounting_root_unchanged', True), 'nanite_enabled': False,
           'surface_assets_reused_without_writes': REUSE_SURFACE,
           'body_thickness_mm': M.get('body_thickness_mm'),
           'original_surface_material_retained': M.get('original_surface_material_retained', True),
           'uv_z_cm': M.get('uv_z_cm'), 'root_transition_cm': M.get('root_transition_cm'),
           'existing_editor_packages_overwritten': False if SURFACE_D != D else None,
           'ui_icon_preserved': M.get('preserve_ui_icon', False)}

def record():
    (P / 'import_receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def saved(asset):
    # AssetTools duplication supports a live play session; EditorAssetLibrary
    # metadata helpers do not. The saved receipt retains this revision's ownership.
    if not playing:
        L.set_metadata_tag(asset, 'TangDaoTengyunRevision', REVISION)
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()], False):
        raise RuntimeError('Tengyun asset save failed: ' + asset.get_path_name())
    receipt['assets'].append(asset.get_path_name())
    owned_paths.add(asset.get_path_name())
    record()
    return asset

def owned(asset):
    return asset.get_path_name() in owned_paths or (
        not playing and L.get_metadata_tag(asset, 'TangDaoTengyunRevision') == REVISION)

def duplicate(original, path):
    folder, name = path.rsplit('/', 1)
    return A.duplicate_asset(name, folder, original)

def imported(file, path, options=None):
    obj = u.load_asset(path)
    if obj:
        if not owned(obj):
            raise RuntimeError('Preserved an unowned Tengyun asset: ' + path)
        return obj
    task = u.AssetImportTask()
    task.filename = str(file)
    task.destination_path, task.destination_name = path.rsplit('/', 1)
    task.automated = True
    task.replace_existing = False
    task.save = False
    if options:
        task.options = options
    A.import_asset_tasks([task])
    obj = u.load_asset(path)
    if not obj or not task.imported_object_paths:
        raise RuntimeError('Tengyun asset import failed: ' + str(file))
    return obj

record()
textures = {}
for key in ['BaseColor', 'ORM', 'Normal']:
    if REUSE_SURFACE:
        texture = u.load_asset(SURFACE_D + '/Textures/T_TangDao_Tengyun_' + key)
        if not texture:
            raise RuntimeError('Missing the saved Tengyun steel texture: ' + key)
        textures[key] = texture
        continue
    texture = imported(P / 'Textures' / ('TangDao_Tengyun_' + key + '.png'), SURFACE_D + '/Textures/T_TangDao_Tengyun_' + key)
    texture.set_editor_property('srgb', key == 'BaseColor')
    texture.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_NORMALMAP if key == 'Normal' else u.TextureCompressionSettings.TC_MASKS if key == 'ORM' else u.TextureCompressionSettings.TC_BC7)
    texture.set_editor_property('never_stream', False)
    if key == 'Normal':
        texture.set_editor_property('flip_green_channel', True)
    textures[key] = saved(texture)

path = SURFACE_D + '/Materials/' + M.get('material_name', 'M_TangDaoBladeRuneSurface_Tengyun')
material = u.load_asset(path)
if REUSE_SURFACE and not material:
    raise RuntimeError('Missing the saved cloud-compatible Tengyun steel material')
if material and not owned(material) and not REUSE_SURFACE:
    raise RuntimeError('Preserved an unowned Tengyun blade material')
if not material:
    original = u.load_asset(M.get('material_source', '/Game/Weapons/TangDao20261002/SurfaceV2/Materials/M_TangDaoBladeRuneSurface'))
    if not original:
        raise RuntimeError('Missing the current native blade-rune surface')
    material = duplicate(original, path)
    if not material:
        raise RuntimeError('Tengyun native-rune material duplication failed')
    for expression in E.get_material_expressions(material):
        if isinstance(expression, u.MaterialExpressionTextureSample):
            texture = expression.get_editor_property('texture')
            if texture:
                for key in textures:
                    if texture.get_name() in ['T_TangDao_' + key, 'T_TangDao_Tengyun_' + key]:
                        expression.set_editor_property('texture', textures[key])
        if isinstance(expression, u.MaterialExpressionScalarParameter) and str(expression.get_editor_property('parameter_name')) == 'RuneMode':
            expression.set_editor_property('default_value', -1.)
    # Keep all source rune masks, HLSL, exposure compensation and Substrate
    # emission inputs; only the three steel texture bindings are replaced.
if not REUSE_SURFACE:
    errors = list(E.recompile_material(material) or [])
    if errors:
        raise RuntimeError('Tengyun material compilation failed: ' + str(errors))
    saved(material)
temporal_path = path + '_Whirlwind'
temporal = u.load_asset(temporal_path)
if REUSE_SURFACE and not temporal:
    raise RuntimeError('Missing the saved Tengyun temporal material')
if temporal and not owned(temporal) and not REUSE_SURFACE:
    raise RuntimeError('Preserved an unowned Tengyun temporal material')
if not temporal:
    temporal = duplicate(material, temporal_path)
    if not temporal:
        raise RuntimeError('Tengyun temporal material duplication failed')
    response = E.create_material_expression(temporal, u.MaterialExpressionTemporalResponsivenessOutput)
    one = E.create_material_expression(temporal, u.MaterialExpressionConstant)
    one.set_editor_property('r', 1.)
    if not E.connect_material_expressions(one, '', response, ''):
        raise RuntimeError('Tengyun temporal output connection failed')
if not REUSE_SURFACE:
    errors = list(E.recompile_material(temporal) or [])
    if errors:
        raise RuntimeError('Tengyun temporal material compilation failed: ' + str(errors))
    saved(temporal)

options = u.FbxImportUI()
options.automated_import_should_detect_type = False
options.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
options.import_mesh = True
options.import_as_skeletal = False
options.import_materials = False
options.import_textures = False
options.import_animations = False
options.lod_number = 3
options.auto_compute_lod_distances = True
cfg = options.static_mesh_import_data
cfg.combine_meshes = False
cfg.import_mesh_lods = True
cfg.auto_generate_collision = False
cfg.generate_lightmap_u_vs = False
cfg.build_nanite = False
cfg.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
cfg.normal_generation_method = u.FBXNormalGenerationMethod.MIKK_T_SPACE
mesh_path = M['mesh'].split('.')[0]
mesh = imported(P / 'Export' / (M['mesh_name'] + '.fbx'), mesh_path, options)
for index, slot in enumerate(mesh.static_materials):
    name = str(slot.material_slot_name)
    if name not in M['materials']:
        raise RuntimeError('Unexpected Tengyun material slot: ' + name)
    target = u.load_asset(M['materials'][name])
    if not target:
        raise RuntimeError('Missing Tengyun material: ' + name)
    mesh.set_material(index, target)
nanite = mesh.get_editor_property('nanite_settings')
nanite.enabled = False
nanite.explicit_tangents = True
nanite.fallback_relative_error = 0.
mesh.set_editor_property('nanite_settings', nanite)
saved(mesh)

# This blade previously saved three empty LODs during PIE. Do not publish that
# state again: the physical blade must exist before registering its option.
sm = u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
triangles = [mesh.get_num_triangles(i) for i in range(sm.get_lod_count(mesh))]
bounds = mesh.get_bounds()
if len(triangles) != 3 or min(triangles) < 1000 or not 80 < bounds.box_extent.z * 2 < 95:
    raise RuntimeError('Tengyun geometry is incomplete: LODs=' + str(triangles) + ', length_cm=' + str(bounds.box_extent.z * 2))
receipt.update(lod_triangles_saved=triangles, length_cm=bounds.box_extent.z * 2)

icon_name = 'ue_tang_dao_blade_1_tengyun_dragon'
icon_file = P / 'Icons' / (icon_name + '.png')
if not icon_file.exists():
    raise RuntimeError('Finish the actual blade modification icon before publishing the option')
target_file = ROOT / 'Content/ColdSteelData/AttachmentIcons20260913' / icon_file.name
if not M.get('preserve_ui_icon', False):
    shutil.copy2(icon_file, target_file)
    icon = imported(target_file, '/Game/ColdSteelData/AttachmentIcons20260913/' + icon_name)
    icon.set_editor_property('lod_group', u.TextureGroup.TEXTUREGROUP_UI)
    icon.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_EDITOR_ICON)
    icon.set_editor_property('never_stream', True)
    icon.set_editor_property('srgb', True)
    saved(icon)

mapping_path = ROOT / 'Content/ColdSteelData/whirlwind-temporal-materials.json'
mapping = json.loads(mapping_path.read_text(encoding='utf-8-sig'))
backup = P / 'Before' / mapping_path.name
backup.parent.mkdir(exist_ok=True)
if not backup.exists():
    shutil.copy2(mapping_path, backup)
mapping[material.get_path_name()] = temporal.get_path_name()
temporary = mapping_path.with_suffix('.json.tengyun.tmp')
temporary.write_text(json.dumps(mapping, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
temporary.replace(mapping_path)
receipt.update(complete=True, ui_icon=str(target_file), textures={k: v.get_path_name() for k, v in textures.items()},
               material=material.get_path_name(), whirlwind_material=temporal.get_path_name(),
               gameplay_stats_changed=False, runtime_tested=False)
record()
runpy.run_path(str(P / 'catalog_extension.py'), run_name='__main__')
# Retain the full cloud-rune catalog and its base/Yanling/Tengyun bindings when
# this blade alone is re-authored. The joint material already contains its graph.
cloud_extension = P.parent/'CloudRune20261002/catalog_extension.py'
if cloud_extension.exists():
    cloud = runpy.run_path(str(cloud_extension), run_name='tang_dao_cloud_extension')
    if cloud['installed']():
        cloud['install']()
print('TENGYUN_BLADE_ASSETS_SAVED ' + str(len(receipt['assets'])), flush=True)
