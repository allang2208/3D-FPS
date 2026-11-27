"""Master UE 5.8 headless authoring script for LumberMill-R49 (isolated Stage host).

End-to-end execution:
  1. Import all 8 Blender 3-room Lumber Mill architecture/hero FBXs + 23 Quixel 3D lumber props +
     style-tuned woodchip mulch material (full Nanite + KBoxElem simple collision + <=1024/512 caps).
  2. Update expanded 3-road + yard RoadWearField / RoadMixField / TrackFrames / ShoulderLeafField /
     ContinuousMeadowField textures and recompile MF_TrailDirt + terrain materials.
  3. Apply Landscape edit layer "Lumber mill road & yard" (height + C_LayerInfo paint) on
     L_ForestPathForest, rebuild Landscape Nanite, export exact Y=+252m seam reference.f32, and
     prune/re-seat overlapping L_ForestPathForest PCGVolume instances (zero floating/clipping trees!).
  4. Re-bake L_ForestPathVillage outer terrain tiles, BakeMapRoads (M-key world map!), near grass,
     meadow grass, pruned HillsLandscape, and 3-road RoadLandscape (with R48b physical grounding refit).
  5. Assemble the complete 3-room Lumber Mill complex (Warehouse, Tool Room + Sawing Canopy,
     2-Story Walkable Bunkhouse) + richly dressed yard & interiors inside ONE HISM-optimized
     LumberMill_Compound actor with strict cull distances, shadow budgets, and warm practical lanterns.
  6. Run R48b texture/Nanite/HISM performance pass and automated grounding/overlap/VRAM audit!
"""
import json
import math
import os
import struct
import sys
from collections import defaultdict
from pathlib import Path

import unreal as u

TOOLS = Path("D:/FPS3D/FPSGAME/Tools/WorldGeneration/ForestVillage")
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(TOOLS.parent / "VillageStable"))
sys.path.insert(0, str(TOOLS.parent / "AbandonedVillage"))

import author_forest_road_mix as road_mix
import author_road_upgrade_r48 as r48_auth
import author_roadside_leaves as leaves_mod
import author_trail_cover_level as level
import author_trail_cover_materials as art
import import_lumber_mill_r49 as lm_import
import landscape_themes as themes
import optimize_hills_perf_r48b as perf_opt
import stable_lighting as shop_lights
from shop_staff_light import WICK as SHOP_WICK_MAT

R48_SRC = Path(os.environ.get("FPS_ROAD_R48_SOURCE", "F:/FPSGAMEData/ArtProduction/SourceAssets/WorldGeneration/HillsForestPath/RoadUpgrade-R48"))
R49_SRC = Path(os.environ["FPS_LUMBER_R49_SOURCE"])
R49_BATCH = Path(os.environ["FPS_FOREST_REFERENCE_BATCH"])

lib = u.EditorAssetLibrary
ed = u.MaterialEditingLibrary
save_utils = u.EditorLoadingAndSavingUtils
actors_sub = u.get_editor_subsystem(u.EditorActorSubsystem)

# Yard origin in world cm: Center (154.0 m, 62.0 m), Datum Z = +11.00 m
YARD_CX_CM = 15400.0
YARD_CY_CM = 6200.0
YARD_Z_CM = 1100.0
YARD_HX_M = 17.5
YARD_HY_M = 13.5
YARD_CR_M = 7.2


def yard_sdf_m(xm: float, ym: float) -> float:
    qx = abs(xm - 154.0) - (YARD_HX_M - YARD_CR_M)
    qy = abs(ym - 62.0) - (YARD_HY_M - YARD_CR_M)
    return math.hypot(max(qx, 0.0), max(qy, 0.0)) + min(max(qx, qy), 0.0) - YARD_CR_M


def load_lumber_road_xy_m(csv_path: Path):
    pts = []
    for line in csv_path.read_text(encoding="utf-8").splitlines()[1:]:
        parts = line.strip().split(",")
        if len(parts) >= 2:
            pts.append((float(parts[0]), float(parts[1])))
    return pts


def min_dist_to_polyline(xm: float, ym: float, pts):
    best2 = 1e18
    for px, py in pts:
        d2 = (xm - px) ** 2 + (ym - py) ** 2
        if d2 < best2:
            best2 = d2
    return math.sqrt(best2)


def build_ground_sampler(region_i16_path: Path):
    """Exact mirror of AForestVillageRegion::GroundHeight(X, Y) in cm."""
    heights = struct.unpack("<" + str(1025 * 1025) + "h", region_i16_path.read_bytes())

    def gz_cm(x_cm: float, y_cm: float) -> float:
        gx = max(0.0, min(1024.0, x_cm * 0.01 + 624.0))
        gy = max(0.0, min(1024.0, y_cm * 0.01 + 320.0))
        i0 = max(0, min(1023, int(math.floor(gx))))
        j0 = max(0, min(1023, int(math.floor(gy))))
        i = i0 if (-252 <= (i0 - 624) < 252) else (i0 & ~1)
        j = j0 if (-252 <= (j0 - 320) < 612) else (j0 & ~1)
        k = i + (1 if (-252 <= (i - 624) < 252) else 2)
        l = j + (1 if (-252 <= (j - 320) < 612) else 2)
        uf = (gx - i) / (k - i)
        vf = (gy - j) / (l - j)
        a = heights[j * 1025 + i]
        d = heights[l * 1025 + k]
        if uf >= vf:
            return float(a * (1.0 - uf) + heights[j * 1025 + k] * (uf - vf) + d * vf)
        return float(a * (1.0 - vf) + heights[l * 1025 + i] * (vf - uf) + d * uf)

    return gz_cm


def update_landscape_and_study_pcg(ter_dir: Path):
    """Apply Landscape edit layer + C_LayerInfo paint on L_ForestPathForest, rebuild Nanite,
    export updated reference.f32, and cleanly prune/re-seat overlapping study PCGVolume instances!
    """
    copy_map = level.copy
    world = save_utils.load_map(copy_map)
    if not world:
        raise RuntimeError("Could not load L_ForestPathForest copy: " + copy_map)

    all_actors = level.actor_list()
    landscape = next(
        a for a in all_actors
        if isinstance(a, u.Landscape) and a.get_path_name().startswith(copy_map + ".")
    )
    delta_file = str(ter_dir / "lumber-landscape-delta.i16")
    paint_file = str(ter_dir / "lumber-landscape-paint.u8")
    if not u.ForestVillageRegion.write_lumber_landscape_layer(landscape, delta_file, paint_file):
        raise RuntimeError("WriteLumberLandscapeLayer failed on L_ForestPathForest")

    # Export exact post-layer Landscape surface so outer tiles meet Y=+252m with 0.00 cm step!
    if not u.ForestVillageRegion.export_forest_surface(landscape, str(ter_dir / "reference.f32")):
        raise RuntimeError("ExportForestSurface failed after Lumber Landscape edit")

    # Prune overlapping L_ForestPathForest PCGVolume instances inside lumber road & yard,
    # and re-seat surviving instances on the graded cut/fill slopes!
    road_pts = load_lumber_road_xy_m(ter_dir / "lumber-road.csv")
    ls_delta = struct.unpack("<" + str(505 * 505) + "h", (ter_dir / "lumber-landscape-delta.i16").read_bytes())

    def delta_at_cm(x_cm: float, y_cm: float) -> float:
        fx = max(0.0, min(504.0, x_cm * 0.01 + 252.0))
        fy = max(0.0, min(504.0, y_cm * 0.01 + 252.0))
        i0, j0 = min(503, int(math.floor(fx))), min(503, int(math.floor(fy)))
        ux, uy = fx - i0, fy - j0
        d00 = ls_delta[j0 * 505 + i0]
        d10 = ls_delta[j0 * 505 + i0 + 1]
        d01 = ls_delta[(j0 + 1) * 505 + i0]
        d11 = ls_delta[(j0 + 1) * 505 + i0 + 1]
        return float((d00 * (1.0 - ux) + d10 * ux) * (1.0 - uy) + (d01 * (1.0 - ux) + d11 * ux) * uy)

    pruned_total = 0
    reseated_total = 0
    vol_report = {}
    for a in all_actors:
        if not isinstance(a, u.PCGVolume) or not a.get_path_name().startswith(copy_map + "."):
            continue
        lbl = a.get_actor_label()
        is_canopy = ("Canopy" in lbl or "Hazel" in lbl)
        road_clear = 4.2 if is_canopy else 3.1
        yard_clear = 5.2 if is_canopy else 3.2
        v_pruned = 0
        v_reseated = 0
        for comp in a.get_components_by_class(u.InstancedStaticMeshComponent):
            n = comp.get_instance_count()
            if n == 0:
                continue
            kept = []
            changed = False
            for idx in range(n):
                tf = comp.get_instance_transform(idx, world_space=True)
                xm, ym = float(tf.translation.x) * 0.01, float(tf.translation.y) * 0.01
                # Quick AABB filter around our logging corridor & yard X in [80..195], Y in [20..255]
                if 78.0 <= xm <= 202.0 and 18.0 <= ym <= 255.0:
                    ysdf = yard_sdf_m(xm, ym)
                    rd = min_dist_to_polyline(xm, ym, road_pts)
                    if ysdf <= yard_clear or rd <= road_clear:
                        v_pruned += 1
                        changed = True
                        continue
                    dz = delta_at_cm(float(tf.translation.x), float(tf.translation.y))
                    if abs(dz) > 0.5:
                        loc = tf.translation
                        rot_r = tf.rotation.rotator() if isinstance(tf.rotation, u.Quat) else tf.rotation
                        tf = u.Transform(
                            location=u.Vector(loc.x, loc.y, loc.z + dz),
                            rotation=rot_r,
                            scale=tf.scale3d,
                        )
                        v_reseated += 1
                        changed = True
                kept.append(tf)
            if changed:
                comp.modify()
                comp.clear_instances()
                if kept:
                    comp.add_instances(kept, False, True, False)
        vol_report[lbl] = {"pruned": v_pruned, "reseated": v_reseated}
        pruned_total += v_pruned
        reseated_total += v_reseated
        print(f"[STUDY-PCG] {lbl:26s} | pruned={v_pruned:4d} | reseated={v_reseated:4d}")

    if not save_utils.save_map(world, copy_map):
        raise RuntimeError("Could not save updated L_ForestPathForest")
    return {"pruned_total": pruned_total, "reseated_total": reseated_total, "volumes": vol_report}


def update_expanded_road_materials(r49_src: Path, batch: Path):
    """Import expanded 3-road+yard RoadWearField, RoadMixField, TrackFrames, ShoulderLeafField,
    ContinuousMeadowField and re-bind MF_TrailDirt & terrain shaders!
    """
    # 1) Expanded T_RoadWearField (1024x512)
    gate_dir = "/Game/ForestPathStudy/VillageRegion/Reference/GateRoad"
    wear_task = u.AssetImportTask()
    wear_task.filename = str(r49_src / "RoadMix/T_RoadWearField.png")
    wear_task.destination_path = gate_dir
    wear_task.destination_name = "T_RoadWearField"
    wear_task.replace_existing = True
    wear_task.automated = True
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([wear_task])
    wear_tex = u.load_asset(gate_dir + "/T_RoadWearField")
    if not wear_tex:
        raise RuntimeError("Missing T_RoadWearField")
    wear_tex.set_editor_property("srgb", False)
    wear_tex.set_editor_property("compression_settings", u.TextureCompressionSettings.TC_BC7)
    wear_tex.set_editor_property("compression_no_alpha", False)
    for ax in ("address_x", "address_y"):
        wear_tex.set_editor_property(ax, u.TextureAddress.TA_CLAMP)
    lib.save_loaded_asset(wear_tex, False)

    # 2) Re-bind MF_TrailDirt with updated gate_road_surface.ush + forest_road_mix.ush + expanded fields
    road_mix.import_maps(r49_src / "RoadMix")
    fn = u.load_asset("/Game/ForestPathStudy/VillageRegion/Reference/MF_TrailDirt")
    custom = next(
        n for n in ed.get_material_function_expressions(fn)
        if str(n.get_editor_property("desc")) == "R21 independent soil and moss"
    )
    original = (TOOLS / "trail_soil.ush").read_text(encoding="utf-8-sig")
    blend = """RoadNormal=normalize(lerp(RoadNormal,compactNormal,roadMix));
RoadRoughness=lerp(RoadRoughness,compactData.g,roadMix);
RoadAO=lerp(RoadAO,compactData.r,roadMix);
RoadHeight=lerp(RoadHeight,compactData.b,roadMix);
return lerp(color,compactColor,roadMix);"""
    code = (TOOLS / "gate_road_surface.ush").read_text(encoding="utf-8-sig") + "\n" + original.replace("return color;", blend)
    code = road_mix.bind(fn, custom, code)
    custom.set_editor_property("code", code)
    ed.update_material_function(fn)
    lib.save_loaded_asset(fn, False)

    # 3) Update expanded T_ShoulderLeafField + recompile M_ForestReferenceMesh & M_ForestVillageLandscape
    leaves_mod.install(r49_src / "RoadMix/Leaves", reuse_surface=True)

    # 4) Update T_ContinuousMeadowField
    art.src = r49_src / "Terrain"
    cm_field = art.tex("T_ContinuousMeadowField", art.ref + "/ContinuousMeadow", "BC7", False)
    for ax in ("address_x", "address_y"):
        cm_field.set_editor_property(ax, u.TextureAddress.TA_CLAMP)
    cm_field.set_editor_property("compression_no_alpha", False)
    art.save(cm_field)

    # 5) Keep R48b 2048px cap on RoadMix & Leaves atlases (never touch Field/TrackFrames!)
    for folder in ("/Game/ForestPathStudy/VillageRegion/Reference/GateRoad/RoadMix",
                   "/Game/ForestPathStudy/VillageRegion/WoodlandDressing/Leaves"):
        for apath in lib.list_assets(folder, recursive=False, include_folder=False):
            nm = apath.split("/")[-1].lower()
            if "field" in nm or "trackframes" in nm:
                continue
            t = u.load_asset(apath)
            if isinstance(t, u.Texture2D):
                t.set_editor_property("max_texture_size", 2048)
                t.set_editor_property("never_stream", False)
                lib.save_loaded_asset(t, False)

    road_mix.compile_surfaces(batch)


