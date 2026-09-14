"""Author wider continuous smoke, a barrel tail and softer flash transitions.

Asset compilation only, using the locally owned V8/V9 dependencies. No gameplay
or preview rendering. Run with -run=pythonscript -multiprocess and D3D12.
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
    unreal.log('GUNPLAY_V10_SAVED ' + asset.get_path_name())


def ref(system, emitter, script='', module='', renderer=-1):
    result = unreal.NiagaraExt_StackItemReference()
    for key, value in dict(system=system, emitter_name=emitter, script_name=script,
                           module_name=module, renderer_index=renderer).items():
        result.set_editor_property(key, value)
    return result


def put(system, emitter, script, module, name, value, typ=FLOAT):
    if not unreal.RainAssetEditor.set_input(system, emitter, script, module, name, typ, value):
        raise RuntimeError('Could not author ' + emitter + '/' + module + '/' + name)


def expression(system, emitter, script, module, name, code):
    put(system, emitter, script, module, name, '(HlslExpression="' + code + '")', EXPR)


def wire(source, output, target, pin):
    if not LIB.connect_material_expressions(source, output, target, pin):
        raise RuntimeError('Could not connect ' + target.get_name() + '/' + pin)


def custom(material, description, code, inputs, output):
    result = next((node for node in LIB.get_material_expressions(material)
                   if isinstance(node, unreal.MaterialExpressionCustom)
                   and node.get_editor_property('description') == description), None)
    if not result:
        result = LIB.create_material_expression(material, unreal.MaterialExpressionCustom)
    result.set_editor_property('description', description)
    result.set_editor_property('code', code)
    result.set_editor_property('output_type', output)
    pins = []
    for name in inputs:
        pin = unreal.CustomInput()
        pin.set_editor_property('input_name', name)
        pins.append(pin)
    result.set_editor_property('inputs', pins)
    return result


def smooth_age(start, end):
    t = '(saturate((Particles.NormalizedAge - %s) / %s))' % (start, end - start)
    return '(' + t + '*' + t + '*(3.0-2.0*' + t + '))'


def assign_material(system, emitter, material, blend=True):
    data = unreal.NiagaraExt_RendererData()
    data.set_editor_property('property_values', json.dumps({
        'Material': material.get_path_name(), 'bSubImageBlend': blend}))
    API.call_method('SetRendererData', (ref(system, emitter, renderer=0), data))


def flash_materials():
    parent = duplicate(DEST + '/M_MuzzleFlashFeatherV8', 'M_MuzzleFlashFeatherV10')
    nodes = {node.get_name(): node for node in LIB.get_material_expressions(parent)}
    raw_mask = nodes['MaterialExpressionSaturate_9']
    particle_color = nodes['MaterialExpressionParticleColor_1']
    feather = custom(parent, 'Gunplay V10 pixel footprint feather',
        (ROOT / 'SourceAssets/GunplayVFX20260914/FlashFeatherV10.hlsl').read_text(encoding='utf-8'),
        ['Opacity', 'ParticleAlpha'], unreal.CustomMaterialOutputType.CMOT_FLOAT1)
    wire(raw_mask, '', feather, 'Opacity')
    wire(particle_color, 'A', feather, 'ParticleAlpha')
    wire(feather, '', nodes['MaterialExpressionMultiply_1'], 'A')

    # The Epic alpha-composite master already premultiplies emissive by opacity.
    # Grade that result, keeping the core bright and the outer veil warm and dim.
    # Never add an unfaded emissive halo outside the alpha silhouette.
    edge_color = custom(parent, 'Gunplay V10 warm edge transition', '''
float core = smoothstep(0.10, 0.82, saturate(Opacity));
float3 tint = lerp(float3(1.0, 0.68, 0.38), float3(1.0, 1.0, 1.0), core);
float energy = lerp(0.62, 1.08, core);
return PremultipliedEmission * tint * energy;''',
        ['PremultipliedEmission', 'Opacity'], unreal.CustomMaterialOutputType.CMOT_FLOAT3)
    wire(nodes['MaterialExpressionMultiply_23'], '', edge_color, 'PremultipliedEmission')
    wire(raw_mask, '', edge_color, 'Opacity')
    output = nodes['MaterialExpressionSetMaterialAttributes_1']
    # This source node sets only Emissive after its incoming material attributes.
    # UE returns a localized display name for that pin in Chinese editor builds.
    emission_pin = str(LIB.get_material_expression_input_names(output)[1])
    wire(edge_color, '', output, emission_pin)
    for node in nodes.values():
        if isinstance(node, unreal.MaterialExpressionTextureSampleParameterSubUV):
            node.set_editor_property('blend', True)
    parent.set_editor_property('enable_responsive_aa', True)
    LIB.set_base_material_usage(parent, unreal.MaterialUsage.MATUSAGE_NIAGARA_SPRITES, True)
    errors = LIB.recompile_material(parent)
    if errors:
        raise RuntimeError('Flash material compilation failed: ' + '\n'.join(errors))
    save(parent)

    materials = {}
    for kind in ['Core', 'Lobes']:
        material = duplicate(DEST + '/MI_MuzzleFlash' + kind + 'V8', 'MI_MuzzleFlash' + kind + 'V10')
        LIB.set_material_instance_parent(material, parent)
        for name, value in {'Depth Fade Distance': 6.0, 'Opacity Clip Value': 0.0}.items():
            LIB.set_material_instance_scalar_parameter_value(material, name, value)
        LIB.set_material_instance_static_switch_parameter_value(material, 'Use Particle Alpha As Threshold', False)
        LIB.update_material_instance(material)
        save(material)
        materials[kind] = material
    return materials


materials = flash_materials()
flashes = duplicate(DEST + '/NS_FPS_MuzzleFlashV9', 'NS_FPS_MuzzleFlashV10')
for emitter in ['Flash_Center', 'MuzzleFlash_Front', 'MuzzleFlash_Side']:
    assign_material(flashes, emitter, materials['Core' if emitter == 'Flash_Center' else 'Lobes'])
    expression(flashes, emitter, 'ParticleUpdateScript', 'ScaleColor', 'Scale Alpha',
        smooth_age(0, .025) + ' * pow(1.0 - ' + smooth_age(.035, 1) + ', 1.20)')
if not unreal.RainAssetEditor.compile_rain(flashes):
    raise RuntimeError('Could not compile flash system')
save(flashes)

smoke_source = unreal.load_asset(DEST + '/NS_FPS_MuzzleSmokeStreamV9')
system = duplicate(DEST + '/NS_FPS_MuzzleSmokeStreamV9', 'NS_FPS_MuzzleSmokeStreamV10')
variables = API.call_method('GetUserVariables', (system,)).export_text()
for name in ['SmokeForwardSpeed', 'SmokeSpreadScale']:
    if 'User.' + name not in variables:
        variable = unreal.NiagaraExt_UserVariable()
        variable.import_text('(Name="User.' + name + '",Type=(ClassStructOrEnum="' + FLOAT + '",UnderlyingType=2))')
        API.call_method('AddUserVariables', (system, [variable]))
for name, value in [('Lifetime Min', 2.1), ('Lifetime Max', 2.5)]:
    put(system, SMOKE, 'ParticleSpawnScript', 'InitializeParticle', name, '(Value=%s)' % value)
expression(system, SMOKE, 'ParticleSpawnScript', 'AddVelocity', 'Velocity Speed', 'User.SmokeForwardSpeed')
put(system, SMOKE, 'ParticleSpawnScript', 'AddVelocity', 'Cone Angle', '(Value=23)')
# DuplicateAsset retains the module GUIDs but not the source package metadata.
rise = unreal.EditorAssetLibrary.get_metadata_tag(smoke_source, 'GunplayV9.Rise')
put(system, SMOKE, 'ParticleUpdateScript', rise, 'Gravity', '(X=3.0,Y=2.0,Z=18.0)', '/Script/CoreUObject.Vector3f')
spread = unreal.EditorAssetLibrary.get_metadata_tag(smoke_source, 'GunplayV9.Spread')
expression(system, SMOKE, 'ParticleUpdateScript', spread, 'Particles.SpriteSize',
    'Particles.SmokeBirthSize * float2(0.85 + 1.8 * Particles.NormalizedAge, 0.85 + 2.1 * Particles.NormalizedAge)'
    ' * lerp(1.0, clamp(User.SmokeSpreadScale, 1.0, 2.5), ' + smooth_age(.04, .60) + ')')
expression(system, SMOKE, 'ParticleUpdateScript', 'ScaleColor', 'Scale Alpha',
    smooth_age(0, .075) + ' * pow(saturate(1.0 - Particles.NormalizedAge), 1.35)')
# Reuse the V9 continuous density field with its repaired Niagara sprite usage.
# The expanding smoke is world-space and retains its own birth size and color.
if not unreal.RainAssetEditor.compile_rain(system):
    raise RuntimeError('Could not compile smoke system')
save(system)

output = Path(unreal.Paths.project_saved_dir()) / 'GunplayVFX20260914'
output.mkdir(parents=True, exist_ok=True)
(output / 'created-assets-v10.json').write_text(json.dumps(CREATED, indent=2), encoding='utf-8')
unreal.log('GUNPLAY_V10_ASSETS_CREATED')
