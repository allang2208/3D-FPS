"""Author M_VillageDistantBeacon (R55 upgrade) and M_VillageWarmWindow for HillsPerfOpt-R55.

Upgrades the ultra-far village night silhouette (Second Tier):
1. M_VillageDistantBeacon:
   - Mode 0: Hooded exterior lamp halo with tighter far scale (1.55x max), near-zero forward pop,
     upward cap attenuation (brighter downward spill), and Scene DepthFade.
   - Mode 1: Ground-hugging wide flat backlit valley haze dome (~3.7:1 aspect, seated below terrain
     at the base) so village rooftops/bellcote/windmill sails read as dark silhouettes.
   - Mode 2: Horizontal terrain-seated ground spill pool beneath street/gate/yard lanterns.
2. M_VillageWarmWindow:
   - Physically anchored emissive window glass quads placed inside real repaired buildings
     (rectangular casement / Gothic lancet arch / rose oculus) with mullion tracery, warm
     interior gradient, grazing-angle reveal fade, and close-range fade-out.
"""

import datetime
import hashlib
import json
import os
import shutil
from pathlib import Path

import unreal as u

PROJECT_ROOT = Path("D:/FPS3D/FPSGAME")
CONTENT_ROOT = PROJECT_ROOT / "Content"
BATCH_DIR = Path(os.environ.get("FPS_HILLS_R55_BATCH", "F:/FPSGAMEData/ArtProduction/HillsForestPath/HillsPerfOpt-R55"))
BEFORE_CONTENT = BATCH_DIR / "Before" / "Content"

BEACON_PKG = "/Game/WorldGeneration/TemperateHills/ShopLighting/M_VillageDistantBeacon"
WINDOW_PKG = "/Game/WorldGeneration/TemperateHills/ShopLighting/M_VillageWarmWindow"

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
        return {"package": pkg_path, "disk_path": str(src), "backup_path": None, "before_sha256": None}
    rel = src.relative_to(CONTENT_ROOT)
    dst = BEFORE_CONTENT / rel
    if not dst.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    return {
        "package": pkg_path,
        "disk_path": str(src),
        "backup_path": str(dst),
        "before_sha256": sha256_file(dst),
    }


def get_or_create_material(pkg_path: str) -> tuple:
    folder, name = pkg_path.rsplit("/", 1)
    lib.make_directory(folder)
    existed = lib.does_asset_exist(pkg_path)
    backup_info = backup_if_exists(pkg_path)
    if existed:
        mat = u.load_asset(pkg_path)
    else:
        mat = tools.create_asset(name, folder, u.Material, u.MaterialFactoryNew())
    if not isinstance(mat, u.Material):
        raise RuntimeError(f"Failed to load/create material: {pkg_path}")
    return mat, existed, backup_info


def wire(src, out_pin: str, dst, in_pin: str):
    if not mat_ed.connect_material_expressions(src, out_pin, dst, in_pin):
        raise RuntimeError(f"Failed wiring {src.get_name()}.{out_pin} -> {dst.get_name()}.{in_pin}")


def clear_material_expressions(mat):
    mat_ed.disconnect_material_property(mat, u.MaterialProperty.MP_EMISSIVE_COLOR)
    mat_ed.disconnect_material_property(mat, u.MaterialProperty.MP_WORLD_POSITION_OFFSET)
    for old_expr in list(mat_ed.get_material_expressions(mat)):
        mat_ed.delete_material_expression(mat, old_expr)
    mat_ed.delete_all_material_expressions(mat)
    remaining = list(mat_ed.get_material_expressions(mat))
    if remaining:
        raise RuntimeError(f"Expected 0 expressions after cleanup on {mat.get_path_name()}, found {len(remaining)}")


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


def inst_data(mat, idx: int, default: float, x: int, y: int):
    n = mat_ed.create_material_expression(mat, u.MaterialExpressionPerInstanceCustomData, x, y)
    n.set_editor_property("data_index", idx)
    n.set_editor_property("const_default_value", default)
    return n