def add_subobject(actor, cls):
    sub = u.get_engine_subsystem(u.SubobjectDataSubsystem)
    bf = u.SubobjectDataBlueprintFunctionLibrary
    parent = sub.k2_gather_subobject_data_for_instance(actor)[0]
    handle, err = sub.add_new_subobject(u.AddNewSubobjectParams(parent_handle=parent, new_class=cls))
    obj = bf.get_associated_object(bf.get_data(handle))
    if not obj:
        raise RuntimeError(f"add_subobject({cls}) failed: {err}")
    return obj


def assemble_lumber_mill_compound(world, r49_src: Path, catalog: dict, r48_catalog: list):
    """Spawn ONE clean static actor LumberMill_Compound containing:
       - 3 Hero 3-Room Buildings (Warehouse, ToolRoom + Canopy, 2-Story Walkable Bunkhouse)
       - HISM-batched Yard, Warehouse, ToolRoom & 2F Bunkhouse Props (strict cull/shadow budgets!)
       - 7 Warm Practical Lantern / Hearth Point Lights (fixture-lighting-standard.md, CastShadow=False)
    """
    gz_cm = build_ground_sampler(r49_src / "Terrain/region.i16")

    # Remove any previous LumberMill_Compound actor cleanly (idempotent re-runs!)
    for a in level.actor_list():
        if a.get_actor_label() == "LumberMill_Compound" or "LumberMill.R49" in map(str, a.tags):
            actors_sub.destroy_actor(a)

    origin = u.Vector(YARD_CX_CM, YARD_CY_CM, YARD_Z_CM)
    comp_actor = actors_sub.spawn_actor_from_class(u.Actor, origin)
    if not comp_actor or not comp_actor.get_path_name().startswith(level.village + "."):
        raise RuntimeError("Failed spawning LumberMill_Compound in persistent level")
    comp_actor.set_actor_label("LumberMill_Compound")
    comp_actor.set_editor_property("tags", ["LumberMill.R49"])
    if not comp_actor.root_component:
        add_subobject(comp_actor, u.SceneComponent)
    comp_actor.root_component.set_mobility(u.ComponentMobility.STATIC)
    comp_actor.set_actor_location(origin, False, True)

    # Helper to resolve Quixel, Ruined & existing project meshes + bounding boxes
    arch = catalog["arch"]
    ruined = catalog.get("ruined", {})
    props = catalog["props"]
    r48_by_role = defaultdict(list)
    for row in r48_catalog:
        r48_by_role[row["role"]].append(row)

    TAG_RUIN = "LumberMill.Ruin"
    TAG_RESTORED = "LumberMill.Restored"
    TAG_SHARED = "LumberMill.Shared"
    TAG_SOLID = "LumberMill.Solid"

    def tag_component(comp, state_tag: str, solid: bool = False):
        """Tag a component for C++ dual-state Ruined/Restored switching and apply default map state (Ruined visible, Restored hidden)."""
        tags = [state_tag]
        if solid:
            tags.append(TAG_SOLID)
        comp.set_editor_property("component_tags", tags)
        show_default = (state_tag != TAG_RESTORED)
        comp.set_visibility(show_default)
        comp.set_hidden_in_game(not show_default)
        if isinstance(comp, u.PrimitiveComponent):
            if show_default and solid:
                comp.set_collision_profile_name("BlockAll")
                comp.set_collision_enabled(u.CollisionEnabled.QUERY_AND_PHYSICS)
            else:
                comp.set_collision_profile_name("BlockAll" if solid else "NoCollision")
                comp.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)

    def qmesh(role, idx=0):
        ms = props[role]["meshes"]
        return ms[min(idx, len(ms) - 1)]["mesh"]

    # Verified resident project meshes (zero extra Texture Pool!)
    P = {
        "log_stack": "/Game/WorldGeneration/TemperateHills/VillageCarpenter/Props/SM_CarpenterLogStack.SM_CarpenterLogStack",
        "drying_rack": "/Game/WorldGeneration/TemperateHills/VillageCarpenter/Props/SM_CarpenterDryingRack.SM_CarpenterDryingRack",
        "seasoning": "/Game/WorldGeneration/TemperateHills/VillageCarpenter/YardDetail/SM_CarpenterSeasoningBoards.SM_CarpenterSeasoningBoards",
        "flitches": "/Game/WorldGeneration/TemperateHills/VillageCarpenter/YardDetail/SM_CarpenterYardFlitches.SM_CarpenterYardFlitches",
        "offcut_crib": "/Game/WorldGeneration/TemperateHills/VillageCarpenter/YardDetail/SM_CarpenterOffcutCrib.SM_CarpenterOffcutCrib",
        "chop_block": "/Game/WorldGeneration/TemperateHills/VillageCarpenter/Props/SM_CarpenterBlock.SM_CarpenterBlock",
        "carp_tools": "/Game/WorldGeneration/TemperateHills/VillageCarpenter/Props/SM_CarpenterTools.SM_CarpenterTools",
        "shavings": "/Game/WorldGeneration/TemperateHills/VillageCarpenter/Props/SM_CarpenterShavings.SM_CarpenterShavings",
        "bench_curls": "/Game/WorldGeneration/TemperateHills/VillageCarpenter/YardDetail/SM_CarpenterBenchCurls.SM_CarpenterBenchCurls",
        "hewing_chips": "/Game/WorldGeneration/TemperateHills/VillageCarpenter/YardDetail/SM_CarpenterHewingChips.SM_CarpenterHewingChips",
        "saw_slivers": "/Game/WorldGeneration/TemperateHills/VillageCarpenter/YardDetail/SM_CarpenterSawSlivers.SM_CarpenterSawSlivers",
        "spoiled_stock": "/Game/WorldGeneration/TemperateHills/VillageCarpenter/Props/SM_CarpenterSpoiledStock.SM_CarpenterSpoiledStock",
        "chest": "/Game/WorldGeneration/TemperateHills/VillageCarpenter/InteriorR1/SM_CarpenterJoinersChest.SM_CarpenterJoinersChest",
        "peg_bin": "/Game/WorldGeneration/TemperateHills/VillageCarpenter/InteriorR1/SM_CarpenterPegBin.SM_CarpenterPegBin",
        "hinge_tray": "/Game/WorldGeneration/TemperateHills/VillageCarpenter/InteriorR1/SM_CarpenterHingeTray.SM_CarpenterHingeTray",
        "stacked_cases": "/Game/WorldGeneration/TemperateHills/VillageCarpenter/InteriorR1/SM_CarpenterStackedCases.SM_CarpenterStackedCases",
        "wash_barrel": "/Game/WorldGeneration/TemperateHills/VillageCarpenter/InteriorR1/SM_CarpenterWashBarrel.SM_CarpenterWashBarrel",
        "timber_bed": "/Game/WorldGeneration/TemperateHills/VillageBlacksmith/ArtPassR2/Meshes/SM_VillageTimberBed.SM_VillageTimberBed",
        "oak_table": "/Game/WorldGeneration/TemperateHills/VillageBlacksmith/ArtPassR2/Meshes/SM_VillageOakTable.SM_VillageOakTable",
        "oak_stool": "/Game/WorldGeneration/TemperateHills/VillageBlacksmith/ArtPassR2/Meshes/SM_VillageOakStool.SM_VillageOakStool",
        "oak_shelf": "/Game/WorldGeneration/TemperateHills/VillageBlacksmith/ArtPassR2/Meshes/SM_VillageOakShelf.SM_VillageOakShelf",
        "tavern_table": "/Game/WorldGeneration/VillageTavern/Furniture/SM_TavernTable.SM_TavernTable",
        "tavern_stool": "/Game/WorldGeneration/VillageTavern/Furniture/SM_TavernStool.SM_TavernStool",
        "cupboard": "/Game/WorldGeneration/VillageTavern/Inn/SM_InnCupboard_JoineryR4.SM_InnCupboard_JoineryR4",
        "bowl": "/Game/WorldGeneration/VillageTavern/DiningBowls/SM_TavernEatingBowl.SM_TavernEatingBowl",
        "stew_bowl": "/Game/WorldGeneration/VillageTavern/DiningBowls/SM_TavernStewBowl.SM_TavernStewBowl",
        "spoon": "/Game/WorldGeneration/VillageTavern/EatingUtensils/SM_TavernWoodSpoon.SM_TavernWoodSpoon",
        "grain_sack": "/Game/WorldGeneration/TemperateHills/VillageBakery/Props/SM_BakeryGrainSack.SM_BakeryGrainSack",
        "hay_wagon": "/Game/WorldGeneration/TemperateHills/VillageStable/PropsR43/SM_Stable_HayWagon.SM_Stable_HayWagon",
        "lamp_post": "/Game/WorldGeneration/TemperateHills/VillageStable/PropsR43/SM_Stable_YardLampPost.SM_Stable_YardLampPost",
        "mill_barrow": "/Game/WorldGeneration/TemperateHills/VillageWindmill/Yard/Meshes/SM_MillBarrow.SM_MillBarrow",
        "lantern": "/Game/UnrealNormandy/StaticMeshes/SM_Props_Lantern_02A.SM_Props_Lantern_02A",
        # Official player production tool Felling Axe (production_tools.json -> tool_axe = 伐木斧!)
        "official_axe": "/Game/Items/ProductionTools/BattleAxe20260919/SM_BattleAxe.SM_BattleAxe",
        # Our Blender 5.1 bespoke 3A sawmill hero props (R49c upgraded suite!)
        "sawbuck": arch["SM_LM_SawbuckStation"]["mesh"],
        "crosscut_saw": arch["SM_LM_TwoManCrosscutSaw"]["mesh"],
        "frame_pit_saw": arch["SM_LM_FramePitSaw"]["mesh"],
        "bench_saw_set": arch["SM_LM_WorkbenchSawSet"]["mesh"],
        "chop_stump_a": arch["SM_LM_ChoppingStumpA"]["mesh"],
        "chop_stump_b": arch["SM_LM_ChoppingStumpB"]["mesh"],
        "bunk_bed": arch["SM_LM_BunkBed"]["mesh"],
        "timber_rack": arch["SM_LM_TimberRack"]["mesh"],
        "camp_fence_panel": arch["SM_LM_CampFencePanel"]["mesh"],
        "camp_fence_post": arch["SM_LM_CampFencePost"]["mesh"],
        "camp_gate_arch": arch["SM_LM_CampGateArch"]["mesh"],
        "bark_chips_a": arch["SM_LM_BarkChipScatterA"]["mesh"],
        "bark_chips_b": arch["SM_LM_BarkChipScatterB"]["mesh"],
        # Ruined R51 Blender 5.1 meshes (0 extra VRAM, resident PBR materials!)
        "ruin_gate_arch": ruined["SM_LM_CampGateArch_Ruined"]["mesh"],
        "ruin_fence_panel": ruined["SM_LM_CampFencePanel_Ruined"]["mesh"],
        "ruin_timber_rack": ruined["SM_LM_TimberRack_Ruined"]["mesh"],
        "rubble_a": ruined["SM_LM_RubblePileA"]["mesh"],
        "rubble_b": ruined["SM_LM_RubblePileB"]["mesh"],
        # Our newly acquired & style-calibrated Quixel Megascans lumber props
        "q_logpile1": qmesh("lumber_logpile_s1"),
        "q_logpile2": qmesh("lumber_logpile_s2"),
        "q_firewood": qmesh("lumber_firewood_pack"),
        "q_plank_stack": qmesh("lumber_plank_stack"),
        "q_planks": qmesh("lumber_planks"),
        "q_boards": qmesh("lumber_boards"),
        "q_axe": qmesh("tool_axe"),
        "q_bowsaw": qmesh("tool_bowsaw"),
        "q_framesaw": qmesh("tool_framesaw"),
        "q_wedge": qmesh("tool_wedge"),
        "q_handsaw": qmesh("tool_handsaw"),
        "q_hammer": qmesh("tool_hammer"),
        "q_pulley": qmesh("prop_pulley"),
        "q_rope": qmesh("prop_rope"),
        "q_bucket": qmesh("prop_bucket"),
        "q_ladder": qmesh("prop_ladder"),
        "q_sack": qmesh("prop_sack"),
        "q_bench": qmesh("prop_bench"),
        "q_shelf": qmesh("prop_shelf"),
        "q_chair": qmesh("prop_chair"),
        # R48 verified natural yard/clearing props (NO roadside broken fences, NO ruined stone walls!)
        "r48_logpile": r48_by_role["prop_logpile"][0]["mesh"],
        "r48_barrel": r48_by_role["prop_barrel"][0]["mesh"],
        "r48_crate": r48_by_role["prop_crate"][0]["mesh"],
        "r48_beam": r48_by_role["prop_beam"][0]["mesh"],
        "r48_wheel": r48_by_role["prop_wheel"][0]["mesh"],
        "r48_boulder": r48_by_role["rock_boulder"][0]["mesh"],
        "r48_stump0": r48_by_role["stump"][0]["mesh"],
        "r48_stump1": r48_by_role["stump"][1]["mesh"],
        "r48_log0": r48_by_role["log"][0]["mesh"],
        "r48_log1": r48_by_role["log"][1]["mesh"],
    }

    # Load and cache StaticMesh assets + exact bounding boxes (skips gracefully if any optional resident path missing)
    sm_cache = {}
    box_cache = {}
    for k, mpath in list(P.items()):
        sm = u.load_asset(mpath)
        if isinstance(sm, u.StaticMesh):
            sm_cache[k] = sm
            b = sm.get_bounding_box()
            box_cache[k] = (
                float(b.min.x), float(b.min.y), float(b.min.z),
                float(b.max.x), float(b.max.y), float(b.max.z),
            )
        else:
            print(f"[WARN] Optional resident mesh missing ({k}): {mpath}")

    # 1) Place BOTH sets of 3 Hero Buildings (Restored hidden by default, Ruined visible by default!)
    DZ_BLDG = 30.0
    buildings = [
        ("SM_LM_Warehouse", (-520.0, -670.0, DZ_BLDG), 0.0),
        ("SM_LM_ToolRoom",  (340.0, -670.0, DZ_BLDG), 0.0),
        ("SM_LM_Bunkhouse", (1040.0, -600.0, DZ_BLDG), 0.0),
    ]
    for bname, (lx, ly, lz), yaw in buildings:
        sm = u.load_asset(arch[bname]["mesh"])
        smc = add_subobject(comp_actor, u.StaticMeshComponent)
        smc.set_mobility(u.ComponentMobility.STATIC)
        smc.set_static_mesh(sm)
        smc.set_relative_location_and_rotation(
            u.Vector(lx, ly, lz), u.Rotator(pitch=0.0, yaw=yaw, roll=0.0), False, True
        )
        smc.set_cast_shadow(True)
        smc.set_editor_property("can_ever_affect_navigation", True)
        smc.set_editor_property("ld_max_draw_distance", 28000.0)
        smc.set_editor_property("visible_in_ray_tracing", False)
        smc.set_editor_property("receives_decals", False)
        tag_component(smc, TAG_RESTORED, solid=True)

    ruined_buildings = [
        ("SM_LM_Warehouse_Ruined", (-520.0, -670.0, DZ_BLDG), 0.0),
        ("SM_LM_ToolRoom_Ruined",  (340.0, -670.0, DZ_BLDG), 0.0),
        ("SM_LM_Bunkhouse_Ruined", (1040.0, -600.0, DZ_BLDG), 0.0),
    ]
    for bname, (lx, ly, lz), yaw in ruined_buildings:
        sm = u.load_asset(ruined[bname]["mesh"])
        smc = add_subobject(comp_actor, u.StaticMeshComponent)
        smc.set_mobility(u.ComponentMobility.STATIC)
        smc.set_static_mesh(sm)
        smc.set_relative_location_and_rotation(
            u.Vector(lx, ly, lz), u.Rotator(pitch=0.0, yaw=yaw, roll=0.0), False, True
        )
        smc.set_cast_shadow(True)
        smc.set_editor_property("can_ever_affect_navigation", True)
        smc.set_editor_property("ld_max_draw_distance", 28000.0)
        smc.set_editor_property("visible_in_ray_tracing", False)
        smc.set_editor_property("receives_decals", False)
        tag_component(smc, TAG_RUIN, solid=True)

    # 2) HISM Prop Accumulator grouped by (state_tag, mesh_key, tier) for dual-state switching & minimal draw calls!
    TIER_CFG = {
        "hero":    dict(cull_start=10000, cull_end=13500, shadow=True,  col="BlockAll",    nav=True,  df=False),
        "medium":  dict(cull_start=5400,  cull_end=7200,  shadow=True,  col="BlockAll",    nav=False, df=False),
        "clutter": dict(cull_start=3200,  cull_end=4400,  shadow=False, col="NoCollision", nav=False, df=False),
        "chip":    dict(cull_start=2600,  cull_end=3600,  shadow=False, col="NoCollision", nav=False, df=False),
    }
    hism_buckets = defaultdict(list)  # (state_tag, key, tier) -> list[u.Transform] in Actor-local coords!
    grounding_audit = []

    def ter_z_local(lx: float, ly: float) -> float:
        return gz_cm(YARD_CX_CM + lx, YARD_CY_CM + ly) - YARD_Z_CM

    def _rotated_aabb_bounds(bx0, by0, bz0, bx1, by1, bz1, sx, sy, sz, pitch, yaw, roll):
        """Exact rotated 8-corner AABB in local space (eliminates floating tilted barrels/wagons/chairs/wheels!)."""
        quat = u.Rotator(pitch=pitch, yaw=yaw, roll=roll).quaternion()
        min_x = min_y = min_z = 1e9
        max_x = max_y = max_z = -1e9
        for px in (bx0 * sx, bx1 * sx):
            for py in (by0 * sy, by1 * sy):
                for pz in (bz0 * sz, bz1 * sz):
                    v = quat.rotate_vector(u.Vector(px, py, pz))
                    if v.x < min_x: min_x = v.x
                    if v.y < min_y: min_y = v.y
                    if v.z < min_z: min_z = v.z
                    if v.x > max_x: max_x = v.x
                    if v.y > max_y: max_y = v.y
                    if v.z > max_z: max_z = v.z
        return min_x, min_y, min_z, max_x, max_y, max_z

    def place_on_z(key: str, tier: str, lx: float, ly: float, surface_z_local: float,
                   yaw: float = 0.0, scale: float = 1.0, pitch: float = 0.0, roll: float = 0.0,
                   embed: float = 0.5, use_terrain: bool = False, raw_pivot: bool = False,
                   pivot_z_at_ground: bool = False, scale_xyz=None, state_tag: str = TAG_RESTORED):
        """Seat mesh cleanly onto surface_z_local (or exact lowest footprint terrain if use_terrain=True) using exact rotated bounds!"""
        if key not in sm_cache:
            return
        bx0, by0, bz0, bx1, by1, bz1 = box_cache[key]
        sx, sy, sz = scale_xyz if scale_xyz is not None else (scale, scale, scale)
        r_min_x, r_min_y, r_min_z, r_max_x, r_max_y, r_max_z = _rotated_aabb_bounds(
            bx0, by0, bz0, bx1, by1, bz1, sx, sy, sz, pitch, yaw, roll
        )
        if use_terrain:
            # Sample center + 4 footprint corners and seat onto the lowest ground point so slopes NEVER expose floating ends!
            hx = max(12.0, min(140.0, 0.45 * (r_max_x - r_min_x)))
            hy = max(12.0, min(140.0, 0.45 * (r_max_y - r_min_y)))
            z_base = min(
                ter_z_local(lx, ly),
                ter_z_local(lx - hx, ly - hy),
                ter_z_local(lx + hx, ly - hy),
                ter_z_local(lx - hx, ly + hy),
                ter_z_local(lx + hx, ly + hy),
            )
        else:
            z_base = surface_z_local
        z_pos = (z_base - embed) if pivot_z_at_ground else (z_base - r_min_z - embed)
        if raw_pivot or pivot_z_at_ground:
            loc = u.Vector(lx, ly, z_pos)
        else:
            cx_r = 0.5 * (r_min_x + r_max_x)
            cy_r = 0.5 * (r_min_y + r_max_y)
            loc = u.Vector(lx - cx_r, ly - cy_r, z_pos)
        rot = u.Rotator(pitch=pitch, yaw=yaw, roll=roll)
        hism_buckets[(state_tag, key, tier)].append(u.Transform(location=loc, rotation=rot, scale=u.Vector(sx, sy, sz)))
        actual_bot_z = z_pos + r_min_z
        gap_cm = actual_bot_z - z_base
        grounding_audit.append({
            "state": state_tag, "key": key, "tier": tier,
            "xy_local": [round(lx, 1), round(ly, 1)],
            "z_surf": round(z_base, 1),
            "bot_z": round(actual_bot_z, 1),
            "gap_cm": round(gap_cm, 2),
            "mounted": (not use_terrain) and (surface_z_local > FL1 + 5.0),
        })

    # =========================================================================
    # A) ROOM 1 — 仓库 (Warehouse, Center=(-520, -670, +18), Floor FL1 = +34 cm)
    #    Spans X in [-1040..0], Y in [-1020..-320]; Front door X=[-670..-370], Y=-320; East door X=0, Y=[-780..-640]
    # =========================================================================
    FL1 = 16.0 + DZ_BLDG  # +34.0 cm (cleanly above Nanite Landscape displacement!)
    # 3 Heavy cantilevered timber racks loaded with seasoned lumber along west & rear walls
    place_on_z("timber_rack", "hero", -945.0, -765.0, FL1, yaw=90.0, scale=0.96, embed=0.2)
    place_on_z("timber_rack", "hero", -760.0, -942.0, FL1, yaw=0.0, scale=0.96, embed=0.2)
    place_on_z("timber_rack", "hero", -340.0, -942.0, FL1, yaw=0.0, scale=0.96, embed=0.2)
    # Stacked timber planks, seasoning boards & cut logs (shifted well clear of X=0 shared wall with ToolRoom!)
    place_on_z("q_plank_stack", "hero", -815.0, -485.0, FL1, yaw=2.0, scale=0.56, embed=0.4)
    place_on_z("q_planks", "medium", -815.0, -570.0, FL1, yaw=4.0, scale=0.50, embed=0.4)
    place_on_z("seasoning", "hero", -278.0, -475.0, FL1, yaw=88.0, scale=0.90, embed=0.4)
    place_on_z("q_logpile1", "hero", -195.0, -895.0, FL1, yaw=90.0, scale=1.65, embed=0.5)
    place_on_z("q_boards", "clutter", -580.0, -905.0, FL1, yaw=12.0, scale=2.10, embed=0.2)
    # Supply & rigging corner (medieval joiner chests & stacked cases — zero modern mechanic toolboxes!)
    place_on_z("stacked_cases", "medium", -942.0, -420.0, FL1, yaw=8.0, scale=0.96, embed=0.3)
    place_on_z("chest", "medium", -852.0, -408.0, FL1, yaw=-12.0, scale=0.94, embed=0.3)
    place_on_z("r48_barrel", "medium", -950.0, -515.0, FL1, yaw=24.0, scale=0.95, embed=0.4)
    place_on_z("r48_barrel", "medium", -945.0, -585.0, FL1, yaw=-40.0, scale=0.92, embed=0.4)
    place_on_z("q_sack", "medium", -115.0, -420.0, FL1, yaw=15.0, scale=1.05, embed=0.5)
    place_on_z("q_sack", "medium", -85.0, -485.0, FL1, yaw=-35.0, scale=0.98, embed=0.5)
    place_on_z("grain_sack", "medium", -148.0, -478.0, FL1, yaw=42.0, scale=0.96, embed=0.4)
    place_on_z("stacked_cases", "medium", -112.0, -555.0, FL1, yaw=90.0, scale=0.94, embed=0.3)
    place_on_z("chest", "medium", -540.0, -935.0, FL1, yaw=0.0, scale=0.95, embed=0.3)
    place_on_z("q_rope", "clutter", -320.0, -415.0, FL1, yaw=22.0, scale=1.15, embed=0.3)
    place_on_z("q_bucket", "clutter", -280.0, -430.0, FL1, yaw=-18.0, scale=0.95, embed=0.3)
    place_on_z("q_ladder", "medium", -970.0, -640.0, FL1, yaw=90.0, pitch=-12.0, scale=1.50, embed=1.0)
    # Spare Two-Man Crosscut Saw displayed visibly on NW Warehouse interior timber wall!
    place_on_z("crosscut_saw", "clutter", -825.0, -350.0, 178.0 + DZ_BLDG, yaw=0.0, scale=0.95, embed=0.0, pivot_z_at_ground=True)
    # Double wooden pulley hanging directly inside WH_HoistEye shackle (eye Z = 326 + DZ_BLDG = 344 -> pulley bottom Z = 290)!
    place_on_z("q_pulley", "clutter", -520.0, -225.0, 272.0 + DZ_BLDG, yaw=90.0, scale=1.00, embed=0.0)

    # =========================================================================
    # B) ROOM 2 — 工具间 (Tool Room, Center=(+340, -670, +18), Floor FL1 = +34 cm) + SAWING CANOPY
    # =========================================================================
    WB_TOP = 95.0 + DZ_BLDG  # +113.0 cm
    place_on_z("bench_saw_set", "clutter", 365.0, -935.0, WB_TOP, yaw=-6.0, scale=1.04, embed=0.1, pivot_z_at_ground=True)
    place_on_z("carp_tools", "clutter", 242.0, -942.0, WB_TOP, yaw=12.0, scale=0.94, embed=0.2)
    place_on_z("q_hammer", "clutter", 465.0, -935.0, WB_TOP, yaw=38.0, scale=1.05, embed=0.2)
    place_on_z("q_wedge", "clutter", 195.0, -930.0, WB_TOP, yaw=-15.0, scale=1.10, embed=0.2)
    place_on_z("bench_curls", "clutter", 300.0, -922.0, WB_TOP, yaw=8.0, scale=0.92, embed=0.1)
    place_on_z("hinge_tray", "clutter", 488.0, -956.0, WB_TOP, yaw=-6.0, scale=0.92, embed=0.1)
    # Hero Wall-Mounted Saws
    place_on_z("crosscut_saw", "clutter", 340.0, -982.0, 170.0 + DZ_BLDG, yaw=0.0, scale=0.90, embed=0.0, pivot_z_at_ground=True)
    place_on_z("frame_pit_saw", "clutter", 640.0, -860.0, 122.0 + DZ_BLDG, yaw=-90.0, scale=0.96, embed=0.0, pivot_z_at_ground=True)
    # Spare Official Player Felling Axe (SM_BattleAxe) propped neatly against workbench front-left leg!
    # NOTE: SM_BattleAxe's weapon materials (M_ToolHead_Master_Axe & M_BattleAxe) are non-ISM weapon shaders,
    # so ALL decorative official_axe placements use dedicated StaticMeshComponents (ZERO white WorldGrid fallback!).
    def add_static_axe(lx, ly, lz, pitch, yaw, roll, scale=1.0):
        if "official_axe" not in sm_cache:
            return
        smc = add_subobject(comp_actor, u.StaticMeshComponent)
        smc.set_mobility(u.ComponentMobility.STATIC)
        smc.set_static_mesh(sm_cache["official_axe"])
        smc.set_relative_location_and_rotation(
            u.Vector(lx, ly, lz), u.Rotator(pitch=pitch, yaw=yaw, roll=roll), False, True
        )
        smc.set_relative_scale3d(u.Vector(scale, scale, scale))
        smc.set_cast_shadow(False)
        smc.set_editor_property("ld_max_draw_distance", 4400.0)
        smc.set_editor_property("affect_distance_field_lighting", False)
        smc.set_editor_property("affect_dynamic_indirect_lighting", False)
        smc.set_editor_property("visible_in_ray_tracing", False)
        smc.set_editor_property("receives_decals", False)
        smc.set_editor_property("generate_overlap_events", False)
        tag_component(smc, TAG_RESTORED, solid=False)

    add_static_axe(172.0, -882.0, FL1 + 37.5, pitch=-14.0, yaw=28.0, roll=6.0, scale=1.00)
    # Under & beside workbench + along east/west tool walls (keeping ALL 3 doorways 100% open!)
    place_on_z("peg_bin", "clutter", 118.0, -935.0, FL1, yaw=15.0, scale=0.95, embed=0.2)
    place_on_z("offcut_crib", "medium", 575.0, -920.0, FL1, yaw=-90.0, scale=0.92, embed=0.3)
    place_on_z("shavings", "clutter", 340.0, -845.0, FL1, yaw=30.0, scale=1.02, embed=0.1)
    place_on_z("drying_rack", "medium", 112.0, -455.0, FL1, yaw=90.0, scale=0.90, embed=0.3)
    place_on_z("spoiled_stock", "medium", 572.0, -455.0, FL1, yaw=-85.0, scale=0.88, embed=0.3)
    place_on_z("wash_barrel", "medium", 582.0, -545.0, FL1, yaw=12.0, scale=0.92, embed=0.3)
    place_on_z("q_bowsaw", "clutter", 95.0, -870.0, FL1, yaw=75.0, pitch=8.0, scale=1.08, embed=0.3)
    place_on_z("q_shelf", "clutter", 636.0, -470.0, 152.0 + DZ_BLDG, yaw=-90.0, scale=1.02, embed=0.0)
    place_on_z("q_bucket", "clutter", 168.0, -865.0, FL1, yaw=20.0, scale=0.92, embed=0.3)

    # Covered Open-Sided Front Sawing Canopy (X in [+40..+640], Y in [-310..-10])
    # West Canopy Bay: Active Sawing Station (3A Organic Sawbuck + Two-Man Crosscut Saw seated MID-KERF!)
    sb_x, sb_y, sb_yaw = 152.0, -155.0, 8.0
    sb_tz = ter_z_local(sb_x, sb_y)
    place_on_z("sawbuck", "hero", sb_x, sb_y, sb_tz, yaw=sb_yaw, scale=1.00, embed=0.6)
    place_on_z("bark_chips_b", "chip", 158.0, -152.0, sb_tz, yaw=22.0, scale=0.88, embed=0.0, pivot_z_at_ground=True)
    kerf_rad = math.radians(sb_yaw)
    saw_x = sb_x + 28.0 * math.cos(kerf_rad)
    saw_y = sb_y + 28.0 * math.sin(kerf_rad)
    place_on_z("crosscut_saw", "clutter", saw_x, saw_y, sb_tz + 96.5, yaw=sb_yaw + 90.0, pitch=3.0, scale=1.00, embed=0.0, pivot_z_at_ground=True)
    place_on_z("frame_pit_saw", "clutter", 56.0, -45.0, 0.0, yaw=-26.0, pitch=0.0, roll=-11.0, scale=1.04, embed=0.5, use_terrain=True)
    place_on_z("saw_slivers", "clutter", 172.0, -142.0, 0.0, yaw=-18.0, scale=1.08, embed=0.1, use_terrain=True)
    place_on_z("q_wedge", "clutter", 96.0, -245.0, 0.0, yaw=55.0, scale=1.18, embed=0.4, use_terrain=True)
    place_on_z("q_bucket", "clutter", 78.0, -102.0, 0.0, yaw=-12.0, scale=0.96, embed=0.5, use_terrain=True)
    # East Canopy Bay: Freshly Sawn Plank Stack + Hewing Chips
    place_on_z("q_planks", "medium", 535.0, -165.0, 0.0, yaw=88.0, scale=0.48, embed=0.5, use_terrain=True)
    place_on_z("hewing_chips", "clutter", 495.0, -160.0, 0.0, yaw=32.0, scale=1.04, embed=0.1, use_terrain=True)
    place_on_z("q_bowsaw", "clutter", 592.0, -245.0, 0.0, yaw=-68.0, pitch=10.0, scale=1.08, embed=0.4, use_terrain=True)

    # =========================================================================
    # C) ROOM 3 — 临时宿舍（二层）(Two-Story Bunkhouse, Center=(+1040, -600, +18))
    #    1F Floor FL1 = +34 cm; 2F Floor FL2 = +330 cm!
    # =========================================================================
    place_on_z("tavern_table", "medium", 955.0, -510.0, FL1, yaw=0.0, scale=0.95, embed=0.2)
    place_on_z("q_bench", "medium", 955.0, -595.0, FL1, yaw=0.0, scale=0.94, embed=0.3)
    place_on_z("q_bench", "medium", 955.0, -425.0, FL1, yaw=180.0, scale=0.94, embed=0.3)
    place_on_z("q_chair", "medium", 828.0, -510.0, FL1, yaw=90.0, scale=0.96, embed=0.3)
    place_on_z("q_chair", "medium", 1082.0, -510.0, FL1, yaw=-90.0, scale=0.96, embed=0.3)
    # Tableware on dining table (table top Z = FL1 + 78 = 112 cm)
    place_on_z("bowl", "clutter", 920.0, -525.0, FL1 + 78.0, yaw=15.0, scale=1.0, embed=0.1)
    place_on_z("stew_bowl", "clutter", 988.0, -500.0, FL1 + 78.0, yaw=-25.0, scale=1.0, embed=0.1)
    place_on_z("spoon", "clutter", 950.0, -527.0, FL1 + 78.0, yaw=40.0, scale=1.0, embed=0.1)
    # Firewood logs stacked boldly atop forged-iron hearth andirons (Z = FL1 + 13 = 47 cm, X=1346, Y=-630)!
    for h_dx, h_dy, h_dz, h_yaw, h_pitch, h_sc in (
        (0.0, -16.0, 0.0, 84.0, 0.0, 2.45),
        (-2.0, 14.0, 0.0, 96.0, 0.0, 2.40),
        (3.0, -2.0, 6.0, 74.0, 8.0, 2.55),
        (-4.0, 4.0, 11.0, 108.0, -10.0, 2.30),
    ):
        place_on_z("q_firewood", "clutter", 1346.0 + h_dx, -630.0 + h_dy, FL1 + 13.0 + h_dz, yaw=h_yaw, pitch=h_pitch, scale=h_sc, embed=0.2)
    # Glowing hearth ember coal bed resting between the forged iron andirons (reuses resident M_StaffHearthEmber!)
    ember_mat = u.load_asset("/Game/WorldGeneration/TemperateHills/ShopLighting/M_StaffHearthEmber")
    if ember_mat:
        ember_smc = add_subobject(comp_actor, u.StaticMeshComponent)
        ember_smc.set_mobility(u.ComponentMobility.STATIC)
        ember_smc.set_static_mesh(u.load_asset("/Engine/BasicShapes/Sphere"))
        ember_smc.set_material(0, ember_mat)
        ember_smc.set_relative_location(u.Vector(1348.0, -630.0, FL1 + 8.5), False, True)
        ember_smc.set_relative_scale3d(u.Vector(0.36, 0.72, 0.14))
        ember_smc.set_cast_shadow(False)
        ember_smc.set_collision_profile_name("NoCollision")
        ember_smc.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
        ember_smc.set_editor_property("ld_max_draw_distance", 2200.0)
        tag_component(ember_smc, TAG_RESTORED, solid=False)
    # Cupboard, hearth firewood reserve, bucket, chest & shelf
    place_on_z("cupboard", "medium", 825.0, -238.0, FL1, yaw=180.0, scale=0.90, embed=0.3)
    place_on_z("q_logpile2", "medium", 1280.0, -768.0, FL1, yaw=82.0, scale=0.92, embed=0.4)
    for fw_dx, fw_dy, fw_y in ((0.0, 0.0, 12.0), (12.0, -14.0, 75.0), (-10.0, -8.0, -30.0)):
        place_on_z("q_firewood", "clutter", 1280.0 + fw_dx, -708.0 + fw_dy, FL1, yaw=fw_y, scale=1.95, embed=0.2)
    place_on_z("q_bucket", "clutter", 1285.0, -460.0, FL1, yaw=-20.0, scale=0.92, embed=0.3)
    place_on_z("chest", "medium", 1185.0, -245.0, FL1, yaw=180.0, scale=0.92, embed=0.3)
    place_on_z("q_shelf", "clutter", 726.0, -450.0, 152.0 + DZ_BLDG, yaw=90.0, scale=1.0, embed=0.0)
    place_on_z("q_bench", "medium", 805.0, -135.0, 0.0, yaw=0.0, scale=0.92, embed=0.4, use_terrain=True)

    # --- 2F Walkable Dormitory (Floor FL2 = +330 cm!) ---
    FL2 = 312.0 + DZ_BLDG
    place_on_z("bunk_bed", "hero", 768.0, -565.0, FL2, yaw=90.0, scale=0.98, embed=0.2)
    place_on_z("bunk_bed", "hero", 768.0, -310.0, FL2, yaw=90.0, scale=0.98, embed=0.2)
    place_on_z("timber_bed", "hero", 1255.0, -310.0, FL2, yaw=-90.0, scale=0.98, embed=0.2)
    place_on_z("chest", "medium", 878.0, -565.0, FL2, yaw=90.0, scale=0.88, embed=0.2)
    place_on_z("chest", "medium", 878.0, -310.0, FL2, yaw=90.0, scale=0.88, embed=0.2)
    place_on_z("chest", "medium", 1140.0, -310.0, FL2, yaw=-90.0, scale=0.88, embed=0.2)
    place_on_z("oak_table", "medium", 1040.0, -255.0, FL2, yaw=0.0, scale=0.92, embed=0.2)
    place_on_z("q_chair", "medium", 1040.0, -345.0, FL2, yaw=0.0, scale=0.95, embed=0.2)
    place_on_z("oak_stool", "medium", 1110.0, -265.0, FL2, yaw=-45.0, scale=0.95, embed=0.2)
    place_on_z("oak_shelf", "medium", 1325.0, -590.0, FL2, yaw=-90.0, scale=0.92, embed=0.2)
    place_on_z("q_shelf", "clutter", 1352.0, -490.0, FL2 + 138.0, yaw=-90.0, scale=0.98, embed=0.0)
    place_on_z("bowl", "clutter", 1020.0, -250.0, FL2 + 78.0, yaw=10.0, scale=0.95, embed=0.1)

    # =========================================================================
    # D) RE-ZONED LUMBER MILL WORKING YARD — 3A CHOPPING STUMPS + OFFICIAL FELLING AXE + RAIN-WET DECALS (R49c!)
    # =========================================================================
    # 1) Rain-Reactive Organic Woodchip Deferred Decals (M_LM_WoodchipDecal: MPC_FPS_Weather + 4-oct domain-warped FBM!)
    decal_mat = u.load_asset(f"{lm_import.LM_MATS}/M_LM_WoodchipDecal")
    decal_specs = [
        # (lx, ly, half_x_cm, half_y_cm, yaw_deg) — Note: DecalComponent with pitch=-90 maps decal_size (DepthX, SizeY, SizeZ)
        (825.0,  425.0, 225.0, 195.0,  18.0),   # Around Chopping Stump A
        (1055.0, 520.0, 235.0, 185.0, -42.0),   # Around Chopping Stump B
        (935.0,  345.0, 180.0, 155.0,  64.0),   # Bridging work scatter between stumps & cordwood
        (160.0, -155.0, 200.0, 170.0,  12.0),   # Under Sawing Canopy Sawbuck
        (-900.0, 275.0, 245.0, 210.0, -26.0),   # West Log Deck woodchip/bark bed
        (-1180.0, -85.0, 225.0, 190.0, 34.0),   # West Seasoning Yard bark bed
    ]
    decal_count = 0
    if decal_mat:
        for dx, dy, hy_sz, hz_sz, dyaw in decal_specs:
            dc = add_subobject(comp_actor, u.DecalComponent)
            dc.set_mobility(u.ComponentMobility.STATIC)
            dc.set_decal_material(decal_mat)
            dc.set_relative_location_and_rotation(
                u.Vector(dx, dy, ter_z_local(dx, dy) + 1.0),
                u.Rotator(pitch=-90.0, yaw=dyaw, roll=0.0), False, True,
            )
            dc.set_editor_property("decal_size", u.Vector(12.0, hy_sz, hz_sz))
            dc.set_fade_screen_size(0.008)
            dc.set_sort_order(1)
            tag_component(dc, TAG_RESTORED, solid=False)
            decal_count += 1

    # 2) DEDICATED EAST WOOD-CHOPPING & FIREWOOD SPLITTING ZONE
    #    Two distinct 3A weathered, deeply scarred oak chopping stumps + OFFICIAL PROJECT FELLING AXE (SM_BattleAxe)
    #    embedded solidly into each stump's sculpted central V-kerf + 3D scattered bark/woodchip clusters!
    def embed_official_axe_on_stump(stump_x, stump_y, stump_yaw, stump_scale,
                                    kerf_local_xyz, kerf_yaw_local, axe_pitch_deg, axe_roll_deg,
                                    bite_depth_cm=4.8, axe_scale=1.08):
        """Mathematically embed official SM_BattleAxe blade edge (local +10.8, 0, +28.0 cm) deep into stump V-kerf!"""
        if "official_axe" not in sm_cache:
            return
        st_tz = ter_z_local(stump_x, stump_y) - 0.5
        sr = math.radians(stump_yaw)
        cs, sn = math.cos(sr), math.sin(sr)
        kx, ky, kz = kerf_local_xyz
        wx = stump_x + (kx * cs - ky * sn) * stump_scale
        wy = stump_y + (kx * sn + ky * cs) * stump_scale
        wz = st_tz + kz * stump_scale - bite_depth_cm
        axe_rot = u.Rotator(pitch=axe_pitch_deg, yaw=stump_yaw + kerf_yaw_local, roll=axe_roll_deg)
        # Rotate measured blade-center local offset (10.8, 0, 28.0) * axe_scale to solve exact pivot placement!
        blade_local = u.Vector(10.8 * axe_scale, 0.0, 28.0 * axe_scale)
        blade_off = axe_rot.quaternion().rotate_vector(blade_local)
        pivot_loc = u.Vector(wx - blade_off.x, wy - blade_off.y, wz - blade_off.z)
        add_static_axe(pivot_loc.x, pivot_loc.y, pivot_loc.z,
                       pitch=axe_pitch_deg, yaw=stump_yaw + kerf_yaw_local, roll=axe_roll_deg, scale=axe_scale)

    # Chopping Stump A + Official SM_BattleAxe embedded in main V-kerf (rotated cleanly toward yard light for iconic silhouette!)
    place_on_z("chop_stump_a", "hero", 820.0, 420.0, 0.0, yaw=72.0, scale=1.05, embed=0.5, use_terrain=True, pivot_z_at_ground=True)
    embed_official_axe_on_stump(820.0, 420.0, 72.0, 1.05, (6.0, -2.0, 71.2), 18.0, axe_pitch_deg=-124.0, axe_roll_deg=3.5, bite_depth_cm=4.8, axe_scale=1.10)
    place_on_z("bark_chips_a", "chip", 828.0, 432.0, 0.0, yaw=16.0, scale=1.00, embed=0.0, use_terrain=True, pivot_z_at_ground=True)

    # Chopping Stump B (distinct variant with cleft billet!) + 2nd Official SM_BattleAxe embedded in V-kerf (6, -3, 67.2, yaw=-28)
    place_on_z("chop_stump_b", "hero", 1045.0, 515.0, 0.0, yaw=136.0, scale=0.98, embed=0.5, use_terrain=True, pivot_z_at_ground=True)
    embed_official_axe_on_stump(1045.0, 515.0, 136.0, 0.98, (6.0, -3.0, 67.2), -28.0, axe_pitch_deg=-118.0, axe_roll_deg=-3.0, bite_depth_cm=4.6, axe_scale=1.08)
    place_on_z("bark_chips_b", "chip", 1052.0, 505.0, 0.0, yaw=-54.0, scale=1.04, embed=0.0, use_terrain=True, pivot_z_at_ground=True)

    # Secondary chopping block, splitting wedges & corded firewood stacks around splitting area
    place_on_z("chop_block", "medium", 935.0, 315.0, 0.0, yaw=16.0, scale=1.00, embed=1.0, use_terrain=True)
    place_on_z("q_wedge", "clutter", 895.0, 355.0, 0.0, yaw=42.0, scale=1.22, embed=0.4, use_terrain=True)
    place_on_z("q_wedge", "clutter", 975.0, 470.0, 0.0, yaw=-65.0, scale=1.16, embed=0.4, use_terrain=True)
    for fw_x, fw_y, fw_yaw, fw_sc in [
        (765.0, 365.0, 18.0, 2.25), (785.0, 495.0, -42.0, 2.15),
        (985.0, 580.0, 64.0, 2.20), (1120.0, 455.0, -15.0, 2.10),
        (1145.0, 395.0, 32.0, 2.25),
    ]:
        place_on_z("q_firewood", "clutter", fw_x, fw_y, 0.0, yaw=fw_yaw, scale=fw_sc, embed=0.4, use_terrain=True)
    # Organized East Perimeter Cordwood Stacks & Medieval Splitting Supplies (replaced modern mechanic r48_crate with medieval chest!)
    place_on_z("q_logpile1", "hero", 1255.0, 380.0, 0.0, yaw=88.0, scale=1.82, embed=1.0, use_terrain=True)
    place_on_z("q_logpile2", "hero", 1265.0, 620.0, 0.0, yaw=92.0, scale=1.86, embed=1.0, use_terrain=True)
    place_on_z("r48_logpile", "hero", 1120.0, 880.0, 0.0, yaw=-28.0, scale=1.16, embed=1.5, use_terrain=True)
    place_on_z("r48_barrel", "medium", 705.0, 235.0, 0.0, yaw=18.0, scale=0.98, embed=0.8, use_terrain=True)
    # Tuck joiner's chest cleanly under East Sawing Canopy wall (zero optical clutter behind Chopping Stump A!)
    place_on_z("chest", "medium", 590.0, -255.0, 0.0, yaw=0.0, scale=0.92, embed=0.6, use_terrain=True)
    place_on_z("q_rope", "clutter", 718.0, 310.0, 0.0, yaw=-25.0, scale=1.10, embed=0.4, use_terrain=True)
    place_on_z("q_bucket", "clutter", 760.0, 455.0, 0.0, yaw=25.0, scale=0.98, embed=0.4, use_terrain=True)
    place_on_z("r48_wheel", "medium", 1320.0, 505.0, 0.0, yaw=40.0, scale=0.96, embed=1.5, use_terrain=True)

    # 3) DEDICATED WEST TIMBER UNLOADING, LOG-DECK & SEASONING YARD + 3D bark chip scatter
    place_on_z("bark_chips_a", "chip", -895.0, 275.0, 0.0, yaw=-32.0, scale=1.12, embed=0.0, use_terrain=True, pivot_z_at_ground=True)
    place_on_z("bark_chips_b", "chip", -1175.0, -85.0, 0.0, yaw=48.0, scale=1.08, embed=0.0, use_terrain=True, pivot_z_at_ground=True)
    place_on_z("log_stack", "hero", -1240.0, 120.0, 0.0, yaw=86.0, scale=1.10, embed=1.2, use_terrain=True)
    place_on_z("log_stack", "hero", -1250.0, -230.0, 0.0, yaw=92.0, scale=1.06, embed=1.2, use_terrain=True)
    place_on_z("timber_rack", "hero", -1340.0, 500.0, 0.0, yaw=90.0, scale=1.00, embed=1.0, use_terrain=True)
    place_on_z("r48_logpile", "hero", -1180.0, 860.0, 0.0, yaw=26.0, scale=1.16, embed=1.5, use_terrain=True)
    place_on_z("flitches", "hero", -965.0, 565.0, 0.0, yaw=6.0, scale=1.04, embed=0.8, use_terrain=True)
    place_on_z("seasoning", "hero", -745.0, 710.0, 0.0, yaw=-4.0, scale=1.04, embed=0.8, use_terrain=True)
    place_on_z("q_logpile1", "hero", -920.0, 215.0, 0.0, yaw=84.0, scale=1.82, embed=1.0, use_terrain=True)
    place_on_z("q_logpile2", "hero", -885.0, 395.0, 0.0, yaw=12.0, scale=1.86, embed=1.0, use_terrain=True)
    place_on_z("q_plank_stack", "hero", -625.0, 225.0, 0.0, yaw=-4.0, scale=0.80, embed=0.8, use_terrain=True)
    place_on_z("r48_beam", "medium", -1165.0, -470.0, 0.0, yaw=76.0, scale=1.12, embed=1.5, use_terrain=True)
    place_on_z("r48_beam", "medium", -1215.0, -525.0, 0.0, yaw=82.0, scale=1.06, embed=1.5, use_terrain=True)
    place_on_z("shavings", "clutter", -900.0, 145.0, 0.0, yaw=12.0, scale=1.22, embed=0.2, use_terrain=True)
    place_on_z("hewing_chips", "clutter", -735.0, 155.0, 0.0, yaw=-40.0, scale=1.18, embed=0.2, use_terrain=True)

    # 4) Timber Transport Wagons & Wheelbarrows (parked cleanly along loading aprons, leaving 5.5 m driveway wide open!)
    place_on_z("hay_wagon", "hero", 650.0, 845.0, 0.0, yaw=-64.0, scale=1.00, embed=1.2, use_terrain=True)
    place_on_z("hay_wagon", "hero", -655.0, 965.0, 0.0, yaw=118.0, scale=0.96, embed=1.2, use_terrain=True)
    place_on_z("mill_barrow", "medium", -360.0, 155.0, 0.0, yaw=36.0, scale=1.02, embed=1.0, use_terrain=True)
    place_on_z("mill_barrow", "medium", -425.0, 315.0, 0.0, yaw=-28.0, scale=1.00, embed=1.0, use_terrain=True)

    # 5) GRAND SAWMILL CAMP GATEWAY ARCH & CONTINUOUS WEATHERED STABLE-STYLE PERIMETER FENCE (ZERO broken fences / ruined walls!)
    gate_x, gate_y = 0.0, 1220.0
    gate_tz = ter_z_local(gate_x, gate_y)
    place_on_z("camp_gate_arch", "hero", gate_x, gate_y, gate_tz, yaw=0.0, scale=1.00, embed=0.0, pivot_z_at_ground=True)
    # Courtyard guide lamp posts beside main circulation junctions (lanterns hung directly on their hooks in Section 4!)
    yard_lamp_posts = [
        ("YardPost_W", -245.0, -90.0, 22.0),
        ("YardPost_E",  620.0, 145.0, -145.0),
    ]
    for _lp_nm, lpx, lpy, lpyaw in yard_lamp_posts:
        place_on_z("lamp_post", "hero", lpx, lpy, 0.0, yaw=lpyaw, scale=1.00, embed=2.0, use_terrain=True)

    # Continuous 4-sided terrain-following Weathered Stable-Style Camp Fence Enclosure (240 cm mortised oak bays, -55 cm posts!)
    PANEL_BAY_CM = 240.0
    def add_camp_fence_run(p_start, p_end, close_end_post: bool = True):
        x0, y0 = p_start
        x1, y1 = p_end
        dx, dy = x1 - x0, y1 - y0
        total_d = math.hypot(dx, dy)
        n_segs = max(1, int(round(total_d / PANEL_BAY_CM)))
        ux, uy = dx / total_d, dy / total_d
        seg_d = total_d / n_segs
        sx_bay = seg_d / PANEL_BAY_CM
        yaw_f = math.degrees(math.atan2(uy, ux))
        for k in range(n_segs):
            px0, py0 = x0 + ux * (k * seg_d), y0 + uy * (k * seg_d)
            px1, py1 = x0 + ux * ((k + 1) * seg_d), y0 + uy * ((k + 1) * seg_d)
            z0 = ter_z_local(px0, py0)
            z1 = ter_z_local(px1, py1)
            # Pitch panel smoothly along ground grade (clamped +/- 14 deg so posts remain sturdy & natural!)
            pitch_f = max(-14.0, min(14.0, math.degrees(math.atan2(z1 - z0, seg_d))))
            place_on_z("camp_fence_panel", "hero", px0, py0, z0, yaw=yaw_f, pitch=pitch_f,
                       embed=0.0, pivot_z_at_ground=True, scale_xyz=(sx_bay, 1.0, 1.0))
        if close_end_post:
            place_on_z("camp_fence_post", "hero", x1, y1, ter_z_local(x1, y1), yaw=yaw_f,
                       scale=1.0, embed=0.0, pivot_z_at_ground=True)

    # Complete unbroken 4-sided camp perimeter tying flush into both piers of SM_LM_CampGateArch!
    # North-West: (-1540, +1160) -> Gate West Pier (-300, +1220) (Gate pier itself closes the end!)
    add_camp_fence_run((-1540.0, 1160.0), (-300.0, 1220.0), close_end_post=False)
    # North-East: Gate East Pier (+300, +1220) -> (+1540, +1140)
    add_camp_fence_run((300.0, 1220.0), (1540.0, 1140.0), close_end_post=True)
    # East perimeter (102 cm outside Bunkhouse stone chimney!): (+1540, +1140) -> (+1560, -1180)
    add_camp_fence_run((1540.0, 1140.0), (1560.0, -1180.0), close_end_post=True)
    # South perimeter (behind all 3 buildings with clean 160 cm service alley!): (+1560, -1180) -> (-1540, -1180)
    add_camp_fence_run((1560.0, -1180.0), (-1540.0, -1180.0), close_end_post=True)
    # West perimeter (closing cleanly back to NW corner!): (-1540, -1180) -> (-1540, +1160)
    add_camp_fence_run((-1540.0, -1180.0), (-1540.0, 1160.0), close_end_post=False)

    # 6) Natural Forest Clearing Boulders, Felled Stumps & Logs OUTSIDE the Camp Fence Perimeter (SHARED in Ruined & Restored!)
    for bx, by, byaw, bsc in [
        (1780.0, -880.0, 22.0, 0.72),
        (1820.0, 210.0, -48.0, 0.68),
        (1740.0, 1020.0, 110.0, 0.60),
        (1320.0, -1400.0, 65.0, 0.74),
        (-620.0, -1420.0, -30.0, 0.66),
        (-1740.0, -1080.0, 145.0, 0.62),
    ]:
        place_on_z("r48_boulder", "medium", bx, by, 0.0, yaw=byaw, scale=bsc, embed=16.0, use_terrain=True, state_tag=TAG_SHARED)

    for idx_s, (sx, sy, syaw, ssc) in enumerate([
        (-1700.0, 1020.0, 18.0, 1.05),
        (-1760.0, 340.0, 112.0, 0.96),
        (-1780.0, -320.0, -64.0, 1.08),
        (-1420.0, -1380.0, 44.0, 0.98),
        (680.0, -1420.0, -25.0, 1.04),
        (1780.0, -260.0, 80.0, 0.94),
        (1740.0, 680.0, -120.0, 1.02),
        (1120.0, 1380.0, 35.0, 0.92),
        (-980.0, 1380.0, -78.0, 1.00),
    ]):
        place_on_z("r48_stump0" if idx_s % 2 == 0 else "r48_stump1", "medium", sx, sy, 0.0, yaw=syaw, scale=ssc, embed=6.0, use_terrain=True, state_tag=TAG_SHARED)

    for idx_l, (lx, ly, lyaw, lsc) in enumerate([
        (-1800.0, 620.0, 72.0, 0.88),
        (-1420.0, 1380.0, -16.0, 0.84),
        (1340.0, 1340.0, 24.0, 0.86),
        (-1240.0, -1400.0, 14.0, 0.85),
    ]):
        place_on_z("r48_log0" if idx_l % 2 == 0 else "r48_log1", "medium", lx, ly, 0.0, yaw=lyaw, scale=lsc, embed=8.0, use_terrain=True, state_tag=TAG_SHARED)

    # =========================================================================
    # E) RUINED LUMBER MILL STATE (LumberMill.Ruin — Active Before Quest Completion!)
    #    Sagging gate arch, breached monster-smashed fence perimeter, collapsed timber racks,
    #    overturned wagons/barrows, scattered logs/rubble, dark cold interiors (ZERO lanterns/lights!),
    #    preserving clear combat lanes & all 7 monster spawn zones!
    # =========================================================================
    # 1) Sagging Ruined Camp Gate Arch (no lanterns!)
    place_on_z("ruin_gate_arch", "hero", gate_x, gate_y, gate_tz, yaw=0.0, scale=1.00, embed=0.0, pivot_z_at_ground=True, state_tag=TAG_RUIN)

    # 2) Breached & Broken Camp Perimeter Fence (alternating broken bays, leaning panels & 3 open monster breaches!)
    def add_ruined_fence_run(p_start, p_end, breach_indices=(), broken_indices=(), close_end_post: bool = True):
        x0, y0 = p_start
        x1, y1 = p_end
        dx, dy = x1 - x0, y1 - y0
        total_d = math.hypot(dx, dy)
        n_segs = max(1, int(round(total_d / PANEL_BAY_CM)))
        ux, uy = dx / total_d, dy / total_d
        seg_d = total_d / n_segs
        sx_bay = seg_d / PANEL_BAY_CM
        yaw_f = math.degrees(math.atan2(uy, ux))
        for k in range(n_segs):
            if k in breach_indices:
                continue
            px0, py0 = x0 + ux * (k * seg_d), y0 + uy * (k * seg_d)
            px1, py1 = x0 + ux * ((k + 1) * seg_d), y0 + uy * ((k + 1) * seg_d)
            z0, z1 = ter_z_local(px0, py0), ter_z_local(px1, py1)
            pitch_f = max(-14.0, min(14.0, math.degrees(math.atan2(z1 - z0, seg_d))))
            next_is_breach = ((k + 1) in breach_indices)
            if k in broken_indices or next_is_breach:
                # Self-supporting broken bay (ZERO floating right-hand rails next to breaches or gate!)
                place_on_z("ruin_fence_panel", "hero", px0, py0, z0, yaw=yaw_f, pitch=pitch_f,
                           embed=2.0, pivot_z_at_ground=True, scale_xyz=(sx_bay, 1.0, 1.0), state_tag=TAG_RUIN)
            else:
                roll_lean = (5.0 if k % 2 == 0 else -4.5)
                place_on_z("camp_fence_panel", "hero", px0, py0, z0, yaw=yaw_f, pitch=pitch_f, roll=roll_lean,
                           embed=2.0, pivot_z_at_ground=True, scale_xyz=(sx_bay, 1.0, 1.0), state_tag=TAG_RUIN)
        if close_end_post:
            place_on_z("camp_fence_post", "hero", x1, y1, ter_z_local(x1, y1), yaw=yaw_f, roll=4.5,
                       scale=1.0, embed=2.0, pivot_z_at_ground=True, state_tag=TAG_RUIN)

    add_ruined_fence_run((-1540.0, 1160.0), (-300.0, 1220.0), breach_indices=(2,), broken_indices=(1, 3, 4), close_end_post=False)
    add_ruined_fence_run((300.0, 1220.0), (1540.0, 1140.0), breach_indices=(1,), broken_indices=(0, 2, 4), close_end_post=True)
    add_ruined_fence_run((1540.0, 1140.0), (1560.0, -1180.0), breach_indices=(2, 6), broken_indices=(1, 3, 5, 7, 8), close_end_post=True)
    add_ruined_fence_run((1560.0, -1180.0), (-1540.0, -1180.0), breach_indices=(5,), broken_indices=(1, 3, 6, 8, 10, 11), close_end_post=True)
    add_ruined_fence_run((-1540.0, -1180.0), (-1540.0, 1160.0), breach_indices=(4,), broken_indices=(0, 2, 5, 7, 8), close_end_post=False)

    # 3) Ruined Interiors (broken racks, toppled chests/barrels/furniture, cold dead hearth — ZERO lights or fresh food!)
    place_on_z("ruin_timber_rack", "hero", -945.0, -765.0, FL1, yaw=90.0, scale=0.96, embed=0.2, state_tag=TAG_RUIN)
    place_on_z("ruin_timber_rack", "hero", -760.0, -942.0, FL1, yaw=4.0, scale=0.96, embed=0.2, state_tag=TAG_RUIN)
    place_on_z("r48_barrel", "medium", -925.0, -525.0, FL1, yaw=35.0, pitch=86.0, scale=0.95, embed=1.5, state_tag=TAG_RUIN)
    place_on_z("chest", "medium", -865.0, -420.0, FL1, yaw=-32.0, roll=22.0, scale=0.94, embed=1.2, state_tag=TAG_RUIN)
    place_on_z("q_logpile1", "hero", -195.0, -895.0, FL1, yaw=102.0, scale=1.55, embed=0.5, state_tag=TAG_RUIN)
    place_on_z("rubble_b", "clutter", -450.0, -860.0, FL1, yaw=22.0, scale=0.88, embed=0.0, pivot_z_at_ground=True, state_tag=TAG_RUIN)
    place_on_z("rubble_a", "clutter", -210.0, -455.0, FL1, yaw=-40.0, scale=0.82, embed=0.0, pivot_z_at_ground=True, state_tag=TAG_RUIN)
    # ToolRoom interior ruined clutter
    place_on_z("offcut_crib", "medium", 570.0, -915.0, FL1, yaw=-74.0, scale=0.92, embed=0.3, state_tag=TAG_RUIN)
    place_on_z("wash_barrel", "medium", 565.0, -540.0, FL1, yaw=42.0, pitch=84.0, scale=0.92, embed=1.5, state_tag=TAG_RUIN)
    place_on_z("rubble_b", "clutter", 210.0, -520.0, FL1, yaw=55.0, scale=0.78, embed=0.0, pivot_z_at_ground=True, state_tag=TAG_RUIN)
    # Bunkhouse 1F & 2F overturned furnishings
    place_on_z("tavern_table", "medium", 945.0, -515.0, FL1, yaw=14.0, roll=16.0, scale=0.95, embed=1.2, state_tag=TAG_RUIN)
    place_on_z("q_chair", "medium", 820.0, -460.0, FL1, yaw=115.0, pitch=82.0, scale=0.96, embed=1.5, state_tag=TAG_RUIN)
    place_on_z("cupboard", "medium", 830.0, -242.0, FL1, yaw=166.0, scale=0.90, embed=0.3, state_tag=TAG_RUIN)
    place_on_z("bunk_bed", "hero", 772.0, -565.0, FL2, yaw=96.0, scale=0.98, embed=0.2, state_tag=TAG_RUIN)
    place_on_z("timber_bed", "hero", 1250.0, -310.0, FL2, yaw=-78.0, scale=0.98, embed=0.2, state_tag=TAG_RUIN)
    place_on_z("oak_table", "medium", 1045.0, -260.0, FL2, yaw=22.0, roll=-14.0, scale=0.92, embed=1.2, state_tag=TAG_RUIN)
    place_on_z("rubble_b", "clutter", 900.0, -430.0, FL2, yaw=-35.0, scale=0.75, embed=0.0, pivot_z_at_ground=True, state_tag=TAG_RUIN)

    # 4) Ruined Yard Dressing (overturned wagons/carts, spilled timber, weathered stumps without axes, rubble mounds —
    #    ALL positioned cleanly away from the 7 monster spawns: (120,320), (-560,220), (780,140), (-120,860), (380,820), (-820,560), (920,540)!)
    # Overturned hay wagon in NW yard & tilted wreck in SE chopping yard (exact rotated-AABB seated cleanly into yard mud!)
    place_on_z("hay_wagon", "hero", -1160.0, 880.0, 0.0, yaw=132.0, roll=48.0, pitch=6.0, scale=0.96, embed=5.0, use_terrain=True, state_tag=TAG_RUIN)
    place_on_z("hay_wagon", "hero", 1295.0, 935.0, 0.0, yaw=-48.0, roll=-52.0, pitch=-8.0, scale=0.92, embed=5.0, use_terrain=True, state_tag=TAG_RUIN)
    place_on_z("mill_barrow", "medium", -340.0, 40.0, 0.0, yaw=64.0, roll=112.0, scale=1.00, embed=3.5, use_terrain=True, state_tag=TAG_RUIN)
    # Broken outdoor timber rack & tumbled log piles on West apron
    place_on_z("ruin_timber_rack", "hero", -1340.0, 480.0, 0.0, yaw=84.0, scale=1.00, embed=1.0, use_terrain=True, state_tag=TAG_RUIN)
    place_on_z("log_stack", "hero", -1255.0, -180.0, 0.0, yaw=96.0, scale=1.04, embed=1.5, use_terrain=True, state_tag=TAG_RUIN)
    place_on_z("r48_logpile", "hero", -1190.0, 220.0, 0.0, yaw=38.0, scale=1.14, embed=2.0, use_terrain=True, state_tag=TAG_RUIN)
    place_on_z("r48_beam", "medium", -1040.0, 140.0, 0.0, yaw=62.0, scale=1.10, embed=2.5, use_terrain=True, state_tag=TAG_RUIN)
    place_on_z("r48_wheel", "medium", -920.0, 820.0, 0.0, yaw=22.0, pitch=72.0, scale=0.96, embed=3.5, use_terrain=True, state_tag=TAG_RUIN)
    # East abandoned chopping stumps (weathered stumps WITHOUT official player axes, plus spilled firewood & overturned barrels!)
    place_on_z("r48_stump0", "medium", 1220.0, 380.0, 0.0, yaw=40.0, scale=1.08, embed=5.0, use_terrain=True, state_tag=TAG_RUIN)
    place_on_z("r48_stump1", "medium", 1265.0, 565.0, 0.0, yaw=-75.0, scale=1.02, embed=5.0, use_terrain=True, state_tag=TAG_RUIN)
    place_on_z("r48_barrel", "medium", 1160.0, 240.0, 0.0, yaw=-28.0, pitch=86.0, scale=0.96, embed=3.5, use_terrain=True, state_tag=TAG_RUIN)
    place_on_z("r48_log0", "medium", 1280.0, 160.0, 0.0, yaw=18.0, scale=0.90, embed=5.0, use_terrain=True, state_tag=TAG_RUIN)
    place_on_z("q_firewood", "clutter", 1140.0, 440.0, 0.0, yaw=28.0, scale=2.15, embed=0.8, use_terrain=True, state_tag=TAG_RUIN)
    place_on_z("q_firewood", "clutter", 1190.0, 650.0, 0.0, yaw=-52.0, scale=2.05, embed=0.8, use_terrain=True, state_tag=TAG_RUIN)
    place_on_z("bark_chips_a", "chip", 1200.0, 440.0, 0.0, yaw=12.0, scale=1.05, embed=0.0, use_terrain=True, pivot_z_at_ground=True, state_tag=TAG_RUIN)
    place_on_z("bark_chips_b", "chip", -1020.0, 260.0, 0.0, yaw=-44.0, scale=1.10, embed=0.0, use_terrain=True, pivot_z_at_ground=True, state_tag=TAG_RUIN)
    # Grounded architectural rubble piles around ruined roofs, canopy collapse & fence breaches (NoCollision clutter so AI never snags!)
    for rb_key, rbx, rby, rbyaw, rbsc in [
        ("rubble_a", -240.0, -255.0,  18.0, 1.00),  # Front-east Warehouse collapse debris
        ("rubble_b", -960.0, -240.0, -32.0, 0.94),  # Front-west Warehouse rubble
        ("rubble_a",  580.0,  -20.0,  42.0, 1.05),  # Collapsed East Sawing Canopy debris
        ("rubble_b", 1265.0,  -95.0, -18.0, 0.96),  # Bunkhouse East porch collapse debris
        ("rubble_b", -880.0, 1140.0,  64.0, 0.92),  # NW fence breach debris
        ("rubble_a",  640.0, 1130.0, -48.0, 0.96),  # NE fence breach debris
        ("rubble_b", 1460.0,  580.0,  82.0, 0.90),  # East fence breach debris
    ]:
        place_on_z(rb_key, "clutter", rbx, rby, 0.0, yaw=rbyaw, scale=rbsc, embed=4.0, use_terrain=True, pivot_z_at_ground=True, state_tag=TAG_RUIN)

    # 3) Create One HISM Component per (state_tag, mesh_key, tier) — dual-state switching + ultra-low draw calls!
    hism_count = 0
    inst_total = 0
    by_mesh_counts = {}
    for (state_tag, key, tier), tfs in sorted(hism_buckets.items()):
        sm = sm_cache[key]
        cfg = TIER_CFG[tier]
        hc = add_subobject(comp_actor, u.HierarchicalInstancedStaticMeshComponent)
        hc.set_mobility(u.ComponentMobility.STATIC)
        hc.set_static_mesh(sm)
        hc.set_cull_distances(cfg["cull_start"], cfg["cull_end"])
        hc.set_cast_shadow(cfg["shadow"])
        hc.set_editor_property("can_ever_affect_navigation", cfg["nav"])
        hc.set_editor_property("affect_distance_field_lighting", cfg["df"])
        hc.set_editor_property("affect_dynamic_indirect_lighting", False)
        hc.set_editor_property("visible_in_ray_tracing", False)
        hc.set_editor_property("receives_decals", False)
        hc.set_editor_property("generate_overlap_events", False)
        hc.add_instances(tfs, False, False, False)
        tag_component(hc, state_tag, solid=(cfg["col"] == "BlockAll"))
        hism_count += 1
        inst_total += len(tfs)
        short_st = state_tag.split(".")[-1]
        by_mesh_counts[f"{short_st}:{key}({tier})"] = len(tfs)

    # 4) VILLAGE SHOP CHAIN-HUNG PENDANTS, WALL-BRACKET LAMPS & EXACT UVillageInteriorLighting STANDARD!
    #    Zero floating lamps! Every hanging lantern physically rivets to roof tie-beams / rafters / walls / gate arms
    #    via stable_lighting.py (forged iron plate + drop rod/bracket + SM_ChainLink01a chain + SM_Props_Lantern_02A
    #    with MI_StaffLampWick + UVillageInteriorLighting::Configure -> InverseExposureBlend=1.0, exact Shop brightness/color!).
    subs = u.get_engine_subsystem(u.SubobjectDataSubsystem)
    sdata = u.SubobjectDataBlueprintFunctionLibrary
    parent_h = subs.k2_gather_subobject_data_for_instance(comp_actor)[0]
    lantern_mesh = u.load_asset(shop_lights.LANTERN_MESH)
    wick_mat = u.load_asset(SHOP_WICK_MAT)
    chain_mesh = u.load_asset(shop_lights.CHAIN_MESH)
    if not (lantern_mesh and wick_mat and chain_mesh):
        raise RuntimeError("Missing Village Shop lighting assets (Lantern / MI_StaffLampWick / SM_ChainLink01a)")
    chain_box = chain_mesh.get_bounding_box()
    iron_poses, chain_poses = [], []
    lamp_audit = []

    def add_beam_pendant(name, x, y, soffit_z, bottom_z, height_cm, yaw_deg, level_mul, radius_cm, draw_dist=2400.0):
        shop_lights.append_pendant_hardware(
            iron_poses, chain_poses, chain_box, x, y, soffit_z, bottom_z + height_cm, yaw_deg=yaw_deg
        )
        info = shop_lights.add_lantern_and_light(
            subs, sdata, parent_h, lantern_mesh, wick_mat,
            x, y, bottom_z, height_cm, yaw_deg=yaw_deg,
            level=level_mul, draw_dist=draw_dist, attenuation_radius=radius_cm, cull_dist=2600.0,
        )
        lamp_audit.append({"name": name, "mount": "beam_pendant", "soffit_z": soffit_z, **info})

    def add_wall_chain_lamp(name, wx, wy, dx, dy, arm_z, reach_cm, bottom_z, height_cm, yaw_deg, level_mul, radius_cm, draw_dist=2400.0):
        hx, hy = shop_lights.append_wall_bracket_hardware(
            iron_poses, chain_poses, chain_box, wx, wy, dx, dy, arm_z, reach_cm, bottom_z + height_cm, brace_drop_cm=16.0
        )
        info = shop_lights.add_lantern_and_light(
            subs, sdata, parent_h, lantern_mesh, wick_mat,
            hx, hy, bottom_z, height_cm, yaw_deg=yaw_deg,
            level=level_mul, draw_dist=draw_dist, attenuation_radius=radius_cm, cull_dist=2600.0,
        )
        lamp_audit.append({"name": name, "mount": "wall_bracket", "xy": [round(hx, 1), round(hy, 1)], **info})

    def add_seated_lantern(name, x, y, surface_z, height_cm, yaw_deg, level_mul, radius_cm, draw_dist=2200.0):
        info = shop_lights.add_lantern_and_light(
            subs, sdata, parent_h, lantern_mesh, wick_mat,
            x, y, surface_z, height_cm, yaw_deg=yaw_deg,
            level=level_mul, draw_dist=draw_dist, attenuation_radius=radius_cm, cull_dist=2400.0,
        )
        lamp_audit.append({"name": name, "mount": "table_seated", "xy": [round(x, 1), round(y, 1)], **info})

    # 4a) Warehouse Twin Roof Tie-Beam Pendants (bolted flush to WH_Roof_Tie_1 & WH_Roof_Tie_2 soffit Z=335+DZ_BLDG!)
    WH_TIE_Z = 335.0 + DZ_BLDG
    add_beam_pendant("WH_Pendant_W", -670.7, -670.0, WH_TIE_Z, WH_TIE_Z - 77.0, 34.0, 0.0, 0.72, 760.0)
    add_beam_pendant("WH_Pendant_E", -369.3, -670.0, WH_TIE_Z, WH_TIE_Z - 77.0, 34.0, 0.0, 0.72, 760.0)

    # 4b) Tool Room Central Tie-Beam Pendant (TR_Roof_Tie_1 soffit) + South Wall Bracket on solid plaster beside Workbench!
    add_beam_pendant("TR_Pendant_Center", 340.0, -670.0, WH_TIE_Z, WH_TIE_Z - 79.0, 34.0, 0.0, 0.76, 720.0)
    add_wall_chain_lamp("TR_BenchBracket", 228.0, -996.0, 0.0, 1.0, 232.0 + DZ_BLDG, 30.0, 174.0 + DZ_BLDG, 30.0, 0.0, 0.48, 520.0)

    # 4c) Sawing Canopy Central Rafter Pendant (bolted flush to Can_Raf_0 soffit Z=262.1+DZ_BLDG at Y=-165!)
    CAN_RAF_Z = 262.1 + DZ_BLDG
    add_beam_pendant("Canopy_Pendant", 340.0, -165.0, CAN_RAF_Z, CAN_RAF_Z - 56.0, 32.0, 90.0, 0.68, 660.0)

    # 4d) Bunkhouse 1F: Foyer West-Wall Chain Bracket + Dining Table Seated Lantern + Dressed Stone Hearth Ember Light!
    add_wall_chain_lamp("BH1F_FoyerBracket", 704.0, -380.0, 1.0, 0.0, 232.0 + DZ_BLDG, 32.0, 174.0 + DZ_BLDG, 32.0, 90.0, 0.66, 660.0)
    add_seated_lantern("BH1F_TableLantern", 974.0, -510.0, FL1 + 78.0, 28.0, 15.0, 0.48, 520.0)
    # Hearth firelight (reuses VillageInteriorLighting standard with warm ember tint & InverseExposureBlend=1.0!)
    hearth_pl = add_subobject(comp_actor, u.PointLightComponent)
    hearth_pl.set_mobility(u.ComponentMobility.MOVABLE)
    hearth_pl.set_relative_location(u.Vector(1340.0, -630.0, FL1 + 36.0), False, True)
    u.VillageInteriorLighting.configure(hearth_pl, 0.52)
    hearth_pl.set_light_color(u.LinearColor(1.0, 0.54, 0.22, 1.0))
    hearth_pl.set_editor_property("attenuation_radius", 440.0)
    hearth_pl.set_editor_property("max_draw_distance", 2200.0)
    hearth_pl.set_editor_property("max_distance_fade_range", 450.0)
    hearth_pl.set_cast_shadows(False)
    lamp_audit.append({"name": "BH1F_HearthEmber", "mount": "hearth_firebox", "xy": [1340.0, -630.0], "light_z": round(FL1 + 36.0, 1)})

    # 4e) Bunkhouse 2F: Collar-Beam Ceiling Pendant (bolted flush to BH_Roof_Col_2 soffit Z=582.5+DZ_BLDG at Y=-468!) + Seated Desk Lantern!
    BH2_COL_Z = 582.5 + DZ_BLDG
    add_beam_pendant("BH2F_DormPendant", 1040.0, -468.0, BH2_COL_Z, BH2_COL_Z - 76.5, 34.0, 0.0, 0.76, 740.0)
    add_seated_lantern("BH2F_DeskLantern", 1060.0, -250.0, FL2 + 78.0, 26.0, -10.0, 0.34, 380.0)

    # 4f) Camp Gate Arch Twin Forged-Chain Lanterns (hanging directly from GA_LEye rings at Z = gate_tz + 327.0!)
    c_len = max(1.0, float(chain_box.max.x - chain_box.min.x))
    c_mid = u.Vector(
        0.5 * (float(chain_box.min.x) + float(chain_box.max.x)),
        0.5 * (float(chain_box.min.y) + float(chain_box.max.y)),
        0.5 * (float(chain_box.min.z) + float(chain_box.max.z)),
    )
    c_pivot = u.Transform(location=-c_mid)
    for gside, gx_l in (("W", -292.0), ("E", 292.0)):
        eye_z = gate_tz + 327.0
        crown_z = gate_tz + 314.0
        bot_z = crown_z - 36.0
        sc_ch = 15.0 / c_len
        chain_poses.append(u.MathLibrary.compose_transforms(
            c_pivot,
            u.Transform(
                location=u.Vector(gx_l, gate_y + 44.0, 0.5 * (eye_z + crown_z)),
                rotation=u.Rotator(pitch=90.0, yaw=0.0),
                scale=u.Vector(sc_ch, sc_ch, sc_ch),
            ),
        ))
        info = shop_lights.add_lantern_and_light(
            subs, sdata, parent_h, lantern_mesh, wick_mat,
            gx_l, gate_y + 44.0, bot_z, 36.0, yaw_deg=0.0,
            level=0.76, draw_dist=2800.0, attenuation_radius=720.0, cull_dist=3200.0,
        )
        lamp_audit.append({"name": f"GateArch_Lantern_{gside}", "mount": "gate_iron_eye_chain", "xy": [gx_l, gate_y + 44.0], **info})

    # 4g) Courtyard Lamp Post Hook Lanterns (hung directly on SM_Stable_YardLampPost forged hooks!)
    for lp_nm, lpx, lpy, lpyaw in yard_lamp_posts:
        rad = math.radians(lpyaw)
        hx = lpx + 36.0 * math.cos(rad)
        hy = lpy + 36.0 * math.sin(rad)
        tz_lp = ter_z_local(lpx, lpy) - 2.0
        hook_z = tz_lp + 232.0
        lh = 32.0
        info = shop_lights.add_lantern_and_light(
            subs, sdata, parent_h, lantern_mesh, wick_mat,
            hx, hy, hook_z - lh, lh, yaw_deg=lpyaw,
            level=0.68, draw_dist=2600.0, attenuation_radius=660.0, cull_dist=3000.0,
        )
        lamp_audit.append({"name": lp_nm + "_Lantern", "mount": "yard_lamp_post_hook", "xy": [round(hx, 1), round(hy, 1)], **info})

    # Batch all forged iron mounting plates/rods/brackets & chain links into 2 ultra-cheap static ISMs (cull 26 m)!
    iron_ism = shop_lights.make_iron_hardware_ism(subs, sdata, parent_h, cull_distance=2600.0)
    iron_ism.add_instances(iron_poses, False, False, False)
    chain_ism = shop_lights.make_chain_ism(subs, sdata, parent_h, cull_distance=2600.0)
    chain_ism.add_instances(chain_poses, False, False, False)

    # Tag ALL lamp lanterns, PointLightComponents, iron & chain hardware as LumberMill.Restored (hidden in Ruined state!)
    for sc in comp_actor.get_components_by_class(u.SceneComponent):
        if sc == comp_actor.root_component:
            continue
        ctags = set(map(str, sc.get_editor_property("component_tags")))
        if not (ctags & {TAG_RUIN, TAG_RESTORED, TAG_SHARED}):
            tag_component(sc, TAG_RESTORED, solid=False)

    # 5) AUTOMATED DUAL-STATE DOORWAY, STAIRCASE, 7-MONSTER SPAWN WALKABILITY, MATERIAL USAGE & ZERO-FLOATING GROUND AUDIT!
    walk_audit = audit_compound_walkability(comp_actor, buildings, dz_bldg=DZ_BLDG)
    mat_audit = audit_compound_material_usage(comp_actor)
    floating_props = [row for row in grounding_audit if (not row["mounted"]) and row["gap_cm"] > 1.5]
    ground_summary = {
        "total_checked": len(grounding_audit),
        "floating_count": len(floating_props),
        "max_gap_cm": max((row["gap_cm"] for row in grounding_audit if not row["mounted"]), default=0.0),
        "floating_examples": floating_props[:12],
    }
    print(f"[COMPOUND] LumberMill_Compound (Dual-State): 3+3 buildings (+{DZ_BLDG:.0f}cm) + {hism_count} HISMs ({inst_total} props) + {decal_count} decals + {len(lamp_audit)} restored lamps")
    print("[GROUNDING]", json.dumps(ground_summary, indent=2))
    print("[WALKABILITY]", json.dumps(walk_audit, indent=2))
    print("[MATERIAL_USAGE]", json.dumps(mat_audit, indent=2))
    if floating_props:
        raise RuntimeError("ZERO-FLOATING GROUND AUDIT FAILED: " + json.dumps(floating_props[:10]))
    if not walk_audit["all_clear"]:
        raise RuntimeError("DOORWAY/STAIR/SPAWN WALKABILITY AUDIT FAILED: " + json.dumps(walk_audit["blockers"]))
    if not mat_audit["all_clear"]:
        raise RuntimeError("MATERIAL USAGE AUDIT FAILED (WHITE/MISSING/UNSUPPORTED HISM MATERIAL): " + json.dumps(mat_audit["issues"]))
    return {
        "buildings_restored": 3,
        "buildings_ruined": 3,
        "hism_components": hism_count,
        "prop_instances": inst_total,
        "woodchip_decals": decal_count,
        "practical_lights": len(lamp_audit),
        "lamp_hardware_instances": {"iron": len(iron_poses), "chain": len(chain_poses)},
        "grounding_audit": ground_summary,
        "walkability_audit": walk_audit,
        "material_usage_audit": mat_audit,
        "by_mesh": by_mesh_counts,
    }


