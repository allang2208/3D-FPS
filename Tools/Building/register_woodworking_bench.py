"""Register the clean woodworking layout while preserving existing palette fields.

Requires imported meshes and source provenance from
SourceAssets/WoodworkingBenchV6Controls20261013. Run with -WoodworkingBenchRegister
in a headless commandlet, or main(bridge=True) through the editor mutex bridge.
"""
from pathlib import Path
import datetime
import hashlib
import json
import math
import re
import sys

PROJECT = Path(__file__).resolve().parents[2]
ROOT = PROJECT / 'SourceAssets/WoodworkingBenchV6Controls20261013'
PALETTE = '/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette'
PALETTE_FILE = PROJECT / 'Content/Building/Voxels/Rounded/DA_VoxelBuildPalette.uasset'
ID = 'woodworking_bench'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_inputs():
    config = json.loads((ROOT / 'registration.json').read_text(encoding='utf-8-sig'))
    if config.get('revision') != 'V6Controls20261013' or config.get('ready_for_registration') is not True:
        raise RuntimeError('clean-layout source/model review is incomplete; no palette entry will be written.')
    if config.get('menu_category') != 'other' or config.get('material_group') != '':
        raise RuntimeError('Woodworking bench belongs to the top-level Other tab; material_group must be empty.')
    mesh_path = config.get('mesh', '')
    if not isinstance(mesh_path, str) or not mesh_path.startswith('/Game/Building/'):
        raise RuntimeError('Specify the real imported clean-layout static mesh path under /Game/Building/.')
    relative = config.get('source_manifest', '')
    if not relative:
        raise RuntimeError('The verified clean-layout source manifest is required.')
    manifest = (ROOT / relative).resolve()
    if not manifest.is_relative_to(ROOT.resolve()) or not manifest.is_file():
        raise RuntimeError('Source manifest must exist inside SourceAssets/WoodworkingBenchV6Controls20261013.')
    package = mesh_path.split('.')[0]
    mesh_file = PROJECT / 'Content' / (package.removeprefix('/Game/') + '.uasset')
    if not mesh_file.is_file():
        raise RuntimeError('clean-layout mesh has not been imported: ' + str(mesh_file))
    return config, manifest, mesh_file


