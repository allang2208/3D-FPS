"""Import and save one cloven guard and its private PBR; no gameplay tests."""
from datetime import datetime
from pathlib import Path
import json
import os
import shutil
import unreal as u

P = Path(__file__).resolve().parent
ROOT = P.parents[2]
D = '/Game/Weapons/HighlandClaymore20260922/ClovenSurface20261002'
CATALOG = ROOT / 'Content/ColdSteelData/highland-claymore-modules.json'
target = json.loads(CATALOG.read_text(encoding='utf-8-sig'))['slots']['guard']['highland_cloven_guard']['mesh']
expected = '/Game/Weapons/HighlandClaymore20260922/SurfaceRepairV4_20260927/SM_Highland_Guard_Cloven_SurfaceV4.SM_Highland_Guard_Cloven_SurfaceV4'
if target != expected:
    raise RuntimeError('Cloven ownership changed; preserve the current catalog: '+target)
L, E, A = u.EditorAssetLibrary, u.MaterialEditingLibrary, u.AssetToolsHelpers.get_asset_tools()
editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
if os.environ.get('CLOVEN_HEADLESS') != '1' and editor and editor.get_game_world() is not None:
    raise RuntimeError('Current play uses the guard; finish it before importing this asset.')
old_mesh = u.load_asset(target)
if not old_mesh:
    raise RuntimeError('Current cloven guard missing: '+target)
if os.environ.get('CLOVEN_HEADLESS') != '1':
    dirty = u.EditorLoadingAndSavingUtils.get_dirty_content_packages()
    if any(p.get_path_name() == old_mesh.get_outer().get_path_name() for p in dirty):
        raise RuntimeError('The guard contains unsaved editor edits; preserve them before installation.')
stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
before = P / 'Before' / stamp
before.mkdir(parents=True, exist_ok=True)
package = target.split('.')[0]
dest, name = package.rsplit('/', 1)
disk = ROOT / 'Content' / (package.removeprefix('/Game/')+'.uasset')
for suffix in ['.uasset', '.uexp', '.ubulk']:
    source = disk.with_suffix(suffix)
    if source.exists():
        shutil.copy2(source, before / source.name)
materials = {str(slot.material_slot_name): slot.material_interface for slot in old_mesh.static_materials}
S = u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
settings = S.get_lod_build_settings(old_mesh, 0)
nanite = old_mesh.get_editor_property('nanite_settings')
lod_group = old_mesh.get_editor_property('lod_group')
lods = []
count = S.get_lod_count(old_mesh)
if count > 1:
    sizes = S.get_lod_screen_sizes(old_mesh)
    for index in range(count):
        reduction = S.get_lod_reduction_settings(old_mesh, index)
        row = u.EditorScriptingMeshReductionSettings()
        row.percent_triangles = reduction.percent_triangles
        row.screen_size = sizes[index]
        lods.append(row)
receipt = {'revision': 'ArcUV_PBR_20261002', 'target': target,
           'backup': str(before), 'assets': [], 'complete': False, 'tested': False,
           'original_materials': {k: v.get_path_name() if v else None for k, v in materials.items()}}

def record():
    (P / 'install_receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')

def save(asset):
    if not L.save_loaded_asset(asset, False):
        raise RuntimeError('Save failed: '+asset.get_path_name())
    receipt['assets'].append({'asset': asset.get_path_name(), 'saved': True})
    record()

def node(material, cls, **properties):
    value = E.create_material_expression(material, cls)
    for key, prop in properties.items():
        value.set_editor_property(key, prop)
    return value

def wire(a, output, b, pin):
    if not E.connect_material_expressions(a, output, b, pin):
        raise RuntimeError('Material connection failed: '+pin)

textures = {}
for key in ['BaseColor', 'Normal', 'ORM']:
    asset_name = 'T_ClovenWing_'+key
    asset = u.load_asset(D+'/Textures/'+asset_name)
    if asset is None:
        task = u.AssetImportTask()
        task.filename = str(P / 'Textures' / (asset_name+'.png'))
        task.destination_path = D+'/Textures'
        task.destination_name = asset_name
        task.automated = True
        task.replace_existing = False
        task.save = False
        A.import_asset_tasks([task])
        asset = u.load_asset(D+'/Textures/'+asset_name)
        if not asset or not task.imported_object_paths:
            raise RuntimeError('Texture import failed: '+asset_name)
        asset.set_editor_property('srgb', key == 'BaseColor')
        compression = (u.TextureCompressionSettings.TC_NORMALMAP if key == 'Normal' else
                       u.TextureCompressionSettings.TC_MASKS if key == 'ORM' else
                       u.TextureCompressionSettings.TC_DEFAULT)
        asset.set_editor_property('compression_settings', compression)
        group = u.TextureGroup.TEXTUREGROUP_WEAPON_NORMAL_MAP if key == 'Normal' else u.TextureGroup.TEXTUREGROUP_WEAPON
        asset.set_editor_property('lod_group', group)
        asset.set_editor_property('max_texture_size', 2048)
        asset.set_editor_property('lod_bias', 0)
        if key == 'Normal':
            asset.set_editor_property('flip_green_channel', True)
        save(asset)
    textures[key] = asset

