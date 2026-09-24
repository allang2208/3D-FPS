"""Build separate shot impulse and continuous/world-space muzzle smoke assets.

Project-authored Niagara assets; references are design research, not copied code.
Background authoring only, with no gameplay or rendered acceptance.
"""
import json
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.project_dir())
OUT = ROOT / 'SourceAssets/MuzzleSmokeV1520260923'
DEST = '/Game/Weapons/GunplayFX'
LIB = u.MaterialEditingLibrary
TOOLS = u.AssetToolsHelpers.get_asset_tools()
API = u.get_default_object(u.NiagaraToolset_System)
EMITTER = 'Muzzle_Smoke'
FLOAT = '/Script/Niagara.NiagaraFloat'
VEC2 = '/Script/CoreUObject.Vector2f'
VEC4 = '/Script/CoreUObject.Vector4f'
EXPR = '/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression'
SAVED = []


def ref(system, script='', module='', renderer=-1):
    result = u.NiagaraExt_StackItemReference()
    for key, value in dict(system=system, emitter_name=EMITTER, script_name=script,
                           module_name=module, renderer_index=renderer).items():
        result.set_editor_property(key, value)
    return result


def duplicate(source, name):
    path = DEST + '/' + name
    asset = u.load_asset(path) if u.EditorAssetLibrary.does_asset_exist(path) else None
    if asset is None:
        asset = TOOLS.duplicate_asset(name, DEST, u.load_asset(DEST + '/' + source))
    if asset is None:
        raise RuntimeError('Cannot create ' + path)
    return asset


def put(system, script, module, name, value, typ=FLOAT):
    if not u.RainAssetEditor.set_input(system, EMITTER, script, module, name, typ, value):
        raise RuntimeError('Cannot set ' + module + '/' + name)


def expression(system, script, module, name, code):
    put(system, script, module, name, '(HlslExpression="' + code + '")', EXPR)


def smooth(start, end):
    t = f'saturate((Particles.NormalizedAge-{start})/{end-start})'
    return f'(({t})*({t})*(3-2*({t})))'


def assignment(system, script, variable, typ, code):
    tag = 'SmokeV15.' + script + '.' + variable
    module = u.EditorAssetLibrary.get_metadata_tag(system, tag)
    if not module:
        entry = u.NiagaraExt_SetParameterEntry()
        entry.import_text('(Variable=(Name="' + variable + '",Type=(ClassStructOrEnum="' + typ + '",UnderlyingType=2)))')
        module = str(API.call_method('AddSetParametersModule', (ref(system, script), [entry])).get_editor_property('module_name'))
        u.EditorAssetLibrary.set_metadata_tag(system, tag, module)
    expression(system, script, module, variable, code)


def save(asset):
    if isinstance(asset, u.NiagaraSystem) and not u.RainAssetEditor.compile_rain(asset):
        raise RuntimeError('Niagara compile failed: ' + asset.get_path_name())
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()], False):
        raise RuntimeError('Cannot save ' + asset.get_path_name())
    SAVED.append(asset.get_path_name())
    u.log('MUZZLE_V15_SAVED ' + asset.get_path_name())


def wire(source, output, target, pin):
    if not LIB.connect_material_expressions(source, output, target, pin):
        raise RuntimeError('Cannot connect ' + target.get_name() + '/' + pin)


def material():
    mat = duplicate('M_MuzzleSmokeMantaflowV14', 'M_MuzzleSmokeLayeredV15')
    nodes = LIB.get_material_expressions(mat)
    density = next(n for n in nodes if isinstance(n, u.MaterialExpressionCustom)
                   and n.get_editor_property('description') == 'Mantaflow V14 smoke flipbook')
    density.set_editor_property('code', (OUT / 'SmokeDensity.hlsl').read_text(encoding='utf-8'))
    sight = next(n for n in nodes if isinstance(n, u.MaterialExpressionCustom)
                 and n.get_editor_property('description') == 'Gunplay V12 aged smoke sightline')
    pins = list(sight.get_editor_property('inputs'))
    if not any(str(p.get_editor_property('input_name')) == 'SightProtection' for p in pins):
        pin = u.CustomInput()
        pin.set_editor_property('input_name', 'SightProtection')
        pins.append(pin)
        sight.set_editor_property('inputs', pins)
    dynamic = next((n for n in nodes if isinstance(n, u.MaterialExpressionDynamicParameter)), None)
    if dynamic is None:
        dynamic = LIB.create_material_expression(mat, u.MaterialExpressionDynamicParameter)
    dynamic.set_editor_property('param_names', ['SightProtection', 'Layer', 'UnusedZ', 'UnusedW'])
    # Output zero is the red channel; named Outputs refresh only in an editor graph.
    wire(dynamic, '', sight, 'SightProtection')
    sight.set_editor_property('code', (OUT / 'SmokeSightline.hlsl').read_text(encoding='utf-8'))
    errors = LIB.recompile_material(mat)
    if errors:
        raise RuntimeError('Smoke material compile failed: ' + str(errors))
    save(mat)
    return mat


