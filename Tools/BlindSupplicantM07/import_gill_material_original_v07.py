"""UE background production hook for new original-UV gill material.

Call author_material() from the V07 importer before assigning the M07_Gills
slot. This creates fresh assets; old rooted material graphs are never deleted.
No editor UI, render or test is started.
"""
import json
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/BlindSupplicantM07Meshy20261001')
RECIPE = ROOT/'RecoveryOriginalV07/gills/gill_surface_recipe_v07.json'
DEST = '/Game/Monsters/BlindSupplicantM07'


def author_material(save_callback=None):
    record = json.loads(RECIPE.read_text(encoding='utf-8'))
    name = record['material']['asset_name']
    existing = u.load_asset(DEST+'/Materials/'+name)
    if existing is not None:
        # This material revision owns its own graph; repeated imports safely
        # reuse the already-saved graph rather than mutating rooted nodes.
        return existing
    save = save_callback or (lambda asset: u.EditorAssetLibrary.save_loaded_asset(asset, only_if_is_dirty=False))
    textures = {}
    for semantic in ('BaseColor', 'Roughness', 'Metallic', 'Normal', 'Thickness'):
        task = u.AssetImportTask()
        task.filename = record['textures'][semantic]
        task.destination_path = DEST+'/Textures'
        task.destination_name = 'T_M07_OriginalGills_V07_'+semantic
        task.automated = True
        task.replace_existing = True
        task.replace_existing_settings = True
        task.save = False
        task.factory = u.TextureFactory()
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        texture = u.load_asset(task.destination_path+'/'+task.destination_name)
        if texture is None:
            raise RuntimeError('Original-UV V07 gill texture import failed: '+semantic)
        texture.set_editor_property('srgb', semantic == 'BaseColor')
        texture.set_editor_property('compression_settings',
            u.TextureCompressionSettings.TC_NORMALMAP if semantic == 'Normal' else
            u.TextureCompressionSettings.TC_DEFAULT if semantic == 'BaseColor' else
            u.TextureCompressionSettings.TC_MASKS)
        if semantic == 'Normal':
            texture.set_editor_property('flip_green_channel', True)
        save(texture)
        textures[semantic] = texture
    material = u.AssetToolsHelpers.get_asset_tools().create_asset(name, DEST+'/Materials', u.Material, u.MaterialFactoryNew())
    if material is None:
        raise RuntimeError('Could not create fresh OriginalV07 gill material.')
    material.set_editor_property('two_sided', True)
    material.set_editor_property('blend_mode', u.BlendMode.BLEND_OPAQUE)
    material.set_editor_property('shading_model', u.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE)
    mel = u.MaterialEditingLibrary
    slab = mel.create_material_expression(material, u.MaterialExpressionSubstrateShadingModels)
    slab.set_editor_property('shading_model_override', u.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE)
    nodes = {}
    for semantic, prop in [('BaseColor', u.MaterialProperty.MP_BASE_COLOR), ('Roughness', u.MaterialProperty.MP_ROUGHNESS),
                           ('Metallic', u.MaterialProperty.MP_METALLIC), ('Normal', u.MaterialProperty.MP_NORMAL)]:
        node = mel.create_material_expression(material, u.MaterialExpressionTextureSample)
        node.set_editor_property('texture', textures[semantic])
        node.set_editor_property('sampler_type', u.MaterialSamplerType.SAMPLERTYPE_NORMAL if semantic == 'Normal' else
            u.MaterialSamplerType.SAMPLERTYPE_COLOR if semantic == 'BaseColor' else u.MaterialSamplerType.SAMPLERTYPE_MASKS)
        output = 'RGB' if semantic in ('BaseColor', 'Normal') else 'R'
        if not mel.connect_material_expressions(node, output, slab, semantic):
            raise RuntimeError('Original-UV gill Substrate link failed: '+semantic)
        mel.connect_material_property(node, output, prop)
        nodes[semantic] = node
    # TwoSidedFoliage backlighting keeps layer separation and visible branch
    # patterns in an opaque depth-writing pass. It does not alpha-composite
    # multiple folded shells into the prior translucent haze.
    strength = mel.create_material_expression(material, u.MaterialExpressionScalarParameter)
    strength.set_editor_property('parameter_name', 'ThinTissueBacklighting')
    strength.set_editor_property('default_value', record['material']['thin_organic_backlighting_scale'])
    tissue = mel.create_material_expression(material, u.MaterialExpressionMultiply)
    mel.connect_material_expressions(nodes['BaseColor'], 'RGB', tissue, 'A')
    mel.connect_material_expressions(strength, '', tissue, 'B')
    if not mel.connect_material_expressions(tissue, '', slab, 'Subsurface Color'):
        raise RuntimeError('Original-UV thin tissue SubSurfaceColor link failed.')
    mel.connect_material_property(tissue, '', u.MaterialProperty.MP_SUBSURFACE_COLOR)
    if not mel.connect_material_property(slab, '', u.MaterialProperty.MP_FRONT_MATERIAL):
        raise RuntimeError('Original-UV tissue front material link failed.')
    mel.set_base_material_usage(material, u.MaterialUsage.MATUSAGE_SKELETAL_MESH, True)
    mel.set_base_material_usage(material, u.MaterialUsage.MATUSAGE_CLOTHING, True)
    mel.recompile_material(material)
    save(material)
    return material


if __name__ == '__main__':
    author_material()
