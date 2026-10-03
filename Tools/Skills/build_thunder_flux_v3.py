"""Import and save the original turbulent electrical beam. No play/render/tests.

Owns only ThunderFluxV3. Keeps the old V2 assets for recovery and reads the
original Blender/packed-field sources from SourceAssets/ThunderLanceFlux20261001.
"""
import json
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.project_dir())
SOURCE = ROOT / 'SourceAssets/ThunderLanceFlux20261001'
DEST = '/Game/Skills/ElectricMagic/ThunderFluxV3'
LIB = u.MaterialEditingLibrary
EAL = u.EditorAssetLibrary
TOOLS = u.AssetToolsHelpers.get_asset_tools()
NAMES = ['T_ThunderFluxFields', 'SM_ThunderFluxTube', 'M_ThunderFluxBody', 'M_ThunderFluxFilaments']


def save(asset):
    if not EAL.save_loaded_asset(asset, False):
        raise RuntimeError('Cannot save ' + asset.get_path_name())


def imported(name, filename, options=None):
    asset = u.load_asset(DEST + '/' + name)
    if asset:
        return asset
    task = u.AssetImportTask()
    task.filename = str(SOURCE / filename)
    task.destination_path = DEST
    task.destination_name = name
    task.automated = True
    task.replace_existing = False
    task.save = False
    if options:
        task.options = options
    TOOLS.import_asset_tasks([task])
    asset = u.load_asset(DEST + '/' + name)
    if not asset:
        raise RuntimeError('Import failed: ' + filename)
    return asset


def build_material(name, texture, filament):
    material = u.load_asset(DEST + '/' + name)
    if not material:
        material = TOOLS.create_asset(name, DEST, u.Material, u.MaterialFactoryNew())
    if not material:
        raise RuntimeError('Cannot create ' + name)
    # DeleteAllMaterialExpressions mutates the array it iterates, leaving stale
    # nodes with severed inputs ("missing input" compile errors). Snapshot the
    # list and delete each expression by reference instead.
    for expression in LIB.get_material_expressions(material):
        LIB.delete_material_expression(material, expression)
    # The beam body attenuates the background; only the narrow electric strands
    # remain additive. Increasing additive opacity alone cannot hide scenery.
    for key, value in {'blend_mode': u.BlendMode.BLEND_ADDITIVE if filament else u.BlendMode.BLEND_TRANSLUCENT,
                       'shading_model': u.MaterialShadingModel.MSM_UNLIT,
                       'two_sided': True, 'disable_depth_test': False,
                       'enable_responsive_aa': True, 'output_translucent_velocity': True}.items():
        material.set_editor_property(key, value)

    def node(kind):
        return LIB.create_material_expression(material, kind)

    def scalar(name, value):
        result = node(u.MaterialExpressionScalarParameter)
        result.set_editor_property('parameter_name', name)
        result.set_editor_property('default_value', value)
        return result

    def vector(name, value):
        result = node(u.MaterialExpressionVectorParameter)
        result.set_editor_property('parameter_name', name)
        result.set_editor_property('default_value', u.LinearColor(*value))
        return result

    def custom(code, inputs, kind=u.CustomMaterialOutputType.CMOT_FLOAT1):
        result = node(u.MaterialExpressionCustom)
        result.set_editor_property('code', code)
        result.set_editor_property('output_type', kind)
        pins = []
        for name in inputs:
            pin = u.CustomInput()
            pin.set_editor_property('input_name', name)
            pins.append(pin)
        result.set_editor_property('inputs', pins)
        for name, (expression, output) in inputs.items():
            if not LIB.connect_material_expressions(expression, output, result, name):
                raise RuntimeError('Cannot connect flux ' + name)
        return result

    def multiply(a, b):
        result = node(u.MaterialExpressionMultiply)
        LIB.connect_material_expressions(a, '', result, 'A')
        LIB.connect_material_expressions(b, '', result, 'B')
        return result

    position = node(u.MaterialExpressionWorldPosition)
    normal = node(u.MaterialExpressionPixelNormalWS)
    view = node(u.MaterialExpressionCameraVectorWS)
    age, alpha = scalar('BeamAge', 0.), scalar('BeamAlpha', 1.)
    role = scalar('Role', 3. if filament else 1.)
    origin = vector('Origin', (0., 0., 0., 0.))
    axis = vector('Axis', (1., 0., 0., 0.))
    length, radius = scalar('Length', 2745.), scalar('Radius', 84.)
    seed = scalar('Seed', 0.)
    noise = node(u.MaterialExpressionTextureObject)
    noise.set_editor_property('texture', texture)
    common_inputs = {'P': (position, ''), 'Origin': (origin, 'RGB'), 'Axis': (axis, 'RGB'),
                     'Age': (age, ''), 'Seed': (seed, ''), 'Length': (length, '')}
    mask_inputs = dict(common_inputs, N=(normal, ''), V=(view, ''))
    shared = (SOURCE / 'FluxCommon.hlsl').read_text(encoding='utf-8')
    if filament:
        mask = custom((SOURCE / 'FluxFilaments.hlsl').read_text(encoding='utf-8'), mask_inputs)
    else:
        mask = custom(shared + (SOURCE / 'FluxMask.hlsl').read_text(encoding='utf-8'),
                      dict(mask_inputs, Role=(role, ''), NoiseTex=(noise, '')))
    displacement = custom(shared + (SOURCE / 'FluxDisplacement.hlsl').read_text(encoding='utf-8'),
                          dict(common_inputs, Role=(role, ''), Radius=(radius, ''), NoiseTex=(noise, '')),
                          u.CustomMaterialOutputType.CMOT_FLOAT3)
    color = vector('BeamColor', (.25, .70, 1., 1.))
    emission = scalar('Emission', 42. if filament else 21.)
    opacity = scalar('Opacity', 1. if filament else .93)
    # Permanent bright spearhead band plus a launch flash that sweeps the beam
    # forward once before decaying away.
    flash = custom('float3 ax=normalize(Axis);float qq=dot(P-Origin,ax)/max(Length,1.0);'
                   'float head=1.0+2.6*exp(-pow((qq-.88)/.05,2.0));'
                   'float travel=1.0+1.8*exp(-pow((qq-saturate(Age/.11))/.045,2.0))*exp(-Age*7.0);'
                   'return (1.0+1.4*exp(-Age*38.0))*(.96+.04*sin(Age*63.0))*head*travel;',
                   {'Age': (age, ''), 'P': (position, ''), 'Origin': (origin, 'RGB'),
                    'Axis': (axis, 'RGB'), 'Length': (length, '')})
    light = multiply(multiply(color, emission), flash)
    coverage = multiply(multiply(mask, alpha), opacity)
    for expression, prop in [(light, u.MaterialProperty.MP_EMISSIVE_COLOR),
                             (coverage, u.MaterialProperty.MP_OPACITY),
                             (displacement, u.MaterialProperty.MP_WORLD_POSITION_OFFSET)]:
        if not LIB.connect_material_property(expression, '', prop):
            raise RuntimeError('Cannot connect ' + str(prop))
    LIB.recompile_material(material)
    save(material)
    return material


