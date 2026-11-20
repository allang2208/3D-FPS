"""Save the resident-focus variant of the dungeon's visible green contour."""
from pathlib import Path

import unreal as u


base = "/Game/Dungeons/StaffLiving20261002/ScenePolishV4/Materials/M_Staff_ContainerOutline_V4"
folder = "/Game/Characters/ResidentInteraction"
destination = folder + "/M_ResidentFocusOutline"
assets = u.EditorAssetLibrary
editing = u.MaterialEditingLibrary

assets.make_directory(folder)
material = (assets.load_asset(destination) if assets.does_asset_exist(destination)
            else assets.duplicate_asset(base, destination))
if not material:
    raise RuntimeError("Could not create resident outline material")

edge = editing.get_material_property_input_node(material, u.MaterialProperty.MP_EMISSIVE_COLOR)
nodes = editing.get_material_expressions(material)
stencil = next((node for node in nodes if isinstance(node, u.MaterialExpressionScalarParameter)
                and str(node.get_editor_property("parameter_name")) == "ResidentStencil"), None)
if not stencil:
    stencil = editing.create_material_expression(material, u.MaterialExpressionScalarParameter, -700, 640)
    stencil.set_editor_property("parameter_name", "ResidentStencil")
    stencil.set_editor_property("default_value", 0)
    pins = [pin for pin in edge.get_editor_property("inputs") if str(pin.get_editor_property("input_name")) != "Yellow"]
    pin = u.CustomInput()
    pin.set_editor_property("input_name", "ResidentStencil")
    edge.set_editor_property("inputs", pins + [pin])
    if not editing.connect_material_expressions(stencil, "", edge, "ResidentStencil"):
        raise RuntimeError("Could not connect per-view resident stencil")
    for node in nodes:
        if isinstance(node, u.MaterialExpressionVectorParameter) and str(node.get_editor_property("parameter_name")) == "Yellow":
            editing.delete_material_expression(material, node)

edge.set_editor_property("code", Path(__file__).with_name("resident_outline.hlsl").read_text("utf-8"))
edge.set_editor_property("description", "Visible resident silhouette selected by this camera")
material.set_editor_property("blendable_priority", 31)
material.set_editor_property("is_blendable", False)
errors = editing.recompile_material(material)
if errors:
    raise RuntimeError(str(errors))
if not assets.save_loaded_asset(material, False):
    raise RuntimeError("Could not save " + destination)
u.log("Saved resident focus material " + destination)
