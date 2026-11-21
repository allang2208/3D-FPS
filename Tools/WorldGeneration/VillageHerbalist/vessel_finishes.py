"""Author the six shelf-vessel looks used by the village herbalist."""
from pathlib import Path
import json

import unreal as u


folder = "/Game/Building/PotionWorkbench20261015/V1/HerbalistVessels"
owner = "VillageHerbalist.VesselFinishes"
library = u.EditorAssetLibrary
editing = u.MaterialEditingLibrary
assets = u.AssetToolsHelpers.get_asset_tools()


def asset(name, cls, factory):
    path = folder + "/" + name
    if library.does_asset_exist(path):
        obj = library.load_asset(path)
        if library.get_metadata_tag(obj, "VillageHerbalist.Owner") != owner:
            raise RuntimeError("Existing material has another owner " + path)
    else:
        obj = assets.create_asset(name, folder, cls, factory())
    if not obj:
        raise RuntimeError("Could not create " + path)
    library.set_metadata_tag(obj, "VillageHerbalist.Owner", owner)
    return obj


def node(mat, cls, **properties):
    result = editing.create_material_expression(mat, cls)
    for key, value in properties.items():
        result.set_editor_property(key, value)
    return result


def wire(src, dst, pin, output=""):
    if pin == "Input":
        inputs = editing.get_material_expression_input_names(dst)
        if len(inputs) == 1:
            pin = str(inputs[0])
    if not editing.connect_material_expressions(src, output, dst, pin):
        raise RuntimeError("Could not bind " + dst.get_name() + "." + pin)


def prop(src, target):
    if not editing.connect_material_property(src, "", target):
        raise RuntimeError("Could not connect " + str(target))


def scalar(mat, name, default):
    return node(mat, u.MaterialExpressionScalarParameter, parameter_name=name, default_value=default)


def vector(mat, name, rgb):
    return node(mat, u.MaterialExpressionVectorParameter, parameter_name=name, default_value=u.LinearColor(*rgb, 1))


def master(name, transparent):
    mat = asset(name, u.Material, u.MaterialFactoryNew)
    for expression in list(editing.get_material_expressions(mat)):
        editing.delete_material_expression(mat, expression)
    mat.set_editor_property("two_sided", False)
    slab = node(mat, u.MaterialExpressionSubstrateSlabBSDF)
    if transparent:
        mat.set_editor_property("blend_mode", u.BlendMode.BLEND_TRANSLUCENT_COLORED_TRANSMITTANCE)
        mat.set_editor_property("translucency_lighting_mode", u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
        mat.set_editor_property("translucency_pass", u.MaterialTranslucencyPass.MTP_BEFORE_DOF)
        mat.set_editor_property("refraction_method", u.RefractionMode.RM_NONE)
        mat.set_editor_property("is_thin_surface", True)
        simple = next(getattr(u.MaterialSubSurfaceType, n) for n in dir(u.MaterialSubSurfaceType)
                      if "SIMPLE" in n and "VOLUME" in n)
        slab.set_editor_property("sub_surface_type", simple)
        conversion = node(mat, u.MaterialExpressionSubstrateTransmittanceToMFP)
        wire(vector(mat, "Transmission", (.98, .99, .98)), conversion, "TransmittanceColor")
        # This is transmittance per visible glass wall, at the default Slab thickness.
        wire(node(mat, u.MaterialExpressionConstant, r=.01), conversion, "Thickness")
        wire(conversion, slab, "SSS MFP", "MFP")
        wire(node(mat, u.MaterialExpressionConstant, r=.002), slab, "Diffuse Albedo")
        prop(node(mat, u.MaterialExpressionConstant, r=1.), u.MaterialProperty.MP_OPACITY)
    else:
        mat.set_editor_property("blend_mode", u.BlendMode.BLEND_OPAQUE)
        # Extracts render to depth before their glass. The actual mesh has a
        # separate horizontal meniscus; its upward-facing facets scatter more light.
        normal = node(mat, u.MaterialExpressionPixelNormalWS)
        up = node(mat, u.MaterialExpressionComponentMask, r=False, g=False, b=True, a=False)
        wire(normal, up, "Input")
        amount = node(mat, u.MaterialExpressionSaturate)
        wire(up, amount, "Input")
        colour = node(mat, u.MaterialExpressionLinearInterpolate)
        wire(vector(mat, "Extract", (.28, .024, .024)), colour, "A")
        wire(vector(mat, "Meniscus", (.43, .055, .04)), colour, "B")
        wire(amount, colour, "Alpha")
        wire(colour, slab, "Diffuse Albedo")
    wire(scalar(mat, "Reflectance", .012), slab, "F0")
    wire(scalar(mat, "Roughness", .33), slab, "Roughness")
    prop(slab, u.MaterialProperty.MP_FRONT_MATERIAL)
    editing.layout_material_expressions(mat)
    errors = editing.recompile_material(mat)
    if errors:
        raise RuntimeError(name + " " + str(errors))
    return mat


glass = master("M_HerbalistGlass", True)
extract = master("M_HerbalistExtract", False)
surfaces = [glass, extract]
looks = {
    "glass":       (glass, .33, .010, {"Transmission": (.973, .988, .982)}),
    "amberglass":  (glass, .35, .011, {"Transmission": (.972, .857, .684)}),
    "clearliquid": (glass, .26, .012, {"Transmission": (.824, .889, .813)}),
    "redliquid":   (extract, .33, .012, {"Extract": (.295, .018, .031), "Meniscus": (.46, .053, .044)}),
    "greenliquid": (extract, .32, .012, {"Extract": (.037, .213, .041), "Meniscus": (.123, .319, .076)}),
    "blueliquid":  (extract, .31, .012, {"Extract": (.025, .158, .415), "Meniscus": (.057, .287, .491)}),
}
for name, (parent, roughness, reflectance, colours) in looks.items():
    instance = asset("MI_PW_" + name, u.MaterialInstanceConstant, u.MaterialInstanceConstantFactoryNew)
    editing.set_material_instance_parent(instance, parent)
    for key, value in (("Roughness", roughness), ("Reflectance", reflectance)):
        editing.set_material_instance_scalar_parameter_value(instance, key, value)
    for key, rgb in colours.items():
        editing.set_material_instance_vector_parameter_value(instance, key, u.LinearColor(*rgb, 1))
    editing.update_material_instance(instance)
    surfaces.append(instance)

for surface in surfaces:
    if not library.save_loaded_asset(surface, False):
        raise RuntimeError("Could not save " + surface.get_path_name())
receipt = Path(u.Paths.project_saved_dir()).resolve() / "HerbalistVessels.json"
receipt.write_text(json.dumps([s.get_path_name() for s in surfaces], indent=2), encoding="utf8")
