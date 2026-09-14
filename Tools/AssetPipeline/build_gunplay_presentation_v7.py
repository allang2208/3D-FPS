"""Author brighter muzzle smoke and layered, deforming muzzle flashes from local V6.

Run in UnrealEditor-Cmd with -run=pythonscript -unattended -multiprocess -NullRHI.
Creates project copies of owned Epic assets; does not run gameplay or previews.
"""
import json
from pathlib import Path
import unreal

DEST = '/Game/Weapons/GunplayFX'
API = unreal.get_default_object(unreal.NiagaraToolset_System)
LIB = unreal.MaterialEditingLibrary
FLOAT = '/Script/Niagara.NiagaraFloat'
EXPR = '/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression'
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
    unreal.log('GUNPLAY_V7_SAVED ' + asset.get_path_name())


def ref(system, emitter, script='', renderer=-1):
    result = unreal.NiagaraExt_StackItemReference()
    for key, value in dict(system=system, emitter_name=emitter, script_name=script,
                           renderer_index=renderer).items():
        result.set_editor_property(key, value)
    return result


def put(system, emitter, script, module, name, value, typ=FLOAT):
    if not unreal.RainAssetEditor.set_input(system, emitter, script, module, name, typ, value):
        raise RuntimeError('Could not author ' + emitter + '/' + module + '/' + name)


def expression(system, emitter, script, module, name, hlsl):
    put(system, emitter, script, module, name, '(HlslExpression="' + hlsl + '")', EXPR)


def smooth_age(start, end):
    # Niagara's CPU VectorVM needs the polynomial; smoothstep is not a VM opcode.
    t = '(saturate((Particles.NormalizedAge - %s) / %s))' % (start, end - start)
    return '(' + t + '*' + t + '*(3.0-2.0*' + t + '))'


def shape_module(system, emitter, script, attribute):
    # Store birth size explicitly: HLSL alone does not register Niagara Initial attributes.
    tag = 'GunplayV7.ShapeModule.' + emitter + '.' + script
    module = unreal.EditorAssetLibrary.get_metadata_tag(system, tag)
    if not module:
        entry = unreal.NiagaraExt_SetParameterEntry()
        entry.import_text('(Variable=(Name="' + attribute + '",Type=(ClassStructOrEnum="/Script/CoreUObject.Vector2f",UnderlyingType=2)))')
        topology = API.call_method('AddSetParametersModule',
            (ref(system, emitter, script), [entry]))
        module = str(topology.get_editor_property('module_name'))
        unreal.EditorAssetLibrary.set_metadata_tag(system, tag, module)
    return module


def smoke(system, hot):
    material = duplicate(DEST + ('/MI_BarrelWispyV6' if hot else '/MI_MuzzleSmokeV6'),
                         'MI_BarrelWispyV7' if hot else 'MI_MuzzleSmokeV7')
    names = {str(name) for name in LIB.get_scalar_parameter_names(material)}
    # Readable close to the camera, with restrained ambient fill and soft intersections.
    for name, value in [('Near Fade Distance', 8), ('Depth Fade Distance', 2.5),
                        ('Opacity Gain', 1.55 if hot else 1.40),
                        ('Emissive Gain', .20 if hot else .06),
                        ('Fake Ambient Light Intensity', 1.35)]:
        if name in names:
            LIB.set_material_instance_scalar_parameter_value(material, name, value)
    LIB.update_material_instance(material)
    save(material)
    renderer = unreal.NiagaraExt_RendererData()
    renderer.set_editor_property('property_values', json.dumps({'Material': material.get_path_name()}))
    API.call_method('SetRendererData', (ref(system, 'Muzzle_Smoke', renderer=0), renderer))
    for name, value in [('Lifetime Min', .90 if hot else .65),
                        ('Lifetime Max', 1.25 if hot else .95),
                        ('Uniform Sprite Size Min', 38 if hot else 44),
                        ('Uniform Sprite Size Max', 56 if hot else 64)]:
        put(system, 'Muzzle_Smoke', 'ParticleSpawnScript', 'InitializeParticle', name, '(Value=%s)' % value)
    put(system, 'Muzzle_Smoke', 'ParticleSpawnScript', 'AddVelocity', 'Cone Angle',
        '(Value=%s)' % (24 if hot else 16))
    # Fast puff formation, then a gradual fade instead of a barely visible late tail.
    expression(system, 'Muzzle_Smoke', 'ParticleUpdateScript', 'ScaleColor', 'Scale Alpha',
        smooth_age(0, .08) + ' * (1.0 - ' + smooth_age(.22, 1) + ')')


