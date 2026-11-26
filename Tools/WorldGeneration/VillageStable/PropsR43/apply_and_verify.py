"""End-to-end headless UE 5.8 pipeline for StablePropsR44:
1. Archive & project-wide delete broken SM_Mil_Trench_Bench_Wood_01;
2. Import 2K weathered textures, VertexColor-weathered ISM materials & upgraded 3-LOD meshes;
3. Relocate 8 doorway-blocking Windmill shrubs to spacious paddock fence edges;
4. Refresh Cabin (grounded pots) & Yard (no bench, no street lamps, upgraded hero props);
5. Exhaustive automated self-verification, save map & SHA-256 recovery receipt.
"""
import hashlib
import json
import math
import shutil
import sys
from pathlib import Path

import unreal as ue

HERE = Path(__file__).resolve().parent
STABLE_TOOLS = HERE.parent
PROJECT = STABLE_TOOLS.parents[2]
sys.path[:0] = [str(HERE), str(STABLE_TOOLS), str(STABLE_TOOLS.parent / 'AbandonedVillage')]

from import_props import import_all_props
from retire_bench_r44 import (
    BENCH_DIR_DISK,
    BENCH_KEY,
    clean_external_maps_and_bp,
    finalize_delete_bench_assets,
    relocate_cabin_doorway_shrubs,
    strip_bench_in_current_level,
)
from stable_master_house import HOUSE_CX, HOUSE_CY, install_stable_master_house
from stable_ground_detail import install_ground_detail

LEVEL = '/Game/WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage'
MAP_FILE = PROJECT / 'Content/WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage.umap'
BATCH = Path('F:/FPSGAMEData/ArtProduction/HillsVillageStable/PropsR44-20261126')
TRASH_BENCH = PROJECT / 'trash/RetireMilTrenchBench-20261126'


