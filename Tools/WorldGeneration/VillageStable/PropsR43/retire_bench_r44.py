"""Project-wide retirement of broken SM_Mil_Trench_Bench_Wood_01 & relocation of Windmill doorway shrubs."""
import hashlib
import json
import math
import shutil
from pathlib import Path
import unreal as ue

ASSETS = ue.EditorAssetLibrary
BENCH_DIR_UE = '/Game/MilitaryTrench/Assets/3D/Mil_Trench_Bench_Wood_01'
BENCH_DIR_DISK = Path('F:/FPSGAMEData/Content/MilitaryTrench/Assets/3D/Mil_Trench_Bench_Wood_01')
BENCH_KEY = 'Mil_Trench_Bench_Wood_01'

# Spacious open perimeter fence spots for relocating the 8 doorway-blocking Village_05_Windmill hazel shrubs
OPEN_FENCE_SHRUB_TARGETS = [
    (1055.0, 4495.0, -2.0, 0.32, 22.0),   # SW paddock fence corner
    (1225.0, 4555.0, -2.0, 0.30, 108.0),  # South paddock fence margin
    (2770.0, 4555.0, -2.0, 0.34, -35.0),  # South-east paddock fence
    (3040.0, 4545.0, -2.0, 0.28, 64.0),   # South fence behind farrier corner
    (5700.0, 4460.0, -2.0, 0.34, -18.0),  # SE barn service fence corner
    (5715.0, 3440.0, -2.0, 0.32, 145.0),  # East fence north of barn
    (5720.0, 1790.0, -2.0, 0.30, -72.0),  # NE wagon gate fence corner
    (4285.0, 2060.0, -2.0, 0.32, 42.0),   # NW forecourt bakery fence edge
    (1120.0, 3380.0, -2.0, 0.26, 85.0),   # Extra fallback: NW fence margin
    (2200.0, 3360.0, -2.0, 0.28, -50.0),  # Extra fallback: North paddock fence
]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _strip_bench_from_loaded_world(actors) -> list:
    """Remove all actors or SMC/ISM components referencing Mil_Trench_Bench_Wood_01 in the currently loaded level."""
    removed = []
    subs = ue.get_engine_subsystem(ue.SubobjectDataSubsystem)
    data = ue.SubobjectDataBlueprintFunctionLibrary

    for actor in list(actors.get_all_level_actors()):
        lbl = actor.get_actor_label()
        smcs = list(actor.get_components_by_class(ue.StaticMeshComponent))
        hit_comps = []
        for comp in smcs:
            sm = comp.static_mesh
            mesh_hit = bool(sm and BENCH_KEY in sm.get_path_name())
            mat_hit = any(
                comp.get_material(i) is not None and BENCH_KEY in comp.get_material(i).get_path_name()
                for i in range(comp.get_num_materials())
            )
            if mesh_hit or mat_hit:
                hit_comps.append(comp)
        if not hit_comps:
            continue

        # If the entire actor is solely a bench actor (e.g. StaticMeshActor or single-component HISM), destroy actor cleanly
        if len(hit_comps) == len(smcs) and (isinstance(actor, ue.StaticMeshActor) or BENCH_KEY in lbl or lbl.endswith('_WoodBench')):
            actors.destroy_actor(actor)
            removed.append(dict(action='destroyed_actor', actor=lbl, components=len(hit_comps)))
            continue

        # Multi-component building actor (Windmill, Bakery, Gunshop): remove only the bench component cleanly
        actor.modify()
        handles = subs.k2_gather_subobject_data_for_instance(actor)
        root_handle = handles[0] if handles else None
        for comp in hit_comps:
            cname = comp.get_name()
            if isinstance(comp, ue.InstancedStaticMeshComponent):
                comp.clear_instances()
            for i in range(comp.get_num_materials()):
                comp.set_material(i, None)
            comp.set_static_mesh(None)
            deleted_via_sub = False
            for h in handles:
                if data.get_associated_object(data.get_data(h)) == comp:
                    try:
                        subs.delete_subobject(root_handle, h, actor)
                        deleted_via_sub = True
                    except Exception:
                        deleted_via_sub = False
                    break
            if not deleted_via_sub:
                try:
                    comp.destroy_component(actor)
                except Exception:
                    pass
            removed.append(dict(action='stripped_component', actor=lbl, component=cname, subobject_deleted=deleted_via_sub))
    return removed


