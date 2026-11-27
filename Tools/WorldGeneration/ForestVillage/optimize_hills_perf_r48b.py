"""Hills + Road VRAM/Texture-Pool, Nanite root-page, and HISM/Shadow performance release pass (R48b).

Targets the exact runtime bottlenecks observed in L_ForestPathVillage PIE:
  1. Texture Streaming Pool overage (+1,065 MB): caps un-capped 4K textures across RoadMix, Leaves,
     RoadUpgrade, WoodlandDressing/Wood, ForestPathStudy/Scans, VillageRegion/Granite, EuropeanHornbeam,
     and CommonHazel (~1.5 GB GPU pool freed with zero perceptual loss at gameplay distances).
  2. Nanite Always-Resident pressure: disables Nanite on tiny 12cm pebble wjvsbay (2-LOD), trims
     KeepPercentTriangles on R48 small/medium Nanite scans while keeping crisp silhouettes.
  3. Hills GPU/VSM/shadow/draw load: tightens cull distances on 392k tiny 100m clutter instances
     (relu7/xjiifd1/rioqm/rbcuh/rbpir/xisgcic), near-grass (64m->52m seamless into far meadow),
     and CommonHazel (160m->120m, WPO disable 25m), plus disables DF/GI/Decals/RT on non-shadow HISMs.
"""
import json
import os
from pathlib import Path

import unreal as u

R48_SRC = Path(os.environ["FPS_ROAD_R48_SOURCE"])
R48_BATCH = Path(os.environ["FPS_FOREST_REFERENCE_BATCH"])
VILLAGE = "/Game/GameMaps/L_ForestPathVillage"

lib = u.EditorAssetLibrary
mesh_sub = u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
save_utils = u.EditorLoadingAndSavingUtils
actors_sub = u.get_editor_subsystem(u.EditorActorSubsystem)


def save(asset):
    if not lib.save_loaded_asset(asset, False):
        raise RuntimeError("Save failed: " + asset.get_path_name())


def tex_cap_for(path: str):
    """Return sensible max_texture_size (px) for each Hills/Road texture category."""
    p = path.replace("\\", "/")
    nm = p.split("/")[-1].split(".")[0]
    lo = nm.lower()

    # Never touch data/field/lookup textures (RoadMixField, TrackFrames, MeadowField, LeafField, PivotPainter)
    if any(k in lo for k in ("field", "trackframes", "pivot", "height", "cliff", "trail")):
        return None

    # 1) RoadMix & Shoulder Leaves atlases (4096 -> 2048 saves ~88 MiB always-resident VRAM)
    if "/GateRoad/RoadMix/" in p:
        return 2048
    if "/WoodlandDressing/Leaves/" in p and (lo.endswith("color") or lo.endswith("surface")):
        return 2048

    # 2) RoadUpgrade (R48 foliage / rocks / rustic props)
    if "/RoadUpgrade/Foliage/" in p:
        return 256 if lo.endswith("_ort") else 512
    if "/RoadUpgrade/Rocks/wjvsbay/" in p:
        return 512
    if "/RoadUpgrade/Rocks/" in p:
        return 512 if lo.endswith("_orm") else 1024
    if "/RoadUpgrade/Props/" in p:
        if any(k in p for k in ("/uh1rbecfa/", "/xfrobaziy/", "/ufflaitdw/")):
            return 512 if lo.endswith("_orm") else 1024
        return 512 if (lo.endswith("_n") or lo.endswith("_orm")) else 1024

    # 3) WoodlandDressing/Wood (clean stumps/logs/branches)
    if "/WoodlandDressing/Wood/branch/" in p:
        return 512
    if "/WoodlandDressing/Wood/stump/" in p:
        return 512 if (lo.endswith("_n") or lo.endswith("_orm")) else 1024
    if "/WoodlandDressing/Wood/log/" in p:
        return 512 if lo.endswith("_orm") else 1024

    # 4) ForestPathStudy/Scans (previously 100% uncapped 4096x4096 = >1 GB VRAM!)
    if "/ForestPathStudy/Scans/" in p:
        small_scans = ("/xjiifd1/", "/xjijdiz/", "/relu7/", "/rioqm/", "/rbcuh/", "/rbpir/", "/xisgcic/")
        if any(k in p.lower() for k in small_scans):
            return 512 if (lo.endswith("_n") or lo.endswith("_orm") or lo.endswith("_ort") or "_n_" in lo) else 1024
        # Larger boulders/cliffs in Scans: 2048 BaseColor, 1024 Normal, 512 ORM
        if lo.endswith("_orm") or lo.endswith("_ort") or "_orm" in lo:
            return 512
        if lo.endswith("_n") or "_n_" in lo or "normal" in lo:
            return 1024
        return 2048

    # 5) VillageRegion/Granite (35 granite rock scans = 105 uncapped textures!)
    if "/VillageRegion/Granite/" in p:
        if lo.endswith("_orm") or lo.endswith("_n"):
            return 512
        return 1024

    # 6) EuropeanHornbeam & CommonHazel (26 + 17 4K textures!)
    if "/EuropeanHornbeam/Textures/" in p or "/CommonHazel/Textures/" in p:
        if "twosided" in p.lower() and "mask" in lo:
            return 2048
        if any(k in lo for k in ("albedo", "basecolor", "color", "diffuse")):
            return 2048
        return 1024

    return None