def audit_compound_material_usage(comp_actor):
    """Verify ZERO null/WorldGrid/Default materials and ZERO HISM or Nanite usage-flag mismatches on LumberMill_Compound."""
    issues = []
    checked_comps = 0
    checked_slots = 0
    for smc in comp_actor.get_components_by_class(u.StaticMeshComponent):
        sm = smc.static_mesh
        if not sm:
            continue
        checked_comps += 1
        is_hism = isinstance(smc, u.InstancedStaticMeshComponent)
        nanite_on = bool(sm.get_editor_property("nanite_settings").enabled)
        n_mats = max(smc.get_num_materials(), len(sm.get_editor_property("static_materials")))
        for idx in range(n_mats):
            checked_slots += 1
            mi = smc.get_material(idx)
            if not mi:
                issues.append({"comp": smc.get_name(), "mesh": sm.get_name(), "slot": idx, "err": "NULL_MATERIAL"})
                continue
            mpath = mi.get_path_name()
            if "WorldGridMaterial" in mpath or "DefaultMaterial" in mpath:
                issues.append({"comp": smc.get_name(), "mesh": sm.get_name(), "slot": idx, "err": "DEFAULT_GRID_MATERIAL", "mat": mpath})
                continue
            base = mi.get_base_material() if isinstance(mi, u.MaterialInstance) else mi
            if isinstance(base, u.Material):
                if is_hism and not bool(base.get_editor_property("used_with_instanced_static_meshes")):
                    issues.append({"comp": smc.get_name(), "mesh": sm.get_name(), "slot": idx, "err": "MISSING_USED_WITH_ISM", "base": base.get_path_name()})
                if nanite_on and not bool(base.get_editor_property("used_with_nanite")):
                    issues.append({"comp": smc.get_name(), "mesh": sm.get_name(), "slot": idx, "err": "MISSING_USED_WITH_NANITE", "base": base.get_path_name()})
    return {
        "all_clear": len(issues) == 0,
        "checked_components": checked_comps,
        "checked_slots": checked_slots,
        "issues": issues,
    }


