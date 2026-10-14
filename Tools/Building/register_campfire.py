"""Save one native campfire in the existing Other building catalog. No model edits or tests."""
import datetime
import hashlib
import json
import math
from pathlib import Path
import unreal as u

PROJECT = Path(u.Paths.project_dir()).resolve()
PALETTE = '/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette'
MESH = '/Game/EasyBuildingSystem/Meshes/Props/Stylized/SM_Stylized_Campfire'
CLASS = '/Script/FPSGAME.ColdSteelCampfire'


def main(bridge=False):
    if PROJECT != Path('D:/FPS3D/FPSGAME').resolve():
        raise RuntimeError('Wrong project; no assets changed.')
    commandlet = '-run=pythonscript' in u.SystemLibrary.get_command_line().casefold()
    if bridge:
        level = u.get_editor_subsystem(u.LevelEditorSubsystem)
        if commandlet or not level or level.is_in_play_in_editor():
            raise RuntimeError('Use the mutex bridge in an idle editor.')
    elif not commandlet:
        raise RuntimeError('Use the offline commandlet or main(bridge=True) via the mutex bridge.')
    if any(p.get_name() == PALETTE for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
        raise RuntimeError('Palette has unsaved edits; preserve them.')
    file = PROJECT / 'Content/Building/Voxels/Rounded/DA_VoxelBuildPalette.uasset'
    originals = {p: p.read_bytes() for p in (file, file.with_suffix('.uexp'), file.with_suffix('.ubulk')) if p.exists()}
    palette = u.load_asset(PALETTE)
    mesh = u.load_asset(MESH)
    cls = u.load_class(None, CLASS)
    flame = u.get_default_object(cls).get_editor_property('flame_system') if cls else None
    if not palette or not mesh or not cls or not flame:
        raise RuntimeError('Native class or source asset missing; finish the ordinary Editor build first.')
    entries = list(palette.get_editor_property('components'))
    if any(str(e.id).casefold() == 'campfire' for e in entries):
        raise RuntimeError('Campfire already exists; preserve the existing registration and read its state before changing it.')
    subsystem = u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
    simple = subsystem.get_simple_collision_count(mesh)
    convex = subsystem.get_convex_collision_count(mesh)
    if simple + convex <= 0:
        raise RuntimeError('Source campfire lacks simple collision; do not register an unplaceable/falling piece.')
    bounds = mesh.get_bounds()
    extent = bounds.box_extent
    dimensions = [2 * extent.x, 2 * extent.y, 2 * extent.z]
    cells = [max(1, math.ceil(d / 20.0 - 1e-4)) for d in dimensions]
    entry = u.VoxelBuildPrefab()
    entry.set_editor_property('id', u.Name('campfire'))
    entry.set_editor_property('display_name', u.Text('篝火'))
    entry.set_editor_property('mesh', mesh)
    entry.set_editor_property('actor_class', cls)
    entry.set_editor_property('footprint', u.IntVector(*cells))
    entry.set_editor_property('mount', u.VoxelPrefabMount.FREE)
    entry.set_editor_property('material', u.Name(''))
    # Logic actor and its ghost both use mesh bounds to put the base on the surface.
    entry.set_editor_property('pivot_offset_cm', u.Vector(0, 0, 0))
    entry.set_editor_property('actor_offset_cm', u.Vector(0, 0, 0))
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    receipt_dir = PROJECT / 'SourceAssets/Campfire20261012/RegistrationReceipts' / stamp
    receipt_dir.mkdir(parents=True, exist_ok=False)
    for path, data in originals.items():
        (receipt_dir / path.name).write_bytes(data)
    if any(p.read_bytes() != b for p, b in originals.items()):
        raise RuntimeError('Concurrent catalog write; registration stopped before mutation.')
    palette.modify()
    palette.set_editor_property('components', entries + [entry])
    if not u.EditorAssetLibrary.save_loaded_asset(palette, False):
        raise RuntimeError('Palette save failed; original bytes retained in ' + str(receipt_dir))
    report = {'utc': stamp, 'palette': PALETTE, 'added_id': 'campfire', 'display_name': '篝火',
        'menu': 'B → 其他 → 篝火', 'actor_class': CLASS, 'mesh': mesh.get_path_name(),
        'flame': flame.get_path_name(), 'radius_cm': 500, 'natural_consumption_multiplier': 0.5,
        'dimensions_cm': dimensions, 'footprint_cells': cells,
        'simple_collision_count': simple, 'convex_collision_count': convex,
        'original_entry_count': len(entries), 'saved_entry_count': len(entries) + 1,
        'before_sha256': hashlib.sha256(originals[file]).hexdigest(),
        'after_sha256': hashlib.sha256(file.read_bytes()).hexdigest(),
        'mode': 'mutex_bridge' if bridge else 'offline_commandlet', 'saved': True,
        'maps_saved': False, 'gameplay_tested': False, 'new_models': False}
    (receipt_dir / 'receipt.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print('CAMPFIRE_REGISTERED ' + json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