def _strip_bench_from_blueprint(bp_path: str) -> dict:
    """Remove any component referencing Mil_Trench_Bench_Wood_01 from a Blueprint asset and save it."""
    if not ASSETS.does_asset_exist(bp_path):
        return dict(blueprint=bp_path, status='not_found')
    bp = ue.load_asset(bp_path)
    subs = ue.get_engine_subsystem(ue.SubobjectDataSubsystem)
    data = ue.SubobjectDataBlueprintFunctionLibrary
    handles = list(subs.k2_gather_subobject_data_for_blueprint(bp))
    root = handles[0] if handles else None
    stripped = []
    for h in handles:
        obj = data.get_associated_object(data.get_data(h))
        if isinstance(obj, ue.StaticMeshComponent):
            sm = obj.static_mesh
            hit = bool(sm and BENCH_KEY in sm.get_path_name()) or any(
                obj.get_material(i) is not None and BENCH_KEY in obj.get_material(i).get_path_name()
                for i in range(obj.get_num_materials())
            )
            if hit:
                obj.modify()
                obj.set_static_mesh(None)
                for i in range(obj.get_num_materials()):
                    obj.set_material(i, None)
                try:
                    subs.delete_subobjects(root, [h], bp)
                except Exception:
                    pass
                stripped.append(obj.get_name())
    if stripped:
        try:
            ue.BlueprintEditorLibrary.compile_blueprint(bp)
        except Exception:
            pass
        ASSETS.save_loaded_asset(bp, False)
    return dict(blueprint=bp_path, stripped=stripped)


def _archive_disk_files(files: list[Path], root_base: Path, trash_dir: Path) -> list:
    records = []
    for src in files:
        if not src.exists():
            continue
        rel = src.relative_to(root_base)
        dst = trash_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        records.append(dict(
            original=str(src),
            archived=str(dst),
            size_bytes=src.stat().st_size,
            sha256=_sha256(src),
        ))
    return records


def clean_external_maps_and_bp(trash_dir: Path, permanent_manifest_path: Path) -> dict:
    """Clean BP_Trench_Wall_02, L_MilitaryTrench_FPS_Test & external-actor references before loading L_AbandonedVillage."""
    content_root = Path('F:/FPSGAMEData/Content')
    trash_dir.mkdir(parents=True, exist_ok=True)
    manifest_file = trash_dir / 'manifest.json'
    prior = json.loads(manifest_file.read_text(encoding='utf-8')) if manifest_file.exists() else None

    reg = ue.AssetRegistryHelpers.get_asset_registry()
    all_refs = set()
    for pkg in (
        BENCH_DIR_UE + '/StaticMeshes/SM_Mil_Trench_Bench_Wood_01',
        BENCH_DIR_UE + '/Materials/MI_Mil_Trench_Bench_Wood_01',
        BENCH_DIR_UE + '/Materials/MI_Mil_Trench_Bench_Wood_01_RVT',
    ):
        deps = reg.get_referencers(pkg, ue.AssetRegistryDependencyOptions(include_hard_package_references=True)) or []
        all_refs.update(str(d) for d in deps)

    # 1. Archive all 6 Mil_Trench_Bench_Wood_01 source .uasset files BEFORE touching anything (if not already archived)
    archived = list(prior.get('archived_files', [])) if prior else []
    archived_originals = {r['original'] for r in archived}
    bench_files = sorted(BENCH_DIR_DISK.rglob('*')) if BENCH_DIR_DISK.exists() else []
    bench_files = [p for p in bench_files if p.is_file() and str(p) not in archived_originals]
    if bench_files:
        archived.extend(_archive_disk_files(bench_files, content_root, trash_dir))

    # 2. Clean Blueprint reference (only if still referenced)
    bp_pkg = '/Game/MilitaryTrench/Assets/Blueprints/BP_Trench_Wall_02'
    if bp_pkg in all_refs:
        bp_report = _strip_bench_from_blueprint(bp_pkg)
    else:
        bp_report = prior.get('blueprint_cleanup', dict(blueprint=bp_pkg, status='already_clean')) if prior else dict(blueprint=bp_pkg, status='not_referenced')

    # 3. Clean non-village map L_MilitaryTrench_FPS_Test (only if still referenced — avoids needless map load!)
    trench_map = '/Game/GameMaps/L_MilitaryTrench_FPS_Test'
    if trench_map in all_refs and ASSETS.does_asset_exist(trench_map):
        w = ue.EditorLoadingAndSavingUtils.load_map(trench_map)
        trench_removed = []
        if w:
            actors = ue.get_editor_subsystem(ue.EditorActorSubsystem) or ue.new_object(ue.EditorActorSubsystem)
            trench_removed = _strip_bench_from_loaded_world(actors)
            if trench_removed:
                ue.EditorLoadingAndSavingUtils.save_map(w, trench_map)
    else:
        trench_removed = prior.get('trench_map_cleanup', []) if prior else []

    # 4. Clean World Partition external actor packages still referencing Mil_Trench_Bench_Wood_01
    ext_removed = list(prior.get('external_actor_cleanup', [])) if prior else []
    for dep in sorted(all_refs):
        if not dep.startswith('/Game/__ExternalActors__/'):
            continue
        disk_file = content_root / (dep.removeprefix('/Game/') + '.uasset')
        if disk_file.exists():
            archived.extend(_archive_disk_files([disk_file], content_root, trash_dir))
            ok_del = ASSETS.delete_asset(dep)
            if not ok_del and disk_file.exists():
                disk_file.unlink()
                ok_del = True
            ext_removed.append(dict(package=dep, disk=str(disk_file), deleted=bool(ok_del)))

    manifest = dict(
        retired_asset_root=BENCH_DIR_UE,
        trash_dir=str(trash_dir),
        archived_files=archived,
        blueprint_cleanup=bp_report,
        trench_map_cleanup=trench_removed,
        external_actor_cleanup=ext_removed,
    )
    manifest_file.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')
    permanent_manifest_path.parent.mkdir(parents=True, exist_ok=True)
    permanent_manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')
    return manifest


