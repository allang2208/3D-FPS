"""Create a dedicated skinned Manny body and switch the body configuration.

Run inside the existing editor through Tools/AssetPipeline/mcp_call_codex.ps1.
Only this task's new body assets are saved. No PIE, rendering or gameplay tests.
"""
import json
from pathlib import Path

import unreal as u


ROOT = Path("D:/FPS3D/FPSGAME").resolve()
if Path(u.Paths.project_dir()).resolve() != ROOT:
    raise RuntimeError("Body skin must be installed in D:/FPS3D/FPSGAME")

DEST = "/Game/Characters/Mannequins/PlayerBodySkin"
SOURCE = "/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple"
BODY_NAME = "SKM_Manny_PlayerSkin"
SOURCE_FILES = ROOT / "SourceAssets/PlayerBody20260921"
CONFIG = ROOT / "Content/ColdSteelData/player_body.json"
configuration_before = CONFIG.read_bytes()
configuration = json.loads(configuration_before.decode("utf-8-sig"))
previous_body = configuration["body_mesh"]
if previous_body.split(".")[0] not in (SOURCE, DEST + "/" + BODY_NAME):
    raise RuntimeError("The configured player body changed; preserve the new selection")

L, E = u.MaterialEditingLibrary, u.EditorAssetLibrary
A = u.AssetToolsHelpers.get_asset_tools()
source_mesh = u.load_asset(SOURCE)
if not source_mesh:
    raise RuntimeError("Missing source Manny mesh: " + SOURCE)
skin_tint = u.LinearColor(0.36, 0.235, 0.185, 1.0)
saved = []


def save(asset):
    if not E.save_loaded_asset(asset, False):
        raise RuntimeError("Could not save " + asset.get_path_name())
    saved.append(asset.get_path_name())


profile = u.load_asset(DEST + "/SSP_PlayerBodySkin")
if not profile:
    profile = A.create_asset("SSP_PlayerBodySkin", DEST, u.SubsurfaceProfile,
                             u.SubsurfaceProfileFactory())
    settings = profile.get_editor_property("settings")
    settings.set_editor_property("surface_albedo", skin_tint)
    settings.set_editor_property("enable_burley", True)
    settings.set_editor_property("mean_free_path_distance", 1.0)
    profile.set_editor_property("settings", settings)
    save(profile)

material = u.load_asset(DEST + "/M_PlayerBodySkin")
if material and E.get_metadata_tag(material, "PlayerBodySkinGraph") != "1":
    raise RuntimeError("Existing incomplete or independently edited material; preserve its graph")
