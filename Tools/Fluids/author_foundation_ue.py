"""Save the free fluid foundation in an isolated UE commandlet project.

Run with PythonScript commandlet, unattended + NullRHI. Never opens a level,
starts PIE, renders a preview, or writes into existing FPSGAME assets.
FLUID_FOUNDATION_STAGES may select templates,volume,liquid,water for resuming.
"""
import json
import os
from pathlib import Path

import unreal

PROJECT = Path(__file__).resolve().parents[2]
SOURCE = PROJECT / 'SourceAssets' / 'FluidFoundation20260923'
DEST = '/Game/Fluids/Foundation'
EAL = unreal.EditorAssetLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
MEL = unreal.MaterialEditingLibrary
unreal.AssetRegistryHelpers.get_asset_registry().scan_paths_synchronous([DEST], force_rescan=True)
STAGE = ''
SAVED = []


def save(asset, origin):
    EAL.set_metadata_tag(asset, 'FluidFoundation.Source', origin)
    EAL.set_metadata_tag(asset, 'FluidFoundation.Status', 'Authored; runtime and visual testing not performed')
    if not EAL.save_loaded_asset(asset, only_if_is_dirty=False):
        raise RuntimeError('Save failed: ' + asset.get_path_name())
    path = asset.get_path_name()
    SAVED.append(path)
    (SOURCE / ('ue-' + STAGE + '-saved.json')).write_text(
        json.dumps(SAVED, indent=2), encoding='utf-8')
    print('FLUID_ASSET_SAVED ' + path, flush=True)
    return asset


def duplicate(source, path):
    folder, name = path.rsplit('/', 1)
    obj = EAL.load_asset(path) if EAL.does_asset_exist(path) else TOOLS.duplicate_asset(name, folder, unreal.load_asset(source))
    if not obj:
        raise RuntimeError('Duplicate failed: ' + source)
    return obj


def create(path, cls, factory):
    if EAL.does_asset_exist(path):
        return EAL.load_asset(path)
    folder, name = path.rsplit('/', 1)
    obj = TOOLS.create_asset(name, folder, cls, factory)
    if not obj:
        raise RuntimeError('Create failed: ' + path)
    return obj


def blueprint(path, parent):
    factory = unreal.BlueprintFactory()
    factory.set_editor_property('parent_class', parent)
    bp = create(path, unreal.Blueprint, factory)
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    return bp, unreal.get_default_object(bp.generated_class())


def finish_bp(bp, origin):
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    return save(bp, origin)


def component_blueprint(path, component_class):
    bp, _ = blueprint(path, unreal.Actor)
    subsystem = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    library = unreal.SubobjectDataBlueprintFunctionLibrary
    handles = subsystem.k2_gather_subobject_data_for_blueprint(bp)
    for handle in handles:
        obj = library.get_object_for_blueprint(library.get_data(handle), bp)
        if isinstance(obj, component_class):
            return bp, obj
    params = unreal.AddNewSubobjectParams(parent_handle=handles[0],
                                          new_class=component_class, blueprint_context=bp)
    handle, reason = subsystem.add_new_subobject(params=params)
    obj = library.get_object_for_blueprint(library.get_data(handle), bp)
    if not obj:
        raise RuntimeError('Could not add component: ' + str(reason))
    return bp, obj


def templates():
    for template, name in [
        ('Gas/2D/Systems/Grid2D_Gas_Smoke', 'NS_Smoke2D'),
        ('Gas/2D/Systems/Grid2D_Gas_SmokeFire', 'NS_Fire2D'),
        ('Gas/3D/Systems/Grid3D_Gas_Smoke', 'NS_Smoke3D_Local'),
        ('Gas/3D/Systems/Grid3D_Gas_Fire', 'NS_Fire3D_Local')]:
        origin = '/NiagaraFluids/Templates/' + template
        system = save(duplicate(origin, DEST + '/Niagara/' + name), origin)
        bp, cdo = blueprint(DEST + '/Actors/BP_' + name[3:], unreal.NiagaraActor)
        component = cdo.get_editor_property('niagara_component')
        component.set_asset(system)
        component.set_auto_activate(True)
        finish_bp(bp, origin + '; Epic template-derived authoring baseline')


def expr(mat, cls, **props):
    node = MEL.create_material_expression(mat, cls)
    for key, value in props.items():
        node.set_editor_property(key, value)
    return node


def connect(src, output, target, pin):
    if not MEL.connect_material_expressions(src, output, target, pin):
        raise RuntimeError('Cannot connect material input ' + pin)


def prop(src, output, target):
    if not MEL.connect_material_property(src, output, target):
        raise RuntimeError('Cannot connect material property ' + str(target))


def scalar(mat, name, value):
    return expr(mat, unreal.MaterialExpressionScalarParameter, parameter_name=name, default_value=value)


