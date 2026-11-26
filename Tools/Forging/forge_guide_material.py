"""Shared high-contrast guide for every forge blank; no asset saves on import."""
import sys
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.project_dir())
sys.path.insert(0, str(ROOT / 'Tools/Fluids'))
from furnace_material_graph import node, wire, prop, custom, scalar

def build_guide_material(path):
    library = u.MaterialEditingLibrary
    material = u.load_asset(path) if u.EditorAssetLibrary.does_asset_exist(path) else None
    if material is None:
        folder, name = path.rsplit('/', 1)
        material = u.AssetToolsHelpers.get_asset_tools().create_asset(name, folder, u.Material, u.MaterialFactoryNew())
    material.modify()
    library.delete_all_material_expressions(material)
    material.set_editor_property('blend_mode', u.BlendMode.BLEND_TRANSLUCENT)
    material.set_editor_property('shading_model', u.MaterialShadingModel.MSM_UNLIT)
    material.set_editor_property('two_sided', True)
    material.set_editor_property('disable_depth_test', True)
    material.set_editor_property('allow_front_layer_translucency', False)
    material.set_editor_property('translucency_pass', u.MaterialTranslucencyPass.MTP_AFTER_DOF)
    uv = node(material, u.MaterialExpressionTextureCoordinate)
    tint = node(material, u.MaterialExpressionVectorParameter)
    tint.set_editor_property('parameter_name', 'Tint')
    tint.set_editor_property('default_value', u.LinearColor(.015, .65, 1, 1))
    heat = scalar(material, 'Heat', 1.4)
    guide = custom(material, (ROOT / 'SourceAssets/ForgeContrast20261024/Guide.hlsl').read_text(encoding='utf-8'),
                   {'UV': uv, 'Tint': (tint, 'RGB'), 'Heat': heat}, 4)
    rgb = custom(material, 'return Guide.rgb;', {'Guide': guide}, 3)
    opacity = custom(material, 'return Guide.a;', {'Guide': guide})
    # Exposure-compensated bounded colors keep white/cyan readable in the forge
    # camera without adding HDR glow or competing with the steel's emission.
    exposure = node(material, u.MaterialExpressionEyeAdaptationInverse)
    light_pin = next(str(pin) for pin in library.get_material_expression_input_names(exposure) if 'LightValue' in str(pin))
    wire(rgb, exposure, light_pin)
    prop(material, exposure, 'EMISSIVE_COLOR')
    prop(material, opacity, 'OPACITY')
    slab = node(material, u.MaterialExpressionSubstrateShadingModels)
    slab.set_editor_property('shading_model_override', u.MaterialShadingModel.MSM_UNLIT)
    wire(exposure, slab, 'Emissive Color'); wire(opacity, slab, 'Opacity')
    prop(material, slab, 'FRONT_MATERIAL')
    return material