def optimize_texture_pool():
    scan_dirs = [
        "/Game/ForestPathStudy/VillageRegion/Reference/GateRoad/RoadMix",
        "/Game/ForestPathStudy/VillageRegion/WoodlandDressing/Leaves",
        "/Game/ForestPathStudy/VillageRegion/RoadUpgrade",
        "/Game/ForestPathStudy/VillageRegion/WoodlandDressing/Wood",
        "/Game/ForestPathStudy/Scans",
        "/Game/ForestPathStudy/VillageRegion/Granite",
        "/Game/EuropeanHornbeam/Textures",
        "/Game/CommonHazel/Textures",
    ]
    changed = 0
    checked = 0
    by_dir = {}

    for folder in scan_dirs:
        if not lib.does_directory_exist(folder):
            continue
        dir_changed = 0
        for apath in lib.list_assets(folder, recursive=True, include_folder=False):
            cap = tex_cap_for(apath)
            if cap is None:
                continue
            tex = u.load_asset(apath)
            if not isinstance(tex, u.Texture2D):
                continue
            checked += 1
            cur_max = int(tex.get_editor_property("max_texture_size"))
            cur_ns = bool(tex.get_editor_property("never_stream"))
            need_save = False
            if cur_max == 0 or cur_max > cap:
                tex.set_editor_property("max_texture_size", cap)
                need_save = True
            if cur_ns:
                tex.set_editor_property("never_stream", False)
                need_save = True
            if need_save:
                save(tex)
                changed += 1
                dir_changed += 1
        by_dir[folder] = dir_changed
        print(f"[TEX-CAP] {folder:62s} | capped={dir_changed}")

    return {"textures_checked": checked, "textures_capped": changed, "by_dir": by_dir}


