"""Hills + Cross-Map R52 GPU / VSM / VRAM optimization pass (HillsPerfOpt-R52).

Pass A:
  - Add RoadWeight scalar early-out to /Game/ForestPathStudy/VillageRegion/Reference/MF_TrailDirt
    so non-road pixels on M_ForestReferenceMesh skip ~27 MF_TrailDirt texture samples.
  - Inject distance-pruned HLSL shaders (forest_road_mix.ush, trail_soil.ush, cliff_surface.ush,
    roadside_leaves.ush, continuous_meadow.ush) and compile M_ForestReferenceMesh /
    M_ForestVillageLandscape / MI_ForestTilePacked (before/after stats in compiled.json).
Pass B:
  - Set WorldPositionOffsetDisableDistance on L_ForestPathVillage ForestVillageRegion_1 foliage &
    grass HISMs and BronzeTorch_* unculled point lights (max_draw_distance=4500, fade=600).
  - Set WorldPositionOffsetDisableDistance and AffectDynamicIndirectLighting=False on
    L_ForestPathForest PCGVolume foliage/clutter ISMs.
  - Read-only audit of TemperateHillsWorld tree PCG graph / partitioning config.
Pass C:
  - Strip bloated legacy LOD1/LOD2 on 4 Nanite foliage meshes (CommonHazel 01/02, Hornbeam 04/05).
  - Cap T_Voronoi_Perturbed_4k -> 1024 + streamable mips; inspect & cap T_Detail_Wood01a -> 2048 if safe.
"""
import datetime
import hashlib
import json
import os
import sys
import shutil
from pathlib import Path

import unreal as u

RECIPE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(RECIPE_DIR))
import author_forest_road_mix as road_mix

PROJECT_ROOT = Path("D:/FPS3D/FPSGAME")
CONTENT_ROOT = PROJECT_ROOT / "Content"
BATCH_DIR = Path(os.environ.get("FPS_HILLS_R52_BATCH", "F:/FPSGAMEData/ArtProduction/HillsForestPath/HillsPerfOpt-R52"))
BEFORE_CONTENT = BATCH_DIR / "Before" / "Content"

VILLAGE_MAP = "/Game/GameMaps/L_ForestPathVillage"
FOREST_MAP = "/Game/ForestPathStudy/VillageRegion/Reference/TrailLandscape/L_ForestPathForest"
REF_FOLDER = "/Game/ForestPathStudy/VillageRegion/Reference"

lib = u.EditorAssetLibrary
mat_ed = u.MaterialEditingLibrary
mesh_sub = u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
save_utils = u.EditorLoadingAndSavingUtils
actors_sub = u.get_editor_subsystem(u.EditorActorSubsystem)
level_sub = u.get_editor_subsystem(u.LevelEditorSubsystem)


def pkg_to_disk(pkg_path: str) -> Path:
    clean = pkg_path.split(".")[0]
    if not clean.startswith("/Game/"):
        raise ValueError(f"Expected /Game/ path: {pkg_path}")
    for ext in (".uasset", ".umap"):
        candidate = CONTENT_ROOT / (clean[6:] + ext)
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"Asset/Map missing on disk for {clean}")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


class ReceiptRecorder:
    def __init__(self):
        self.backed_up = {}

    def backup_before(self, pkg_path: str) -> dict:
        clean = pkg_path.split(".")[0]
        src = pkg_to_disk(clean)
        rel = src.relative_to(CONTENT_ROOT)
        dst = BEFORE_CONTENT / rel
        if clean not in self.backed_up:
            before_sha = sha256_file(src)
            if not dst.exists():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                for ext in (".uexp", ".ubulk", ".uptnl"):
                    side_src = src.with_suffix(ext)
                    if side_src.exists():
                        shutil.copy2(side_src, dst.with_suffix(ext))
            self.backed_up[clean] = {
                "package": clean,
                "disk_path": str(src),
                "backup_path": str(dst),
                "before_sha256": before_sha,
            }
        return self.backed_up[clean]

    def finalize_hashes(self):
        records = []
        files = sorted(list(BEFORE_CONTENT.rglob("*.uasset")) + list(BEFORE_CONTENT.rglob("*.umap")))
        for dst in files:
            rel = dst.relative_to(BEFORE_CONTENT)
            clean = "/Game/" + rel.with_suffix("").as_posix()
            src = CONTENT_ROOT / rel
            records.append({
                "package": clean,
                "disk_path": str(src),
                "backup_path": str(dst),
                "before_sha256": sha256_file(dst),
                "after_sha256": sha256_file(src) if src.exists() else None,
            })
        return records


