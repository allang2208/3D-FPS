"""Build local V6 gun smoke and a project-authored soft tracer material.

Uses owned Epic examples and the accepted V5 systems, never overwrites their assets.
Run with UnrealEditor-Cmd -run=pythonscript -script=<this file> -unattended -multiprocess -NullRHI.
This is asset creation/compilation only; no scene, preview, audit or gameplay run.
"""
import json
from pathlib import Path
import unreal

ROOT = Path(unreal.Paths.project_dir())
DEST = '/Game/Weapons/GunplayFX'
LIB = unreal.MaterialEditingLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
API = unreal.get_default_object(unreal.NiagaraToolset_System)
CREATED = []


def save(asset):
    if isinstance(asset, unreal.Material):
        LIB.recompile_material(asset)
    if not unreal.EditorAssetLibrary.save_loaded_asset(asset, False):
        raise RuntimeError('Could not save ' + asset.get_path_name())
    CREATED.append(asset.get_path_name())
    unreal.log('GUNPLAY_V6_SAVED ' + asset.get_path_name())
    return asset


def duplicate(source_path, name):
    path = DEST + '/' + name
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        return unreal.load_asset(path)
    source = unreal.load_asset(source_path)
    if not source:
        raise RuntimeError('Required local source missing: ' + source_path)
    return TOOLS.duplicate_asset(name, DEST, source)


def node(material, cls):
    return LIB.create_material_expression(material, cls)


def wire(source, target, pin, output=''):
    if not LIB.connect_material_expressions(source, output, target, pin):
        raise RuntimeError('Could not connect material pin ' + pin)


def scalar(material, name, value):
    result = node(material, unreal.MaterialExpressionScalarParameter)
    result.set_editor_property('parameter_name', name)
    result.set_editor_property('default_value', value)
    return result