def strip_bench_in_current_level(actors) -> list:
    """Clean all Mil_Trench_Bench_Wood_01 instances/actors in the currently loaded L_AbandonedVillage."""
    return _strip_bench_from_loaded_world(actors)


def finalize_delete_bench_assets() -> dict:
    """Delete all 6 Mil_Trench_Bench_Wood_01 assets from UE Content & verify zero files remain on disk."""
    delete_order = [
        BENCH_DIR_UE + '/StaticMeshes/SM_Mil_Trench_Bench_Wood_01',
        BENCH_DIR_UE + '/Materials/MI_Mil_Trench_Bench_Wood_01',
        BENCH_DIR_UE + '/Materials/MI_Mil_Trench_Bench_Wood_01_RVT',
        BENCH_DIR_UE + '/Textures/T_Mil_Trench_Bench_Wood_01_B',
        BENCH_DIR_UE + '/Textures/T_Mil_Trench_Bench_Wood_01_N',
        BENCH_DIR_UE + '/Textures/T_Mil_Trench_Bench_Wood_01_ORM',
    ]
    results = {}
    for pkg in delete_order:
        if ASSETS.does_asset_exist(pkg):
            results[pkg] = bool(ASSETS.delete_asset(pkg))
        else:
            results[pkg] = 'already_gone'

    # Clean empty subfolders and any lingering package files on disk if UE held a soft transient cache
    if BENCH_DIR_DISK.exists():
        remaining_files = [p for p in BENCH_DIR_DISK.rglob('*') if p.is_file()]
        for p in remaining_files:
            p.unlink()
        shutil.rmtree(BENCH_DIR_DISK, ignore_errors=True)

    still_on_disk = list(BENCH_DIR_DISK.rglob('*')) if BENCH_DIR_DISK.exists() else []
    still_in_ue = [p for p in delete_order if ASSETS.does_asset_exist(p)]
    if still_on_disk or still_in_ue:
        raise RuntimeError(f'Failed full deletion of {BENCH_KEY}: disk={still_on_disk}, ue={still_in_ue}')
    return dict(deleted=results, remaining_disk=0, remaining_ue=0)


def relocate_cabin_doorway_shrubs(actors) -> dict:
    """Relocate all Village_05_Windmill hazel shrubs blocking the Stablemaster Cabin doorway to open fence perimeters."""
    windmill = next((a for a in actors.get_all_level_actors() if a.get_actor_label() == 'Village_05_Windmill'), None)
    if not windmill:
        raise RuntimeError('Missing Village_05_Windmill actor')

    windmill.modify()
    moved = []
    target_idx = 0
    for comp in windmill.get_components_by_class(ue.InstancedStaticMeshComponent):
        sm = comp.static_mesh
        if not sm or not sm.get_name().startswith('SM_Hazel'):
            continue
        comp.modify()
        for i in range(comp.get_instance_count()):
            tf = comp.get_instance_transform(i, True)
            loc = tf.translation
            # Catch every Windmill hazel shrub inside the cabin & doorway zone (X: 1150..2150, Y: 3300..4450)
            if 1150.0 <= loc.x <= 2150.0 and 3300.0 <= loc.y <= 4450.0:
                tx, ty, tz, t_max_sc, tyaw = OPEN_FENCE_SHRUB_TARGETS[target_idx % len(OPEN_FENCE_SHRUB_TARGETS)]
                target_idx += 1
                orig_sc = float(tf.scale3d.x)
                new_sc = min(orig_sc, t_max_sc) if orig_sc > 0.22 else max(orig_sc, 0.24)
                new_tf = ue.Transform(
                    location=ue.Vector(tx, ty, tz),
                    rotation=ue.Rotator(yaw=tyaw),
                    scale=ue.Vector(new_sc, new_sc, new_sc),
                )
                comp.update_instance_transform(i, new_tf, True, True, True)
                moved.append(dict(
                    mesh=sm.get_name(),
                    index=i,
                    from_cm=[round(float(loc.x), 1), round(float(loc.y), 1), round(float(loc.z), 1)],
                    to_cm=[tx, ty, tz],
                    from_scale=round(orig_sc, 2),
                    to_scale=round(new_sc, 2),
                ))
    return dict(relocated_count=len(moved), relocated=moved)