def save_asset(obj):
    if not lib.save_loaded_asset(obj, False):
        raise RuntimeError(f"Failed to save asset: {obj.get_path_name()}")


def collect_shader_stats(paths: list[str]) -> dict:
    out = {}
    for path in paths:
        if not lib.does_asset_exist(path):
            continue
        mat = u.load_asset(path)
        if not isinstance(mat, u.MaterialInterface):
            continue
        stats = mat_ed.get_statistics(mat)
        out[mat.get_path_name()] = {
            "num_pixel_shader_instructions": int(stats.get_editor_property("num_pixel_shader_instructions")),
            "num_samplers": int(stats.get_editor_property("num_samplers")),
        }
    return out


def expr_inputs(container, expr) -> dict:
    names = list(mat_ed.get_material_expression_input_names(expr))
    nodes = list(mat_ed.get_inputs_for_material_expression(container, expr))
    return dict(zip(map(str, names), nodes))


def find_road_mask_expr(mat):
    def is_uv4_source(node) -> bool:
        if isinstance(node, u.MaterialExpressionTextureCoordinate):
            return int(node.get_editor_property("coordinate_index")) == 4
        if isinstance(node, u.MaterialExpressionStaticSwitchParameter):
            false_in = expr_inputs(mat, node).get("False")
            return isinstance(false_in, u.MaterialExpressionTextureCoordinate) and int(false_in.get_editor_property("coordinate_index")) == 4
        return False

    for expr in mat_ed.get_material_expressions(mat):
        if not isinstance(expr, u.MaterialExpressionComponentMask):
            continue
        if (
            bool(expr.get_editor_property("r"))
            and not bool(expr.get_editor_property("g"))
            and not bool(expr.get_editor_property("b"))
            and not bool(expr.get_editor_property("a"))
        ):
            ins = mat_ed.get_inputs_for_material_expression(mat, expr)
            if ins and is_uv4_source(ins[0]):
                return expr
    return None


def update_ground_cover_hlsl(mat) -> dict:
    """Update 'R26 continuous ground cover' custom HLSL (meadow + leaves + cliff) on mat if pins match."""
    nodes = list(mat_ed.get_material_expressions(mat))
    shade = next((n for n in nodes if str(n.get_editor_property("desc")) == "R26 continuous ground cover"), None)
    if not shade:
        return {"present": False, "updated": False}
    pins = {str(i.get_editor_property("input_name")) for i in shade.get_editor_property("inputs")}
    required = {"P", "F", "Bank", "Detail", "BaseN", "BladeN", "Wet", "GroundRoughness", "LeafField", "LeafColor", "LeafSurface", "CliffField", "CliffColor", "CliffNormal", "CliffData", "CliffEye"}
    if not required.issubset(pins):
        return {"present": True, "updated": False, "missing_pins": sorted(required - pins)}

    base = (RECIPE_DIR / "continuous_meadow.ush").read_text(encoding="utf-8-sig")
    if base.count("return GroundColor;") != 1:
        raise RuntimeError("Unexpected continuous_meadow.ush structure")
    leaves_code = (RECIPE_DIR / "roadside_leaves.ush").read_text(encoding="utf-8-sig")
    cliff_code = (RECIPE_DIR / "cliff_surface.ush").read_text(encoding="utf-8-sig")
    field = "float exposure=Texture2DSampleLevel(CliffField,GetMaterialSharedSampler(CliffFieldSampler,Material.Clamp_WorldGroupSettings),(P.xy*.01+float2(624.,320.))/1024.,0.).r;"
    code = base.replace("return GroundColor;", leaves_code)
    code = code.replace("float cover=saturate(F.r);", field + "\nfloat cover=saturate(F.r)*(1.-smoothstep(.69,.99,exposure));")
    code = code.replace("if(amount>.025)", "if(amount>.025 && exposure<.985)")
    code = code.replace("return GroundColor;", cliff_code)

    shade.set_editor_property("code", code)
    return {"present": True, "updated": True}