def _aabb_overlap(a0, a1, b0, b1):
    return (a0[0] < b1[0] and a1[0] > b0[0] and
            a0[1] < b1[1] and a1[1] > b0[1] and
            a0[2] < b1[2] and a1[2] > b0[2])


def _kbox_aabb_in_yard(bx_elem, bldg_xyz):
    """Conservative tight AABB of a KBoxElem (including yaw/pitch/roll rotation!) in LumberMill_Compound local cm."""
    c = bx_elem.get_editor_property("center")
    hx = float(bx_elem.get_editor_property("x")) * 0.5
    hy = float(bx_elem.get_editor_property("y")) * 0.5
    hz = float(bx_elem.get_editor_property("z")) * 0.5
    rot = bx_elem.get_editor_property("rotation")
    pitch_r = math.radians(float(rot.pitch))
    yaw_r = math.radians(float(rot.yaw))
    roll_r = math.radians(float(rot.roll))
    # Rotate all 8 corners of the local KBoxElem box
    cp, sp = math.cos(pitch_r), math.sin(pitch_r)
    cy, sy = math.cos(yaw_r), math.sin(yaw_r)
    cr, sr = math.cos(roll_r), math.sin(roll_r)
    xs, ys, zs = [], [], []
    for sx in (-hx, hx):
        for sy_c in (-hy, hy):
            for sz in (-hz, hz):
                # Roll (X) -> Pitch (Y) -> Yaw (Z)
                y1 = sy_c * cr - sz * sr
                z1 = sy_c * sr + sz * cr
                x2 = sx * cp + z1 * sp
                z2 = -sx * sp + z1 * cp
                x3 = x2 * cy - y1 * sy
                y3 = x2 * sy + y1 * cy
                xs.append(bldg_xyz[0] + float(c.x) + x3)
                ys.append(bldg_xyz[1] + float(c.y) + y3)
                zs.append(bldg_xyz[2] + float(c.z) + z2)
    return (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))


