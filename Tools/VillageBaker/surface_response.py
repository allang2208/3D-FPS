"""Baker-specific dielectric response for the Substrate materials used on his R4 mesh."""
import unreal as u


# The bare portrait includes the brows, eyes and hair in the face atlas. Its
# existing spatial roughness variation supplies the remaining highlight detail.
SPECULAR = {
    "M_VillageBaker_FaceHair_0": .32,
    "M_VillageBaker_Neck": .32,
    "M_Baker_Skin": .32,
    "M_VillageBaker_CapLinen": .23,
    "M_Baker_Apron": .30,
    "M_Baker_Cuff": .30,
    "M_Baker_Pants": .30,
    "M_Baker_Sash": .30,
    "M_Baker_Shirt": .30,
    "M_Baker_Thread": .30,
    "M_Baker_Towel": .30,
}


def connect(material, slab):
    level = SPECULAR.get(material.get_name())
    if level is None:
        return
    editor = u.MaterialEditingLibrary
    inputs = editor.get_inputs_for_material_expression(material, slab)
    node = next((v for v in inputs if isinstance(v, u.MaterialExpressionConstant)
                 and v.get_editor_property("desc") == "Baker dielectric specular"), None)
    if node is None:
        node = editor.create_material_expression(material, u.MaterialExpressionConstant, -265, -170)
        node.set_editor_property("desc", "Baker dielectric specular")
    node.set_editor_property("r", level)
    if not editor.connect_material_expressions(node, "", slab, "Specular"):
        raise RuntimeError("Could not set specular for " + material.get_path_name())