def pass_a_terrain_shaders(recorder: ReceiptRecorder) -> dict:
    stat_paths = [
        REF_FOLDER + "/M_ForestReferenceMesh",
        REF_FOLDER + "/TrailCover/M_ForestVillageLandscape",
        REF_FOLDER + "/Terrain/MI_ForestTilePacked",
    ]
    mi_packed = u.load_asset(REF_FOLDER + "/Terrain/MI_ForestTilePacked")
    packed_base = mi_packed.get_base_material() if mi_packed else None
    if packed_base and packed_base.get_path_name().split(".")[0] not in stat_paths:
        stat_paths.append(packed_base.get_path_name().split(".")[0])

    stats_before = collect_shader_stats(stat_paths)

    # 1. Update MF_TrailDirt with RoadWeight early-out + updated gate_road / trail_soil / forest_road_mix HLSL
    fn_path = REF_FOLDER + "/MF_TrailDirt"
    fn = u.load_asset(fn_path)
    if not isinstance(fn, u.MaterialFunction):
        raise RuntimeError(f"Missing MaterialFunction: {fn_path}")
    recorder.backup_before(fn_path)
    fn.modify()

    fn_nodes = list(mat_ed.get_material_function_expressions(fn))
    custom = next((n for n in fn_nodes if str(n.get_editor_property("desc")) == "R21 independent soil and moss"), None)
    if not custom:
        raise RuntimeError("Could not find 'R21 independent soil and moss' in MF_TrailDirt")

    inputs = list(custom.get_editor_property("inputs"))
    if not any(str(i.get_editor_property("input_name")) == "RoadWeight" for i in inputs):
        extra = u.CustomInput()
        extra.set_editor_property("input_name", "RoadWeight")
        inputs.append(extra)
        custom.set_editor_property("inputs", inputs)

    rw_expr = next(
        (e for e in fn_nodes if isinstance(e, u.MaterialExpressionFunctionInput) and str(e.get_editor_property("input_name")) == "RoadWeight"),
        None,
    )
    if not rw_expr:
        rw_expr = mat_ed.create_material_expression_in_function(fn, u.MaterialExpressionFunctionInput)
        rw_expr.set_editor_property("input_name", "RoadWeight")
    rw_expr.set_editor_property("input_type", u.FunctionInputType.FUNCTION_INPUT_SCALAR)
    rw_expr.set_editor_property("use_preview_value_as_default", True)

    rw_default = next(
        (e for e in fn_nodes if isinstance(e, u.MaterialExpressionConstant) and str(e.get_editor_property("desc")) == "R52 RoadWeight default 1"),
        None,
    )
    if not rw_default:
        rw_default = mat_ed.create_material_expression_in_function(fn, u.MaterialExpressionConstant)
        rw_default.set_editor_property("desc", "R52 RoadWeight default 1")
    rw_default.set_editor_property("r", 1.0)
    if not mat_ed.connect_material_expressions(rw_default, "", rw_expr, "Preview"):
        raise RuntimeError("Failed wiring RoadWeight default Constant -> rw_expr.Preview in MF_TrailDirt")

    if not mat_ed.connect_material_expressions(rw_expr, "", custom, "RoadWeight"):
        raise RuntimeError("Failed wiring RoadWeight FunctionInput -> custom.RoadWeight in MF_TrailDirt")

    original = (RECIPE_DIR / "trail_soil.ush").read_text(encoding="utf-8-sig")
    if original.count("return color;") != 1:
        raise RuntimeError("Unexpected trail_soil.ush outputs")
    blend = (
        "RoadNormal=normalize(lerp(RoadNormal,compactNormal,roadMix));\n"
        "RoadRoughness=lerp(RoadRoughness,compactData.g,roadMix);\n"
        "RoadAO=lerp(RoadAO,compactData.r,roadMix);\n"
        "RoadHeight=lerp(RoadHeight,compactData.b,roadMix);\n"
        "return lerp(color,compactColor,roadMix);"
    )
    road_guard = (
        "[branch] if(RoadWeight<=0.0005)\n"
        "{\n"
        "    RoadNormal=float3(0.,0.,1.);RoadRoughness=.85;RoadAO=1.;RoadHeight=.5;\n"
        "    return float3(0.,0.,0.);\n"
        "}\n"
    )
    combined_code = road_guard + (RECIPE_DIR / "gate_road_surface.ush").read_text(encoding="utf-8-sig") + "\n" + original.replace("return color;", blend)
    bound_code = road_mix.bind(fn, custom, combined_code)
    custom.set_editor_property("code", bound_code)
    mat_ed.update_material_function(fn)
    save_asset(fn)
    u.log(f"[R52-PASS-A] Updated & saved {fn_path}")

    # 2. Wire RoadWeight on M_ForestReferenceMesh (and base of MI_ForestTilePacked if separate) + update ground cover HLSL
    mats_to_update = [REF_FOLDER + "/M_ForestReferenceMesh", REF_FOLDER + "/TrailCover/M_ForestVillageLandscape"]
    if packed_base:
        bp = packed_base.get_path_name().split(".")[0]
        if bp not in mats_to_update:
            mats_to_update.append(bp)

    mat_reports = {}
    for mpath in mats_to_update:
        mat = u.load_asset(mpath)
        if not isinstance(mat, u.Material):
            continue
        recorder.backup_before(mpath)
        mat.modify()

        wired_calls = 0
        road_mask = find_road_mask_expr(mat)
        if road_mask:
            for expr in mat_ed.get_material_expressions(mat):
                if isinstance(expr, u.MaterialExpressionMaterialFunctionCall):
                    mf = expr.get_editor_property("material_function")
                    if mf and mf.get_path_name().split(".")[0] == fn_path:
                        cur_in = expr_inputs(mat, expr)
                        if "RoadWeight" not in cur_in:
                            previous = {
                                k: (v, str(mat_ed.get_input_node_output_name_for_material_expression(expr, v) or ""))
                                for k, v in cur_in.items() if v
                            }
                            if not expr.set_material_function(fn):
                                raise RuntimeError(f"Failed refreshing MF_TrailDirt pins on {mpath}")
                            refreshed_in = expr_inputs(mat, expr)
                            for k, (src, out_name) in previous.items():
                                if refreshed_in.get(k) != src:
                                    if not mat_ed.connect_material_expressions(src, out_name, expr, k):
                                        raise RuntimeError(f"Failed restoring pin {k} on {mpath}")
                            final_in = expr_inputs(mat, expr)
                            if any(final_in.get(k) != src for k, (src, _) in previous.items()):
                                raise RuntimeError(f"Pin restore verification failed on {mpath}: {list(final_in)}")
                        if mat_ed.connect_material_expressions(road_mask, "", expr, "RoadWeight"):
                            wired_calls += 1
                        else:
                            raise RuntimeError(f"Failed wiring road mask -> MF_TrailDirt.RoadWeight on {mpath}")
        if mpath.endswith("/M_ForestReferenceMesh") and wired_calls == 0:
            raise RuntimeError(f"Expected >=1 MF_TrailDirt RoadWeight call wired on {mpath}, got 0 (road_mask={road_mask})")

        gc_info = update_ground_cover_hlsl(mat)
        errors = mat_ed.recompile_material(mat)
        if errors:
            raise RuntimeError(f"Material compile error on {mpath}: {errors}")
        save_asset(mat)
        mat_reports[mpath] = {"wired_trail_dirt_calls": wired_calls, "ground_cover_hlsl": gc_info}
        u.log(f"[R52-PASS-A] Compiled & saved {mpath}: {json.dumps(mat_reports[mpath])}")

    stats_after = collect_shader_stats(stat_paths)
    compiled_report = {"before": stats_before, "after": stats_after, "materials": mat_reports}
    (BATCH_DIR / "compiled.json").write_text(json.dumps(compiled_report, indent=2), encoding="utf-8")
    return compiled_report


