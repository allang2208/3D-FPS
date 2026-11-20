"""Shared rain, colour and relief finish for quarry scans and dressed stone."""
from pathlib import Path
import sys

import unreal as ue

tool_dir = str(Path(__file__).resolve().parent)
if tool_dir not in sys.path:
    sys.path.insert(0, tool_dir)
from quarry_stone_relief import apply_stone_relief


SPOIL_COLOR = """
float3 scan=Base;
float light=saturate(dot(scan,float3(.213,.715,.072)));
float grain=smoothstep(.10,.85,light);
float dirt=.5+.27*sin(P.x*.028+P.y*.019)+.23*sin(P.y*.065-P.z*.031);
float3 dusty=lerp(float3(.049,.041,.031),float3(.181,.159,.122),grain);
return dusty*(.77+.23*dirt)*(1.-saturate(Wet)*(.29+.10*dirt));
"""

WEATHER_COLOR = "Quarry.WorkedStone.Color"
WEATHER_ROUGHNESS = "Quarry.WorkedStone.Roughness"


def apply_weathered_finish(mat):
    """Update the original weather nodes in place before installing the grain layer."""
    lib = ue.MaterialEditingLibrary
    field = ("float patch=.5+.27*sin(P.x*.012+P.y*.009)+.23*sin(P.z*.026-P.x*.017); "
             "float w=saturate(Wet)*(.73+.27*patch);\n")
    color = (SPOIL_COLOR if mat.get_name() == "M_LimestoneSpoil" else
             field + "float3 stone=Base;return stone*float3(.93,.91,.86)*(.92+.08*patch)*(1.-.30*w);")
    rough = field + "return lerp(clamp(Base,.42,.97),clamp(Base*.60,.33,.54),w);"
    existing = {str(expr.get_editor_property("desc")): expr
                for expr in lib.get_material_expressions(mat)
                if isinstance(expr, ue.MaterialExpressionCustom)}
    changed = not mat.get_editor_property("used_with_nanite")
    if changed:
        mat.set_editor_property("used_with_nanite", True)
    weather = None
    for label, prop, out_type, code in (
        (WEATHER_COLOR, ue.MaterialProperty.MP_BASE_COLOR, ue.CustomMaterialOutputType.CMOT_FLOAT3, color),
        (WEATHER_ROUGHNESS, ue.MaterialProperty.MP_ROUGHNESS, ue.CustomMaterialOutputType.CMOT_FLOAT1, rough),
    ):
        expr = existing.get(label)
        if expr:
            if expr.get_editor_property("code") != code:
                expr.set_editor_property("code", code)
                changed = True
            continue
        source = lib.get_material_property_input_node(mat, prop)
        channel = lib.get_material_property_input_node_output_name(mat, prop) if source else ""
        if not source:
            source = lib.create_material_expression(mat, ue.MaterialExpressionConstant)
            source.r = .82 if prop == ue.MaterialProperty.MP_ROUGHNESS else .30
        if weather is None:
            weather = lib.create_material_expression(mat, ue.MaterialExpressionCollectionParameter)
            weather.set_editor_property("collection", ue.load_asset("/Game/Weather/Materials/MPC_FPS_Weather"))
            weather.set_editor_property("parameter_name", "WeatherWetness")
            position = lib.create_material_expression(mat, ue.MaterialExpressionWorldPosition)
        expr = lib.create_material_expression(mat, ue.MaterialExpressionCustom)
        expr.set_editor_property("desc", label)
        pins = []
        for key in ("Base", "Wet", "P"):
            pin = ue.CustomInput()
            pin.set_editor_property("input_name", key)
            pins.append(pin)
        expr.set_editor_property("inputs", pins)
        expr.set_editor_property("output_type", out_type)
        expr.set_editor_property("code", code)
        for dep, output, key in ((source, channel, "Base"), (weather, "", "Wet"), (position, "", "P")):
            if not lib.connect_material_expressions(dep, output, expr, key):
                raise RuntimeError(f"{mat.get_name()}: cannot connect {label}.{key}")
        if not lib.connect_material_property(expr, "", prop):
            raise RuntimeError(f"{mat.get_name()}: cannot connect {label}")
        changed = True
    relief_changed = apply_stone_relief(mat)
    return changed or relief_changed


if __name__ == "__main__":
    mat = ue.load_asset("/Game/WorldGeneration/TemperateHills/WhiteCliffs/Materials/M_LimestoneSpoil")
    if apply_weathered_finish(mat):
        errors = ue.MaterialEditingLibrary.recompile_material(mat)
        if errors or not ue.EditorAssetLibrary.save_loaded_asset(mat, False):
            raise RuntimeError("Could not save quarry spoil " + str(errors))
    ue.log("QUARRY_SPOIL_COLOUR_SAVED")