def tracer():
    name = 'M_BallisticTracerSoftV2'
    material = unreal.load_asset(DEST + '/' + name) if unreal.EditorAssetLibrary.does_asset_exist(DEST + '/' + name) else None
    if not material:
        material = TOOLS.create_asset(name, DEST, unreal.Material, unreal.MaterialFactoryNew())
    material.set_editor_property('enable_responsive_aa', True)
    expressions = LIB.get_material_expressions(material)
    shader = (ROOT / 'SourceAssets/GunplayVFX20260913/TracerSoft.hlsl').read_text(encoding='utf-8')
    if expressions:
        for expression in expressions:
            if isinstance(expression, unreal.MaterialExpressionCustom):
                expression.set_editor_property('code', shader)
        return save(material)
    material.set_editor_property('blend_mode', unreal.BlendMode.BLEND_ADDITIVE)
    material.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
    material.set_editor_property('two_sided', False)
    material.set_editor_property('disable_depth_test', False)
    world = node(material, unreal.MaterialExpressionWorldPosition)
    local = node(material, unreal.MaterialExpressionTransformPosition)
    local.set_editor_property('transform_source_type', unreal.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_WORLD)
    local.set_editor_property('transform_type', unreal.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_LOCAL)
    wire(world, local, '')
    tint = node(material, unreal.MaterialExpressionVectorParameter)
    tint.set_editor_property('parameter_name', 'Tint')
    tint.set_editor_property('default_value', unreal.LinearColor(1, .63, .18, 1))
    inputs = dict(LocalPosition=local, Tint=tint,
                  NormalWS=node(material, unreal.MaterialExpressionPixelNormalWS),
                  ViewVector=node(material, unreal.MaterialExpressionCameraVectorWS),
                  Exposure=node(material, unreal.MaterialExpressionEyeAdaptation),
                  Emission=scalar(material, 'Emission', 7), Opacity=scalar(material, 'Opacity', 1))
    shape = node(material, unreal.MaterialExpressionCustom)
    shape.set_editor_property('code', shader)
    shape.set_editor_property('description', 'Soft current-flight tracer')
    shape.set_editor_property('output_type', unreal.CustomMaterialOutputType.CMOT_FLOAT4)
    pins = []
    for name in inputs:
        pin = unreal.CustomInput()
        pin.set_editor_property('input_name', name)
        pins.append(pin)
    shape.set_editor_property('inputs', pins)
    for name, source in inputs.items():
        wire(source, shape, name)
    rgb = node(material, unreal.MaterialExpressionComponentMask)
    alpha = node(material, unreal.MaterialExpressionComponentMask)
    for channel in ['r', 'g', 'b', 'a']:
        rgb.set_editor_property(channel, channel != 'a')
        alpha.set_editor_property(channel, channel == 'a')
    wire(shape, rgb, '')
    wire(shape, alpha, '')
    fade = node(material, unreal.MaterialExpressionDepthFade)
    fade.set_editor_property('fade_distance_default', 4)
    wire(alpha, fade, 'Opacity')
    LIB.connect_material_property(rgb, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    LIB.connect_material_property(fade, '', unreal.MaterialProperty.MP_OPACITY)
    return save(material)


def stack_ref(system, emitter, renderer=-1):
    result = unreal.NiagaraExt_StackItemReference()
    for name, value in dict(system=system, emitter_name=emitter, renderer_index=renderer).items():
        result.set_editor_property(name, value)
    return result


def put(system, script, module, name, value, typ='/Script/Niagara.NiagaraFloat'):
    if not unreal.RainAssetEditor.set_input(system, 'Muzzle_Smoke', script, module, name, typ, value):
        raise RuntimeError('Could not author ' + system.get_name() + ': ' + module + '.' + name)


def smoke_system(kind):
    hot = kind == 'BarrelSmoke'
    system = duplicate(DEST + '/NS_FPS_' + kind + 'EpicV5', 'NS_FPS_' + kind + 'EpicV6')
    material = duplicate('/Game/NiagaraExamples/Materials/MI_SmokeWispy_8x8_Emissive' if hot else
        '/Game/NiagaraExamples/FX_Weapons/MuzzleFlashes/Materials/Instances/MI_Flipbook_Smoke_Muzzle',
        'MI_BarrelWispyV6' if hot else 'MI_MuzzleSmokeV6')
    # The texture and normal channels stay with their original material parent.
    names = {str(name) for name in LIB.get_scalar_parameter_names(material)}
    for name, value in [('Emissive Gain', 0), ('Near Fade Distance', 55), ('Depth Fade Distance', 1.5)]:
        if name in names:
            LIB.set_material_instance_scalar_parameter_value(material, name, value)
    LIB.update_material_instance(material)
    save(material)
    renderer = unreal.NiagaraExt_RendererData()
    renderer.set_editor_property('property_values', json.dumps({'Material': material.get_path_name()}))
    API.call_method('SetRendererData', (stack_ref(system, 'Muzzle_Smoke', 0), renderer))
    # Explicit smoke scale separates suppressor flash attenuation from visible smoke.
    if 'User.SmokeScale' not in API.call_method('GetUserVariables', (system,)).export_text():
        variable = unreal.NiagaraExt_UserVariable()
        # The gameplay component sets this parameter before Activate(), like Smoke Color.
        variable.import_text('(Name="User.SmokeScale",Type=(ClassStructOrEnum="/Script/Niagara.NiagaraFloat",UnderlyingType=2))')
        API.call_method('AddUserVariables', (system, [variable]))
    scale_module = 'SetVariables_285AF4AB4D469F20CC2C7FB5409ABDBA'
    expression_type = '/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression'
    for name in ['SpriteSize', 'Velocity']:
        put(system, 'ParticleSpawnScript', scale_module, 'Particles.' + name,
            '(HlslExpression="Particles.' + name + ' * User.SmokeScale")', expression_type)
    for name, value in [('Lifetime Min', .75 if hot else .50), ('Lifetime Max', 1.05 if hot else .80),
                        ('Uniform Sprite Size Min', 30 if hot else 38),
                        ('Uniform Sprite Size Max', 44 if hot else 55)]:
        put(system, 'ParticleSpawnScript', 'InitializeParticle', name, '(Value=%s)' % value)
    put(system, 'ParticleSpawnScript', 'AddVelocity', 'Velocity Speed', '(Value=%s)' % (100 if hot else 170))
    put(system, 'ParticleSpawnScript', 'AddVelocity', 'Cone Angle', '(Value=%s)' % (20 if hot else 10))
    put(system, 'ParticleUpdateScript', 'Drag', 'Drag', '(Value=%s)' % (1.0 if hot else 1.8))
    if not unreal.RainAssetEditor.compile_rain(system):
        raise RuntimeError('Niagara compilation failed: ' + system.get_path_name())
    return save(system)


tracer()
smoke_system('Muzzle')
smoke_system('BarrelSmoke')
output = ROOT / 'Saved/GunplayVFX20260913'
output.mkdir(parents=True, exist_ok=True)
(output / 'created-assets.json').write_text(json.dumps(CREATED, indent=2), encoding='utf-8')
unreal.log('GUNPLAY_V6_ASSETS_CREATED')