def wpo_for_mesh(mesh_name: str, pkg_path: str) -> tuple[int | None, bool]:
    """Return (wpo_disable_distance_cm, disable_dynamic_gi) for foliage/clutter meshes."""
    lo = mesh_name.lower()
    pkg_lo = pkg_path.lower()
    if "rainforestgrass" in lo:
        return 2600, True
    if "commonhazel" in lo:
        return 2200, False
    if "europeanhornbeam" in lo:
        return 3500, False
    if (
        lo.startswith(("sm_rbcuh_", "sm_rbpir_", "sm_planttype"))
        or "/roadupgrade/foliage/" in pkg_lo
    ):
        return 2200, True
    if any(k in lo for k in ("relu7", "xjiifd1", "rioqm", "xisgcic")):
        return 2400, True
    return None, False


def apply_wpo_disable(ic, wpo: int) -> None:
    ic.modify()
    ic.set_world_position_offset_disable_distance(int(wpo))
    if int(ic.get_editor_property("world_position_offset_disable_distance")) != int(wpo):
        ic.set_editor_property("world_position_offset_disable_distance", int(wpo))
    actual = int(ic.get_editor_property("world_position_offset_disable_distance"))
    if actual != int(wpo):
        raise RuntimeError(f"Failed setting WPO disable distance on {ic.get_path_name()}: expected {wpo}, got {actual}")


