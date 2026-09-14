"""Continuous world-space smoke and a flash-only copy of V8. No gameplay or renders.

UnrealEditor-Cmd -run=pythonscript -script=<file> -unattended -multiprocess -NullRHI.
"""
import json
from pathlib import Path
import unreal

ROOT = Path(unreal.Paths.project_dir())
DEST = '/Game/Weapons/GunplayFX'
API = unreal.get_default_object(unreal.NiagaraToolset_System)
LIB = unreal.MaterialEditingLibrary
CREATED = []
SMOKE = 'Muzzle_Smoke'
FLOAT = '/Script/Niagara.NiagaraFloat'
EXPR = '/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression'


def duplicate(source, name):
    path = DEST + '/' + name
    asset = unreal.load_asset(path) if unreal.EditorAssetLibrary.does_asset_exist(path) else None
    if not asset:
        asset = unreal.EditorAssetLibrary.duplicate_asset(source, path)
    if not asset:
        raise RuntimeError('Could not create ' + path)
    return asset


def save(asset):
    if not unreal.EditorAssetLibrary.save_loaded_asset(asset, False):
        raise RuntimeError('Could not save ' + asset.get_path_name())
    CREATED.append(asset.get_path_name())
    unreal.log('GUNPLAY_V9_SAVED ' + asset.get_path_name())


def ref(system, script='', module='', renderer=-1):
    result = unreal.NiagaraExt_StackItemReference()
    for key, value in dict(system=system, emitter_name=SMOKE, script_name=script,
                           module_name=module, renderer_index=renderer).items():
        result.set_editor_property(key, value)
    return result


def put(system, script, module, name, value, typ=FLOAT):
    if not unreal.RainAssetEditor.set_input(system, SMOKE, script, module, name, typ, value):
        raise RuntimeError('Could not author ' + module + '/' + name)


def expression(system, script, module, name, code):
    put(system, script, module, name, '(HlslExpression="' + code + '")', EXPR)


def wire(source, output, target, pin):
    if not LIB.connect_material_expressions(source, output, target, pin):
        raise RuntimeError('Could not connect ' + target.get_name() + '/' + pin)


