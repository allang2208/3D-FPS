"""Author the Eclipse debuff's ground decal in the active FPSGAME project."""
from pathlib import Path

import unreal as ue


def build():
    if Path(ue.Paths.get_project_file_path()).stem not in {"FPSGAME", "EclipseAuraHost"}:
        raise RuntimeError("Select FPSGAME or the Eclipse aura authoring host")

    folder = "/Game/Weapons/FrontierCompoundBow/EclipseAuraR3"
    name = "M_EclipseGroundAura"
    ue.EditorAssetLibrary.make_directory(folder)
    path = f"{folder}/{name}"
    if ue.EditorAssetLibrary.does_asset_exist(path):
        material = ue.EditorAssetLibrary.load_asset(path)
    else:
        material = ue.AssetToolsHelpers.get_asset_tools().create_asset(
            name, folder, ue.Material, ue.MaterialFactoryNew())
    graph = ue.MaterialEditingLibrary
    graph.delete_all_material_expressions(material)
    material.set_editor_property("material_domain", ue.MaterialDomain.MD_DEFERRED_DECAL)
    material.set_editor_property("blend_mode", ue.BlendMode.BLEND_TRANSLUCENT)

    uv = graph.create_material_expression(material, ue.MaterialExpressionTextureCoordinate, -700, -80)
    clock = graph.create_material_expression(material, ue.MaterialExpressionTime, -700, 60)
    world = graph.create_material_expression(material, ue.MaterialExpressionWorldPosition, -700, 200)
    mask = graph.create_material_expression(material, ue.MaterialExpressionCustom, -380, 0)
    mask.set_editor_property("description", "Eclipse rim, penumbra and ground-facing mask")
    mask.set_editor_property("output_type", ue.CustomMaterialOutputType.CMOT_FLOAT1)
    pins = []
    for key in ("UV", "Seconds", "WorldPos"):
        pin = ue.CustomInput()
        pin.set_editor_property("input_name", key)
        pins.append(pin)
    mask.set_editor_property("inputs", pins)
    mask.set_editor_property("code", """
float r = length(2.0 * UV - 1.0);
float aa = clamp(fwidth(r), 0.003, 0.05);
float rim = 1.0 - smoothstep(0.016, 0.027 + aa, abs(r - 0.84));
float halo = 1.0 - smoothstep(0.0, 0.11, abs(r - 0.84));
float inner = 1.0 - smoothstep(0.003, 0.012 + aa, abs(r - 0.74));
float pulse = 0.93 + 0.07 * sin(Seconds * 2.6);
float3 n = cross(ddx(WorldPos), ddy(WorldPos));
float floorMask = smoothstep(0.32, 0.60, abs(n.z) * rsqrt(max(dot(n,n), 1e-12)));
return saturate(rim * 0.86 + halo * 0.32 + inner * 0.32) * floorMask * pulse;
""")
    for node, key in ((uv, "UV"), (clock, "Seconds"), (world, "WorldPos")):
        if not graph.connect_material_expressions(node, "", mask, key):
            raise RuntimeError(f"Could not bind {key}")
    for index, (color, prop) in enumerate((
        ((0.24, 0.052, 0.022), ue.MaterialProperty.MP_BASE_COLOR),
        ((0.53, 0.089, 0.031), ue.MaterialProperty.MP_EMISSIVE_COLOR),
    )):
        tint = graph.create_material_expression(material, ue.MaterialExpressionConstant3Vector, -380, 190 + 100 * index)
        tint.set_editor_property("constant", ue.LinearColor(*color, 1.0))
        if not graph.connect_material_property(tint, "", prop):
            raise RuntimeError(f"Could not bind {prop}")
    if not graph.connect_material_property(mask, "", ue.MaterialProperty.MP_OPACITY):
        raise RuntimeError("Could not bind opacity")
    graph.recompile_material(material)
    if not ue.EditorAssetLibrary.save_loaded_asset(material, False):
        raise RuntimeError("Could not save Eclipse ground aura")
    ue.log(f"Saved {material.get_path_name()}")


build()