def audit_compound_walkability(comp_actor, buildings, dz_bldg=18.0):
    """Verify ZERO cooked Chaos KBoxElem or Solid HISM collider obstructs ANY doorway/stair in Restored OR Ruined state,
    and verify ALL 7 quest monster spawn capsules are 100% clear in Ruined state!"""
    def collect_state_boxes(state_tag: str):
        bldg_boxes, prop_boxes, bldg_counts = [], [], {}
        smcs = [c for c in comp_actor.get_components_by_class(u.StaticMeshComponent)
                if not isinstance(c, u.InstancedStaticMeshComponent)]
        for smc in smcs:
            ctags = set(map(str, smc.get_editor_property("component_tags")))
            if "LumberMill.Solid" not in ctags or not (ctags & {state_tag, "LumberMill.Shared"}):
                continue
            sm = smc.static_mesh
            if not sm or not sm.get_name().startswith("SM_LM_"):
                continue
            loc = smc.get_editor_property("relative_location")
            bxyz = (float(loc.x), float(loc.y), float(loc.z))
            body = sm.get_editor_property("body_setup")
            elems = list(body.get_editor_property("agg_geom").get_editor_property("box_elems")) if body else []
            bldg_counts[sm.get_name()] = len(elems)
            for ei, be in enumerate(elems):
                a0, a1 = _kbox_aabb_in_yard(be, bxyz)
                bldg_boxes.append((f"{sm.get_name()}[{ei}]", a0, a1))

        for hc in comp_actor.get_components_by_class(u.HierarchicalInstancedStaticMeshComponent):
            ctags = set(map(str, hc.get_editor_property("component_tags")))
            if "LumberMill.Solid" not in ctags or not (ctags & {state_tag, "LumberMill.Shared"}):
                continue
            sm = hc.static_mesh
            if not sm:
                continue
            bb = sm.get_bounding_box()
            corners = [
                u.Vector(x, y, z)
                for x in (bb.min.x, bb.max.x)
                for y in (bb.min.y, bb.max.y)
                for z in (bb.min.z, bb.max.z)
            ]
            for idx in range(hc.get_instance_count()):
                tf = hc.get_instance_transform(idx, world_space=False)
                pts = [tf.transform_location(p) for p in corners]
                a0 = (min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))
                a1 = (max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts))
                prop_boxes.append((f"{sm.get_name()}#{idx}", a0, a1))
        return bldg_boxes, prop_boxes, bldg_counts

    z1_lo, z1_hi = 22.0 + dz_bldg, 214.0 + dz_bldg
    z2_lo, z2_hi = 318.0 + dz_bldg, 502.0 + dz_bldg
    corridors = [
        ("WH_FrontDoor",   (-564.0, -430.0, z1_lo), (-476.0, -210.0, z1_hi)),
        ("WH_to_TR_Door",  (-110.0, -754.0, z1_lo), (110.0,  -666.0, z1_hi)),
        ("TR_FrontDoor",   (296.0,  -430.0, z1_lo), (384.0,  -210.0, z1_hi)),
        ("TR_to_BH_Door",  (570.0,  -739.0, z1_lo), (790.0,  -651.0, z1_hi)),
        ("BH_FrontDoor",   (996.0,  -290.0, z1_lo), (1084.0, -50.0,  z1_hi)),
        ("BH_StairFoot",   (760.0,  -972.0, z1_lo), (822.0,  -888.0, z1_hi)),
        ("BH_StairLand2F", (1270.0, -972.0, z2_lo), (1355.0, -888.0, z2_hi)),
    ]
    for k in range(16):
        sx = 1040.0 + (-215.0 + (k + 0.5) * (440.0 / 16.0))
        sz_top = 16.0 + dz_bldg + (k + 1.0) * (296.0 / 16.0)
        corridors.append((f"BH_StairHead_{k}", (sx - 12.0, -972.0, sz_top + 24.0), (sx + 12.0, -888.0, sz_top + 196.0)))

    # 7 Monster spawn clearances in Ruined state (generous safety radius around each spawn!)
    monster_spawns = [
        ("Spawn_Witch_0",     (-560.0, 220.0), 90.0, 190.0),
        ("Spawn_Witch_1",     (780.0,  140.0), 90.0, 190.0),
        ("Spawn_Dog_0",       (-120.0, 860.0), 95.0, 140.0),
        ("Spawn_Dog_1",       (380.0,  820.0), 95.0, 140.0),
        ("Spawn_Dog_2",       (-820.0, 560.0), 95.0, 140.0),
        ("Spawn_Dog_3",       (920.0,  540.0), 95.0, 140.0),
        ("Spawn_HandBrain_0", (120.0,  320.0), 140.0, 220.0),
    ]

    blockers = []
    all_bldg_counts = {}
    prop_counts = {}
    for st_name, st_tag in (("Restored", "LumberMill.Restored"), ("Ruined", "LumberMill.Ruin")):
        b_boxes, p_boxes, b_cnt = collect_state_boxes(st_tag)
        all_bldg_counts.update(b_cnt)
        prop_counts[st_name] = len(p_boxes)
        boxes = b_boxes + p_boxes
        for cname, c0, c1 in corridors:
            for bname, b0, b1 in boxes:
                if _aabb_overlap(c0, c1, b0, b1):
                    blockers.append({"state": st_name, "corridor": cname, "blocker": bname,
                                     "box_min": [round(v, 1) for v in b0], "box_max": [round(v, 1) for v in b1]})
        if st_name == "Ruined":
            for mname, (mx, my), mr, mh in monster_spawns:
                c0 = (mx - mr, my - mr, 10.0)
                c1 = (mx + mr, my + mr, 10.0 + mh)
                for bname, b0, b1 in boxes:
                    if _aabb_overlap(c0, c1, b0, b1):
                        blockers.append({"state": "Ruined", "corridor": mname, "blocker": bname,
                                         "box_min": [round(v, 1) for v in b0], "box_max": [round(v, 1) for v in b1]})
    return {
        "all_clear": len(blockers) == 0,
        "tested_corridors_per_state": len(corridors),
        "tested_monster_spawns": len(monster_spawns),
        "building_kbox_counts": all_bldg_counts,
        "blockall_prop_instances": prop_counts,
        "blockers": blockers,
    }


