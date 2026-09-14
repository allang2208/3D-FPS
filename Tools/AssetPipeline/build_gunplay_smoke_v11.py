"""Author brief, translucent muzzle smoke that keeps the aiming area readable.

Uses local V9/V10 smoke only; leaves V10 flash assets untouched. Asset authoring
and compilation, with no gameplay, screenshots or preview rendering.
"""
import json
from pathlib import Path
import unreal

ROOT = Path(unreal.Paths.project_dir())
DEST = '/Game/Weapons/GunplayFX'
API = unreal.get_default_object(unreal.NiagaraToolset_System)
LIB = unreal.MaterialEditingLibrary
FLOAT = '/Script/Niagara.NiagaraFloat'
EXPR = '/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression'
CREATED = []


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
    unreal.log('GUNPLAY_V11_SAVED ' + asset.get_path_name())


def ref(system, renderer=-1):
    result = unreal.NiagaraExt_StackItemReference()
    for key, value in dict(system=system, emitter_name='Muzzle_Smoke', renderer_index=renderer).items():
        result.set_editor_property(key, value)
    return result


def put(system, script, module, name, value, typ=FLOAT):
    if not unreal.RainAssetEditor.set_input(system, 'Muzzle_Smoke', script, module, name, typ, value):
        raise RuntimeError('Could not author ' + module + '/' + name)


def expression(system, script, module, name, code):
    put(system, script, module, name, '(HlslExpression="' + code + '")', EXPR)


def wire(source, output, target, pin):
    if not LIB.connect_material_expressions(source, output, target, pin):
        raise RuntimeError('Could not connect ' + target.get_name() + '/' + pin)


def sightline_material():
    material = duplicate(DEST + '/M_MuzzleSmokeSheetV9', 'M_MuzzleSmokeSheetV11')
    nodes = LIB.get_material_expressions(material)
    density = next(node for node in nodes if isinstance(node, unreal.MaterialExpressionCustom)
                   and node.get_editor_property('description') == 'Continuous world-space smoke density')
    opacity = next(node for node in nodes if isinstance(node, unreal.MaterialExpressionMultiply)
                   and density in LIB.get_inputs_for_material_expression(material, node))
    depth_fade = next(node for node in nodes if isinstance(node, unreal.MaterialExpressionDepthFade))
    sight = next((node for node in nodes if isinstance(node, unreal.MaterialExpressionCustom)
                  and node.get_editor_property('description') == 'Gunplay V11 sightline transparency'), None)
    if not sight:
        sight = LIB.create_material_expression(material, unreal.MaterialExpressionCustom)
        screen = LIB.create_material_expression(material, unreal.MaterialExpressionScreenPosition)
        view_size = LIB.create_material_expression(material, unreal.MaterialExpressionViewSize)
        pins = []
        for name in ['Opacity', 'ViewportUV', 'ViewportSize']:
            pin = unreal.CustomInput()
            pin.set_editor_property('input_name', name)
            pins.append(pin)
        sight.set_editor_property('inputs', pins)
        wire(opacity, '', sight, 'Opacity')
        wire(screen, 'ViewportUV', sight, 'ViewportUV')
        wire(view_size, '', sight, 'ViewportSize')
    sight.set_editor_property('description', 'Gunplay V11 sightline transparency')
    sight.set_editor_property('output_type', unreal.CustomMaterialOutputType.CMOT_FLOAT1)
    sight.set_editor_property('code',
        (ROOT / 'SourceAssets/GunplayVFX20260914/SmokeSightlineV11.hlsl').read_text(encoding='utf-8'))
    wire(sight, '', depth_fade, 'Opacity')
    LIB.set_base_material_usage(material, unreal.MaterialUsage.MATUSAGE_NIAGARA_SPRITES, True)
    errors = LIB.recompile_material(material)
    if errors:
        raise RuntimeError('Smoke material compilation failed: ' + '\n'.join(errors))
    save(material)
    return material


material = sightline_material()
system = duplicate(DEST + '/NS_FPS_MuzzleSmokeStreamV10', 'NS_FPS_MuzzleSmokeStreamV11')
variables = API.call_method('GetUserVariables', (system,)).export_text()
for name, typ in [('SmokeTailBlend', FLOAT), ('SmokeDrift', '/Script/CoreUObject.Vector3f')]:
    if 'User.' + name not in variables:
        variable = unreal.NiagaraExt_UserVariable()
        variable.import_text('(Name="User.' + name + '",Type=(ClassStructOrEnum="' + typ + '",UnderlyingType=2))')
        API.call_method('AddUserVariables', (system, [variable]))
# Main smoke clears rapidly; sparse tail particles have a slightly longer drift.
# Lifetime and velocity are sampled at spawn, not overwritten on existing smoke.
expression(system, 'ParticleSpawnScript', 'InitializeParticle', 'Lifetime Min',
           'lerp(0.55, 0.80, saturate(User.SmokeTailBlend))')
expression(system, 'ParticleSpawnScript', 'InitializeParticle', 'Lifetime Max',
           'lerp(0.85, 1.10, saturate(User.SmokeTailBlend))')
expression(system, 'ParticleSpawnScript', 'SetVariables_285AF4AB4D469F20CC2C7FB5409ABDBA',
           'Particles.Velocity', 'Particles.Velocity * User.SmokeScale + User.SmokeDrift')
put(system, 'ParticleUpdateScript', 'Drag', 'Drag', '(Value=0.85)')
source = unreal.load_asset(DEST + '/NS_FPS_MuzzleSmokeStreamV9')
rise = unreal.EditorAssetLibrary.get_metadata_tag(source, 'GunplayV9.Rise')
put(system, 'ParticleUpdateScript', rise, 'Gravity', '(X=0.0,Y=0.0,Z=10.0)', '/Script/CoreUObject.Vector3f')
# As the cloud spreads, its density falls instead of painting a larger opaque veil.
# Retain the V10 expansion shape and continuous emission to avoid per-shot puffs.
t = 'saturate(Particles.NormalizedAge / 0.07)'
expression(system, 'ParticleUpdateScript', 'ScaleColor', 'Scale Alpha',
    '(' + t + '*' + t + '*(3.0-2.0*' + t + '))'
    ' * pow(saturate(1.0 - Particles.NormalizedAge), 1.65) / (1.0 + 1.6 * Particles.NormalizedAge)')
data = unreal.NiagaraExt_RendererData()
data.set_editor_property('property_values', json.dumps({'Material': material.get_path_name()}))
API.call_method('SetRendererData', (ref(system, renderer=0), data))
if not unreal.RainAssetEditor.compile_rain(system):
    raise RuntimeError('Could not compile smoke system')
save(system)
output = Path(unreal.Paths.project_saved_dir()) / 'GunplayVFX20260914'
output.mkdir(parents=True, exist_ok=True)
(output / 'created-assets-v11.json').write_text(json.dumps(CREATED, indent=2), encoding='utf-8')
unreal.log('GUNPLAY_V11_ASSETS_CREATED')
