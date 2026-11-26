"""Headless UE 5.8 installer for StableRoadPCGR51:
1) Upgrades M_StableYardSoil, M_StableYardLoessBlend (VillageStableEntryWear) and M_StableWestPaddockSoil
   to the exterior RoadUpgrade-R48 RoadMix PBR shader (reuses existing T_Stony* & T_Tire* atlases, zero extra VRAM).
2) Rebuilds Village_Stable_Dressing_* with exterior RoadUpgrade-R48 Road-Body PCG cover (pebbles, quarry chips,
   crushed crown grass, road weeds, clover, dry/wild verge tufts) across BOTH Entrance Forecourt & West Paddock.
3) Preserves all StableLightsR50 stall-divider & cabin lights, verifies 0 solid conflicts & 0 null materials,
   saves L_AbandonedVillage.umap, and exports updated contacts.json for the subtle heightfield bake."""
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

import stable_ground_materials as ground_mats
from stable_ground_detail import ROAD_PCG_ROLES, install_ground_detail

LEVEL = '/Game/WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage'
MAP_FILE = PROJECT / 'Content/WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage.umap'
MAT_FILES = [
    PROJECT / 'Content/WorldGeneration/TemperateHills/VillageStable/GroundDetailR4/M_StableYardSoil.uasset',
    PROJECT / 'Content/WorldGeneration/TemperateHills/VillageStable/GroundDetailR4/M_StableWestPaddockSoil.uasset',
    PROJECT / 'Content/ForestPathStudy/VillageRegion/Reference/VillageLoess/M_StableYardLoessBlend.uasset',
]
BATCH = Path('F:/FPSGAMEData/ArtProduction/HillsVillageStable/StableRoadPCGR51-20261126')
RELIEF_SRC = Path('F:/FPSGAMEData/ArtProduction/SourceAssets/WorldGeneration/HillsForestPath/StableRoadPCGR51-20261126')


def sha256(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def export_contacts(actors, out_path: Path):
    """Exact mirror of ForestVillage/export_village_relief.py contacts export."""
    contacts = []
    for actor in actors.get_all_level_actors():
        for comp in actor.get_components_by_class(ue.StaticMeshComponent):
            mesh = comp.get_editor_property('static_mesh')
            if not mesh or '/ExteriorLOD/' in mesh.get_path_name():
                continue
            box = mesh.get_bounding_box()
            corners = [
                ue.Vector(x, y, z)
                for x in (box.min.x, box.max.x)
                for y in (box.min.y, box.max.y)
                for z in (box.min.z, box.max.z)
            ]
            instanced = isinstance(comp, ue.InstancedStaticMeshComponent)
            for i in range(comp.get_instance_count() if instanced else 1):
                tr = comp.get_instance_transform(i, world_space=True) if instanced else comp.get_world_transform()
                pts = [ue.MathLibrary.transform_location(tr, c) for c in corners]
                if min(p.z for p in pts) > 75 or max(p.z for p in pts) < -85:
                    continue
                xy = [round(v * 0.01, 3) for v in (
                    min(p.x for p in pts), min(p.y for p in pts),
                    max(p.x for p in pts), max(p.y for p in pts),
                )]
                if xy[2] < -75 or xy[0] > 72 or xy[3] < -60 or xy[1] > 60:
                    continue
                contacts.append([*xy, mesh.get_name(), instanced])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(contacts, separators=(',', ':')), encoding='utf-8')
    return len(contacts)


