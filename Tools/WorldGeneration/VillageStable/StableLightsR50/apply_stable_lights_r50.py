"""Headless UE 5.8 installer & strict vertex-level anti-clipping verifier for StableLightsR50:
1) Stablemaster Cabin: removes 1 interior lamp (2 -> 1 central beam-mounted forged-iron pendant + 1 exterior porch bracket lantern).
2) Stable Barn: installs 8 forged-iron stall-divider lanterns across all 4 dividers (X = 3740, 4180, 4620, 5060):
   - 4 front courtyard oak-pilaster wall-bracket lanterns
   - 4 interior overhead tie-beam pendants directly above each A05 stall partition
3) Performs exact vertex-level & AABB zero-clipping verification against all barn/cabin structures, doors, cribs & props."""
import hashlib
import json
import shutil
import sys
from pathlib import Path

import unreal as ue

HERE = Path(__file__).resolve().parent
STABLE_TOOLS = HERE.parent
PROJECT = STABLE_TOOLS.parents[2]
sys.path[:0] = [str(STABLE_TOOLS), str(STABLE_TOOLS.parent / 'AbandonedVillage')]

from stable_master_house import FLOOR_TOP_Z, HOUSE_CX, HOUSE_CY, install_stable_master_house
from stable_ground_detail import install_ground_detail

LEVEL = '/Game/WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage'
MAP_FILE = PROJECT / 'Content/WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage.umap'
BATCH = Path('F:/FPSGAMEData/ArtProduction/HillsVillageStable/StableLightsR50-20261126')


def sha256(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _mesh_world_aabb(comp):
    bb = comp.static_mesh.get_bounding_box()
    tf = comp.get_world_transform()
    corners = [
        ue.Vector(x, y, z)
        for x in (bb.min.x, bb.max.x)
        for y in (bb.min.y, bb.max.y)
        for z in (bb.min.z, bb.max.z)
    ]
    pts = [ue.MathLibrary.transform_location(tf, c) for c in corners]
    return (
        min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts),
        max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts),
    )


def _aabb_overlap(a, b, pad=0.0):
    return (
        a[3] + pad > b[0] and a[0] - pad < b[3]
        and a[4] + pad > b[1] and a[1] - pad < b[4]
        and a[5] + pad > b[2] and a[2] - pad < b[5]
    )


def _mesh_vertices_local(sm, cache):
    key = sm.get_path_name()
    if key not in cache:
        dm, _ = ue.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(
            sm, ue.DynamicMesh(), ue.GeometryScriptCopyMeshFromAssetOptions(), ue.GeometryScriptMeshReadLOD())
        _, verts, _ = ue.GeometryScript_MeshQueries.get_all_vertex_positions(dm, False)
        cache[key] = [(float(v.x), float(v.y), float(v.z)) for v in ue.GeometryScript_List.convert_vector_list_to_array(verts)]
    return cache[key]


