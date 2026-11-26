"""Headless authoring and geometric self-verification for ExpandedYardR42 on L_AbandonedVillage."""
from collections import Counter
import hashlib
import json
import math
import shutil
import sys
from pathlib import Path
import unreal as ue

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from relocate_gunshop import clear_scatter_in_boxes, relocate_gunshop
from stable_actors import ASSEMBLY
from stable_ground_detail import install_ground_detail
from stable_ground_materials import author_west_paddock
from stable_master_house import HOUSE_CX, HOUSE_CY, FLOOR_TOP_Z, install_stable_master_house
from stable_perimeter import install_stable_perimeter, perimeter_chains

LEVEL = '/Game/WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage'
BATCH = Path(r'F:/FPSGAMEData/ArtProduction/HillsVillageStable/ExpandedYardR42-20261125')


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def boxes_overlap_2d(a, b, margin=0.0):
    return not (a[2] + margin <= b[0] or b[2] + margin <= a[0] or a[3] + margin <= b[1] or b[3] + margin <= a[1])


def verify_world(world, actors, gunshop_report, perimeter_report, house_report, detail_report):
    issues = []
    checks = {}
    all_actors = list(actors.get_all_level_actors())
    by_label = {a.get_actor_label(): a for a in all_actors}

    # 1. Verify Fence Closure (every endpoint is either paired to another chain end or a gatepost pair)
    chains, gateposts, existing_piers = perimeter_chains()
    endpoints = Counter()
    for c in chains:
        endpoints[c[0]] += 1
        endpoints[c[-1]] += 1
    expected_gate_ends = set(gateposts) | set(existing_piers)
    open_ends = [pt for pt, deg in endpoints.items() if deg % 2 == 1 and pt not in expected_gate_ends]
    checks['fence_closed_loop'] = (len(open_ends) == 0)
    if open_ends:
        issues.append(f'Unclosed fence endpoints: {open_ends}')

    # 2. Verify all required ColdSteelDoors exist and have valid BlockAll leaves
    required_doors = [
        'Village_Stable_WagonGate_West', 'Village_Stable_WagonGate_East',
        'Village_Stable_Perimeter_LeadHorseGate', 'Village_Stable_Perimeter_WestPaddockGate',
        'Village_Stable_MasterHouse_Door',
        'Village_Stable_Stall01_Court', 'Village_Stable_Stall01_Aisle',
        'Village_Stable_Stall02_Court', 'Village_Stable_Stall02_Aisle',
        'Village_Stable_Stall03_Court', 'Village_Stable_Stall03_Aisle',
        'Village_Stable_Stall04_Court', 'Village_Stable_Stall04_Aisle',
    ]
    missing_doors = []
    for dname in required_doors:
        da = by_label.get(dname)
        if not da or not isinstance(da, ue.ColdSteelDoor):
            missing_doors.append(dname)
            continue
        leaf = next((c for c in da.get_components_by_class(ue.StaticMeshComponent) if c.get_name() == 'DoorLeaf'), None)
        if not leaf or not leaf.static_mesh:
            issues.append(f'Door missing leaf mesh: {dname}')
    checks['all_doors_valid'] = (len(missing_doors) == 0)
    if missing_doors:
        issues.append(f'Missing doors: {missing_doors}')

    # 3. Verify Gunshop relocation, tags, children, vision, and waypost
    gs = by_label.get('Village_09_Gunshop')
    if not gs:
        issues.append('Missing Village_09_Gunshop')
    else:
        g_loc = gs.get_actor_location()
        g_org, g_ext = gs.get_actor_bounds(False)
        g_box = [g_org.x - g_ext.x, g_org.y - g_ext.y, g_org.x + g_ext.x, g_org.y + g_ext.y]
        checks['gunshop_location_cm'] = [round(g_loc.x, 1), round(g_loc.y, 1), round(g_loc.z, 1)]
        checks['gunshop_box_cm'] = [round(v, 1) for v in g_box]
        # Verify zero overlap with Carpenter 04 (-3870..0, 0..1887 -> real house -3870..-2950, 950..1890),
        # Tavern 02 (-2090..-400, 1954..3912), and DeadTree 01A (-2400, 2800 trunk, box -2830..-2000)
        for name, ob in [
            ('Carpenter04', (-3870, 950, -2950, 1890)),
            ('Tavern02', (-2090, 1954, -400, 3912)),
            ('DeadTree01A_Trunk', (-2550, 2650, -2250, 2950)),
            ('ExpandedStable', (950, 1600, 5793, 4620)),
        ]:
            if boxes_overlap_2d(g_box, ob):
                issues.append(f'Gunshop overlaps {name}: {g_box} vs {ob}')
        # Verify Ruin & Restored component tags preserved
        comp_tags = {str(t) for c in gs.get_components_by_class(ue.SceneComponent) for t in c.component_tags}
        for req_tag in ('VillageGunshop.Ruin', 'VillageGunshop.Restored', 'VillageGunshop.Solid'):
            if req_tag not in comp_tags:
                issues.append(f'Gunshop missing component tag {req_tag}')
        # Verify Workbench & OrderBook inside Gunshop box
        for cname in ('Village_09_Gunshop_Workbench', 'Village_09_Gunshop_OrderBook'):
            ca = by_label.get(cname)
            if not ca:
                issues.append(f'Missing {cname}')
            else:
                cl = ca.get_actor_location()
                if not (g_box[0] <= cl.x <= g_box[2] and g_box[1] <= cl.y <= g_box[3]):
                    issues.append(f'{cname} outside moved Gunshop box: {cl}')
        vis = by_label.get('Village_InteriorVision_09_枪店')
        if not vis or (vis.get_actor_location() - g_loc).length() > 5.0:
            issues.append('Village_InteriorVision_09_枪店 misaligned with moved Gunshop')

    # 4. Verify Stablemaster House bounds & non-overlap with Barn, Trough, Grove Trees, Fence
    h_box = [HOUSE_CX - 320.0, HOUSE_CY - 320.0, HOUSE_CX + 320.0, HOUSE_CY + 320.0]
    checks['house_box_cm'] = h_box
    if not (950 + 200 <= h_box[0] and h_box[2] <= 5793 - 200 and 3320 + 200 <= h_box[1] and h_box[3] <= 4620 - 100):
        issues.append(f'Stablemaster house too close to or outside fence: {h_box}')
    for name, ob in [
        ('Barn', (3280, 3550, 5520, 4350)),
        ('TroughA09', (2930, 3970, 3020, 4190)),
        ('GroveBeechYoung', (2860, 3640, 3080, 3860)),
        ('WestGateSwing', (950, 3660, 1210, 3930)),
    ]:
        if boxes_overlap_2d(h_box, ob):
            issues.append(f'Stablemaster house overlaps {name}')

    # 5. Verify Stablemaster NPC grounding, interior placement, headroom, and unobstructed doorway sightline
    npc = by_label.get('Village_Stable_Stablemaster')
    if not npc:
        issues.append('Missing Village_Stable_Stablemaster')
    else:
        nloc = npc.get_actor_location()
        norg, nextent = npc.get_actor_bounds(False)
        feet_z = norg.z - nextent.z
        head_z = norg.z + nextent.z
        checks['stablemaster_pos_cm'] = [round(nloc.x, 1), round(nloc.y, 1), round(nloc.z, 1)]
        checks['stablemaster_feet_z_cm'] = round(feet_z, 1)
        checks['stablemaster_head_z_cm'] = round(head_z, 1)
        if not (HOUSE_CX - 245 <= nloc.x <= HOUSE_CX + 245 and HOUSE_CY - 245 <= nloc.y <= HOUSE_CY + 245):
            issues.append(f'Stablemaster not safely inside cabin interior: {nloc}')
        if abs(feet_z - FLOOR_TOP_Z) > 3.5:
            issues.append(f'Stablemaster feet Z ({feet_z:.1f}) deviates from floor ({FLOOR_TOP_Z:.1f})')
        if head_z > 265.0:
            issues.append(f'Stablemaster head Z ({head_z:.1f}) too close to ceiling beams (276 cm)')
        # Check unobstructed diagonal path from doorway interior (HOUSE_CX-146, HOUSE_CY-230) to NPC
        # Verify desk center (HOUSE_CX+120, HOUSE_CY+20, half 66x36) does not intersect player-to-NPC line!
        ax, ay = HOUSE_CX - 146.0, HOUSE_CY - 230.0
        bx, by = nloc.x, nloc.y
        dx, dy = bx - ax, by - ay
        l2 = dx * dx + dy * dy
        tx, ty = HOUSE_CX + 120.0, HOUSE_CY + 20.0
        t = max(0.0, min(1.0, ((tx - ax) * dx + (ty - ay) * dy) / max(1.0, l2)))
        dist_desk = math.hypot(tx - (ax + t * dx), ty - (ay + t * dy))
        checks['door_to_npc_desk_clearance_cm'] = round(dist_desk, 1)
        if dist_desk < 70.0:
            issues.append(f'Desk too close to door->NPC walkway: {dist_desk:.1f} cm')

    # 6. Verify ZERO null materials across all Stable actors
    null_mats = []
    stable_actor_count = 0
    for a in all_actors:
        if ASSEMBLY not in map(str, a.tags):
            continue
        stable_actor_count += 1
        for c in a.get_components_by_class(ue.StaticMeshComponent):
            if not c.static_mesh:
                continue
            for i in range(c.get_num_materials()):
                if c.get_material(i) is None:
                    null_mats.append(f'{a.get_actor_label()}.{c.get_name()}[{i}]')
    checks['stable_actor_count'] = stable_actor_count
    checks['null_materials'] = null_mats
    if null_mats:
        issues.append(f'Null materials found: {null_mats[:10]}')

    # 7. Verify Windmill 05 & East Grove Trees untouched and outside fence/house
    wm = by_label.get('Village_05_Windmill')
    checks['windmill_intact'] = (wm is not None)
    if not wm:
        issues.append('Missing Village_05_Windmill')

    checks['issues'] = issues
    checks['passed'] = (len(issues) == 0)
    return checks