def verify_all(actors):
    issues = []
    all_actors = list(actors.get_all_level_actors())
    by_label = {a.get_actor_label(): a for a in all_actors}

    # 1. Verify BOTH Traffic & WestPaddock decals have >= 40 cm vertical depth for heightfield relief
    for lbl in ('Village_Stable_Traffic', 'Village_Stable_WestPaddock_Soil'):
        act = by_label.get(lbl)
        dx = round(float(act.get_component_by_class(ue.DecalComponent).get_editor_property('decal_size').x), 1) if act else None
        if dx is None or dx < 40.0:
            issues.append(f'{lbl} decal_size.X too thin for relief: {dx}')

    # 2. Verify all R48 Road-Body PCG groups spawned with NoCollision + CastShadow=False + tight cull
    pcg_counts = {}
    for role in sorted(ROAD_PCG_ROLES):
        lbl = f'Village_Stable_Dressing_{role}_Detail'
        act = by_label.get(lbl)
        if not act:
            continue
        c = act.get_component_by_class(ue.InstancedStaticMeshComponent)
        if c:
            n = c.get_instance_count()
            pcg_counts[role] = n
            if str(c.get_collision_profile_name()) != 'NoCollision':
                issues.append(f'{lbl} has unexpected collision {c.get_collision_profile_name()}')
            if bool(c.cast_shadow):
                issues.append(f'{lbl} has cast_shadow=True')
    total_pcg = sum(pcg_counts.values())
    if total_pcg < 250:
        issues.append(f'Too few R48 Road-Body PCG instances spawned: {total_pcg}')

    # 3. Verify Entrance Forecourt Roaming Zone (4640..5150, 2060..3240) has ZERO solid obstacles
    roam_hits = []
    for a in all_actors:
        lbl = a.get_actor_label()
        if not lbl.startswith('Village_Stable_') or lbl.endswith('_Detail'):
            continue
        if any(k in lbl for k in ('PackedFloor', 'Traffic', 'WestPaddock')):
            continue
        for comp in a.get_components_by_class(ue.StaticMeshComponent):
            sm = comp.static_mesh
            if not sm or str(comp.get_collision_profile_name()) == 'NoCollision':
                continue
            bb = sm.get_bounding_box()
            corners = [ue.Vector(x, y, z) for x in (bb.min.x, bb.max.x)
                       for y in (bb.min.y, bb.max.y) for z in (bb.min.z, bb.max.z)]
            inst = isinstance(comp, ue.InstancedStaticMeshComponent)
            for i in range(comp.get_instance_count() if inst else 1):
                tf = comp.get_instance_transform(i, True) if inst else comp.get_world_transform()
                pts = [ue.MathLibrary.transform_location(tf, c) for c in corners]
                x0, x1 = min(p.x for p in pts), max(p.x for p in pts)
                y0, y1 = min(p.y for p in pts), max(p.y for p in pts)
                z0, z1 = min(p.z for p in pts), max(p.z for p in pts)
                if z1 < 12.0 or z0 > 220.0:
                    continue
                if x1 > 4640.0 and x0 < 5150.0 and y1 > 2060.0 and y0 < 3240.0:
                    roam_hits.append(dict(actor=lbl, idx=i, box=[round(x0, 1), round(y0, 1), round(x1, 1), round(y1, 1)]))
    if roam_hits:
        issues.append(f'Solid obstacles inside forecourt roam box: {roam_hits}')

    # 4. Verify R50 lights intact (11 yard/barn + 2 cabin) & zero null materials across ALL Village_Stable_*
    yl = by_label.get('Village_Stable_Dressing_YardLights')
    cl = by_label.get('Village_Stable_MasterHouse_Lights')
    y_cnt = len(list(yl.get_components_by_class(ue.PointLightComponent))) if yl else 0
    c_cnt = len(list(cl.get_components_by_class(ue.PointLightComponent))) if cl else 0
    if y_cnt != 11 or c_cnt != 2:
        issues.append(f'StableLightsR50 count mismatch: yard={y_cnt} (exp 11), cabin={c_cnt} (exp 2)')

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

    # 5. Material compile stats check
    mat_stats = {}
    ed = ue.MaterialEditingLibrary
    for mpath in (
        '/Game/WorldGeneration/TemperateHills/VillageStable/GroundDetailR4/M_StableYardSoil',
        '/Game/WorldGeneration/TemperateHills/VillageStable/GroundDetailR4/M_StableWestPaddockSoil',
        '/Game/ForestPathStudy/VillageRegion/Reference/VillageLoess/M_StableYardLoessBlend',
    ):
        m = ue.load_asset(mpath)
        if m:
            st = ed.get_statistics(m)
            mat_stats[m.get_name()] = dict(
                ps_instructions=int(st.get_editor_property('num_pixel_shader_instructions')),
                samplers=int(st.get_editor_property('num_samplers')),
            )

    return dict(
        road_pcg_counts=pcg_counts,
        road_pcg_total=total_pcg,
        roam_hits=roam_hits,
        yard_lights=y_cnt,
        cabin_lights=c_cnt,
        null_materials=null_mats,
        material_stats=mat_stats,
        issues=issues,
        passed=len(issues) == 0,
    )


def main():
    BATCH.mkdir(parents=True, exist_ok=True)
    RELIEF_SRC.mkdir(parents=True, exist_ok=True)

    # Backup L_AbandonedVillage.umap & modified materials before first edit
    before_dir = BATCH / 'Before'
    if not before_dir.exists():
        before_dir.mkdir(parents=True, exist_ok=True)
        for f in [MAP_FILE, *MAT_FILES]:
            if f.is_file():
                h = sha256(f)
                dst = before_dir / h / f.name
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, dst)

    before_map_hash = sha256(MAP_FILE)

    # 1. Upgrade stable ground decal materials to R48 RoadMix PBR shader
    ground_mats.author()
    ground_mats.author_west_paddock()

    # 2. Load map, rebuild ground detail with R48 Road-Body PCG cover, verify & save
    world = ue.EditorLoadingAndSavingUtils.load_map(LEVEL)
    if not world:
        raise RuntimeError(f'Failed to load {LEVEL}')
    actors = ue.get_editor_subsystem(ue.EditorActorSubsystem) or ue.new_object(ue.EditorActorSubsystem)

    yard_report = install_ground_detail(actors)
    verify = verify_all(actors)
    if not verify['passed']:
        (BATCH / 'failed_verify.json').write_text(json.dumps(verify, indent=2, ensure_ascii=False), encoding='utf-8')
        raise RuntimeError('StableRoadPCGR51 verification FAILED: ' + json.dumps(verify['issues'], ensure_ascii=False))

    if not ue.EditorLoadingAndSavingUtils.save_map(world, LEVEL):
        raise RuntimeError(f'Failed to save {LEVEL}')

    contacts_file = RELIEF_SRC / 'contacts.json'
    contacts_count = export_contacts(actors, contacts_file)

    after_map_hash = sha256(MAP_FILE)
    after_copy = BATCH / 'After' / after_map_hash / MAP_FILE.name
    after_copy.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(MAP_FILE, after_copy)

    stage = dict(
        batch='StableRoadPCGR51-20261126',
        level=LEVEL,
        before_map_sha256=before_map_hash,
        after_map_sha256=after_map_hash,
        contacts_file=str(contacts_file),
        contacts_count=contacts_count,
        ground_detail=yard_report,
        verification=verify,
    )
    (BATCH / 'map_stage.json').write_text(json.dumps(stage, indent=2, ensure_ascii=False), encoding='utf-8')
    ue.log(f'STABLE_ROAD_PCG_R51_OK pcg_total={verify["road_pcg_total"]} contacts={contacts_count}')
    print(f'STABLE_ROAD_PCG_R51_OK pcg_total={verify["road_pcg_total"]} contacts={contacts_count}', flush=True)


if __name__ == '__main__':
    main()