def mul(mat, a, b):
    node = expr(mat, unreal.MaterialExpressionMultiply)
    connect(a, '', node, 'A')
    connect(b, '', node, 'B')
    return node


def import_file(filename, folder, name, factory, options=None):
    path = folder + '/' + name
    if EAL.does_asset_exist(path):
        return EAL.load_asset(path)
    task = unreal.AssetImportTask()
    for key, value in dict(filename=str(filename), destination_path=folder,
                           destination_name=name, automated=True,
                           replace_existing=False, save=True, factory=factory).items():
        task.set_editor_property(key, value)
    if options is not None:
        task.set_editor_property('options', options)
    TOOLS.import_asset_tasks([task])
    results = task.get_objects()
    if not results:
        raise RuntimeError('Import produced no asset: ' + str(filename))
    return results[0]


def volume():
    manifest = json.loads((SOURCE / 'Fire/bake-manifest.json').read_text(encoding='utf-8'))
    # The SVT factory names sequences from their filename prefix (fluid_data).
    svt = import_file(manifest['files'][0], DEST + '/Volumes', 'fluid_data',
                      unreal.SparseVolumeTextureFactory())
    save(svt, manifest['source'])
    # UE's unattended importer packs the seven source scalar components in order:
    # AttributesA = density, flame, shadow, temperature; AttributesB.xyz = velocity.
    layout = [(g['name'], g['channels']) for g in manifest['grids']]
    if layout != [('density', 1), ('flame', 1), ('shadow', 1), ('temperature', 1), ('velocity', 3)]:
        raise RuntimeError('Source VDB layout changed; update explicit material channel mapping')
    for fire in (False, True):
        name = 'Fire' if fire else 'Smoke'
        mat = create(DEST + '/Materials/M_SVT_' + name, unreal.Material, unreal.MaterialFactoryNew())
        mat.set_editor_property('material_domain', unreal.MaterialDomain.MD_VOLUME)
        mat.set_editor_property('blend_mode', unreal.BlendMode.BLEND_ADDITIVE)
        MEL.delete_all_material_expressions(mat)
        sample = expr(mat, unreal.MaterialExpressionSparseVolumeTextureSampleParameter,
                      parameter_name='SparseVolumeTexture', sparse_volume_texture=svt)
        density = expr(mat, unreal.MaterialExpressionComponentMask, r=True, g=False, b=False, a=False)
        connect(sample, 'Attributes A', density, '')
        extinction = mul(mat, density, scalar(mat, 'DensityScale', 0.08))
        volume_bsdf = expr(mat, unreal.MaterialExpressionSubstrateVolumetricFogCloudBSDF)
        connect(extinction, '', volume_bsdf, 'Extinction')
        prop(volume_bsdf, '', unreal.MaterialProperty.MP_FRONT_MATERIAL)
        albedo = expr(mat, unreal.MaterialExpressionVectorParameter,
                      parameter_name='SmokeAlbedo', default_value=unreal.LinearColor(0.32, 0.34, 0.36, 1))
        connect(albedo, '', volume_bsdf, 'Albedo')
        if fire:
            flame = expr(mat, unreal.MaterialExpressionComponentMask, r=False, g=True, b=False, a=False)
            connect(sample, 'Attributes A', flame, '')
            temp = expr(mat, unreal.MaterialExpressionComponentMask, r=False, g=False, b=False, a=True)
            connect(sample, 'Attributes A', temp, '')
            kelvin = expr(mat, unreal.MaterialExpressionAdd, const_b=800.0)
            connect(mul(mat, temp, scalar(mat, 'TemperatureScale', 1400.0)), '', kelvin, 'A')
            blackbody = expr(mat, unreal.MaterialExpressionBlackBody)
            connect(kelvin, '', blackbody, '')
            emission = mul(mat, mul(mat, flame, blackbody), scalar(mat, 'EmissionScale', 5.0))
            connect(emission, '', volume_bsdf, 'EmissiveColor')
        errors = MEL.recompile_material(mat)
        if errors:
            raise RuntimeError(str(errors))
        save(mat, 'Original material; explicit Mantaflow grid mapping; density per UE centimeter')
        bp, component = component_blueprint(DEST + '/Actors/BP_SVT_' + name, unreal.HeterogeneousVolumeComponent)
        component.set_material(0, mat)
        component.set_editor_property('relative_scale3d', unreal.Vector(100, 100, 100))
        component.set_editor_property('pivot_at_centroid', False)
        component.set_frame_rate(manifest['fps'])
        component.set_start_frame(0)
        component.set_end_frame(manifest['frames'] - 1)
        component.set_playing(True)
        component.set_looping(False)  # The authored cache is deliberately not advertised as seamless.
        finish_bp(bp, 'Original Mantaflow cache; 3 seconds; meter-to-centimeter transform')


