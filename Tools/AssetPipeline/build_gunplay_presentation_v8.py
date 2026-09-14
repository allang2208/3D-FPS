"""Author denser white smoke and continuous, feathered muzzle flash alpha from V7.

UnrealEditor-Cmd -run=pythonscript -script=<file> -unattended -multiprocess -NullRHI.
Uses local owned Epic material/texture dependencies. No gameplay, tests or renders.
"""
import json
from pathlib import Path
import unreal

DEST = '/Game/Weapons/GunplayFX'
API = unreal.get_default_object(unreal.NiagaraToolset_System)
LIB = unreal.MaterialEditingLibrary
CREATED = []


def duplicate(source, name):
    target = DEST + '/' + name
    asset = unreal.load_asset(target) if unreal.EditorAssetLibrary.does_asset_exist(target) else None
    if not asset:
        asset = unreal.EditorAssetLibrary.duplicate_asset(source, target)
    if not asset:
        raise RuntimeError('Could not create ' + target)
    return asset


def save(asset):
    if not unreal.EditorAssetLibrary.save_loaded_asset(asset, False):
        raise RuntimeError('Could not save ' + asset.get_path_name())
    CREATED.append(asset.get_path_name())
    unreal.log('GUNPLAY_V8_SAVED ' + asset.get_path_name())


def put(system, emitter, script, module, name, value, typ='/Script/Niagara.NiagaraFloat'):
    if not unreal.RainAssetEditor.set_input(system, emitter, script, module, name, typ, value):
        raise RuntimeError('Could not author ' + emitter + '/' + module + '/' + name)


def expression(system, emitter, module, name, hlsl):
    put(system, emitter, 'ParticleUpdateScript', module, name,
        '(HlslExpression="' + hlsl + '")', '/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression')


def smooth_age(start, end):
    t = '(saturate((Particles.NormalizedAge - %s) / %s))' % (start, end - start)
    return '(' + t + '*' + t + '*(3.0-2.0*' + t + '))'


def assign_material(system, emitter, material):
    ref = unreal.NiagaraExt_StackItemReference()
    for name, value in dict(system=system, emitter_name=emitter, renderer_index=0).items():
        ref.set_editor_property(name, value)
    data = unreal.NiagaraExt_RendererData()
    data.set_editor_property('property_values', json.dumps({'Material': material.get_path_name()}))
    API.call_method('SetRendererData', (ref, data))


def scalars(material, values):
    names = {str(name) for name in LIB.get_scalar_parameter_names(material)}
    for name, value in values.items():
        if name in names:
            LIB.set_material_instance_scalar_parameter_value(material, name, value)
    LIB.update_material_instance(material)


def wire(source, output, target, pin):
    if not LIB.connect_material_expressions(source, output, target, pin):
        raise RuntimeError('Could not connect ' + target.get_name() + '/' + pin)


def flash_materials():
    # V7's three flash renderers use this same alpha-composite master. Its final
    # stage premultiplies emissive by opacity, so the new fade affects both together.
    parent = duplicate('/Game/NiagaraExamples/Materials/MasterMaterials/M_SmokeAndFire_Sprites',
                       'M_MuzzleFlashFeatherV8')
    nodes = {node.get_name(): node for node in LIB.get_material_expressions(parent)}
    raw_mask = nodes['MaterialExpressionSaturate_9']
    opacity_gain = nodes['MaterialExpressionMultiply_1']
    particle_color = nodes['MaterialExpressionParticleColor_1']
    feather = next((node for node in nodes.values() if isinstance(node, unreal.MaterialExpressionCustom)
                    and node.get_editor_property('description') == 'Gunplay V8 continuous feather'), None)
    if not feather:
        feather = LIB.create_material_expression(parent, unreal.MaterialExpressionCustom)
    feather.set_editor_property('description', 'Gunplay V8 continuous feather')
    feather.set_editor_property('output_type', unreal.CustomMaterialOutputType.CMOT_FLOAT1)
    pins = []
    for name in ['Opacity', 'ParticleAlpha']:
        pin = unreal.CustomInput()
        pin.set_editor_property('input_name', name)
        pins.append(pin)
    feather.set_editor_property('inputs', pins)
    # Lift the texture's grey fringe, then feather its weakest values to zero.
    # No discard or alpha-as-threshold erosion: even the last faint pixels fade continuously.
    feather.set_editor_property('code', '''float a = pow(saturate(Opacity), 0.68);
float rim = smoothstep(0.0, 0.26, a);
return a * rim * saturate(ParticleAlpha);''')
    wire(raw_mask, '', feather, 'Opacity')
    wire(particle_color, 'A', feather, 'ParticleAlpha')
    wire(feather, '', opacity_gain, 'A')
    parent.set_editor_property('enable_responsive_aa', True)
    LIB.recompile_material(parent)
    save(parent)
    materials = {}
    for key, source in [('Core', 'MI_MuzzleFlash_Sphere'), ('Lobes', 'MI_Flipbook_Pyro_Muzzle')]:
        material = duplicate('/Game/NiagaraExamples/FX_Weapons/MuzzleFlashes/Materials/Instances/' + source,
                             'MI_MuzzleFlash' + key + 'V8')
        LIB.set_material_instance_parent(material, parent)
        scalars(material, {'Opacity Gain': .90 if key == 'Core' else .82,
                           'Opacity Clip Value': 0, 'Depth Fade Distance': 3.5})
        save(material)
        materials[key] = material
    return materials


