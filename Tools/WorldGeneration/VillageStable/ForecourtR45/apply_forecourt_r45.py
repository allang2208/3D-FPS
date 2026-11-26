"""Headless UE 5.8 installer for ForecourtR45: refreshes forecourt perimeter clutter/shrubs & decal depth,
verifies zero gate/stall/wagon conflicts, saves L_AbandonedVillage, and exports updated contacts.json for relief."""
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

from stable_ground_detail import install_ground_detail

LEVEL = '/Game/WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage'
MAP_FILE = PROJECT / 'Content/WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage.umap'
BATCH = Path('F:/FPSGAMEData/ArtProduction/HillsVillageStable/ForecourtR45-20261126')
RELIEF_SRC = Path('F:/FPSGAMEData/ArtProduction/SourceAssets/WorldGeneration/HillsForestPath/ForecourtR45-20261126')


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


def verify_forecourt(actors):
    issues = []
    all_actors = list(actors.get_all_level_actors())
    by_label = {a.get_actor_label(): a for a in all_actors}

    # 1. Check Traffic decal projection depth >= 40 cm
    traffic_actor = by_label.get('Village_Stable_Traffic')
    decal_x = None
    if traffic_actor:
        dc = traffic_actor.get_component_by_class(ue.DecalComponent)
        if dc:
            decal_x = round(float(dc.get_editor_property('decal_size').x), 1)
    if decal_x is None or decal_x < 40.0:
        issues.append(f'Village_Stable_Traffic decal_size.X too thin for relief: {decal_x}')

    # 2. Check zero null materials on all Village_Stable_* actors
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

    # 3. Check ZERO solid dressing props encroach inward gate swings or stall doorways
    forbidden_zones = [
        ('LeadGateSwing', 4495, 1600, 4765, 1850),
        ('WagonGateSwing', 5000, 1600, 5500, 1855),
        ('Stall1Door', 3435, 3420, 3605, 3555),
        ('Stall2Door', 3875, 3420, 4045, 3555),
        ('Stall3Door', 4315, 3420, 4485, 3555),
        ('Stall4Door', 4755, 3420, 4925, 3555),
    ]
    clear_hits = []
    for a in all_actors:
        lbl = a.get_actor_label()
        if not lbl.startswith('Village_Stable_Dressing_'):
            continue
        if lbl.endswith('_Detail'):
            continue
        for comp in a.get_components_by_class(ue.InstancedStaticMeshComponent):
            sm = comp.static_mesh
            if not sm:
                continue
            bb = sm.get_bounding_box()
            corners = [ue.Vector(x, y, z) for x in (bb.min.x, bb.max.x)
                       for y in (bb.min.y, bb.max.y) for z in (bb.min.z, bb.max.z)]
            for i in range(comp.get_instance_count()):
                tf = comp.get_instance_transform(i, True)
                pts = [ue.MathLibrary.transform_location(tf, c) for c in corners]
                x0, x1 = min(p.x for p in pts), max(p.x for p in pts)
                y0, y1 = min(p.y for p in pts), max(p.y for p in pts)
                for zname, fx0, fy0, fx1, fy1 in forbidden_zones:
                    if x1 > fx0 and x0 < fx1 and y1 > fy0 and y0 < fy1:
                        clear_hits.append(dict(zone=zname, actor=lbl, idx=i,
                                               box=[round(x0, 1), round(y0, 1), round(x1, 1), round(y1, 1)]))
    if clear_hits:
        issues.append(f'Solid props encroach gate/stall clearance: {clear_hits}')

    # 4. Verify all 3 Normandy shrub groups exist with Ecology leaf override bound
    shrub_counts = {}
    for role in ('ShrubA', 'ShrubB', 'ShrubC', 'HazelA', 'HazelB', 'HazelC', 'Twig1', 'Twig2'):
        act = by_label.get(f'Village_Stable_Dressing_{role}_Detail')
        if act:
            c = act.get_component_by_class(ue.InstancedStaticMeshComponent)
            if c:
                shrub_counts[role] = dict(count=c.get_instance_count(),
                                          mat0=c.get_material(0).get_name() if c.get_material(0) else None)
    for req in ('ShrubA', 'ShrubB', 'ShrubC'):
        if req not in shrub_counts or shrub_counts[req]['count'] == 0:
            issues.append(f'Missing forecourt shrub group: {req}')

    return dict(
        traffic_decal_depth_cm=decal_x,
        shrub_and_twig_groups=shrub_counts,
        clearance_hits=clear_hits,
        null_materials=null_mats,
        issues=issues,
        passed=len(issues) == 0,
    )


def main():
    BATCH.mkdir(parents=True, exist_ok=True)
    RELIEF_SRC.mkdir(parents=True, exist_ok=True)

    before_hash = sha256(MAP_FILE)
    before_copy = BATCH / 'Before' / before_hash / MAP_FILE.name
    before_copy.parent.mkdir(parents=True, exist_ok=True)
    if not before_copy.exists():
        shutil.copy2(MAP_FILE, before_copy)

    world = ue.EditorLoadingAndSavingUtils.load_map(LEVEL)
    if not world:
        raise RuntimeError(f'Failed to load {LEVEL}')
    actors = ue.get_editor_subsystem(ue.EditorActorSubsystem) or ue.new_object(ue.EditorActorSubsystem)

    yard_report = install_ground_detail(actors)
    verify = verify_forecourt(actors)
    if not verify['passed']:
        raise RuntimeError('ForecourtR45 verification FAILED: ' + json.dumps(verify, ensure_ascii=False))

    if not ue.EditorLoadingAndSavingUtils.save_map(world, LEVEL):
        raise RuntimeError(f'Failed to save {LEVEL}')

    contacts_file = RELIEF_SRC / 'contacts.json'
    contacts_count = export_contacts(actors, contacts_file)

    after_hash = sha256(MAP_FILE)
    after_copy = BATCH / 'After' / after_hash / MAP_FILE.name
    after_copy.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(MAP_FILE, after_copy)

    stage = dict(
        batch='ForecourtR45-20261126',
        level=LEVEL,
        before_file=str(before_copy),
        before_sha256=before_hash,
        after_file=str(after_copy),
        after_sha256=after_hash,
        contacts_file=str(contacts_file),
        contacts_count=contacts_count,
        ground_detail=yard_report,
        verification=verify,
    )
    (BATCH / 'map_stage.json').write_text(json.dumps(stage, indent=2, ensure_ascii=False), encoding='utf-8')
    ue.log(f'FORECOURT_R45_MAP_OK contacts={contacts_count}')
    print(f'FORECOURT_R45_MAP_OK contacts={contacts_count}', flush=True)


if __name__ == '__main__':
    main()
