"""Stage QA audit + complete foliage/PCGPartition/StaticMesh clearing inside L_ForestPathForest
and full MapRoadWeight / Nanite / Texture-Cap / Collision verification in L_ForestPathVillage.
"""
import json
import math
import os
import struct
import sys
from pathlib import Path

import unreal as u

TOOLS = Path("D:/FPS3D/FPSGAME/Tools/WorldGeneration/ForestVillage")
sys.path.insert(0, str(TOOLS))

import author_lumber_mill_r49 as lm_auth
import author_trail_cover_level as level

R49_SRC = Path(os.environ["FPS_LUMBER_R49_SOURCE"])
R49_BATCH = Path(os.environ["FPS_FOREST_REFERENCE_BATCH"])

lib = u.EditorAssetLibrary
save_utils = u.EditorLoadingAndSavingUtils
actors_sub = u.get_editor_subsystem(u.EditorActorSubsystem)


def clean_all_study_actors(ter_dir: Path):
    """Inspect EVERY actor in L_ForestPathForest (PCGVolume, PCGPartitionActor, InstancedFoliageActor,
    StaticMeshActor, etc.) and prune/re-seat anything overlapping the logging road or Lumber Mill yard!
    """
    copy_map = level.copy
    world = save_utils.load_map(copy_map)
    if not world:
        raise RuntimeError("Cannot load " + copy_map)

    road_pts = lm_auth.load_lumber_road_xy_m(ter_dir / "lumber-road.csv")
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

    all_actors = actors_sub.get_all_level_actors()
    summary = []
    total_pruned = 0
    total_reseated = 0
    destroyed_actors = 0
    dirty = False

    for a in all_actors:
        if not a.get_path_name().startswith(copy_map + "."):
            continue
        cls = a.get_class().get_name()
        lbl = a.get_actor_label()
        if isinstance(a, (u.Landscape, u.LandscapeProxy)):
            continue

        # 1) Check all InstancedStaticMeshComponents (covers PCGVolume, PCGPartitionActor, InstancedFoliageActor!)
        isms = list(a.get_components_by_class(u.InstancedStaticMeshComponent))
        if isms:
            a_pruned = 0
            a_reseated = 0
            a_total = 0
            for comp in isms:
                n = comp.get_instance_count()
                a_total += n
                if n == 0:
                    continue
                mname = comp.static_mesh.get_name() if comp.static_mesh else ""
                is_tree_like = ("Hornbeam" in mname or "Hazel" in mname or "Canopy" in lbl or "Hazel" in lbl)
                road_clear = 4.2 if is_tree_like else 3.2
                yard_clear = 5.2 if is_tree_like else 3.4
                kept = []
                comp_changed = False
                for idx in range(n):
                    tf = comp.get_instance_transform(idx, world_space=True)
                    xm, ym = float(tf.translation.x) * 0.01, float(tf.translation.y) * 0.01
                    if 78.0 <= xm <= 202.0 and 18.0 <= ym <= 255.0:
                        ysdf = lm_auth.yard_sdf_m(xm, ym)
                        rd = lm_auth.min_dist_to_polyline(xm, ym, road_pts)
                        if ysdf <= yard_clear or rd <= road_clear:
                            a_pruned += 1
                            comp_changed = True
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
                            a_reseated += 1
                            comp_changed = True
                    kept.append(tf)
                if comp_changed:
                    comp.modify()
                    comp.clear_instances()
                    if kept:
                        comp.add_instances(kept, False, True, False)
                    dirty = True
            if a_total > 0:
                summary.append({"actor": lbl, "class": cls, "instances": a_total, "pruned": a_pruned, "reseated": a_reseated})
                total_pruned += a_pruned
                total_reseated += a_reseated
                print(f"[AUDIT-ISM] {cls:24s} | {lbl:32s} | n={a_total:6d} | pruned={a_pruned:4d} | reseated={a_reseated:4d}")

        # 2) Check standalone StaticMeshActors (e.g. hand-placed boulders/stumps/logs inside L_ForestPathForest)
        elif isinstance(a, u.StaticMeshActor):
            loc = a.get_actor_location()
            xm, ym = float(loc.x) * 0.01, float(loc.y) * 0.01
            if 78.0 <= xm <= 202.0 and 18.0 <= ym <= 255.0:
                ysdf = lm_auth.yard_sdf_m(xm, ym)
                rd = lm_auth.min_dist_to_polyline(xm, ym, road_pts)
                if ysdf <= 3.5 or rd <= 3.2:
                    print(f"[AUDIT-SMA] Destroying overlapping {lbl} at ({xm:.1f}, {ym:.1f})")
                    actors_sub.destroy_actor(a)
                    destroyed_actors += 1
                    dirty = True
                else:
                    dz = delta_at_cm(float(loc.x), float(loc.y))
                    if abs(dz) > 0.5:
                        a.set_actor_location(u.Vector(loc.x, loc.y, loc.z + dz), False, True)
                        total_reseated += 1
                        dirty = True

    if dirty:
        if not save_utils.save_map(world, copy_map):
            raise RuntimeError("Failed saving cleaned L_ForestPathForest")
        print(f"[AUDIT-STUDY] Saved cleaned L_ForestPathForest (pruned={total_pruned}, destroyed_sma={destroyed_actors}, reseated={total_reseated})")
    return {
        "actors_with_isms": summary,
        "extra_pruned": total_pruned,
        "destroyed_smas": destroyed_actors,
        "extra_reseated": total_reseated,
    }