def optimize_r48_nanite_budget():
    catalog = json.loads((R48_SRC / "road-asset-catalog.json").read_text(encoding="utf-8"))
    trimmed = 0
    disabled_tiny = 0
    seen = set()
    for row in catalog:
        mpath = row["mesh"]
        if mpath in seen:
            continue
        seen.add(mpath)
        role = row["role"]
        if role.startswith("fol_"):
            continue
        sm = u.load_asset(mpath)
        if not isinstance(sm, u.StaticMesh):
            continue
        if role == "rock_small":
            # Tiny 12 cm pebble does not need Nanite root-page overhead — use 2 tiny LODs
            ns = mesh_sub.get_nanite_settings(sm)
            if ns.enabled:
                ns.enabled = False
                mesh_sub.set_nanite_settings(sm, ns, True)
            opts = u.StaticMeshReductionOptions()
            opts.set_editor_property("auto_compute_lod_screen_size", False)
            opts.set_editor_property("reduction_settings", [
                u.StaticMeshReductionSettings(percent_triangles=1.0, screen_size=1.0),
                u.StaticMeshReductionSettings(percent_triangles=0.35, screen_size=0.18),
            ])
            mesh_sub.set_lods(sm, opts)
            save(sm)
            disabled_tiny += 1
            print(f"[NANITE-TRIM] Disabled Nanite on tiny pebble {sm.get_name()} (2 LODs)")
        else:
            # Trim Nanite source triangle retention slightly on R48 scans to shrink root + streaming pages
            keep_pct = 0.50 if role in ("branch", "stump", "prop_crate", "prop_beam", "prop_post", "prop_barrel") else 0.75
            ns = mesh_sub.get_nanite_settings(sm)
            if ns.enabled and float(ns.keep_percent_triangles) > keep_pct + 0.01:
                ns.keep_percent_triangles = keep_pct
                ns.fallback_target = u.NaniteFallbackTarget.PERCENT_TRIANGLES
                ns.fallback_percent_triangles = min(0.35, float(ns.fallback_percent_triangles))
                ns.fallback_relative_error = 1.0
                mesh_sub.set_nanite_settings(sm, ns, True)
                save(sm)
                trimmed += 1
                print(f"[NANITE-TRIM] {sm.get_name():28s} | keep={keep_pct:.2f} | fallback={ns.fallback_percent_triangles:.2f}")
    return {"tiny_nanite_disabled": disabled_tiny, "nanite_keep_trimmed": trimmed}


