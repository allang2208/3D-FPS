"""Author and compile the M_VillageDistantBeacon material for R53 (HillsPerfOpt-R53)."""
import datetime
import hashlib
import json
import os
import shutil
from pathlib import Path

import unreal as u

PROJECT_ROOT = Path("D:/FPS3D/FPSGAME")
CONTENT_ROOT = PROJECT_ROOT / "Content"
BATCH_DIR = Path(os.environ.get("FPS_HILLS_R53_BATCH", "F:/FPSGAMEData/ArtProduction/HillsForestPath/HillsPerfOpt-R53"))
BEFORE_CONTENT = BATCH_DIR / "Before" / "Content"

BEACON_PKG = "/Game/WorldGeneration/TemperateHills/ShopLighting/M_VillageDistantBeacon"

lib = u.EditorAssetLibrary
mat_ed = u.MaterialEditingLibrary
tools = u.AssetToolsHelpers.get_asset_tools()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def pkg_to_disk(pkg_path: str) -> Path:
    clean = pkg_path.split(".")[0]
    return CONTENT_ROOT / (clean[6:] + ".uasset")


def backup_if_exists(pkg_path: str):
    src = pkg_to_disk(pkg_path)
    if not src.exists():
        return None
    rel = src.relative_to(CONTENT_ROOT)
    dst = BEFORE_CONTENT / rel
    if not dst.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    return {"package": pkg_path, "disk_path": str(src), "backup_path": str(dst), "before_sha256": sha256_file(dst)}


def get_or_create_material(pkg_path: str) -> tuple:
    folder, name = pkg_path.rsplit("/", 1)
    lib.make_directory(folder)
    existed = lib.does_asset_exist(pkg_path)
    if existed:
        backup_info = backup_if_exists(pkg_path)
        mat = u.load_asset(pkg_path)
    else:
        backup_info = {"package": pkg_path, "disk_path": str(pkg_to_disk(pkg_path)), "backup_path": None, "before_sha256": None}
        mat = tools.create_asset(name, folder, u.Material, u.MaterialFactoryNew())
    if not isinstance(mat, u.Material):
        raise RuntimeError(f"Failed to load/create material: {pkg_path}")
    return mat, existed, backup_info


def wire(src, out_pin: str, dst, in_pin: str):
    if not mat_ed.connect_material_expressions(src, out_pin, dst, in_pin):
        raise RuntimeError(f"Failed wiring {src.get_name()}.{out_pin} -> {dst.get_name()}.{in_pin}")


def add_custom(mat, desc: str, x: int, y: int, output_type, code: str, pin_specs: list):
    expr = mat_ed.create_material_expression(mat, u.MaterialExpressionCustom, x, y)
    expr.set_editor_property("description", desc)
    expr.set_editor_property("desc", desc)
    expr.set_editor_property("output_type", output_type)
    inputs = []
    for pin_name, _, _ in pin_specs:
        ci = u.CustomInput()
        ci.set_editor_property("input_name", pin_name)
        inputs.append(ci)
    expr.set_editor_property("inputs", inputs)
    expr.set_editor_property("code", code)
    for pin_name, src, out_pin in pin_specs:
        wire(src, out_pin, expr, pin_name)
    return expr