def smoke_material():
    name = 'M_MuzzleSmokeSheetV9'
    path = DEST + '/' + name
    material = unreal.load_asset(path) if unreal.EditorAssetLibrary.does_asset_exist(path) else None
    if not material:
        material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, DEST, unreal.Material, unreal.MaterialFactoryNew())
    material.set_editor_property('blend_mode', unreal.BlendMode.BLEND_TRANSLUCENT)
    material.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_DEFAULT_LIT)
    material.set_editor_property('translucency_lighting_mode', unreal.TranslucencyLightingMode.TLM_VOLUMETRIC_NON_DIRECTIONAL)
    material.set_editor_property('two_sided', True)
    material.set_editor_property('disable_depth_test', False)
    material.set_editor_property('enable_responsive_aa', True)
    # Author the sprite shader permutation explicitly; runtime cannot rely on
    # an editor preview automatically setting this usage flag.
    LIB.set_base_material_usage(material, unreal.MaterialUsage.MATUSAGE_NIAGARA_SPRITES, True)
    code = (ROOT / 'SourceAssets/GunplayVFX20260914/ContinuousSmoke.hlsl').read_text(encoding='utf-8')
    nodes = LIB.get_material_expressions(material)
    if nodes:
        for node in nodes:
            if isinstance(node, unreal.MaterialExpressionCustom):
                node.set_editor_property('code', code)
    else:
        def node(cls):
            return LIB.create_material_expression(material, cls)
        color = node(unreal.MaterialExpressionParticleColor)
        density = node(unreal.MaterialExpressionCustom)
        density.set_editor_property('description', 'Continuous world-space smoke density')
        density.set_editor_property('output_type', unreal.CustomMaterialOutputType.CMOT_FLOAT1)
        density.set_editor_property('code', code)
        inputs = dict(PositionWS=node(unreal.MaterialExpressionWorldPosition),
                      SpriteUV=node(unreal.MaterialExpressionTextureCoordinate),
                      Clock=node(unreal.MaterialExpressionTime))
        pins = []
        for name in inputs:
            pin = unreal.CustomInput()
            pin.set_editor_property('input_name', name)
            pins.append(pin)
        density.set_editor_property('inputs', pins)
        for name, source in inputs.items():
            wire(source, '', density, name)
        opacity = node(unreal.MaterialExpressionMultiply)
        wire(density, '', opacity, 'A')
        wire(color, 'A', opacity, 'B')
        fade = node(unreal.MaterialExpressionDepthFade)
        fade.set_editor_property('fade_distance_default', 8)
        wire(opacity, '', fade, 'Opacity')
        fill = node(unreal.MaterialExpressionMultiply)
        fill.set_editor_property('const_b', .045)
        wire(color, 'RGB', fill, 'A')
        LIB.connect_material_property(color, 'RGB', unreal.MaterialProperty.MP_BASE_COLOR)
        LIB.connect_material_property(fill, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
        LIB.connect_material_property(fade, '', unreal.MaterialProperty.MP_OPACITY)
    errors = LIB.recompile_material(material)
    if errors:
        raise RuntimeError('Smoke material compilation failed: ' + '\n'.join(errors))
    save(material)
    return material


def add_module(system, script, asset, tag, after=''):
    key = 'GunplayV9.' + tag
    name = unreal.EditorAssetLibrary.get_metadata_tag(system, key)
    if not name:
        topology = API.call_method('AddModule', (ref(system, script, after), unreal.load_asset(asset)))
        name = str(topology.get_editor_property('module_name'))
        unreal.EditorAssetLibrary.set_metadata_tag(system, key, name)
    return name


def assignment(system, script, attribute, code, tag):
    key = 'GunplayV9.' + tag
    name = unreal.EditorAssetLibrary.get_metadata_tag(system, key)
    if not name:
        entry = unreal.NiagaraExt_SetParameterEntry()
        entry.import_text('(Variable=(Name="' + attribute + '",Type=(ClassStructOrEnum="/Script/CoreUObject.Vector2f",UnderlyingType=2)))')
        topology = API.call_method('AddSetParametersModule', (ref(system, script), [entry]))
        name = str(topology.get_editor_property('module_name'))
        unreal.EditorAssetLibrary.set_metadata_tag(system, key, name)
    expression(system, script, name, attribute, code)


material = smoke_material()
flashes = duplicate(DEST + '/NS_FPS_MuzzleEpicV8', 'NS_FPS_MuzzleFlashV9')
if 'EmitterName="Muzzle_Smoke"' in API.call_method('GetSystemSummary', (flashes,)).export_text():
    API.call_method('RemoveEmitter', (ref(flashes),))
# All retained flash emitters and their V8 materials are unchanged.
if not unreal.RainAssetEditor.compile_rain(flashes):
    raise RuntimeError('Could not compile flash system')
save(flashes)

system = duplicate(DEST + '/NS_FPS_BarrelSmokeEpicV8', 'NS_FPS_MuzzleSmokeStreamV9')
edata = unreal.NiagaraExt_EmitterData()
edata.set_editor_property('property_values', json.dumps({'bLocalSpace': False, 'bDeterminism': False}))
API.call_method('SetEmitterData', (ref(system), edata))
put(system, 'EmitterUpdateScript', 'EmitterState', 'Loop Behavior',
    '(Enum="/Script/Engine.UserDefinedEnum\'/Niagara/Enums/ENiagara_EmitterStateOptions.ENiagara_EmitterStateOptions\'",EnumName="ENiagara_EmitterStateOptions::NewEnumerator0",DisplayName=NSLOCTEXT("[B0445FD5480567CC755E43ACB5A7B80E]", "64BA41D948A2ACE53757E8B36DDEF806", "Infinite"))',
    '/Script/NiagaraEditor.NiagaraExt_StackInputData_Enum')
topology = API.call_method('GetEmitterTopology', (ref(system),)).export_text()
if 'ModuleName="SpawnBurst_Instantaneous"' in topology:
    API.call_method('RemoveModule', (ref(system, 'EmitterUpdateScript', 'SpawnBurst_Instantaneous'),))
for module in ['SubUVAnimation', 'DynamicMaterialParameters']:
    if 'ModuleName="' + module + '"' in topology:
        API.call_method('SetModuleEnabled', (ref(system, 'ParticleUpdateScript', module), False))
if 'User.SpawnRate' not in API.call_method('GetUserVariables', (system,)).export_text():
    variable = unreal.NiagaraExt_UserVariable()
    variable.import_text('(Name="User.SpawnRate",Type=(ClassStructOrEnum="/Script/Niagara.NiagaraFloat",UnderlyingType=2))')
    API.call_method('AddUserVariables', (system, [variable]))
rate = add_module(system, 'EmitterUpdateScript', '/Niagara/Modules/Emitter/SpawnRate', 'Rate', 'EmitterState')
expression(system, 'EmitterUpdateScript', rate, 'SpawnRate', 'clamp(User.SpawnRate, 0.0, 80.0)')
for name, value in [('Lifetime Min', 1.6), ('Lifetime Max', 2.0),
                    ('Uniform Sprite Size Min', 34), ('Uniform Sprite Size Max', 46)]:
    put(system, 'ParticleSpawnScript', 'InitializeParticle', name, '(Value=%s)' % value)
put(system, 'ParticleSpawnScript', 'AddVelocity', 'Velocity Speed', '(Value=95)')
put(system, 'ParticleSpawnScript', 'AddVelocity', 'Cone Angle', '(Value=18)')
put(system, 'ParticleUpdateScript', 'Drag', 'Drag', '(Value=1.25)')
gravity = add_module(system, 'ParticleUpdateScript', '/Niagara/Modules/Update/Forces/GravityForce', 'Rise', 'Drag')
put(system, 'ParticleUpdateScript', gravity, 'Gravity', '(X=2.0,Y=1.5,Z=13.0)', '/Script/CoreUObject.Vector3f')
assignment(system, 'ParticleSpawnScript', 'Particles.SmokeBirthSize', 'Particles.SpriteSize', 'BirthSize')
assignment(system, 'ParticleUpdateScript', 'Particles.SpriteSize',
    'Particles.SmokeBirthSize * float2(0.85 + 1.8 * Particles.NormalizedAge, 0.85 + 2.1 * Particles.NormalizedAge)', 'Spread')
# Low-opacity layers overlap; a long, continuous fade removes bead-like birth/death edges.
expression(system, 'ParticleUpdateScript', 'ScaleColor', 'Scale Alpha',
    'saturate(Particles.NormalizedAge * 12.0) * pow(saturate(1.0 - Particles.NormalizedAge), 1.25)')
rdata = unreal.NiagaraExt_RendererData()
rdata.set_editor_property('property_values', json.dumps({'Material': material.get_path_name(),
    'SubImageSize': {'X': 1.0, 'Y': 1.0}, 'bSubImageBlend': False,
    'Alignment': 'Unaligned', 'FacingMode': 'FaceCamera'}))
API.call_method('SetRendererData', (ref(system, renderer=0), rdata))
if not unreal.RainAssetEditor.compile_rain(system):
    raise RuntimeError('Could not compile continuous smoke')
save(system)
output = Path(unreal.Paths.project_saved_dir()) / 'GunplayVFX20260914'
output.mkdir(parents=True, exist_ok=True)
(output / 'created-assets-v9.json').write_text(json.dumps(CREATED, indent=2), encoding='utf-8')
unreal.log('GUNPLAY_V9_ASSETS_CREATED')