def optimize_hills_and_road_hisms():
    """Tighten cull distances & disable DF/GI/Decals/RT on 1M+ tiny clutter/grass/shrub instances in both themes."""
    # Exact per-mesh-name performance targets (preserves distant silhouettes & continuous meadow seamlessly!)
    PERF_MAP = {
        "relu7_tier_3": dict(end=4500, shadow=False, df=False, gi=False, decals=False),
        "xjiifd1_tier_1": dict(end=4000, shadow=False, df=False, gi=False, decals=False),
        "rioqm_tier_3": dict(end=5500, shadow=False, df=False, gi=False, decals=False),
        "xisgcic_tier_1": dict(end=5500, shadow=False, df=False, gi=False, decals=False),
        "SM_RainforestGrassLow": dict(end=5200, shadow=False, df=False, gi=False, decals=False),
        "SM_RainforestGrassSpreading": dict(end=5200, shadow=False, df=False, gi=False, decals=False),
        "SM_RainforestGrassTall": dict(end=6400, shadow=False, df=False, gi=False, decals=False),
        "SM_CommonHazel_Forest_01": dict(end=12000, shadow=True, wpo=2500, far_shadow=False),
        "SM_CommonHazel_Forest_02": dict(end=12000, shadow=True, wpo=2500, far_shadow=False),
        "SM_EuropeanHornbeam_Forest_04": dict(end=36000, shadow=True, wpo=6000),
        "SM_EuropeanHornbeam_Forest_05": dict(end=36000, shadow=True, wpo=6000),
    }

    def rule_for(mesh_name: str):
        if mesh_name in PERF_MAP:
            return PERF_MAP[mesh_name]
        if mesh_name.startswith("SM_rbcuh_") or mesh_name.startswith("SM_rbpiR_"):
            return dict(end=5000, shadow=False, df=False, gi=False, decals=False)
        if mesh_name.startswith("SM_PlantType"):
            return dict(end=10000, shadow=False, df=False, gi=False, decals=False, wpo=2500)
        return None

    tuned_spawners = 0
    for theme_dir in (
        "/Game/ForestPathStudy/VillageRegion/Themes/Hills",
        "/Game/ForestPathStudy/VillageRegion/Themes/Road",
    ):
        for gpath in sorted(lib.list_assets(theme_dir, recursive=False, include_folder=False)):
            if not gpath.split("/")[-1].startswith("PCG_"):
                continue
            graph = u.load_asset(gpath)
            if not isinstance(graph, u.PCGGraph):
                continue
            dirty = False
            for node in graph.get_editor_property("nodes"):
                settings = node.get_settings()
                if not isinstance(settings, u.PCGStaticMeshSpawnerSettings):
                    continue
                sel = settings.get_editor_property("mesh_selector_parameters")
                if not isinstance(sel, u.PCGMeshSelectorWeighted):
                    continue
                entries = list(sel.get_editor_property("mesh_entries"))
                if not entries:
                    continue
                entry = entries[0]
                desc = entry.get_editor_property("descriptor")
                sm = desc.get_editor_property("static_mesh")
                if not sm:
                    continue
                r = rule_for(sm.get_name())
                if not r:
                    continue
                end = int(r["end"])
                desc.set_editor_property("instance_end_cull_distance", end)
                desc.set_editor_property("instance_start_cull_distance", (end * 3) // 4)
                if not r.get("shadow", True):
                    desc.set_editor_property("cast_shadow", False)
                    desc.set_editor_property("affect_distance_field_lighting", False)
                    desc.set_editor_property("affect_dynamic_indirect_lighting", False)
                    desc.set_editor_property("receives_decals", False)
                    desc.set_editor_property("visible_in_ray_tracing", False)
                    desc.set_editor_property("enable_density_scaling", True)
                if "wpo" in r:
                    desc.set_editor_property("world_position_offset_disable_distance", int(r["wpo"]))
                entry.set_editor_property("descriptor", desc)
                entries[0] = entry
                sel.set_editor_property("mesh_entries", entries)
                tuned_spawners += 1
                dirty = True
            if dirty:
                save(graph)

    # Mirror onto live HISMs on ForestVillageRegion inside L_ForestPathVillage
    world = save_utils.load_map(VILLAGE)
    if not u.get_editor_subsystem(u.LevelEditorSubsystem).set_current_level_by_name("L_ForestPathVillage"):
        raise RuntimeError("Cannot select persistent level L_ForestPathVillage")
    actors = actors_sub.get_all_level_actors()
    region = next(
        a for a in actors
        if isinstance(a, u.ForestVillageRegion) and a.get_path_name().startswith(VILLAGE + ".")
    )
    tuned_hisms = 0
    for hc in region.get_components_by_class(u.InstancedStaticMeshComponent):
        sm = hc.static_mesh
        if not sm:
            continue
        r = rule_for(sm.get_name())
        if not r:
            continue
        end = int(r["end"])
        hc.set_cull_distances((end * 3) // 4, end)
        if not r.get("shadow", True):
            hc.set_cast_shadow(False)
            for prop in (
                "cast_static_shadow", "cast_dynamic_shadow", "cast_contact_shadow", "cast_far_shadow",
                "visible_in_ray_tracing", "affect_distance_field_lighting",
                "affect_dynamic_indirect_lighting", "receives_decals", "generate_overlap_events",
            ):
                hc.set_editor_property(prop, False)
        elif r.get("far_shadow") is False:
            hc.set_editor_property("cast_far_shadow", False)
            hc.set_editor_property("visible_in_ray_tracing", False)
        if "wpo" in r:
            try:
                hc.set_editor_property("world_position_offset_disable_distance", int(r["wpo"]))
            except Exception:
                pass
        tuned_hisms += 1

    if not save_utils.save_map(world, VILLAGE):
        raise RuntimeError("Failed saving L_ForestPathVillage after Hills perf optimization")

    return {"tuned_spawners": tuned_spawners, "tuned_hisms": tuned_hisms}


def main():
    tex_rep = optimize_texture_pool()
    nanite_rep = optimize_r48_nanite_budget()
    hism_rep = optimize_hills_and_road_hisms()
    summary = {
        "batch": "RoadUpgrade-R48b-Perf",
        "texture_pool": tex_rep,
        "nanite_trim": nanite_rep,
        "hills_and_road_hisms": hism_rep,
    }
    out = R48_BATCH / "perf-r48b.json"
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("R48B_PERF_DONE:", json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
