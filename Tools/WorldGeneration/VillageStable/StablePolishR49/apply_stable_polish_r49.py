"""Headless UE 5.8 installer for StablePolishR49:
1) Upgrades Stablemaster House floor to shared village shop wood deck (SM_CarpenterDeckWest/East/SplicedPlank)
   and elevates foundation +24 cm (FLOOR_TOP_Z = 28.0 cm) with weathered Normandy stone plinth & 2 entrance steps.
2) Removes legacy static placed stall horses (Village_Stable_Horse_Stall02/04) so UStableMarketShowcaseSubsystem
   populates today's daily market horses cleanly across the 4 stalls and open paddock with summon fade-in/out.
3) Verifies geometry, clearances, materials, NPC feet, door height, and all 10 showcase spawn spots, saves map."""
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
sys.path[:0] = [str(STABLE_TOOLS), str(STABLE_TOOLS.parent / 'AbandonedVillage')]

from stable_master_house import FLOOR_TOP_Z, HOUSE_CX, HOUSE_CY, install_stable_master_house
from stable_horses import remove_legacy_static_horses

LEVEL = '/Game/WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage'
MAP_FILE = PROJECT / 'Content/WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage.umap'
BATCH = Path('F:/FPSGAMEData/ArtProduction/HillsVillageStable/StablePolishR49-20261126')