def liquid():
    manifest = json.loads((SOURCE / 'Liquid/bake-manifest.json').read_text(encoding='utf-8'))
    options = unreal.AbcImportSettings()
    options.set_editor_property('import_type', unreal.AlembicImportType.GEOMETRY_CACHE)
    conversion = options.get_editor_property('conversion_settings')
    # Blender's Alembic writer converts Z-up to Y-up. Rotate back and convert m to cm.
    conversion.set_editor_property('scale', unreal.Vector(100, -100, 100))
    conversion.set_editor_property('rotation', unreal.Vector(90, 0, 0))
    options.set_editor_property('conversion_settings', conversion)
    sampling = options.get_editor_property('sampling_settings')
    sampling.set_editor_property('frame_start', 1)
    sampling.set_editor_property('frame_end', manifest['frames'])
    options.set_editor_property('sampling_settings', sampling)
    mesh = import_file(manifest['files'][0], DEST + '/Geometry', 'GC_Mantaflow_LiquidDrop',
                       unreal.AlembicImportFactory(), options)
    save(mesh, manifest['source'])
    mat = create(DEST + '/Materials/M_LiquidCache', unreal.Material, unreal.MaterialFactoryNew())
    mat.set_editor_property('blend_mode', unreal.BlendMode.BLEND_TRANSLUCENT)
    mat.set_editor_property('two_sided', True)
    MEL.delete_all_material_expressions(mat)
    color = expr(mat, unreal.MaterialExpressionVectorParameter, parameter_name='WaterTint',
                 default_value=unreal.LinearColor(0.015, 0.09, 0.12, 1))
    prop(color, '', unreal.MaterialProperty.MP_BASE_COLOR)
    prop(scalar(mat, 'Opacity', 0.45), '', unreal.MaterialProperty.MP_OPACITY)
    prop(scalar(mat, 'Roughness', 0.08), '', unreal.MaterialProperty.MP_ROUGHNESS)
    prop(scalar(mat, 'Specular', 0.5), '', unreal.MaterialProperty.MP_SPECULAR)
    surface = expr(mat, unreal.MaterialExpressionSubstrateShadingModels,
                   shading_model_override=unreal.MaterialShadingModel.MSM_DEFAULT_LIT)
    for material_property, pin in [(unreal.MaterialProperty.MP_BASE_COLOR, 'BaseColor'),
                                   (unreal.MaterialProperty.MP_OPACITY, 'Opacity'),
                                   (unreal.MaterialProperty.MP_ROUGHNESS, 'Roughness'),
                                   (unreal.MaterialProperty.MP_SPECULAR, 'Specular')]:
        connect(MEL.get_material_property_input_node(mat, material_property), '', surface, pin)
    prop(surface, '', unreal.MaterialProperty.MP_FRONT_MATERIAL)
    MEL.set_base_material_usage(mat, unreal.MaterialUsage.MATUSAGE_GEOMETRY_CACHE, True)
    errors = MEL.recompile_material(mat)
    if errors:
        raise RuntimeError(str(errors))
    save(mat, 'Original baseline surface for a baked liquid cache')
    bp, cdo = blueprint(DEST + '/Actors/BP_LiquidDrop_Cached', unreal.GeometryCacheActor)
    component = cdo.get_editor_property('geometry_cache_component')
    component.set_geometry_cache(mesh)
    component.set_material(0, mat)
    component.set_editor_property('looping', False)
    component.set_editor_property('running', True)
    finish_bp(bp, 'Original 2-second baked liquid; cosmetic cache, no runtime liquid solver')


def water():
    source = '/Water/Materials/WaterSurface/Water_Material_CustomMesh'
    mat = save(duplicate(source, DEST + '/Materials/MI_Water_CustomMesh'), source)
    for style in ('River', 'Lake'):
        path = '/Water/Materials/WaterSurface/Water_Material_' + style
        save(duplicate(path, DEST + '/Materials/MI_Water_' + style), path)
    bp, cdo = blueprint(DEST + '/Actors/BP_Water_CustomSurface', unreal.WaterBodyCustom)
    component = cdo.get_editor_property('water_body_component')
    component.set_editor_property('affects_landscape', False)
    component.set_editor_property('water_mesh_override', unreal.load_asset('/Water/Meshes/LakeMesh'))
    component.set_water_material(mat)
    component.set_editor_property('water_static_mesh_material', mat)
    finish_bp(bp, 'Epic Water Custom body; Landscape deformation disabled for FPSGAME DynamicMesh terrain')


for STAGE in os.environ.get('FLUID_FOUNDATION_STAGES', 'templates,volume,liquid,water').split(','):
    SAVED = []
    print('FLUID_STAGE_START ' + STAGE, flush=True)
    {'templates': templates, 'volume': volume, 'liquid': liquid, 'water': water}[STAGE]()
    print('FLUID_STAGE_SAVED ' + STAGE, flush=True)
