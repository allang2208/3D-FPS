"""Create only /Game/Weapons/GunplayFX procedural materials in an isolated UE commandlet.

UnrealEditor-Cmd.exe FPSGAME.uproject -run=pythonscript -script=<this file>
    -nullrhi -unattended -nosplash
No third-party files, maps, existing materials, editor settings or weather are modified.
"""
import json
from pathlib import Path

import unreal

DEST = "/Game/Weapons/GunplayFX"
FLASH_NAME = "M_GunFlash_Exposure"
SOURCE = Path(unreal.Paths.project_dir()) / "SourceAssets" / "GunplayFX"
SOURCE.mkdir(parents=True, exist_ok=True)
LIB = unreal.MaterialEditingLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()

FLASH_CODE = """
float2 p = (UV - 0.5) * 2.0;
float angle = atan2(p.y, p.x) + Seed;
float lobes = 0.76 + 0.16 * sin(angle * 5.0) + 0.08 * cos(angle * 9.0 + Seed);
float radius = length(p) / max(lobes, 0.35);
float fringe = 0.84 + 0.16 * sin(p.x * 25.0 + sin(p.y * 16.0) + Seed);
return pow(saturate(1.0 - radius), 1.25) * fringe;
""".strip()

SMOKE_CODE = """
float2 p = (UV - 0.5) * 2.0;
float low = sin(p.x * 4.2 + Seed) * cos(p.y * 3.7 + Seed * 1.6);
float mid = sin(p.x * 10.5 + sin(p.y * 7.2) + Seed * 2.3);
float fine = sin(p.x * 23.0 + p.y * 17.5 + Seed * 3.1);
float density = saturate(0.64 + 0.19 * low + 0.12 * mid + 0.05 * fine);
float edge = saturate(1.0 - length(p) + low * 0.09);
return smoothstep(0.0, 0.35, edge) * density * saturate(edge * 1.3);
""".strip()


def expr(material, cls, x=0, y=0):
    return LIB.create_material_expression(material, cls, x, y)


def scalar(material, name, value, x=-800, y=0):
    node = expr(material, unreal.MaterialExpressionScalarParameter, x, y)
    node.set_editor_property("parameter_name", name)
    node.set_editor_property("default_value", value)
    return node


def tint(material, value):
    node = expr(material, unreal.MaterialExpressionVectorParameter, -800, 320)
    node.set_editor_property("parameter_name", "Tint")
    node.set_editor_property("default_value", unreal.LinearColor(*value))
    return node


def connect(source, destination, socket):
    if not LIB.connect_material_expressions(source, "", destination, socket):
        raise RuntimeError(f"Material connection failed: {source.get_name()} -> {socket}")


def material_asset(name):
    path = f"{DEST}/{name}"
    material = unreal.load_asset(path)
    if material is None:
        material = TOOLS.create_asset(name, DEST, unreal.Material, unreal.MaterialFactoryNew())
    if not isinstance(material, unreal.Material):
        raise RuntimeError(f"Expected writable owned Material: {path}")
    # Existing runtime-referenced expressions can be rooted by the game CDO.
    # Callers retain existing graphs and apply additive upgrades below.
    return material