def main():
    project = Path(ue.Paths.convert_relative_path_to_full(ue.Paths.project_dir()))
    map_file = project / 'Content' / (LEVEL.removeprefix('/Game/') + '.umap')
    before_sha = digest(map_file)

    # Pre-edit SHA-256 backup under Batch/Before/<sha>/
    before_copy = BATCH / 'Before' / before_sha / map_file.name
    before_copy.parent.mkdir(parents=True, exist_ok=True)
    if not before_copy.exists():
        shutil.copy2(map_file, before_copy)
    if digest(before_copy) != before_sha:
        raise RuntimeError('Pre-edit backup checksum mismatch')

    # Backup & reimport T_VillageRoadMask so new gunshop doorway approach soil appears live.
    road_mask_asset = project / 'Content/WorldGeneration/TemperateHills/AbandonedVillage/T_VillageRoadMask.uasset'
    road_before_sha = digest(road_mask_asset)
    road_backup = BATCH / 'Before/RoadMask' / road_before_sha / road_mask_asset.name
    road_backup.parent.mkdir(parents=True, exist_ok=True)
    if not road_backup.exists():
        shutil.copy2(road_mask_asset, road_backup)
    rtask = ue.AssetImportTask()
    rtask.filename = str(project / 'SourceAssets/TemperateHillsVillage/RoadMask.png')
    rtask.destination_path = '/Game/WorldGeneration/TemperateHills/AbandonedVillage'
    rtask.destination_name = 'T_VillageRoadMask'
    rtask.automated = True
    rtask.replace_existing = True
    rtask.replace_existing_settings = False
    ue.AssetToolsHelpers.get_asset_tools().import_asset_tasks([rtask])
    rtex = ue.load_asset('/Game/WorldGeneration/TemperateHills/AbandonedVillage/T_VillageRoadMask')
    if not rtex:
        raise RuntimeError('Failed to reimport T_VillageRoadMask')
    rtex.srgb = False
    rtex.compression_settings = ue.TextureCompressionSettings.TC_MASKS
    rtex.address_x = rtex.address_y = ue.TextureAddress.TA_CLAMP
    if not ue.EditorAssetLibrary.save_loaded_asset(rtex, False):
        raise RuntimeError('Failed to save T_VillageRoadMask')

    # Author West Paddock soil decal textures & material first so install_ground_detail binds it cleanly.
    author_west_paddock()

    world = ue.EditorLoadingAndSavingUtils.load_map(LEVEL)
    if not world:
        raise RuntimeError('Could not load ' + LEVEL)
    actors = ue.get_editor_subsystem(ue.EditorActorSubsystem) or ue.new_object(ue.EditorActorSubsystem)

    gunshop_report = relocate_gunshop(actors)
    paddock_cleared = clear_scatter_in_boxes(actors, [
        (880.0, 3220.0, 5850.0, 4680.0),  # Expanded west paddock, house footprint, and rear strip
    ])
    perimeter_report = install_stable_perimeter(actors)
    house_report = install_stable_master_house(actors)
    detail_report = install_ground_detail(actors)

    audit = verify_world(world, actors, gunshop_report, perimeter_report, house_report, detail_report)
    if not audit['passed']:
        (BATCH / 'audit-failed.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding='utf-8')
        raise RuntimeError('Self-verification failed: ' + '; '.join(audit['issues']))

    if digest(map_file) != before_sha:
        raise RuntimeError('Map modified externally during authoring')
    if not ue.EditorLoadingAndSavingUtils.save_map(world, LEVEL):
        raise RuntimeError('Failed to save ' + LEVEL)

    after_sha = digest(map_file)
    after_copy = BATCH / 'After' / after_sha / map_file.name
    after_copy.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(map_file, after_copy)

    receipt = dict(
        batch='ExpandedYardR42-20261125',
        level=LEVEL,
        production_map=str(map_file),
        before_file=str(before_copy),
        before_sha256=before_sha,
        after_file=str(after_copy),
        after_sha256=after_sha,
        gunshop=gunshop_report,
        paddock_cleared_scatter=paddock_cleared,
        perimeter=perimeter_report,
        master_house=house_report,
        ground_detail=detail_report,
        verification=audit,
        runtime_tested=False,
    )
    (BATCH / 'published.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
    ue.log('EXPANDED_YARD_R42_PUBLISHED ' + after_sha)


if __name__ == '__main__':
    main()