if not material:
    material = A.create_asset("M_PlayerBodySkin", DEST, u.Material, u.MaterialFactoryNew())

    def node(cls, **properties):
        expression = L.create_material_expression(material, cls)
        for name, value in properties.items():
            expression.set_editor_property(name, value)
        return expression

    def scalar(name, value):
        return node(u.MaterialExpressionScalarParameter,
                    parameter_name=name, default_value=value)

    def output(expression, pin, prop):
        if not L.connect_material_property(expression, pin, prop):
            raise RuntimeError("Could not connect skin material output: " + str(prop))

    inputs = {
        "UV": node(u.MaterialExpressionTextureCoordinate),
        "SkinTint": node(u.MaterialExpressionVectorParameter,
                         parameter_name="SkinTint", default_value=skin_tint),
        "SkinRoughness": scalar("SkinRoughness", 0.49),
        "ToneVariation": scalar("ToneVariation", 0.055),
        "PoreTiling": scalar("PoreTiling", 1800.0),
        "SkinDetailStrength": scalar("SkinDetailStrength", 0.008),
    }
    shader = node(u.MaterialExpressionCustom,
                  code=(SOURCE_FILES / "body_skin.hlsl").read_text(encoding="utf-8"),
                  output_type=u.CustomMaterialOutputType.CMOT_FLOAT3,
                  description="Full-body procedural skin")
    custom_inputs = []
    for name in inputs:
        item = u.CustomInput()
        item.set_editor_property("input_name", name)
        custom_inputs.append(item)
    shader.set_editor_property("inputs", custom_inputs)
    custom_outputs = []
    for name, kind in (("OutNormal", u.CustomMaterialOutputType.CMOT_FLOAT3),
                       ("OutRoughness", u.CustomMaterialOutputType.CMOT_FLOAT1)):
        item = u.CustomOutput()
        item.set_editor_property("output_name", name)
        item.set_editor_property("output_type", kind)
        custom_outputs.append(item)
    shader.set_editor_property("additional_outputs", custom_outputs)
    for name, expression in inputs.items():
        if not L.connect_material_expressions(expression, "", shader, name):
            raise RuntimeError("Could not connect skin shader input: " + name)

    output(shader, "", u.MaterialProperty.MP_BASE_COLOR)
    output(shader, "OutNormal", u.MaterialProperty.MP_NORMAL)
    output(shader, "OutRoughness", u.MaterialProperty.MP_ROUGHNESS)
    output(scalar("SkinSpecular", 0.35), "", u.MaterialProperty.MP_SPECULAR)
    output(scalar("SkinScatterStrength", 0.18), "", u.MaterialProperty.MP_OPACITY)
    output(node(u.MaterialExpressionConstant, r=0.0), "", u.MaterialProperty.MP_METALLIC)
    material.set_editor_property("shading_model", u.MaterialShadingModel.MSM_SUBSURFACE_PROFILE)
    material.set_editor_property("subsurface_profile", profile)
    L.set_material_usage(material, u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    L.layout_material_expressions(material)
    errors = L.recompile_material(material)
    if errors:
        raise RuntimeError("Skin shader compilation failed: " + str(errors))
    E.set_metadata_tag(material, "PlayerBodySkinGraph", "1")
    save(material)

instance = u.load_asset(DEST + "/MI_PlayerBodySkin")
if not instance:
    instance = A.create_asset("MI_PlayerBodySkin", DEST, u.MaterialInstanceConstant,
                              u.MaterialInstanceConstantFactoryNew())
    L.set_material_instance_parent(instance, material)
    L.update_material_instance(instance)
    save(instance)

body = u.load_asset(DEST + "/" + BODY_NAME)
if not body:
    body = A.duplicate_asset(BODY_NAME, DEST, source_mesh)
if not body:
    raise RuntimeError("Could not create the dedicated player body mesh")
materials = body.get_editor_property("materials")
slots = []
for index, item in enumerate(materials):
    slots.append({"index": index, "name": str(item.material_slot_name),
                  "material": instance.get_path_name()})
    item.material_interface = instance
    # Unreal's reflected struct array iteration yields values; write the edited
    # struct back into its slot before assigning the array to the skeletal mesh.
    materials[index] = item
body.set_editor_property("materials", materials)
E.set_metadata_tag(body, "PlayerBodySourceMesh", SOURCE)
save(body)

# Keep all other config text and concurrent edits; activate only saved assets.
if CONFIG.read_bytes() != configuration_before:
    raise RuntimeError("Body configuration changed during import; saved assets left available")
text = configuration_before.decode("utf-8")
old_value = json.dumps(previous_body)
new_value = json.dumps(body.get_path_name())
if text.count(old_value) != 1:
    raise RuntimeError("Cannot uniquely replace body_mesh without changing other configuration")
CONFIG.write_bytes(text.replace(old_value, new_value, 1).encode("utf-8"))

report = {
    "scope": "All material slots on the third-person player body",
    "source_mesh": SOURCE,
    "body_mesh": body.get_path_name(),
    "material_instance": instance.get_path_name(),
    "subsurface_profile": profile.get_path_name(),
    "slots": slots,
    "saved_assets": saved,
    "configuration": str(CONFIG),
    "source": "Locally authored procedural skin; no downloaded scan",
    "first_person_assets_modified": False,
    "geometry_or_skeleton_modified": False,
    "runtime_tested": False,
}
(SOURCE_FILES / "body_skin_install.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, ensure_ascii=False))
