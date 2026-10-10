"""Author and save V36 materials at the stable default quartz world/UI paths."""
import json
import runpy
import shutil
import traceback
from pathlib import Path
import unreal as u

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[2]
BASE = '/Game/Weapons/ApprenticeStaff20260927'
DEST = BASE + '/QuartzOpticsV36'
WORLD = BASE + '/QuartzAimV22/Materials/M_Staff_QuartzDenseV22'
PREVIEW = '/Game/UI/GunsmithWorkbench/M_StaffQuartzPreviewV23'
E = u.EditorAssetLibrary
R = ROOT / 'install-receipt.json'
report = dict(revision=36, complete=False, saved_assets=[], installed=[], backups=[],
              runtime_tested=False, rendered=False, cpp_changed=False,
              geometry_changed=False, lamp_point_light_changed=False)


def record():
    R.write_text(json.dumps(report, indent=2), encoding='utf-8')


def install():
    dirty = {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    conflicts = [p for p in dirty if p in (WORLD, PREVIEW) or p.startswith(DEST + '/')]
    if conflicts:
        raise RuntimeError('Unsaved quartz targets: ' + ', '.join(conflicts))
    if '-run=' not in u.SystemLibrary.get_command_line().lower():
        editor = u.get_editor_subsystem(u.LevelEditorSubsystem)
        if editor and editor.is_in_play_in_editor():
            raise RuntimeError('PIE is active; quartz assets preserved until play ends.')
    for path, name in ((WORLD, 'WorldMaterial'), (PREVIEW, 'PreviewMaterial')):
        original = u.load_asset(path)
        if not original:
            raise RuntimeError('Missing active quartz material ' + path)
        relative = Path(path.removeprefix('/Game/') + '.uasset')
        before = ROOT / 'Before/Content' / relative
        if not before.exists():
            before.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(PROJECT / 'Content' / relative, before)
        backup_path = DEST + '/Before/' + name
        if not E.does_asset_exist(backup_path):
            backup = E.duplicate_asset(path, backup_path)
            if not backup or not E.save_loaded_asset(backup, False):
                raise RuntimeError('Cannot preserve ' + path)
        report['backups'].append(dict(target=path, copy=backup_path, disk=str(before)))
        record()

    head = u.load_asset(BASE + '/Meshes/SM_Staff_head_crystal_false')
    if not head:
        raise RuntimeError('Default quartz head is missing')
    slots = [i for i, slot in enumerate(head.static_materials)
             if slot.material_interface and slot.material_interface.get_path_name().split('.')[0] == WORLD]
    if not slots:
        raise RuntimeError('Installed head no longer uses the expected quartz material; source left untouched')
    mesh, status = u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(head, u.DynamicMesh(),
                        u.GeometryScriptCopyMeshFromAssetOptions(), u.GeometryScriptMeshReadLOD())
    if status != u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError('Cannot extract current quartz authoring geometry')
    _, vertices, _ = u.GeometryScript_MeshQueries.get_all_vertex_positions(mesh, False)
    vertices = u.GeometryScript_List.convert_vector_list_to_array(vertices)
    _, triangles, _ = u.GeometryScript_MeshQueries.get_all_triangle_indices(mesh, False)
    triangles = u.GeometryScript_List.convert_triangle_list_to_array(triangles)
    chosen = []
    for i, tri in enumerate(triangles):
        material_id, valid = u.GeometryScript_Materials.get_triangle_material_id(mesh, i)
        if valid and material_id in slots:
            chosen.append([tri.x, tri.y, tri.z])
    if not chosen:
        raise RuntimeError('No quartz triangles in installed head')
    indices = sorted({i for t in chosen for i in t})
    compact = {original:i for i, original in enumerate(indices)}
    source = dict(source=head.get_path_name(),
                  vertices_cm=[[vertices[i].x, vertices[i].y, vertices[i].z] for i in indices],
                  triangles=[[compact[i] for i in t] for t in chosen])
    (ROOT/'installed-quartz-input.json').write_text(json.dumps(source,separators=(',',':')),encoding='utf-8')
    geometry = runpy.run_path(str(ROOT/'author_optics.py'))['author'](source)
    report['optical_planes'] = len(geometry['planes'])
    report['source_quartz_triangles'] = len(chosen)
    record()
    print('STAFF_QUARTZ_V36_OPTICS_AUTHORED planes=' + str(len(geometry['planes'])), flush=True)

    build = runpy.run_path(str(ROOT/'ue_material.py'))['build_quartz_material']
    for preview in (False, True):
        asset = build(rebuild=True, preview=preview, candidate=True)
        report['saved_assets'].append(asset.get_path_name())
        record()
    # Both complete independent graphs must compile and save before installation.
    for preview in (False, True):
        asset = build(rebuild=True, preview=preview)
        report['saved_assets'].append(asset.get_path_name())
        report['installed'].append(asset.get_path_name())
        record()
    report['complete'] = True
    record()
    print('STAFF_QUARTZ_V36_SAVED materials=4 geometry_changed=false tested=false rendered=false', flush=True)


try:
    install()
except Exception:
    report['error'] = traceback.format_exc()
    record()
    raise
