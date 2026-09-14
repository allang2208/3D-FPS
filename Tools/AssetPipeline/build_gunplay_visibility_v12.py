"""Restore fresh smoke visibility and axial tracer visibility from local assets.

Material/Niagara authoring and compilation only. No game, previews or tests.
"""
import json
from pathlib import Path
import unreal

ROOT = Path(unreal.Paths.project_dir())
DEST = '/Game/Weapons/GunplayFX'
API = unreal.get_default_object(unreal.NiagaraToolset_System)
LIB = unreal.MaterialEditingLibrary
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
    unreal.log('GUNPLAY_V12_SAVED ' + asset.get_path_name())


def compile_material(material):
    errors = LIB.recompile_material(material)
    if errors:
        raise RuntimeError('Material compilation failed: ' + '\n'.join(errors))
    save(material)


def wire(source, output, target, pin):
    if not LIB.connect_material_expressions(source, output, target, pin):
        raise RuntimeError('Could not connect ' + target.get_name() + '/' + pin)


smoke_material = duplicate(DEST + '/M_MuzzleSmokeSheetV11', 'M_MuzzleSmokeSheetV12')
nodes = LIB.get_material_expressions(smoke_material)
sight = next(node for node in nodes if isinstance(node, unreal.MaterialExpressionCustom)
             and node.get_editor_property('description') in [
                 'Gunplay V11 sightline transparency', 'Gunplay V12 aged smoke sightline'])
inputs = list(sight.get_editor_property('inputs'))
if not any(str(pin.get_editor_property('input_name')) == 'ParticleAge' for pin in inputs):
    pin = unreal.CustomInput()
    pin.set_editor_property('input_name', 'ParticleAge')
    inputs.append(pin)
    sight.set_editor_property('inputs', inputs)
    age = LIB.create_material_expression(smoke_material, unreal.MaterialExpressionParticleRelativeTime)
    wire(age, '', sight, 'ParticleAge')
sight.set_editor_property('description', 'Gunplay V12 aged smoke sightline')
sight.set_editor_property('code',
    (ROOT / 'SourceAssets/GunplayVFX20260914/SmokeSightlineV12.hlsl').read_text(encoding='utf-8'))
LIB.set_base_material_usage(smoke_material, unreal.MaterialUsage.MATUSAGE_NIAGARA_SPRITES, True)
compile_material(smoke_material)

system = duplicate(DEST + '/NS_FPS_MuzzleSmokeStreamV11', 'NS_FPS_MuzzleSmokeStreamV12')
# Keep the short lifetime and capped continuous rate. Make the first part of each
# layer readable, then smoothly dilute the expanded cloud instead of extending it.
# A 20% boost is limited to the youngest smoke; it fades out by 35% age.
# Keep this expression shared with the targeted live-editor authoring script.
alpha = ' '.join((ROOT / 'SourceAssets/GunplayVFX20260914/SmokeAlphaV12.hlsl').read_text(encoding='utf-8').splitlines())
if not unreal.RainAssetEditor.set_input(system, 'Muzzle_Smoke', 'ParticleUpdateScript',
        'ScaleColor', 'Scale Alpha', EXPR, '(HlslExpression="' + alpha + '")'):
    raise RuntimeError('Could not author smoke opacity curve')
ref = unreal.NiagaraExt_StackItemReference()
for key, value in dict(system=system, emitter_name='Muzzle_Smoke', renderer_index=0).items():
    ref.set_editor_property(key, value)
data = unreal.NiagaraExt_RendererData()
data.set_editor_property('property_values', json.dumps({'Material': smoke_material.get_path_name()}))
API.call_method('SetRendererData', (ref, data))
if not unreal.RainAssetEditor.compile_rain(system):
    raise RuntimeError('Could not compile smoke system')
save(system)

tracer = duplicate(DEST + '/M_BallisticTracerSoftV2', 'M_BallisticTracerVisibleV12')
nodes = LIB.get_material_expressions(tracer)
shape = next(node for node in nodes if isinstance(node, unreal.MaterialExpressionCustom))
shape.set_editor_property('description', 'Gunplay V12 axial and side tracer visibility')
shape.set_editor_property('code',
    (ROOT / 'SourceAssets/GunplayVFX20260914/TracerVisibleV12.hlsl').read_text(encoding='utf-8'))
for node in nodes:
    if isinstance(node, unreal.MaterialExpressionDepthFade):
        node.set_editor_property('fade_distance_default', 1.0)
tracer.set_editor_property('enable_responsive_aa', True)
compile_material(tracer)

output = Path(unreal.Paths.project_saved_dir()) / 'GunplayVFX20260914'
output.mkdir(parents=True, exist_ok=True)
(output / 'created-assets-v12.json').write_text(json.dumps(CREATED, indent=2), encoding='utf-8')
unreal.log('GUNPLAY_V12_ASSETS_CREATED')