def build_shared_coords(mat):
    world_pos = mat_ed.create_material_expression(mat, u.MaterialExpressionWorldPosition, -1250, -320)
    cam_pos = mat_ed.create_material_expression(mat, u.MaterialExpressionCameraPositionWS, -1250, -160)

    local_origin = mat_ed.create_material_expression(mat, u.MaterialExpressionConstant3Vector, -1500, 0)
    local_origin.set_editor_property("constant", u.LinearColor(0.0, 0.0, 0.0, 1.0))

    center_ws = mat_ed.create_material_expression(mat, u.MaterialExpressionTransformPosition, -1250, 0)
    center_ws.set_editor_property("transform_source_type", u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_INSTANCE)
    center_ws.set_editor_property("transform_type", u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_WORLD)
    wire(local_origin, "", center_ws, "")

    cam_to_center = mat_ed.create_material_expression(mat, u.MaterialExpressionSubtract, -920, -140)
    wire(center_ws, "", cam_to_center, "A")
    wire(cam_pos, "", cam_to_center, "B")

    center_offset = mat_ed.create_material_expression(mat, u.MaterialExpressionSubtract, -920, -280)
    wire(world_pos, "", center_offset, "A")
    wire(center_ws, "", center_offset, "B")

    rand_node = mat_ed.create_material_expression(mat, u.MaterialExpressionPerInstanceRandom, -1250, 720)
    time_node = mat_ed.create_material_expression(mat, u.MaterialExpressionTime, -1250, 820)
    night_param = mat_ed.create_material_expression(mat, u.MaterialExpressionScalarParameter, -1250, 920)
    night_param.set_editor_property("parameter_name", "NightIntensity")
    night_param.set_editor_property("default_value", 1.0)
    return cam_to_center, center_offset, rand_node, time_node, night_param


def validate_and_save(mat, pkg_path: str, expected_customs: int) -> dict:
    errors = mat_ed.recompile_material(mat)
    if errors:
        raise RuntimeError(f"Material compile errors on {pkg_path}: {errors}")

    customs = [e for e in mat_ed.get_material_expressions(mat) if isinstance(e, u.MaterialExpressionCustom)]
    if len(customs) != expected_customs:
        raise RuntimeError(f"Expected {expected_customs} Custom expressions on {pkg_path}, found {len(customs)}")
    for ce in customs:
        names = list(mat_ed.get_material_expression_input_names(ce))
        ins = list(mat_ed.get_inputs_for_material_expression(mat, ce))
        missing = [str(n) for n, i in zip(names, ins) if i is None]
        if missing:
            raise RuntimeError(f"Custom node {ce.get_editor_property('description')} has unwired pins: {missing}")

    if not lib.save_loaded_asset(mat, False):
        raise RuntimeError(f"Failed saving material {pkg_path}")

    st_after = mat_ed.get_statistics(mat)
    stats_after = {
        "num_pixel_shader_instructions": int(st_after.get_editor_property("num_pixel_shader_instructions")),
        "num_vertex_shader_instructions": int(st_after.get_editor_property("num_vertex_shader_instructions")),
        "num_samplers": int(st_after.get_editor_property("num_samplers")),
    }
    if stats_after["num_samplers"] > 2:
        raise RuntimeError(f"Expected <=2 samplers on {pkg_path}, got {stats_after['num_samplers']}")
    return stats_after