def verify_stable_lights(actors, house_report, yard_report):
    issues = []
    all_actors = list(actors.get_all_level_actors())
    by_label = {a.get_actor_label(): a for a in all_actors}

    # --- 1. Stablemaster Cabin Light Count (1 interior + 1 exterior porch = 2) ---
    cabin_actor = by_label.get('Village_Stable_MasterHouse_Lights')
    if not cabin_actor:
        issues.append('Missing Village_Stable_MasterHouse_Lights')
        cabin_lights = []
        cabin_lanterns = []
    else:
        cabin_lights = list(cabin_actor.get_components_by_class(ue.PointLightComponent))
        cabin_lanterns = [
            c for c in cabin_actor.get_components_by_class(ue.StaticMeshComponent)
            if not isinstance(c, ue.InstancedStaticMeshComponent)
            and c.static_mesh and c.static_mesh.get_name() == 'SM_Props_Lantern_02A'
        ]
    interior_lights = [
        c for c in cabin_lights
        if (HOUSE_CX - 280.0 <= c.get_world_location().x <= HOUSE_CX + 280.0
            and HOUSE_CY - 280.0 <= c.get_world_location().y <= HOUSE_CY + 280.0)
    ]
    exterior_lights = [c for c in cabin_lights if c not in interior_lights]
    if len(interior_lights) != 1:
        issues.append(f'Expected exactly 1 cabin interior light, found {len(interior_lights)}')
    if len(exterior_lights) != 1:
        issues.append(f'Expected exactly 1 cabin exterior porch light, found {len(exterior_lights)}')

    # --- 2. Yard & Barn Stall-Divider Light Count (3 yard + 8 stall dividers = 11) ---
    yard_actor = by_label.get('Village_Stable_Dressing_YardLights')
    if not yard_actor:
        issues.append('Missing Village_Stable_Dressing_YardLights')
        yard_lights = []
        yard_lanterns = []
    else:
        yard_lights = list(yard_actor.get_components_by_class(ue.PointLightComponent))
        yard_lanterns = [
            c for c in yard_actor.get_components_by_class(ue.StaticMeshComponent)
            if not isinstance(c, ue.InstancedStaticMeshComponent)
            and c.static_mesh and c.static_mesh.get_name() == 'SM_Props_Lantern_02A'
        ]
    if len(yard_lights) != 11:
        issues.append(f'Expected 11 PointLights on Village_Stable_Dressing_YardLights (3 yard + 8 stall dividers), found {len(yard_lights)}')
    if len(yard_lanterns) != 11:
        issues.append(f'Expected 11 lantern meshes on Village_Stable_Dressing_YardLights, found {len(yard_lanterns)}')

    # Collect target lanterns to verify against ALL world geometry (2 cabin + 8 barn stall dividers)
    target_lanterns = []
    for c in cabin_lanterns:
        bb = _mesh_world_aabb(c)
        target_lanterns.append(('Cabin_' + c.get_name(), bb))
    for c in yard_lanterns:
        bb = _mesh_world_aabb(c)
        cx = 0.5 * (bb[0] + bb[3])
        cy = 0.5 * (bb[1] + bb[4])
        if 3600.0 <= cx <= 5200.0 and cy >= 3400.0:
            target_lanterns.append(('Barn_' + c.get_name(), bb))

    if len(target_lanterns) != 10:
        issues.append(f'Expected 10 checked lanterns (2 cabin + 8 barn stall dividers), found {len(target_lanterns)}')

    # --- 3. Headroom & Partition Clearance Checks ---
    lantern_boxes = []
    for name, bb in target_lanterns:
        cx, cy = 0.5 * (bb[0] + bb[3]), 0.5 * (bb[1] + bb[4])
        lantern_boxes.append(dict(
            name=name,
            x=[round(bb[0], 1), round(bb[3], 1)],
            y=[round(bb[1], 1), round(bb[4], 1)],
            z=[round(bb[2], 1), round(bb[5], 1)],
        ))
        if name.startswith('Cabin_') and HOUSE_CY - 280.0 <= cy <= HOUSE_CY + 280.0:
            if bb[2] - FLOOR_TOP_Z < 200.0:
                issues.append(f'{name} headroom above wood deck too low: {bb[2] - FLOOR_TOP_Z:.1f} cm')
            if bb[5] >= 299.5:
                issues.append(f'{name} top {bb[5]:.1f} clips ceiling beam soffit 300.0 cm')
        elif name.startswith('Barn_') and cy < 3530.0:
            # Front courtyard pilaster lantern
            if bb[2] < 200.0:
                issues.append(f'{name} front pilaster bottom_z={bb[2]:.1f} < 200 cm headroom')
            if bb[4] > 3515.0:
                issues.append(f'{name} front pilaster max_y={bb[4]:.1f} too close to roof eave 3520.2 cm')
        elif name.startswith('Barn_') and cy >= 3700.0:
            # Interior stall-divider pendant above A05 (top 165.0) & below tie-beam (bottom 271.2)
            if bb[2] < 210.0:
                issues.append(f'{name} interior divider bottom_z={bb[2]:.1f} too close to A05 top 165.0 cm')
            if bb[5] > 265.0:
                issues.append(f'{name} interior divider top_z={bb[5]:.1f} too close to tie-beam soffit 271.2 cm')

    # --- 4. Exact Vertex-Level + AABB Anti-Clipping Check Against ALL Stable Structures & Props ---
    # For composite meshes whose overall AABB spans hollow interiors (A01_Bent, A01_Roof, PierShoes, BentJoint,
    # LongPlates, DoorWall, WindowWall, Roof, RoofEnd), we test EVERY actual mesh vertex against each lantern AABB!
    hollow_meshes = {
        'SM_Stable_A01_Bent', 'SM_Stable_A01_Roof', 'SM_Stable_PierShoes',
        'SM_Stable_BentJoint', 'SM_Stable_LongPlates', 'SM_H_OldWall_Door_00A',
        'SM_H_OldWall_Window_00A', 'SM_Roof_00A', 'SM_RoofEnd_00A',
    }
    vert_cache = {}
    clip_hits = []

    for a in all_actors:
        lbl = a.get_actor_label()
        if not lbl.startswith('Village_Stable_'):
            continue
        if lbl in ('Village_Stable_MasterHouse_Lights', 'Village_Stable_Dressing_YardLights'):
            continue
        if 'PackedFloor' in lbl or 'Traffic' in lbl or 'WestPaddock' in lbl:
            continue
        for comp in a.get_components_by_class(ue.StaticMeshComponent):
            sm = comp.static_mesh
            if not sm:
                continue
            sm_name = sm.get_name()
            bb = sm.get_bounding_box()
            corners = [
                ue.Vector(x, y, z)
                for x in (bb.min.x, bb.max.x)
                for y in (bb.min.y, bb.max.y)
                for z in (bb.min.z, bb.max.z)
            ]
            inst = isinstance(comp, ue.InstancedStaticMeshComponent)
            count = comp.get_instance_count() if inst else 1
            for i in range(count):
                tf = comp.get_instance_transform(i, True) if inst else comp.get_world_transform()
                pts = [ue.MathLibrary.transform_location(tf, c) for c in corners]
                inst_bb = (
                    min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts),
                    max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts),
                )
                for lname, lbb in target_lanterns:
                    if not _aabb_overlap(lbb, inst_bb, pad=1.0):
                        continue
                    if sm_name in hollow_meshes:
                        # Transform lantern AABB into mesh local space or test vertices in world space
                        inv_tf = ue.MathLibrary.invert_transform(tf)
                        l_corners = [
                            ue.Vector(x, y, z)
                            for x in (lbb[0] - 1.0, lbb[3] + 1.0)
                            for y in (lbb[1] - 1.0, lbb[4] + 1.0)
                            for z in (lbb[2] - 1.0, lbb[5] + 1.0)
                        ]
                        loc_pts = [ue.MathLibrary.transform_location(inv_tf, c) for c in l_corners]
                        lx0, lx1 = min(p.x for p in loc_pts), max(p.x for p in loc_pts)
                        ly0, ly1 = min(p.y for p in loc_pts), max(p.y for p in loc_pts)
                        lz0, lz1 = min(p.z for p in loc_pts), max(p.z for p in loc_pts)
                        verts = _mesh_vertices_local(sm, vert_cache)
                        hit_v = [v for v in verts if lx0 <= v[0] <= lx1 and ly0 <= v[1] <= ly1 and lz0 <= v[2] <= lz1]
                        if hit_v:
                            clip_hits.append(dict(lantern=lname, obstacle=lbl, mesh=sm_name, idx=i, hit_verts=len(hit_v)))
                    else:
                        clip_hits.append(dict(
                            lantern=lname, obstacle=lbl, mesh=sm_name, idx=i,
                            obstacle_bb=[round(v, 1) for v in inst_bb],
                        ))

    if clip_hits:
        issues.append(f'Lantern clipping/conflict detected: {clip_hits}')

    # --- 5. Zero Null Materials + Regression Checks (R45 Traffic Decal & R49 Wood Deck) ---
    null_mats = []
    for a in all_actors:
        lbl = a.get_actor_label()
        if not lbl.startswith('Village_Stable_'):
            continue
        for c in a.get_components_by_class(ue.StaticMeshComponent):
            if c.static_mesh is None:
                continue
            for i in range(c.get_num_materials()):
                if c.get_material(i) is None:
                    null_mats.append(f'{lbl}.{c.get_name()}[{i}]')
    if null_mats:
        issues.append(f'Null materials: {null_mats}')

    traffic = by_label.get('Village_Stable_Traffic')
    decal_depth = round(float(traffic.get_component_by_class(ue.DecalComponent).get_editor_property('decal_size').x), 1) if traffic else None
    if decal_depth is None or decal_depth < 40.0:
        issues.append(f'ForecourtR45 Traffic decal depth regressed: {decal_depth}')

    if not by_label.get('Village_Stable_MasterHouse_DeckWest') or not by_label.get('Village_Stable_MasterHouse_DeckEast'):
        issues.append('StablePolishR49 cabin wood deck missing!')

    leftover_horses = [
        a.get_actor_label() for a in all_actors
        if 'VillageStable.Horses' in map(str, a.tags) or a.get_actor_label().startswith('Village_Stable_Horse_Stall')
    ]
    if leftover_horses:
        issues.append(f'Legacy static horses reappeared: {leftover_horses}')

    return dict(
        cabin_interior_light_count=len(interior_lights),
        cabin_exterior_light_count=len(exterior_lights),
        yard_total_light_count=len(yard_lights),
        checked_lantern_boxes=lantern_boxes,
        clip_hits=clip_hits,
        null_materials=null_mats,
        traffic_decal_depth_cm=decal_depth,
        issues=issues,
        passed=len(issues) == 0,
    )


