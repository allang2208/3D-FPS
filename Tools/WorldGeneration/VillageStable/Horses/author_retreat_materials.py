"""Build the masked retreat variants from the production warhorse surfaces."""
import unreal as u

HORSES = "/Game/WorldGeneration/TemperateHills/VillageStable/Horses"
LIB = u.EditorAssetLibrary
MAT = u.MaterialEditingLibrary


def make_variant(source, name, has_hair_mask):
    dest = HORSES + "/RetreatR21/" + name
    material = LIB.load_asset(dest) if LIB.does_asset_exist(dest) else LIB.duplicate_asset(HORSES + source, dest)
    if not material:
        raise RuntimeError(dest)
    if LIB.get_metadata_tag(material, "HorseRetreatFade") == "R21":
        return
    opacity = u.MaterialProperty.MP_OPACITY_MASK
    previous = MAT.get_material_property_input_node(material, opacity) if has_hair_mask else None
    if has_hair_mask and not previous:
        raise RuntimeError("Missing authored hair coverage in " + source)
    channel = MAT.get_material_property_input_node_output_name(material, opacity) if previous else ""
    material.set_editor_property("blend_mode", u.BlendMode.BLEND_MASKED)
    def node(kind):
        return MAT.create_material_expression(material, kind)
    def wire(src, output, target, pin):
        if not MAT.connect_material_expressions(src, output, target, pin):
            raise RuntimeError("Could not connect " + str(pin))
    fade = node(u.MaterialExpressionScalarParameter)
    fade.set_editor_property("parameter_name", "HorseRetreatFade")
    fade.set_editor_property("default_value", 0.0)
    fade.set_editor_property("use_custom_primitive_data", True)
    fade.set_editor_property("primitive_data_index", 0)
    coverage = node(u.MaterialExpressionOneMinus)
    wire(fade, "", coverage, "")
    dither = node(u.MaterialExpressionMaterialFunctionCall)
    dither.set_editor_property("material_function", u.load_asset("/Engine/Functions/Engine_MaterialFunctions02/Utility/DitherTemporalAA"))
    wire(coverage, "", dither, MAT.get_material_expression_input_names(dither)[0])
    mask = dither
    if previous:
        mask = node(u.MaterialExpressionMultiply)
        wire(previous, channel, mask, "A")
        wire(dither, "", mask, "B")
    if not MAT.connect_material_property(mask, "", opacity):
        raise RuntimeError("Unbound opacity in " + dest)
    MAT.layout_material_expressions(material)
    MAT.recompile_material(material)
    LIB.set_metadata_tag(material, "HorseRetreatFade", "R21")
    if not LIB.save_loaded_asset(material, False):
        raise RuntimeError("Could not save " + dest)


LIB.make_directory(HORSES + "/RetreatR21")
make_variant("/Surfaces/M_StableWarhorse", "M_Warhorse_Retreat", False)
make_variant("/ManeR17/M_Warhorse_Mane", "M_Mane_Retreat", True)
u.log("HORSE_RETREAT_MATERIALS_SAVED")