def sha256(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _ism_world_aabb(actor):
    """Compute exact world-space AABB [min_x, min_y, max_x, max_y, min_z, max_z] across all ISM instances."""
    xs, ys, zs = [], [], []
    for comp in actor.get_components_by_class(ue.InstancedStaticMeshComponent):
        sm = comp.static_mesh
        if not sm:
            continue
        bb = sm.get_bounding_box()
        corners = [
            ue.Vector(x, y, z)
            for x in (bb.min.x, bb.max.x)
            for y in (bb.min.y, bb.max.y)
            for z in (bb.min.z, bb.max.z)
        ]
        for i in range(comp.get_instance_count()):
            tf = comp.get_instance_transform(i, True)
            for c in corners:
                w = ue.MathLibrary.transform_location(tf, c)
                xs.append(float(w.x))
                ys.append(float(w.y))
                zs.append(float(w.z))
    if not xs:
        return None
    return [round(min(xs), 1), round(min(ys), 1), round(max(xs), 1), round(max(ys), 1),
            round(min(zs), 1), round(max(zs), 1)]


def verify_scene(actors):
    issues = []
    all_actors = list(actors.get_all_level_actors())
    by_label = {a.get_actor_label(): a for a in all_actors}

    # 1. Verify active R44 props & trade signs exist with zero null materials
    required_labels = [
        'Village_Stable_MasterHouse_SaddleStand',
        'Village_Stable_MasterHouse_TackWallRack_Detail',
        'Village_Stable_MasterHouse_TradeSign',
        'Village_Stable_MasterHouse_WindowPot_Detail',
        'Village_Stable_Dressing_SaddleStand',
        'Village_Stable_Dressing_TackWallRack_Detail',
        'Village_Stable_Dressing_JumpRail',
        'Village_Stable_Dressing_HayWagon',
        'Village_TradeWaypost_Stable',
    ]
    missing = [lbl for lbl in required_labels if lbl not in by_label]
    if missing:
        issues.append(f'Missing expected R44 actors: {missing}')

    # 2. Verify street lamps & broken bench are GONE from the stable area and entire level
    for forbidden in ('Village_Stable_Dressing_YardLampPost', 'Village_Stable_Dressing_WoodBench', 'Village_000_SM_Mil_Trench_Bench_Wood_01'):
        if forbidden in by_label:
            issues.append(f'Forbidden actor still present in level: {forbidden}')

    bench_refs_in_level = []
    null_mats = []
    prop_counts = {}
    for a in all_actors:
        lbl = a.get_actor_label()
        for comp in a.get_components_by_class(ue.StaticMeshComponent):
            sm = comp.static_mesh
            if sm and BENCH_KEY in sm.get_path_name():
                bench_refs_in_level.append(f'{lbl}.{comp.get_name()}')
            if not (lbl.startswith('Village_Stable_') or lbl == 'Village_TradeWaypost_Stable'):
                continue
            if sm is None:
                continue
            for i in range(comp.get_num_materials()):
                if comp.get_material(i) is None:
                    null_mats.append(f'{lbl}.{comp.get_name()}[{i}]')
            if isinstance(comp, ue.InstancedStaticMeshComponent) and lbl in required_labels:
                prop_counts[lbl] = comp.get_instance_count()
    if bench_refs_in_level:
        issues.append(f'Level still references retired bench: {bench_refs_in_level}')
    if null_mats:
        issues.append(f'Null materials detected: {null_mats}')

    # Verify YardLights has ONLY 3 gate/barn lanterns (zero street-lamp post lanterns)
    yard_lights = by_label.get('Village_Stable_Dressing_YardLights')
    yard_light_count = len(yard_lights.get_components_by_class(ue.PointLightComponent)) if yard_lights else 0
    if yard_light_count != 3:
        issues.append(f'Expected 3 mounted yard/gate lanterns (no street lamps), found {yard_light_count}')

    # 3. Verify all WindowPot instances are grounded (Z <= 6.0 cm, ZERO floating windowsill pots!)
    pot_actor = by_label.get('Village_Stable_MasterHouse_WindowPot_Detail')
    pot_positions = []
    if pot_actor:
        for comp in pot_actor.get_components_by_class(ue.InstancedStaticMeshComponent):
            for i in range(comp.get_instance_count()):
                loc = comp.get_instance_transform(i, True).translation
                pot_positions.append([round(float(loc.x), 1), round(float(loc.y), 1), round(float(loc.z), 1)])
                if loc.z > 6.0 or loc.z < -2.0:
                    issues.append(f'WindowPot[{i}] not grounded on ground/floor: z={loc.z:.1f}')

    # 4. Verify ZERO hazel shrubs near cabin doorway or any stable gate (clear radius 320 cm)
    clear_doors = [
        ('CabinDoor', HOUSE_CX - 146.0, HOUSE_CY - 294.9, 320.0),
        ('WestGate', 967.0, 3795.0, 300.0),
        ('LeadGate', 4620.0, 1600.0, 300.0),
        ('WagonGate', 5310.0, 1600.0, 300.0),
    ]
    door_shrub_hits = []
    for a in all_actors:
        for comp in a.get_components_by_class(ue.InstancedStaticMeshComponent):
            sm = comp.static_mesh
            if not sm or not sm.get_name().startswith('SM_Hazel'):
                continue
            for i in range(comp.get_instance_count()):
                loc = comp.get_instance_transform(i, True).translation
                for dname, dx, dy, rad in clear_doors:
                    dist = math.hypot(loc.x - dx, loc.y - dy)
                    if dist < rad:
                        door_shrub_hits.append(dict(
                            near=dname, dist_cm=round(dist, 1), actor=a.get_actor_label(),
                            mesh=sm.get_name(), pos=[round(float(loc.x), 1), round(float(loc.y), 1)],
                        ))
    if door_shrub_hits:
        issues.append(f'Shrubs still blocking doorway/gates: {door_shrub_hits}')

    # 5. Verify weathered hero materials actively bound on HayWagon (Rope) and SaddleStand (Leather & Blanket)
    wagon_sm = ue.load_asset('/Game/WorldGeneration/TemperateHills/VillageStable/PropsR43/SM_Stable_HayWagon')
    saddle_sm = ue.load_asset('/Game/WorldGeneration/TemperateHills/VillageStable/PropsR43/SM_Stable_SaddleStand')
    wagon_mats = {str(s.material_slot_name): (s.material_interface.get_name() if s.material_interface else None)
                  for s in wagon_sm.static_materials} if wagon_sm else {}
    saddle_mats = {str(s.material_slot_name): (s.material_interface.get_name() if s.material_interface else None)
                   for s in saddle_sm.static_materials} if saddle_sm else {}
    if wagon_mats.get('Rope') != 'M_StableWeatheredRope':
        issues.append(f'HayWagon Rope material mismatch: {wagon_mats.get("Rope")}')
    if saddle_mats.get('LeatherMain') != 'M_StableSaddleLeather':
        issues.append(f'SaddleStand LeatherMain mismatch: {saddle_mats.get("LeatherMain")}')
    if saddle_mats.get('Blanket') != 'M_StableWoolBlanket':
        issues.append(f'SaddleStand Blanket mismatch: {saddle_mats.get("Blanket")}')

    # 6. Verify MI_StableSign on both Trade Signs
    sign_bindings = {}
    for s_lbl in ('Village_Stable_MasterHouse_TradeSign', 'Village_TradeWaypost_Stable'):
        act = by_label.get(s_lbl)
        if not act:
            continue
        found_mi = False
        for c in act.get_components_by_class(ue.StaticMeshComponent):
            if c.static_mesh and 'BoardR2' in c.static_mesh.get_name():
                slot = c.get_material_index('Paint')
                mat = c.get_material(slot) if slot >= 0 else None
                if mat and 'MI_StableSign' in mat.get_path_name():
                    found_mi = True
                    sign_bindings[s_lbl] = mat.get_path_name()
        if not found_mi:
            issues.append(f'{s_lbl} missing MI_StableSign on Paint slot')

    # 7. Verify JumpRail, HayWagon, TackWallRacks & Cabin SaddleStand placement bounds
    jump_bounds = _ism_world_aabb(by_label['Village_Stable_Dressing_JumpRail']) if 'Village_Stable_Dressing_JumpRail' in by_label else None
    wagon_bounds = _ism_world_aabb(by_label['Village_Stable_Dressing_HayWagon']) if 'Village_Stable_Dressing_HayWagon' in by_label else None
    cabin_saddle = by_label.get('Village_Stable_MasterHouse_SaddleStand')
    cabin_saddle_bounds = _ism_world_aabb(cabin_saddle) if cabin_saddle else None
    if jump_bounds and abs(jump_bounds[4]) > 2.5:
        issues.append(f'JumpRail not grounded: min_z={jump_bounds[4]}')
    if wagon_bounds and abs(wagon_bounds[4]) > 2.5:
        issues.append(f'HayWagon not grounded: min_z={wagon_bounds[4]}')
    if cabin_saddle_bounds and abs(cabin_saddle_bounds[4] - 4.0) > 2.0:
        issues.append(f'Cabin SaddleStand not on floor Z=4: {cabin_saddle_bounds[4]}')

    # 8. Verify Windmill & Gunshop remain intact
    windmill_ok = 'Village_05_Windmill' in by_label
    gunshop_ok = 'Village_09_Gunshop' in by_label
    if not windmill_ok or not gunshop_ok:
        issues.append(f'Missing landmark actor: windmill={windmill_ok}, gunshop={gunshop_ok}')

    return dict(
        prop_counts=prop_counts,
        yard_light_count=yard_light_count,
        window_pots_cm=pot_positions,
        door_shrub_hits=door_shrub_hits,
        wagon_key_materials=dict(Rope=wagon_mats.get('Rope'), Hay=wagon_mats.get('Hay'), Oak=wagon_mats.get('Oak')),
        saddle_key_materials=dict(LeatherMain=saddle_mats.get('LeatherMain'), LeatherDark=saddle_mats.get('LeatherDark'), Blanket=saddle_mats.get('Blanket')),
        sign_bindings=sign_bindings,
        jump_bounds_cm=jump_bounds,
        wagon_bounds_cm=wagon_bounds,
        cabin_saddle_bounds_cm=cabin_saddle_bounds,
        bench_refs_in_level=bench_refs_in_level,
        null_materials=null_mats,
        windmill_intact=windmill_ok,
        gunshop_intact=gunshop_ok,
        issues=issues,
        passed=len(issues) == 0,
    )


def main():
    BATCH.mkdir(parents=True, exist_ok=True)
    before_hash = sha256(MAP_FILE)
    before_copy = BATCH / 'Before' / before_hash / MAP_FILE.name
    before_copy.parent.mkdir(parents=True, exist_ok=True)
    if not before_copy.exists():
        shutil.copy2(MAP_FILE, before_copy)

    # 1. Archive retired bench & clean BP_Trench_Wall_02 + L_MilitaryTrench_FPS_Test + World Partition external actors
    retire_pre = clean_external_maps_and_bp(TRASH_BENCH, BATCH / 'retired_bench_manifest.json')

    # 2. Import new 2K weathered textures, 18 VertexColor-weathered ISM materials & 5 upgraded 3-LOD meshes
    import_report = import_all_props()

    # 3. Load production village level, strip broken bench across all village actors, relocate doorway shrubs, reinstall Cabin & Yard
    world = ue.EditorLoadingAndSavingUtils.load_map(LEVEL)
    if not world:
        raise RuntimeError(f'Failed to load level {LEVEL}')
    actors = ue.get_editor_subsystem(ue.EditorActorSubsystem) or ue.new_object(ue.EditorActorSubsystem)

    level_bench_cleanup = strip_bench_in_current_level(actors)
    shrub_report = relocate_cabin_doorway_shrubs(actors)
    cabin_report = install_stable_master_house(actors)
    yard_report = install_ground_detail(actors)

    # 4. Save L_AbandonedVillage first so it releases hard references to SM_Mil_Trench_Bench_Wood_01 before asset deletion
    verify = verify_scene(actors)
    if not verify['passed']:
        raise RuntimeError('R44 verification FAILED: ' + json.dumps(verify, ensure_ascii=False))

    if not ue.EditorLoadingAndSavingUtils.save_map(world, LEVEL):
        raise RuntimeError(f'Failed to save {LEVEL}')

    # 5. Permanently delete Mil_Trench_Bench_Wood_01 assets from Content & verify 0 files left on disk
    retire_delete = finalize_delete_bench_assets()
    if BENCH_DIR_DISK.exists():
        raise RuntimeError(f'Retired bench directory still exists on disk: {BENCH_DIR_DISK}')

    after_hash = sha256(MAP_FILE)
    after_copy = BATCH / 'After' / after_hash / MAP_FILE.name
    after_copy.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(MAP_FILE, after_copy)

    receipt = dict(
        batch='PropsR44-20261126',
        level=LEVEL,
        production_map=str(MAP_FILE),
        before_file=str(before_copy),
        before_sha256=before_hash,
        after_file=str(after_copy),
        after_sha256=after_hash,
        retired_bench=dict(
            archive=retire_pre,
            village_level_cleanup=level_bench_cleanup,
            deletion=retire_delete,
        ),
        doorway_shrubs=shrub_report,
        imported=import_report,
        master_house=cabin_report,
        ground_detail=yard_report,
        verification=verify,
        runtime_tested=False,
    )
    (BATCH / 'published.json').write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding='utf-8')
    ue.log('STABLE_PROPS_R44_OK')
    print('STABLE_PROPS_R44_OK', flush=True)


if __name__ == '__main__':
    main()
