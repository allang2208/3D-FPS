"""Import Mantaflow smoke atlas and save a scoped V14 muzzle smoke variant.

Run using UnrealEditor-Cmd -run=pythonscript -script=<absolute path>
-unattended -nop4 -nosplash -NullRHI -multiprocess.
Asset import/authoring/compilation only; no game or preview runs.
"""
import json
from pathlib import Path

import unreal

ROOT = Path(unreal.Paths.project_dir())
SOURCE = ROOT / 'SourceAssets/MuzzleSmokeMantaflow20260923'
DEST = '/Game/Weapons/GunplayFX'
LIB = unreal.MaterialEditingLibrary
ASSETS = unreal.AssetToolsHelpers.get_asset_tools()
SAVED = []


def save(asset):
    if not unreal.EditorAssetLibrary.save_loaded_asset(asset, False):
        raise RuntimeError('Could not save ' + asset.get_path_name())
    SAVED.append(asset.get_path_name())
    unreal.log('MUZZLE_MANTAFLOW_SAVED ' + asset.get_path_name())


def duplicate(source, name):
    path = DEST + '/' + name
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        return unreal.load_asset(path)
    original = unreal.load_asset(DEST + '/' + source)
    asset = ASSETS.duplicate_asset(name, DEST, original)
    if not asset:
        raise RuntimeError('Could not duplicate ' + source)
    return asset


def wire(source, output, target, pin):
    if not LIB.connect_material_expressions(source, output, target, pin):
        raise RuntimeError('Could not connect ' + target.get_name() + '/' + pin)


def import_texture():
    filename = SOURCE / 'T_MuzzleSmokeMantaflowV14.png'
    if not filename.is_file():
        raise RuntimeError('Bake the Mantaflow source before importing the atlas')
    task = unreal.AssetImportTask()
    task.set_editor_property('filename', str(filename))
    task.set_editor_property('destination_path', DEST)
    task.set_editor_property('destination_name', 'T_MuzzleSmokeMantaflowV14')
    task.set_editor_property('automated', True)
    task.set_editor_property('replace_existing', True)
    task.set_editor_property('save', False)
    ASSETS.import_asset_tasks([task])
    paths = task.get_editor_property('imported_object_paths')
    if not paths:
        raise RuntimeError('Texture import did not produce an asset')
    texture = unreal.load_asset(paths[0])
    texture.set_editor_property('srgb', False)
    texture.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_MASKS)
    texture.set_editor_property('mip_gen_settings', unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    texture.set_editor_property('address_x', unreal.TextureAddress.TA_CLAMP)
    texture.set_editor_property('address_y', unreal.TextureAddress.TA_CLAMP)
    texture.set_editor_property('filter', unreal.TextureFilter.TF_BILINEAR)
    save(texture)
    return texture


def author_material(texture):
    material = duplicate('M_MuzzleSmokeSheetV12', 'M_MuzzleSmokeMantaflowV14')
    nodes = LIB.get_material_expressions(material)
    density = next(n for n in nodes if isinstance(n, unreal.MaterialExpressionCustom)
                   and n.get_editor_property('description') in (
                       'Continuous world-space smoke density', 'Mantaflow V14 smoke flipbook'))
    density.set_editor_property('description', 'Mantaflow V14 smoke flipbook')
    density.set_editor_property('code', (SOURCE / 'MuzzleSmokeFlipbookV14.hlsl').read_text(encoding='utf-8'))
    density.set_editor_property('output_type', unreal.CustomMaterialOutputType.CMOT_FLOAT1)
    inputs = []
    for name in ('SpriteUV', 'SmokeAtlas', 'ParticleAge'):
        item = unreal.CustomInput()
        item.set_editor_property('input_name', name)
        inputs.append(item)
    density.set_editor_property('inputs', inputs)
    uv = next(n for n in nodes if isinstance(n, unreal.MaterialExpressionTextureCoordinate))
    age = next(n for n in nodes if isinstance(n, unreal.MaterialExpressionParticleRelativeTime))
    atlas = next((n for n in nodes if isinstance(n, unreal.MaterialExpressionTextureObject)), None)
    if atlas is None:
        atlas = LIB.create_material_expression(material, unreal.MaterialExpressionTextureObject)
    atlas.set_editor_property('texture', texture)
    atlas.set_editor_property('sampler_type', unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
    wire(uv, '', density, 'SpriteUV')
    wire(atlas, '', density, 'SmokeAtlas')
    wire(age, '', density, 'ParticleAge')
    # Retain the existing lighting, ParticleColor alpha, depth intersection fade
    # and V12 age-dependent sightline protection. Only density is replaced.
    LIB.set_base_material_usage(material, unreal.MaterialUsage.MATUSAGE_NIAGARA_SPRITES, True)
    errors = LIB.recompile_material(material)
    if errors:
        raise RuntimeError('Smoke material compilation failed: ' + str(errors))
    save(material)
    return material


def author_system(material):
    system = duplicate('NS_FPS_MuzzleSmokeStreamV12', 'NS_FPS_MuzzleSmokeMantaflowV14')
    api = unreal.get_default_object(unreal.NiagaraToolset_System)
    ref = unreal.NiagaraExt_StackItemReference()
    for key, value in dict(system=system, emitter_name='Muzzle_Smoke', renderer_index=0).items():
        ref.set_editor_property(key, value)
    data = unreal.NiagaraExt_RendererData()
    data.set_editor_property('property_values', json.dumps({
        'Material': material.get_path_name(),
        'SubImageSize': {'X': 1.0, 'Y': 1.0}, 'bSubImageBlend': False}))
    api.call_method('SetRendererData', (ref, data))
    unreal.EditorAssetLibrary.set_metadata_tag(system, 'SmokeBake.Source',
                                              'Original Mantaflow impulse 96^3 / 64 frames')
    unreal.EditorAssetLibrary.set_metadata_tag(system, 'SmokeBake.Runtime',
                                              'V12 world-space emission + V14 density flipbook')
    if not unreal.RainAssetEditor.compile_rain(system):
        raise RuntimeError('Could not compile muzzle smoke system')
    save(system)


unreal.AssetRegistryHelpers.get_asset_registry().scan_paths_synchronous([DEST], force_rescan=True)
author_system(author_material(import_texture()))
(SOURCE / 'ue-assets.json').write_text(json.dumps({
    'saved_assets': SAVED,
    'status': 'assets_imported_authored_compiled_saved',
    'runtime_tested': False, 'visual_tested': False,
    'preserved': ['world-space particles', 'heat and shot feed', 'stop-fire wisps',
                  'ADS and scope alpha', 'existing muzzle placement', 'V10 muzzle flash'],
}, indent=2), encoding='utf-8')
unreal.log('MUZZLE_MANTAFLOW_AUTHORING_COMPLETE')