def build_flux():
    targets = {DEST + '/' + name for name in NAMES}
    if any(str(p.get_path_name()) in targets for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
        raise RuntimeError('Preserve unsaved ThunderFluxV3 assets')
    editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if editor and editor.get_game_world():
        raise RuntimeError('End PIE before saving ThunderFluxV3')
    for filename in ['SM_ThunderFluxTube.fbx', 'T_ThunderFluxFields.png', 'FluxCommon.hlsl',
                     'FluxMask.hlsl', 'FluxDisplacement.hlsl', 'FluxFilaments.hlsl']:
        if not (SOURCE / filename).is_file():
            raise RuntimeError('Produce the original flux source first: ' + filename)
    EAL.make_directory(DEST)
    texture = imported(NAMES[0], 'T_ThunderFluxFields.png')
    texture.set_editor_property('srgb', False)
    texture.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_MASKS)
    texture.set_editor_property('address_x', u.TextureAddress.TA_WRAP)
    texture.set_editor_property('address_y', u.TextureAddress.TA_WRAP)
    texture.set_editor_property('never_stream', True)
    save(texture)
    options = u.FbxImportUI()
    options.import_mesh = True
    options.import_materials = False
    options.import_textures = False
    options.automated_import_should_detect_type = False
    options.import_as_skeletal = False
    options.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
    options.static_mesh_import_data.combine_meshes = True
    options.static_mesh_import_data.auto_generate_collision = False
    options.static_mesh_import_data.convert_scene_unit = True
    options.static_mesh_import_data.generate_lightmap_u_vs = False
    options.static_mesh_import_data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    mesh = imported(NAMES[1], 'SM_ThunderFluxTube.fbx', options)
    body = build_material(NAMES[2], texture, False)
    filaments = build_material(NAMES[3], texture, True)
    mesh.set_material(0, body)
    save(mesh)
    saved = [asset.get_path_name() for asset in [texture, mesh, body, filaments]]
    receipt = {
        'saved_assets': saved, 'source': str(SOURCE), 'provenance': 'original mesh, field data and HLSL',
        'reference': 'user supplied Comet Azur screenshot; visual direction only',
        'diameters_cm': [264, 168, 87, 291], 'components_per_beam': 4,
        'emission': [12, 21, 31.5, 42], 'opacity': [.45, .93, 1., 1.],
        'body_blend': 'translucent', 'filament_blend': 'additive',
        'range_cm': '(1800 + 30 * skill_level) * 1.5 before equipment bonuses',
        'range_multiplier': 2., 'visual_strength_multiplier': 1.5,
        'establishment_seconds': .09, 'hold_seconds': 'skills.json beamHold (default .45)',
        'fade_seconds': 'skills.json beamFade (default .6); filaments linger +45%',
        'flow': 'billowing displaced envelope, rolling density, coherent core, snapped branched electric strands',
        'spear_profile': 'narrow tail .55, head mass +.30 at q=.88, pointed tip below .10 at q=1',
        'lateral_snake': 'perpendicular low/high frequency bends by role; filament arcs lift off-surface',
        'charge_ratio': 'beam diameters scale lerp(.55,1,ratio); emission lerp(.65,1,ratio); light scales with ratio',
        'collision': False, 'damage_changed': False, 'gameplay_tested': False, 'rendered': False}
    folder = ROOT / 'Saved/ThunderLanceSpear20261002'
    folder.mkdir(parents=True, exist_ok=True)
    (folder / 'asset-authoring.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
    print('THUNDER_FLUX_V3_SAVED ' + json.dumps(receipt, ensure_ascii=False))
    return saved


if __name__ == '__main__':
    build_flux()