def pass_b_level_tuning(recorder: ReceiptRecorder) -> dict:
    # 1. L_ForestPathVillage
    recorder.backup_before(VILLAGE_MAP)
    world_v = save_utils.load_map(VILLAGE_MAP)
    if not level_sub.set_current_level_by_name("L_ForestPathVillage"):
        raise RuntimeError("Cannot select persistent level L_ForestPathVillage")

    village_wpo_tuned = 0
    village_gi_disabled = 0
    village_lights_tuned = 0
    sublevel_unculled_bronze_lights = []
    hills_pcg_audit = {}

    for actor in actors_sub.get_all_level_actors():
        ap = actor.get_path_name()
        if not ap.startswith(VILLAGE_MAP + "."):
            if "BronzeTorch" in actor.get_name():
                for pl in actor.get_components_by_class(u.PointLightComponent):
                    if float(pl.get_editor_property("max_draw_distance")) <= 0.0:
                        sublevel_unculled_bronze_lights.append(pl.get_path_name())
            continue
        if isinstance(actor, u.ForestVillageRegion):
            for ic in actor.get_components_by_class(u.InstancedStaticMeshComponent):
                sm = ic.static_mesh
                if not sm:
                    continue
                wpo, off_gi = wpo_for_mesh(sm.get_name(), sm.get_path_name())
                if wpo is not None:
                    apply_wpo_disable(ic, int(wpo))
                    village_wpo_tuned += 1
                    if off_gi and bool(ic.get_editor_property("affect_dynamic_indirect_lighting")):
                        ic.set_editor_property("affect_dynamic_indirect_lighting", False)
                        village_gi_disabled += 1
        elif "BronzeTorch" in actor.get_name():
            for pl in actor.get_components_by_class(u.PointLightComponent):
                cur_draw = float(pl.get_editor_property("max_draw_distance"))
                if cur_draw <= 0.0:
                    pl.modify()
                    pl.set_editor_property("max_draw_distance", 4500.0)
                    pl.set_editor_property("max_distance_fade_range", 600.0)
                    village_lights_tuned += 1
        elif actor.get_class().get_name() == "TemperateHillsWorld":
            try:
                assets_da = actor.get_editor_property("assets")
                if assets_da:
                    graphs = list(assets_da.get_editor_property("graphs"))
                    hills_pcg_audit = {
                        "assets_data": assets_da.get_path_name(),
                        "graph0": graphs[0].get_path_name() if graphs else None,
                        "graphs_count": len(graphs),
                    }
                pcg_info = []
                for pcg in actor.get_components_by_class(u.PCGComponent):
                    g = pcg.get_graph()
                    pcg_info.append({
                        "component": pcg.get_name(),
                        "partitioned": bool(pcg.get_editor_property("is_component_partitioned")),
                        "graph": g.get_path_name() if g else None,
                    })
                hills_pcg_audit["pcg_components"] = pcg_info
            except Exception as exc:
                hills_pcg_audit["audit_error"] = str(exc)

    if not save_utils.save_map(world_v, VILLAGE_MAP):
        raise RuntimeError(f"Failed saving {VILLAGE_MAP}")
    u.log(f"[R52-PASS-B] {VILLAGE_MAP}: wpo={village_wpo_tuned}, gi_off={village_gi_disabled}, bronze_lights={village_lights_tuned}, sublevel_bronze={len(sublevel_unculled_bronze_lights)}")

    # 2. L_ForestPathForest
    recorder.backup_before(FOREST_MAP)
    world_f = save_utils.load_map(FOREST_MAP)
    forest_wpo_tuned = 0
    forest_gi_disabled = 0
    for actor in actors_sub.get_all_level_actors():
        ap = actor.get_path_name()
        if not ap.startswith(FOREST_MAP + "."):
            continue
        if isinstance(actor, u.PCGVolume):
            for ic in actor.get_components_by_class(u.InstancedStaticMeshComponent):
                sm = ic.static_mesh
                if not sm:
                    continue
                wpo, off_gi = wpo_for_mesh(sm.get_name(), sm.get_path_name())
                if wpo is not None:
                    apply_wpo_disable(ic, int(wpo))
                    forest_wpo_tuned += 1
                    if off_gi and bool(ic.get_editor_property("affect_dynamic_indirect_lighting")):
                        ic.set_editor_property("affect_dynamic_indirect_lighting", False)
                        forest_gi_disabled += 1
    if not save_utils.save_map(world_f, FOREST_MAP):
        raise RuntimeError(f"Failed saving {FOREST_MAP}")
    u.log(f"[R52-PASS-B] {FOREST_MAP}: wpo={forest_wpo_tuned}, gi_off={forest_gi_disabled}")

    return {
        "village_map": {
            "path": VILLAGE_MAP,
            "wpo_tuned_components": village_wpo_tuned,
            "gi_disabled_components": village_gi_disabled,
            "bronze_torch_lights_capped": village_lights_tuned,
            "sublevel_unculled_bronze_lights": sublevel_unculled_bronze_lights,
        },
        "forest_map": {
            "path": FOREST_MAP,
            "wpo_tuned_components": forest_wpo_tuned,
            "gi_disabled_components": forest_gi_disabled,
        },
        "temperate_hills_pcg_audit": hills_pcg_audit,
    }