def flashes(system):
    lifetimes = {'Flash_Center': (.035, .052), 'MuzzleFlash_Front': (.045, .075),
                 'MuzzleFlash_Side': (.038, .065)}
    for emitter, (minimum, maximum) in lifetimes.items():
        for name, value in [('Lifetime Min', minimum), ('Lifetime Max', maximum)]:
            put(system, emitter, 'ParticleSpawnScript', 'InitializeParticle', name, '(Value=%s)' % value)
        # A brief attack and a curved decay keep the brightest phase readable without a hard cut.
        expression(system, emitter, 'ParticleUpdateScript', 'ScaleColor', 'Scale Alpha',
            smooth_age(0, .045) + ' * pow(saturate(1.0 - Particles.NormalizedAge), %s)' %
            (1.35 if emitter == 'Flash_Center' else 1.65))
        # Keep hue from the authored HDR color; alpha now handles the fade.
        put(system, emitter, 'ParticleUpdateScript', 'ScaleColor', 'ScaleRGB', '(Value=0)',
            '/Script/Niagara.NiagaraBool')
    for name, value in [('Uniform Sprite Size Min', 29), ('Uniform Sprite Size Max', 43)]:
        put(system, 'Flash_Center', 'ParticleSpawnScript', 'InitializeParticle', name, '(Value=%s)' % value)
    # Remove the example's second lifetime multiplication on the side flash.
    expression(system, 'MuzzleFlash_Side', 'ParticleSpawnScript',
        'SetVariables_8AD2DF8F42A2CECE59229E9B6B66351E', 'Particles.Lifetime', 'Particles.Lifetime')
    for emitter in ['MuzzleFlash_Front', 'MuzzleFlash_Side']:
        birth = shape_module(system, emitter, 'ParticleSpawnScript', 'Particles.GunplayBirthSize')
        expression(system, emitter, 'ParticleSpawnScript', birth,
            'Particles.GunplayBirthSize', 'Particles.SpriteSize')
        module = shape_module(system, emitter, 'ParticleUpdateScript', 'Particles.SpriteSize')
        # Texture axes deform independently: a short stretch followed by narrowing/collapse.
        expression(system, emitter, 'ParticleUpdateScript', module, 'Particles.SpriteSize',
            'Particles.GunplayBirthSize * float2(0.78 + 0.34 * sin(Particles.NormalizedAge * 3.141593), '
            '0.86 + 0.40 * sin(Particles.NormalizedAge * 2.8))')


for kind in ['Muzzle', 'BarrelSmoke']:
    system = duplicate(DEST + '/NS_FPS_' + kind + 'EpicV6', 'NS_FPS_' + kind + 'EpicV7')
    smoke(system, kind == 'BarrelSmoke')
    if kind == 'Muzzle':
        flashes(system)
    if not unreal.RainAssetEditor.compile_rain(system):
        raise RuntimeError('Niagara compilation failed: ' + system.get_path_name())
    save(system)

output = Path(unreal.Paths.project_saved_dir()) / 'GunplayVFX20260914'
output.mkdir(parents=True, exist_ok=True)
(output / 'created-assets-v7.json').write_text(json.dumps(CREATED, indent=2), encoding='utf-8')
unreal.log('GUNPLAY_V7_ASSETS_CREATED')