def main():
    BATCH.mkdir(parents=True, exist_ok=True)
    existing_before = sorted((BATCH / 'Before').glob('*/L_AbandonedVillage.umap')) if (BATCH / 'Before').exists() else []
    if existing_before:
        before_copy = existing_before[0]
        before_hash = before_copy.parent.name
    else:
        before_hash = sha256(MAP_FILE)
        before_copy = BATCH / 'Before' / before_hash / MAP_FILE.name
        before_copy.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(MAP_FILE, before_copy)

    world = ue.EditorLoadingAndSavingUtils.load_map(LEVEL)
    if not world:
        raise RuntimeError(f'Failed to load {LEVEL}')
    actors = ue.get_editor_subsystem(ue.EditorActorSubsystem) or ue.new_object(ue.EditorActorSubsystem)

    house_report = install_stable_master_house(actors)
    yard_report = install_ground_detail(actors)
    verify = verify_stable_lights(actors, house_report, yard_report)
    if not verify['passed']:
        (BATCH / 'failed_verify.json').write_text(json.dumps(verify, indent=2, ensure_ascii=False), encoding='utf-8')
        raise RuntimeError('StableLightsR50 verification FAILED: ' + json.dumps(verify['issues'], ensure_ascii=False))

    failed_file = BATCH / 'failed_verify.json'
    if failed_file.exists():
        failed_file.unlink()

    if not ue.EditorLoadingAndSavingUtils.save_map(world, LEVEL):
        raise RuntimeError(f'Failed to save {LEVEL}')

    after_hash = sha256(MAP_FILE)
    after_copy = BATCH / 'After' / after_hash / MAP_FILE.name
    after_copy.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(MAP_FILE, after_copy)

    report = dict(
        batch='StableLightsR50-20261126',
        level=LEVEL,
        before_file=str(before_copy),
        before_sha256=before_hash,
        after_file=str(after_copy),
        after_sha256=after_hash,
        master_house_lights=house_report['lights'],
        yard_and_barn_lights=yard_report['yard_lights'],
        verification=verify,
    )
    (BATCH / 'published.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    ue.log('STABLE_LIGHTS_R50_OK')
    print('STABLE_LIGHTS_R50_OK', flush=True)


if __name__ == '__main__':
    main()
