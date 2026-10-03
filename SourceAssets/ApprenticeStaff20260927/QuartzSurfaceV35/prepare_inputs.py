"""Preserve only the current default quartz targets and export authoring inputs.

Use the existing editor mutex bridge or a background Python commandlet. This
reads the actual installed geometry; it never exports a scene or starts PIE.
"""
import json
import shutil
from pathlib import Path
import unreal as u

ROOT = Path(__file__).resolve().parent
BASE = '/Game/Weapons/ApprenticeStaff20260927'
DEST = BASE + '/QuartzSurfaceV35'
INPUTS = ROOT / 'Inputs'
E = u.EditorAssetLibrary
NAMES = ('SM_Staff_Base', 'SM_Staff_head_crystal_false')
WORLD = BASE + '/QuartzAimV22/Materials/M_Staff_QuartzDenseV22'
PREVIEW = '/Game/UI/GunsmithWorkbench/M_StaffQuartzPreviewV23'
TARGETS = [BASE + folder + name for folder in ('/Meshes/', '/BarkRebuildV21/Meshes/') for name in NAMES]
TARGETS += [WORLD, PREVIEW]


def prepare():
    receipt_path = ROOT / 'inputs-receipt.json'
    if receipt_path.exists() and json.loads(receipt_path.read_text(encoding='utf-8')).get('complete'):
        print('STAFF_QUARTZ_V35_INPUTS_REUSED')
        return
    if '-run=' not in u.SystemLibrary.get_command_line().lower():
        editor = u.get_editor_subsystem(u.LevelEditorSubsystem)
        if editor and editor.is_in_play_in_editor():
            raise RuntimeError('Default quartz replacement requires PIE to end; current assets preserved.')
    dirty = {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    conflicts = [p for p in TARGETS if p in dirty]
    if conflicts:
        raise RuntimeError('Unsaved default quartz targets: ' + ', '.join(conflicts))
    INPUTS.mkdir(parents=True, exist_ok=True)
    receipt = {'complete': False, 'backups': [], 'meshes': [], 'runtime_tested': False, 'rendered': False}
    for path in TARGETS:
        asset = u.load_asset(path)
        if not asset:
            raise RuntimeError('Missing default quartz input ' + path)
        # Preserve the original package names for an offline byte-for-byte
        # rollback. UE duplicates below are separately available to artists.
        relative = Path(path.removeprefix('/Game/') + '.uasset')
        disk_before = ROOT / 'Before/Content' / relative
        if not disk_before.exists():
            disk_before.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT.parents[2] / 'Content' / relative, disk_before)
        suffix = ('PreviewMaterial' if path == PREVIEW else 'WorldMaterial' if path == WORLD
                  else ('ActiveMeshes/' if '/Meshes/' in path and '/BarkRebuildV21/' not in path
                        else 'V21Meshes/') + asset.get_name())
        backup = DEST + '/Before/' + suffix
        if not E.does_asset_exist(backup):
            preserved = E.duplicate_asset(path, backup)
            if not preserved or not E.save_loaded_asset(preserved, False):
                raise RuntimeError('Cannot preserve ' + path)
        receipt['backups'].append({'target': path, 'backup': backup})
        receipt_path.write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    for name in NAMES:
        asset = u.load_asset(BASE + '/Meshes/' + name)
        task = u.AssetExportTask()
        task.object = asset
        task.filename = str(INPUTS / (name + '.fbx'))
        task.automated = True
        task.prompt = False
        task.replace_identical = True
        task.exporter = u.StaticMeshExporterFBX()
        task.options = u.FbxExportOption()
        task.options.set_editor_property('ascii', False)
        if not u.Exporter.run_asset_export_task(task):
            raise RuntimeError('Cannot export authoring input ' + name)
        bounds = asset.get_bounds()
        receipt['meshes'].append({
            'name': name, 'fbx': task.filename,
            'origin_cm': [bounds.origin.x, bounds.origin.y, bounds.origin.z],
            'size_cm': [bounds.box_extent.x * 2, bounds.box_extent.y * 2, bounds.box_extent.z * 2],
            'slots': [{'name': str(s.material_slot_name),
                       'material': s.material_interface.get_path_name() if s.material_interface else None}
                      for s in asset.static_materials]})
        receipt_path.write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    receipt['complete'] = True
    receipt_path.write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print('STAFF_QUARTZ_V35_INPUTS_SAVED meshes=2 backups=6')


prepare()
