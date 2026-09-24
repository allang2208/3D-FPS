"""Install combustion fields in the current persistent fireball material only.

Use the existing editor bridge if UE is open. This script does not change
Niagara emitters, maps, spell logic, light intensity or other fire magic.
"""
import hashlib
import json
import shutil
from pathlib import Path

import unreal

ROOT = Path(unreal.Paths.project_dir()).resolve()
SOURCE = ROOT / 'SourceAssets/FireballFluidCore20260923'
DEST = '/Game/Skills/Fireball/FluidCore20260923'
MATERIAL = '/Game/Skills/Fireball/TorchBurn20260921/M_FireballCohesiveCore'
LIB = unreal.MaterialEditingLibrary


def ensure_texture():
    path = DEST + '/T_FireballCombustionFields'
    texture = unreal.load_asset(path) if unreal.EditorAssetLibrary.does_asset_exist(path) else None
    if texture is None:
        filename = SOURCE / 'T_FireballCombustionFields.png'
        if not filename.is_file():
            raise RuntimeError('Restore or bake the original fireball combustion atlas first')
        task = unreal.AssetImportTask()
        for key, value in dict(filename=str(filename), destination_path=DEST,
                               destination_name='T_FireballCombustionFields', automated=True,
                               replace_existing=False, save=False).items():
            task.set_editor_property(key, value)
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        imported = task.get_editor_property('imported_object_paths')
        if not imported:
            raise RuntimeError('Combustion texture import failed')
        texture = unreal.load_asset(imported[0])
        for key, value in dict(srgb=False,
                               compression_settings=unreal.TextureCompressionSettings.TC_MASKS,
                               mip_gen_settings=unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS,
                               address_x=unreal.TextureAddress.TA_CLAMP,
                               address_y=unreal.TextureAddress.TA_CLAMP,
                               filter=unreal.TextureFilter.TF_BILINEAR).items():
            texture.set_editor_property(key, value)
        save(texture)
    return texture


def save(asset):
    if not unreal.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()], False):
        raise RuntimeError('Could not save ' + asset.get_path_name())
    unreal.log('FIREBALL_FLUID_CORE_SAVED ' + asset.get_path_name())


def connect(source, output, target, pin):
    if not LIB.connect_material_expressions(source, output, target, pin):
        raise RuntimeError('Could not connect combustion input ' + pin)


def input_pin(name):
    value = unreal.CustomInput()
    value.set_editor_property('input_name', name)
    return value


def install_on_material(material):
    texture = ensure_texture()
    nodes = LIB.get_material_expressions(material)
    fields = next(n for n in nodes if isinstance(n, unreal.MaterialExpressionCustom)
                  and ('float edgeRadius' in n.get_editor_property('code')
                       or n.get_editor_property('description') == 'Fireball cohesive combustion'))
    uv = next(n for n in nodes if isinstance(n, unreal.MaterialExpressionTextureCoordinate))
    clock = next(n for n in nodes if isinstance(n, unreal.MaterialExpressionTime))
    atlas = next((n for n in nodes if isinstance(n, unreal.MaterialExpressionTextureObject)
                  and n.get_editor_property('desc') == 'Fireball combustion atlas'), None)
    if atlas is None:
        atlas = LIB.create_material_expression(material, unreal.MaterialExpressionTextureObject)
        atlas.set_editor_property('desc', 'Fireball combustion atlas')
    atlas.set_editor_property('texture', texture)
    atlas.set_editor_property('sampler_type', unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
    sample = next((n for n in nodes if isinstance(n, unreal.MaterialExpressionCustom)
                   and n.get_editor_property('description') == 'Fireball Mantaflow animation'), None)
    if sample is None:
        sample = LIB.create_material_expression(material, unreal.MaterialExpressionCustom)
        sample.set_editor_property('description', 'Fireball Mantaflow animation')
    sample.set_editor_property('inputs', [input_pin(name) for name in ('UV', 'Clock', 'Atlas')])
    sample.set_editor_property('output_type', unreal.CustomMaterialOutputType.CMOT_FLOAT3)
    sample.set_editor_property('code', (SOURCE / 'CombustionSample.hlsl').read_text(encoding='utf-8'))
    connect(uv, '', sample, 'UV')
    connect(clock, '', sample, 'Clock')
    connect(atlas, '', sample, 'Atlas')
    pins = list(fields.get_editor_property('inputs'))
    if not any(str(pin.get_editor_property('input_name')) == 'Combustion' for pin in pins):
        pins.append(input_pin('Combustion'))
        fields.set_editor_property('inputs', pins)
    fields.set_editor_property('description', 'Fireball cohesive combustion')
    fields.set_editor_property('code', (SOURCE / 'CohesiveCombustion.hlsl').read_text(encoding='utf-8'))
    connect(sample, '', fields, 'Combustion')
    # Existing EyeAdaptationInverse, premultiplied opacity, depth fade and
    # temporal response remain wired exactly where the torch-core author put them.
    errors = LIB.recompile_material(material)
    if errors:
        raise RuntimeError('Fireball combustion material compile failed: ' + str(errors))
    save(material)
    return texture


def main():
    SOURCE.mkdir(parents=True, exist_ok=True)
    material = unreal.load_asset(MATERIAL)
    if material is None:
        raise RuntimeError('Current cohesive fireball core is missing')
    # Preserve the previous saved material before the first scoped edit.
    previous = ROOT / 'Content' / (MATERIAL.removeprefix('/Game/') + '.uasset')
    backup = SOURCE / 'Before' / previous.name
    backup.parent.mkdir(parents=True, exist_ok=True)
    if not backup.exists():
        shutil.copy2(previous, backup)
    texture = install_on_material(material)
    (SOURCE / 'delivery.json').write_text(json.dumps({
        'status': 'texture_imported_material_updated_compilation_requested_assets_saved',
        'material': material.get_path_name(), 'texture': texture.get_path_name(),
        'active_system': '/Game/Skills/Fireball/NS_FireballSlowBurnCore',
        'backup': str(backup), 'backup_sha256': hashlib.sha256(backup.read_bytes()).hexdigest(),
        'niagara_structure_changed': False, 'gameplay_changed': False,
        'additional_lights': 0, 'runtime_volume_simulation': False,
        'shader_compile_note': 'Material recompile API returned no immediate errors; editor may finish shader jobs asynchronously',
        'runtime_tested': False, 'visual_tested': False, 'performance_measured': False,
    }, indent=2), encoding='utf-8')
    unreal.log('FIREBALL_FLUID_CORE_INSTALLED')


if __name__ == '__main__':
    main()
