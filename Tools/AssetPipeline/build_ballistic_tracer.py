"""Create the owned, depth-tested tracer material; no imported textures."""
import unreal

path = "/Game/Weapons/GunplayFX/M_BallisticTracer"
lib = unreal.MaterialEditingLibrary
material = unreal.load_asset(path)
if material is None:
    material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        "M_BallisticTracer", "/Game/Weapons/GunplayFX", unreal.Material, unreal.MaterialFactoryNew())
    material.set_editor_property("blend_mode", unreal.BlendMode.BLEND_ADDITIVE)
    material.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    material.set_editor_property("two_sided", True)
    material.set_editor_property("disable_depth_test", False)
    def node(cls):
        return lib.create_material_expression(material, cls)
    tint = node(unreal.MaterialExpressionVectorParameter)
    tint.set_editor_property("parameter_name", "Tint")
    tint.set_editor_property("default_value", unreal.LinearColor(1, .68, .22, 1))
    gain = node(unreal.MaterialExpressionScalarParameter)
    gain.set_editor_property("parameter_name", "Emission")
    gain.set_editor_property("default_value", 4)
    opacity = node(unreal.MaterialExpressionScalarParameter)
    opacity.set_editor_property("parameter_name", "Opacity")
    opacity.set_editor_property("default_value", 1)
    multiply = node(unreal.MaterialExpressionMultiply)
    lib.connect_material_expressions(tint, "", multiply, "A")
    lib.connect_material_expressions(gain, "", multiply, "B")
    exposure = node(unreal.MaterialExpressionEyeAdaptationInverse)
    corrected = node(unreal.MaterialExpressionMultiply)
    lib.connect_material_expressions(multiply, "", corrected, "A")
    lib.connect_material_expressions(exposure, "", corrected, "B")
    lib.connect_material_property(corrected, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    lib.connect_material_property(opacity, "", unreal.MaterialProperty.MP_OPACITY)
    lib.recompile_material(material)
    assert unreal.EditorAssetLibrary.save_loaded_asset(material, only_if_is_dirty=False)
assert not material.get_editor_property("disable_depth_test")
unreal.log("BALLISTIC_TRACER_MATERIAL_OK " + material.get_path_name())