def smoke(system, hot):
    material = duplicate(DEST + ('/MI_BarrelWispyV7' if hot else '/MI_MuzzleSmokeV7'),
                         'MI_BarrelWhiteV8' if hot else 'MI_MuzzleWhiteV8')
    scalars(material, {'Opacity Gain': 2.15 if hot else 1.95,
                       'Fake Ambient Light Intensity': 1.45,
                       'Emissive Gain': .20 if hot else .06})
    # White density follows the runtime particle color instead of a blackbody tint.
    LIB.set_material_instance_static_switch_parameter_value(material, 'Use Blackbody', False)
    LIB.set_material_instance_static_switch_parameter_value(material, 'Use Particle Color For Base Color', True)
    LIB.set_material_instance_static_switch_parameter_value(material, 'Use Particle Alpha As Threshold', False)
    LIB.update_material_instance(material)
    save(material)
    assign_material(system, 'Muzzle_Smoke', material)
    for name, value in [('Lifetime Min', 1.0 if hot else .75),
                        ('Lifetime Max', 1.35 if hot else 1.05)]:
        put(system, 'Muzzle_Smoke', 'ParticleSpawnScript', 'InitializeParticle', name, '(Value=%s)' % value)
    expression(system, 'Muzzle_Smoke', 'ScaleColor', 'Scale Alpha',
        smooth_age(0, .06) + ' * (1.0 - ' + smooth_age(.34, 1) + ')')


materials = flash_materials()
for kind in ['Muzzle', 'BarrelSmoke']:
    system = duplicate(DEST + '/NS_FPS_' + kind + 'EpicV7', 'NS_FPS_' + kind + 'EpicV8')
    smoke(system, kind == 'BarrelSmoke')
    if kind == 'Muzzle':
        for emitter, (minimum, maximum) in {
            'Flash_Center': (.040, .060), 'MuzzleFlash_Front': (.095, .125),
            'MuzzleFlash_Side': (.070, .100)}.items():
            assign_material(system, emitter, materials['Core' if emitter == 'Flash_Center' else 'Lobes'])
            for name, value in [('Lifetime Min', minimum), ('Lifetime Max', maximum)]:
                put(system, emitter, 'ParticleSpawnScript', 'InitializeParticle', name, '(Value=%s)' % value)
            expression(system, emitter, 'ScaleColor', 'Scale Alpha',
                smooth_age(0, .025) + ' * pow(1.0 - ' + smooth_age(.06, 1) + ', 1.35)')
    if not unreal.RainAssetEditor.compile_rain(system):
        raise RuntimeError('Niagara compilation failed: ' + system.get_path_name())
    save(system)

output = Path(unreal.Paths.project_saved_dir()) / 'GunplayVFX20260914'
output.mkdir(parents=True, exist_ok=True)
(output / 'created-assets-v8.json').write_text(json.dumps(CREATED, indent=2), encoding='utf-8')
unreal.log('GUNPLAY_V8_ASSETS_CREATED')