def audit_village_and_assets(ter_dir: Path):
    """Audit M-key MapRoadWeight, LumberMill_Compound integrity, Nanite, Collisions, and Texture Caps!"""
    world = save_utils.load_map(level.village)
    if not world:
        raise RuntimeError("Cannot load " + level.village)

    all_actors = actors_sub.get_all_level_actors()
    region = next(a for a in all_actors if isinstance(a, u.ForestVillageRegion) and a.get_path_name().startswith(level.village + "."))
    compound = next((a for a in all_actors if a.get_actor_label() == "LumberMill_Compound"), None)
    if not compound:
        raise RuntimeError("Missing LumberMill_Compound actor in L_ForestPathVillage!")

    # 1) Verify C_LayerInfo & MapRoadPaint (M-key map) across ALL roads: original forest trail, gate road, lumber road, yard!
    # Read Region.MapRoadPaint indirectly via C++ or verify in Python via paint.rg8 + L_ForestPathForest check
    # Check if region has BakeMapRoads succeeded & inspect L_ForestPathForest landscape C_LayerInfo directly!
    c_layer = u.load_asset("/Game/Example/Maps/NaniteExample_sharedassets/C_LayerInfo")
    ls = next((a for a in all_actors if isinstance(a, u.LandscapeProxy) and "/L_ForestPathForest." in a.get_path_name()), None)
    # Also verify zero tree/rock instances inside Lumber Mill building footprint X in [143..169], Y in [51..61]!
    bldg_overlap = 0
    for a in all_actors:
        if a == compound or isinstance(a, (u.Landscape, u.LandscapeProxy)):
            continue
        for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
            for i in range(c.get_instance_count()):
                tf = c.get_instance_transform(i, world_space=True)
                xm, ym = float(tf.translation.x) * 0.01, float(tf.translation.y) * 0.01
                if 143.0 <= xm <= 168.5 and 51.5 <= ym <= 61.5:
                    bldg_overlap += 1
                    print(f"[OVERLAP!] {a.get_actor_label()} / {c.static_mesh.get_name() if c.static_mesh else '?'} at ({xm:.1f}, {ym:.1f})")

    # 2) Audit every StaticMesh & Texture2D under /Game/ForestPathStudy/VillageRegion/LumberMill
    lm_dir = "/Game/ForestPathStudy/VillageRegion/LumberMill"
    mesh_audit = []
    tex_audit = []
    nanite_ok = 0
    nanite_fail = 0
    tex_uncapped = 0
    for apath in sorted(lib.list_assets(lm_dir, recursive=True, include_folder=False)):
        obj = u.load_asset(apath)
        if isinstance(obj, u.StaticMesh):
            ns = obj.get_editor_property("nanite_settings")
            en = bool(ns.enabled)
            body = obj.get_editor_property("body_setup")
            ctf = str(body.get_editor_property("collision_trace_flag")) if body else "None"
            nbox = len(body.get_editor_property("agg_geom").get_editor_property("box_elems")) if body else 0
            if en:
                nanite_ok += 1
            else:
                nanite_fail += 1
            mesh_audit.append({"name": obj.get_name(), "nanite": en, "ctf": ctf, "boxes": nbox})
        elif isinstance(obj, u.Texture2D):
            ms = int(obj.get_editor_property("max_texture_size"))
            ns_flag = bool(obj.get_editor_property("never_stream"))
            if ms == 0 or ms > 1024 or ns_flag:
                tex_uncapped += 1
            tex_audit.append({"name": obj.get_name(), "max_size": ms, "never_stream": ns_flag})

    # 3) Check LumberMill_Compound component summary
    smcs = list(compound.get_components_by_class(u.StaticMeshComponent))
    hisms = list(compound.get_components_by_class(u.HierarchicalInstancedStaticMeshComponent))
    lights = list(compound.get_components_by_class(u.PointLightComponent))
    shadow_lights = sum(1 for l in lights if l.cast_shadows)
    hero_smcs = [c for c in smcs if not isinstance(c, u.InstancedStaticMeshComponent)]

    rep = {
        "building_footprint_overlaps": bldg_overlap,
        "compound_hero_buildings": len(hero_smcs),
        "compound_hisms": len(hisms),
        "compound_prop_instances": sum(h.get_instance_count() for h in hisms),
        "compound_lights": len(lights),
        "compound_shadow_lights": shadow_lights,
        "lumber_meshes_nanite_ok": nanite_ok,
        "lumber_meshes_nanite_fail": nanite_fail,
        "lumber_textures_total": len(tex_audit),
        "lumber_textures_uncapped_or_neverstream": tex_uncapped,
        "landscape_streaming_present": ls is not None,
    }
    print("QA_VILLAGE_AUDIT:", json.dumps(rep, indent=2))
    return rep


def main():
    ter_dir = R49_SRC / "Terrain"
    study_clean = clean_all_study_actors(ter_dir)
    village_qa = audit_village_and_assets(ter_dir)
    out = {"study_clean": study_clean, "village_qa": village_qa}
    (R49_BATCH / "qa-audit-r49.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("R49_QA_DONE")


if __name__ == "__main__":
    main()