NANITE_TREES = [
    "/Game/CommonHazel/Geometry/SimpleWind/SM_CommonHazel_Forest_01",
    "/Game/CommonHazel/Geometry/SimpleWind/SM_CommonHazel_Forest_02",
    "/Game/EuropeanHornbeam/Geometry/SimpleWind/SM_EuropeanHornbeam_Forest_04",
    "/Game/EuropeanHornbeam/Geometry/SimpleWind/SM_EuropeanHornbeam_Forest_05",
]


def reset_mesh_min_lod_zero(mesh) -> dict:
    # Note: MinLOD (FPerPlatformInt) is UPROPERTY() without Blueprint/EditAnywhere access in UE Python;
    # on a 1-LOD mesh UStaticMesh::PostLoad() clamps MinLOD.Default to 0 in memory before saving,
    # while platform/quality overrides & LODForCollision are explicitly reset here.
    mesh.set_minimum_lod_for_platforms({})
    mesh.set_min_lod_for_quality_levels({}, 0)
    lfc = int(mesh.get_editor_property("lod_for_collision"))
    if lfc > 0:
        mesh.set_editor_property("lod_for_collision", 0)

    after_plat = dict(mesh.get_minimum_lod_for_platforms())
    q_map, q_def = mesh.get_min_lod_for_quality_levels()
    lfc_after = int(mesh.get_editor_property("lod_for_collision"))
    if len(after_plat) != 0 or int(q_def) != 0 or lfc_after > 0:
        raise RuntimeError(
            f"MinLOD reset verification failed on {mesh.get_path_name()}: "
            f"per_platform={after_plat}, q_def={q_def}, lod_for_collision={lfc_after}"
        )
    return {
        "per_platform": {str(k): int(v) for k, v in after_plat.items()},
        "quality_default": int(q_def),
        "quality_map": {str(k): int(v) for k, v in dict(q_map).items()},
        "lod_for_collision": lfc_after,
    }


