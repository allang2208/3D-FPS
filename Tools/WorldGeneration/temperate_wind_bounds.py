"""Author culling margins for the active hills' DynamicWind skeletal foliage.

UE 5.8 DynamicWindData has no animation bounds. InstancedSkinnedMesh sends
SkeletalMesh.GetBounds to instance culling, so a rest-pose box clips wind motion.
These are deliberately bounded authoring margins, not a measured wind envelope.
They still require a moving-camera/storm visual check in the game.
"""
import json
import shutil
from pathlib import Path
import unreal as u

PROJECT = Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir()))
ROOT = PROJECT / 'SourceAssets/HillsVegetationStreaming20261113'
BASE = '/Game/WorldGeneration/TemperateHills'


def apply_bounds(mesh):
    data = next((d for d in mesh.get_editor_property('asset_user_data')
                 if d and d.get_class().get_name() == 'DynamicWindSkeletalData'), None)
    if not data or not data.get_editor_property('bIsEnabled'):
        raise RuntimeError('Expected active DynamicWind data: ' + mesh.get_path_name())
    bounds = mesh.get_imported_bounds()
    height = bounds.box_extent.z * 2
    # Keep vertical normalization in DynamicWindProvider unchanged. The broad
    # phase primarily needs lateral room for swaying trunks and branch crowns.
    # Preserve any larger authored margin and never accumulate on reruns.
    lateral = max(height * .12, max(bounds.box_extent.x, bounds.box_extent.y) * .25)
    changed = False
    before, after = {}, {}
    for prop in ('positive_bounds_extension', 'negative_bounds_extension'):
        old = mesh.get_editor_property(prop)
        new = u.Vector(max(old.x, lateral), max(old.y, lateral), old.z)
        before[prop] = [old.x, old.y, old.z]
        after[prop] = [new.x, new.y, new.z]
        if new.x != old.x or new.y != old.y:
            mesh.set_editor_property(prop, new)
            changed = True
    return {'changed': changed, 'height_cm': height, 'lateral_margin_cm': lateral,
            'before': before, 'after': after}


def main():
    world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    for command in ('Editor.AsyncSkinnedAssetCompilation 0', 'gc.AllowParallelGC 0'):
        u.SystemLibrary.execute_console_command(world, command)
    da = u.load_asset(BASE + '/DA_TemperateHillsStreaming')
    targets = {}
    for role in ('trees', 'forest_saplings', 'forest_shrubs', 'forest_ferns'):
        for soft in da.get_editor_property(role):
            targets[soft.get_path_name()] = role
    dirty = {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if any(path.split('.')[0] in dirty for path in targets):
        raise RuntimeError('A wind bounds target has unsaved edits')
    report = {'meshes': {}, 'saved': [], 'game_run': False, 'visual_acceptance': False}
    for path, role in targets.items():
        relative = path.split('.')[0].removeprefix('/Game/')
        for suffix in ('.uasset', '.uexp', '.ubulk'):
            source = PROJECT / 'Content' / (relative + suffix)
            backup = ROOT / 'Before/Content' / (relative + suffix)
            if source.exists() and not backup.exists():
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, backup)
        mesh = u.load_asset(path)
        if not isinstance(mesh, u.SkeletalMesh):
            raise RuntimeError('Expected skeletal vegetation: ' + path)
        row = apply_bounds(mesh)
        row['role'] = role
        report['meshes'][path] = row
        if row['changed']:
            if not u.EditorAssetLibrary.save_loaded_asset(mesh, False):
                raise RuntimeError('Save failed: ' + path)
            report['saved'].append(path)
    ROOT.mkdir(parents=True, exist_ok=True)
    (ROOT / 'wind-bounds.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    u.log(f'HILLS_WIND_BOUNDS_SAVED meshes={len(targets)} saved={len(report["saved"])}')


if __name__ == '__main__':
    main()