def audit_lumber_assets_vram():
    """Verify 100% Nanite, 100% <=1024/512/256 texture caps, zero NeverStream, and estimate total LumberMill VRAM MB."""
    lm_dir = "/Game/ForestPathStudy/VillageRegion/LumberMill"
    nanite_ok = 0
    nanite_fail = 0
    tex_total = 0
    tex_uncapped = 0
    vram_bytes = 0
    for apath in sorted(lib.list_assets(lm_dir, recursive=True, include_folder=False)):
        obj = u.load_asset(apath)
        if isinstance(obj, u.StaticMesh):
            # Smart Nanite Policy: multi-island architectural shells & thin-plank/saw-tooth interior props use auto-LODs
            # (prevents Nanite root-page thin-plank shredding & keeps Always-Resident Nanite memory lean!)
            if obj.get_name() in (
                "SM_LM_Warehouse", "SM_LM_ToolRoom", "SM_LM_Bunkhouse",
                "SM_LM_Warehouse_Ruined", "SM_LM_ToolRoom_Ruined", "SM_LM_Bunkhouse_Ruined",
                "SM_LM_TimberRack", "SM_LM_TimberRack_Ruined", "SM_LM_BunkBed",
                "SM_LM_ChoppingStumpA", "SM_LM_ChoppingStumpB",
                "SM_LM_TwoManCrosscutSaw", "SM_LM_FramePitSaw", "SM_LM_WorkbenchSawSet",
                # R52 moving wagon dynamic meshes intentionally use 3-level LODs instead of Nanite
                "SM_LM_TimberWagon_Chassis", "SM_LM_TimberWagon_FrontAxle",
                "SM_LM_TimberWagon_Wheel", "SM_LM_HorseHarness",
            ):
                continue
            if bool(obj.get_editor_property("nanite_settings").enabled):
                nanite_ok += 1
            else:
                nanite_fail += 1
        elif isinstance(obj, u.Texture2D):
            tex_total += 1
            ms = int(obj.get_editor_property("max_texture_size"))
            ns_flag = bool(obj.get_editor_property("never_stream"))
            if ms == 0 or ms > 1024 or ns_flag:
                tex_uncapped += 1
            # BC7/BC5/DXT5 conservative 1 byte/pixel * 1.333 mipchain estimate
            sz = ms if ms > 0 else 1024
            vram_bytes += int(sz * sz * 1.333)
    return {
        "nanite_ok": nanite_ok,
        "nanite_fail": nanite_fail,
        "textures_total": tex_total,
        "textures_uncapped_or_neverstream": tex_uncapped,
        "est_vram_mb": round(vram_bytes / (1024.0 * 1024.0), 2),
    }