def main(bridge=False):
    config, manifest, mesh_file = check_inputs()  # Fail before Unreal import or any writes.
    import unreal as u
    if Path(u.Paths.project_dir()).resolve() != PROJECT.resolve():
        raise RuntimeError('Wrong Unreal project.')
    commandlet = '-run=pythonscript' in u.SystemLibrary.get_command_line().casefold()
    if bridge:
        if commandlet:
            raise RuntimeError('Bridge mode is only for the current interactive editor.')
        level = u.get_editor_subsystem(u.LevelEditorSubsystem)
        if not level or level.is_in_play_in_editor():
            raise RuntimeError('Registration requires an idle editor outside PIE.')
    elif not commandlet or '-WoodworkingBenchRegister' not in u.SystemLibrary.get_command_line():
        raise RuntimeError('Use the offline commandlet with -WoodworkingBenchRegister, or the mutex bridge.')
    dirty = u.EditorLoadingAndSavingUtils.get_dirty_content_packages()
    if any(p.get_name() == PALETTE for p in dirty):
        raise RuntimeError('Active palette contains unsaved edits; preserve them and stop.')
    protected = [PALETTE_FILE] + [p for p in [PALETTE_FILE.with_suffix('.uexp'), PALETTE_FILE.with_suffix('.ubulk')] if p.exists()]
    original_bytes = {str(path):path.read_bytes() for path in protected}
    before = {path:hashlib.sha256(data).hexdigest() for path, data in original_bytes.items()}
    editor = u.EditorAssetLibrary
    palette = editor.load_asset(PALETTE)
    mesh = editor.load_asset(config['mesh'])
    if not palette or not isinstance(mesh, u.StaticMesh):
        raise RuntimeError('Active palette or clean-layout static mesh is unavailable.')
    manifest_hash = sha(manifest)
    if editor.get_metadata_tag(mesh, 'WoodworkingBenchSourceManifestSHA256') != manifest_hash:
        raise RuntimeError('Mesh provenance does not match the reviewed clean-layout source manifest.')
    entries = list(palette.get_editor_property('components'))
    ids = [str(e.id).casefold() for e in entries]
    if len(ids) != len(set(ids)):
        raise RuntimeError('Existing palette has duplicate component IDs; preserve it for review.')
    for entry in entries:
        if str(entry.id).casefold() != ID and entry.mesh == mesh:
            raise RuntimeError('Refusing to reuse another buildable model: ' + str(entry.id))
    slots = list(mesh.static_materials)
    if not slots or any(slot.material_interface is None for slot in slots):
        raise RuntimeError('All original original material slots must be assigned before registration.')
    subsystem = u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
    lods = subsystem.get_lod_count(mesh)
    triangles = [mesh.get_num_triangles(i) for i in range(lods)]
    simple = subsystem.get_simple_collision_count(mesh)
    convex = subsystem.get_convex_collision_count(mesh)
    body = mesh.get_editor_property('body_setup')
    if not triangles or any(t <= 0 for t in triangles) or simple + convex <= 0 or not body:
        raise RuntimeError('Mesh needs valid geometry and simple/convex collision before registration.')
    collision_mode = body.get_editor_property('collision_trace_flag')
    if collision_mode == u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE:
        raise RuntimeError('Complex-as-simple cannot support the existing falling-prefab physics.')
    bounds = mesh.get_bounds()
    ext = bounds.box_extent
    dimensions = [2 * ext.x, 2 * ext.y, 2 * ext.z]
    if any(not math.isfinite(x) or x <= 0 for x in dimensions):
        raise RuntimeError('Invalid clean-layout mesh bounds.')
    cells = [max(1, math.ceil(x / 20.0 - 1e-4)) for x in dimensions]
    # ComputeTransform already subtracts the rotated Bounds.Origin. Do not subtract it twice.
    offset = [0, 0, ext.z - cells[2] * 10.0]
    # Preserve every existing gameplay/placement field; this revision only replaces the mesh.
    if ID in ids:
        entry = entries[ids.index(ID)]
        entry.set_editor_property('mesh', mesh)
    else:
        entry = u.VoxelBuildPrefab()
        entry.set_editor_property('id', ID)
        entry.set_editor_property('display_name', u.Text('木工工作台'))
        entry.set_editor_property('mesh', mesh)
        entry.set_editor_property('footprint', u.IntVector(*cells))
        entry.set_editor_property('mount', u.VoxelPrefabMount.FREE)
        entry.set_editor_property('material', u.Name(config['material_group']))
        entry.set_editor_property('pivot_offset_cm', u.Vector(*offset))
    def normalized(value):
        return re.sub(r'0x[0-9A-Fa-f]+', 'POINTER', str(value))
    previous_other = [normalized(e) for e in entries if str(e.id).casefold() != ID]
    if ID in ids:
        entries[ids.index(ID)] = entry
    else:
        entries.append(entry)  # Keep every existing entry's order and all category order unchanged.
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    receipt_dir = ROOT / 'RegistrationReceipts' / stamp
    receipt_dir.mkdir(parents=True, exist_ok=False)
    for path, data in original_bytes.items():
        (receipt_dir / Path(path).name).write_bytes(data)
    if any(sha(Path(p)) != h for p, h in before.items()):
        raise RuntimeError('Concurrent palette change before registration.')
    palette.modify()
    palette.set_editor_property('components', entries)
    after = list(palette.components)
    if [normalized(e) for e in after if str(e.id).casefold() != ID] != previous_other:
        raise RuntimeError('Unrelated palette entry changed; do not save.')
    if sum(str(e.id).casefold() == ID for e in after) != 1:
        raise RuntimeError('Woodworking ID is not unique; do not save.')
    if any(sha(Path(p)) != h for p, h in before.items()):
        raise RuntimeError('Concurrent palette disk change; do not save.')
    if not editor.save_loaded_asset(palette, False):
        raise RuntimeError('Palette save failed; backup preserved at ' + str(receipt_dir))
    report = {'utc':stamp, 'id':ID, 'caption':'木工工作台', 'menu':'B → 其他 → 木工工作台', 'menu_category':'other', 'material_group':'',
              'palette':PALETTE, 'mesh':mesh.get_path_name(), 'source_manifest_sha256':manifest_hash,
              'mesh_sha256':sha(mesh_file), 'bounds_origin_cm':[bounds.origin.x,bounds.origin.y,bounds.origin.z],
              'dimensions_cm':dimensions, 'footprint_cells':cells, 'pivot_offset_cm':offset,
              'materials':[str(s.material_interface.get_path_name()) for s in slots],
              'triangles_by_lod':triangles, 'collision_mode':str(collision_mode),
              'simple_collision_count':simple, 'convex_collision_count':convex,
              'palette_backup_sha256':before, 'palette_after_sha256':sha(PALETTE_FILE),
              'other_entries_preserved':True, 'registration_mode':'mutex_bridge' if bridge else 'offline_commandlet', 'existing_entry_gameplay_fields_preserved':ID in ids,
              'maps_saved':False, 'gameplay_tested':False}
    (receipt_dir / 'receipt.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print('WOODWORKING_BENCH_REGISTERED ' + json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError) as error:
        print('WOODWORKING_BENCH_BLOCKED: ' + str(error), file=sys.stderr)
        raise SystemExit(2)