def author_system(mat, pulse):
    name = 'NS_FPS_MuzzleSmokeShotV15' if pulse else 'NS_FPS_MuzzleSmokeStreamV15'
    system = duplicate('NS_FPS_MuzzleSmokeMantaflowV14', name)
    variables = API.call_method('GetUserVariables', (system,)).export_text()
    if 'User.SightProtection' not in variables:
        variable = u.NiagaraExt_UserVariable()
        variable.import_text('(Name="User.SightProtection",Type=(ClassStructOrEnum="' + FLOAT + '",UnderlyingType=2))')
        API.call_method('AddUserVariables', (system, [variable]))
    # Source size and speed had been coupled: 95 cm/s became 26.6 cm/s at .28
    # scale. Birth velocity now has its own units, independent of sprite size.
    expression(system, 'ParticleSpawnScript', 'SetVariables_285AF4AB4D469F20CC2C7FB5409ABDBA',
               'Particles.Velocity', 'Particles.Velocity + User.SmokeDrift')
    expression(system, 'ParticleSpawnScript', 'InitializeParticle', 'Lifetime Min',
               '0.30' if pulse else 'lerp(0.50,0.90,saturate(User.SmokeTailBlend))')
    expression(system, 'ParticleSpawnScript', 'InitializeParticle', 'Lifetime Max',
               '0.46' if pulse else 'lerp(0.75,1.30,saturate(User.SmokeTailBlend))')
    put(system, 'ParticleSpawnScript', 'AddVelocity', 'Cone Angle', '(Value=16)' if pulse else '(Value=24)')
    put(system, 'ParticleUpdateScript', 'Drag', 'Drag', '(Value=3.6)' if pulse else '(Value=1.25)')
    v9 = u.load_asset(DEST + '/NS_FPS_MuzzleSmokeStreamV9')
    rise = u.EditorAssetLibrary.get_metadata_tag(v9, 'GunplayV9.Rise')
    spread = u.EditorAssetLibrary.get_metadata_tag(v9, 'GunplayV9.Spread')
    put(system, 'ParticleUpdateScript', rise, 'Gravity',
        '(X=0,Y=0,Z=12)' if pulse else '(X=0,Y=0,Z=18)', '/Script/CoreUObject.Vector3f')
    size = ('Particles.SmokeBirthSize * float2(0.72+1.25*' + smooth(0, .8)
            + ',1.3+1.5*' + smooth(0, .8) + ')') if pulse else (
                'Particles.SmokeBirthSize * float2(0.85+1.7*Particles.NormalizedAge,0.9+2.0*Particles.NormalizedAge)'
                ' * lerp(1.0,clamp(User.SmokeSpreadScale,1.0,2.5),' + smooth(.08, .75) + ')')
    expression(system, 'ParticleUpdateScript', spread, 'Particles.SpriteSize', size)
    alpha = smooth(0, .035) + '*(1-' + smooth(.18 if pulse else .24, 1) + ')'
    alpha += '/(1+0.50*Particles.NormalizedAge)'
    expression(system, 'ParticleUpdateScript', 'ScaleColor', 'Scale Alpha', alpha)
    assignment(system, 'ParticleUpdateScript', 'Particles.DynamicMaterialParameter', VEC4,
               'float4(saturate(User.SightProtection),0,0,0)')
    if pulse:
        topology = API.call_method('GetEmitterTopology', (ref(system),)).export_text()
        rate = u.EditorAssetLibrary.get_metadata_tag(v9, 'GunplayV9.Rate')
        if 'ModuleName="' + rate + '"' in topology:
            API.call_method('RemoveModule', (ref(system, 'EmitterUpdateScript', rate),))
        if 'ModuleName="SpawnBurst_Instantaneous"' not in topology:
            API.call_method('AddModule', (ref(system, 'EmitterUpdateScript'),
                                          u.load_asset('/Niagara/Modules/Emitter/SpawnBurst_Instantaneous')))
        put(system, 'EmitterUpdateScript', 'SpawnBurst_Instantaneous', 'Spawn Count', '(Value=3)', '/Script/Niagara.NiagaraInt32')
        put(system, 'EmitterUpdateScript', 'SpawnBurst_Instantaneous', 'Spawn Time', '(Value=0)')
        source = u.load_asset('/Game/NiagaraExamples/FX_Explosions/NS_Explosion_Small')
        for key, display in [('Life Cycle Mode', 'System'), ('Loop Behavior', 'Infinite')]:
            value = u.RainAssetEditor.read_input(source, 'Explosion', 'EmitterUpdateScript', 'EmitterState', key)
            value = value.replace('NewEnumerator0', 'NewEnumerator1').replace('"' + display + '"', '"Self"' if key == 'Life Cycle Mode' else '"Once"')
            put(system, 'EmitterUpdateScript', 'EmitterState', key, value, '/Script/NiagaraEditor.NiagaraExt_StackInputData_Enum')
        put(system, 'EmitterUpdateScript', 'EmitterState', 'Loop Duration', '(Value=0.10)')
    renderer = u.NiagaraExt_RendererData()
    renderer.set_editor_property('property_values', json.dumps({
        'Material': mat.get_path_name(), 'Alignment': 'VelocityAligned' if pulse else 'Unaligned',
        'FacingMode': 'FaceCamera', 'SubImageSize': {'X': 1.0, 'Y': 1.0}, 'bSubImageBlend': False}))
    API.call_method('SetRendererData', (ref(system, renderer=0), renderer))
    save(system)


OUT.mkdir(parents=True, exist_ok=True)
u.AssetRegistryHelpers.get_asset_registry().scan_paths_synchronous([DEST], force_rescan=True)
mat = material()
author_system(mat, False)
author_system(mat, True)
(OUT / 'assets.json').write_text(json.dumps({'saved': SAVED, 'runtime_tested': False,
    'visual_tested': False, 'burst_particles_per_shot': 3,
    'source': 'Project-authored V14 Mantaflow atlas and Epic-derived project Niagara templates'}, indent=2), encoding='utf-8')
u.log('MUZZLE_V15_ASSETS_COMPLETE')
