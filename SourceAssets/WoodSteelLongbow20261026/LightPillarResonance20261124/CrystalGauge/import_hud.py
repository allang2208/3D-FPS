"""Author the crystal gauge texture and its translucent Slate material."""
from pathlib import Path
import unreal as ue

HERE = Path(__file__).resolve().parent
DEST = "/Game/Weapons/WoodSteelLongbow20261026/LightPillarHUD"
TEXTURE = "T_LightPillar_CrystalGauge"
MATERIAL = "M_LightPillar_CrystalGaugeHUD"
assets = ue.EditorAssetLibrary
tools = ue.AssetToolsHelpers.get_asset_tools()
graph = ue.MaterialEditingLibrary
assets.make_directory(DEST)

task = ue.AssetImportTask()
task.filename = str(HERE / (TEXTURE + "_Final.png"))
task.destination_path = DEST
task.destination_name = TEXTURE
task.automated = True
task.replace_existing = True
task.save = False
tools.import_asset_tasks([task])
texture = assets.load_asset(DEST + "/" + TEXTURE)
if not isinstance(texture, ue.Texture2D):
    raise RuntimeError("Crystal gauge texture import failed")
texture.set_editor_property("lod_group", ue.TextureGroup.TEXTUREGROUP_UI)
texture.set_editor_property("compression_settings", ue.TextureCompressionSettings.TC_EDITOR_ICON)
texture.set_editor_property("mip_gen_settings", ue.TextureMipGenSettings.TMGS_NO_MIPMAPS)
texture.set_editor_property("never_stream", True)
texture.set_editor_property("srgb", True)
texture.set_editor_property("filter", ue.TextureFilter.TF_BILINEAR)
for axis in ("address_x", "address_y"):
    texture.set_editor_property(axis, ue.TextureAddress.TA_CLAMP)

if assets.does_asset_exist(DEST + "/" + MATERIAL):
    material = assets.load_asset(DEST + "/" + MATERIAL)
else:
    material = tools.create_asset(MATERIAL, DEST, ue.Material, ue.MaterialFactoryNew())
for node in list(graph.get_material_expressions(material)):
    graph.delete_material_expression(material, node)
material.set_editor_property("material_domain", ue.MaterialDomain.MD_UI)
material.set_editor_property("blend_mode", ue.BlendMode.BLEND_TRANSLUCENT)

def wire(source, output, target, pin):
    if not graph.connect_material_expressions(source, output, target, pin):
        raise RuntimeError(f"Could not wire {source.get_name()}.{output} to {target.get_name()}.{pin}")

uv = graph.create_material_expression(material, ue.MaterialExpressionTextureCoordinate)
sample = graph.create_material_expression(material, ue.MaterialExpressionTextureSampleParameter2D)
sample.set_editor_property("parameter_name", "GaugeTexture")
sample.set_editor_property("texture", texture)
wire(uv, "", sample, "UVs")
state = graph.create_material_expression(material, ue.MaterialExpressionVectorParameter)
state.set_editor_property("parameter_name", "ResonanceState")
state.set_editor_property("default_value", ue.LinearColor(0, 0, 0, 0))
shader = graph.create_material_expression(material, ue.MaterialExpressionCustom)
shader.set_editor_property("output_type", ue.CustomMaterialOutputType.CMOT_FLOAT4)
shader.set_editor_property("code", """
// The cuts are at 37.3% and 62.9% of this artwork; each stack fills one pane.
float x = UV.x;
float stage = clamp(Progress * 3.0, 0.0, 3.0);
float front = 0.373 * saturate(stage)
            + 0.256 * saturate(stage - 1.0)
            + 0.371 * saturate(stage - 2.0);
float lit = stage <= 0.0 ? 0.0 : (stage >= 3.0 ? 1.0 : 1.0 - smoothstep(front-0.003,front+0.003,x));
float luma = dot(RGB,float3(0.2126,0.7152,0.0722));
float glass = smoothstep(0.435,0.465,UV.y) * (1.0-smoothstep(0.548,0.577,UV.y))
            * smoothstep(0.095,0.145,x) * (1.0-smoothstep(0.855,0.905,x));
float3 idle = lerp(RGB * 0.71, luma * float3(0.19,0.20,0.22), glass);
float crest = smoothstep(0.10,0.75,luma) * glass;
float glint = Gain * exp(-pow((x-front)/0.020, 2.0));
float3 active = RGB + float3(0.65,0.46,0.17) * crest * (0.30*glint+0.12*Pulse+0.055*Breath);
return float4(lerp(idle,active,lit),Alpha);
""")
connections = {
    "UV": (uv, ""), "RGB": (sample, "RGB"), "Alpha": (sample, "A"),
    "Progress": (state, "R"), "Gain": (state, "G"), "Breath": (state, "B"), "Pulse": (state, "A"),
}
pins = []
for name in connections:
    pin = ue.CustomInput()
    pin.set_editor_property("input_name", name)
    pins.append(pin)
shader.set_editor_property("inputs", pins)
for name, (source, output) in connections.items():
    wire(source, output, shader, name)
for channels, target in (("rgb", ue.MaterialProperty.MP_EMISSIVE_COLOR), ("a", ue.MaterialProperty.MP_OPACITY)):
    mask = graph.create_material_expression(material, ue.MaterialExpressionComponentMask)
    for channel in "rgba":
        mask.set_editor_property(channel, channel in channels)
    wire(shader, "", mask, "")
    if not graph.connect_material_property(mask, "", target):
        raise RuntimeError(f"Could not connect crystal gauge material output {target}")
errors = graph.recompile_material(material)
if errors:
    raise RuntimeError(str(errors))
if "-nullrhi" not in ue.SystemLibrary.get_command_line().lower():
    graph.get_statistics(material)
if not ue.EditorLoadingAndSavingUtils.save_packages([texture.get_outermost(), material.get_outermost()], False):
    raise RuntimeError("Could not save crystal gauge packages")
ue.log("LIGHT_PILLAR_HUD_SAVED " + material.get_path_name())
