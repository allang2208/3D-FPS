"""Author the shop residents' HDR response in the current UE project."""
from pathlib import Path

import unreal as u


directory = "/Game/Characters/ResidentInteraction"
name = "M_ResidentShopHighlightResponse"
path = directory + "/" + name
library = u.EditorAssetLibrary
edit = u.MaterialEditingLibrary
library.make_directory(directory)
material = (library.load_asset(path) if library.does_asset_exist(path)
            else u.AssetToolsHelpers.get_asset_tools().create_asset(
                name, directory, u.Material, u.MaterialFactoryNew()))
edit.delete_all_material_expressions(material)
material.set_editor_property("material_domain", u.MaterialDomain.MD_POST_PROCESS)
# At native resolution depth of field and TSR can subsequently resolve the
# corrected colour and silhouette together. Bloom receives the adjusted HDR.
material.set_editor_property("blendable_location", u.BlendableLocation.BL_SCENE_COLOR_BEFORE_DOF)
material.set_editor_property("disable_pre_exposure_scale", True)
material.set_editor_property("is_blendable", False)

curve = edit.create_material_expression(material, u.MaterialExpressionCustom, -240, 0)
curve.set_editor_property("description", "Visible resident highlight response")
curve.set_editor_property("output_type", u.CustomMaterialOutputType.CMOT_FLOAT3)
curve.set_editor_property("code", Path(__file__).with_suffix(".hlsl").read_text(encoding="utf-8"))

sources = []
for index, (pin, texture_id) in enumerate((
        ("SceneInput", u.SceneTextureId.PPI_POST_PROCESS_INPUT0),
        ("ResidentId", u.SceneTextureId.PPI_CUSTOM_STENCIL),
        ("VisibleDepth", u.SceneTextureId.PPI_SCENE_DEPTH),
        ("ResidentDepth", u.SceneTextureId.PPI_CUSTOM_DEPTH))):
    sample = edit.create_material_expression(material, u.MaterialExpressionSceneTexture, -720, index * 150)
    sample.set_editor_property("scene_texture_id", texture_id)
    sample.set_editor_property("filtered", False)
    sources.append((pin, sample, "Color"))
eye = edit.create_material_expression(material, u.MaterialExpressionEyeAdaptation, -720, 600)
sources.append(("EyeExposure", eye, ""))
mask = edit.create_material_expression(material, u.MaterialExpressionScalarParameter, -720, 730)
mask.set_editor_property("parameter_name", "VisibleResidentSlots")
mask.set_editor_property("default_value", 0.0)
sources.append(("VisibleSlots", mask, ""))

inputs = []
for pin, _, _ in sources:
    entry = u.CustomInput()
    entry.set_editor_property("input_name", pin)
    inputs.append(entry)
curve.set_editor_property("inputs", inputs)
for pin, node, output in sources:
    if not edit.connect_material_expressions(node, output, curve, pin):
        raise RuntimeError("Could not wire " + pin)
if not edit.connect_material_property(curve, "", u.MaterialProperty.MP_EMISSIVE_COLOR):
    raise RuntimeError("Could not connect the scene output")
errors = edit.recompile_material(material)
if errors:
    raise RuntimeError(str(errors))
if not library.save_loaded_asset(material, False):
    raise RuntimeError("Could not save " + path)
u.SystemLibrary.execute_console_command(None, "RecompileShaders Material " + name + " Windows")
u.log("Saved " + path)