def main():
    R49_BATCH.mkdir(parents=True, exist_ok=True)
    ter_dir = R49_SRC / "Terrain"
    hills_theme_dir = R49_SRC / "Themes/HillsLandscape"
    road_theme_dir = R49_SRC / "Themes/RoadLandscape"
    compound_only = os.environ.get("FPS_LUMBER_COMPOUND_ONLY", "0") == "1"

    # 1) Import all 14 Blender R49b FBX meshes + ground-blended M_LM_WoodchipMulch + tightened Quixel caps
    catalog = lm_import.import_all(R49_SRC)
    r48_catalog = json.loads((R48_SRC / "road-asset-catalog.json").read_text(encoding="utf-8"))

    study_report = None
    fine_count, fine_cells = None, None
    road_tune = None
    perf_hism = None

    if not compound_only:
        # 2) Update expanded 3-road+yard road materials & recompile MF_TrailDirt + terrain shaders
        update_expanded_road_materials(R49_SRC, R49_BATCH)

        # 3) Apply Landscape edit layer (height + C_LayerInfo paint), Nanite rebuild, reference.f32 export, & PCGVolume clearing!
        study_report = update_landscape_and_study_pcg(ter_dir)

        # 4) Load L_ForestPathVillage, bake outer terrain + MapRoads (M-key map!), near grass, fine meadow, and dual-theme PCG!
        world = save_utils.load_map(level.village)
        if not u.get_editor_subsystem(u.LevelEditorSubsystem).set_current_level_by_name("L_ForestPathVillage"):
            raise RuntimeError("Cannot select persistent level L_ForestPathVillage")

        actors = level.actor_list()
        region = next(
            a for a in actors
            if isinstance(a, u.ForestVillageRegion) and a.get_path_name().startswith(level.village + ".")
        )
        if not region.bake_reference_surface(str(ter_dir), art.asset(art.ref + "/MI_ForestReference")):
            raise RuntimeError("bake_reference_surface failed for LumberMill-R49")
        if not region.install_grass_cover(str(ter_dir / "Grass/near_grass.u8"), True):
            raise RuntimeError("install_grass_cover failed for LumberMill-R49")

        level.src = ter_dir
        fine_count, fine_cells = level.place_meadows(world)

        templates = [
            c for a in actors
            if isinstance(a, u.PCGVolume) and "/L_ForestPathForest." in a.get_path_name()
            for c in a.get_components_by_class(u.InstancedStaticMeshComponent)
        ]
        if not templates:
            raise RuntimeError("Missing reference PCG templates in L_ForestPathForest")

        hills_pts = themes.point_input(themes.preset("HillsLandscape"), hills_theme_dir)
        if not region.bake_vegetation(hills_pts, templates, "HillsLandscape"):
            raise RuntimeError("Failed baking pruned HillsLandscape")

        road_pts = themes.point_input(themes.preset("RoadLandscape"), road_theme_dir)
        if not region.bake_vegetation(road_pts, templates, "RoadLandscape"):
            raise RuntimeError("Failed baking 3-road RoadLandscape")

        r48_auth.R48_SRC = R49_SRC
        road_tune = r48_auth.refit_road_pcg_and_spawners(region, road_theme_dir / "road-slot-rules.json")

        if not save_utils.save_map(world, level.village):
            raise RuntimeError("Failed saving L_ForestPathVillage prior to HISM perf pass")

        perf_hism = perf_opt.optimize_hills_and_road_hisms()

    # Load L_ForestPathVillage and assemble the R49b Lumber Mill Compound!
    world = save_utils.load_map(level.village)
    if not u.get_editor_subsystem(u.LevelEditorSubsystem).set_current_level_by_name("L_ForestPathVillage"):
        raise RuntimeError("Cannot select persistent level L_ForestPathVillage for compound assembly")
    compound_report = assemble_lumber_mill_compound(world, R49_SRC, catalog, r48_catalog)

    if not save_utils.save_map(world, level.village):
        raise RuntimeError("Failed saving L_ForestPathVillage")

    # 6) Verify compiled shader stats + Nanite / VRAM audit
    compiled_path = R49_BATCH / "compiled.json"
    compiled = json.loads(compiled_path.read_text(encoding="utf-8")) if compiled_path.is_file() else {}
    for mpath in (
        "/Game/ForestPathStudy/VillageRegion/LumberMill/Materials/M_LumberPropScan",
        "/Game/ForestPathStudy/VillageRegion/LumberMill/Materials/M_LM_WoodchipDecal",
    ):
        lm_mat = u.load_asset(mpath)
        if lm_mat:
            st = ed.get_statistics(lm_mat)
            compiled[lm_mat.get_path_name()] = {
                k: st.get_editor_property(k) for k in ("num_pixel_shader_instructions", "num_samplers")
            }
    vram_audit = audit_lumber_assets_vram()
    if vram_audit["nanite_fail"] != 0 or vram_audit["textures_uncapped_or_neverstream"] != 0:
        raise RuntimeError("LUMBER ASSET PERF AUDIT FAILED: " + json.dumps(vram_audit))

    result = {
        "batch": "LumberMillQuest-R51" if compound_only else "LumberMill-R49",
        "compound_only": compound_only,
        "arch_imported": len(catalog["arch"]),
        "ruined_imported": len(catalog.get("ruined", {})),
        "quixel_props_imported": len(catalog["props"]),
        "lumber_mill_compound": compound_report,
        "asset_vram_audit": vram_audit,
        "compiled_materials": compiled,
    }
    if not compound_only:
        result.update({
            "study_landscape_pcg": study_report,
            "fine_meadow_instances": fine_count,
            "fine_meadow_cells": fine_cells,
            "road_spawner_tuning": road_tune,
            "hills_hism_perf": perf_hism,
        })
    out_file = R49_BATCH / ("authored-r51.json" if compound_only else "authored.json")
    out_file.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print("R51_AUTHOR_DONE:", json.dumps({k: v for k, v in result.items() if k != "lumber_mill_compound"}, indent=2))
    print("R51_COMPOUND:", json.dumps({k: v for k, v in compound_report.items() if k != "by_mesh"}, indent=2))


if __name__ == "__main__":
    main()