def build_beacon_material() -> tuple:
    mat, existed, backup_info = get_or_create_material(BEACON_PKG)
    st_before = mat_ed.get_statistics(mat) if existed else None
    stats_before = (
        {
            "num_pixel_shader_instructions": int(st_before.get_editor_property("num_pixel_shader_instructions")),
            "num_vertex_shader_instructions": int(st_before.get_editor_property("num_vertex_shader_instructions")),
            "num_samplers": int(st_before.get_editor_property("num_samplers")),
        }
        if st_before
        else None
    )

    mat.modify()
    clear_material_expressions(mat)

    mat.set_editor_property("blend_mode", u.BlendMode.BLEND_ADDITIVE)
    mat.set_editor_property("shading_model", u.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property("two_sided", True)
    mat.set_editor_property("used_with_instanced_static_meshes", True)
    mat.set_editor_property("enable_tessellation", False)

    uv = mat_ed.create_material_expression(mat, u.MaterialExpressionTextureCoordinate, -1250, -480)
    uv.set_editor_property("coordinate_index", 0)
    cam_to_center, center_offset, rand_node, time_node, night_param = build_shared_coords(mat)

    radius_cm = inst_data(mat, 0, 56.0, -1250, 160)
    strength = inst_data(mat, 1, 1.0, -1250, 260)
    warmth = inst_data(mat, 2, 0.55, -1250, 360)
    min_fade_cm = inst_data(mat, 3, 4400.0, -1250, 460)
    mode = inst_data(mat, 4, 0.0, -1250, 560)

    wpo_code = """
float2 cUV = (UV - 0.5) * 2.0;
float dist = length(CamToCenter);
float fadeIn = smoothstep(MinFadeCm * 0.85, MinFadeCm * 1.45, dist);
if (Mode > 1.5)
{
    return (fadeIn - 1.0) * CenterOffset;
}
if (Mode > 0.5)
{
    float3 fwdXY = normalize(float3(-CamToCenter.x, -CamToCenter.y, 0.0) + float3(0.0001, 0.0, 0.0));
    float3 rightXY = normalize(cross(float3(0.0, 0.0, 1.0), fwdXY));
    float halfW = RadiusCm * fadeIn;
    float halfH = RadiusCm * 0.27 * fadeIn;
    float3 targetOffset = rightXY * (cUV.x * halfW) + float3(0.0, 0.0, (-cUV.y + 0.55) * halfH);
    return targetOffset - CenterOffset;
}
float distScale = lerp(1.0, 1.55, smoothstep(6000.0, 70000.0, dist));
float r = RadiusCm * distScale * fadeIn;
float3 viewDir = CamToCenter / max(dist, 1.0);
float3 targetOffset = (ResolvedView.ViewRight * cUV.x + ResolvedView.ViewUp * (-cUV.y)) * r
    - viewDir * min(dist * 0.002, 6.0);
return targetOffset - CenterOffset;
""".strip()

    wpo_node = add_custom(
        mat,
        "R55 Distant Beacon WPO",
        -460,
        -260,
        u.CustomMaterialOutputType.CMOT_FLOAT3,
        wpo_code,
        [
            ("UV", uv, ""),
            ("CamToCenter", cam_to_center, ""),
            ("CenterOffset", center_offset, ""),
            ("RadiusCm", radius_cm, ""),
            ("MinFadeCm", min_fade_cm, ""),
            ("Mode", mode, ""),
        ],
    )

    fade_dist_node = add_custom(
        mat,
        "R55 Distant Beacon FadeDistance",
        -700,
        60,
        u.CustomMaterialOutputType.CMOT_FLOAT1,
        "return (Mode > 1.5) ? 45.0 : ((Mode > 0.5) ? 450.0 : 80.0);",
        [("Mode", mode, "")],
    )

    depth_fade = mat_ed.create_material_expression(mat, u.MaterialExpressionDepthFade, -500, 60)
    depth_fade.set_editor_property("opacity_default", 1.0)
    depth_fade.set_editor_property("fade_distance_default", 80.0)
    df_names = [str(n) for n in mat_ed.get_material_expression_input_names(depth_fade)]
    fade_pin = next((n for n in df_names if "fade" in n.lower()), "FadeDistance")
    wire(fade_dist_node, "", depth_fade, fade_pin)

    emissive_code = """
float dist = length(CamToCenter);
float nearFade = smoothstep(MinFadeCm * 0.90, MinFadeCm * 1.65, dist);
float farFade = 1.0 - smoothstep(115000.0, 148000.0, dist);
float env = NightIntensity * nearFade * farFade * DepthSoft;
if (env <= 0.0005)
{
    return float3(0.0, 0.0, 0.0);
}
if (Mode > 1.5)
{
    float rPool = saturate(length(CenterOffset) / max(RadiusCm, 1.0));
    if (rPool >= 1.0) return float3(0.0, 0.0, 0.0);
    float falloff = pow(saturate(1.0 - rPool), 2.2) * (0.94 + 0.06 * sin(Time * 2.2 + Rand * 6.28318));
    float3 poolCol = lerp(float3(1.0, 0.48, 0.14), float3(1.0, 0.72, 0.30), saturate(Warmth));
    return poolCol * (falloff * Strength * env);
}
if (Mode > 0.5)
{
    float halfH = max(RadiusCm * 0.27, 1.0);
    float hNorm = clamp((CenterOffset.z + 0.45 * halfH) / (2.0 * halfH), 0.0, 1.0);
    float xNorm = saturate(length(CenterOffset.xy) / max(RadiusCm, 1.0));
    if (xNorm >= 1.0) return float3(0.0, 0.0, 0.0);
    float arch = sqrt(saturate(1.0 - xNorm * xNorm));
    float bottomMelt = smoothstep(0.0, 0.16, hNorm);
    float topFade = pow(saturate(1.0 - max(0.0, hNorm - 0.14) / 0.86), 2.5);
    float archMask = smoothstep(0.0, 0.25, arch - hNorm * 0.82);
    float xGauss = exp(-xNorm * xNorm * 2.8);
    float dome = bottomMelt * topFade * archMask * xGauss * 0.26 * Strength;
    float3 hazeCol = lerp(float3(1.0, 0.42, 0.12), float3(1.0, 0.68, 0.28), saturate(Warmth));
    return hazeCol * (dome * env);
}
float2 p = (UV - 0.5) * 2.0;
float r = length(p);
if (r >= 1.0)
{
    return float3(0.0, 0.0, 0.0);
}
float distScale = lerp(1.0, 1.55, smoothstep(6000.0, 70000.0, dist));
float rScaled = max(RadiusCm * distScale, 1.0);
float vWorld = clamp(CenterOffset.z / rScaled, -1.0, 1.0);
float hood = lerp(1.05, 0.48, smoothstep(0.02, 0.70, vWorld));
float core = exp(-r * r * 18.0);
float halo = pow(saturate(1.0 - r), 3.2) * 0.46;
float flicker = 0.93 + 0.07 * sin(Time * 2.6 + Rand * 6.28318);
float distBoost = lerp(1.0, 1.75, smoothstep(8000.0, 75000.0, dist));
float lum = (core * 2.1 + halo) * hood * Strength * flicker * distBoost;
float3 beaconCol = lerp(float3(1.0, 0.54, 0.16), float3(1.0, 0.88, 0.54), saturate(Warmth + core * 0.32));
return beaconCol * (lum * env);
""".strip()

    emissive_node = add_custom(
        mat,
        "R55 Distant Beacon Emissive",
        -240,
        240,
        u.CustomMaterialOutputType.CMOT_FLOAT3,
        emissive_code,
        [
            ("UV", uv, ""),
            ("CamToCenter", cam_to_center, ""),
            ("CenterOffset", center_offset, ""),
            ("Time", time_node, ""),
            ("Rand", rand_node, ""),
            ("NightIntensity", night_param, ""),
            ("RadiusCm", radius_cm, ""),
            ("Strength", strength, ""),
            ("Warmth", warmth, ""),
            ("MinFadeCm", min_fade_cm, ""),
            ("Mode", mode, ""),
            ("DepthSoft", depth_fade, ""),
        ],
    )

    if not mat_ed.connect_material_property(emissive_node, "", u.MaterialProperty.MP_EMISSIVE_COLOR):
        raise RuntimeError(f"Failed connecting MP_EMISSIVE_COLOR on {BEACON_PKG}")
    if not mat_ed.connect_material_property(wpo_node, "", u.MaterialProperty.MP_WORLD_POSITION_OFFSET):
        raise RuntimeError(f"Failed connecting MP_WORLD_POSITION_OFFSET on {BEACON_PKG}")

    stats_after = validate_and_save(mat, BEACON_PKG, 3)
    disk_path = pkg_to_disk(BEACON_PKG)
    backup_info["after_sha256"] = sha256_file(disk_path) if disk_path.exists() else None
    report = {
        "package": BEACON_PKG,
        "existed_before": existed,
        "before": stats_before,
        "after": stats_after,
    }
    return report, backup_info


def build_warm_window_material() -> tuple:
    mat, existed, backup_info = get_or_create_material(WINDOW_PKG)
    st_before = mat_ed.get_statistics(mat) if existed else None
    stats_before = (
        {
            "num_pixel_shader_instructions": int(st_before.get_editor_property("num_pixel_shader_instructions")),
            "num_vertex_shader_instructions": int(st_before.get_editor_property("num_vertex_shader_instructions")),
            "num_samplers": int(st_before.get_editor_property("num_samplers")),
        }
        if st_before
        else None
    )

    mat.modify()
    clear_material_expressions(mat)

    mat.set_editor_property("blend_mode", u.BlendMode.BLEND_ADDITIVE)
    mat.set_editor_property("shading_model", u.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property("two_sided", True)
    mat.set_editor_property("used_with_instanced_static_meshes", True)
    mat.set_editor_property("enable_tessellation", False)

    cam_to_center, center_offset, rand_node, time_node, night_param = build_shared_coords(mat)
    normal_ws = mat_ed.create_material_expression(mat, u.MaterialExpressionVertexNormalWS, -1250, -60)

    shape_type = inst_data(mat, 0, 0.0, -1250, 160)
    warmth = inst_data(mat, 1, 0.62, -1250, 260)
    strength = inst_data(mat, 2, 1.25, -1250, 360)
    min_fade_cm = inst_data(mat, 3, 3200.0, -1250, 460)
    half_width_cm = inst_data(mat, 4, 48.0, -1250, 560)
    half_height_cm = inst_data(mat, 5, 56.0, -1250, 660)

    emissive_code = """
float dist = length(CamToCenter);
float nearFade = smoothstep(MinFadeCm * 0.88, MinFadeCm * 1.85, dist);
float farFade = 1.0 - smoothstep(110000.0, 145000.0, dist);
float env = NightIntensity * nearFade * farFade;
if (env <= 0.0005)
{
    return float3(0.0, 0.0, 0.0);
}
float uAbs = saturate(length(CenterOffset.xy) / max(HalfWidthCm, 1.0));
float v = clamp(CenterOffset.z / max(HalfHeightCm, 1.0), -1.0, 1.0);
float mask = 0.0;
float tracery = 1.0;
if (ShapeType > 1.5)
{
    float rad = length(float2(uAbs, v));
    mask = 1.0 - smoothstep(0.86, 0.96, rad);
    float ring = smoothstep(0.04, 0.11, abs(rad - 0.50));
    float crossBars = smoothstep(0.04, 0.10, uAbs) * smoothstep(0.04, 0.10, abs(v));
    tracery = lerp(0.28, 1.0, min(ring, crossBars));
}
else if (ShapeType > 0.5)
{
    float archHalfW = (v > 0.12) ? pow(saturate(1.0 - (v - 0.12) / 0.88), 0.72) : 1.0;
    mask = (1.0 - smoothstep(archHalfW - 0.08, archHalfW, uAbs))
        * smoothstep(-1.0, -0.90, v)
        * (1.0 - smoothstep(0.92, 1.0, v));
    float mullion = smoothstep(0.04, 0.11, uAbs);
    float leadH = smoothstep(0.025, 0.075, abs(frac((v + 1.0) * 1.5) - 0.5));
    tracery = lerp(0.30, 1.0, min(mullion, leadH));
}
else
{
    mask = (1.0 - smoothstep(0.88, 0.98, uAbs))
        * smoothstep(-0.98, -0.88, v)
        * (1.0 - smoothstep(0.88, 0.98, v));
    float mullion = smoothstep(0.03, 0.09, uAbs);
    float transom = smoothstep(0.03, 0.09, abs(v - 0.28));
    tracery = lerp(0.25, 1.0, min(mullion, transom));
}
float interiorGrad = lerp(1.18, 0.62, saturate((v + 0.5) * 0.72)) * (1.0 - 0.22 * uAbs * uAbs);
float3 viewDir = normalize(-CamToCenter);
float facing = pow(saturate(abs(dot(normalize(NormalWS), viewDir))), 0.35);
float flicker = 0.95 + 0.05 * sin(Time * 1.9 + Rand * 6.28318);
float distBoost = lerp(1.0, 1.85, smoothstep(10000.0, 75000.0, dist));
float3 warmCol = lerp(float3(1.0, 0.52, 0.15), float3(1.0, 0.82, 0.42), saturate(Warmth));
return warmCol * (Strength * mask * tracery * interiorGrad * facing * flicker * distBoost * env);
""".strip()

    emissive_node = add_custom(
        mat,
        "R55 Warm Window Emissive",
        -380,
        180,
        u.CustomMaterialOutputType.CMOT_FLOAT3,
        emissive_code,
        [
            ("CamToCenter", cam_to_center, ""),
            ("CenterOffset", center_offset, ""),
            ("NormalWS", normal_ws, ""),
            ("Time", time_node, ""),
            ("Rand", rand_node, ""),
            ("NightIntensity", night_param, ""),
            ("ShapeType", shape_type, ""),
            ("Warmth", warmth, ""),
            ("Strength", strength, ""),
            ("MinFadeCm", min_fade_cm, ""),
            ("HalfWidthCm", half_width_cm, ""),
            ("HalfHeightCm", half_height_cm, ""),
        ],
    )

    if not mat_ed.connect_material_property(emissive_node, "", u.MaterialProperty.MP_EMISSIVE_COLOR):
        raise RuntimeError(f"Failed connecting MP_EMISSIVE_COLOR on {WINDOW_PKG}")

    stats_after = validate_and_save(mat, WINDOW_PKG, 1)
    disk_path = pkg_to_disk(WINDOW_PKG)
    backup_info["after_sha256"] = sha256_file(disk_path) if disk_path.exists() else None
    report = {
        "package": WINDOW_PKG,
        "existed_before": existed,
        "before": stats_before,
        "after": stats_after,
    }
    return report, backup_info


def main():
    BATCH_DIR.mkdir(parents=True, exist_ok=True)
    BEFORE_CONTENT.mkdir(parents=True, exist_ok=True)

    beacon_rep, beacon_bk = build_beacon_material()
    window_rep, window_bk = build_warm_window_material()

    compiled = {
        "batch": "HillsPerfOpt-R55",
        "materials": [beacon_rep, window_rep],
    }
    (BATCH_DIR / "compiled.json").write_text(json.dumps(compiled, indent=2), encoding="utf-8")

    receipt = {
        "batch": "HillsPerfOpt-R55",
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "script": "Tools/WorldGeneration/ForestVillage/optimize_hills_perf_r55.py",
        "materials": [beacon_rep, window_rep],
        "backups_and_hashes": [beacon_bk, window_bk],
    }
    (BATCH_DIR / "published.json").write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8")

    u.log(
        f"[R55-DONE] beacon(ps={beacon_rep['after']['num_pixel_shader_instructions']}, "
        f"vs={beacon_rep['after']['num_vertex_shader_instructions']}, samplers={beacon_rep['after']['num_samplers']}) | "
        f"window(ps={window_rep['after']['num_pixel_shader_instructions']}, "
        f"vs={window_rep['after']['num_vertex_shader_instructions']}, samplers={window_rep['after']['num_samplers']})"
    )


if __name__ == "__main__":
    main()