def card_material(name, code, additive):
    existing = unreal.load_asset(f"{DEST}/{name}")
    if isinstance(existing, unreal.Material):
        return existing.get_path_name()
    material = material_asset(name)
    material.set_editor_property("blend_mode", unreal.BlendMode.BLEND_ADDITIVE if additive else unreal.BlendMode.BLEND_TRANSLUCENT)
    material.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    material.set_editor_property("two_sided", True)
    material.set_editor_property("disable_depth_test", False)
    uv = expr(material, unreal.MaterialExpressionTextureCoordinate, -1000, -260)
    seed = scalar(material, "Seed", 1.0, -1000, -100)
    shape = expr(material, unreal.MaterialExpressionCustom, -700, -230)
    shape.set_editor_property("code", code)
    shape.set_editor_property("output_type", unreal.CustomMaterialOutputType.CMOT_FLOAT1)
    custom_inputs = []
    for name in ("UV", "Seed"):
        item = unreal.CustomInput()
        item.set_editor_property("input_name", name)
        custom_inputs.append(item)
    shape.set_editor_property("inputs", custom_inputs)
    connect(uv, shape, "UV")
    connect(seed, shape, "Seed")
    opacity = scalar(material, "Opacity", 0.6 if additive else 0.24, -700, 0)
    alpha = expr(material, unreal.MaterialExpressionMultiply, -400, -170)
    connect(shape, alpha, "A")
    connect(opacity, alpha, "B")
    # Soften intersections while preserving depth tests at nearby geometry.
    fade = expr(material, unreal.MaterialExpressionDepthFade, -180, -170)
    fade.set_editor_property("fade_distance_default", 1.5)
    connect(alpha, fade, "Opacity")
    LIB.connect_material_property(fade, "", unreal.MaterialProperty.MP_OPACITY)
    color = tint(material, (1.0, 0.42, 0.075, 1.0) if additive else (0.24, 0.26, 0.28, 1.0))
    emission = scalar(material, "Emission", 3.0 if additive else 0.12, -800, 470)
    color_gain = expr(material, unreal.MaterialExpressionMultiply, -400, 300)
    connect(color, color_gain, "A")
    # Smoke keeps its neutral visible color; flash intensity is independently bounded.
    if additive:
        connect(emission, color_gain, "B")
    else:
        one = scalar(material, "AmbientGain", 1.0, -800, 600)
        connect(one, color_gain, "B")
    if additive:
        # UE's inverse-exposure node defaults to unit LightValue and full Alpha.
        # Keep the short cosmetic flash readable across daylight/night exposure.
        inverse_exposure = expr(material, unreal.MaterialExpressionEyeAdaptationInverse, -180, 510)
        exposed_color = expr(material, unreal.MaterialExpressionMultiply, 60, 310)
        connect(color_gain, exposed_color, "A")
        connect(inverse_exposure, exposed_color, "B")
        LIB.connect_material_property(exposed_color, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    else:
        LIB.connect_material_property(color_gain, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    LIB.recompile_material(material)
    if not unreal.EditorAssetLibrary.save_loaded_asset(material, only_if_is_dirty=False):
        raise RuntimeError(f"Failed to save owned material: {material.get_path_name()}")
    return material.get_path_name()


def casing_material():
    existing = unreal.load_asset(f"{DEST}/M_CasingBrass")
    if isinstance(existing, unreal.Material):
        return existing.get_path_name()
    material = material_asset("M_CasingBrass")
    material.set_editor_property("blend_mode", unreal.BlendMode.BLEND_OPAQUE)
    material.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_DEFAULT_LIT)
    color = tint(material, (0.42, 0.25, 0.075, 1.0))
    LIB.connect_material_property(color, "", unreal.MaterialProperty.MP_BASE_COLOR)
    for param, default, prop in (("Metallic", 0.82, unreal.MaterialProperty.MP_METALLIC), ("Roughness", 0.31, unreal.MaterialProperty.MP_ROUGHNESS)):
        node = scalar(material, param, default)
        LIB.connect_material_property(node, "", prop)
    LIB.recompile_material(material)
    unreal.EditorAssetLibrary.save_loaded_asset(material, only_if_is_dirty=False)
    return material.get_path_name()


def upgrade_flash_exposure():
    material = unreal.load_asset(f"{DEST}/{FLASH_NAME}")
    if any(isinstance(node, unreal.MaterialExpressionEyeAdaptationInverse)
           for node in LIB.get_material_expressions(material)):
        return
    # Append the correction, without deleting rooted existing expressions.
    color = LIB.get_material_property_input_node(material, unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    if color is None:
        raise RuntimeError("Flash has no emissive color input")
    inverse = expr(material, unreal.MaterialExpressionEyeAdaptationInverse, -180, 510)
    corrected = expr(material, unreal.MaterialExpressionMultiply, 60, 310)
    connect(color, corrected, "A")
    connect(inverse, corrected, "B")
    if not LIB.connect_material_property(corrected, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR):
        raise RuntimeError("Failed to connect exposure-corrected emissive")
    LIB.recompile_material(material)
    if not unreal.EditorAssetLibrary.save_loaded_asset(material, only_if_is_dirty=False):
        raise RuntimeError("Failed to save exposure-corrected flash")


flash_only = "-gunplayflashonly" in unreal.SystemLibrary.get_command_line().lower()
assets = [card_material(FLASH_NAME, FLASH_CODE, True)]
upgrade_flash_exposure()
if not flash_only:
    assets += [card_material("M_GunSmoke", SMOKE_CODE, False), casing_material()]
for asset in assets:
    if not unreal.EditorAssetLibrary.does_asset_exist(asset):
        raise RuntimeError(f"Saved FX asset missing: {asset}")
(SOURCE / "flash_opacity.hlsl").write_text(FLASH_CODE + "\n", encoding="utf-8")
(SOURCE / "smoke_opacity.hlsl").write_text(SMOKE_CODE + "\n", encoding="utf-8")
report = {"assets": assets, "source": "Original analytic HLSL authored for FPSGAME; no downloaded textures", "pool_limit": 64,
          "flash_exposure_inverse": True, "flash_only_update": flash_only,
          "flash_seconds": [0.045, 0.065], "smoke_lifetime_seconds": [0.8, 1.25], "smoke_space": "world",
          "muzzle_socket": "WPN_SOCKET_Muzzle", "eject_socket": "WPN_SOCKET_Eject",
          "validation": "Materials created, connected, saved and read back; final rendered runtime handled separately"}
(SOURCE / "build_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
(SOURCE / "CREDITS.md").write_text("# Gunplay FX source\n\nOriginal procedural flash and smoke HLSL plus runtime animation, authored for this FPSGAME project on 2026-09-09. No third-party art downloads are used.\n\nGeometry uses Unreal Engine BasicShapes Plane/Cylinder, provided with the engine under its applicable license. The project-owned materials can be regenerated with Tools/AssetPipeline/build_gunplay_fx.py.\n", encoding="utf-8")
unreal.log("GUNPLAY_FX_BUILD_COMPLETE " + json.dumps(report))