def pass_c_vram_cleanup(recorder: ReceiptRecorder) -> dict:
    # 1. Strip redundant bloated legacy LOD1/LOD2 from 4 Nanite foliage StaticMeshes
    mesh_reports = []
    for mpath in NANITE_TREES:
        if not lib.does_asset_exist(mpath):
            mesh_reports.append({"package": mpath, "exists": False})
            continue
        mesh = u.load_asset(mpath)
        ns = mesh.get_editor_property("nanite_settings")
        nanite_on = bool(ns.get_editor_property("enabled"))
        before_lods = int(mesh.get_num_lods())
        before_tris = [int(mesh.get_num_triangles(i)) for i in range(before_lods)]
        changed = False
        min_lod_state = None
        if nanite_on and before_lods > 1:
            recorder.backup_before(mpath)
            mesh.modify()
            ok = bool(mesh_sub.remove_lods(mesh))
            ns_after = mesh.get_editor_property("nanite_settings")
            if not ok or not bool(ns_after.get_editor_property("enabled")) or int(mesh.get_num_lods()) != 1:
                raise RuntimeError(f"RemoveLods validation failed on {mpath}: ok={ok}, nanite={ns_after.get_editor_property('enabled')}, lods={mesh.get_num_lods()}")
            min_lod_state = reset_mesh_min_lod_zero(mesh)
            save_asset(mesh)
            changed = True
        mesh_reports.append({
            "package": mpath,
            "exists": True,
            "nanite_enabled": nanite_on,
            "before_lods": before_lods,
            "before_tris": before_tris,
            "after_lods": int(mesh.get_num_lods()),
            "min_lod_state": min_lod_state,
            "changed": changed,
        })
        u.log(f"[R52-PASS-C] Mesh {mpath}: tris={before_tris} lods={before_lods}->{mesh.get_num_lods()} nanite={nanite_on} changed={changed}")

    # 2. Textures: T_Voronoi_Perturbed_4k -> 1024 + streamable mips; T_Detail_Wood01a -> inspect & 2048 if safe
    tex_reports = []
    for tpath, target_max in [
        ("/Game/Landscape/Textures/T_Voronoi_Perturbed_4k", 1024),
        ("/Game/UndergroundTunnel/Textures/Wood/T_Detail_Wood01a", 2048),
    ]:
        if not lib.does_asset_exist(tpath):
            tex_reports.append({"package": tpath, "exists": False})
            continue
        tex = u.load_asset(tpath)
        if not isinstance(tex, u.Texture2D):
            tex_reports.append({"package": tpath, "exists": True, "skipped": "not_texture2d"})
            continue
        sx, sy = int(tex.blueprint_get_size_x()), int(tex.blueprint_get_size_y())
        cur_max = int(tex.get_editor_property("max_texture_size"))
        cur_ns = bool(tex.get_editor_property("never_stream"))
        cur_mip = tex.get_editor_property("mip_gen_settings")
        cur_comp = tex.get_editor_property("compression_settings")

        need_cap = cur_max == 0 or cur_max > target_max
        need_ns = cur_ns
        need_mip = cur_mip == u.TextureMipGenSettings.TMGS_NO_MIPMAPS
        safe_comp = cur_comp not in (
            u.TextureCompressionSettings.TC_VECTOR_DISPLACEMENTMAP,
            u.TextureCompressionSettings.TC_HDR,
            u.TextureCompressionSettings.TC_HDR_F32,
        )
        changed = False
        if safe_comp and (need_cap or need_ns or need_mip):
            recorder.backup_before(tpath)
            tex.modify()
            if need_cap:
                tex.set_editor_property("max_texture_size", target_max)
            if need_ns:
                tex.set_editor_property("never_stream", False)
            if need_mip:
                tex.set_editor_property("mip_gen_settings", u.TextureMipGenSettings.TMGS_SIMPLE_AVERAGE)
            save_asset(tex)
            changed = True
        tex_reports.append({
            "package": tpath,
            "exists": True,
            "size": [sx, sy],
            "compression": str(cur_comp),
            "safe_comp": safe_comp,
            "before": {"max_texture_size": cur_max, "never_stream": cur_ns, "mip_gen": str(cur_mip)},
            "after": {
                "max_texture_size": int(tex.get_editor_property("max_texture_size")),
                "never_stream": bool(tex.get_editor_property("never_stream")),
                "mip_gen": str(tex.get_editor_property("mip_gen_settings")),
            },
            "changed": changed,
        })
        u.log(f"[R52-PASS-C] Tex {tpath} ({sx}x{sy}) max:{cur_max}->{tex.get_editor_property('max_texture_size')} ns:{cur_ns}->{tex.get_editor_property('never_stream')} changed={changed}")

    return {"meshes": mesh_reports, "textures": tex_reports}