def build_beacon_material() -> dict:
    BATCH_DIR.mkdir(parents=True, exist_ok=True)
    BEFORE_CONTENT.mkdir(parents=True, exist_ok=True)

    mat, existed, backup_info = get_or_create_material(BEACON_PKG)
    stats_before = None
    if existed:
        st = mat_ed.get_statistics(mat)
        stats_before = {
            "num_pixel_shader_instructions": int(st.get_editor_property("num_pixel_shader_instructions")),
            "num_vertex_shader_instructions": int(st.get_editor_property("num_vertex_shader_instructions")),
            "num_samplers": int(st.get_editor_property("num_samplers")),
        }

    mat.modify()
    mat_ed.disconnect_material_property(mat, u.MaterialProperty.MP_EMISSIVE_COLOR)
    mat_ed.disconnect_material_property(mat, u.MaterialProperty.MP_WORLD_POSITION_OFFSET)
    for old_expr in list(mat_ed.get_material_expressions(mat)):
        mat_ed.delete_material_expression(mat, old_expr)
    mat_ed.delete_all_material_expressions(mat)
    remaining = list(mat_ed.get_material_expressions(mat))
    if remaining:
        raise RuntimeError(f"Expected 0 expressions after cleanup, found {len(remaining)}")

    mat.set_editor_property("blend_mode", u.BlendMode.BLEND_ADDITIVE)
    mat.set_editor_property("shading_model", u.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property("two_sided", True)
    mat.set_editor_property("used_with_instanced_static_meshes", True)
    mat.set_editor_property("enable_tessellation", False)

    # Shared coordinates & LWC-safe relative vectors
    uv = mat_ed.create_material_expression(mat, u.MaterialExpressionTextureCoordinate, -1200, -480)
    uv.set_editor_property("coordinate_index", 0)

    world_pos = mat_ed.create_material_expression(mat, u.MaterialExpressionWorldPosition, -1200, -320)
    cam_pos = mat_ed.create_material_expression(mat, u.MaterialExpressionCameraPositionWS, -1200, -160)

    local_origin = mat_ed.create_material_expression(mat, u.MaterialExpressionConstant3Vector, -1450, 0)
    local_origin.set_editor_property("constant", u.LinearColor(0.0, 0.0, 0.0, 1.0))

    center_ws = mat_ed.create_material_expression(mat, u.MaterialExpressionTransformPosition, -1200, 0)
    center_ws.set_editor_property("transform_source_type", u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_INSTANCE)
    center_ws.set_editor_property("transform_type", u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_WORLD)
    wire(local_origin, "", center_ws, "")

    cam_to_center = mat_ed.create_material_expression(mat, u.MaterialExpressionSubtract, -880, -140)
    wire(center_ws, "", cam_to_center, "A")
    wire(cam_pos, "", cam_to_center, "B")

    center_offset = mat_ed.create_material_expression(mat, u.MaterialExpressionSubtract, -880, -280)
    wire(world_pos, "", center_offset, "A")
    wire(center_ws, "", center_offset, "B")

    def inst_data(idx: int, default: float, y: int):
        n = mat_ed.create_material_expression(mat, u.MaterialExpressionPerInstanceCustomData, -1200, y)
        n.set_editor_property("data_index", idx)
        n.set_editor_property("const_default_value", default)
        return n

    radius_cm = inst_data(0, 90.0, 160)
    strength = inst_data(1, 1.2, 260)
    warmth = inst_data(2, 0.6, 360)
    min_fade_cm = inst_data(3, 3200.0, 460)
    is_haze = inst_data(4, 0.0, 560)

    rand_node = mat_ed.create_material_expression(mat, u.MaterialExpressionPerInstanceRandom, -1200, 680)
    time_node = mat_ed.create_material_expression(mat, u.MaterialExpressionTime, -1200, 780)
    night_param = mat_ed.create_material_expression(mat, u.MaterialExpressionScalarParameter, -1200, 880)
    night_param.set_editor_property("parameter_name", "NightIntensity")
    night_param.set_editor_property("default_value", 1.0)

    wpo_code = """
float2 cUV = (UV - 0.5) * 2.0;
float dist = length(CamToCenter);
float fadeIn = smoothstep(MinFadeCm * 0.70, MinFadeCm * 1.40, dist);
float distScale = (IsHaze > 0.5) ? 1.0 : lerp(1.0, 2.8, smoothstep(5000.0, 60000.0, dist));
float r = RadiusCm * distScale * fadeIn;
float3 viewDir = CamToCenter / max(dist, 1.0);
float3 targetOffset = (ResolvedView.ViewRight * cUV.x + ResolvedView.ViewUp * (-cUV.y)) * r
    - viewDir * min(dist * 0.02, 40.0);
return targetOffset - CenterOffset;
""".strip()

    wpo_node = add_custom(
        mat,
        "R53 Distant Beacon Billboard WPO",
        -420,
        -240,
        u.CustomMaterialOutputType.CMOT_FLOAT3,
        wpo_code,
        [
            ("UV", uv, ""),
            ("CamToCenter", cam_to_center, ""),
            ("CenterOffset", center_offset, ""),
            ("RadiusCm", radius_cm, ""),
            ("MinFadeCm", min_fade_cm, ""),
            ("IsHaze", is_haze, ""),
        ],
    )

    emissive_code = """
float dist = length(CamToCenter);
float nearFade = smoothstep(MinFadeCm * 0.85, MinFadeCm * 1.85, dist);
float farFade = 1.0 - smoothstep(115000.0, 148000.0, dist);
float2 p = (UV - 0.5) * 2.0;
float r = length(p);
if (r >= 1.0)
{
    return float3(0.0, 0.0, 0.0);
}
if (IsHaze > 0.5)
{
    float halo = pow(saturate(1.0 - r), 2.4) * 0.28 * Strength;
    float3 hazeCol = lerp(float3(1.0, 0.42, 0.14), float3(1.0, 0.74, 0.36), saturate(Warmth));
    return hazeCol * (halo * NightIntensity * nearFade * farFade);
}
float core = exp(-r * r * 14.0);
float halo = pow(saturate(1.0 - r), 3.0) * 0.55;
float flicker = 0.92 + 0.08 * sin(Time * 2.6 + Rand * 6.28318);
float distBoost = lerp(1.0, 2.2, smoothstep(8000.0, 75000.0, dist));
float lum = (core * 2.4 + halo) * Strength * flicker * distBoost;
float3 beaconCol = lerp(float3(1.0, 0.55, 0.18), float3(1.0, 0.88, 0.56), saturate(Warmth + core * 0.35));
return beaconCol * (lum * NightIntensity * nearFade * farFade);
""".strip()

    emissive_node = add_custom(
        mat,
        "R53 Distant Beacon Emissive Glow",
        -420,
        220,
        u.CustomMaterialOutputType.CMOT_FLOAT3,
        emissive_code,
        [
            ("UV", uv, ""),
            ("CamToCenter", cam_to_center, ""),
            ("Time", time_node, ""),
            ("Rand", rand_node, ""),
            ("NightIntensity", night_param, ""),
            ("Strength", strength, ""),
            ("Warmth", warmth, ""),
            ("MinFadeCm", min_fade_cm, ""),
            ("IsHaze", is_haze, ""),
        ],
    )

    if not mat_ed.connect_material_property(emissive_node, "", u.MaterialProperty.MP_EMISSIVE_COLOR):
        raise RuntimeError("Failed connecting MP_EMISSIVE_COLOR")
    if not mat_ed.connect_material_property(wpo_node, "", u.MaterialProperty.MP_WORLD_POSITION_OFFSET):
        raise RuntimeError("Failed connecting MP_WORLD_POSITION_OFFSET")

    errors = mat_ed.recompile_material(mat)
    if errors:
        raise RuntimeError(f"Material compile errors on {BEACON_PKG}: {errors}")

    customs = [e for e in mat_ed.get_material_expressions(mat) if isinstance(e, u.MaterialExpressionCustom)]
    if len(customs) != 2:
        raise RuntimeError(f"Expected exactly 2 Custom expressions, found {len(customs)}")
    for ce in customs:
        names = list(mat_ed.get_material_expression_input_names(ce))
        ins = list(mat_ed.get_inputs_for_material_expression(mat, ce))
        missing = [str(n) for n, i in zip(names, ins) if i is None]
        if missing:
            raise RuntimeError(f"Custom node {ce.get_editor_property('description')} has unwired pins: {missing}")

    if not lib.save_loaded_asset(mat, False):
        raise RuntimeError(f"Failed saving material {BEACON_PKG}")

    st_after = mat_ed.get_statistics(mat)
    stats_after = {
        "num_pixel_shader_instructions": int(st_after.get_editor_property("num_pixel_shader_instructions")),
        "num_vertex_shader_instructions": int(st_after.get_editor_property("num_vertex_shader_instructions")),
        "num_samplers": int(st_after.get_editor_property("num_samplers")),
    }
    if stats_after["num_samplers"] > 2:
        raise RuntimeError(f"Expected <=2 engine samplers (0 textures) on {BEACON_PKG}, got {stats_after['num_samplers']}")

    compiled = {
        "package": BEACON_PKG,
        "existed_before": existed,
        "before": stats_before,
        "after": stats_after,
    }
    (BATCH_DIR / "compiled.json").write_text(json.dumps(compiled, indent=2), encoding="utf-8")

    disk_path = pkg_to_disk(BEACON_PKG)
    backup_info["after_sha256"] = sha256_file(disk_path) if disk_path.exists() else None
    receipt = {
        "batch": "HillsPerfOpt-R53",
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "script": "Tools/WorldGeneration/ForestVillage/optimize_hills_perf_r53.py",
        "material": compiled,
        "backups_and_hashes": [backup_info],
    }
    receipt_path = BATCH_DIR / "published.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8")
    u.log(f"[R53-DONE] {BEACON_PKG} ps={stats_after['num_pixel_shader_instructions']} vs={stats_after['num_vertex_shader_instructions']} samplers={stats_after['num_samplers']}")


if __name__ == "__main__":
    build_beacon_material()