material_name = 'M_ClovenWingSurface20261002'
material = u.load_asset(D+'/'+material_name)
if material is None:
    material = A.create_asset(material_name, D, u.Material, u.MaterialFactoryNew())
    material.set_editor_property('blend_mode', u.BlendMode.BLEND_OPAQUE)
    material.set_editor_property('two_sided', False)
    material.set_editor_property('use_material_attributes', False)
    slab = node(material, u.MaterialExpressionSubstrateShadingModels,
                shading_model_override=u.MaterialShadingModel.MSM_DEFAULT_LIT)
    uv = node(material, u.MaterialExpressionTextureCoordinate, coordinate_index=0)
    samples = {}
    for key, sampler in [('BaseColor', u.MaterialSamplerType.SAMPLERTYPE_COLOR),
                         ('Normal', u.MaterialSamplerType.SAMPLERTYPE_NORMAL),
                         ('ORM', u.MaterialSamplerType.SAMPLERTYPE_MASKS)]:
        sample = node(material, u.MaterialExpressionTextureSample, texture=textures[key], sampler_type=sampler)
        wire(uv, '', sample, 'UVs')
        samples[key] = sample
    specular = node(material, u.MaterialExpressionConstant, r=.5)
    for source, output, pin, prop in [
        (samples['BaseColor'], 'RGB', 'BaseColor', u.MaterialProperty.MP_BASE_COLOR),
        (samples['Normal'], 'RGB', 'Normal', u.MaterialProperty.MP_NORMAL),
        (samples['ORM'], 'G', 'Roughness', u.MaterialProperty.MP_ROUGHNESS),
        (samples['ORM'], 'B', 'Metallic', u.MaterialProperty.MP_METALLIC),
        (samples['ORM'], 'R', 'AmbientOcclusion', u.MaterialProperty.MP_AMBIENT_OCCLUSION),
        (specular, '', 'Specular', u.MaterialProperty.MP_SPECULAR)]:
        # AO remains a global material output; this Substrate conversion node
        # exposes the surface inputs but does not have an AmbientOcclusion pin.
        if pin != 'AmbientOcclusion':
            wire(source, output, slab, pin)
        if not E.connect_material_property(source, output, prop):
            raise RuntimeError('Legacy material mirror failed: '+pin)
    if not E.connect_material_property(slab, '', u.MaterialProperty.MP_FRONT_MATERIAL):
        raise RuntimeError('Substrate FrontMaterial connection failed')
    E.layout_material_expressions(material)
    errors = list(E.recompile_material(material) or [])
    if errors:
        raise RuntimeError('Material compilation failed: '+str(errors))
    L.set_metadata_tag(material, 'ClovenSurfaceRevision', 'ArcUV_PBR_20261002')
    save(material)

# Replace geometry at the stable runtime path, keeping the V5 seat and every
# original material by slot name. Only the additional wing slot gets new PBR.
options = u.FbxImportUI()
options.automated_import_should_detect_type = False
options.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
options.import_as_skeletal = False
options.import_mesh = True
options.import_materials = False
options.import_textures = False
options.import_animations = False
cfg = options.static_mesh_import_data
cfg.combine_meshes = True
cfg.auto_generate_collision = False
cfg.generate_lightmap_u_vs = False
cfg.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
cfg.vertex_color_import_option = u.VertexColorImportOption.REPLACE
cfg.import_uniform_scale = 1.
cfg.convert_scene = True
cfg.convert_scene_unit = True
cfg.force_front_x_axis = False
task = u.AssetImportTask()
task.filename = str(P / 'Export/SM_Highland_Guard_Cloven_ArcSurface20261002.fbx')
task.destination_path = dest
task.destination_name = name
task.automated = True
task.replace_existing = True
task.replace_existing_settings = True
task.options = options
task.factory = u.FbxFactory()
task.save = False
A.import_asset_tasks([task])
mesh = u.load_asset(target)
if not mesh or not task.imported_object_paths:
    raise RuntimeError('Guard FBX import failed: '+target)
slots = list(mesh.static_materials)
new_slot = False
for slot in slots:
    key = str(slot.material_slot_name)
    if key.split('.')[0] == material_name:
        slot.material_interface = material
        slot.material_slot_name = material_name
        new_slot = True
    else:
        old = materials.get(key) or materials.get(key.split('.')[0])
        if old is None:
            raise RuntimeError('Unmapped original guard slot: '+key)
        slot.material_interface = old
mesh.static_materials = slots
if not new_slot:
    raise RuntimeError('Imported mesh does not contain the authored wing surface slot')
settings.recompute_normals = False
settings.recompute_tangents = True
settings.use_mikk_t_space = True
settings.use_high_precision_tangent_basis = True
settings.use_full_precision_u_vs = True
S.set_lod_build_settings(mesh, 0, settings)
mesh.set_editor_property('nanite_settings', nanite)
mesh.set_editor_property('lod_group', lod_group)
if lods:
    reductions = u.EditorScriptingMeshReductionOptions()
    reductions.auto_compute_lod_screen_size = False
    reductions.reduction_settings = lods
    S.set_lods(mesh, reductions)
L.set_metadata_tag(mesh, 'ClovenSurfaceRevision', 'ArcUV_PBR_20261002')
L.set_metadata_tag(mesh, 'HighlandSource', task.filename)
save(mesh)
receipt['materials'] = {str(s.material_slot_name): s.material_interface.get_path_name() for s in slots}
receipt['complete'] = True
record()
print('CLOVEN_SURFACE_INSTALL_COMPLETE '+target)
