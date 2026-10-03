"""Create an original-UV body material, without mutating prior rooted graphs."""
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/BlindSupplicantM07Meshy20261001')
DEST = '/Game/Monsters/BlindSupplicantM07'


def author_material(save):
    existing = u.load_asset(DEST+'/Materials/M07_Body_OriginalV07')
    if existing:
        return existing
    textures = {}
    for semantic, filename in [('BaseColor', 'M07_basecolor_source.jpg'), ('Roughness', 'M07_roughness.png'),
                               ('Metallic', 'M07_metallic.png'), ('Normal', 'M07_normal_source.jpg')]:
        task = u.AssetImportTask()
        task.filename = str(ROOT/'Textures'/filename)
        task.destination_path = DEST+'/Textures'
        task.destination_name = 'T_M07_OriginalBody_V07_'+semantic
        task.automated = True
        task.replace_existing = True
        task.replace_existing_settings = True
        task.save = False
        task.factory = u.TextureFactory()
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        texture = u.load_asset(task.destination_path+'/'+task.destination_name)
        if not texture:
            raise RuntimeError('Original-UV body texture import failed: '+semantic)
        texture.set_editor_property('srgb', semantic == 'BaseColor')
        texture.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_NORMALMAP if semantic == 'Normal' else
            u.TextureCompressionSettings.TC_DEFAULT if semantic == 'BaseColor' else u.TextureCompressionSettings.TC_MASKS)
        if semantic == 'Normal':
            texture.set_editor_property('flip_green_channel', True)
        save(texture)
        textures[semantic] = texture
    material = u.AssetToolsHelpers.get_asset_tools().create_asset('M07_Body_OriginalV07', DEST+'/Materials', u.Material, u.MaterialFactoryNew())
    material.set_editor_property('blend_mode', u.BlendMode.BLEND_OPAQUE)
    material.set_editor_property('two_sided', True)
    mel = u.MaterialEditingLibrary
    slab = mel.create_material_expression(material, u.MaterialExpressionSubstrateShadingModels)
    for semantic, prop in [('BaseColor', u.MaterialProperty.MP_BASE_COLOR), ('Roughness', u.MaterialProperty.MP_ROUGHNESS),
                           ('Metallic', u.MaterialProperty.MP_METALLIC), ('Normal', u.MaterialProperty.MP_NORMAL)]:
        node = mel.create_material_expression(material, u.MaterialExpressionTextureSample)
        node.set_editor_property('texture', textures[semantic])
        node.set_editor_property('sampler_type', u.MaterialSamplerType.SAMPLERTYPE_NORMAL if semantic == 'Normal' else
            u.MaterialSamplerType.SAMPLERTYPE_COLOR if semantic == 'BaseColor' else u.MaterialSamplerType.SAMPLERTYPE_MASKS)
        output = 'RGB' if semantic in ('BaseColor', 'Normal') else 'R'
        mel.connect_material_property(node, output, prop)
        mel.connect_material_expressions(node, output, slab, semantic)
    mel.connect_material_property(slab, '', u.MaterialProperty.MP_FRONT_MATERIAL)
    mel.set_base_material_usage(material, u.MaterialUsage.MATUSAGE_SKELETAL_MESH, True)
    mel.recompile_material(material)
    u.EditorAssetLibrary.set_metadata_tag(material, 'UVSource', 'Original Meshy GLB; no V03/V05 donor-body atlas')
    save(material)
    return material