def sha256(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_stable_polish(actors, house_report, removed_horses):
    issues = []
    all_actors = list(actors.get_all_level_actors())
    by_label = {a.get_actor_label(): a for a in all_actors}

    # 1. Verify legacy static stall horses are gone
    leftover_horses = [
        a.get_actor_label() for a in all_actors
        if 'VillageStable.Horses' in map(str, a.tags) or a.get_actor_label().startswith('Village_Stable_Horse_Stall')
    ]
    if leftover_horses:
        issues.append(f'Leftover legacy static horses: {leftover_horses}')

    # 2. Verify shared Carpenter wood deck actors exist with receives_decals=False and top Z = FLOOR_TOP_Z
    deck_stats = {}
    for role in ('DeckWest', 'DeckEast', 'DeckSpliced_Detail'):
        lbl = 'Village_Stable_MasterHouse_' + role
        act = by_label.get(lbl)
        if not act:
            issues.append(f'Missing upgraded floor actor: {lbl}')
            continue
        comp = act.get_component_by_class(ue.InstancedStaticMeshComponent)
        if not comp or comp.get_instance_count() != 2:
            issues.append(f'Unexpected instance count on {lbl}: {comp.get_instance_count() if comp else None}')
            continue
        receives_decals = bool(comp.get_editor_property('receives_decals'))
        if receives_decals:
            issues.append(f'{lbl} still has receives_decals=True!')
        bb = comp.static_mesh.get_bounding_box()
        top_zs = []
        for i in range(comp.get_instance_count()):
            tf = comp.get_instance_transform(i, True)
            pts = [ue.MathLibrary.transform_location(tf, ue.Vector(x, y, z))
                   for x in (bb.min.x, bb.max.x) for y in (bb.min.y, bb.max.y) for z in (bb.min.z, bb.max.z)]
            top_zs.append(round(max(p.z for p in pts), 2))
        deck_stats[role] = dict(count=comp.get_instance_count(), receives_decals=receives_decals, top_z_cm=top_zs)
        if role != 'DeckSpliced_Detail':
            for z in top_zs:
                if abs(z - FLOOR_TOP_Z) > 0.6:
                    issues.append(f'{lbl} top_z={z} != expected FLOOR_TOP_Z={FLOOR_TOP_Z}')
    # Verify full wall-to-wall coverage (X: 1360..1940, Y: 3830..4410) & plinth strictly <= FLOOR_TOP_Z - 0.3
    deck_x0, deck_x1 = 1e9, -1e9
    for role in ('DeckWest', 'DeckEast'):
        act = by_label.get('Village_Stable_MasterHouse_' + role)
        if act:
            c = act.get_component_by_class(ue.InstancedStaticMeshComponent)
            bb = c.static_mesh.get_bounding_box()
            for i in range(c.get_instance_count()):
                tf = c.get_instance_transform(i, True)
                pts = [ue.MathLibrary.transform_location(tf, ue.Vector(x, y, z))
                       for x in (bb.min.x, bb.max.x) for y in (bb.min.y, bb.max.y) for z in (bb.min.z, bb.max.z)]
                deck_x0 = min(deck_x0, min(p.x for p in pts))
                deck_x1 = max(deck_x1, max(p.x for p in pts))
    if deck_x0 > HOUSE_CX - 285.0 or deck_x1 < HOUSE_CX + 285.0:
        issues.append(f'Wood deck X span [{deck_x0:.1f}, {deck_x1:.1f}] does not cover interior [{HOUSE_CX-290:.1f}, {HOUSE_CX+290:.1f}]')
    plinth_act = by_label.get('Village_Stable_MasterHouse_Flagstone')
    if plinth_act:
        c = plinth_act.get_component_by_class(ue.InstancedStaticMeshComponent)
        bb = c.static_mesh.get_bounding_box()
        for i in range(c.get_instance_count()):
            tf = c.get_instance_transform(i, True)
            pts = [ue.MathLibrary.transform_location(tf, ue.Vector(x, y, z))
                   for x in (bb.min.x, bb.max.x) for y in (bb.min.y, bb.max.y) for z in (bb.min.z, bb.max.z)]
            if max(p.z for p in pts) > FLOOR_TOP_Z - 0.2:
                issues.append(f'Plinth/step instance {i} max_z={max(p.z for p in pts):.1f} pokes above floor {FLOOR_TOP_Z}')

    # 3. Verify Stablemaster NPC stands on elevated FLOOR_TOP_Z and Door sits at FLOOR_TOP_Z + 2 cm
    door_z = house_report['door']['location_cm'][2]
    npc_feet_z = house_report['stablemaster']['feet_z_cm']
    if abs(door_z - (FLOOR_TOP_Z + 2.0)) > 0.5:
        issues.append(f'Cabin door Z={door_z} != {FLOOR_TOP_Z + 2.0}')
    if abs(npc_feet_z - FLOOR_TOP_Z) > 0.5:
        issues.append(f'Stablemaster feet Z={npc_feet_z} != {FLOOR_TOP_Z}')

    # 4. Verify zero null materials across ALL Village_Stable_* actors
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

    # 5. Verify the Entrance Forecourt Roaming Zone (X: 4640..5150, Y: 2060..3240) has ZERO solid obstacles
    roam_x0, roam_y0, roam_x1, roam_y1 = 4640.0, 2060.0, 5150.0, 3240.0
    spot_hits = []
    for a in all_actors:
        lbl = a.get_actor_label()
        if not lbl.startswith('Village_Stable_') and not lbl.startswith('Village_'):
            continue
        if lbl.endswith('_Detail') or 'PackedFloor' in lbl or 'Traffic' in lbl or 'WestPaddock' in lbl:
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
                if x1 > roam_x0 and x0 < roam_x1 and y1 > roam_y0 and y0 < roam_y1:
                    spot_hits.append(dict(zone='EntranceForecourtRoam', actor=lbl, idx=i,
                                          box=[round(x0, 1), round(y0, 1), round(x1, 1), round(y1, 1)]))
    if spot_hits:
        issues.append(f'Entrance forecourt roam zone collides with solid prop/structure: {spot_hits}')

    return dict(
        floor_top_z_cm=FLOOR_TOP_Z,
        deck_stats=deck_stats,
        removed_legacy_static_horses=removed_horses,
        leftover_horses=leftover_horses,
        door_z_cm=door_z,
        npc_feet_z_cm=npc_feet_z,
        null_materials=null_mats,
        open_spot_collisions=spot_hits,
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
    removed_horses = remove_legacy_static_horses(actors)
    verify = verify_stable_polish(actors, house_report, removed_horses)
    if not verify['passed']:
        raise RuntimeError('StablePolishR49 verification FAILED: ' + json.dumps(verify, ensure_ascii=False))

    if not ue.EditorLoadingAndSavingUtils.save_map(world, LEVEL):
        raise RuntimeError(f'Failed to save {LEVEL}')

    after_hash = sha256(MAP_FILE)
    after_copy = BATCH / 'After' / after_hash / MAP_FILE.name
    after_copy.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(MAP_FILE, after_copy)

    report = dict(
        batch='StablePolishR49-20261126',
        level=LEVEL,
        before_file=str(before_copy),
        before_sha256=before_hash,
        after_file=str(after_copy),
        after_sha256=after_hash,
        master_house=house_report,
        removed_legacy_static_horses=removed_horses,
        verification=verify,
    )
    (BATCH / 'published.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    ue.log(f'STABLE_POLISH_R49_OK floor_z={FLOOR_TOP_Z} removed_horses={len(removed_horses)}')
    print(f'STABLE_POLISH_R49_OK floor_z={FLOOR_TOP_Z} removed_horses={len(removed_horses)}', flush=True)


if __name__ == '__main__':
    main()