def fix_tree_min_lod_only(recorder: ReceiptRecorder):
    receipt_path = BATCH_DIR / "published.json"
    if not receipt_path.exists():
        raise RuntimeError(f"Expected existing receipt at {receipt_path}")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))

    fix_reports = []
    for mpath in NANITE_TREES:
        mesh = u.load_asset(mpath)
        ns = mesh.get_editor_property("nanite_settings")
        nanite_on = bool(ns.get_editor_property("enabled"))
        lods = int(mesh.get_num_lods())
        if not nanite_on or lods != 1:
            raise RuntimeError(f"Unexpected tree mesh state on {mpath}: nanite={nanite_on}, lods={lods}")
        recorder.backup_before(mpath)
        mesh.modify()
        state = reset_mesh_min_lod_zero(mesh)
        save_asset(mesh)
        fix_reports.append({
            "package": mpath,
            "nanite_enabled": nanite_on,
            "lods": lods,
            "min_lod_state": state,
        })
        u.log(f"[R52-MINLOD-FIX] {mpath}: lods={lods} nanite={nanite_on} state={json.dumps(state)}")

    receipt["tree_min_lod_fix"] = {
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "meshes": fix_reports,
    }
    receipt["backups_and_hashes"] = recorder.finalize_hashes()
    receipt["modified_asset_count"] = len(receipt["backups_and_hashes"])
    receipt_path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8")
    u.log(f"[R52-MINLOD-DONE] fixed={len(fix_reports)} receipt={receipt_path}")


def main():
    BATCH_DIR.mkdir(parents=True, exist_ok=True)
    BEFORE_CONTENT.mkdir(parents=True, exist_ok=True)
    recorder = ReceiptRecorder()

    if os.environ.get("FPS_R52_ONLY_TREE_MIN_LOD") == "1":
        fix_tree_min_lod_only(recorder)
        return

    pass_a = pass_a_terrain_shaders(recorder)
    pass_b = pass_b_level_tuning(recorder)
    pass_c = pass_c_vram_cleanup(recorder)
    backups = recorder.finalize_hashes()

    receipt = {
        "batch": "HillsPerfOpt-R52",
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "script": "Tools/WorldGeneration/ForestVillage/optimize_hills_perf_r52.py",
        "pass_a_terrain_shaders": pass_a,
        "pass_b_level_tuning": pass_b,
        "pass_c_vram_cleanup": pass_c,
        "modified_asset_count": len(backups),
        "backups_and_hashes": backups,
    }
    receipt_path = BATCH_DIR / "published.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8")
    u.log(f"[R52-DONE] modified={len(backups)} receipt={receipt_path}")


if __name__ == "__main__":
    main()
